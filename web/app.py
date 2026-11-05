"""
web/app.py
StoryBook Studio 메인 FastAPI 애플리케이션 진입점
- 정적 파일(/static, /projects) 마운트
- 7대 기능별 모듈 라우터(web/routers/*) 통합 등록
- 기존 스크립트 및 테스트 코드 하위 호환을 위한 심볼 재익스포트(Re-export)
"""

from pathlib import Path
from fastapi import FastAPI, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from core.config import BASE_DIR
from web.routers import (
    auth_admin,
    projects,
    studio_poem,
    illustration,
    audio_video,
    publishing,
    thesaurus,
    inquiries,
)


app = FastAPI(
    title="StoryBook Studio",
    description="기억 기반 시화집 독립출판 웹 스튜디오"
)


# 디렉토리 경로 설정 및 보장
WEB_DIR = Path(__file__).resolve().parent
STATIC_DIR = WEB_DIR / "static"
TEMPLATES_DIR = WEB_DIR / "templates"

STATIC_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
(BASE_DIR / "projects").mkdir(parents=True, exist_ok=True)

# 정적 파일 마운트
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/projects", StaticFiles(directory=str(BASE_DIR / "projects")), name="projects")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# 7대 기능별 APIRouter 통합 등록
app.include_router(auth_admin.router, tags=["1. 인증 · 관리자 · AI 설정"])
app.include_router(projects.router, tags=["2. 시집 프로젝트 · 서재 관리"])
app.include_router(studio_poem.router, tags=["3. 시 창작 · 퇴고 · 원고 관리"])
app.include_router(illustration.router, tags=["4. 300 DPI 서정 삽화 생성"])
app.include_router(audio_video.router, tags=["5. 시낭송(TTS) · 노래 · 비디오"])
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

