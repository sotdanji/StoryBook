"""노랫말 운율화(작사), 노래 음원 업로드/트리밍, Colab YuE2 작곡 노트북 라우터"""

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

from core.config import GEMINI_API_KEY
from core.project_manager import project_manager
from core.csv_builder import build_canva_csv
from core.colab_builder import build_yue2_notebook_dict, DEFAULT_GENRE_PROMPT
from core.audio_processor import clean_and_optimize_audio, trim_audio_manually, parse_time_to_seconds

WEB_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = WEB_DIR / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter()


class LyricsGenerateRequest(BaseModel):
    title: str
    poem_body: str
    genre: Optional[str] = "minyo"
    custom_guide: Optional[str] = ""

class ColabNotebookRequest(BaseModel):
    episode_no: str
    title: str
    genre_prompt: Optional[str] = ""
    lyrics: Optional[str] = ""


class TrimAudioRequest(BaseModel):
    episode_no: str
    start_time: str = "00:00"
    end_time: str = ""

@router.post("/api/generate_lyrics")
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


@router.post("/api/upload_audio")
async def upload_audio_endpoint(
    audio_file: UploadFile = File(...),
    episode_no: str = Form(...),
    lyrics: Optional[str] = Form(None)
):
    """
    [100% 서버 일원화]
    사용자가 외부 AI(Colab YuE2, Suno 등)나 웹 녹음기에서 녹음한 오디오 파일을
    /tmp 임시 버퍼에서 앞뒤 무음 자동 검사/트리밍 및 320kbps MP3로 최적화한 뒤
    Cloudflare R2에 업로드하고 Turso DB에 동기화합니다.
    """
    import tempfile
    from core.r2_storage import r2_storage
    try:
        active_id = project_manager.get_active_project_id()
        orig_name = Path(audio_file.filename or "song.mp3").name
        clean_ep = re.sub(r'[^0-9]', '', episode_no).zfill(2) if episode_no else "01"
        safe_name = f"{clean_ep}_음원.mp3"
        rel_path = f"music/{safe_name}"

        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            temp_upload = tmp_dir / f"upload_tmp_{orig_name}"
            target_path = tmp_dir / safe_name

            with open(temp_upload, "wb") as buffer:
                shutil.copyfileobj(audio_file.file, buffer)

            proc_result = clean_and_optimize_audio(temp_upload, target_path)
            opt_bytes = target_path.read_bytes() if target_path.exists() else temp_upload.read_bytes()

        r2_storage.upload_bytes(opt_bytes, f"{active_id}/{rel_path}", content_type="audio/mpeg")
        web_url = f"/projects/{active_id}/{rel_path}?t={int(time.time())}"

        # Turso DB에 music_file 경로 및 가사(lyrics) 자동 업데이트
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

@router.post("/api/trim_audio")
async def trim_audio_endpoint(req: TrimAudioRequest):
    """지정한 회차의 음원을 R2에서 /tmp로 가져와 수동 트리밍 후 다시 R2에 업로드"""
    import tempfile
    from core.r2_storage import r2_storage
    try:
        active_id = project_manager.get_active_project_id()
        clean_ep = re.sub(r'[^0-9]', '', req.episode_no).zfill(2) if req.episode_no else "01"
        safe_name = f"{clean_ep}_음원.mp3"
        rel_path = f"music/{safe_name}"

        raw_bytes = r2_storage.get_media_bytes(f"/projects/{active_id}/{rel_path}")
        if not raw_bytes:
            mgr = project_manager.get_active_manuscript_manager()
            work = mgr.get_work_by_episode(req.episode_no)
            if work and getattr(work, "music_file", ""):
                rel_path = work.music_file.lstrip("./")
                safe_name = Path(rel_path).name
                raw_bytes = r2_storage.get_media_bytes(f"/projects/{active_id}/{rel_path}")

        if not raw_bytes:
            return {"success": False, "error": f"{req.episode_no}의 등록된 음원 파일을 찾을 수 없습니다."}

        start_sec = parse_time_to_seconds(req.start_time) or 0.0
        end_sec = parse_time_to_seconds(req.end_time) if req.end_time else None

        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            target_path = tmp_dir / safe_name
            target_path.write_bytes(raw_bytes)
            res = trim_audio_manually(target_path, start_sec=start_sec, end_sec=end_sec)
            if res["success"] and target_path.exists():
                r2_storage.upload_bytes(target_path.read_bytes(), f"{active_id}/{rel_path}", content_type="audio/mpeg")

        if res["success"]:
            web_url = f"/projects/{active_id}/{rel_path}?t={int(time.time())}"
            return {
                "success": True,
                "message": res["message"],
                "new_duration": res["new_duration"],
                "new_duration_str": res["new_duration_str"],
                "web_url": web_url,
                "filename": safe_name
            }
        else:
            return {"success": False, "error": res["message"]}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.post("/api/export_colab_notebook")
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

