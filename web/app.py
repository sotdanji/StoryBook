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
from core.csv_builder import build_canva_csv
from core.book_spec import calculate_spine_and_cover, inspect_images
from core.pdf_builder import build_pdf_book
from core.bookk_pdf_builder import BookkPDFBuilder, BOOKK_FORMATS
from core.image_optimizer import ensure_300dpi_image
from core.poetic_engine import poetic_engine
from core.colab_builder import build_yue2_notebook_dict, DEFAULT_GENRE_PROMPT
from core.colab_image_builder import build_sdxl_image_notebook_dict, DEFAULT_STYLE_PRESETS
from core.poetic_thesaurus import lookup_poetic_words, get_all_categories_summary, suggest_poetic_synonyms_ai, POETIC_THESAURUS_DB

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
    mode: str  # "shorten", "subdued", "rhythm"

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

class GenerateImageCandidatesRequest(BaseModel):
    episode_no: str
    prompt: Optional[str] = ""
    title: Optional[str] = ""
    memory_anchor: Optional[str] = ""
    custom_guide: Optional[str] = ""
    reference_image: Optional[str] = None  # Base64 데이터 URL 또는 base64 인코딩 이미지
    direct_use_photo: Optional[bool] = False  # 사용자가 첨부한 사진 자체를 300 DPI 출판용 삽화로 즉시 변환 사용

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
                "audio_file": getattr(w, "audio_file", ""),
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
            img_file = w.image_file or ""
            img_path = f"/projects/{safe_name}/images/{img_file}" if img_file else ""
            audio_f = getattr(w, "audio_file", "") or ""
            audio_path = f"/projects/{safe_name}/images/{audio_f}" if audio_f else ""

            episodes.append({
                "ep": w.episode_no,
                "title": w.title,
                "image": img_path,
                "memory": w.memory_anchor,
                "body": w.poem_body,
                "hasMusic": bool(audio_f),
                "audio": audio_path,
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
    """현재 시 본문을 사용자가 원하는 방향(압축, 절제, 운율 정돈)으로 즉시 다듬기"""
    refined = poetic_engine.refine_poem(req.poem_body, req.mode)
    return {"success": True, "refined_body": refined}

@app.post("/api/generate_image_prompt")
async def generate_image_prompt_endpoint(req: ImagePromptRequest):
    """다듬어진 시 제목과 본문을 분석하여 300 DPI 서정 삽화 프롬프트 생성 (사용자 친화적 한국어 프롬프트 우선)"""
    korean_prompt = poetic_engine.generate_korean_art_prompt(
        title=req.title,
        poem_body=req.poem_body,
        core_memory=req.core_memory,
        sensory_details=req.sensory_details,
        style_mode=req.style_mode or "literal",
        art_style=req.art_style or "watercolor",
        custom_guide=req.custom_guide or ""
    )
    english_prompt = poetic_engine.generate_art_prompt_with_gemini(
        title=req.title,
        poem_body=req.poem_body,
        core_memory=req.core_memory,
        sensory_details=req.sensory_details,
        style_mode=req.style_mode or "literal",
        art_style=req.art_style or "watercolor",
        custom_guide=req.custom_guide or ""
    )
    korean_instruction = poetic_engine.get_image_generation_instruction_ko(
        title=req.title,
        poem_body=req.poem_body,
        art_style=req.art_style or "watercolor",
        custom_guide=req.custom_guide or ""
    )
    return {
        "success": True,
        "prompt": korean_prompt,
        "korean_prompt": korean_prompt,
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
    work = PoemWork(
        episode_no=req.episode_no,
        title=req.title,
        status=req.status,
        memory_anchor=req.memory_anchor,
        image_file=req.image_file,
        art_direction=req.art_direction,
        poem_body=req.poem_body,
        audio_file=req.audio_file or "",
        lyrics=req.lyrics or "",
        author=req.author or "",
        layout_mode=req.layout_mode or "compact"
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

    # 원고에도 audio_file 경로 자동 업데이트
    mgr = project_manager.get_active_manuscript_manager()
    work = mgr.get_work_by_episode(episode_no)
    if work:
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

@app.post("/api/generate_lyrics")
async def generate_lyrics_endpoint(req: LyricsGenerateRequest):
    """다듬어진 시 본문을 기반으로 3대 서정 장르(민요, 포크, 가곡)에 맞춘 노래 가사 생성"""
    try:
        lyrics_data = poetic_engine.generate_song_lyrics(
            title=req.title,
            poem_body=req.poem_body,
            genre=req.genre or "minyo"
        )
        return {
            "success": True,
            "data": lyrics_data,
            "lyrics": lyrics_data.get("lyrics", "")
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/upload_audio")
async def upload_audio_endpoint(
    audio_file: UploadFile = File(...),
    episode_no: str = Form(...)
):
    """사용자가 외부 AI(Colab YuE2, Suno 등)에서 생성한 오디오 파일을 현재 프로젝트의 music/ 디렉토리에 저장"""
    try:
        project_dir = project_manager.get_project_dir()
        music_dir = project_dir / "music"
        music_dir.mkdir(parents=True, exist_ok=True)

        orig_name = audio_file.filename or "song.mp3"
        ext = Path(orig_name).suffix.lower()
        if ext not in [".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac"]:
            ext = ".mp3"

        clean_ep = re.sub(r'[^0-9]', '', episode_no).zfill(2) if episode_no else "01"
        safe_name = f"{clean_ep}_음원{ext}"
        target_path = music_dir / safe_name

        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(audio_file.file, buffer)

        rel_path = f"music/{safe_name}"
        active_id = project_manager.get_active_project_id()
        web_url = f"/projects/{active_id}/{rel_path}"

        return {
            "success": True,
            "audio_file": rel_path,
            "web_url": web_url,
            "filename": safe_name
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/speak_poem")
async def speak_poem_endpoint(req: SpeakPoemRequest):
    """
    최신 Gemini TTS(gemini-3.8-flash-tts)를 활용하여 
    시 본문을 서정적인 전문 성우 음성(audio/wav)으로 생성합니다.
    """
    import base64
    import time
    from core.config import GEMINI_API_KEY
    key = os.getenv("GEMINI_API_KEY") or GEMINI_API_KEY
    if not key or not genai:
        raise HTTPException(status_code=400, detail="Gemini API 키가 등록되지 않았습니다.")

    poem_text = req.poem_body.strip()
    if not poem_text:
        raise HTTPException(status_code=400, detail="낭송할 시 본문이 비어 있습니다.")

    try:
        client = genai.Client(api_key=key)
        # 서정적 호흡의 전문 낭독 프롬프트
        tts_prompt = (
            f"다음 한국 서정시를 차분하고 깊은 울림을 지닌 목소리로 서정적이고 따뜻하게 낭독해 주세요.\n\n"
            f"제목: {req.title}\n\n{poem_text}"
        )

        # 최신 gemini-3.8-flash-tts 우선 호출 (폴백: gemini-2.5-flash-preview-tts)
        models_to_try = ["gemini-3.8-flash-tts", "gemini-2.5-flash-preview-tts"]
        audio_data = None
        mime_type = "audio/wav"

        for m_name in models_to_try:
            try:
                res = client.models.generate_content(
                    model=m_name,
                    contents=tts_prompt
                )
                if res and res.candidates and res.candidates[0].content and res.candidates[0].content.parts:
                    for part in res.candidates[0].content.parts:
                        if hasattr(part, "inline_data") and part.inline_data and part.inline_data.data:
                            audio_data = part.inline_data.data
                            mime_type = getattr(part.inline_data, "mime_type", "audio/wav")
                            print(f"[Gemini TTS 성공] {m_name} 모델로 낭송 생성 완료 ({len(audio_data)} bytes)")
                            break
                if audio_data:
                    break
            except Exception as tts_err:
                print(f"[Gemini TTS {m_name}] 시도 실패: {tts_err}")
                continue

        if not audio_data:
            raise RuntimeError("Gemini 음성 합성 응답에서 오디오 데이터를 찾을 수 없습니다.")

        b64_audio = base64.b64encode(audio_data).decode("utf-8")
        data_uri = f"data:{mime_type};base64,{b64_audio}"

        # 프로젝트 music 폴더에 자동 음원 저장
        clean_ep = re.sub(r'[^0-9]', '', req.episode_no).zfill(2) if req.episode_no else "01"
        project_dir = project_manager.get_project_dir()
        music_dir = project_dir / "music"
        music_dir.mkdir(parents=True, exist_ok=True)
        recite_filename = f"{clean_ep}_낭송.wav"
        recite_path = music_dir / recite_filename
        with open(recite_path, "wb") as f:
            f.write(audio_data)

        active_id = project_manager.get_active_project_id()
        audio_url = f"/projects/{active_id}/music/{recite_filename}?t={int(time.time())}"

        return {
            "success": True,
            "data_uri": data_uri,
            "audio_url": audio_url,
            "filename": recite_filename,
            "rel_path": f"music/{recite_filename}",
            "message": "Gemini 3.8 고음질 서정 낭송이 생성되었습니다."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini 음성 합성 오류: {str(e)}")

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

    # 프롬프트 구성 (사용자가 수정한 프롬프트 우선, 없으면 기억 중심 기반 생성)
    prompt_text = req.prompt.strip() if req.prompt and req.prompt.strip() else ""
    if not prompt_text:
        anchor = req.memory_anchor or req.title or "고향의 추억"
        prompt_text = (
            f"Delicate Korean lyric watercolor illustration of {anchor}, "
            f"warm nostalgic morning sunlight, soft translucent washes, peaceful empty space, textured white paper"
        )

    seed = random.randint(1000, 999999)

    try:
        # 통합 3단계 고신뢰도 파이프라인으로 생성 및 300 DPI 저장
        img_bytes = await asyncio.to_thread(_generate_art_image_bytes, prompt_text, seed)
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

def _generate_art_image_bytes(prompt_str: str, seed_val: int) -> bytes:
    """
    [지능형 하이브리드 이미지 생성 파이프라인]
    ★ 1순위 (최우선 직행) : Google Gemini Image (API 키 연결 시 한국어/정서 1위 엔진 즉시 가동)
    ★ 2순위 (무료 폴백) : Pollinations AI turbo/default (API 키 미등록자 또는 할당량 초과 시 오픈 서버)
    ★ 3순위 (보조 폴백) : Pollinations AI flux
    """
    clean_p = _clean_image_prompt(prompt_str)
    
    # [서예/한자/텍스트 및 서양 오두막 원천 차단 가드레일]
    lower_p = clean_p.lower()
    guard_clauses = []
    if "no text" not in lower_p and "without text" not in lower_p:
        guard_clauses.append("pure fine art illustration without any text")
    if "no calligraphy" not in lower_p:
        guard_clauses.append("no calligraphy")
    if "no letters" not in lower_p:
        guard_clauses.append("no letters or words")
    if "no seal" not in lower_p and "no stamp" not in lower_p:
        guard_clauses.append("no seal stamp or signature")
    if "vertical" not in lower_p and "portrait" not in lower_p:
        guard_clauses.append("vertical portrait orientation (3:4 tall aspect ratio)")

    if guard_clauses:
        guarded_prompt = f"{clean_p}, {', '.join(guard_clauses)}"
    else:
        guarded_prompt = clean_p

    # ========================================================
    # ★ 1순위 (최우선) : Google Gemini Image (API 키 연결 시)
    # 구글의 방대한 한국어/동양 문화 이해력으로 정밀 세로형 수채화 즉시 생성!
    # ========================================================
    api_key = os.getenv("GEMINI_API_KEY") or GEMINI_API_KEY
    if api_key and genai:
        print("[1순위 최우선 직행: Google Gemini Image] 구글 고지능 이미지 AI로 한국 서정 삽화를 즉시 생성합니다.")
        try:
            client = genai.Client(api_key=api_key)
            image_models = ["gemini-2.5-flash-image", "gemini-3.1-flash-image", "gemini-3-pro-image"]
            
            has_ko = bool(re.search(r'[\uac00-\ud7a3]', prompt_str))
            if has_ko:
                gemini_contents = (
                    "한국 출판 시화집을 위한 정통 서정 수채화 삽화를 3:4 세로형 구도(A5 규격)로 아름답고 깊이 있게 그려주세요.\n"
                    "핵심 가이드:\n"
                    "1. 화풍: 맑고 투명한 물빛 번짐(Wet-on-wet)과 따뜻한 아침 햇살, 전통 수채화 종이의 섬세한 질감.\n"
                    "2. 여백: 외곽 10%는 책의 순백 종이(#FFFFFF)와 자연스럽게 융합되도록 은은하고 부드러운 페이드아웃 여백(Soft Vignette).\n"
                    "3. 금지: 글자, 한글, 알파벳, 한자, 낙관, 서명, 사각 테두리 선 절대 금지.\n"
                    "4. 배경: 어두운 동굴이나 땅구멍, 서양식 통나무집(cabin), 샬레 등 절대 배제. 북풍을 막아주는 양지바른 언덕 비탈과 흙 둔덕 아래 따스한 야외 흙터만 표현.\n"
                    f"5. 장면 연출: {clean_p}"
                )
            else:
                gemini_contents = f"Generate a delicate Korean lyric watercolor illustration on textured paper, in vertical portrait orientation (3:4 tall aspect ratio), 300 dpi, pure fine art without any text, letters, calligraphy, stamps, or frames: {guarded_prompt}"

            for m_name in image_models:
                try:
                    res = client.models.generate_content(
                        model=m_name,
                        contents=gemini_contents
                    )
                    if res and res.candidates and res.candidates[0].content and res.candidates[0].content.parts:
                        for part in res.candidates[0].content.parts:
                            if hasattr(part, "inline_data") and part.inline_data and part.inline_data.data:
                                print(f"[Google Gemini 성공] {m_name} 모델로 최고 품질 삽화 생성 완료 ({len(part.inline_data.data)} bytes)")
                                return part.inline_data.data
                except Exception as m_err:
                    print(f"[Gemini 모델 {m_name} 실패, 다음 시도]: {m_err}")
                    continue
        except Exception as gemini_err:
            print(f"[Gemini 1순위 일시 불가, 2순위 무료 오픈 AI로 자동 전환]: {gemini_err}")

    # ========================================================
    # ★ 2순위 (무료 폴백) : Pollinations AI
    # API 키가 없거나 Gemini 할당량 초과 시 무료 오픈 AI로 안전하게 전환
    # ========================================================
    print("[2순위 무료 오픈 AI 전환] Pollinations 엔진으로 생성을 진행합니다.")
    encoded = urllib.parse.quote(guarded_prompt)
    neg_items = [
        "text", "letters", "words", "typography", "hangul", "chinese characters", "calligraphy",
        "stamp", "seal", "signature", "frame", "border", "watermark", "logo", "blurry", "ugly",
        "horizontal", "landscape orientation", "wide panorama"
    ]
    if "cabin" not in lower_p and "cottage" not in lower_p and "house" not in lower_p:
        neg_items.extend(["cabin", "western log cabin", "chalet"])
    neg_param = urllib.parse.quote(",".join(neg_items))

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
                    print(f"[2순위 Pollinations 성공] 무료 오픈 AI로 생성 완료 ({len(data)} bytes)")
                    return data
        except Exception as p_err:
            print(f"[Pollinations 일시 불가] {p_err}")
            continue

    # ========================================================
    # ★ 3순위 (보조 폴백) : 추가 무료 오픈 이미지 엔드포인트
    # ========================================================
    try:
        free_backup_url = f"https://image.pollinations.ai/prompt/{encoded}?width=768&height=1024&nologo=true"
        url_req = urllib.request.Request(free_backup_url, headers={"User-Agent": "StoryBook-Studio/1.0"})
        with urllib.request.urlopen(url_req, timeout=20) as resp:
            data = resp.read()
            if len(data) > 1000:
                print(f"[3순위 무료 오픈 폴백 성공] ({len(data)} bytes)")
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

def _download_and_save_candidate(prompt_str: str, seed_val: int, file_path: Path):
    img_bytes = _generate_art_image_bytes(prompt_str, seed_val)
    ensure_300dpi_image(img_bytes, file_path)

@app.post("/api/generate_image_candidates")
async def generate_image_candidates(req: GenerateImageCandidatesRequest):
    """
    무료 한도(Rate Limit) 절약 및 초고속 생성을 위해 단 1장의 최적 서정 삽화를 즉시 생성하고 원고에 자동 반영합니다.
    참조 사진(reference_image)이 전달된 경우 멀티모달 비전 분석을 통해 사진 구도와 피사체를 수채화로 재창작하거나,
    direct_use_photo=True인 경우 해당 사진 자체를 300 DPI 순백 여백 보정하여 바로 시안으로 사용합니다.
    """
    clean_ep = re.sub(r'[^0-9]', '', req.episode_no).zfill(2)
    images_dir = project_manager.get_active_images_dir()
    images_dir.mkdir(parents=True, exist_ok=True)

    ref_bytes = _parse_base64_image(req.reference_image)

    # [옵션 B] 사진 자체를 300 DPI 순백 여백 보정 후 바로 시안으로 등록
    if req.direct_use_photo and ref_bytes:
        seed = random.randint(100000, 999999)
        filename = f"{clean_ep}_생성후보.jpg"
        target_path = images_dir / filename
        print(f"[{req.episode_no}화] 첨부 사진 자체를 300 DPI 수채화 여백 보정하여 바로 시안 등록 ({len(ref_bytes)} bytes)")
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
    custom_guide = req.custom_guide.strip() if req.custom_guide else ""

    api_key = os.getenv("GEMINI_API_KEY") or GEMINI_API_KEY
    has_korean = bool(re.search(r'[\uac00-\ud7a3]', base_prompt))
    
    # 프롬프트가 없거나, 연출 가이드가 추가되었거나, 참조 사진이 있는 경우 최적 프롬프트 조립
    if custom_guide or ref_bytes or not base_prompt or len(base_prompt) < 15:
        ref_msg = " + [참조 사진 비전 분석]" if ref_bytes else ""
        print(f"[{req.episode_no}화 프롬프트 조립] 연출 가이드('{custom_guide}'){ref_msg} 반영하여 감성 프롬프트를 생성합니다.")
        mgr = project_manager.get_active_manuscript_manager()
        works = mgr.load_works()
        target_work = next((w for w in works if clean_ep in w.episode_no or w.episode_no.strip() == req.episode_no.strip()), None)

        p_title = req.title or (target_work.title if target_work else "고향의 추억")
        p_body = (target_work.poem_body if target_work and target_work.poem_body else "")
        p_memory = req.memory_anchor or (target_work.memory_anchor if target_work else "")
        p_direction = (target_work.art_direction if target_work and target_work.art_direction else "")

        if api_key and genai:
            # Gemini 1순위: 한국어 문화 정서 100% 직행
            base_prompt = poetic_engine.generate_korean_art_prompt(
                title=p_title,
                poem_body=p_body,
                core_memory=p_memory,
                sensory_details=p_direction,
                style_mode="literal",
                art_style="watercolor",
                custom_guide=custom_guide,
                api_key=api_key
            )
        else:
            base_prompt = poetic_engine.generate_art_prompt_with_gemini(
                title=p_title,
                poem_body=p_body,
                core_memory=p_memory,
                sensory_details=p_direction,
                style_mode="literal",
                art_style="watercolor",
                custom_guide=custom_guide,
                reference_image_bytes=ref_bytes
            )

    # 단일 최적 시안 생성 (미리보기 확인 후 [삽입] 클릭 시에만 원고에 반영)
    seed = random.randint(100000, 999999)
    filename = f"{clean_ep}_생성후보.jpg"
    target_path = images_dir / filename

    try:
        # 단 1회 초고속 생성 (300 DPI 규격 보정)
        await asyncio.to_thread(_download_and_save_candidate, base_prompt, seed, target_path)

        # 원고 즉시 덮어쓰기는 수행하지 않음 (사용자가 미리보기 후 [삽입]을 선택할 때만 반영)
        return {
            "success": True,
            "episode_no": req.episode_no,
            "filename": filename,
            "used_prompt": base_prompt,
            "image_url": f"/images/{filename}?t={seed}",
            "message": f"[{req.episode_no}] 새 삽화 시안이 생성되었습니다. 미리보기 창에서 확인하세요.",
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
            else:
                w.image_file = f"./images/{final_filename}"
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
                else:
                    w.image_file = f"./images/{filename}"
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
    clean_ep = re.sub(r'[^0-9]', '', req.episode_no).zfill(2)
    filename = f"{clean_ep}_생성후보_2부.jpg"

    images_dir = project_manager.get_active_images_dir()
    images_dir.mkdir(parents=True, exist_ok=True)
    target_path = images_dir / filename

    ref_bytes = _parse_base64_image(req.reference_image)

    # [옵션 B] 사진 자체를 300 DPI 순백 여백 보정 후 바로 2부 시안으로 등록
    if req.direct_use_photo and ref_bytes:
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
    custom_guide = (req.custom_guide or "").strip()
    if custom_guide or ref_bytes or not prompt_text:
        # ★ 묘책: 시의 후반부(Part 2) 본문을 정밀 분석한 전용 연작 서정 프롬프트 자동 조립!
        if target_work:
            prompt_text = poetic_engine.generate_sequel_image_prompt(
                title=target_work.title,
                poem_body=target_work.poem_body or "",
                core_memory=target_work.memory_anchor or "",
                sensory_details="",
                custom_guide=custom_guide
            )
        else:
            prompt_text = (
                "authentic Korean lyric transparent watercolor painting, intimate nostalgic midnight room, "
                "warm kerosene lamp glowing in chilly night breeze, on pure clean white paper background, wide 10% white margin, "
                "soft vignetting, delicate brush textures, masterpiece, no text, no frame"
            )

    seed = random.randint(100000, 999999)

    try:
        # 다단계 무료 폴백 엔진 & 300 DPI 사방 10% 수채화 블러 비네팅 마스크 자동 적용
        await asyncio.to_thread(_download_and_save_candidate, prompt_text, seed, target_path)

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
async def export_bookk_interior(format_key: str = "b6_mod", paper_type: str = "white_100g"):
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
async def export_bookk_cover(format_key: str = "b6_mod", paper_type: str = "white_100g", total_pages: int = 80):
    """부크크 표지 펼침면(뒤표지 + 책등 세네카 + 앞표지 + 도련 3mm) PDF 생성 및 다운로드"""
    try:
        info = project_manager.get_active_project_info()
        p_dir = project_manager.get_project_dir()
        builder = BookkPDFBuilder(format_key=format_key, paper_type=paper_type)

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
    mgr = ManuscriptManager()
    success = mgr.update_work_layout_config(req.episode_no, req.layout_config)
    if not success:
        raise HTTPException(status_code=404, detail=f"작품 '{req.episode_no}'을(를) 찾을 수 없습니다.")
    return {
        "success": True,
        "message": f"'{req.episode_no}'의 조판 설정이 성공적으로 저장되었습니다.",
        "episode_no": req.episode_no
    }




