"""시집 프로젝트 관리(생성/선택/수정/삭제/백업), 현재 상태(/api/status), 갤러리 및 정적 미디어 서빙 라우터"""

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
import logging
logger = logging.getLogger(__name__)

from fastapi import APIRouter, Request, HTTPException, UploadFile, File, Form, Body
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

try:
    from google import genai
except ImportError:
    genai = None

from core.auth_manager import auth_manager
from core.project_manager import project_manager

WEB_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = WEB_DIR / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter()


class ProjectSelectRequest(BaseModel):
    project_id: str

class ProjectCreateRequest(BaseModel):
    name: str
    subtitle: Optional[str] = ""
    author: Optional[str] = ""
    target_count: Optional[int] = 35
    description: Optional[str] = ""
    book_type: Optional[str] = "illustrated"
    author_type: Optional[str] = "single"

class ProjectUpdateRequest(BaseModel):
    project_id: Optional[str] = None
    name: str
    subtitle: Optional[str] = ""
    author: Optional[str] = ""
    target_count: Optional[int] = 35
    description: Optional[str] = ""
    book_type: Optional[str] = "illustrated"
    author_type: Optional[str] = "single"

class ProjectDeleteRequest(BaseModel):
    project_id: str


def _safe_child(base: Path, rel: str):
    """base 폴더 내부의 실제 파일일 때만 경로를 반환 (경로 탈출/절대경로 차단)"""
    try:
        rel = (rel or "").replace("\\", "/").lstrip("/")
        if not rel or ":" in rel or "\x00" in rel:
            return None
        base_r = base.resolve()
        cand = (base_r / rel).resolve()
        cand.relative_to(base_r)
        return cand if cand.is_file() else None
    except Exception:
        return None


# 동적 이미지 서빙 (활성 프로젝트 폴더 내 images 서빙)
@router.get("/images/{image_path:path}")
async def serve_image(image_path: str):
    img_name = Path(image_path.replace("\\", "/")).name

    # 1. 활성 프로젝트의 images 디렉토리
    p_img = _safe_child(project_manager.get_active_images_dir(), img_name)
    if p_img:
        return FileResponse(str(p_img))

    # 2. 프로젝트 폴더 내 상대경로
    p_direct = _safe_child(project_manager.get_project_dir(), image_path)
    if p_direct:
        return FileResponse(str(p_direct))

    raise HTTPException(status_code=404, detail="이미지를 찾을 수 없습니다.")

# 동적 오디오 음원 서빙 (활성 프로젝트 및 프로젝트별 music 서빙)
@router.get("/music/{audio_path:path}")
async def serve_audio(audio_path: str):
    audio_name = Path(audio_path.replace("\\", "/")).name

    # 1. 활성 프로젝트의 music 디렉토리
    p_music = _safe_child(project_manager.get_project_dir() / "music", audio_name)
    if p_music:
        return FileResponse(str(p_music))

    # 2. 프로젝트 폴더 내 상대경로
    p_direct = _safe_child(project_manager.get_project_dir(), audio_path)
    if p_direct:
        return FileResponse(str(p_direct))

    raise HTTPException(status_code=404, detail="음원 파일을 찾을 수 없습니다.")


# -------------------------------------------------------------
# 시집 프로젝트 관리 API (계정별 분리 및 격리)
# -------------------------------------------------------------
@router.get("/api/projects")
async def get_projects():
    """현재 로그인한 회원 전용 시집 목록 및 활성 시집 반환"""
    current_user = auth_manager.get_current_user()
    user_id = current_user.get("user_id") if current_user else None

    # 내 계정의 시집 및 아직 미할당된 시집만 안전하게 필터링
    projects = project_manager.list_projects(user_id=user_id)
    active_info = project_manager.get_active_project_info()
    return {
        "projects": projects,
        "active_project": asdict(active_info)
    }

@router.post("/api/projects/select")
async def select_project(req: ProjectSelectRequest):
    try:
        project_manager.set_active_project_id(req.project_id)
        info = project_manager.get_active_project_info()
        return {"success": True, "active_project": asdict(info)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/api/projects/create")
async def create_project(req: ProjectCreateRequest):
    name = req.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="시집 제목을 입력해주세요.")
    try:
        current_user = auth_manager.get_current_user()
        owner_id = current_user.get("user_id", "") if current_user else ""
        owner_email = current_user.get("email", "") if current_user else ""

        book_type = req.book_type if req.book_type in ("illustrated", "standard") else "illustrated"
        author_type = req.author_type if req.author_type in ("single", "collab") else "single"
        info = project_manager.create_project(
            name=name,
            subtitle=req.subtitle.strip() if req.subtitle else ("삶의 궤적을 빚어낸 서정 시화집" if book_type == "illustrated" else "서정 시집"),
            author=req.author.strip() if req.author else (current_user.get("display_name", "기억의 작가") if current_user else "기억의 작가"),
            target_count=req.target_count or 35,
            description=req.description.strip() if req.description else "",
            book_type=book_type,
            author_type=author_type,
            owner_id=owner_id,
            owner_email=owner_email
        )
        return {"success": True, "project": asdict(info)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"시집 생성 실패: {str(e)}")

@router.post("/api/projects/update")
async def update_project(req: ProjectUpdateRequest):
    name = req.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="시집 제목을 입력해주세요.")
    try:
        info = project_manager.update_project_info(
            project_id=req.project_id,
            name=name,
            subtitle=req.subtitle or "",
            author=req.author or "",
            target_count=req.target_count or 35,
            description=req.description or "",
            book_type=req.book_type,
            author_type=req.author_type
        )
        return {"success": True, "project": asdict(info)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/api/projects/delete")
async def delete_project(req: ProjectDeleteRequest):
    try:
        project_manager.delete_project(req.project_id)
        active_info = project_manager.get_active_project_info()
        return {"success": True, "active_project": asdict(active_info)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/api/projects/export_zip")
async def export_project_zip(project_id: Optional[str] = None):
    try:
        pid = project_id or project_manager.get_active_project_id()
        info = project_manager.get_project_info(pid)
        zip_path = await asyncio.to_thread(project_manager.export_project_zip, pid)
        if not zip_path.exists():
            raise HTTPException(status_code=500, detail="백업 파일 생성에 실패했습니다.")

        safe_name = urllib.parse.quote(f"{info.name}_전체백업.zip")
        return FileResponse(
            path=str(zip_path),
            filename=f"{info.name}_전체백업.zip",
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_name}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"백업 생성 실패: {str(e)}")


# -------------------------------------------------------------
# 현재 활성 프로젝트 상태 및 창작 API
# -------------------------------------------------------------
@router.get("/api/status")
async def get_status():
    mgr = project_manager.get_active_manuscript_manager()
    info = project_manager.get_active_project_info()
    works = mgr.load_works()
    completed = mgr.get_completed_count()
    next_num = mgr.get_next_episode_number()
    return {
        "project": asdict(info),
        "target_count": info.target_count,
        "completed_count": completed,
        "progress_percent": round((completed / max(1, info.target_count)) * 100, 1),
        "next_episode": f"제{str(next_num).zfill(2)}화",
        "works": [
            {
                "episode_no": w.episode_no,
                "title": w.title,
                "status": w.status,
                "chapter": getattr(w, "chapter", ""),
                "author": getattr(w, "author", ""),
                "memory_anchor": w.memory_anchor,
                "image_file": w.image_file,
                "image_file_2": getattr(w, "image_file_2", ""),
                "layout_mode": getattr(w, "layout_mode", "compact"),
                "part2_mode": getattr(w, "part2_mode", "motif_symbol"),
                "layout_config": getattr(w, "layout_config", None),
                "recite_file": getattr(w, "recite_file", ""),
                "music_file": getattr(w, "music_file", ""),
                "audio_file": getattr(w, "audio_file", "") or getattr(w, "music_file", "") or getattr(w, "recite_file", ""),
                "lyrics": getattr(w, "lyrics", ""),
                "art_direction": w.art_direction,
                "poem_body": w.poem_body
            }
            for w in works
        ]
    }

@router.get("/api/gallery_data")
async def get_gallery_data(project_id: Optional[str] = None):
    try:
        pid = project_id or project_manager.get_active_project_id()
        info = project_manager.get_project_info(pid)
        mgr = project_manager.get_manuscript_manager(pid)
        works = mgr.load_works()

        safe_name = info.name.replace(" ", "_")
        episodes = []
        for w in works:
            img_file = (w.image_file or "").replace("./", "").lstrip("/")
            if img_file.startswith("images/"):
                img_path = f"/projects/{safe_name}/{img_file}"
            elif img_file:
                img_path = f"/projects/{safe_name}/images/{img_file}"
            else:
                img_path = ""

            recite_f = getattr(w, "recite_file", "") or ""
            music_f = getattr(w, "music_file", "") or ""
            # 하위 호환 매핑
            if not recite_f and not music_f:
                old_a = getattr(w, "audio_file", "") or ""
                if "낭송" in old_a or old_a.endswith(".webm"):
                    recite_f = old_a
                else:
                    music_f = old_a

            # 🎵 실제 파일 시스템의 3대 음원 자동 탐색 (육성 / AI낭송 / 노래)
            import re
            ep_digits = re.sub(r'[^0-9]', '', w.episode_no or '').zfill(2)
            proj_dir = project_manager.get_project_dir(pid)
            music_dir = proj_dir / "music"

            def _clean_audio_url(f_path):
                if not f_path:
                    return ""
                f_clean = f_path.replace("./", "").lstrip("/")
                return f"/projects/{safe_name}/{f_clean}"

            # 1) 육성 시 낭송 (내 목소리 직접 녹음)
            voice_f = ""
            for ext in ["wav", "webm", "mp3", "m4a"]:
                cand = music_dir / f"{ep_digits}_육성.{ext}"
                if cand.exists():
                    voice_f = f"music/{cand.name}"
                    break
            if not voice_f and recite_f and ("육성" in recite_f or recite_f.endswith(".webm")):
                voice_f = recite_f

            # 2) AI 시 낭송 (AI TTS 성우)
            ai_recite_f = ""
            for ext in ["wav", "mp3", "m4a"]:
                for tag in ["낭송", "AI낭송"]:
                    cand = music_dir / f"{ep_digits}_{tag}.{ext}"
                    if cand.exists():
                        ai_recite_f = f"music/{cand.name}"
                        break
                if ai_recite_f:
                    break
            if not ai_recite_f and recite_f and "육성" not in recite_f and "음악" not in recite_f:
                ai_recite_f = recite_f

            # 3) 음악 시 낭송 (Suno 배경음악 낭송 / Spoken Word)
            music_recite_f = ""
            for ext in ["mp3", "m4a", "wav"]:
                for tag in ["음악낭송", "음악시낭송"]:
                    cand = music_dir / f"{ep_digits}_{tag}.{ext}"
                    if cand.exists():
                        music_recite_f = f"music/{cand.name}"
                        break
                if music_recite_f:
                    break
            if not music_recite_f and recite_f and "음악" in recite_f:
                music_recite_f = recite_f

            # 4) 노래 듣기 (가창 노래)
            song_f = ""
            for ext in ["mp3", "m4a", "wav"]:
                for tag in ["노래", "음원", "music"]:
                    cand = music_dir / f"{ep_digits}_{tag}.{ext}"
                    if cand.exists():
                        song_f = f"music/{cand.name}"
                        break
                if song_f:
                    break
            if not song_f and music_f:
                song_f = music_f

            # 하위 호환 매핑
            recite_f = voice_f or ai_recite_f or music_recite_f
            music_f = song_f

            recite_path = _clean_audio_url(recite_f)
            music_path = _clean_audio_url(music_f)
            voice_path = _clean_audio_url(voice_f)
            ai_recite_path = _clean_audio_url(ai_recite_f)
            music_recite_path = _clean_audio_url(music_recite_f)
            song_path = _clean_audio_url(song_f)

            # 🎬 비디오 파일(낭송 영상 및 노래 영상 각각) 감지
            poem_video_path = ""
            song_video_path = ""
            videos_dir = proj_dir / "videos"
            if videos_dir.exists() and ep_digits:
                # 노래 영상
                matched_song_v = list(videos_dir.glob(f"*{ep_digits}*music*.mp4")) or list(videos_dir.glob(f"{ep_digits}_*노래*.mp4"))
                if matched_song_v:
                    latest_song = max(matched_song_v, key=os.path.getmtime)
                    song_video_path = f"/api/poem_video/stream/{safe_name}/{latest_song.name}"
                # 낭송 영상
                matched_poem_v = list(videos_dir.glob(f"*{ep_digits}*recite*.mp4")) or list(videos_dir.glob(f"{ep_digits}_*낭송*.mp4")) or list(videos_dir.glob(f"{ep_digits}_*.mp4"))
                if matched_poem_v:
                    latest_poem = max(matched_poem_v, key=os.path.getmtime)
                    poem_video_path = f"/api/poem_video/stream/{safe_name}/{latest_poem.name}"

            has_video = bool(poem_video_path or song_video_path)
            default_video = song_video_path or poem_video_path

            episodes.append({
                "ep": w.episode_no,
                "title": w.title,
                "image": img_path,
                "memory": w.memory_anchor,
                "body": w.poem_body,
                "hasRecite": bool(recite_f),
                "recite": recite_path,
                "hasVoice": bool(voice_f),
                "voice": voice_path,
                "hasAiRecite": bool(ai_recite_f),
                "aiRecite": ai_recite_path,
                "hasMusicRecite": bool(music_recite_f),
                "musicRecite": music_recite_path,
                "hasSong": bool(song_f),
                "song": song_path,
                "hasMusic": bool(music_f),
                "music": music_path,
                "hasAudio": bool(voice_f or ai_recite_f or music_recite_f or song_f),
                "audio": music_path or recite_path,
                "lyrics": getattr(w, "lyrics", "") or "",
                "hasVideo": has_video,
                "video": default_video,
                "hasPoemVideo": bool(poem_video_path),
                "poemVideo": poem_video_path,
                "hasSongVideo": bool(song_video_path),
                "songVideo": song_video_path,
                "image2": f"/projects/{safe_name}/{getattr(w, 'image_file_2', '').replace('./', '').lstrip('/')}" if getattr(w, "image_file_2", "") else "",
                "layout_mode": getattr(w, "layout_mode", "compact") or "compact",
                "part2_mode": getattr(w, "part2_mode", "motif_symbol") or "motif_symbol",
                "layout_config": getattr(w, "layout_config", None),
                "chapter": getattr(w, "chapter", "") or "",
                "author": getattr(w, "author", "") or info.author
            })

        projects_list = project_manager.list_projects()
        book_structure = project_manager.get_book_structure(pid)

        return {
            "success": True,
            "project": asdict(info),
            "projects": projects_list,
            "episodes": episodes,
            "book_structure": book_structure
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api/book/structure")
async def get_book_structure_api(project_id: Optional[str] = None):
    """
    [Full Book Architecture]
    책 전체의 시퀀스 구조(앞표지 -> 속표지 -> 서문 -> 목차 -> 부/시화 본문 -> 맺음말 -> 판권지 -> 뒤표지)와
    각 섹션별 페이지 번호, 완성 상태(상태 머신), 세부 데이터를 단일 모델로 반환합니다.
    """
    try:
        struct = project_manager.get_book_structure(project_id)
        return {"success": True, "data": struct}
    except Exception as e:
        logger.error(f"Failed to get book structure: {e}")
        return {"success": False, "error": str(e)}


@router.post("/api/book/structure/update_section")
async def update_book_section_api(payload: Dict[str, Any] = Body(...), project_id: Optional[str] = None):
    """
    특정 섹션(서문, 에필로그, 판권, 표지 등)의 메타데이터를 실시간 수정하고
    최신 책 전체 구조를 반환합니다.
    """
    try:
        section_id = payload.get("section_id")
        if not section_id:
            return {"success": False, "error": "section_id is required"}
        data = payload.get("data", {})
        struct = project_manager.update_section_content(section_id, data, project_id)
        try:
            from core.gallery_builder import sync_project_gallery_html
            sync_project_gallery_html(project_id)
        except Exception:
            pass
        return {"success": True, "data": struct}
    except Exception as e:
        logger.error(f"Failed to update book section: {e}")
        return {"success": False, "error": str(e)}


# -------------------------------------------------------------
# 시화 갤러리 웹 서빙 & 독립 웹 배포용 패키징 API
# -------------------------------------------------------------
@router.get("/gallery", response_class=HTMLResponse)
@router.get("/gallery/{project_id}", response_class=HTMLResponse)
async def view_gallery_page(project_id: Optional[str] = None):
    """
    온라인 시화 갤러리 웹 서빙:
    - 활성 또는 지정된 시집의 최신 시화집_갤러리.html 동기화 후 반환
    """
    from core.gallery_builder import sync_project_gallery_html
    pid = project_id or project_manager.get_active_project_id()
    try:
        pdir = project_manager.get_project_dir(pid)
    except Exception:
        raise HTTPException(status_code=404, detail="존재하지 않는 시집 프로젝트입니다.")

    # 최신 원고 및 에셋 동기화
    try:
        sync_project_gallery_html(pid)
    except Exception as e:
        logger.warning(f"Gallery sync warning: {e}")

    gallery_file = pdir / "시화집_갤러리.html"
    if not gallery_file.exists():
        raise HTTPException(status_code=404, detail="시화 갤러리 파일을 찾을 수 없습니다.")

    html_content = gallery_file.read_text(encoding="utf-8")
    return HTMLResponse(content=html_content)


@router.get("/api/projects/export_gallery_zip")
async def export_gallery_zip_api(project_id: Optional[str] = None):
    """
    웹 배포용 단일 정적 갤러리 ZIP 패키지 다운로드:
    - Netlify, GitHub Pages, Vercel 등에 폴더만 올리면 열리는 index.html 패키지
    """
    import asyncio
    import urllib.parse
    pid = project_id or project_manager.get_active_project_id()
    try:
        info = project_manager.get_project_info(pid)
        zip_path = await asyncio.to_thread(project_manager.export_gallery_web_zip, pid)
        if not zip_path.exists():
            raise HTTPException(status_code=500, detail="갤러리 웹 배포용 패키지 생성에 실패했습니다.")

        safe_name = urllib.parse.quote(f"{info.name}_온라인갤러리_웹배포용.zip")
        return FileResponse(
            path=str(zip_path),
            filename=f"{info.name}_온라인갤러리_웹배포용.zip",
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_name}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"갤러리 배포 패키지 생성 실패: {str(e)}")
