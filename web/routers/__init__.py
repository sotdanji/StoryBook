"""StoryBook Studio FastAPI 모듈형 라우터 패키지"""
from web.routers import (
    auth_admin,
    projects,
    studio_poem,
    illustration,
    audio_video,
    publishing,
    thesaurus,
)

__all__ = [
    "auth_admin",
    "projects",
    "studio_poem",
    "illustration",
    "audio_video",
    "publishing",
    "thesaurus",
]
