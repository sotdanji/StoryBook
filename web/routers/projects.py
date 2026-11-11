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

from fastapi import APIRouter, Request, Response, HTTPException, UploadFile, File, Form, Body
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


# 동적 이미지 서빙 (100% Cloudflare R2 클라우드 오브젝트 스토리지)
@router.get("/images/{image_path:path}")
async def serve_image(image_path: str):
    from fastapi.responses import Response
    from core.r2_storage import r2_storage
    r2_storage.reload_config()
    pid = project_manager.get_active_project_id()
    img_name = Path(image_path.replace("\\", "/")).name

    if r2_storage.public_url:
        rel_key = f"{pid}/images/{img_name}"
        return RedirectResponse(url=f"{r2_storage.public_url}/{urllib.parse.quote(rel_key, safe='/~')}", status_code=307)

    raw_bytes = r2_storage.get_media_bytes(f"/projects/{pid}/images/{img_name}")
    if raw_bytes:
        ext = Path(img_name).suffix.lower()
        mime = "image/png" if ext == ".png" else ("image/webp" if ext == ".webp" else "image/jpeg")
        return Response(content=raw_bytes, media_type=mime)

    raise HTTPException(status_code=404, detail="이미지를 찾을 수 없습니다.")

# 동적 오디오 음원 서빙 (100% Cloudflare R2 클라우드 오브젝트 스토리지)
@router.get("/music/{audio_path:path}")
async def serve_audio(audio_path: str):
    from fastapi.responses import Response
    from core.r2_storage import r2_storage
    r2_storage.reload_config()
    pid = project_manager.get_active_project_id()
    audio_name = Path(audio_path.replace("\\", "/")).name

    if r2_storage.public_url:
        rel_key = f"{pid}/music/{audio_name}"
        return RedirectResponse(url=f"{r2_storage.public_url}/{urllib.parse.quote(rel_key, safe='/~')}", status_code=307)

    raw_bytes = r2_storage.get_media_bytes(f"/projects/{pid}/music/{audio_name}")
    if raw_bytes:
        ext = Path(audio_name).suffix.lower()
        mime = "audio/wav" if ext == ".wav" else ("audio/webm" if ext == ".webm" else "audio/mpeg")
        return Response(content=raw_bytes, media_type=mime)

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
async def select_project(req: ProjectSelectRequest, response: Response):
    try:
        project_manager.set_active_project_id(req.project_id)
        info = project_manager.get_active_project_info()
        import urllib.parse
        response.set_cookie(
            key="sb_active_project",
            value=urllib.parse.quote(info.id),
            max_age=30 * 24 * 3600,
            httponly=False,
            samesite="lax",
            path="/"
        )
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


@router.post("/api/projects/import_zip")
async def import_project_zip_endpoint(zip_file: UploadFile = File(...)):
    """
    [내 시집 전체백업.zip 업로드 복원 API]
    사용자가 PC에 내려받았던 `{시집명}_전체백업.zip` 사본을 다시 서버(Turso DB + Cloudflare R2)로 일괄 복원합니다.
    """
    if not zip_file.filename or not zip_file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="유효한 .zip 백업 파일을 선택해주세요.")
    try:
        zip_bytes = await zip_file.read()
        current_user = auth_manager.get_current_user()
        owner_id = current_user.get("user_id", "") if current_user else ""
        owner_email = current_user.get("email", "") if current_user else ""

        restored_info = await asyncio.to_thread(
            project_manager.import_project_zip,
            zip_bytes,
            owner_id,
            owner_email
        )
        return {
            "success": True,
            "project": asdict(restored_info),
            "message": f"「{restored_info.name}」 시집이 클라우드 서버(Turso DB + R2)로 완벽히 복원되었습니다!"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"백업 ZIP 복원 실패: {str(e)}")


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

        safe_name = info.id or info.name.replace(" ", "_")
        episodes = []
        for w in works:
            img_file = (w.image_file or "").replace("./", "").lstrip("/")
            if img_file.startswith("http://") or img_file.startswith("https://") or img_file.startswith("/projects/"):
                img_path = img_file
            elif img_file.startswith("images/") or img_file.startswith("media/"):
                img_path = f"/projects/{safe_name}/{img_file}"
            elif img_file:
                img_path = f"/projects/{safe_name}/images/{img_file}"
            else:
                img_path = ""

            recite_f = getattr(w, "recite_file", "") or ""
            music_f = getattr(w, "music_file", "") or ""
            if not recite_f and not music_f:
                old_a = getattr(w, "audio_file", "") or ""
                if "낭송" in old_a or old_a.endswith(".webm"):
                    recite_f = old_a
                else:
                    music_f = old_a

            def _clean_audio_url(f_path):
                if not f_path:
                    return ""
                if f_path.startswith("http://") or f_path.startswith("https://") or f_path.startswith("/projects/"):
                    return f_path
                f_clean = f_path.replace("./", "").lstrip("/")
                return f"/projects/{safe_name}/{f_clean}"

            # 1) 육성 시 낭송 (100% Turso DB 메타데이터)
            voice_f = getattr(w, "voice_user_file", "") or ""
            if not voice_f and recite_f and ("육성" in recite_f or recite_f.endswith(".webm")):
                voice_f = recite_f

            # 2) AI 시 낭송 (100% Turso DB 메타데이터)
            ai_recite_f = getattr(w, "voice_tts_file", "") or ""
            if not ai_recite_f and recite_f and "육성" not in recite_f and "음악" not in recite_f:
                ai_recite_f = recite_f

            # 3) 음악 시 낭송 (100% Turso DB 메타데이터)
            music_recite_f = getattr(w, "voice_suno_file", "") or getattr(w, "voice_bgm_file", "") or ""
            if not music_recite_f and recite_f and "음악" in recite_f:
                music_recite_f = recite_f

            # 4) 노래 듣기 (100% Turso DB 메타데이터)
            song_f = music_f or ""

            recite_f = voice_f or ai_recite_f or music_recite_f
            music_f = song_f

            recite_path = _clean_audio_url(recite_f)
            music_path = _clean_audio_url(music_f)
            voice_path = _clean_audio_url(voice_f)
            ai_recite_path = _clean_audio_url(ai_recite_f)
            music_recite_path = _clean_audio_url(music_recite_f)
            song_path = _clean_audio_url(song_f)

            # 🎬 비디오 파일 감지 (100% Turso DB 메타데이터)
            poem_video_path = getattr(w, "video_file", "") or ""
            if poem_video_path and not (poem_video_path.startswith("http") or poem_video_path.startswith("/")):
                poem_video_path = f"/projects/{safe_name}/{poem_video_path.lstrip('./')}"
            song_video_path = poem_video_path if "노래" in poem_video_path else ""

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
        return {"success": True, "data": struct}
    except Exception as e:
        logger.error(f"Failed to update book section: {e}")
        return {"success": False, "error": str(e)}


@router.post("/api/book/structure/toggle_optional_section")
async def toggle_optional_section_api(payload: Dict[str, Any] = Body(...), project_id: Optional[str] = None):
    """
    옵션 부속지(추천사, 작품 해설 등)를 원클릭으로 활성화/비활성화하고 최신 책 구조를 반환합니다.
    """
    try:
        section_type = payload.get("section_type")  # "recommendation" or "commentary"
        enabled = bool(payload.get("enabled", False))
        if section_type not in ("recommendation", "commentary"):
            return {"success": False, "error": "Invalid section_type"}

        struct = project_manager.update_section_content(
            section_type,
            {"enabled": enabled, **payload.get("data", {})},
            project_id
        )
        return {"success": True, "data": struct}
    except Exception as e:
        logger.error(f"Failed to toggle optional section: {e}")
        return {"success": False, "error": str(e)}


# -------------------------------------------------------------
# 모둠솥 공용 서가 (Bookshelf) & 시화 갤러리 웹 서빙
# -------------------------------------------------------------
@router.get("/gallery", response_class=HTMLResponse)
async def view_gallery_portal_or_book(request: Request, project_id: Optional[str] = None, view: Optional[str] = None):
    """
    - 기본 접속(/gallery): 모둠솥 공용 서가 포털(bookshelf_portal.html) 서빙
    - 개별 시집 감상 파라미터(?view=1 또는 ?project_id=...): 3D 넘겨보기 뷰어 서빙
    """
    if view == "1" or (project_id and request.query_params.get("view")):
        from core.gallery_builder import render_project_gallery_html
        pid = project_id or request.query_params.get("project_id") or project_manager.get_active_project_id()
        html_content = render_project_gallery_html(pid, relative_paths=False)
        resp = HTMLResponse(content=html_content)
        resp.set_cookie(key="sb_active_project", value=urllib.parse.quote(pid), max_age=30*24*3600, httponly=False, samesite="lax")
        return resp

    # 공용 서가 포털
    return templates.TemplateResponse(
        request=request,
        name="bookshelf_portal.html",
        context={"request": request}
    )


@router.get("/gallery/view/{project_id}", response_class=HTMLResponse)
@router.get("/gallery/{project_id}", response_class=HTMLResponse)
async def view_gallery_book_page(request: Request, project_id: str):
    """지정된 시집 프로젝트의 3D/2-Layer 넘겨보기 뷰어"""
    from core.gallery_builder import render_project_gallery_html
    pid = project_id or project_manager.get_active_project_id()
    try:
        html_content = render_project_gallery_html(pid, relative_paths=False)
        resp = HTMLResponse(content=html_content)
        resp.set_cookie(key="sb_active_project", value=urllib.parse.quote(pid), max_age=30*24*3600, httponly=False, samesite="lax")
        return resp
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"시화 갤러리 렌더링 오류: {str(e)}")


@router.get("/author/{user_id}", response_class=HTMLResponse)
async def view_author_bookshelf_page(request: Request, user_id: str):
    """작가 개인 서재 페이지 (/author/{user_id})"""
    from core.db_manager import db_manager
    current_user = auth_manager.get_current_user()
    is_owner = bool(current_user and current_user.get("user_id") == user_id)

    profile = db_manager.get_author_profile(user_id)
    if not profile:
        user_row = db_manager.get_user_by_id(user_id)
        pen_name = (user_row.get("display_name") if user_row else None) or user_id
        profile = {"user_id": user_id, "pen_name": pen_name, "bio": ""}

    items = db_manager.get_bookshelf_items(user_id=user_id, only_published=not is_owner)
    return templates.TemplateResponse(
        request=request,
        name="author_bookshelf.html",
        context={
            "request": request,
            "author": profile,
            "items": items,
            "is_owner": is_owner
        }
    )


# -------------------------------------------------------------
# 모둠솥 서가(Bookshelf) API
# -------------------------------------------------------------
@router.get("/api/bookshelf/public")
async def get_public_bookshelf_api(keyword: Optional[str] = None, limit: int = 50, offset: int = 0):
    """공용 서가 출품작 목록 조회"""
    from core.db_manager import db_manager
    items = db_manager.get_bookshelf_items(only_published=True, keyword=keyword, limit=limit, offset=offset)
    return {"success": True, "items": items}


class AddExternalBookRequest(BaseModel):
    title: str
    author_name: str
    book_type: Optional[str] = "external_ebook"
    cover_image_url: Optional[str] = ""
    view_url: str
    excerpt: Optional[str] = ""


@router.post("/api/bookshelf/add_external")
async def add_external_book_api(req: AddExternalBookRequest):
    """작가 소장 외부 e-Book / 출판 도서 등록"""
    from core.db_manager import db_manager
    current_user = auth_manager.get_current_user()
    user_id = current_user.get("user_id") if current_user else "guest_author"

    item = db_manager.upsert_bookshelf_item({
        "user_id": user_id,
        "book_type": req.book_type or "external_ebook",
        "title": req.title.strip(),
        "author_name": req.author_name.strip(),
        "cover_image_url": req.cover_image_url.strip(),
        "view_url": req.view_url.strip(),
        "excerpt": req.excerpt.strip(),
        "is_published": 1,
        "has_recite": 0
    })
    return {"success": True, "item": item}


@router.post("/api/bookshelf/publish_current")
async def publish_current_project_api(project_id: Optional[str] = None):
    """현재 스튜디오의 시화집을 모둠솥 공용 서가에 1-클릭 출품 (수정 시 자동 갱신)"""
    from core.db_manager import db_manager
    current_user = auth_manager.get_current_user()
    user_id = current_user.get("user_id") if current_user else "author_user"

    pid = project_id or project_manager.get_active_project_id()
    info = project_manager.get_project_info(pid)
    mgr = project_manager.get_manuscript_manager(pid)
    works = mgr.load_works()

    has_recite = any(
        bool(getattr(w, "voice_user_file", "") or getattr(w, "voice_tts_file", "") or getattr(w, "recite_file", ""))
        for w in works
    )

    cover_url = getattr(info, "cover_image", "")
    if not cover_url and works and works[0].image_file:
        cover_url = works[0].image_file

    if cover_url and not cover_url.startswith("http") and not cover_url.startswith("/"):
        safe_name = info.name.replace(" ", "_")
        cover_url = f"/projects/{safe_name}/{cover_url.lstrip('./')}"

    excerpt = ""
    if works and works[0].poem_body:
        lines = [l.strip() for l in works[0].poem_body.splitlines() if l.strip()]
        excerpt = " / ".join(lines[:2])
    elif getattr(info, "prologue", ""):
        excerpt = info.prologue[:100]

    author_name = info.author or (current_user.get("display_name") if current_user else "시인")

    item = db_manager.upsert_bookshelf_item({
        "user_id": user_id,
        "book_type": "internal_storybook",
        "title": info.name,
        "author_name": author_name,
        "cover_image_url": cover_url,
        "excerpt": excerpt,
        "view_url": f"/gallery/view/{pid}",
        "project_id": pid,
        "is_published": 1,
        "has_recite": 1 if has_recite else 0
    })

    db_manager.upsert_author_profile(user_id, pen_name=author_name)

    return {"success": True, "item": item}


class ToggleVisibilityRequest(BaseModel):
    item_id: str


@router.post("/api/bookshelf/toggle_visibility")
async def toggle_bookshelf_visibility_api(req: ToggleVisibilityRequest):
    """출품 도서 공개/비공개 전환"""
    from core.db_manager import db_manager
    current_user = auth_manager.get_current_user()
    user_id = current_user.get("user_id") if current_user else "author_user"

    new_val = db_manager.toggle_bookshelf_visibility(req.item_id, user_id)
    if new_val is None:
        raise HTTPException(status_code=403, detail="권한이 없거나 존재하지 않는 도서입니다.")
    return {"success": True, "is_published": new_val}


@router.delete("/api/bookshelf/item/{item_id}")
async def delete_bookshelf_item_api(item_id: str):
    """서가에서 도서 삭제"""
    from core.db_manager import db_manager
    current_user = auth_manager.get_current_user()
    user_id = current_user.get("user_id") if current_user else "author_user"

    success = db_manager.delete_bookshelf_item(item_id, user_id)
    return {"success": success}


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
