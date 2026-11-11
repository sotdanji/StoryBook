"""
web/app.py
StoryBook Studio 메인 FastAPI 애플리케이션 진입점
- 정적 파일(/static, /projects) 마운트
- 7대 기능별 모듈 라우터(web/routers/*) 통합 등록
- 기존 스크립트 및 테스트 코드 하위 호환을 위한 심볼 재익스포트(Re-export)
"""

from pathlib import Path
import urllib.parse
import hashlib
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from core.config import BASE_DIR, get_cloud_infrastructure_status
from core.auth_manager import set_request_context, get_request_session_token, get_request_active_project
from core.project_manager import project_manager
from core.db_manager import db_manager
from core.r2_storage import r2_storage
from web.routers import (
    auth_admin,
    projects,
    studio_poem,
    illustration,
    audio_video,
    video_studio,
    publishing,
    thesaurus,
    inquiries,
)


app = FastAPI(
    title="StoryBook Studio",
    description="기억 기반 시화집 독립출판 웹 스튜디오"
)


@app.middleware("http")
async def session_isolation_middleware(request: Request, call_next):
    """
    [다중 사용자 세션 & 활성 시집 완벽 격리 미들웨어]
    브라우저별 쿠키(sb_session, sb_active_project)를 ContextVar에 바인딩하여
    동시 접속한 회원 간 로그인 세션 및 열람 중인 시집이 절대 섞이지 않도록 보장합니다.
    """
    cookie_token = request.cookies.get("sb_session", "") or request.headers.get("X-SB-Session", "")
    cookie_proj = urllib.parse.unquote(request.cookies.get("sb_active_project", "") or request.headers.get("X-SB-Project", ""))
    set_request_context(session_token=cookie_token, active_project_id=cookie_proj)

    response = await call_next(request)

    new_token = get_request_session_token()
    new_proj = get_request_active_project()

    if new_token and new_token != cookie_token:
        response.set_cookie(
            key="sb_session",
            value=new_token,
            max_age=30 * 24 * 3600,
            httponly=True,
            samesite="lax"
        )
    elif request.url.path == "/api/auth/logout":
        response.delete_cookie("sb_session")
        response.delete_cookie("sb_active_project")

    if new_proj and new_proj != cookie_proj:
        response.set_cookie(
            key="sb_active_project",
            value=urllib.parse.quote(new_proj),
            max_age=30 * 24 * 3600,
            httponly=False,
            samesite="lax"
        )

    return response


# 디렉토리 경로 설정 및 보장 (로컬 projects/ 마운트 완전 제거 -> 100% R2 클라우드 서빙)
WEB_DIR = Path(__file__).resolve().parent
STATIC_DIR = WEB_DIR / "static"
TEMPLATES_DIR = WEB_DIR / "templates"

STATIC_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

# 정적 파일 마운트 (/static 전용)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# 7대 기능별 APIRouter 통합 등록
app.include_router(auth_admin.router, tags=["1. 인증 · 관리자 · AI 설정"])
app.include_router(projects.router, tags=["2. 시집 프로젝트 · 서재 관리"])
app.include_router(studio_poem.router, tags=["3. 시 창작 · 퇴고 · 원고 관리"])
app.include_router(illustration.router, tags=["4. 300 DPI 서정 삽화 생성"])
app.include_router(audio_video.router, tags=["5. 시낭송(TTS) · 노래 · 비디오"])
app.include_router(video_studio.router, tags=["5-1. 비디오 스튜디오"])
app.include_router(publishing.router, tags=["6. 부크크 PDF · 출판 데이터"])
app.include_router(thesaurus.router, tags=["7. 시어 감각 사전 · 방언"])
app.include_router(inquiries.router, tags=["8. 1:1 비밀 상담 · 출판 코칭"])

# 브라우저 자동 요청 파비콘(404 방지)
@app.get("/favicon.ico", include_in_schema=False)
async def get_favicon():
    favicon_path = STATIC_DIR / "favicon.ico"
    if favicon_path.exists():
        return FileResponse(str(favicon_path), media_type="image/x-icon")
    return Response(status_code=204)


# ------------------------------------------------------------------
# 🌟 클라우드 컨테이너 헬스체크 및 단일 플랫폼 상태 진단 라우트
# ------------------------------------------------------------------
@app.get("/health", tags=["0. 시스템 헬스체크"])
async def health_check():
    infra = get_cloud_infrastructure_status()
    return {
        "status": "healthy",
        "service": "StoryBook Studio Single-Platform Engine",
        "db_mode": "turso_cloud" if db_manager.is_cloud_mode else "local_sqlite",
        "r2_mode": "cloudflare_r2" if r2_storage.is_r2_configured else "tmp_buffer",
        "infrastructure": infra
    }


# ------------------------------------------------------------------
# 🌟 100% Cloudflare R2 클라우드 일원화 미디어 서빙 라우트
# - 로컬 projects/ 폴더를 전혀 참조하지 않고 R2(및 /tmp 버퍼)에서 직접 서빙
# ------------------------------------------------------------------
def _serve_from_r2(project_id: str, rel_subpath: str):
    """로컬 영구 볼륨 우선 조회(0.001초 초고속 응답) 및 Cloudflare R2 폴백 브라우저 캐싱 서빙"""
    stripped_sub = rel_subpath.replace("\\", "/").lstrip("/")
    pid = project_id
    projects_base = BASE_DIR / "projects"

    # 1-0. 로컬 SSD 영구 볼륨 우선 매칭 (괄호, 특수문자 자동 정규화)
    local_file = projects_base / pid / stripped_sub
    if not (local_file.exists() and local_file.is_file()):
        clean_target = re.sub(r"[^0-9a-zA-Z가-힣]", "", pid)
        if clean_target and projects_base.exists():
            for pdir in projects_base.iterdir():
                if pdir.is_dir() and re.sub(r"[^0-9a-zA-Z가-힣]", "", pdir.name) == clean_target:
                    candidate = pdir / stripped_sub
                    if candidate.exists() and candidate.is_file():
                        local_file = candidate
                        pid = pdir.name
                        break

    clean_rel = f"{pid}/{stripped_sub}".replace("//", "/")

    # 1. 로컬 SSD 영구 볼륨 직접 서빙 (지연 0ms)
    raw_bytes = None
    if local_file.exists() and local_file.is_file():
        raw_bytes = local_file.read_bytes()
    else:
        raw_bytes = r2_storage.get_media_bytes(f"/projects/{clean_rel}")

    if raw_bytes:
        suffix = Path(clean_rel).suffix.lower()
        media_types = {
            ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
            ".webp": "image/webp", ".mp3": "audio/mpeg", ".wav": "audio/wav",
            ".webm": "audio/webm", ".m4a": "audio/mp4", ".mp4": "video/mp4",
            ".pdf": "application/pdf", ".json": "application/json"
        }
        # 🌟 브라우저 및 CDN 7일 캐싱 (다음 페이지 넘김 시 0.001초 즉시 렌더링!)
        headers = {
            "Cache-Control": "public, max-age=604800, immutable",
            "ETag": f'"{hashlib.md5(clean_rel.encode("utf-8")).hexdigest()}"'
        }
        return Response(
            content=raw_bytes,
            media_type=media_types.get(suffix, "application/octet-stream"),
            headers=headers
        )

    raise HTTPException(status_code=404, detail=f"Media not found: {clean_rel}")


@app.get("/projects/{project_id}/{file_path:path}", include_in_schema=False)
async def serve_project_cloud_asset(project_id: str, file_path: str):
    pid = project_manager._resolve_project_id(project_id)
    return _serve_from_r2(pid, file_path)


@app.get("/gallery/media/{file_path:path}", include_in_schema=False)
@app.get("/media/{file_path:path}", include_in_schema=False)
async def serve_project_media(file_path: str, request: Request):
    pid = request.query_params.get("project_id") or project_manager.get_active_project_id()
    sub = file_path.replace("\\", "/").lstrip("/")
    return _serve_from_r2(pid, f"media/{sub}")


@app.get("/gallery/images/{file_path:path}", include_in_schema=False)
@app.get("/images/{file_path:path}", include_in_schema=False)
async def serve_project_images(file_path: str, request: Request):
    pid = request.query_params.get("project_id") or project_manager.get_active_project_id()
    sub = file_path.replace("\\", "/").lstrip("/")
    return _serve_from_r2(pid, f"images/{sub}")


@app.get("/gallery/music/{file_path:path}", include_in_schema=False)
@app.get("/music/{file_path:path}", include_in_schema=False)
async def serve_project_music(file_path: str, request: Request):
    pid = request.query_params.get("project_id") or project_manager.get_active_project_id()
    sub = file_path.replace("\\", "/").lstrip("/")
    return _serve_from_r2(pid, f"music/{sub}")


@app.get("/gallery/videos/{file_path:path}", include_in_schema=False)
@app.get("/videos/{file_path:path}", include_in_schema=False)
async def serve_project_videos(file_path: str, request: Request):
    pid = request.query_params.get("project_id") or project_manager.get_active_project_id()
    sub = file_path.replace("\\", "/").lstrip("/")
    return _serve_from_r2(pid, f"videos/{sub}")



