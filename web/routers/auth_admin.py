"""로그인, 중앙 회원 인증, 최고 관리자(/admin) 및 AI 키/모델 설정 라우터"""

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
from fastapi import APIRouter, Request, Response, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

try:
    from google import genai
except ImportError:
    genai = None

from core.config import TARGET_POEMS_COUNT, DEFAULT_ART_STYLE, PAPER_TYPE, save_gemini_api_key, save_gemini_model, get_gemini_api_key_status, is_admin_email
from core.auth_manager import auth_manager
from core.project_manager import project_manager

WEB_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = WEB_DIR / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter()


class SetApiKeyRequest(BaseModel):
    api_key: str

class SetModelRequest(BaseModel):
    model_name: str

class AuthSessionRequest(BaseModel):
    user_id: Optional[str] = ""
    email: str
    access_token: Optional[str] = ""
    name: Optional[str] = None
    provider: Optional[str] = "turso_email"

class TursoLoginRequest(BaseModel):
    email: str
    password: Optional[str] = ""
    name: Optional[str] = None

# -------------------------------------------------------------
# 중앙 회원 인증 및 로그인 라우트 (Turso DB 자체 인증 일원화)
# -------------------------------------------------------------
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Turso 클라우드 자체 인증 (이메일/구글) 1초 로그인 및 회원가입 페이지"""
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={}
    )

@router.post("/api/auth/turso_login")
async def turso_native_login(req: TursoLoginRequest, response: Response):
    """
    [Supabase 수면 문제 완전 해결]
    Turso DB 기반 자체 회원 로그인/자동 가입 엔드포인트
    """
    try:
        session = auth_manager.authenticate_or_register_email(
            email=req.email,
            password=req.password or "",
            name=req.name
        )
        if session and session.get("token"):
            response.set_cookie(
                key="sb_session",
                value=session["token"],
                max_age=30 * 24 * 3600,
                httponly=True,
                samesite="lax"
            )
        if session and session.get("active_project_id"):
            response.set_cookie(
                key="sb_active_project",
                value=urllib.parse.quote(session["active_project_id"]),
                max_age=30 * 24 * 3600,
                httponly=False,
                samesite="lax"
            )
        claimed = False
        try:
            active_info = project_manager.get_active_project_info()
            if not active_info.owner_id:
                claimed = project_manager.claim_project(active_info.id, session["user_id"], session["email"])
        except Exception:
            pass
        return {
            "success": True,
            "session": session,
            "claimed_project": claimed,
            "message": "로그인 성공! 작성 중이던 시집이 회원님의 계정으로 안전하게 귀속되었습니다." if claimed else "로그인 성공!"
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그인 처리 실패: {str(e)}")

@router.get("/", response_class=HTMLResponse)
async def portal_home_page(request: Request):
    """EduAI Hub & 글솥 통합 포털 대문 페이지"""
    current_user = auth_manager.get_current_user()
    return templates.TemplateResponse(
        request=request,
        name="portal.html",
        context={
            "current_user": current_user,
            "is_admin": auth_manager.is_current_user_admin() if current_user else False
        }
    )

@router.get("/studio", response_class=HTMLResponse)
async def studio_page(request: Request):
    """스튜디오 메인 집필실 및 2-Layer 조판실 (로그인 확인 후 집필실 표시)"""
    is_guest = request.query_params.get("guest") == "true"
    current_user = auth_manager.get_current_user()

    if not current_user and not is_guest:
        return RedirectResponse(url="/login")

    from core.project_manager import project_manager
    active_info = project_manager.get_active_project_info()

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "current_user": current_user,
            "is_guest": is_guest,
            "is_admin": auth_manager.is_current_user_admin(),
            "active_project": active_info
        }
    )

@router.get("/manual", response_class=HTMLResponse)
async def user_manual_page(request: Request):
    """어르신 및 컴퓨터 초보자 맞춤형 큰 글씨 사용 설명서 페이지"""
    return templates.TemplateResponse(
        request=request,
        name="manual.html",
        context={}
    )

@router.get("/admin", response_class=HTMLResponse)
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

@router.post("/api/auth/save_session")
async def save_auth_session(req: AuthSessionRequest):
    """클라이언트 로그인 성공 후 세션을 Turso DB 및 브라우저 쿠키에 영구 저장하고 기존 시집 자동 귀속"""
    try:
        verified_uid = req.user_id or ""
        verified_email = req.email

        session = auth_manager.save_session(
            user_id=verified_uid,
            email=verified_email,
            access_token=req.access_token or "",
            name=req.name,
            provider=req.provider or "turso_email"
        )

        # [자동 귀속: Auto Claim] 현재 활성 시집이 미할당(게스트 작성분) 상태라면 내 계정으로 즉시 소유권 이전
        claimed = False
        try:
            active_info = project_manager.get_active_project_info()
            if not active_info.owner_id:
                claimed = project_manager.claim_project(active_info.id, session["user_id"], session["email"])
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

@router.get("/api/auth/status")
async def get_auth_status():
    """현재 스튜디오 로그인 상태 및 사용자 정보 반환"""
    return auth_manager.get_auth_status()

@router.post("/api/auth/logout")
async def logout_endpoint(response: Response):
    """스튜디오 로그아웃 및 세션 초기화"""
    success = auth_manager.clear_session()
    response.delete_cookie("sb_session")
    response.delete_cookie("sb_active_project")
    return {"success": success}


# -------------------------------------------------------------
# 최고 관리자(Admin) 전용 모니터링 및 제어 API
# -------------------------------------------------------------
class AdminSwitchProjectRequest(BaseModel):
    project_id: str

@router.get("/api/admin/overview")
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
    from core.db_manager import db_manager
    gemini_status = get_gemini_api_key_status()

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
            "turso": {
                "configured": db_manager.is_cloud_mode,
                "mode": "Turso libSQL Cloud Native" if db_manager.is_cloud_mode else "Local SQLite"
            },
            "paper_type": PAPER_TYPE,
            "default_target_count": TARGET_POEMS_COUNT,
            "default_art_style": DEFAULT_ART_STYLE,
            "active_project_id": project_manager.get_active_project_id()
        }
    }

@router.post("/api/admin/project/switch")
async def admin_switch_project(req: AdminSwitchProjectRequest):
    """관리자가 특정 프로젝트로 스튜디오 활성 프로젝트 즉시 전환"""
    if not auth_manager.is_current_user_admin():
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")
    try:
        project_manager.set_active_project_id(req.project_id)
        return {"success": True, "active_project": req.project_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))



@router.get("/api/settings/gemini_key")
async def get_gemini_key_api():
    """현재 Gemini API 키 등록 여부 및 마스킹된 키 조회"""
    return get_gemini_api_key_status()

@router.get("/api/settings/gemini_model")
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

@router.post("/api/settings/gemini_model")
async def set_gemini_model_api(req: SetModelRequest):
    """원하는 Gemini 모델로 즉시 변경 및 영구 저장"""
    model_name = req.model_name.strip()
    if not model_name:
        raise HTTPException(status_code=400, detail="모델명을 입력해주세요.")
    save_gemini_model(model_name)
    return {"success": True, "current_model": model_name, "message": f"AI 모델이 [{model_name}]로 성공적으로 변경되었습니다!"}

@router.post("/api/settings/gemini_key")
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
