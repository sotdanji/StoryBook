"""시낭송 영상(Poem Video) 및 노래 뮤직비디오(Song Video) 렌더링·스트리밍 라우터 (100% 서버 일원화: Turso DB + Cloudflare R2 + /tmp)"""

import os
import re
import tempfile
import urllib.parse
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import Response, RedirectResponse
from pydantic import BaseModel

from core.project_manager import project_manager

router = APIRouter()

VIDEO_STAGE_DIR = Path(tempfile.gettempdir()) / "storybook_video_stage"


class PoemVideoRenderRequest(BaseModel):
    project_name: Optional[str] = None
    episode_no: Any = 1
    audio_type: str = "tts"  # "tts", "recording", "suno"
    custom_audio_path: Optional[str] = None
    aspect_ratio: str = "16:9"  # "16:9" | "9:16"
    spectrum_style: str = "bar"  # "bar" | "mirror" | "wave" | "off"


def _resolve_pid_and_work(project_name: Optional[str], episode_no: Any):
    pid = project_manager._resolve_project_id(project_name or project_manager.get_active_project_id())
    ep_digits = re.sub(r'[^0-9]', '', str(episode_no))
    ep_num = int(ep_digits) if ep_digits else 1
    ep_str = f"{ep_num:02d}"
    mgr = project_manager.get_manuscript_manager(pid)
    work = mgr.get_work_by_episode(str(ep_num)) or mgr.get_work_by_episode(f"제{ep_str}화")
    return pid, ep_num, ep_str, mgr, work


@router.get("/api/poem_video/status/{project_name}/{episode_no}")
async def get_poem_video_status_endpoint(project_name: str, episode_no: str):
    """[100% 서버 일원화] 특정 회차의 영상 제작 상태 및 오디오/삽화 리소스 상태 조회 (Turso DB + R2)"""
    try:
        from core.r2_storage import r2_storage
        pid, ep_num, ep_str, mgr, work = _resolve_pid_and_work(project_name, episode_no)
        safe_proj = pid.replace(" ", "_")

        video_info = {"exists": False}
        v_file = getattr(work, "video_file", "") if work else ""
        if v_file:
            v_name = Path(v_file).name
            v_bytes = r2_storage.get_media_bytes(f"/projects/{pid}/videos/{v_name}") or r2_storage.get_media_bytes(v_file)
            size_mb = round(len(v_bytes) / (1024 * 1024), 2) if v_bytes else 0.0
            video_info = {
                "exists": True,
                "filename": v_name,
                "size_mb": size_mb,
                "url": f"/api/poem_video/stream/{safe_proj}/{v_name}",
                "has_preview": bool(getattr(work, "video_preview", ""))
            }

        recite_tracks = []
        if work:
            # 1) 육성 시 낭송
            v_user = getattr(work, "voice_user_file", "")
            if v_user:
                fname = Path(v_user).name
                recite_tracks.append({
                    "type": "voice",
                    "label": "육성 시 낭송",
                    "icon": "🎙️",
                    "filename": fname,
                    "rel_path": f"music/{fname}",
                    "url": f"/projects/{safe_proj}/music/{fname}",
                    "exists": True
                })
            # 2) AI 시 낭송
            v_tts = getattr(work, "voice_tts_file", "") or getattr(work, "recite_file", "")
            if v_tts and v_tts != v_user:
                fname = Path(v_tts).name
                recite_tracks.append({
                    "type": "ai_recite",
                    "label": "AI 시 낭송",
                    "icon": "🤖",
                    "filename": fname,
                    "rel_path": f"music/{fname}",
                    "url": f"/projects/{safe_proj}/music/{fname}",
                    "exists": True
                })
            # 3) 음악 시 낭송
            v_bgm = getattr(work, "voice_suno_file", "") or getattr(work, "voice_bgm_file", "")
            if v_bgm:
                fname = Path(v_bgm).name
                recite_tracks.append({
                    "type": "music_recite",
                    "label": "음악 시 낭송",
                    "icon": "🎻",
                    "filename": fname,
                    "rel_path": f"music/{fname}",
                    "url": f"/projects/{safe_proj}/music/{fname}",
                    "exists": True
                })

        detected_audio = recite_tracks[0]["filename"] if recite_tracks else None
        detected_path = recite_tracks[0]["rel_path"] if recite_tracks else None
        img_exists = bool(work and getattr(work, "image_file", ""))

        return {
            "success": True,
            "episode_no": ep_num,
            "video": video_info,
            "detected_audio": detected_audio,
            "detected_path": detected_path,
            "recite_tracks": recite_tracks,
            "sources": {
                "has_audio": len(recite_tracks) > 0,
                "audio_name": detected_audio or "낭송 음원 없음",
                "audio_count": len(recite_tracks),
                "image": img_exists
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def _stage_work_media_to_tmp(pid: str, ep_str: str, work: Any, custom_audio_path: Optional[str] = None, prefer_song: bool = False):
    """R2 스토리지에서 해당 회차의 삽화 및 음원 바이트를 /tmp 스테이징 폴더로 다운로드하여 파일 경로 반환"""
    from core.r2_storage import r2_storage
    stage_dir = VIDEO_STAGE_DIR / pid / ep_str
    stage_dir.mkdir(parents=True, exist_ok=True)

    # 1. 삽화 이미지 로드
    img_rel = (getattr(work, "image_file", "") if work else "") or f"images/{ep_str}_삽화.jpg"
    img_name = Path(img_rel.replace("\\", "/")).name
    img_bytes = r2_storage.get_media_bytes(f"/projects/{pid}/images/{img_name}") or r2_storage.get_media_bytes(img_rel)
    if not img_bytes:
        raise FileNotFoundError(f"제{int(ep_str)}화의 삽화 이미지가 클라우드 서버에 없습니다.")
    staged_img = stage_dir / img_name
    staged_img.write_bytes(img_bytes)

    # 2. 음원 로드
    aud_candidates = []
    if custom_audio_path:
        aud_candidates.append(custom_audio_path)
    if work:
        if prefer_song:
            for f in (getattr(work, "music_file", ""), getattr(work, "audio_file", "")):
                if f:
                    aud_candidates.append(f)
        else:
            for f in (getattr(work, "recite_file", ""), getattr(work, "voice_tts_file", ""), getattr(work, "voice_user_file", ""), getattr(work, "music_file", "")):
                if f:
                    aud_candidates.append(f)
    aud_candidates.extend([f"music/{ep_str}_음원.mp3", f"music/{ep_str}_낭송.wav", f"music/{ep_str}_육성.webm"])

    staged_aud = None
    for cand in aud_candidates:
        c_name = Path(str(cand).replace("\\", "/")).name
        aud_bytes = r2_storage.get_media_bytes(f"/projects/{pid}/music/{c_name}") or r2_storage.get_media_bytes(str(cand))
        if aud_bytes:
            staged_aud = stage_dir / c_name
            staged_aud.write_bytes(aud_bytes)
            break

    if not staged_aud:
        raise FileNotFoundError(f"제{int(ep_str)}화의 음원 파일이 클라우드 서버에 없습니다.")

    return str(staged_img), str(staged_aud)


@router.post("/api/poem_video/render")
async def render_poem_video_endpoint(req: PoemVideoRenderRequest):
    """시화 영상 비디오 엔진 호출 (R2 에셋 -> /tmp 스테이징 -> Remotion 렌더링 -> R2 & Turso DB 저장)"""
    try:
        from core.video_director_bridge import video_director_bridge
        pid, ep_num, ep_str, mgr, work = _resolve_pid_and_work(req.project_name, req.episode_no)

        title = work.title if (work and work.title) else f"제{ep_num}화"
        poem_body = (work.poem_body or "") if work else ""
        poem_lines = [line.strip() for line in poem_body.splitlines() if line.strip()]

        if not poem_lines:
            raise ValueError(f"제{ep_num}화의 시 본문 원고가 없습니다.")

        img_path, audio_path = _stage_work_media_to_tmp(pid, ep_str, work, req.custom_audio_path, prefer_song=False)

        res = video_director_bridge.render_poem_video(
            project_name=pid,
            episode_num=ep_num,
            title=title,
            poem_lines=poem_lines,
            image_path=img_path,
            audio_path=audio_path,
            aspect_ratio=req.aspect_ratio,
            spectrum_style=req.spectrum_style,
            is_async=True
        )

        return {
            "success": True,
            "task_id": res.get("task_id"),
            "title": title,
            "audio_used": os.path.basename(audio_path)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/api/poem_video/task/{task_id}")
async def get_poem_video_task_endpoint(task_id: str):
    """영상 렌더링 백그라운드 작업 상태 조회"""
    from core.video_director_bridge import video_director_bridge
    status = video_director_bridge.get_task_status(task_id)
    return {"success": True, "task": status}


@router.post("/api/poem_video/upload_custom_audio")
async def upload_custom_audio_endpoint(
    project_name: str = Form(...),
    episode_no: str = Form(...),
    audio_file: UploadFile = File(...)
):
    """
    [100% 서버 일원화] 사용자가 직접 녹음 파일/Suno 파일 업로드 시
    Cloudflare R2에 업로드하고 Turso DB 해당 회차의 음원으로 자동 등록합니다.
    """
    try:
        from core.r2_storage import r2_storage
        pid, ep_num, ep_str, mgr, work = _resolve_pid_and_work(project_name, episode_no)

        ext = Path(audio_file.filename or "audio.mp3").suffix.lower()
        if ext not in [".mp3", ".wav", ".m4a", ".ogg", ".webm"]:
            ext = ".mp3"

        target_name = f"{ep_str}_음원{ext}"
        rel_path = f"music/{target_name}"
        raw_bytes = await audio_file.read()

        r2_storage.upload_bytes(raw_bytes, f"{pid}/{rel_path}")
        if work:
            work.music_file = rel_path
            mgr.save_work(work)

        return {
            "success": True,
            "filename": target_name,
            "path": f"/projects/{pid}/{rel_path}",
            "size_bytes": len(raw_bytes)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/api/poem_video/open_music_folder")
async def open_music_folder_endpoint(project_name: str = Form(...)):
    """클라우드 서버 일원화 안내"""
    return {
        "success": True,
        "message": "모든 음원은 클라우드 서버(Cloudflare R2)에 안전하게 보관되어 있습니다."
    }


@router.get("/gallery/api/poem_video/stream/{project_name}/{filename}")
@router.get("/api/poem_video/stream/{project_name}/{filename}")
async def stream_poem_video_endpoint(project_name: str, filename: str):
    """완성된 MP4 영상을 Cloudflare R2에서 브라우저로 스트리밍"""
    from core.r2_storage import r2_storage
    r2_storage.reload_config()
    pid = project_manager._resolve_project_id(project_name)
    v_name = Path(filename).name

    if r2_storage.public_url:
        rel_key = f"{pid}/videos/{v_name}"
        return RedirectResponse(url=f"{r2_storage.public_url}/{urllib.parse.quote(rel_key, safe='/~')}", status_code=307)

    raw_bytes = r2_storage.get_media_bytes(f"/projects/{pid}/videos/{v_name}")
    if raw_bytes:
        return Response(content=raw_bytes, media_type="video/mp4")

    raise HTTPException(status_code=404, detail="비디오 파일을 찾을 수 없습니다.")


class MergePlaylistRequest(BaseModel):
    project_name: Optional[str] = None
    aspect_ratio: str = "16:9"


@router.post("/api/poem_video/merge_playlist")
async def merge_poem_video_playlist_endpoint(req: MergePlaylistRequest):
    """프로젝트 내 완성된 영상들을 R2에서 /tmp로 수집하여 하나의 전편 플레이리스트 영상으로 결합"""
    try:
        from core.video_director_bridge import video_director_bridge
        pid = project_manager._resolve_project_id(req.project_name or project_manager.get_active_project_id())
        res = video_director_bridge.merge_playlist_video(
            project_name=pid,
            aspect_ratio=req.aspect_ratio
        )
        return res
    except Exception as e:
        return {"success": False, "error": str(e)}


class SongVideoRenderRequest(BaseModel):
    project_name: Optional[str] = None
    episode_no: Any = 1
    lyrics_text: str
    custom_audio_path: Optional[str] = None
    custom_srt_path: Optional[str] = None
    aspect_ratio: str = "16:9"  # "16:9" | "9:16"
    spectrum_style: str = "mirror"  # "mirror" | "wave" | "bar" | "off"
    lyric_mode: str = "focus2line"  # "focus2line" | "rolling"


@router.get("/api/song_video/status/{project_name}/{episode_no}")
async def get_song_video_status_endpoint(project_name: str, episode_no: str):
    """[100% 서버 일원화] 특정 회차의 노래 영상 제작 상태, 음원 및 가사 리소스 상태 조회 (Turso DB + R2)"""
    try:
        from core.r2_storage import r2_storage
        pid, ep_num, ep_str, mgr, work = _resolve_pid_and_work(project_name, episode_no)
        safe_proj = pid.replace(" ", "_")

        video_info = {"exists": False}
        v_file = getattr(work, "video_file", "") if work else ""
        if v_file and "노래" in v_file:
            v_name = Path(v_file).name
            v_bytes = r2_storage.get_media_bytes(f"/projects/{pid}/videos/{v_name}") or r2_storage.get_media_bytes(v_file)
            size_mb = round(len(v_bytes) / (1024 * 1024), 2) if v_bytes else 0.0
            video_info = {
                "exists": True,
                "filename": v_name,
                "size_mb": size_mb,
                "url": f"/api/poem_video/stream/{safe_proj}/{v_name}",
                "has_preview": bool(getattr(work, "video_preview", ""))
            }

        detected_audio = None
        if work and getattr(work, "music_file", ""):
            detected_audio = Path(work.music_file).name

        img_exists = bool(work and getattr(work, "image_file", ""))
        initial_lyrics = ""
        if work:
            initial_lyrics = (getattr(work, "lyrics", "") or "").strip() or (getattr(work, "poem_body", "") or "").strip()

        return {
            "success": True,
            "episode_no": ep_num,
            "video": video_info,
            "detected_audio": detected_audio,
            "lyrics": initial_lyrics,
            "sources": {
                "has_audio": detected_audio is not None,
                "audio_name": detected_audio or "노래 음원 없음",
                "image": img_exists
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/api/song_video/render")
async def render_song_video_endpoint(req: SongVideoRenderRequest):
    """서정 노래 영상 비디오 엔진 호출 (R2 에셋 -> /tmp 스테이징 -> Remotion 렌더링 -> R2 & Turso DB 저장)"""
    try:
        from core.video_director_bridge import video_director_bridge
        pid, ep_num, ep_str, mgr, work = _resolve_pid_and_work(req.project_name, req.episode_no)
        title = work.title if (work and work.title) else f"제{ep_num}화"

        raw_lyrics = req.lyrics_text.strip()
        if not raw_lyrics:
            raise ValueError(f"제{ep_num}화의 노래 가사가 비어 있습니다.")

        lyrics_lines = []
        meta_line_pattern = re.compile(
            r'^\s*\[.*?\]\s*$|^\s*\((?:intro|verse|chorus|outro|bridge|hook|solo|guitar|piano|instrumental|간주|후렴|전주|후주).*?\)\s*$',
            re.IGNORECASE
        )
        for line in raw_lyrics.splitlines():
            l_str = line.strip()
            if not l_str or meta_line_pattern.match(l_str):
                continue
            clean_l = re.sub(r'\[.*?\]', '', l_str)
            clean_l = re.sub(r'\((?:intro|verse|chorus|outro|bridge|hook|solo|guitar|piano|instrumental|간주|후렴|전주|후주).*?\)', '', clean_l, flags=re.IGNORECASE).strip()
            if clean_l:
                lyrics_lines.append(clean_l)

        if not lyrics_lines:
            raise ValueError("가사 본문 줄이 존재하지 않습니다. ([Intro] 등 설명어 외에 실제 가사를 입력해 주세요)")

        if work:
            work.lyrics = raw_lyrics
            mgr.save_work(work)

        img_path, audio_path = _stage_work_media_to_tmp(pid, ep_str, work, req.custom_audio_path, prefer_song=True)

        res = video_director_bridge.render_song_video(
            project_name=pid,
            episode_num=ep_num,
            title=title,
            lyrics_lines=lyrics_lines,
            image_path=img_path,
            audio_path=audio_path,
            custom_srt_path=req.custom_srt_path,
            aspect_ratio=req.aspect_ratio,
            spectrum_style=req.spectrum_style,
            lyric_mode=req.lyric_mode,
            is_async=True
        )

        return {
            "success": True,
            "task_id": res.get("task_id"),
            "title": title,
            "audio_used": os.path.basename(audio_path)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
