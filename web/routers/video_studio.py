"""시낭송 영상(Poem Video) 및 노래 뮤직비디오(Song Video) 렌더링·스트리밍 라우터"""

import os
import re
import shutil
import random
import urllib.request
import urllib.parse
import asyncio
import time
import base64
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Request, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

try:
    from google import genai
except ImportError:
    genai = None

from core.config import GEMINI_API_KEY
from core.project_manager import project_manager
from core.csv_builder import build_canva_csv
from core.colab_builder import build_yue2_notebook_dict, DEFAULT_GENRE_PROMPT
from core.audio_processor import clean_and_optimize_audio, trim_audio_manually, parse_time_to_seconds

WEB_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = WEB_DIR / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter()


# =========================================================================
# =========================================================================
# [StoryBook Studio] 시화 낭송 영상 (Poem Video) 제작 연동 API 엔드포인트
# =========================================================================

class PoemVideoRenderRequest(BaseModel):
    project_name: Optional[str] = None
    episode_no: Any = 1
    audio_type: str = "tts"  # "tts", "recording", "suno"
    custom_audio_path: Optional[str] = None
    aspect_ratio: str = "16:9"  # "16:9" | "9:16"
    spectrum_style: str = "bar"  # "bar" | "mirror" | "wave" | "off"


@router.get("/api/poem_video/status/{project_name}/{episode_no}")
async def get_poem_video_status_endpoint(project_name: str, episode_no: str):
    """특정 회차의 영상 제작 상태 및 오디오/삽화 리소스 상태 조회"""
    try:
        from core.project_manager import project_manager
        ep_digits = re.sub(r'[^0-9]', '', str(episode_no))
        ep_num = int(ep_digits) if ep_digits else 1
        ep_str = f"{ep_num:02d}"

        project_dir = project_manager.get_project_dir(project_name)
        if not project_dir.exists():
            project_dir = project_manager.get_project_dir()
            project_name = project_dir.name
        videos_dir = project_dir / "videos"
        music_dir = project_dir / "music"
        images_dir = project_dir / "images"

        video_info = {"exists": False}
        if videos_dir.exists():
            matched_videos = list(videos_dir.glob(f"{ep_str}_*.mp4"))
            if matched_videos:
                latest_v = max(matched_videos, key=os.path.getmtime)
                size_mb = round(os.path.getsize(latest_v) / (1024 * 1024), 2)
                preview_f = latest_v.with_name(latest_v.stem + "_preview.png")
                video_info = {
                    "exists": True,
                    "filename": latest_v.name,
                    "size_mb": size_mb,
                    "url": f"/api/poem_video/stream/{project_name}/{latest_v.name}",
                    "has_preview": preview_f.exists()
                }

        # 3대 낭송 음원 상세 탐색 (최대 3개: 1. 육성 시 낭송, 2. AI 시 낭송, 3. 음악 시 낭송)
        safe_proj = project_name.replace(" ", "_")
        recite_tracks = []

        # 1) 육성 시 낭송
        voice_track = None
        for ext in ["wav", "mp3", "webm", "m4a"]:
            cand = music_dir / f"{ep_str}_육성.{ext}"
            if cand.exists():
                voice_track = {
                    "type": "voice",
                    "label": "육성 시 낭송",
                    "icon": "🎙️",
                    "filename": cand.name,
                    "rel_path": f"music/{cand.name}",
                    "url": f"/projects/{safe_proj}/music/{cand.name}",
                    "exists": True
                }
                break
        if voice_track:
            recite_tracks.append(voice_track)

        # 2) AI 시 낭송
        ai_track = None
        for ext in ["wav", "mp3", "m4a"]:
            for tag in ["낭송", "AI낭송"]:
                cand = music_dir / f"{ep_str}_{tag}.{ext}"
                if cand.exists():
                    ai_track = {
                        "type": "ai_recite",
                        "label": "AI 시 낭송",
                        "icon": "🤖",
                        "filename": cand.name,
                        "rel_path": f"music/{cand.name}",
                        "url": f"/projects/{safe_proj}/music/{cand.name}",
                        "exists": True
                    }
                    break
            if ai_track:
                break
        if ai_track:
            recite_tracks.append(ai_track)

        # 3) 음악 시 낭송
        music_recite_track = None
        for ext in ["mp3", "m4a", "wav"]:
            for tag in ["음악낭송", "음악시낭송"]:
                cand = music_dir / f"{ep_str}_{tag}.{ext}"
                if cand.exists():
                    music_recite_track = {
                        "type": "music_recite",
                        "label": "음악 시 낭송",
                        "icon": "🎻",
                        "filename": cand.name,
                        "rel_path": f"music/{cand.name}",
                        "url": f"/projects/{safe_proj}/music/{cand.name}",
                        "exists": True
                    }
                    break
            if music_recite_track:
                break
        if music_recite_track:
            recite_tracks.append(music_recite_track)

        # 기본 선택된 음원
        detected_audio = recite_tracks[0]["filename"] if recite_tracks else None
        detected_path = recite_tracks[0]["rel_path"] if recite_tracks else None

        img_exists = any((images_dir / f"{ep_str}_삽화.{ext}").exists() for ext in ["jpg", "jpeg", "png"]) or any(len(list(images_dir.glob(f"{ep_str}_*.{ext}"))) > 0 for ext in ["jpg", "jpeg", "png"])

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


@router.post("/api/poem_video/render")
async def render_poem_video_endpoint(req: PoemVideoRenderRequest):
    """시화 영상 비디오 엔진 호출 (비동기 백그라운드)"""
    try:
        from core.video_director_bridge import video_director_bridge
        from core.project_manager import project_manager

        project_name = req.project_name
        if not project_name:
            info = project_manager.get_active_project_info()
            project_name = info.name if info else "노을빛_기억"

        ep_digits = re.sub(r'[^0-9]', '', str(req.episode_no))
        ep_num = int(ep_digits) if ep_digits else 1
        ep_str = f"{ep_num:02d}"

        project_dir = project_manager.get_project_dir(project_name)
        images_dir = project_dir / "images"
        music_dir = project_dir / "music"

        mgr = project_manager.get_manuscript_manager(project_name)
        work = mgr.get_work_by_episode(str(ep_num))
        if not work:
            work = mgr.get_work_by_episode(f"제{ep_str}화")

        title = work.title if (work and work.title) else f"제{ep_num}화"
        poem_body = (work.poem_body or "") if work else ""
        poem_lines = [line.strip() for line in poem_body.splitlines() if line.strip()]

        if not poem_lines:
            raise ValueError(f"제{ep_num}화의 시 본문 원고가 없습니다.")

        # 1. 삽화 이미지 찾기
        img_path = None
        if work and getattr(work, 'image_file', '') and (project_dir / work.image_file).exists():
            img_path = str(project_dir / work.image_file)
        else:
            for ext in ["jpg", "jpeg", "png"]:
                cand = images_dir / f"{ep_str}_삽화.{ext}"
                if cand.exists():
                    img_path = str(cand)
                    break
            if not img_path:
                for cand in sorted(images_dir.glob(f"{ep_str}_*")):
                    if cand.suffix.lower() in [".jpg", ".jpeg", ".png"] and not cand.name.endswith("_preview.png"):
                        img_path = str(cand)
                        break

        if not img_path:
            raise FileNotFoundError(f"제{ep_num}화의 삽화 이미지가 없습니다. (images/{ep_str}_*.jpg)")

        # 2. 낭송 음원 탐색 (선택된 트랙 또는 자동 탐색)
        audio_path = None
        if req.custom_audio_path:
            clean_c = req.custom_audio_path.replace("./", "").lstrip("/")
            if (project_dir / clean_c).exists():
                audio_path = str(project_dir / clean_c)
            elif os.path.exists(req.custom_audio_path):
                audio_path = req.custom_audio_path
            elif (music_dir / Path(clean_c).name).exists():
                audio_path = str(music_dir / Path(clean_c).name)

        if not audio_path and work and getattr(work, "recite_file", "") and (project_dir / work.recite_file).exists():
            audio_path = str(project_dir / work.recite_file)

        if not audio_path:
            for ext in ["wav", "mp3", "m4a", "webm"]:
                cand = music_dir / f"{ep_str}_낭송.{ext}"
                if cand.exists():
                    audio_path = str(cand)
                    break
        if not audio_path:
            for ext in ["wav", "mp3", "m4a", "webm"]:
                cand = music_dir / f"{ep_str}_육성.{ext}"
                if cand.exists():
                    audio_path = str(cand)
                    break
        if not audio_path and work and getattr(work, "music_file", "") and (project_dir / work.music_file).exists():
            audio_path = str(project_dir / work.music_file)
        if not audio_path:
            for cand in sorted(music_dir.glob(f"{ep_str}_*")):
                if cand.suffix.lower() in [".mp3", ".wav", ".m4a", ".webm"] and not cand.name.endswith("_backup.mp3"):
                    audio_path = str(cand)
                    break

        if not audio_path:
            raise FileNotFoundError(f"제{ep_num}화의 음원 파일이 없습니다. (TTS 낭송 또는 Suno 음원을 확인해 주세요)")

        res = video_director_bridge.render_poem_video(
            project_name=project_name,
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
    [앱 표준 파일 탐색기 연동] 사용자가 직접 녹음 파일/Suno 파일 업로드
    해당 회차의 공식 음원(projects/{project}/music/{ep:02d}_음원{ext})으로 자동 등록
    """
    try:
        from core.project_manager import project_manager
        ep_digits = re.sub(r'[^0-9]', '', str(episode_no))
        ep_num = int(ep_digits) if ep_digits else 1
        ep_str = f"{ep_num:02d}"

        project_dir = project_manager.get_project_dir(project_name)
        music_dir = project_dir / "music"
        music_dir.mkdir(parents=True, exist_ok=True)

        ext = Path(audio_file.filename).suffix.lower()
        if ext not in [".mp3", ".wav", ".m4a", ".ogg", ".webm"]:
            ext = ".mp3"

        target_path = music_dir / f"{ep_str}_음원{ext}"

        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(audio_file.file, buffer)

        return {
            "success": True,
            "filename": target_path.name,
            "path": str(target_path),
            "size_bytes": os.path.getsize(target_path)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/api/poem_video/open_music_folder")
async def open_music_folder_endpoint(project_name: str = Form(...)):
    """[앱 표준] 프로젝트의 음악 폴더를 윈도우 탐색기로 열기"""
    try:
        from core.project_manager import project_manager
        project_dir = project_manager.get_project_dir(project_name)
        music_dir = project_dir / "music"
        music_dir.mkdir(parents=True, exist_ok=True)

        if os.name == 'nt':
            subprocess.Popen(["explorer", str(music_dir.resolve())])
            return {"success": True, "message": "음악 폴더를 열었습니다."}
        else:
            return {"success": False, "error": "윈도우 탐색기 전용 기능입니다."}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/api/poem_video/stream/{project_name}/{filename}")
async def stream_poem_video_endpoint(project_name: str, filename: str):
    """완성된 MP4 영상을 브라우저로 스트리밍"""
    from core.project_manager import project_manager
    project_dir = project_manager.get_project_dir(project_name)
    video_path = project_dir / "videos" / filename
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="비디오 파일을 찾을 수 없습니다.")
    return FileResponse(
        path=str(video_path),
        media_type="video/mp4",
        filename=filename
    )


class MergePlaylistRequest(BaseModel):
    project_name: Optional[str] = None
    aspect_ratio: str = "16:9"


@router.post("/api/poem_video/merge_playlist")
async def merge_poem_video_playlist_endpoint(req: MergePlaylistRequest):
    """프로젝트 내 완성된 영상들을 하나의 전편 플레이리스트 영상으로 초고속 무손실 결합"""
    try:
        from core.video_director_bridge import video_director_bridge
        from core.project_manager import project_manager

        project_name = req.project_name
        if not project_name:
            info = project_manager.get_active_project_info()
            project_name = info.name if info else "노을빛_기억"

        res = video_director_bridge.merge_playlist_video(
            project_name=project_name,
            aspect_ratio=req.aspect_ratio
        )
        return res
    except Exception as e:
        return {"success": False, "error": str(e)}


# =========================================================================
# [StoryBook Studio] 서정 노래 영상 (Song Video) 제작 연동 API 엔드포인트
# =========================================================================

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
    """특정 회차의 노래 영상 제작 상태, 음원 및 가사 리소스 상태 조회"""
    try:
        from core.project_manager import project_manager
        ep_digits = re.sub(r'[^0-9]', '', str(episode_no))
        ep_num = int(ep_digits) if ep_digits else 1
        ep_str = f"{ep_num:02d}"

        project_dir = project_manager.get_project_dir(project_name)
        if not project_dir.exists():
            project_dir = project_manager.get_project_dir()
            project_name = project_dir.name
        videos_dir = project_dir / "videos"
        music_dir = project_dir / "music"
        images_dir = project_dir / "images"

        video_info = {"exists": False}
        if videos_dir.exists():
            matched_videos = list(videos_dir.glob(f"{ep_str}_*노래*.mp4"))
            if matched_videos:
                latest_v = max(matched_videos, key=os.path.getmtime)
                size_mb = round(os.path.getsize(latest_v) / (1024 * 1024), 2)
                preview_f = latest_v.with_name(latest_v.stem + "_preview.png")
                video_info = {
                    "exists": True,
                    "filename": latest_v.name,
                    "size_mb": size_mb,
                    "url": f"/api/poem_video/stream/{project_name}/{latest_v.name}",
                    "has_preview": preview_f.exists()
                }

        # 1. 해당 회차 노래 음원 자동 감지
        mgr = project_manager.get_manuscript_manager(project_name)
        work = mgr.get_work_by_episode(str(ep_num))
        if not work:
            work = mgr.get_work_by_episode(f"제{ep_str}화")

        detected_audio = None
        if work and getattr(work, "music_file", "") and (project_dir / work.music_file).exists():
            detected_audio = Path(work.music_file).name
        if not detected_audio:
            for ext in ["mp3", "wav", "m4a", "webm"]:
                cand = music_dir / f"{ep_str}_노래.{ext}"
                if cand.exists():
                    detected_audio = cand.name
                    break
        if not detected_audio:
            for ext in ["mp3", "wav", "m4a", "webm"]:
                cand = music_dir / f"{ep_str}_음악.{ext}"
                if cand.exists():
                    detected_audio = cand.name
                    break
        if not detected_audio:
            # Suno 관련 파일 또는 번호로 시작하는 일반 음악 파일
            for cand in sorted(music_dir.glob(f"{ep_str}_*")):
                if cand.suffix.lower() in [".mp3", ".wav", ".m4a", ".webm"] and not cand.name.endswith("_backup.mp3") and "낭송" not in cand.name and "육성" not in cand.name:
                    detected_audio = cand.name
                    break

        img_exists = any((images_dir / f"{ep_str}_삽화.{ext}").exists() for ext in ["jpg", "jpeg", "png"]) or any(len(list(images_dir.glob(f"{ep_str}_*.{ext}"))) > 0 for ext in ["jpg", "jpeg", "png"])

        # 2. 기본 가사 초안 (작사 노랫말 -> 없으면 시 원문)
        initial_lyrics = ""
        if work:
            initial_lyrics = (getattr(work, "lyrics", "") or "").strip()
            if not initial_lyrics:
                initial_lyrics = (getattr(work, "poem_body", "") or "").strip()

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
    """서정 노래 영상 비디오 엔진 호출 (비동기 백그라운드)"""
    try:
        from core.video_director_bridge import video_director_bridge
        from core.project_manager import project_manager

        project_name = req.project_name
        if not project_name:
            info = project_manager.get_active_project_info()
            project_name = info.name if info else "노을빛_기억"

        ep_digits = re.sub(r'[^0-9]', '', str(req.episode_no))
        ep_num = int(ep_digits) if ep_digits else 1
        ep_str = f"{ep_num:02d}"

        project_dir = project_manager.get_project_dir(project_name)
        images_dir = project_dir / "images"
        music_dir = project_dir / "music"

        mgr = project_manager.get_manuscript_manager(project_name)
        work = mgr.get_work_by_episode(str(ep_num))
        if not work:
            work = mgr.get_work_by_episode(f"제{ep_str}화")

        title = work.title if (work and work.title) else f"제{ep_num}화"

        # 1. 가사 줄(line) 정제
        raw_lyrics = req.lyrics_text.strip()
        if not raw_lyrics:
            raise ValueError(f"제{ep_num}화의 노래 가사가 비어 있습니다.")

        # [Verse], [Chorus], (Guitar Solo) 등 메타태그 및 음악 지시어 스마트 정제
        lyrics_lines = []
        meta_line_pattern = re.compile(
            r'^\s*\[.*?\]\s*$|^\s*\((?:intro|verse|chorus|outro|bridge|hook|solo|guitar|piano|instrumental|간주|후렴|전주|후주).*?\)\s*$',
            re.IGNORECASE
        )
        for line in raw_lyrics.splitlines():
            l_str = line.strip()
            if not l_str or meta_line_pattern.match(l_str):
                continue
            # 라인 내부에 섞인 [Chorus] 등 대괄호 및 소괄호 지시어 제거
            clean_l = re.sub(r'\[.*?\]', '', l_str)
            clean_l = re.sub(r'\((?:intro|verse|chorus|outro|bridge|hook|solo|guitar|piano|instrumental|간주|후렴|전주|후주).*?\)', '', clean_l, flags=re.IGNORECASE).strip()
            if clean_l:
                lyrics_lines.append(clean_l)

        if not lyrics_lines:
            raise ValueError("가사 본문 줄이 존재하지 않습니다. ([Intro] 등 설명어 외에 실제 가사를 입력해 주세요)")

        # 노랫말 최신 상태 ManuscriptManager에 영구 동기화
        if work:
            work.lyrics = raw_lyrics
            mgr.save_work(work)

        # 2. 삽화 이미지 찾기
        img_path = None
        if work and getattr(work, 'image_file', '') and (project_dir / work.image_file).exists():
            img_path = str(project_dir / work.image_file)
        else:
            for ext in ["jpg", "jpeg", "png"]:
                cand = images_dir / f"{ep_str}_삽화.{ext}"
                if cand.exists():
                    img_path = str(cand)
                    break
            if not img_path:
                for cand in sorted(images_dir.glob(f"{ep_str}_*")):
                    if cand.suffix.lower() in [".jpg", ".jpeg", ".png"] and not cand.name.endswith("_preview.png"):
                        img_path = str(cand)
                        break

        if not img_path:
            raise FileNotFoundError(f"제{ep_num}화의 삽화 이미지가 없습니다.")

        # 3. 노래 음원 찾기
        audio_path = None
        if req.custom_audio_path and os.path.exists(req.custom_audio_path):
            audio_path = req.custom_audio_path
        elif work and getattr(work, "music_file", "") and (project_dir / work.music_file).exists():
            audio_path = str(project_dir / work.music_file)

        if not audio_path:
            for ext in ["mp3", "wav", "m4a", "webm"]:
                cand = music_dir / f"{ep_str}_노래.{ext}"
                if cand.exists():
                    audio_path = str(cand)
                    break
        if not audio_path:
            for ext in ["mp3", "wav", "m4a", "webm"]:
                cand = music_dir / f"{ep_str}_음악.{ext}"
                if cand.exists():
                    audio_path = str(cand)
                    break
        if not audio_path:
            for cand in sorted(music_dir.glob(f"{ep_str}_*")):
                if cand.suffix.lower() in [".mp3", ".wav", ".m4a", ".webm"] and not cand.name.endswith("_backup.mp3") and "낭송" not in cand.name and "육성" not in cand.name:
                    audio_path = str(cand)
                    break

        if not audio_path:
            raise FileNotFoundError(f"제{ep_num}화의 노래 음원 파일이 없습니다. (Suno 생성 음원 또는 작곡 음원을 등록해 주세요)")

        res = video_director_bridge.render_song_video(
            project_name=project_name,
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
