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
from fastapi import APIRouter, Request, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

try:
    from google import genai
except ImportError:
    genai = None

from core.config import (
    BASE_DIR, IMAGES_DIR, TARGET_POEMS_COUNT, GEMINI_API_KEY, GEMINI_MODEL, DEFAULT_ART_STYLE, CANVA_CSV_FILE, PAPER_TYPE,
    save_gemini_api_key, save_gemini_model, get_gemini_api_key_status, get_supabase_config
)
from core.auth_manager import auth_manager
from core.manuscript import ManuscriptManager, PoemWork
from core.project_manager import project_manager, ProjectInfo
from core.csv_builder import build_canva_csv, build_canva_publishing_metadata_csv
from core.publishing_copier import publishing_copier
from core.book_spec import calculate_spine_and_cover, inspect_images
from core.pdf_builder import build_pdf_book
from core.bookk_pdf_builder import BookkPDFBuilder, BOOKK_FORMATS
from core.image_optimizer import ensure_300dpi_image
from core.poetic_engine import poetic_engine
from core.colab_builder import build_yue2_notebook_dict, DEFAULT_GENRE_PROMPT
from core.colab_image_builder import build_sdxl_image_notebook_dict, DEFAULT_STYLE_PRESETS
from core.poetic_thesaurus import lookup_poetic_words, get_all_categories_summary, suggest_poetic_synonyms_ai, POETIC_THESAURUS_DB
from core.audio_processor import clean_and_optimize_audio, trim_audio_manually, parse_time_to_seconds, get_audio_duration, format_seconds

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


# 동적 이미지 서빙 (활성 프로젝트 폴더 내 images 서빙)
@router.get("/images/{image_path:path}")
async def serve_image(image_path: str):
    clean_path = image_path.replace("..", "").lstrip("/\\")
    img_name = Path(clean_path).name

    # 1. 활성 프로젝트의 images 디렉토리
    p_img = project_manager.get_active_images_dir() / img_name
    if p_img.exists() and p_img.is_file():
        return FileResponse(str(p_img))

    # 2. 프로젝트 폴더 내 상대경로
    p_direct = project_manager.get_project_dir() / clean_path
    if p_direct.exists() and p_direct.is_file():
        return FileResponse(str(p_direct))

    raise HTTPException(status_code=404, detail="이미지를 찾을 수 없습니다.")

# 동적 오디오 음원 서빙 (활성 프로젝트 및 프로젝트별 music 서빙)
@router.get("/music/{audio_path:path}")
async def serve_audio(audio_path: str):
    clean_path = audio_path.replace("..", "").lstrip("/\\")
    audio_name = Path(clean_path).name

    # 1. 활성 프로젝트의 music 디렉토리
    p_music = project_manager.get_project_dir() / "music" / audio_name
    if p_music.exists() and p_music.is_file():
        return FileResponse(str(p_music))

    # 2. 프로젝트 폴더 내 상대경로
    p_direct = project_manager.get_project_dir() / clean_path
    if p_direct.exists() and p_direct.is_file():
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
                "memory_anchor": w.memory_anchor,
                "image_file": w.image_file,
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

            # 🎵 실제 파일 시스템의 낭송/노래 자동 탐색 (누락 방지)
            import re
            ep_digits = re.sub(r'[^0-9]', '', w.episode_no or '').zfill(2)
            proj_dir = project_manager.get_project_dir(pid)
            if not recite_f and ep_digits:
                candidate_rec = proj_dir / "music" / f"{ep_digits}_낭송.wav"
                if candidate_rec.exists():
                    recite_f = f"music/{ep_digits}_낭송.wav"
            if not music_f and ep_digits:
                candidate_mus = proj_dir / "music" / f"{ep_digits}_음원.mp3"
                if candidate_mus.exists():
                    music_f = f"music/{ep_digits}_음원.mp3"

            def _clean_audio_url(f_path):
                if not f_path:
                    return ""
                f_clean = f_path.replace("./", "").lstrip("/")
                return f"/projects/{safe_name}/{f_clean}"

            recite_path = _clean_audio_url(recite_f)
            music_path = _clean_audio_url(music_f)

            episodes.append({
                "ep": w.episode_no,
                "title": w.title,
                "image": img_path,
                "memory": w.memory_anchor,
                "body": w.poem_body,
                "hasRecite": bool(recite_f),
                "recite": recite_path,
                "hasMusic": bool(music_f),
                "music": music_path,
                "hasAudio": bool(recite_f or music_f),
                "audio": music_path or recite_path,
                "lyrics": getattr(w, "lyrics", "") or ""
            })

        projects_list = project_manager.list_projects()

        return {
            "success": True,
            "project": asdict(info),
            "projects": projects_list,
            "episodes": episodes
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
