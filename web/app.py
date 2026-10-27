import os
import re
import shutil
import random
import urllib.request
import urllib.parse
import asyncio
import time
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
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

app = FastAPI(title="StoryBook Studio", description="기억 기반 시화집 독립출판 웹 스튜디오")

# 디렉토리 경로
WEB_DIR = Path(__file__).resolve().parent
STATIC_DIR = WEB_DIR / "static"
TEMPLATES_DIR = WEB_DIR / "templates"

STATIC_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

# 정적 파일 마운트
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/projects", StaticFiles(directory=str(BASE_DIR / "projects")), name="projects")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Pydantic 모델
class DraftRequest(BaseModel):
    core_memory: Optional[str] = ""
    sensory_details: Optional[str] = ""
    spoken_words: Optional[str] = ""
    style_seed: Optional[int] = None
    art_style: Optional[str] = "watercolor"
    deep_interview_answer: Optional[str] = ""

class DeepInterviewRequest(BaseModel):
    core_memory: Optional[str] = ""
    sensory_details: Optional[str] = ""
    spoken_words: Optional[str] = ""

class SetApiKeyRequest(BaseModel):
    api_key: str

class RefinePoemRequest(BaseModel):
    poem_body: str
    mode: Optional[str] = "custom"  # "shorten", "subdued", "rhythm", "custom"
    instruction: Optional[str] = ""  # 사용자 자유 수정 요청문
    title: Optional[str] = ""

class ImagePromptRequest(BaseModel):
    title: str
    poem_body: str
    core_memory: Optional[str] = ""
    sensory_details: Optional[str] = ""
    style_mode: Optional[str] = "literal"
    art_style: Optional[str] = "watercolor"
    custom_guide: Optional[str] = ""

class LyricsGenerateRequest(BaseModel):
    title: str
    poem_body: str
    genre: Optional[str] = "minyo"
    custom_guide: Optional[str] = ""

class UpdateLyricsRequest(BaseModel):
    episode_no: str
    lyrics: str

class ColabNotebookRequest(BaseModel):
    episode_no: str
    title: str
    genre_prompt: Optional[str] = ""
    lyrics: Optional[str] = ""

class ColabImageNotebookRequest(BaseModel):
    episode_no: str
    title: str
    prompt: Optional[str] = ""
    art_style: Optional[str] = "watercolor"
    width: Optional[int] = 768
    height: Optional[int] = 1024

class SetModelRequest(BaseModel):
    model_name: str

class SpeakPoemRequest(BaseModel):
    title: str
    poem_body: str
    episode_no: Optional[str] = "제01화"
    voice: Optional[str] = "Aoede"  # Aoede, Charon, Kore, Puck, Fenrir 또는 Edge-TTS 성우명
    engine: Optional[str] = "auto"   # auto, gemini, edge

# 🎙️ TTS 엔진 상태 및 크레딧 만료 추적 전역 상태
TTS_STATE = {
    "engine": "gemini",            # 'gemini' | 'edge'
    "gemini_credit_expired": False, # 크레딧 만료 여부
    "last_error": None,
    "error_type": None
}

class ImportSunoRequest(BaseModel):
    url: str
    episode_no: str

class TrimAudioRequest(BaseModel):
    episode_no: str
    start_time: str = "00:00"
    end_time: str = ""

class AuthSessionRequest(BaseModel):
    user_id: str
    email: str
    access_token: str
    name: Optional[str] = None
    provider: Optional[str] = "google"

class ExternalPromptRequest(BaseModel):
    core_memory: str
    sensory_details: str
    spoken_words: Optional[str] = ""

class SaveWorkRequest(BaseModel):
    episode_no: str
    title: str
    status: str = "완성 (승인 완료)"
    memory_anchor: str
    image_file: str
    art_direction: str
    poem_body: str
    author: Optional[str] = ""
    audio_file: Optional[str] = ""
    recite_file: Optional[str] = ""
    music_file: Optional[str] = ""
    lyrics: Optional[str] = ""
    layout_mode: Optional[str] = "compact"
    part2_mode: Optional[str] = "motif_symbol"
    image_file_2: Optional[str] = ""

class SaveLayoutRequest(BaseModel):
    episode_no: str
    layout_mode: str = "compact"
    part2_mode: Optional[str] = "motif_symbol"
    image_file_2: Optional[str] = ""

class SaveLayoutConfigRequest(BaseModel):
    episode_no: str
    layout_config: dict

class DeleteWorkRequest(BaseModel):
    episode_no: str

class ReorderItem(BaseModel):
    episode_no: str
    chapter: Optional[str] = ""

class ReorderWorksRequest(BaseModel):
    items: List[ReorderItem]
    auto_renumber: bool = True

class GenerateFreeImageRequest(BaseModel):
    episode_no: str
    prompt: Optional[str] = None
    title: Optional[str] = ""
    memory_anchor: Optional[str] = ""
    art_style: Optional[str] = "watercolor"

class GenerateImageCandidatesRequest(BaseModel):
    episode_no: str
    prompt: Optional[str] = ""
    title: Optional[str] = ""
    memory_anchor: Optional[str] = ""
    custom_guide: Optional[str] = ""
    art_style: Optional[str] = "watercolor"
    reference_image: Optional[str] = None  # Base64 데이터 URL 또는 base64 인코딩 이미지
    direct_use_photo: Optional[bool] = False  # 사용자가 첨부한 사진 자체를 300 DPI 출판용 삽화로 즉시 변환 사용
    base_image_filename: Optional[str] = None  # 연속 편집(Image-to-Image)의 베이스가 될 기존 이미지 파일명
    use_current_as_base: Optional[bool] = True  # 기존 그림의 인물/구도를 유지한 채 부분 수정할지 여부

class SelectImageCandidateRequest(BaseModel):
    episode_no: str
    candidate_filename: str
    candidate_name: Optional[str] = "1안"
    target_slot: Optional[str] = "part1"  # "part1" (1부 본 삽화) or "part2" (2부 연작 삽화)

class GeneratePart2ImageRequest(BaseModel):
    episode_no: str
    prompt: Optional[str] = ""
    custom_guide: Optional[str] = ""
    reference_image: Optional[str] = None
    direct_use_photo: Optional[bool] = False
    art_style: Optional[str] = "watercolor"
    base_image_filename: Optional[str] = None
    use_current_as_base: Optional[bool] = True

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

class BulkParseRequest(BaseModel):
    raw_text: str

class BulkImportRequest(BaseModel):
    raw_text: str
    mode: str = "overwrite"  # "overwrite" or "append"
    auto_prompts: bool = True

class ImportSunoShareRequest(BaseModel):
    share_url: str
    episode_no: str


# 동적 이미지 서빙 (활성 프로젝트 폴더 내 images 서빙)
@app.get("/images/{image_path:path}")
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
@app.get("/music/{audio_path:path}")
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
# 중앙 회원 인증 및 로그인 라우트
# -------------------------------------------------------------
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Supabase 구글 1초 로그인 및 회원가입 페이지"""
    cfg = get_supabase_config()
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "supabase_url": cfg["url"],
            "supabase_anon_key": cfg["anon_key"]
        }
    )

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """스튜디오 메인 집필실 (로그인 검증 및 게스트 분기)"""
    is_guest = request.query_params.get("guest") == "true"
    current_user = auth_manager.get_current_user()
    cfg = get_supabase_config()

    # Supabase가 설정되어 있고, 미로그인 상태이며 게스트 요청이 아닌 경우 로그인 페이지로 안내
    if cfg["configured"] and not current_user and not is_guest:
        return RedirectResponse(url="/login")

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "current_user": current_user,
            "is_guest": is_guest,
            "is_admin": auth_manager.is_current_user_admin()
        }
    )

@app.get("/manual", response_class=HTMLResponse)
async def user_manual_page(request: Request):
    """어르신 및 컴퓨터 초보자 맞춤형 큰 글씨 사용 설명서 페이지"""
    return templates.TemplateResponse(
        request=request,
        name="manual.html",
        context={}
    )

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard_page(request: Request):
    """최고 관리자 전용 대시보드 페이지"""
    current_user = auth_manager.get_current_user()
    if not current_user:
        return RedirectResponse(url="/login")
    if not auth_manager.is_current_user_admin():
        return RedirectResponse(url="/?msg=unauthorized_admin")

    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={
            "current_user": current_user,
            "is_admin": True
        }
    )

@app.post("/api/auth/save_session")
async def save_auth_session(req: AuthSessionRequest):
    """클라이언트 로그인 성공 후 세션을 로컬에 영구 저장 및 기존 시집 자동 귀속"""
    try:
        session = auth_manager.save_session(
            user_id=req.user_id,
            email=req.email,
            access_token=req.access_token,
            name=req.name,
            provider=req.provider or "google"
        )

        # [자동 귀속: Auto Claim] 현재 활성 시집이 미할당(게스트 작성분) 상태라면 내 계정으로 즉시 소유권 이전
        claimed = False
        try:
            active_info = project_manager.get_active_project_info()
            if not active_info.owner_id:
                claimed = project_manager.claim_project(active_info.id, req.user_id, req.email)
        except Exception as claim_err:
            print(f"Auto-claim warning: {claim_err}")

        return {
            "success": True,
            "session": session,
            "claimed_project": claimed,
            "message": "로그인 성공! 작성 중이던 시집이 회원님의 계정으로 안전하게 귀속되었습니다." if claimed else "로그인 성공!"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"세션 저장 실패: {str(e)}")

@app.get("/api/auth/status")
async def get_auth_status():
    """현재 스튜디오 로그인 상태 및 사용자 정보 반환"""
    return auth_manager.get_auth_status()

@app.post("/api/auth/logout")
async def logout_endpoint():
    """스튜디오 로그아웃 및 세션 초기화"""
    success = auth_manager.clear_session()
    return {"success": success}


# -------------------------------------------------------------
# 최고 관리자(Admin) 전용 모니터링 및 제어 API
# -------------------------------------------------------------
class AdminSwitchProjectRequest(BaseModel):
    project_id: str

@app.get("/api/admin/overview")
async def get_admin_overview():
    """관리자 대시보드 전체 통계, 작가 현황, 시스템 상태 반환"""
    if not auth_manager.is_current_user_admin():
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")

    # 전체 프로젝트 조회 (user_id=None 전달로 모든 회원 프로젝트 포함)
    all_projects = project_manager.list_projects(user_id=None)
    
    total_poems = sum(p.get("total_works", 0) for p in all_projects)
    total_completed = sum(p.get("completed_count", 0) for p in all_projects)
    
    # 총 삽화 이미지 및 출판 파일 집계
    total_images = 0
    projects_detail = []
    writers_map = {}

    for p in all_projects:
        pdir = project_manager.get_project_dir(p["id"])
        img_dir = pdir / "images"
        img_count = len(list(img_dir.glob("*.*"))) if img_dir.exists() else 0
        total_images += img_count

        # 출판 자산 확인 (PDF, CSV 등)
        has_pdf = (pdir / "시화집_본문_내지.pdf").exists() or (pdir / "시화집_출판본.pdf").exists()
        has_cover = (pdir / "시화집_표지_인쇄용.pdf").exists() or (pdir / "시화집_표지.png").exists()
        has_csv = (pdir / "시화집_본문데이터.csv").exists()

        p_data = dict(p)
        p_data["image_count"] = img_count
        p_data["has_pdf"] = has_pdf
        p_data["has_cover"] = has_cover
        p_data["has_csv"] = has_csv
        projects_detail.append(p_data)

        # 작가별 통계 집계
        owner_email = p.get("owner_email") or "미할당 (게스트)"
        if owner_email not in writers_map:
            writers_map[owner_email] = {
                "email": owner_email,
                "project_count": 0,
                "total_poems": 0,
                "completed_poems": 0,
                "authors": set(),
                "last_updated": p.get("updated_at")
            }
        writers_map[owner_email]["project_count"] += 1
        writers_map[owner_email]["total_poems"] += p.get("total_works", 0)
        writers_map[owner_email]["completed_poems"] += p.get("completed_count", 0)
        if p.get("author"):
            writers_map[owner_email]["authors"].add(p.get("author"))

    writers_list = []
    for email, w in writers_map.items():
        writers_list.append({
            "email": email,
            "project_count": w["project_count"],
            "total_poems": w["total_poems"],
            "completed_poems": w["completed_poems"],
            "authors": list(w["authors"]),
            "last_updated": w["last_updated"]
        })

    # 시스템 상태
    gemini_status = get_gemini_api_key_status()
    supabase_cfg = get_supabase_config()

    return {
        "success": True,
        "kpi": {
            "total_projects": len(all_projects),
            "total_poems": total_poems,
            "total_completed": total_completed,
            "completion_rate": round((total_completed / max(1, total_poems)) * 100, 1) if total_poems > 0 else 0,
            "total_images": total_images,
            "total_writers": len(writers_map),
        },
        "projects": projects_detail,
        "writers": writers_list,
        "system": {
            "gemini": gemini_status,
            "supabase": {
                "configured": supabase_cfg["configured"],
                "url": supabase_cfg["url"]
            },
            "paper_type": PAPER_TYPE,
            "default_target_count": TARGET_POEMS_COUNT,
            "default_art_style": DEFAULT_ART_STYLE,
            "active_project_id": project_manager.get_active_project_id()
        }
    }

@app.post("/api/admin/project/switch")
async def admin_switch_project(req: AdminSwitchProjectRequest):
    """관리자가 특정 프로젝트로 스튜디오 활성 프로젝트 즉시 전환"""
    if not auth_manager.is_current_user_admin():
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")
    try:
        project_manager.set_active_project_id(req.project_id)
        return {"success": True, "active_project": req.project_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# -------------------------------------------------------------
# 시집 프로젝트 관리 API (계정별 분리 및 격리)
# -------------------------------------------------------------
@app.get("/api/projects")
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

@app.post("/api/projects/select")
async def select_project(req: ProjectSelectRequest):
    try:
        project_manager.set_active_project_id(req.project_id)
        info = project_manager.get_active_project_info()
        return {"success": True, "active_project": asdict(info)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/projects/create")
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

@app.post("/api/projects/update")
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

@app.post("/api/projects/delete")
async def delete_project(req: ProjectDeleteRequest):
    try:
        project_manager.delete_project(req.project_id)
        active_info = project_manager.get_active_project_info()
        return {"success": True, "active_project": asdict(active_info)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/projects/export_zip")
async def export_project_zip(project_id: Optional[str] = None):
    try:
        pid = project_id or project_manager.get_active_project_id()
        info = project_manager.get_project_info(pid)
        zip_path = project_manager.export_project_zip(pid)
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
@app.get("/api/status")
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

@app.get("/api/gallery_data")
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

class RenderVideoRequest(BaseModel):
    project_id: Optional[str] = None
    episode_no: str
    title: str
    image_file: str
    audio_file: Optional[str] = None
    aspect_ratio: str = "16:9"  # "16:9" | "9:16"
    mode: str = "music"         # "music" | "recite" | "bgm"

@app.get("/api/videos")
async def api_list_videos(project_id: Optional[str] = None):
    """현재 활성 프로젝트의 렌더링된 비디오 목록을 반환합니다."""
    try:
        from core.video_renderer import VideoRenderer
        pid = project_id or project_manager.get_active_project_id()
        pdir = project_manager.get_project_dir(pid)
        renderer = VideoRenderer(pdir)
        videos = renderer.list_rendered_videos()
        return {"success": True, "videos": videos}
    except Exception as e:
        return {"success": False, "error": str(e), "videos": []}

@app.post("/api/videos/render")
async def api_render_video(req: RenderVideoRequest):
    """지정된 회차의 고화질 시네마틱 MP4 비디오 렌더링을 실행합니다."""
    try:
        from core.video_renderer import VideoRenderer
        pid = req.project_id or project_manager.get_active_project_id()
        pdir = project_manager.get_project_dir(pid)
        renderer = VideoRenderer(pdir)

        # 이미지 경로 보정
        img_f = req.image_file.replace("./", "").lstrip("/")
        if not img_f.startswith("images/"):
            img_f = f"images/{img_f}"

        # 오디오 경로 보정
        audio_f = None
        if req.audio_file:
            audio_f = req.audio_file.replace("./", "").lstrip("/")
            if not audio_f.startswith("music/") and not audio_f.startswith("images/"):
                audio_f = f"music/{audio_f}"

        out_path = renderer.render_episode_video(
            episode_no=req.episode_no,
            title=req.title,
            image_path=img_f,
            audio_path=audio_f,
            aspect_ratio=req.aspect_ratio,
            mode=req.mode
        )
        return {
            "success": True,
            "filename": out_path.name,
            "path": str(out_path).replace("\\", "/"),
            "sizeMb": round(out_path.stat().st_size / (1024 * 1024), 2)
        }
    except Exception as e:
        print(f"[api_render_video 에러]: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/videos/download/{filename}")
async def api_download_video(filename: str, project_id: Optional[str] = None):
    """렌더링된 비디오 파일을 스트리밍 또는 다운로드합니다."""
    try:
        pid = project_id or project_manager.get_active_project_id()
        pdir = project_manager.get_project_dir(pid)
        vpath = pdir / "videos" / filename
        if not vpath.exists():
            raise HTTPException(status_code=404, detail="비디오 파일을 찾을 수 없습니다.")
        return FileResponse(
            path=str(vpath),
            filename=filename,
            media_type="video/mp4"
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/api/settings/gemini_key")
async def get_gemini_key_api():
    """현재 Gemini API 키 등록 여부 및 마스킹된 키 조회"""
    return get_gemini_api_key_status()

@app.get("/api/settings/gemini_model")
async def get_gemini_model_api():
    """현재 활성화된 Gemini 모델 및 선택 가능한 추천 모델 목록 반환"""
    current_model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    available_models = [
        {"id": "gemini-3.8-flash", "name": "Gemini 3.8 Flash (최신 플래그십 · 초고속/고지능 추천)", "recommended": True},
        {"id": "gemini-3.8-live-extended-thinking", "name": "Gemini 3.8 Live (심층 사고 추론 · 깊은 은유)", "recommended": False},
        {"id": "gemini-3.7-flash", "name": "Gemini 3.7 Flash (3.7세대 안정화 플래시)", "recommended": False},
        {"id": "gemini-3.1-pro-preview", "name": "Gemini 3.1 Pro (전문가급 대규모 심층 분석)", "recommended": False},
        {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash (2.5세대 기본형)", "recommended": False},
        {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro (2.5세대 프로)", "recommended": False}
    ]
    return {
        "success": True,
        "current_model": current_model,
        "models": available_models
    }

@app.post("/api/settings/gemini_model")
async def set_gemini_model_api(req: SetModelRequest):
    """원하는 Gemini 모델로 즉시 변경 및 영구 저장"""
    model_name = req.model_name.strip()
    if not model_name:
        raise HTTPException(status_code=400, detail="모델명을 입력해주세요.")
    save_gemini_model(model_name)
    return {"success": True, "current_model": model_name, "message": f"AI 모델이 [{model_name}]로 성공적으로 변경되었습니다!"}

@app.post("/api/settings/gemini_key")
async def set_gemini_key_api(req: SetApiKeyRequest):
    """Gemini API 키를 검증하고 영구 저장 및 즉시 활성화"""
    key = req.api_key.strip()
    if not key:
        raise HTTPException(status_code=400, detail="API 키를 입력해주세요.")
    
    active_model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    # Google GenAI 클라이언트 테스트
    try:
        from google import genai
        client = genai.Client(api_key=key)
        resp = client.models.generate_content(
            model=active_model,
            contents="Say 'OK' in one word."
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"API 키 검증 실패 (Google API 오류): {e}")

    save_gemini_api_key(key)
    return {"success": True, "message": "Gemini API 키가 성공적으로 등록 및 활성화되었습니다!"}

@app.post("/api/interview/deep_questions")
async def get_deep_interview_questions(req: DeepInterviewRequest):
    """기억 단편을 바탕으로 따뜻한 공감 요약 및 시적 꼬리 질문 3가지 생성"""
    core = (req.core_memory or "").strip()
    sensory = (req.sensory_details or "").strip()
    spoken = (req.spoken_words or "").strip()

    if not core and not sensory and not spoken:
        raise HTTPException(status_code=400, detail="적어도 하나의 기억 실마리를 먼저 입력해주세요.")

    # 1. Gemini API 키가 활성화되어 있으면 최신 Gemini 모델이 맥락을 분석하여 초고품격 꼬리 질문 생성
    from core.config import GEMINI_API_KEY
    if GEMINI_API_KEY:
        try:
            from google import genai
            client = genai.Client(api_key=GEMINI_API_KEY)
            active_model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
            sys_prompt = (
                "당신은 창작자의 숨겨진 기억과 감각을 깨워내는 전문 시 창작 인터뷰어(문학 프로파일러)입니다.\n"
                "사용자가 제공한 기억 단편을 바탕으로:\n"
                "1. 사용자의 기억을 한 문장으로 따뜻하고 시적으로 요약하여 깊이 공감하세요 (summary).\n"
                "2. 시의 완성도를 극적으로 끌어올릴 핵심 감각 꼬리 질문 3가지를 작성하세요:\n"
                "   - Q1: 소리와 촉각, 빛의 농도 등 생생한 감각을 묻는 질문 (category: '소리와 감각', icon: '👂')\n"
                "   - Q2: 그 순간 시선이 가장 오래 머물렀던 결정적 사물이나 인물의 모습 (category: '시선의 머무름', icon: '👁️')\n"
                "   - Q3: 그 자리를 떠날 때 가슴에 맺혔던 침묵이나 마음속 생각 (category: '마음의 결', icon: '❤️')\n"
                "반드시 아래 JSON 형식으로만 답변하세요:\n"
                '{"summary": "...", "questions": [{"id": "q1", "category": "소리와 감각", "icon": "👂", "question": "..."}, {"id": "q2", "category": "시선의 머무름", "icon": "👁️", "question": "..."}, {"id": "q3", "category": "마음의 결", "icon": "❤️", "question": "..."}]}'
            )
            user_msg = f"기억의 시간/장소/사람: {core}\n눈에 밟히는 사물과 행동: {sensory}\n가슴에 남은 말: {spoken}"
            response = client.models.generate_content(
                model=active_model,
                contents=user_msg,
                config={
                    "system_instruction": sys_prompt,
                    "response_mime_type": "application/json",
                    "temperature": 0.7
                }
            )
            import json
            data = json.loads(response.text)
            return {
                "success": True,
                "source": "gemini",
                "summary": data.get("summary", ""),
                "questions": [q.get("question", str(q)) if isinstance(q, dict) else str(q) for q in data.get("questions", [])],
                "data": data
            }
        except Exception:
            pass

    # 2. 로컬 엔진 폴백
    data = poetic_engine.generate_deep_interview_questions(core, sensory, spoken)
    questions_list = [q.get("question", str(q)) if isinstance(q, dict) else str(q) for q in data.get("questions", [])]
    return {
        "success": True,
        "source": "poetic_engine",
        "summary": data.get("summary", ""),
        "questions": questions_list,
        "data": data
    }

@app.post("/api/generate_drafts")
async def generate_drafts(req: DraftRequest):
    mgr = project_manager.get_active_manuscript_manager()
    info = project_manager.get_active_project_info()

    core_memory = (req.core_memory or "").strip()
    sensory_details = (req.sensory_details or "").strip()
    spoken_words = (req.spoken_words or "").strip()
    deep_answer = (req.deep_interview_answer or "").strip()

    if not core_memory and not sensory_details and not spoken_words:
        raise HTTPException(status_code=400, detail="1, 2, 3번 중 적어도 하나의 기억 실마리를 입력해주세요.")

    # 대표 앵커 키워드
    anchor = core_memory or sensory_details or spoken_words or "기억의 한 조각"

    # 이미지 프롬프트 생성
    next_num = mgr.get_next_episode_number()
    img_filename = f"{str(next_num).zfill(2)}_삽화.jpg"
    sensory_part = f", {sensory_details}" if sensory_details and sensory_details != anchor else ""
    spoken_part = f", reminiscent of '{spoken_words}'" if spoken_words and spoken_words != anchor else ""
    img_prompt = (
        f"Korean lyric watercolor illustration, {anchor}{sensory_part}{spoken_part}, "
        f"soft warm lighting, poetic negative space, delicate ink brush style, "
        f"no text, no letters, no watermark, 300 dpi"
    )

    card_a = f"{anchor}에서 포착한 빛과 사물의 조화"
    card_b = f"{sensory_details}에 집중한 서정적 여백의 구도" if sensory_details else f"{anchor}의 깊은 여운을 담은 서정적 구도"

    # 1. Gemini API 키가 있으면 Gemini 2.5 Flash 호출 (상투성 타파 메가 프롬프트)
    from core.config import GEMINI_API_KEY
    if GEMINI_API_KEY:
        try:
            from google import genai
            client = genai.Client(api_key=GEMINI_API_KEY)
            
            system_instruction = (
                f"당신은 백석, 정지용, 기형도의 문학적 계보를 잇는 최고 수준의 한국 현대 서정시인입니다. 시집: 「{info.name}」\n"
                "【엄격한 작시 철학】\n"
                "1. 산문형 문장 나열이나 어설픈 줄바꿈을 엄격히 금지합니다. 철저히 시적 행(Line)과 연(Stanza)의 리듬감으로 재창조하세요.\n"
                "2. '사랑', '그리움', '온기', '희망', '슬픔' 등 뻔하고 상투적인 신파 클리셰 단어를 직접 쓰지 마세요. 사물의 낯설게 하기와 감각의 전이(비유, 환유)로 정서를 드러내세요.\n"
                "3. 사용자가 제공한 실제 사실(장소, 사물, 행동, 말, 심층 인터뷰 디테일)만을 원료로 삼고, 없는 허위 사건이나 인물을 지어내지 마세요.\n"
                "4. A안: 담담하고 서늘하게 정경을 포착하는 서사적 서정시 (사물과 풍경 중심의 여백)\n"
                "5. B안: 깊은 울림과 파격적인 은유, 침묵의 여백을 품은 내면 서정시\n"
                "반드시 다음 JSON 형식으로만 출력하세요:\n"
                '{"title_a": "A안 제목", "body_a": "A안 시 본문", "title_b": "B안 제목", "body_b": "B안 시 본문"}'
            )

            prompt = (
                f"기억의 시간/장소/사람: {core_memory if core_memory else '미입력'}\n"
                f"눈에 밟히는 사물과 행동: {sensory_details if sensory_details else '미입력'}\n"
                f"가슴에 남은 말 한마디: {spoken_words if spoken_words else '없음'}\n"
                f"심층 인터뷰 보충 답변: {deep_answer if deep_answer else '없음(1차 사실 중심 고도화)'}\n\n"
                "위 소재를 바탕으로 상투성을 완전히 파괴한 A안과 B안 시 2편을 창작해 주세요."
            )

            active_model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
            response = client.models.generate_content(
                model=active_model,
                contents=prompt,
                config={
                    "system_instruction": system_instruction,
                    "response_mime_type": "application/json",
                    "temperature": 0.75
                }
            )
            import json
            data = json.loads(response.text)
            return {
                "success": True,
                "source": "gemini",
                "draft_a": {"title": data.get("title_a", "기억의 한 켠"), "body": data.get("body_a", "")},
                "draft_b": {"title": data.get("title_b", "머무는 자리"), "body": data.get("body_b", "")},
                "card_a": card_a,
                "card_b": card_b,
                "image_prompt": img_prompt,
                "suggested_image_file": f"images/{img_filename}"
            }
        except Exception:
            pass

    # 2. 키리스 모드: 업그레이드된 지능형 서정 작시 엔진 (API 키 불필요, 시적 분절 및 심층 답변 융합)
    engine_drafts = poetic_engine.compose_dual_drafts(
        core_memory=core_memory,
        sensory_details=sensory_details,
        spoken_words=spoken_words,
        style_seed=req.style_seed,
        deep_interview_answer=deep_answer
    )

    return {
        "success": True,
        "source": "poetic_engine",
        "draft_a": engine_drafts["draft_a"],
        "draft_b": engine_drafts["draft_b"],
        "card_a": card_a,
        "image_prompt": img_prompt,
        "suggested_image_file": f"images/{img_filename}"
    }

@app.post("/api/refine_poem")
async def refine_poem_endpoint(req: RefinePoemRequest):
    """현재 시 본문을 사용자가 원하는 방향(압축, 절제, 운율 또는 자유 지시문)으로 즉시 다듬기 (Gemini 퇴고 스킬 지원)"""
    res = poetic_engine.refine_poem_with_gemini(
        title=req.title or "시",
        poem_body=req.poem_body,
        mode=req.mode or "custom",
        custom_instruction=req.instruction or ""
    )
    return {
        "success": True,
        "refined_body": res.get("refined_body", req.poem_body),
        "commentary": res.get("commentary", "")
    }

@app.post("/api/generate_lyrics")
async def generate_lyrics_endpoint(req: LyricsGenerateRequest):
    """
    [음악 모듈러 블록 아키텍처]
    시 본문에서 이전 장르 오염을 도려내고, 선택된 서정 장르(민요, 포크, 가곡, 동요) 고유 스킬 블록과
    공통 음악 출판 규격을 결합하여 맞춤 노랫말 및 음악 AI 프롬프트 생성
    """
    try:
        from core.skill_pack import build_modular_song_package
        api_key = os.getenv("GEMINI_API_KEY") or GEMINI_API_KEY
        pkg = build_modular_song_package(
            poem_body=req.poem_body or "",
            title=req.title or "무제",
            genre_key=req.genre or "folk",
            custom_guide=req.custom_guide or "",
            api_key=api_key
        )
        return {
            "success": True,
            "data": pkg,
            "title": pkg.get("title", req.title or "무제"),
            "genre": pkg.get("genre", req.genre or "folk"),
            "genre_name": pkg.get("genre_name", ""),
            "mood_theme": pkg.get("mood_theme", ""),
            "instruments": pkg.get("instruments", ""),
            "bpm": pkg.get("bpm", ""),
            "music_prompt": pkg.get("music_prompt", ""),
            "lyrics": pkg.get("lyrics", "")
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/update_lyrics")
async def update_lyrics_endpoint(req: UpdateLyricsRequest):
    """갤러리 또는 스튜디오에서 특정 회차의 노래 가사만 즉시 수정 및 원고 동기화"""
    try:
        mgr = project_manager.get_active_manuscript_manager()
        work = mgr.get_work_by_episode(req.episode_no)
        if not work:
            clean_ep = re.sub(r'[^0-9]', '', req.episode_no).zfill(2)
            target_ep = f"제{clean_ep}화"
            work = mgr.get_work_by_episode(target_ep)
        if not work:
            raise HTTPException(status_code=404, detail=f"해당 회차({req.episode_no})를 찾을 수 없습니다.")
        work.lyrics = req.lyrics.strip()
        mgr.save_work(work)
        print(f"[노랫말 실시간 수정 완료] {work.episode_no} lyrics 갱신 ({len(work.lyrics)}자)")
        return {"success": True, "episode_no": work.episode_no, "lyrics": work.lyrics}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/generate_image_prompt")
async def generate_image_prompt_endpoint(req: ImagePromptRequest):
    """다듬어진 시 제목과 본문을 분석하여 300 DPI 서정 삽화 프롬프트 생성 (모듈러 블록 아키텍처)"""
    from core.skill_pack import build_modular_art_prompt
    
    raw_korean = poetic_engine.generate_korean_art_prompt(
        title=req.title,
        poem_body=req.poem_body,
        core_memory=req.core_memory,
        sensory_details=req.sensory_details,
        style_mode=req.style_mode or "literal",
        art_style=req.art_style or "watercolor",
        custom_guide=req.custom_guide or ""
    )
    
    # 모듈러 블록 아키텍처를 통한 화풍 전용 블록 결합 및 타 화풍 오염 도려내기
    modular = build_modular_art_prompt(
        raw_prompt=raw_korean,
        art_style=req.art_style or "watercolor",
        custom_guide=req.custom_guide or "",
        title=req.title or "",
        memory_anchor=req.core_memory or ""
    )
    
    english_prompt = modular["guarded_en_prompt"]
    korean_instruction = modular["gemini_ko_content"]
    display_prompt = modular["display_ko_prompt"]

    return {
        "success": True,
        "prompt": display_prompt,
        "korean_prompt": display_prompt,
        "english_prompt": english_prompt,
        "korean_instruction": korean_instruction,
        "style_mode": req.style_mode or "literal",
        "art_style": req.art_style or "watercolor"
    }

@app.post("/api/smart_prompt")
async def get_smart_prompt_endpoint(req: ExternalPromptRequest):
    """외부 무료 AI(ChatGPT, Claude, 뤼튼 등)에 붙여넣을 전문 서정시 프롬프트 생성"""
    info = project_manager.get_active_project_info()
    prompt_text = poetic_engine.get_external_ai_prompt(
        core_memory=req.core_memory,
        sensory_details=req.sensory_details,
        spoken_words=req.spoken_words,
        book_title=info.name
    )
    return {"success": True, "prompt": prompt_text}

@app.post("/api/save_work")
async def save_work(req: SaveWorkRequest):
    mgr = project_manager.get_active_manuscript_manager()
    recite_f = req.recite_file or ""
    music_f = req.music_file or ""
    audio_f = req.audio_file or music_f or recite_f or ""

    # 기존 work가 있다면 2부 삽화, 조판 설정 등 기존 값 보존
    existing_works = mgr.load_works()
    clean_ep = re.sub(r'[^0-9]', '', req.episode_no).zfill(2) if req.episode_no else "01"
    old_work = next((w for w in existing_works if clean_ep in w.episode_no or w.episode_no.strip() == req.episode_no.strip()), None)

    work = PoemWork(
        episode_no=req.episode_no,
        title=req.title,
        status=req.status,
        memory_anchor=req.memory_anchor,
        image_file=req.image_file or (old_work.image_file if old_work else ""),
        art_direction=req.art_direction,
        poem_body=req.poem_body,
        audio_file=audio_f or (old_work.audio_file if old_work else ""),
        recite_file=recite_f or (old_work.recite_file if old_work else ""),
        music_file=music_f or (old_work.music_file if old_work else ""),
        lyrics=req.lyrics or (old_work.lyrics if old_work else ""),
        author=req.author or (old_work.author if old_work else ""),
        layout_mode=req.layout_mode or (old_work.layout_mode if old_work else "compact"),
        chapter=old_work.chapter if old_work else "",
        part2_mode=old_work.part2_mode if old_work else "motif_symbol",
        image_file_2=old_work.image_file_2 if old_work else "",
        layout_config=old_work.layout_config if old_work else None
    )
    mgr.save_work(work)

    # 퇴고 판본(Revision) 스냅샷 자동 보관
    try:
        from core.revision_manager import save_revision_snapshot
        p_dir = project_manager.get_project_dir()
        save_revision_snapshot(
            project_dir=p_dir,
            episode_no=req.episode_no,
            title=req.title,
            poem_body=req.poem_body
        )
    except Exception:
        pass

    # CSV도 자동 동기화 갱신
    try:
        build_canva_csv()
    except Exception:
        pass

    return {"success": True, "message": f"[{req.episode_no}] 「{req.title}」 원고가 저장되었습니다."}

@app.post("/api/save_work_layout")
async def save_work_layout_endpoint(req: SaveLayoutRequest):
    """시화집 조판 편집 화면에서 원클릭으로 조판 모드('compact' vs 'multi_page') 및 4P 좌측면 연출 설정 저장"""
    mgr = project_manager.get_active_manuscript_manager()
    success = mgr.update_work_layout(req.episode_no, req.layout_mode, req.part2_mode, req.image_file_2)
    if not success:
        raise HTTPException(status_code=404, detail=f"{req.episode_no} 작품을 찾을 수 없습니다.")
    return {
        "success": True,
        "episode_no": req.episode_no,
        "layout_mode": req.layout_mode,
        "part2_mode": req.part2_mode,
        "image_file_2": req.image_file_2
    }

@app.post("/api/save_work_layout_config")
async def save_work_layout_config_endpoint(req: SaveLayoutConfigRequest):
    """2P/4P 매트릭스 슬롯 조판 설정 영구 저장"""
    mgr = project_manager.get_active_manuscript_manager()
    success = mgr.update_work_layout_config(req.episode_no, req.layout_config)
    if not success:
        raise HTTPException(status_code=404, detail=f"{req.episode_no} 작품을 찾을 수 없습니다.")
    return {
        "success": True,
        "episode_no": req.episode_no,
        "layout_config": req.layout_config
    }


# -------------------------------------------------------------
# 시인의 집필실: 퇴고 판본(Revision) & 육성 낭송 API
# -------------------------------------------------------------
@app.get("/api/revisions/{episode_no}")
async def get_work_revisions(episode_no: str):
    from core.revision_manager import get_revisions
    p_dir = project_manager.get_project_dir()
    revs = get_revisions(p_dir, episode_no)
    return {"success": True, "revisions": revs}

class CompareRevisionsRequest(BaseModel):
    body_a: str
    body_b: str
    name_a: str = "선택 판본"
    name_b: str = "현재 편집본"

@app.post("/api/compare_revisions")
async def compare_work_revisions(req: CompareRevisionsRequest):
    from core.revision_manager import compare_revisions
    diff_res = compare_revisions(req.body_a, req.body_b, req.name_a, req.name_b)
    return {"success": True, "diff": diff_res}

@app.post("/api/save_voice_recording")
async def save_voice_recording(
    episode_no: str = Form(...),
    title: str = Form(...),
    audio_file: UploadFile = File(...)
):
    p_img_dir = project_manager.get_active_images_dir()
    p_img_dir.mkdir(parents=True, exist_ok=True)

    safe_ep = episode_no.replace(" ", "_").replace("/", "_")
    ext = ".webm"
    if audio_file.filename:
        suffix = Path(audio_file.filename).suffix
        if suffix:
            ext = suffix

    saved_name = f"{safe_ep}_낭송{ext}"
    target_path = p_img_dir / saved_name

    content = await audio_file.read()
    with open(target_path, "wb") as f:
        f.write(content)

    rel_path = f"images/{saved_name}"

    # 원고에도 recite_file 경로 자동 업데이트 (기존 노래 music_file은 보존)
    mgr = project_manager.get_active_manuscript_manager()
    work = mgr.get_work_by_episode(episode_no)
    if work:
        work.recite_file = rel_path
        if not getattr(work, "audio_file", ""):
            work.audio_file = rel_path
        mgr.save_work(work)
        try:
            build_canva_csv()
        except Exception:
            pass

    return {
        "success": True,
        "message": f"[{episode_no}] 육성 낭송 녹음이 안전하게 보관되었습니다.",
        "audio_file": rel_path,
        "filename": saved_name
    }


@app.post("/api/delete_work")
async def delete_work(req: DeleteWorkRequest):
    mgr = project_manager.get_active_manuscript_manager()
    success = mgr.delete_work(req.episode_no)
    if not success:
        raise HTTPException(status_code=404, detail=f"[{req.episode_no}] 작품을 찾을 수 없습니다.")

    # CSV도 자동 동기화 갱신
    try:
        build_canva_csv()
    except Exception:
        pass

    return {"success": True, "message": f"[{req.episode_no}] 원고가 성공적으로 삭제되었습니다."}

@app.post("/api/reorder_works")
async def reorder_works_endpoint(req: ReorderWorksRequest):
    mgr = project_manager.get_active_manuscript_manager()
    items_dict = [it.dict() for it in req.items]
    works = mgr.reorder_works(items_dict, auto_renumber=req.auto_renumber)

    # CSV도 자동 동기화 갱신
    try:
        build_canva_csv()
    except Exception:
        pass

    return {
        "success": True,
        "message": f"총 {len(works)}편의 목차 및 순서가 성공적으로 정리되었습니다.",
        "works_count": len(works)
    }


@app.post("/api/upload_audio")
async def upload_audio_endpoint(
    audio_file: UploadFile = File(...),
    episode_no: str = Form(...),
    lyrics: Optional[str] = Form(None)
):
    """사용자가 외부 AI(Colab YuE2, Suno 등)나 웹 녹음기에서 녹음한 오디오 파일을
    앞뒤 무음 자동 검사/트리밍 및 320kbps MP3로 최적화하여 music/ 디렉토리에 저장하고 가사 동기화"""
    temp_upload = None
    try:
        project_dir = project_manager.get_project_dir()
        music_dir = project_dir / "music"
        music_dir.mkdir(parents=True, exist_ok=True)

        orig_name = audio_file.filename or "song.mp3"
        clean_ep = re.sub(r'[^0-9]', '', episode_no).zfill(2) if episode_no else "01"
        safe_name = f"{clean_ep}_음원.mp3"
        target_path = music_dir / safe_name

        # 임시 업로드 파일로 먼저 저장
        temp_upload = music_dir / f"upload_tmp_{int(time.time())}_{orig_name}"
        with open(temp_upload, "wb") as buffer:
            shutil.copyfileobj(audio_file.file, buffer)

        # 안실장 오디오 프로세서: 앞뒤 무음 자동 감지/트리밍 및 고음질 MP3 변환
        proc_result = clean_and_optimize_audio(temp_upload, target_path)

        rel_path = f"music/{safe_name}"
        active_id = project_manager.get_active_project_id()
        web_url = f"/projects/{active_id}/{rel_path}?t={int(time.time())}"

        # 원고에도 music_file 경로 및 가사(lyrics) 자동 업데이트 (기존 낭송 recite_file은 보존)
        mgr = project_manager.get_active_manuscript_manager()
        work = mgr.get_work_by_episode(episode_no)
        if work:
            work.music_file = rel_path
            if not getattr(work, "audio_file", ""):
                work.audio_file = rel_path
            if lyrics is not None and lyrics.strip():
                work.lyrics = lyrics.strip()
            mgr.save_work(work)

        return {
            "success": True,
            "audio_file": rel_path,
            "music_file": rel_path,
            "web_url": web_url,
            "filename": safe_name,
            "trimmed": proc_result.get("trimmed", False),
            "trim_message": proc_result.get("message", "음원이 성공적으로 등록되었습니다."),
            "orig_duration": proc_result.get("orig_duration_str", ""),
            "final_duration": proc_result.get("final_duration_str", ""),
            "trimmed_seconds": proc_result.get("trimmed_seconds", 0.0)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        if temp_upload and temp_upload.exists():
            try:
                temp_upload.unlink()
            except Exception:
                pass

@app.post("/api/trim_audio")
async def trim_audio_endpoint(req: TrimAudioRequest):
    """지정한 회차의 음원 앞뒤를 수동으로 정밀하게 자르기"""
    try:
        project_dir = project_manager.get_project_dir()
        music_dir = project_dir / "music"
        clean_ep = re.sub(r'[^0-9]', '', req.episode_no).zfill(2) if req.episode_no else "01"
        target_path = music_dir / f"{clean_ep}_음원.mp3"
        if not target_path.exists():
            matches = list(music_dir.glob(f"{clean_ep}_음원.*"))
            if matches:
                target_path = matches[0]
            else:
                return {"success": False, "error": f"{req.episode_no}의 등록된 음원 파일을 찾을 수 없습니다."}

        start_sec = parse_time_to_seconds(req.start_time) or 0.0
        end_sec = parse_time_to_seconds(req.end_time) if req.end_time else None

        res = trim_audio_manually(target_path, start_sec=start_sec, end_sec=end_sec)
        if res["success"]:
            active_id = project_manager.get_active_project_id()
            rel_path = f"music/{target_path.name}"
            web_url = f"/projects/{active_id}/{rel_path}?t={int(time.time())}"
            return {
                "success": True,
                "message": res["message"],
                "new_duration": res["new_duration"],
                "new_duration_str": res["new_duration_str"],
                "web_url": web_url,
                "filename": target_path.name
            }
        else:
            return {"success": False, "error": res["message"]}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/import_suno_url")
async def import_suno_url_endpoint(req: ImportSunoRequest):
    """
    Suno 곡 공유 링크(https://suno.com/song/{uuid})에서 song ID를 추출하여
    Suno 무료 공개 CDN에서 MP3를 직접 무료 다운로드하여 등록 (Out of Downloads 결제 우회)
    """
    try:
        raw_url = req.url.strip()
        # UUID 추출
        uuid_match = re.search(r'([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})', raw_url)
        if not uuid_match:
            return {"success": False, "error": "올바른 Suno 곡 링크나 UUID가 아닙니다. Suno의 [Copy Link] 버튼을 눌러 링크를 복사해주세요."}
        
        song_uuid = uuid_match.group(1).lower()
        cdn_urls = [
            f"https://cdn1.suno.ai/{song_uuid}.mp3",
            f"https://audiopipe.suno.ai/?item_id={song_uuid}"
        ]

        # 음원 다운로드 시도
        audio_bytes = None
        for cdn in cdn_urls:
            try:
                req_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                r = urllib.request.Request(cdn, headers=req_headers)
                with urllib.request.urlopen(r, timeout=15) as resp:
                    if resp.status == 200:
                        audio_bytes = resp.read()
                        if len(audio_bytes) > 1000:
                            break
            except Exception:
                continue

        if not audio_bytes:
            return {"success": False, "error": "Suno 음원 CDN 서버에서 오디오를 내려받지 못했습니다. 링크가 유효한지 확인해주세요."}

        project_dir = project_manager.get_project_dir()
        music_dir = project_dir / "music"
        music_dir.mkdir(parents=True, exist_ok=True)

        clean_ep = re.sub(r'[^0-9]', '', req.episode_no).zfill(2) if req.episode_no else "01"
        safe_name = f"{clean_ep}_음원.mp3"
        target_path = music_dir / safe_name

        with open(target_path, "wb") as f:
            f.write(audio_bytes)

        rel_path = f"music/{safe_name}"
        active_id = project_manager.get_active_project_id()
        web_url = f"/projects/{active_id}/{rel_path}"

        # 원고에도 music_file 자동 업데이트
        mgr = project_manager.get_active_manuscript_manager()
        work = mgr.get_work_by_episode(req.episode_no)
        if work:
            work.music_file = rel_path
            if not getattr(work, "audio_file", ""):
                work.audio_file = rel_path
            mgr.save_work(work)

        return {
            "success": True,
            "audio_file": rel_path,
            "music_file": rel_path,
            "web_url": web_url,
            "filename": safe_name,
            "size": len(audio_bytes)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def build_poetic_recitation_script(title: str, poem_body: str) -> str:
    """
    [poetic-recitation 스킬 기반]
    서정시 원문을 AI 성우(Gemini 3.8 Flash TTS)가 여유로운 호흡(분당 110~130음절)과 
    깊은 침묵(Pause: 연간 1.5초, 행간 0.8초)을 두고 시답게 낭송하도록 시낭송 전용 대본으로 변환합니다.
    """
    clean_title = (title or "").strip()
    norm_body = poem_body.replace('\r\n', '\n').strip()
    
    stanzas = [s.strip() for s in norm_body.split('\n\n') if s.strip()]
    processed_stanzas = []
    
    for stanza in stanzas:
        lines = [line.strip() for line in stanza.split('\n') if line.strip()]
        processed_lines = []
        for line in lines:
            # 끝 구두점 체크
            if not any(line.endswith(punct) for punct in ['.', '?', '!', '...', ',', '—', '~']):
                # 구두점이 없으면 서정 호흡 쉼표/말줄임 보강
                line = line + "..."
            elif line.endswith('.'):
                # 단절되는 마침표 대신 긴 여운의 말줄임표로 변환
                line = line[:-1] + "..."
            processed_lines.append(line)
        # 행과 행 사이에 이중 줄바꿈으로 0.8초 숨고르기 부여
        processed_stanzas.append('\n\n'.join(processed_lines))
    
    # 연과 연 사이에 삼중 줄바꿈으로 1.5초의 자연스러운 침묵 부여
    script_body = '\n\n\n'.join(processed_stanzas)
    
    if clean_title and clean_title != "무제":
        return f"{clean_title}...\n\n\n\n{script_body}"
    return script_body


class SetTtsEngineRequest(BaseModel):
    engine: str

@app.get("/api/tts/status")
async def get_tts_status():
    """현재 TTS 엔진 상태 및 Google 크레딧 만료 여부 반환"""
    return {
        "engine": TTS_STATE["engine"],
        "gemini_credit_expired": TTS_STATE["gemini_credit_expired"],
        "last_error": TTS_STATE["last_error"],
        "error_type": TTS_STATE["error_type"]
    }

@app.post("/api/tts/set_engine")
async def set_tts_engine(req: SetTtsEngineRequest):
    """사용자가 직접 TTS 엔진을 전환 (gemini | edge)"""
    if req.engine in ["gemini", "edge"]:
        TTS_STATE["engine"] = req.engine
        return {"success": True, "engine": TTS_STATE["engine"]}
    raise HTTPException(status_code=400, detail="유효하지 않은 엔진입니다.")

@app.post("/api/tts/check_google")
async def check_google_tts():
    """
    Google Cloud 크레딧이 재충전되었는지 1글자 테스트 호출로 실시간 검증합니다.
    재충전 확인 시 Google Gemini TTS 모드로 자동 원복합니다.
    """
    from core.config import GEMINI_API_KEY
    key = os.getenv("GEMINI_API_KEY") or GEMINI_API_KEY
    if not key or not genai:
        return {"success": False, "message": "Gemini API 키가 등록되어 있지 않습니다."}
    
    try:
        client = genai.Client(api_key=key)
        res = client.models.generate_content(
            model="gemini-3.8-flash-tts",
            contents="달빛.",
            config={
                "response_modalities": ["AUDIO"],
                "speech_config": {
                    "voice_config": {
                        "prebuilt_voice_config": {
                            "voice_name": "Aoede"
                        }
                    }
                }
            }
        )
        if res and res.candidates and res.candidates[0].content:
            TTS_STATE["engine"] = "gemini"
            TTS_STATE["gemini_credit_expired"] = False
            TTS_STATE["last_error"] = None
            TTS_STATE["error_type"] = None
            return {
                "success": True,
                "engine": "gemini",
                "message": "🎉 Google API 크레딧 충전 및 연결이 정상 확인되었습니다! Google Gemini TTS로 복원되었습니다."
            }
        else:
            raise Exception("응답 데이터가 비어 있습니다.")
    except Exception as e:
        err_msg = str(e)
        is_credit_err = "402" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "credit" in err_msg.lower() or "quota" in err_msg.lower()
        TTS_STATE["gemini_credit_expired"] = True
        TTS_STATE["engine"] = "edge"
        TTS_STATE["last_error"] = err_msg
        TTS_STATE["error_type"] = "CREDIT_EXHAUSTED" if is_credit_err else "API_ERROR"
        return {
            "success": False,
            "engine": "edge",
            "gemini_credit_expired": True,
            "error_type": TTS_STATE["error_type"],
            "message": f"아직 Google API 크레딧이 충전되지 않았습니다: {err_msg[:120]}"
        }

@app.post("/api/speak_poem")
async def speak_poem_endpoint(req: SpeakPoemRequest):
    """
    1. 기본: Google Gemini TTS(gemini-3.8-flash-tts)로 선택된 성우로 녹음.
    2. Google API 크레딧 만료 시:
       - 크레딧 만료 상태(gemini_credit_expired) 즉시 기록 및 응답 통지
       - Microsoft Edge-TTS(고품질 신경망)로 자동 전환하여 성우 교체 및 음원 생성
    3. 재충전 시 Google TTS로 원복 가능.
    """
    import sys, os
    import base64
    import time
    import asyncio
    import io, wave
    from core.config import GEMINI_API_KEY

    clean_title = (req.title or "").strip()
    poem_text = req.poem_body.strip()
    if not poem_text:
        raise HTTPException(status_code=400, detail="낭송할 시 본문이 비어 있습니다.")

    clean_ep = re.sub(r'[^0-9]', '', req.episode_no).zfill(2) if req.episode_no else "01"
    project_dir = project_manager.get_project_dir()
    music_dir = project_dir / "music"
    music_dir.mkdir(parents=True, exist_ok=True)

    # 🎙️ poetic-recitation 스킬 기반 시낭송 호흡 대본(Script) 자동 생성
    full_recite_text = build_poetic_recitation_script(clean_title, poem_text)

    audio_data = None
    mime_type = "audio/wav"
    recite_filename = f"{clean_ep}_낭송.wav"
    provider_name = "Gemini 3.8 Flash"
    engine_used = "gemini"
    just_switched_to_edge = False
    credit_notice = None
    last_edge_err = ""

    # 요청된 성우 식별 (Gemini 성우 vs Edge-TTS 성우)
    raw_voice = req.voice or "Aoede"
    is_edge_voice = raw_voice.startswith("ko-KR-")
    
    # 강제 Edge 모드이거나, 이미 크레딧 만료 상태이거나, 요청 엔진이 edge인 경우 Google 시도 건너뜀
    target_engine = req.engine or "auto"
    skip_gemini = (target_engine == "edge") or is_edge_voice or TTS_STATE["gemini_credit_expired"]

    # 1. Google Gemini 3.8 Flash TTS 시도
    if not skip_gemini:
        key = os.getenv("GEMINI_API_KEY") or GEMINI_API_KEY
        gemini_voice = raw_voice if raw_voice in ["Aoede", "Charon", "Kore", "Puck", "Fenrir"] else "Aoede"
        if key and genai:
            try:
                client = genai.Client(api_key=key)
                models_to_try = ["gemini-3.8-flash-tts", "gemini-2.5-flash-preview-tts"]
                for m_name in models_to_try:
                    try:
                        res = client.models.generate_content(
                            model=m_name,
                            contents=full_recite_text,
                            config={
                                "response_modalities": ["AUDIO"],
                                "speech_config": {
                                    "voice_config": {
                                        "prebuilt_voice_config": {
                                            "voice_name": gemini_voice
                                        }
                                    }
                                }
                            }
                        )
                        if res and res.candidates and res.candidates[0].content and res.candidates[0].content.parts:
                            for part in res.candidates[0].content.parts:
                                if hasattr(part, "inline_data") and part.inline_data and part.inline_data.data:
                                    audio_data = part.inline_data.data
                                    mime_type = getattr(part.inline_data, "mime_type", "audio/wav")
                                    provider_name = f"Google Gemini ({gemini_voice})"
                                    engine_used = "gemini"
                                    TTS_STATE["gemini_credit_expired"] = False
                                    break
                        if audio_data:
                            break
                    except Exception as m_err:
                        err_str = str(m_err)
                        print(f"[Gemini TTS {m_name}] 오류: {err_str}")
                        if "402" in err_str or "RESOURCE_EXHAUSTED" in err_str or "credit" in err_str.lower() or "quota" in err_str.lower():
                            TTS_STATE["gemini_credit_expired"] = True
                            TTS_STATE["engine"] = "edge"
                            TTS_STATE["error_type"] = "CREDIT_EXHAUSTED"
                            just_switched_to_edge = True
                            credit_notice = "Google API 크레딧이 만료되어 Edge-TTS(무료 고음질 신경망) 성우로 자동 전환되었습니다. 재충전 시까지 Edge-TTS가 유지됩니다."
                            break
            except Exception as gemini_err:
                print(f"[Gemini 1순위 시도 실패]: {gemini_err}")

    # 2. Edge-TTS 신경망 성우로 생성 (크레딧 만료 또는 Edge 모드 시)
    if not audio_data:
        try:
            import edge_tts
            import edge_tts.constants
            import importlib
            importlib.reload(edge_tts.constants)
            importlib.reload(edge_tts)
            engine_used = "edge"
            
            # 성우 매핑
            if is_edge_voice:
                edge_voice = raw_voice
            elif raw_voice in ["Charon", "Fenrir"]:
                edge_voice = "ko-KR-InJoonNeural"
            elif raw_voice == "Puck":
                edge_voice = "ko-KR-HyunsuMultilingualNeural"
            else:
                edge_voice = "ko-KR-SunHiNeural"

            edge_rate = "-12%" if "InJoon" in edge_voice else "-10%"

            # 성우 친화적 이름 라벨링
            voice_label = "선희 (서정 여성)" if "SunHi" in edge_voice else ("인준 (남성 중저음)" if "InJoon" in edge_voice else ("현수 (차분 청년)" if "Hyunsu" in edge_voice else "봉진 (원로 남성)"))

            title_prefix = f"{clean_title}." if clean_title and clean_title != "무제" else ""
            tts_plain = f"{title_prefix}\n\n{poem_text}"
            recite_path = music_dir / recite_filename

            print(f"[Edge-TTS 신경망 성우 낭송 시작]: {edge_voice} (속도: {edge_rate})")

            # 🚀 uvicorn 비동기 소켓 충돌(403)을 피하기 위해 격리된 서브프로세스로 edge-tts 실행
            import tempfile
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as tf:
                tf.write(tts_plain)
                tf_path = tf.name

            import subprocess
            def run_edge_tts_cli():
                cmd = [
                    sys.executable, "-m", "edge_tts",
                    "--file", tf_path,
                    "--voice", edge_voice,
                    f"--rate={edge_rate}",
                    "--write-media", str(recite_path)
                ]
                return subprocess.run(cmd, capture_output=True, text=True)

            try:
                res = await asyncio.to_thread(run_edge_tts_cli)
                if res.returncode != 0:
                    raise RuntimeError(f"Edge-TTS 프로세스 오류 (code {res.returncode}): {res.stderr}")
            finally:
                if os.path.exists(tf_path):
                    try:
                        os.unlink(tf_path)
                    except Exception:
                        pass

            if recite_path.exists() and recite_path.stat().st_size > 0:
                with open(recite_path, "rb") as f:
                    audio_data = f.read()
                mime_type = "audio/mp3"
                provider_name = f"Edge-TTS 신경망 [{voice_label}]"
                print(f"[Edge-TTS 성공]: {len(audio_data)} bytes ({recite_filename}) 생성 완료")
        except Exception as edge_err:
            last_edge_err = str(edge_err)
            print(f"[Edge-TTS 실행 오류]: {edge_err}")

    if not audio_data:
        raise HTTPException(
            status_code=500,
            detail=f"Gemini 및 Edge 신경망 음성 합성 모두 실패했습니다: {last_edge_err}"
        )

    # Gemini 헤더 없는 PCM 처리
    if mime_type == "audio/wav" and not audio_data.startswith(b"RIFF"):
        wav_io = io.BytesIO()
        with wave.open(wav_io, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(24000)
            wf.writeframes(audio_data)
        audio_data = wav_io.getvalue()

    b64_audio = base64.b64encode(audio_data).decode("utf-8")
    data_uri = f"data:{mime_type};base64,{b64_audio}"

    # 프로젝트 music 폴더에 자동 음원 저장
    recite_path = music_dir / recite_filename
    with open(recite_path, "wb") as f:
        f.write(audio_data)

    # 원고(작품집_원고.md)에 낭송 음원(recite_file) 자동 동기화
    try:
        mgr = project_manager.get_active_manuscript_manager()
        works = mgr.load_works()
        target_ep = f"제{clean_ep}화"
        target_work = next((w for w in works if w.episode_no == target_ep), None)
        if target_work:
            target_work.recite_file = f"music/{recite_filename}"
            mgr.save_work(target_work)
            print(f"[원고 낭송 동기화] {target_ep} recite_file = music/{recite_filename} 저장 완료")
    except Exception as sync_err:
        print(f"[원고 낭송 동기화 알림]: {sync_err}")

    active_id = project_manager.get_active_project_id()
    audio_url = f"/projects/{active_id}/music/{recite_filename}?t={int(time.time())}"

    return {
        "success": True,
        "data_uri": data_uri,
        "audio_url": audio_url,
        "filename": recite_filename,
        "rel_path": f"music/{recite_filename}",
        "engine_used": engine_used,
        "gemini_credit_expired": TTS_STATE["gemini_credit_expired"],
        "just_switched": just_switched_to_edge,
        "credit_notice": credit_notice,
        "provider_name": provider_name,
        "message": f"{provider_name} 고음질 서정 낭송이 생성되었습니다."
    }

@app.post("/api/import_suno_share")
async def import_suno_share_endpoint(req: ImportSunoShareRequest):
    """
    Suno 공유 링크(https://suno.com/song/<UUID>)에서 CDN 오디오 스트림을 추출하여
    무료 계정 다운로드 7회 제한 없이 즉시 프로젝트 내 music/{ep}_음원.mp3로 자동 저장 및 원고 연동
    """
    import urllib.request, time, re

    raw_url = (req.share_url or "").strip()
    if not raw_url:
        raise HTTPException(status_code=400, detail="Suno 공유 링크를 입력해주세요.")

    # 1. UUID 추출 (직접 UUID가 포함된 링크 또는 단축 공유 링크 https://suno.com/s/... 지원)
    song_id = None
    match = re.search(r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})', raw_url, re.IGNORECASE)
    if match:
        song_id = match.group(1).lower()
    else:
        # 단축 공유 링크 (예: https://suno.com/s/...) 리다이렉트 추적
        try:
            resolve_req = urllib.request.Request(raw_url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://suno.com/"
            })
            with urllib.request.urlopen(resolve_req, timeout=10) as resolve_resp:
                final_url = resolve_resp.geturl()
                m_url = re.search(r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})', final_url, re.IGNORECASE)
                if m_url:
                    song_id = m_url.group(1).lower()
                else:
                    html_content = resolve_resp.read().decode("utf-8", errors="ignore")
                    m_html = re.search(r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})', html_content, re.IGNORECASE)
                    if m_html:
                        song_id = m_html.group(1).lower()
        except Exception as resolve_err:
            print(f"[Suno 단축 링크 추적 오류]: {resolve_err}")

    if not song_id:
        raise HTTPException(
            status_code=400, 
            detail="유효한 Suno 곡 공유 링크 형식이 아닙니다.\n지원 형식:\n• https://suno.com/s/단축코드\n• https://suno.com/song/곡UUID"
        )

    # 2. Suno 최신 오디오 스트림 다운로드 (공식 임베드 CloudFront 자동 추출 1순위 -> CDN 직접 시도 2순위)
    audio_bytes = None
    last_err = None

    # [1순위] Suno 공식 임베드 페이지에서 최신 CloudFront 오디오 URL 동적 추출
    try:
        embed_url = f"https://suno.com/embed/{song_id}"
        embed_req = urllib.request.Request(embed_url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://suno.com/"
        })
        with urllib.request.urlopen(embed_req, timeout=10) as embed_resp:
            embed_html = embed_resp.read().decode("utf-8", errors="ignore")
            # CloudFront 또는 CDN 오디오 스트림 URL 정규식 추출
            cf_match = re.search(r'(https://[a-zA-Z0-9.-]+\.cloudfront\.net/[^\s"\'<>\\]+\.(?:m4a|mp3))', embed_html)
            if cf_match:
                stream_url = cf_match.group(1).replace("\\", "")
                print(f"[Suno 임베드 CloudFront 감지]: {stream_url}")
                dl_req = urllib.request.Request(stream_url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Referer": f"https://suno.com/embed/{song_id}"
                })
                with urllib.request.urlopen(dl_req, timeout=20) as dl_resp:
                    data = dl_resp.read()
                    if len(data) > 5000:
                        audio_bytes = data
                        print(f"[Suno CloudFront 다운로드 성공] {len(data)} bytes")
    except Exception as cf_err:
        last_err = cf_err
        print(f"[Suno 임베드 추출 실패, 레거시 CDN으로 폴백]: {cf_err}")

    # [2순위 폴백] 레거시 cdn1 / cdn2 직접 시도
    if not audio_bytes:
        candidate_urls = [
            f"https://cdn1.suno.ai/{song_id}.mp3",
            f"https://cdn2.suno.ai/{song_id}.mp3",
            f"https://audiopipe.suno.ai/?item_id={song_id}"
        ]
        headers_list = [
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": f"https://suno.com/song/{song_id}",
                "Origin": "https://suno.com"
            },
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://suno.com/"
            }
        ]

        for target_url in candidate_urls:
            for headers in headers_list:
                try:
                    url_req = urllib.request.Request(target_url, headers=headers)
                    with urllib.request.urlopen(url_req, timeout=15) as resp:
                        data = resp.read()
                        if len(data) > 5000:
                            audio_bytes = data
                            break
                except Exception as e:
                    last_err = e
                    continue
            if audio_bytes:
                break

    if not audio_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"Suno 음원을 가져오지 못했습니다. 링크가 비공개이거나 유효하지 않은지 확인해주세요. (오류: {last_err})"
        )

    # 3. 프로젝트 music 폴더에 자동 영구 저장
    clean_ep = re.sub(r'[^0-9]', '', req.episode_no).zfill(2) if req.episode_no else "01"
    project_dir = project_manager.get_project_dir()
    music_dir = project_dir / "music"
    music_dir.mkdir(parents=True, exist_ok=True)
    music_filename = f"{clean_ep}_음원.mp3"
    music_path = music_dir / music_filename
    with open(music_path, "wb") as f:
        f.write(audio_bytes)

    # 4. 원고(작품집_원고.md)의 노래 음원(music_file) 자동 동기화
    try:
        mgr = project_manager.get_active_manuscript_manager()
        works = mgr.load_works()
        target_ep = f"제{clean_ep}화"
        target_work = next((w for w in works if w.episode_no == target_ep or clean_ep in w.episode_no), None)
        if target_work:
            target_work.music_file = f"music/{music_filename}"
            mgr.save_work(target_work)
            print(f"[원고 노래 음원 동기화] {target_ep} music_file = music/{music_filename} 저장 완료")
    except Exception as sync_err:
        print(f"[원고 노래 음원 동기화 알림]: {sync_err}")

    active_id = project_manager.get_active_project_id()
    music_url = f"/projects/{active_id}/music/{music_filename}?t={int(time.time())}"

    return {
        "success": True,
        "song_id": song_id,
        "filename": music_filename,
        "music_url": music_url,
        "rel_path": f"music/{music_filename}",
        "message": f"[{req.episode_no}] Suno 노래 음원이 7회 다운로드 제한 없이 성공적으로 가져와졌습니다!"
    }

@app.post("/api/export_colab_notebook")
async def export_colab_notebook_endpoint(req: ColabNotebookRequest):
    """
    [3단계]를 동적으로 조립하여 특정 작품에 즉시 최적화된
    Google Colab YuE2 원클릭 작곡 노트북(.ipynb) 데이터 생성
    """
    try:
        clean_ep = re.sub(r'[^0-9]', '', req.episode_no).zfill(2) if req.episode_no else "01"
        clean_title = re.sub(r'[\s\\/*?:"<>|]', '_', req.title) if req.title else "노래음원"
        filename = f"{clean_ep}_{clean_title}_YuE2_원클릭.ipynb"

        info = project_manager.get_active_project_info()
        nb_data = build_yue2_notebook_dict(
            episode_no=req.episode_no,
            title=req.title,
            genre_prompt=req.genre_prompt or DEFAULT_GENRE_PROMPT,
            lyrics=req.lyrics or "",
            book_title=info.name
        )

        return {
            "success": True,
            "filename": filename,
            "notebook": nb_data
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/export_colab_image_notebook")
async def export_colab_image_notebook_endpoint(req: ColabImageNotebookRequest):
    """
    [3단계]를 동적으로 조립하여 특정 작품에 즉시 최적화된
    Google Colab SDXL Lightning 원클릭 삽화 생성 노트북(.ipynb) 데이터 생성
    """
    try:
        clean_ep = re.sub(r'[^0-9]', '', req.episode_no).zfill(2) if req.episode_no else "01"
        clean_title = re.sub(r'[\s\\/*?:"<>|]', '_', req.title) if req.title else "삽화"
        filename = f"{clean_ep}_{clean_title}_Colab_삽화_원클릭.ipynb"

        info = project_manager.get_active_project_info()
        nb_data = build_sdxl_image_notebook_dict(
            episode_no=req.episode_no,
            title=req.title,
            base_prompt=req.prompt or f"{req.title}의 정경",
            style_key=req.art_style or "watercolor",
            book_title=info.name,
            width=req.width or 768,
            height=req.height or 1024
        )

        return {
            "success": True,
            "filename": filename,
            "notebook": nb_data
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

# -------------------------------------------------------------
# 2원화 삽화 관리 API: 무료 원클릭 자동 생성 & 외부 생성 파일 업로드
# -------------------------------------------------------------
@app.post("/api/generate_image_free")
async def generate_image_free(req: GenerateFreeImageRequest):
    """
    API 키 없이 100% 무료로 고품질 서정 수채화 삽화를 자동 생성 (Pollinations / FLUX 엔진)
    """
    clean_ep = re.sub(r'[^0-9]', '', req.episode_no).zfill(2)
    filename = f"{clean_ep}_삽화.jpg"
    
    # 활성 프로젝트의 images 디렉토리
    images_dir = project_manager.get_active_images_dir()
    images_dir.mkdir(parents=True, exist_ok=True)
    target_path = images_dir / filename

    art_style = req.art_style or "watercolor"

    # 프롬프트 구성 (사용자가 수정한 프롬프트 우선, 없으면 기억 중심 기반 생성)
    prompt_text = req.prompt.strip() if req.prompt and req.prompt.strip() else ""
    if not prompt_text:
        from core.skill_pack import get_art_style_korean_instruction
        anchor = req.memory_anchor or req.title or "고향의 추억"
        style_info = get_art_style_korean_instruction(art_style)
        prompt_text = (
            f"{style_info['prefix_en']} of {anchor}, "
            f"warm nostalgic morning sunlight, peaceful empty space, textured paper margin"
        )

    seed = random.randint(1000, 999999)

    try:
        # 통합 3단계 고신뢰도 파이프라인으로 생성 및 300 DPI 저장
        img_bytes = await asyncio.to_thread(_generate_art_image_bytes, prompt_text, seed, art_style=art_style)
        ensure_300dpi_image(img_bytes, target_path)

        # 활성 원고(작품집_원고.md)의 해당 회차 이미지 파일명 자동 갱신
        mgr = project_manager.get_active_manuscript_manager()
        works = mgr.load_works()
        for w in works:
            if clean_ep in w.episode_no or w.episode_no.strip() == req.episode_no.strip():
                w.image_file = f"./images/{filename}"
                mgr.save_work(w)
                break
        try:
            build_canva_csv()
        except Exception:
            pass

        return {
            "success": True,
            "filename": filename,
            "image_url": f"/images/{filename}?t={seed}",
            "message": f"[{req.episode_no}] 무료 삽화가 성공적으로 생성되었습니다!"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"무료 이미지 생성 중 오류: {str(e)}")

def _clean_image_prompt(raw_prompt: str) -> str:
    """프롬프트 정제: 다중 공백 및 불필요한 특수문자 정리"""
    p = raw_prompt.strip()
    p = re.sub(r"\s+", " ", p).strip(" ,.")
    return p

def _generate_art_image_bytes(prompt_str: str, seed_val: int, art_style: str = "watercolor", ref_image_bytes: Optional[bytes] = None) -> bytes:
    """
    [모듈러 블록 아키텍처 기반 지능형 하이브리드 이미지 생성 파이프라인]
    공통 스킬(순백 10% 여백, 300 DPI, 글자 배제)은 단단히 유지하고,
    화풍 전환 시 이전 화풍 수식어를 100% 도려내어 지정된 화풍 전용 스킬 블록으로 완벽 교체 결합합니다.
    ref_image_bytes가 전달된 경우 기존 베이스 이미지를 유지한 채 지시 사항만 부분 수정(Image-to-Image)합니다.
    ★ 1순위 (최우선 직행) : Google Gemini Image (API 키 연결 시 한국어/정서 1위 엔진 즉시 가동)
    ★ 2순위 (무료 폴백) : Pollinations AI turbo/default (API 키 미등록자 또는 할당량 초과 시 오픈 서버)
    ★ 3순위 (보조 폴백) : Pollinations AI flux
    """
    from core.skill_pack import build_modular_art_prompt
    import io
    from PIL import Image
    
    # [모듈러 블록 아키텍처 조립]
    # 블록 A (선택된 화풍 전용) + 블록 B (오염 제거된 순수 정경) + 블록 C (공통 출판 규격)
    modular = build_modular_art_prompt(prompt_str, art_style=art_style)
    style_name_ko = modular["name_ko"]
    clean_scene = modular["clean_scene"]
    gemini_contents = modular["gemini_ko_content"]
    guarded_prompt = modular["guarded_en_prompt"]
    negative_en = modular["negative_en"]

    # ========================================================
    # ★ 1순위 (최우선) : Google Gemini Image (API 키 연결 시)
    # 지정 화풍 전용 블록과 순수 정경이 조립된 모듈러 지침으로 즉시 생성!
    # ========================================================
    api_key = os.getenv("GEMINI_API_KEY") or GEMINI_API_KEY
    if api_key and genai:
        print(f"[1순위 Google Gemini Image: 화풍={style_name_ko}] 모듈러 스킬 블록으로 [{style_name_ko}] 삽화를 생성합니다.")
        try:
            client = genai.Client(api_key=api_key)
            image_models = ["gemini-2.5-flash-image", "gemini-3.1-flash-image", "gemini-3-pro-image"]

            # [Image-to-Image] 기존 베이스 이미지가 제공된 경우 멀티모달 입력으로 함께 전달
            call_contents = [gemini_contents]
            if ref_image_bytes:
                try:
                    ref_pil = Image.open(io.BytesIO(ref_image_bytes))
                    call_contents = [ref_pil, f"Modify the attached base illustration according to this direction: {gemini_contents}"]
                    print(f"[Google Gemini Image-to-Image] 기존 베이스 이미지를 탑재하여 멀티모달 연속 수정을 수행합니다.")
                except Exception as pil_err:
                    print(f"[기존 이미지 멀티모달 변환 실패, 텍스트 전용으로 진행]: {pil_err}")

            for m_name in image_models:
                try:
                    res = client.models.generate_content(
                        model=m_name,
                        contents=call_contents
                    )
                    if res and res.candidates and res.candidates[0].content and res.candidates[0].content.parts:
                        for part in res.candidates[0].content.parts:
                            if hasattr(part, "inline_data") and part.inline_data and part.inline_data.data:
                                print(f"[Google Gemini 성공] {m_name} 모델로 [{style_name_ko}] 삽화 생성 완료 ({len(part.inline_data.data)} bytes)")
                                return part.inline_data.data
                except Exception as m_err:
                    print(f"[Gemini 모델 {m_name} 실패, 다음 시도]: {m_err}")
                    continue
        except Exception as gemini_err:
            print(f"[Gemini 1순위 일시 불가, 2순위 무료 오픈 AI로 자동 전환]: {gemini_err}")

    # ========================================================
    # ★ 2순위 (무료 폴백) : Pollinations AI
    # 화풍 고유의 Negative 프롬프트(타 화풍 배제)를 주입하여 화풍 혼입을 원천 차단
    # ========================================================
    print(f"[2순위 무료 오픈 AI 전환: 화풍={style_name_ko}] Pollinations 엔진으로 모듈러 블록 삽화를 생성합니다.")
    encoded = urllib.parse.quote(guarded_prompt)
    neg_param = urllib.parse.quote(negative_en)

    candidate_urls = [
        f"https://image.pollinations.ai/prompt/{encoded}?width=768&height=1024&nologo=true&seed={seed_val}&model=turbo&negative={neg_param}",
        f"https://image.pollinations.ai/prompt/{encoded}?width=768&height=1024&nologo=true&seed={seed_val}&negative={neg_param}",
        f"https://image.pollinations.ai/prompt/{encoded}?width=768&height=1024&nologo=true&seed={seed_val}&model=flux&negative={neg_param}"
    ]

    for api_url in candidate_urls:
        try:
            url_req = urllib.request.Request(api_url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            })
            with urllib.request.urlopen(url_req, timeout=25) as resp:
                data = resp.read()
                if len(data) > 1000:
                    print(f"[2순위 Pollinations 성공] 무료 오픈 AI로 [{style_name_ko}] 생성 완료 ({len(data)} bytes)")
                    return data
        except Exception as p_err:
            print(f"[Pollinations 일시 불가] {p_err}")
            continue

    # ========================================================
    # ★ 3순위 (보조 폴백) : 추가 무료 오픈 이미지 엔드포인트
    # ========================================================
    try:
        free_backup_url = f"https://image.pollinations.ai/prompt/{encoded}?width=768&height=1024&nologo=true&negative={neg_param}"
        url_req = urllib.request.Request(free_backup_url, headers={"User-Agent": "StoryBook-Studio/1.0"})
        with urllib.request.urlopen(url_req, timeout=20) as resp:
            data = resp.read()
            if len(data) > 1000:
                print(f"[3순위 무료 오픈 폴백 성공] [{style_name_ko}] ({len(data)} bytes)")
                return data
    except Exception as free_err:
        print(f"[3순위 무료 폴백 실패] {free_err}")

    raise RuntimeError(
        "이미지 생성 서버에 일시적인 연결 지연이 발생했습니다.\n"
        "💡 잠시 후 다시 시도하시거나 [🌊 Google Flow] 또는 [🚀 Colab (SDXL)]을 이용하시면 무제한 고화질로 즉시 생성하실 수 있습니다!"
    )

def _parse_base64_image(b64_str: Optional[str]) -> Optional[bytes]:
    """Base64 data URL 또는 raw base64 문자열을 안전하게 바이너리로 디코딩"""
    if not b64_str:
        return None
    try:
        data = b64_str.strip()
        if "," in data:
            data = data.split(",", 1)[1]
        raw = base64.b64decode(data)
        return raw if len(raw) > 50 else None
    except Exception as e:
        print(f"[참조 이미지 Base64 디코딩 실패]: {e}")
        return None

def _download_and_save_candidate(prompt_str: str, seed_val: int, file_path: Path, art_style: str = "watercolor", ref_image_bytes: Optional[bytes] = None):
    img_bytes = _generate_art_image_bytes(prompt_str, seed_val, art_style=art_style, ref_image_bytes=ref_image_bytes)
    ensure_300dpi_image(img_bytes, file_path)

@app.post("/api/generate_image_candidates")
async def generate_image_candidates(req: GenerateImageCandidatesRequest):
    """
    무료 한도(Rate Limit) 절약 및 초고속 생성을 위해 단 1장의 최적 서정 삽화를 즉시 생성하고 원고에 자동 반영합니다.
    선택된 화풍(수묵담채, 파스텔, 스케치, 유화, 수채화)을 완벽히 반영하여 고품질 삽화를 생성합니다.
    참조 사진(reference_image)이 전달된 경우 멀티모달 비전 분석을 통해 사진 구도와 피사체를 해당 화풍으로 재창작하거나,
    direct_use_photo=True인 경우 해당 사진 자체를 300 DPI 순백 여백 보정하여 바로 시안으로 사용합니다.
    """
    try:
        clean_ep = re.sub(r'[^0-9]', '', req.episode_no).zfill(2)
        images_dir = project_manager.get_active_images_dir()
        images_dir.mkdir(parents=True, exist_ok=True)
        art_style = req.art_style or "watercolor"

        ref_bytes = _parse_base64_image(req.reference_image)

        # [방법 1: 연속 편집 모드 (Image-to-Image)]
        # 사용자가 수동 사진을 첨부하지 않았으나, 현재 그림 유지 부분 수정(use_current_as_base)이 활성화되어 있고 가이드가 있는 경우
        is_refining_existing = False
        if not ref_bytes and req.use_current_as_base and custom_guide:
            cand_files = []
            if req.base_image_filename:
                cand_files.append(images_dir / req.base_image_filename)
            cand_files.append(images_dir / f"{clean_ep}_생성후보.jpg")
            cand_files.append(images_dir / f"{clean_ep}_삽화.jpg")
            
            for c_path in cand_files:
                if c_path.exists() and c_path.stat().st_size > 1000:
                    try:
                        ref_bytes = c_path.read_bytes()
                        is_refining_existing = True
                        print(f"[{req.episode_no}화 Image-to-Image 연속 편집] 기존 그림({c_path.name})을 베이스 이미지로 자동 탑재하여 인물/구도를 유지한 채 부분 수정을 수행합니다.")
                        break
                    except Exception as b_err:
                        print(f"기존 이미지 바이트 로드 실패: {b_err}")

        # [옵션 B] 사진 자체를 300 DPI 순백 여백 보정 후 바로 시안으로 등록
        if req.direct_use_photo and ref_bytes and not is_refining_existing:
            seed = random.randint(100000, 999999)
            filename = f"{clean_ep}_생성후보.jpg"
            target_path = images_dir / filename
            print(f"[{req.episode_no}화] 첨부 사진 자체를 300 DPI 여백 보정하여 바로 시안 등록 ({len(ref_bytes)} bytes)")
            ensure_300dpi_image(ref_bytes, target_path)
            return {
                "success": True,
                "episode_no": req.episode_no,
                "filename": filename,
                "used_prompt": "사용자 첨부 사진 직접 변환 (300 DPI 순백 여백 보정 적용)",
                "image_url": f"/images/{filename}?t={seed}",
                "message": f"[{req.episode_no}] 첨부하신 사진이 300 DPI 출판용 규격과 순백 여백으로 보정되어 등록되었습니다."
            }

        base_prompt = req.prompt.strip() if req.prompt and req.prompt.strip() else ""

        # 모듈러 블록 아키텍처를 통한 화풍 전환 및 오염 제거
        from core.skill_pack import build_modular_art_prompt, strip_style_contamination
        
        mgr = project_manager.get_active_manuscript_manager()
        works = mgr.load_works()
        target_work = next((w for w in works if clean_ep in w.episode_no or w.episode_no.strip() == req.episode_no.strip()), None)

        p_title = req.title or (target_work.title if target_work else "고향의 추억")
        p_body = (target_work.poem_body if target_work and target_work.poem_body else "")
        p_memory = req.memory_anchor or (target_work.memory_anchor if target_work else "")
        p_direction = (target_work.art_direction if target_work and target_work.art_direction else "")

        # 이전 화풍 오염 감지 및 블록 전환 판단
        other_styles = {
            "watercolor": ["수묵", "파스텔", "스케치", "유화", "ink_wash", "pastel", "sketch", "oil_painting"],
            "ink_wash": ["수채화", "파스텔", "스케치", "유화", "watercolor", "pastel", "sketch", "oil_painting"],
            "pastel": ["수채화", "수묵", "스케치", "유화", "watercolor", "ink_wash", "sketch", "oil_painting"],
            "sketch": ["수채화", "수묵", "파스텔", "유화", "watercolor", "ink_wash", "pastel", "oil_painting"],
            "oil_painting": ["수채화", "수묵", "파스텔", "스케치", "watercolor", "ink_wash", "pastel", "sketch"]
        }
        mismatch_keywords = other_styles.get(art_style, [])
        has_mismatched_style = any(kw in base_prompt for kw in mismatch_keywords)

        # 정경 묘사가 비어있거나 화풍이 바뀌었거나 가이드가 있는 경우 서정 정경 생성
        if custom_guide or ref_bytes or not base_prompt or len(base_prompt) < 15 or has_mismatched_style:
            ref_msg = " + [기존 그림 기반 연속 수정]" if is_refining_existing else (" + [참조 사진 비전 분석]" if ref_bytes else "")
            print(f"[{req.episode_no}화 모듈러 블록 조립: 화풍={art_style}] 이전 화풍을 완전히 걷어내고 [{art_style}] 전용 스킬 블록으로 전환합니다.{ref_msg}")

            api_key = os.getenv("GEMINI_API_KEY") or GEMINI_API_KEY
            if ref_bytes:
                raw_scene_prompt = poetic_engine.generate_art_prompt_with_gemini(
                    title=p_title,
                    poem_body=p_body,
                    core_memory=p_memory,
                    sensory_details=p_direction,
                    style_mode="literal",
                    art_style=art_style,
                    custom_guide=custom_guide,
                    reference_image_bytes=ref_bytes,
                    is_refining_existing=is_refining_existing
                )
            else:
                raw_scene_prompt = poetic_engine.generate_korean_art_prompt(
                    title=p_title,
                    poem_body=p_body,
                    core_memory=p_memory,
                    sensory_details=p_direction,
                    style_mode="literal",
                    art_style=art_style,
                    custom_guide=custom_guide,
                    api_key=api_key
                )
        else:
            raw_scene_prompt = base_prompt

        # [모듈러 블록 아키텍처 조립기 최종 가동]
        # 블록 A (선택된 화풍 전용 블록) + 블록 B (이전 화풍 오염이 도려내진 순수 정경) + 블록 C (공통 출판 규격)
        modular = build_modular_art_prompt(
            raw_prompt=raw_scene_prompt,
            art_style=art_style,
            custom_guide=custom_guide,
            title=p_title,
            memory_anchor=p_memory
        )
        final_used_prompt = modular["display_ko_prompt"]

        # 단일 최적 시안 생성 (미리보기 확인 후 [삽입] 클릭 시에만 원고에 반영)
        seed = random.randint(100000, 999999)
        filename = f"{clean_ep}_생성후보.jpg"
        target_path = images_dir / filename

        # 단 1회 초고속 생성 (300 DPI 규격 보정, 모듈러 화풍 스킬 블록 적용, Image-to-Image 바이트 전달)
        await asyncio.to_thread(_download_and_save_candidate, modular["clean_scene"], seed, target_path, art_style=art_style, ref_image_bytes=ref_bytes)

        msg_style = "기존 그림의 인물과 구도를 유지하며 부분 수정한" if is_refining_existing else f"[{modular['name_ko']}] 전용 스킬 블록으로"
        return {
            "success": True,
            "episode_no": req.episode_no,
            "filename": filename,
            "used_prompt": final_used_prompt,
            "image_url": f"/images/{filename}?t={seed}",
            "message": f"[{req.episode_no}] {msg_style} 새 삽화 시안이 생성되었습니다.",
            # 하위 호환 데이터
            "candidate_a": {
                "id": "A",
                "name": "생성 시안",
                "filename": filename,
                "image_url": f"/images/{filename}?t={seed}"
            }
        }
    except Exception as e:
        err_msg = str(e)
        if "402" in err_msg or "한도" in err_msg:
            raise HTTPException(
                status_code=429,
                detail="무료 이미지 서버(Pollinations)의 시간당 무료 한도(Rate Limit)에 도달했습니다. 바로 옆의 [🌊 Google Flow] 또는 [🚀 Colab (SDXL)]을 이용하시면 사용량 제한 없이 즉시 생성하실 수 있습니다!"
            )
        raise HTTPException(status_code=500, detail=f"삽화 생성 중 오류: {err_msg}")

@app.post("/api/select_image_candidate")
async def select_image_candidate(req: SelectImageCandidateRequest):
    """
    모달 팝업에서 사용자가 선택한 시안을 최종 공식 삽화(1부 본 삽화 또는 2부 연작 삽화)로 확정 반영합니다.
    """
    clean_ep = re.sub(r'[^0-9]', '', req.episode_no).zfill(2)
    images_dir = project_manager.get_active_images_dir()
    cand_path = images_dir / req.candidate_filename

    if not cand_path.exists():
        raise HTTPException(status_code=404, detail="선택한 시안 이미지 파일을 찾을 수 없습니다.")

    is_part2 = (req.target_slot == "part2")
    final_filename = f"{clean_ep}_삽화_후반.jpg" if is_part2 else f"{clean_ep}_삽화.jpg"
    final_path = images_dir / final_filename

    # 선택된 시안을 최종 삽화 파일로 복사
    shutil.copyfile(cand_path, final_path)

    # 원고(작품집_원고.md)의 해당 회차 이미지 파일명 및 연출 모드 갱신
    mgr = project_manager.get_active_manuscript_manager()
    works = mgr.load_works()
    for w in works:
        if clean_ep in w.episode_no or w.episode_no.strip() == req.episode_no.strip():
            if is_part2:
                w.image_file_2 = f"./images/{final_filename}"
                w.part2_mode = "image"
                w.layout_mode = "multi_page"
                # 4P 레이아웃 설정이 있으면 슬롯과 3면 이미지 설정도 완벽히 동기화
                cfg = dict(w.layout_config) if getattr(w, 'layout_config', None) else {
                    "page_count": 4,
                    "slots": ["image", "text", "image", "text"],
                    "image_settings": {
                        "page_1": {"mode": "image", "file": w.image_file or ""},
                        "page_3": {"mode": "image", "file": f"./images/{final_filename}"}
                    }
                }
                cfg["page_count"] = 4
                slots = list(cfg.get("slots", ["image", "text", "image", "text"]))
                while len(slots) < 4:
                    slots.append("image" if len(slots) % 2 == 0 else "text")
                slots[2] = "image"
                cfg["slots"] = slots
                img_settings = dict(cfg.get("image_settings", {}))
                img_settings["page_3"] = {"mode": "image", "file": f"./images/{final_filename}"}
                cfg["image_settings"] = img_settings
                w.layout_config = cfg
            else:
                w.image_file = f"./images/{final_filename}"
                if getattr(w, 'layout_config', None):
                    cfg = dict(w.layout_config)
                    img_settings = dict(cfg.get("image_settings", {}))
                    img_settings["page_1"] = {"mode": "image", "file": f"./images/{final_filename}"}
                    cfg["image_settings"] = img_settings
                    w.layout_config = cfg
            mgr.save_work(w)
            break

    try:
        build_canva_csv()
    except Exception:
        pass

    now_t = int(time.time())
    slot_label = "2부 연작 삽화(4면)" if is_part2 else "1부 본 삽화(2면)"
    return {
        "success": True,
        "filename": final_filename,
        "target_slot": req.target_slot or "part1",
        "image_url": f"/images/{final_filename}?t={now_t}",
        "message": f"[{req.episode_no}] 선택하신 그림이 {slot_label}로 성공적으로 반영되었습니다!"
    }

@app.post("/api/upload_image")
async def upload_image(
    file: UploadFile = File(...),
    episode_no: str = Form(...),
    target_slot: str = Form("main")
):
    """
    외부 생성 이미지를 드래그 앤 드롭 또는 파일 선택으로 업로드 (main 또는 4P 모드 part2 슬롯)
    """
    clean_ep = re.sub(r'[^0-9]', '', episode_no).zfill(2)
    filename = f"{clean_ep}_삽화_후반.jpg" if target_slot == "part2" else f"{clean_ep}_삽화.jpg"

    images_dir = project_manager.get_active_images_dir()
    images_dir.mkdir(parents=True, exist_ok=True)
    target_path = images_dir / filename

    try:
        contents = await file.read()
        if len(contents) == 0:
            raise HTTPException(status_code=400, detail="빈 파일입니다.")

        # 300 DPI 출판 인쇄 규격 자동 보정 적용
        opt_res = ensure_300dpi_image(contents, target_path)

        # 활성 원고 및 CSV 자동 갱신
        mgr = project_manager.get_active_manuscript_manager()
        works = mgr.load_works()
        for w in works:
            if clean_ep in w.episode_no or w.episode_no.strip() == episode_no.strip():
                if target_slot == "part2":
                    w.image_file_2 = f"./images/{filename}"
                    w.part2_mode = "image"
                    w.layout_mode = "multi_page"
                    cfg = dict(w.layout_config) if getattr(w, 'layout_config', None) else {
                        "page_count": 4,
                        "slots": ["image", "text", "image", "text"],
                        "image_settings": {
                            "page_1": {"mode": "image", "file": w.image_file or ""},
                            "page_3": {"mode": "image", "file": f"./images/{filename}"}
                        }
                    }
                    cfg["page_count"] = 4
                    slots = list(cfg.get("slots", ["image", "text", "image", "text"]))
                    while len(slots) < 4:
                        slots.append("image" if len(slots) % 2 == 0 else "text")
                    slots[2] = "image"
                    cfg["slots"] = slots
                    img_settings = dict(cfg.get("image_settings", {}))
                    img_settings["page_3"] = {"mode": "image", "file": f"./images/{filename}"}
                    cfg["image_settings"] = img_settings
                    w.layout_config = cfg
                else:
                    w.image_file = f"./images/{filename}"
                    if getattr(w, 'layout_config', None):
                        cfg = dict(w.layout_config)
                        img_settings = dict(cfg.get("image_settings", {}))
                        img_settings["page_1"] = {"mode": "image", "file": f"./images/{filename}"}
                        cfg["image_settings"] = img_settings
                        w.layout_config = cfg
                mgr.save_work(w)
                break
        try:
            build_canva_csv()
        except Exception:
            pass

        t_rand = random.randint(1000, 9999)
        slot_label = "2부 연작 삽화" if target_slot == "part2" else "삽화"
        return {
            "success": True,
            "filename": filename,
            "target_slot": target_slot,
            "image_url": f"/images/{filename}?t={t_rand}",
            "message": f"[{episode_no}] {slot_label}가 성공적으로 등록되었습니다!"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이미지 업로드 실패: {str(e)}")

@app.post("/api/generate_part2_image")
async def generate_part2_image(req: GeneratePart2ImageRequest):
    """
    4P 조판 시 2부(후반부) 좌측면에 배치할 연작 수채화 삽화를 시의 후반부 정경에 맞춰 무료 자동 생성 (미리보기 후 승인 시 반영)
    """
    try:
        clean_ep = re.sub(r'[^0-9]', '', req.episode_no).zfill(2)
        filename = f"{clean_ep}_생성후보_2부.jpg"
        art_style = req.art_style or "watercolor"

        images_dir = project_manager.get_active_images_dir()
        images_dir.mkdir(parents=True, exist_ok=True)
        target_path = images_dir / filename

        ref_bytes = _parse_base64_image(req.reference_image)

        # [방법 1: 2부 연속 편집 모드 (Image-to-Image)]
        is_refining_existing = False
        custom_guide = (req.custom_guide or "").strip()
        if not ref_bytes and req.use_current_as_base and custom_guide:
            cand_files = []
            if req.base_image_filename:
                cand_files.append(images_dir / req.base_image_filename)
            cand_files.append(images_dir / f"{clean_ep}_생성후보_2부.jpg")
            cand_files.append(images_dir / f"{clean_ep}_삽화_후반.jpg")
            for c_path in cand_files:
                if c_path.exists() and c_path.stat().st_size > 1000:
                    try:
                        ref_bytes = c_path.read_bytes()
                        is_refining_existing = True
                        print(f"[{req.episode_no}화 2부 Image-to-Image] 기존 2부 그림({c_path.name})을 베이스로 부분 수정을 수행합니다.")
                        break
                    except Exception as b_err:
                        print(f"2부 기존 이미지 로드 실패: {b_err}")

        # [옵션 B] 사진 자체를 300 DPI 순백 여백 보정 후 바로 2부 시안으로 등록
        if req.direct_use_photo and ref_bytes and not is_refining_existing:
            seed = random.randint(100000, 999999)
            ensure_300dpi_image(ref_bytes, target_path)
            return {
                "success": True,
                "episode_no": req.episode_no,
                "filename": filename,
                "target_slot": "part2",
                "image_url": f"/images/{filename}?t={seed}",
                "message": f"[{req.episode_no}] 첨부하신 사진이 300 DPI 출판용 규격으로 보정되어 2부 연작 삽화 시안으로 등록되었습니다."
            }

        mgr = project_manager.get_active_manuscript_manager()
        works = mgr.load_works()
        target_work = None
        for w in works:
            if clean_ep in w.episode_no or w.episode_no.strip() == req.episode_no.strip():
                target_work = w
                break

        prompt_text = (req.prompt or "").strip()
        if custom_guide or ref_bytes or not prompt_text:
            # ★ 묘책: 시의 후반부(Part 2) 본문을 정밀 분석한 전용 연작 서정 프롬프트 자동 조립!
            if target_work:
                prompt_text = poetic_engine.generate_sequel_image_prompt(
                    title=target_work.title,
                    poem_body=target_work.poem_body or "",
                    core_memory=target_work.memory_anchor or "",
                    sensory_details="",
                    art_style=art_style,
                    custom_guide=custom_guide
                )
            else:
                prompt_text = (
                    "authentic Korean lyric transparent watercolor painting, intimate nostalgic midnight room, "
                    "warm kerosene lamp glowing in chilly night breeze, on pure clean white paper background, wide 10% white margin, "
                    "soft vignetting, delicate brush textures, masterpiece, no text, no frame"
                )

        seed = random.randint(100000, 999999)

        # 다단계 무료 폴백 엔진 & 300 DPI 사방 10% 수채화 블러 비네팅 마스크 자동 적용 (ref_image_bytes 연동)
        await asyncio.to_thread(_download_and_save_candidate, prompt_text, seed, target_path, art_style=art_style, ref_image_bytes=ref_bytes)

        # 원고 즉시 덮어쓰기는 수행하지 않음 (미리보기 창에서 사용자가 [삽화로 삽입]을 누를 때 반영)
        return {
            "success": True,
            "episode_no": req.episode_no,
            "filename": filename,
            "target_slot": "part2",
            "image_url": f"/images/{filename}?t={seed}",
            "message": f"[{req.episode_no}] 2부 연작 삽화가 생성되었습니다. 미리보기 창에서 확인하세요."
        }
    except Exception as e:
        err_msg = str(e)
        if "402" in err_msg or "한도" in err_msg:
            raise HTTPException(
                status_code=429,
                detail="무료 이미지 서버(Pollinations)의 시간당 무료 한도(Rate Limit)에 도달했습니다. 잠시 후 다시 시도하시거나 [🌊 Google Flow]를 이용해주세요."
            )
        raise HTTPException(status_code=500, detail=f"2부 삽화 생성 실패: {err_msg}")

@app.get("/api/export_csv")
async def export_csv():
    info = project_manager.get_active_project_info()
    count, path = build_canva_csv()
    if not path.exists():
        raise HTTPException(status_code=404, detail="CSV 파일을 생성할 수 없습니다.")
    
    safe_name = urllib.parse.quote(f"{info.name}_본문데이터.csv")
    return FileResponse(
        path=str(path),
        filename=f"{info.name}_본문데이터.csv",
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_name}"}
    )

@app.get("/api/book_spec")
async def get_book_spec(pages: int = 80):
    return calculate_spine_and_cover(pages)

@app.get("/api/images")
async def get_images_status():
    return inspect_images()

@app.post("/api/images/enhance_300dpi")
async def enhance_all_images_300dpi():
    """
    현재 활성 시집 폴더 내의 모든 이미지를 검사하여 300 DPI 미만인 경우 일괄 자동 보정
    """
    images_dir = project_manager.get_active_images_dir()
    if not images_dir.exists():
        return {"success": True, "count": 0, "message": "등록된 이미지가 없습니다."}

    supported_exts = {".png", ".jpg", ".jpeg", ".webp"}
    image_files = sorted([f for f in images_dir.iterdir() if f.suffix.lower() in supported_exts])
    
    enhanced_count = 0
    results = []
    for img_path in image_files:
        try:
            res = ensure_300dpi_image(img_path, img_path)
            if res.get("was_enhanced"):
                enhanced_count += 1
            results.append(res)
        except Exception as e:
            results.append({"path": str(img_path), "success": False, "error": str(e)})

    return {
        "success": True,
        "total_images": len(image_files),
        "enhanced_count": enhanced_count,
        "message": f"총 {len(image_files)}개 이미지 중 {enhanced_count}개 이미지가 300 DPI 규격으로 자동 보정되었습니다."
    }

@app.get("/api/export_pdf")
async def export_pdf():
    try:
        info = project_manager.get_active_project_info()
        pdf_path = build_pdf_book()
        if not pdf_path.exists():
            raise HTTPException(status_code=500, detail="PDF 파일 생성에 실패했습니다.")
        
        safe_name = urllib.parse.quote(f"{info.name}_완성본.pdf")
        return FileResponse(
            path=str(pdf_path),
            filename=f"{info.name}_완성본.pdf",
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_name}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF 생성 오류: {str(e)}")

# -------------------------------------------------------------
# 부크크(Bookk) POD 출판 규격 300DPI 인쇄 PDF API
# -------------------------------------------------------------
@app.get("/api/bookk/formats")
async def get_bookk_formats():
    """부크크 지원 판형 목록 및 상세 규격 반환"""
    return {"formats": BOOKK_FORMATS}

@app.get("/api/bookk/export_interior")
async def export_bookk_interior(format_key: str = "a5", paper_type: str = "white_100g"):
    """부크크 300DPI 사방 3mm 도련 및 20mm 제본 여백 내지 완제본 PDF 생성 및 다운로드"""
    try:
        info = project_manager.get_active_project_info()
        p_dir = project_manager.get_project_dir()
        builder = BookkPDFBuilder(format_key=format_key, paper_type=paper_type)

        format_label = "사륙판" if format_key == "b6_mod" else "국판"
        out_filename = f"{info.name}_부크크_내지_{format_label}_300DPI.pdf"
        out_path = p_dir / out_filename

        res = builder.build_interior_pdf(output_path=out_path)
        if not out_path.exists():
            raise HTTPException(status_code=500, detail="부크크 내지 PDF 생성에 실패했습니다.")

        safe_name = urllib.parse.quote(out_filename)
        return FileResponse(
            path=str(out_path),
            filename=out_filename,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_name}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"부크크 내지 PDF 생성 오류: {str(e)}")

@app.get("/api/bookk/export_cover")
async def export_bookk_cover(format_key: str = "b6_mod", paper_type: str = "white_100g", total_pages: int = 0):
    """부크크 표지 펼침면(뒤표지 + 책등 세네카 + 앞표지 + 도련 3mm) PDF 생성 및 다운로드"""
    try:
        info = project_manager.get_active_project_info()
        p_dir = project_manager.get_project_dir()
        builder = BookkPDFBuilder(format_key=format_key, paper_type=paper_type)

        # 총 페이지 수 자동 산출 (미지정 또는 기본값일 때)
        if total_pages <= 0 or total_pages == 28:
            episodes = manuscript_manager.list_episodes()
            # 본문(작품당 2P) + 권두(도비라/서문/목차) + 권말(맺음말/판권지) = 최소 40~80쪽 표준
            actual_pages = len(episodes) * 2 + 8
            total_pages = max(actual_pages, 80)

        format_label = "사륙판" if format_key == "b6_mod" else "국판"
        out_filename = f"{info.name}_부크크_표지_{format_label}_300DPI.pdf"
        out_path = p_dir / out_filename

        res = builder.build_cover_spread_pdf(output_path=out_path, total_pages=total_pages)
        if not out_path.exists():
            raise HTTPException(status_code=500, detail="부크크 표지 PDF 생성에 실패했습니다.")

        safe_name = urllib.parse.quote(out_filename)
        return FileResponse(
            path=str(out_path),
            filename=out_filename,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_name}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"부크크 표지 PDF 생성 오류: {str(e)}")


# -------------------------------------------------------------
# 시집 출판 본문 외 구성 요소 (Front & Back Matter) 관리 API
# -------------------------------------------------------------
class BookExtrasSaveRequest(BaseModel):
    prologue: Optional[str] = ""
    epilogue: Optional[str] = ""
    back_cover_blurb: Optional[str] = ""
    cover_image: Optional[str] = ""
    publisher: Optional[str] = "부크크 (Bookk) 자가출판"
    published_date: Optional[str] = ""
    price: Optional[str] = "13,000원"
    isbn: Optional[str] = ""

class BookExtrasGenerateRequest(BaseModel):
    target: str  # "prologue" | "epilogue" | "back_cover_blurb"

@app.get("/api/book_extras")
async def get_book_extras():
    """현재 활성 시집의 본문 외 출판 구성 요소(서문, 에필로그, 뒷표지카피, 판권) 조회"""
    try:
        info = project_manager.get_active_project_info()
        images_dir = project_manager.get_active_images_dir()
        
        # 프로젝트 내 사용 가능한 삽화 목록
        available_images = []
        if images_dir.exists():
            for f in images_dir.glob("*.*"):
                if f.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]:
                    available_images.append(f.name)
            available_images.sort()

        return {
            "success": True,
            "extras": {
                "prologue": getattr(info, 'prologue', ''),
                "epilogue": getattr(info, 'epilogue', ''),
                "back_cover_blurb": getattr(info, 'back_cover_blurb', ''),
                "cover_image": getattr(info, 'cover_image', ''),
                "publisher": getattr(info, 'publisher', '부크크 (Bookk) 자가출판'),
                "published_date": getattr(info, 'published_date', ''),
                "price": getattr(info, 'price', '13,000원'),
                "isbn": getattr(info, 'isbn', '')
            },
            "project_name": info.name,
            "project_subtitle": info.subtitle,
            "project_author": info.author,
            "available_images": available_images
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"출판 데이터 조회 실패: {str(e)}")

@app.post("/api/book_extras/save")
async def save_book_extras(req: BookExtrasSaveRequest):
    """시집의 본문 외 출판 구성 요소(서문, 에필로그, 뒷표지카피, 판권 정보) 저장"""
    try:
        info = project_manager.update_book_extras(None, req.dict())
        return {"success": True, "message": "출판 구성 요소가 안전하게 저장되었습니다.", "info": asdict(info)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"출판 데이터 저장 실패: {str(e)}")

@app.post("/api/book_extras/generate")
async def generate_book_extras(req: BookExtrasGenerateRequest):
    """수록된 시와 시집 기획 의도를 분석하여 AI 시인의 말 / 맺음말 / 뒷표지 카피 자동 생성"""
    try:
        info = project_manager.get_active_project_info()
        mgr = project_manager.get_active_manuscript_manager()
        works = mgr.load_works()

        if req.target == "prologue":
            generated_text = publishing_copier.generate_prologue(info, works)
        elif req.target == "epilogue":
            generated_text = publishing_copier.generate_epilogue(info, works)
        elif req.target == "back_cover_blurb":
            generated_text = publishing_copier.generate_back_cover_blurb(info, works)
        else:
            raise HTTPException(status_code=400, detail="유효하지 않은 생성 요청 대상입니다.")

        return {
            "success": True,
            "target": req.target,
            "generated_text": generated_text
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 출판 문구 생성 실패: {str(e)}")

@app.get("/api/canva/export_publishing_csv")
async def export_canva_publishing_csv():
    """Canva 표지/서문/목차/에필로그/판권지 일괄 바인딩용 메타데이터 CSV 다운로드"""
    try:
        info = project_manager.get_active_project_info()
        p_dir = project_manager.get_project_dir()
        out_path = p_dir / f"{info.name}_출판구성데이터.csv"
        build_canva_publishing_metadata_csv(output_file=out_path)

        safe_name = urllib.parse.quote(out_path.name)
        return FileResponse(
            path=str(out_path),
            filename=out_path.name,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_name}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Canva 출판 메타데이터 CSV 생성 실패: {str(e)}")


# -------------------------------------------------------------
# 완성 원고 통째 일괄 가져오기 (Bulk Import) 파이프라인
# -------------------------------------------------------------
def clean_poem_title(raw: str, fallback_index: int = 1) -> str:
    """제목 앞에 붙은 번호, 기호 등을 깔끔하게 제거하고 순수 제목만 추출"""
    t = re.sub(r'^[#\s]*', '', raw)
    t = re.sub(r'^(?:\[?\s*제?\s*\d+\s*[화편회]?\s*\]?|\d+[\.\)]|\d+\s*[-:]|\(\d+\))\s*', '', t).strip()
    t = t.lstrip('.-: ').strip()
    return t if t else f"작품 {fallback_index}"

def parse_bulk_manuscript(raw_text: str, start_index: int = 1) -> List[Dict[str, Any]]:
    """
    다양한 형태의 완성 시 원고(마크다운, 번호 목록, 빈 줄 구분 자유 형식)를
    자동으로 개별 시(PoemWork 구조)로 스마트하게 파싱합니다.
    """
    raw_text = raw_text.replace("\r\n", "\n").strip()
    if not raw_text:
        return []

    items = []

    # 1. 마크다운 '## ' 헤더
    if re.search(r'(?m)^##\s+', raw_text):
        chunks = re.split(r'(?m)^##\s+', raw_text)
        chunks = [c.strip() for c in chunks if c.strip()]
        for idx, chunk in enumerate(chunks, start=start_index):
            lines = chunk.split("\n", 1)
            clean_title = clean_poem_title(lines[0].strip(), idx)

            body = lines[1].strip() if len(lines) > 1 else ""
            if "### [시 본문]" in body:
                body = body.split("### [시 본문]", 1)[1].strip()
            elif re.search(r'(?m)^###\s+', body):
                body = re.split(r'(?m)^###\s+', body)[-1].strip()

            body_lines = [l for l in body.split("\n") if not re.match(r'^\s*-\s*\*\*', l)]
            clean_body = "\n".join(body_lines).strip()

            ep_str = f"제{str(idx).zfill(2)}화"
            first_line = clean_body.split("\n")[0] if clean_body else clean_title
            anchor = first_line[:40].strip()
            prompt = f"Korean lyric watercolor illustration, {clean_title}, soft warm morning light, poetic negative space, delicate ink wash style, masterpiece, no text, 300 dpi"

            items.append({
                "episode_no": ep_str,
                "title": clean_title,
                "poem_body": clean_body,
                "memory_anchor": anchor,
                "suggested_prompt": prompt
            })

    # 2. 구분선 (---, ===, ***)
    elif re.search(r'(?m)^(?:\-{3,}|\={3,}|\*{3,})\s*$', raw_text):
        chunks = re.split(r'(?m)^(?:\-{3,}|\={3,}|\*{3,})\s*$', raw_text)
        chunks = [c.strip() for c in chunks if c.strip()]
        cur_idx = start_index
        for chunk in chunks:
            lines = [l.strip() for l in chunk.split("\n") if l.strip()]
            if not lines:
                continue
            title_candidate = clean_poem_title(lines[0], cur_idx)
            clean_body = "\n".join(lines[1:]).strip() if len(lines) > 1 else lines[0]
            ep_str = f"제{str(cur_idx).zfill(2)}화"
            first_body_line = clean_body.split("\n")[0] if clean_body else title_candidate
            anchor = first_body_line[:40].strip()
            prompt = f"Korean lyric watercolor illustration, {title_candidate}, soft warm morning light, poetic negative space, delicate ink wash style, masterpiece, no text, 300 dpi"
            items.append({
                "episode_no": ep_str,
                "title": title_candidate,
                "poem_body": clean_body,
                "memory_anchor": anchor,
                "suggested_prompt": prompt
            })
            cur_idx += 1

    # 3. 빈 줄 2개 이상(\n\s*\n\s*\n)으로 작품 간격이 넓게 구분된 경우
    elif re.search(r'\n\s*\n\s*\n', raw_text):
        chunks = re.split(r'\n\s*\n\s*\n+', raw_text)
        chunks = [c.strip() for c in chunks if c.strip()]
        cur_idx = start_index
        for chunk in chunks:
            lines = chunk.split("\n")
            non_empty = [l.strip() for l in lines if l.strip()]
            if not non_empty:
                continue
            title_candidate = clean_poem_title(non_empty[0], cur_idx)
            idx_in_chunk = lines.index(non_empty[0])
            clean_body = "\n".join(lines[idx_in_chunk + 1:]).strip()
            if not clean_body:
                clean_body = non_empty[0]

            ep_str = f"제{str(cur_idx).zfill(2)}화"
            first_body_line = clean_body.split("\n")[0] if clean_body else title_candidate
            anchor = first_body_line[:40].strip()
            prompt = f"Korean lyric watercolor illustration, {title_candidate}, soft warm morning light, poetic negative space, delicate ink wash style, masterpiece, no text, 300 dpi"
            items.append({
                "episode_no": ep_str,
                "title": title_candidate,
                "poem_body": clean_body,
                "memory_anchor": anchor,
                "suggested_prompt": prompt
            })
            cur_idx += 1

    # 4. 일반 빈 줄 1개 이상 구분
    else:
        chunks = re.split(r'\n{2,}', raw_text)
        chunks = [c.strip() for c in chunks if c.strip()]
        cur_idx = start_index
        for chunk in chunks:
            lines = [l.strip() for l in chunk.split("\n") if l.strip()]
            if not lines:
                continue
            title_candidate = clean_poem_title(lines[0], cur_idx)
            clean_body = "\n".join(lines[1:]).strip() if len(lines) > 1 else lines[0]
            ep_str = f"제{str(cur_idx).zfill(2)}화"
            first_body_line = clean_body.split("\n")[0] if clean_body else title_candidate
            anchor = first_body_line[:40].strip()
            prompt = f"Korean lyric watercolor illustration, {title_candidate}, soft warm morning light, poetic negative space, delicate ink wash style, masterpiece, no text, 300 dpi"
            items.append({
                "episode_no": ep_str,
                "title": title_candidate,
                "poem_body": clean_body,
                "memory_anchor": anchor,
                "suggested_prompt": prompt
            })
            cur_idx += 1

    return items

@app.post("/api/preview_bulk_manuscript")
async def preview_bulk_manuscript(req: BulkParseRequest):
    """붙여넣은 원고를 분석하여 분리된 시 목록을 미리보기로 반환"""
    items = parse_bulk_manuscript(req.raw_text)
    return {
        "success": True,
        "count": len(items),
        "items": items
    }

@app.post("/api/import_bulk_manuscript")
async def import_bulk_manuscript(req: BulkImportRequest):
    """
    분석된 완성 원고를 현재 활성 프로젝트에 일괄 저장 및 반영
    """
    mgr = project_manager.get_active_manuscript_manager()
    existing_works = mgr.load_works() if req.mode == "append" else []
    start_index = len(existing_works) + 1 if req.mode == "append" else 1

    parsed_items = parse_bulk_manuscript(req.raw_text, start_index=start_index)
    if not parsed_items:
        raise HTTPException(status_code=400, detail="유효한 시 본문을 찾을 수 없습니다. 원고 텍스트를 확인해주세요.")

    new_works: List[PoemWork] = list(existing_works)
    for p in parsed_items:
        clean_ep = re.sub(r'[^0-9]', '', p["episode_no"]).zfill(2)
        clean_title = re.sub(r'[\s\\/*?:"<>|]', '', p["title"])
        image_file = f"images/{clean_ep}_{clean_title}.jpg"
        
        art_dir = p["suggested_prompt"] if req.auto_prompts else "한국적 서정 수채화 (300 DPI)"

        new_works.append(PoemWork(
            episode_no=p["episode_no"],
            title=p["title"],
            status="완성 (승인 완료)",
            memory_anchor=p["memory_anchor"],
            image_file=image_file,
            art_direction=art_dir,
            poem_body=p["poem_body"]
        ))

    # 활성 원고 마크다운 파일에 일괄 저장
    info = project_manager.get_active_project_info()
    manuscript_file = project_manager.get_project_dir() / "작품집_원고.md"
    
    header = f"""# {info.name} 원고 (진행 현황: {len(new_works)} / {max(info.target_count, len(new_works))}편 완료)

> **지은이**: {info.author}  
> **부제**: {info.subtitle}  
> **도서 형태**: {'서정 시화집' if getattr(info, 'book_type', 'illustrated') == 'illustrated' else '일반 시집'}  
> **기획**: {info.description}  

---
"""
    body_blocks = []
    for w in new_works:
        block = f"""
## [{w.episode_no}] {w.title}

- **상태**: {w.status}
- **기억의 중심**: {w.memory_anchor}
- **삽화 파일**: `{w.image_file}`
- **그림 방향**: {w.art_direction}

### [시 본문]

{w.poem_body}
"""
        body_blocks.append(block)

    full_md = header + "\n".join(body_blocks)
    manuscript_file.write_text(full_md, encoding="utf-8")

    # 프로젝트 정보(target_count 등) 자동 업데이트
    if len(new_works) > info.target_count:
        project_manager.update_project_info(
            project_id=info.id,
            name=info.name,
            subtitle=info.subtitle,
            author=info.author,
            target_count=len(new_works),
            description=info.description,
            book_type=getattr(info, "book_type", "illustrated")
        )

    # CSV 데이터 자동 갱신
    try:
        build_canva_csv()
    except Exception:
        pass

    return {
        "success": True,
        "count": len(new_works),
        "imported_count": len(parsed_items),
        "message": f"총 {len(parsed_items)}편의 완성 원고가 성공적으로 등록되었습니다!"
    }


# ========================================================
# [기둥 1] 시어(詩語) 감각 사전 & 토속·방언 API
# ========================================================
@app.get("/api/thesaurus/lookup")
async def api_thesaurus_lookup(word: str = ""):
    """단어에 매칭되는 시어 감각 사전 항목을 조회합니다."""
    query = (word or "").strip()
    if not query:
        return {"success": False, "found": False, "word": "", "data": None, "message": "검색할 단어를 입력해 주세요."}
    
    result = lookup_poetic_words(query)
    if not result:
        return {
            "success": True,
            "found": False,
            "word": query,
            "data": None,
            "message": f"'{query}'에 대한 시어 감각 데이터가 아직 없습니다. 아래 추천 테마를 둘러보세요."
        }

    return {
        "success": True,
        "found": True,
        "word": query,
        "matched_key": result["matched_key"],
        "data": result["data"]
    }


@app.get("/api/thesaurus/all")
async def api_thesaurus_all():
    """시어 사전 전체 등록 테마 목록과 미리보기를 반환합니다."""
    themes = get_all_categories_summary()
    return {
        "success": True,
        "categories": themes,
        "themes": themes,
        "total": len(themes)
    }


@app.get("/api/thesaurus/suggest")
async def api_thesaurus_suggest(word: str = "", context: str = ""):
    """
    선택한 단어와 시적 문맥(주변 시행)을 바탕으로,
    서정적 시어, 토속 방언, 은유적 유의어를 실시간 AI/사전 엔진으로 추천합니다.
    """
    query = (word or "").strip()
    if not query:
        return {"success": False, "word": "", "suggestions": [], "message": "단어를 입력해 주세요."}

    result = suggest_poetic_synonyms_ai(query, context)
    return {
        "success": True,
        "word": result.get("word", query),
        "matched_key": result.get("matched_key", query),
        "suggestions": result.get("suggestions", []),
        "source": result.get("source", "heuristic")
    }


class SaveWorkLayoutConfigRequest(BaseModel):
    episode_no: str
    layout_config: Dict[str, Any]


@app.post("/api/save_work_layout_config")
async def save_work_layout_config_api(req: SaveWorkLayoutConfigRequest):
    """작품별 2P/4P 모듈형 매트릭스 조판 설정을 영구 저장"""
    mgr = project_manager.get_active_manuscript_manager()
    success = mgr.update_work_layout_config(req.episode_no, req.layout_config)
    if not success:
        raise HTTPException(status_code=404, detail=f"작품 '{req.episode_no}'을(를) 찾을 수 없습니다.")
    return {
        "success": True,
        "message": f"'{req.episode_no}'의 조판 설정이 성공적으로 저장되었습니다.",
        "episode_no": req.episode_no
    }




