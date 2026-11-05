"""시낭송(audio_tts) · 노래 음원(music_song) · 시화 영상(video_studio) 통합 라우터"""

from fastapi import APIRouter
from web.routers import audio_tts, music_song, video_studio

router = APIRouter()
router.include_router(audio_tts.router)
router.include_router(music_song.router)
router.include_router(video_studio.router)
