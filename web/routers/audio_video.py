"""시낭송(TTS/육성 녹음), 노랫말 작사, Suno/오디오 편집, Colab YuE2 및 시네마틱 MP4 비디오 렌더링 라우터"""

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

class ImportSunoShareRequest(BaseModel):
    share_url: str
    episode_no: str
    target_type: Optional[str] = "song"  # "song" (노래 듣기) | "music_recite" (음악 시 낭송)

class RenderVideoRequest(BaseModel):
    project_id: Optional[str] = None
    episode_no: str
    title: str
    image_file: str
    audio_file: Optional[str] = None
    aspect_ratio: str = "16:9"  # "16:9" | "9:16"
    mode: str = "music"         # "music" | "recite" | "bgm"

@router.get("/api/videos")
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

@router.post("/api/videos/render")
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

        out_path = await asyncio.to_thread(
            renderer.render_episode_video,
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

@router.get("/api/videos/download/{filename}")
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

@router.post("/api/update_lyrics")
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



@router.post("/api/save_voice_recording")
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



@router.post("/api/upload_audio")
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

@router.post("/api/trim_audio")
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

@router.post("/api/import_suno_url")
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

@router.get("/api/tts/status")
async def get_tts_status():
    """현재 TTS 엔진 상태 및 Google 크레딧 만료 여부 반환"""
    return {
        "engine": TTS_STATE["engine"],
        "gemini_credit_expired": TTS_STATE["gemini_credit_expired"],
        "last_error": TTS_STATE["last_error"],
        "error_type": TTS_STATE["error_type"]
    }

@router.post("/api/tts/set_engine")
async def set_tts_engine(req: SetTtsEngineRequest):
    """사용자가 직접 TTS 엔진을 전환 (gemini | edge)"""
    if req.engine in ["gemini", "edge"]:
        TTS_STATE["engine"] = req.engine
        return {"success": True, "engine": TTS_STATE["engine"]}
    raise HTTPException(status_code=400, detail="유효하지 않은 엔진입니다.")

@router.post("/api/tts/check_google")
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

@router.post("/api/speak_poem")
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

@router.post("/api/import_suno_share")
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

    # 3. 프로젝트 music 폴더에 자동 영구 저장 (음악 시 낭송 vs 노래 듣기 구분)
    clean_ep = re.sub(r'[^0-9]', '', req.episode_no).zfill(2) if req.episode_no else "01"
    project_dir = project_manager.get_project_dir()
    music_dir = project_dir / "music"
    music_dir.mkdir(parents=True, exist_ok=True)
    
    is_music_recite = (getattr(req, "target_type", "") == "music_recite")
    music_filename = f"{clean_ep}_음악낭송.mp3" if is_music_recite else f"{clean_ep}_음원.mp3"
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



# =========================================================================
# =========================================================================
# [StoryBook Studio] 시화 낭송 영상 (Poem Video) 제작 연동 API 엔드포인트
# =========================================================================

class PoemVideoRenderRequest(BaseModel):
    project_name: Optional[str] = None
    episode_no: Any = 1
    audio_type: str = "tts"  # "tts", "recording", "suno"
    custom_audio_path: Optional[str] = None
    aspect_ratio: str = "16:9"  # "16:9" | "9:16"
    spectrum_style: str = "bar"  # "bar" | "mirror" | "wave" | "off"


@router.get("/api/poem_video/status/{project_name}/{episode_no}")
async def get_poem_video_status_endpoint(project_name: str, episode_no: str):
    """특정 회차의 영상 제작 상태 및 오디오/삽화 리소스 상태 조회"""
    try:
        from core.project_manager import project_manager
        ep_digits = re.sub(r'[^0-9]', '', str(episode_no))
        ep_num = int(ep_digits) if ep_digits else 1
        ep_str = f"{ep_num:02d}"

        project_dir = project_manager.get_project_dir(project_name)
        if not project_dir.exists():
            project_dir = project_manager.get_project_dir()
            project_name = project_dir.name
        videos_dir = project_dir / "videos"
        music_dir = project_dir / "music"
        images_dir = project_dir / "images"

        video_info = {"exists": False}
        if videos_dir.exists():
            matched_videos = list(videos_dir.glob(f"{ep_str}_*.mp4"))
            if matched_videos:
                latest_v = max(matched_videos, key=os.path.getmtime)
                size_mb = round(os.path.getsize(latest_v) / (1024 * 1024), 2)
                preview_f = latest_v.with_name(latest_v.stem + "_preview.png")
                video_info = {
                    "exists": True,
                    "filename": latest_v.name,
                    "size_mb": size_mb,
                    "url": f"/api/poem_video/stream/{project_name}/{latest_v.name}",
                    "has_preview": preview_f.exists()
                }

        # 3대 낭송 음원 상세 탐색 (최대 3개: 1. 육성 시 낭송, 2. AI 시 낭송, 3. 음악 시 낭송)
        safe_proj = project_name.replace(" ", "_")
        recite_tracks = []

        # 1) 육성 시 낭송
        voice_track = None
        for ext in ["wav", "mp3", "webm", "m4a"]:
            cand = music_dir / f"{ep_str}_육성.{ext}"
            if cand.exists():
                voice_track = {
                    "type": "voice",
                    "label": "육성 시 낭송",
                    "icon": "🎙️",
                    "filename": cand.name,
                    "rel_path": f"music/{cand.name}",
                    "url": f"/projects/{safe_proj}/music/{cand.name}",
                    "exists": True
                }
                break
        if voice_track:
            recite_tracks.append(voice_track)

        # 2) AI 시 낭송
        ai_track = None
        for ext in ["wav", "mp3", "m4a"]:
            for tag in ["낭송", "AI낭송"]:
                cand = music_dir / f"{ep_str}_{tag}.{ext}"
                if cand.exists():
                    ai_track = {
                        "type": "ai_recite",
                        "label": "AI 시 낭송",
                        "icon": "🤖",
                        "filename": cand.name,
                        "rel_path": f"music/{cand.name}",
                        "url": f"/projects/{safe_proj}/music/{cand.name}",
                        "exists": True
                    }
                    break
            if ai_track:
                break
        if ai_track:
            recite_tracks.append(ai_track)

        # 3) 음악 시 낭송
        music_recite_track = None
        for ext in ["mp3", "m4a", "wav"]:
            for tag in ["음악낭송", "음악시낭송"]:
                cand = music_dir / f"{ep_str}_{tag}.{ext}"
                if cand.exists():
                    music_recite_track = {
                        "type": "music_recite",
                        "label": "음악 시 낭송",
                        "icon": "🎻",
                        "filename": cand.name,
                        "rel_path": f"music/{cand.name}",
                        "url": f"/projects/{safe_proj}/music/{cand.name}",
                        "exists": True
                    }
                    break
            if music_recite_track:
                break
        if music_recite_track:
            recite_tracks.append(music_recite_track)

        # 기본 선택된 음원
        detected_audio = recite_tracks[0]["filename"] if recite_tracks else None
        detected_path = recite_tracks[0]["rel_path"] if recite_tracks else None

        img_exists = any((images_dir / f"{ep_str}_삽화.{ext}").exists() for ext in ["jpg", "jpeg", "png"]) or any(len(list(images_dir.glob(f"{ep_str}_*.{ext}"))) > 0 for ext in ["jpg", "jpeg", "png"])

        return {
            "success": True,
            "episode_no": ep_num,
            "video": video_info,
            "detected_audio": detected_audio,
            "detected_path": detected_path,
            "recite_tracks": recite_tracks,
            "sources": {
                "has_audio": len(recite_tracks) > 0,
                "audio_name": detected_audio or "낭송 음원 없음",
                "audio_count": len(recite_tracks),
                "image": img_exists
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/api/poem_video/render")
async def render_poem_video_endpoint(req: PoemVideoRenderRequest):
    """시화 영상 비디오 엔진 호출 (비동기 백그라운드)"""
    try:
        from core.video_director_bridge import video_director_bridge
        from core.project_manager import project_manager

        project_name = req.project_name
        if not project_name:
            info = project_manager.get_active_project_info()
            project_name = info.name if info else "노을빛_기억"

        ep_digits = re.sub(r'[^0-9]', '', str(req.episode_no))
        ep_num = int(ep_digits) if ep_digits else 1
        ep_str = f"{ep_num:02d}"

        project_dir = project_manager.get_project_dir(project_name)
        images_dir = project_dir / "images"
        music_dir = project_dir / "music"

        mgr = project_manager.get_manuscript_manager(project_name)
        work = mgr.get_work_by_episode(str(ep_num))
        if not work:
            work = mgr.get_work_by_episode(f"제{ep_str}화")

        title = work.title if (work and work.title) else f"제{ep_num}화"
        poem_body = (work.poem_body or "") if work else ""
        poem_lines = [line.strip() for line in poem_body.splitlines() if line.strip()]

        if not poem_lines:
            raise ValueError(f"제{ep_num}화의 시 본문 원고가 없습니다.")

        # 1. 삽화 이미지 찾기
        img_path = None
        if work and getattr(work, 'image_file', '') and (project_dir / work.image_file).exists():
            img_path = str(project_dir / work.image_file)
        else:
            for ext in ["jpg", "jpeg", "png"]:
                cand = images_dir / f"{ep_str}_삽화.{ext}"
                if cand.exists():
                    img_path = str(cand)
                    break
            if not img_path:
                for cand in sorted(images_dir.glob(f"{ep_str}_*")):
                    if cand.suffix.lower() in [".jpg", ".jpeg", ".png"] and not cand.name.endswith("_preview.png"):
                        img_path = str(cand)
                        break

        if not img_path:
            raise FileNotFoundError(f"제{ep_num}화의 삽화 이미지가 없습니다. (images/{ep_str}_*.jpg)")

        # 2. 낭송 음원 탐색 (선택된 트랙 또는 자동 탐색)
        audio_path = None
        if req.custom_audio_path:
            clean_c = req.custom_audio_path.replace("./", "").lstrip("/")
            if (project_dir / clean_c).exists():
                audio_path = str(project_dir / clean_c)
            elif os.path.exists(req.custom_audio_path):
                audio_path = req.custom_audio_path
            elif (music_dir / Path(clean_c).name).exists():
                audio_path = str(music_dir / Path(clean_c).name)

        if not audio_path and work and getattr(work, "recite_file", "") and (project_dir / work.recite_file).exists():
            audio_path = str(project_dir / work.recite_file)

        if not audio_path:
            for ext in ["wav", "mp3", "m4a", "webm"]:
                cand = music_dir / f"{ep_str}_낭송.{ext}"
                if cand.exists():
                    audio_path = str(cand)
                    break
        if not audio_path:
            for ext in ["wav", "mp3", "m4a", "webm"]:
                cand = music_dir / f"{ep_str}_육성.{ext}"
                if cand.exists():
                    audio_path = str(cand)
                    break
        if not audio_path and work and getattr(work, "music_file", "") and (project_dir / work.music_file).exists():
            audio_path = str(project_dir / work.music_file)
        if not audio_path:
            for cand in sorted(music_dir.glob(f"{ep_str}_*")):
                if cand.suffix.lower() in [".mp3", ".wav", ".m4a", ".webm"] and not cand.name.endswith("_backup.mp3"):
                    audio_path = str(cand)
                    break

        if not audio_path:
            raise FileNotFoundError(f"제{ep_num}화의 음원 파일이 없습니다. (TTS 낭송 또는 Suno 음원을 확인해 주세요)")

        res = video_director_bridge.render_poem_video(
            project_name=project_name,
            episode_num=ep_num,
            title=title,
            poem_lines=poem_lines,
            image_path=img_path,
            audio_path=audio_path,
            aspect_ratio=req.aspect_ratio,
            spectrum_style=req.spectrum_style,
            is_async=True
        )

        return {
            "success": True,
            "task_id": res.get("task_id"),
            "title": title,
            "audio_used": os.path.basename(audio_path)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/api/poem_video/task/{task_id}")
async def get_poem_video_task_endpoint(task_id: str):
    """영상 렌더링 백그라운드 작업 상태 조회"""
    from core.video_director_bridge import video_director_bridge
    status = video_director_bridge.get_task_status(task_id)
    return {"success": True, "task": status}


@router.post("/api/poem_video/upload_custom_audio")
async def upload_custom_audio_endpoint(
    project_name: str = Form(...),
    episode_no: str = Form(...),
    audio_file: UploadFile = File(...)
):
    """
    [앱 표준 파일 탐색기 연동] 사용자가 직접 녹음 파일/Suno 파일 업로드
    해당 회차의 공식 음원(projects/{project}/music/{ep:02d}_음원{ext})으로 자동 등록
    """
    try:
        from core.project_manager import project_manager
        ep_digits = re.sub(r'[^0-9]', '', str(episode_no))
        ep_num = int(ep_digits) if ep_digits else 1
        ep_str = f"{ep_num:02d}"

        project_dir = project_manager.get_project_dir(project_name)
        music_dir = project_dir / "music"
        music_dir.mkdir(parents=True, exist_ok=True)

        ext = Path(audio_file.filename).suffix.lower()
        if ext not in [".mp3", ".wav", ".m4a", ".ogg", ".webm"]:
            ext = ".mp3"

        target_path = music_dir / f"{ep_str}_음원{ext}"

        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(audio_file.file, buffer)

        return {
            "success": True,
            "filename": target_path.name,
            "path": str(target_path),
            "size_bytes": os.path.getsize(target_path)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/api/poem_video/open_music_folder")
async def open_music_folder_endpoint(project_name: str = Form(...)):
    """[앱 표준] 프로젝트의 음악 폴더를 윈도우 탐색기로 열기"""
    try:
        from core.project_manager import project_manager
        project_dir = project_manager.get_project_dir(project_name)
        music_dir = project_dir / "music"
        music_dir.mkdir(parents=True, exist_ok=True)

        if os.name == 'nt':
            subprocess.Popen(["explorer", str(music_dir.resolve())])
            return {"success": True, "message": "음악 폴더를 열었습니다."}
        else:
            return {"success": False, "error": "윈도우 탐색기 전용 기능입니다."}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/api/poem_video/stream/{project_name}/{filename}")
async def stream_poem_video_endpoint(project_name: str, filename: str):
    """완성된 MP4 영상을 브라우저로 스트리밍"""
    from core.project_manager import project_manager
    project_dir = project_manager.get_project_dir(project_name)
    video_path = project_dir / "videos" / filename
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="비디오 파일을 찾을 수 없습니다.")
    return FileResponse(
        path=str(video_path),
        media_type="video/mp4",
        filename=filename
    )


class MergePlaylistRequest(BaseModel):
    project_name: Optional[str] = None
    aspect_ratio: str = "16:9"


@router.post("/api/poem_video/merge_playlist")
async def merge_poem_video_playlist_endpoint(req: MergePlaylistRequest):
    """프로젝트 내 완성된 영상들을 하나의 전편 플레이리스트 영상으로 초고속 무손실 결합"""
    try:
        from core.video_director_bridge import video_director_bridge
        from core.project_manager import project_manager

        project_name = req.project_name
        if not project_name:
            info = project_manager.get_active_project_info()
            project_name = info.name if info else "노을빛_기억"

        res = video_director_bridge.merge_playlist_video(
            project_name=project_name,
            aspect_ratio=req.aspect_ratio
        )
        return res
    except Exception as e:
        return {"success": False, "error": str(e)}


# =========================================================================
# [StoryBook Studio] 서정 노래 영상 (Song Video) 제작 연동 API 엔드포인트
# =========================================================================

class SongVideoRenderRequest(BaseModel):
    project_name: Optional[str] = None
    episode_no: Any = 1
    lyrics_text: str
    custom_audio_path: Optional[str] = None
    custom_srt_path: Optional[str] = None
    aspect_ratio: str = "16:9"  # "16:9" | "9:16"
    spectrum_style: str = "mirror"  # "mirror" | "wave" | "bar" | "off"
    lyric_mode: str = "focus2line"  # "focus2line" | "rolling"


@router.get("/api/song_video/status/{project_name}/{episode_no}")
async def get_song_video_status_endpoint(project_name: str, episode_no: str):
    """특정 회차의 노래 영상 제작 상태, 음원 및 가사 리소스 상태 조회"""
    try:
        from core.project_manager import project_manager
        ep_digits = re.sub(r'[^0-9]', '', str(episode_no))
        ep_num = int(ep_digits) if ep_digits else 1
        ep_str = f"{ep_num:02d}"

        project_dir = project_manager.get_project_dir(project_name)
        if not project_dir.exists():
            project_dir = project_manager.get_project_dir()
            project_name = project_dir.name
        videos_dir = project_dir / "videos"
        music_dir = project_dir / "music"
        images_dir = project_dir / "images"

        video_info = {"exists": False}
        if videos_dir.exists():
            matched_videos = list(videos_dir.glob(f"{ep_str}_*노래*.mp4"))
            if matched_videos:
                latest_v = max(matched_videos, key=os.path.getmtime)
                size_mb = round(os.path.getsize(latest_v) / (1024 * 1024), 2)
                preview_f = latest_v.with_name(latest_v.stem + "_preview.png")
                video_info = {
                    "exists": True,
                    "filename": latest_v.name,
                    "size_mb": size_mb,
                    "url": f"/api/poem_video/stream/{project_name}/{latest_v.name}",
                    "has_preview": preview_f.exists()
                }

        # 1. 해당 회차 노래 음원 자동 감지
        mgr = project_manager.get_manuscript_manager(project_name)
        work = mgr.get_work_by_episode(str(ep_num))
        if not work:
            work = mgr.get_work_by_episode(f"제{ep_str}화")

        detected_audio = None
        if work and getattr(work, "music_file", "") and (project_dir / work.music_file).exists():
            detected_audio = Path(work.music_file).name
        if not detected_audio:
            for ext in ["mp3", "wav", "m4a", "webm"]:
                cand = music_dir / f"{ep_str}_노래.{ext}"
                if cand.exists():
                    detected_audio = cand.name
                    break
        if not detected_audio:
            for ext in ["mp3", "wav", "m4a", "webm"]:
                cand = music_dir / f"{ep_str}_음악.{ext}"
                if cand.exists():
                    detected_audio = cand.name
                    break
        if not detected_audio:
            # Suno 관련 파일 또는 번호로 시작하는 일반 음악 파일
            for cand in sorted(music_dir.glob(f"{ep_str}_*")):
                if cand.suffix.lower() in [".mp3", ".wav", ".m4a", ".webm"] and not cand.name.endswith("_backup.mp3") and "낭송" not in cand.name and "육성" not in cand.name:
                    detected_audio = cand.name
                    break

        img_exists = any((images_dir / f"{ep_str}_삽화.{ext}").exists() for ext in ["jpg", "jpeg", "png"]) or any(len(list(images_dir.glob(f"{ep_str}_*.{ext}"))) > 0 for ext in ["jpg", "jpeg", "png"])

        # 2. 기본 가사 초안 (작사 노랫말 -> 없으면 시 원문)
        initial_lyrics = ""
        if work:
            initial_lyrics = (getattr(work, "lyrics", "") or "").strip()
            if not initial_lyrics:
                initial_lyrics = (getattr(work, "poem_body", "") or "").strip()

        return {
            "success": True,
            "episode_no": ep_num,
            "video": video_info,
            "detected_audio": detected_audio,
            "lyrics": initial_lyrics,
            "sources": {
                "has_audio": detected_audio is not None,
                "audio_name": detected_audio or "노래 음원 없음",
                "image": img_exists
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/api/song_video/render")
async def render_song_video_endpoint(req: SongVideoRenderRequest):
    """서정 노래 영상 비디오 엔진 호출 (비동기 백그라운드)"""
    try:
        from core.video_director_bridge import video_director_bridge
        from core.project_manager import project_manager

        project_name = req.project_name
        if not project_name:
            info = project_manager.get_active_project_info()
            project_name = info.name if info else "노을빛_기억"

        ep_digits = re.sub(r'[^0-9]', '', str(req.episode_no))
        ep_num = int(ep_digits) if ep_digits else 1
        ep_str = f"{ep_num:02d}"

        project_dir = project_manager.get_project_dir(project_name)
        images_dir = project_dir / "images"
        music_dir = project_dir / "music"

        mgr = project_manager.get_manuscript_manager(project_name)
        work = mgr.get_work_by_episode(str(ep_num))
        if not work:
            work = mgr.get_work_by_episode(f"제{ep_str}화")

        title = work.title if (work and work.title) else f"제{ep_num}화"

        # 1. 가사 줄(line) 정제
        raw_lyrics = req.lyrics_text.strip()
        if not raw_lyrics:
            raise ValueError(f"제{ep_num}화의 노래 가사가 비어 있습니다.")

        # [Verse], [Chorus], (Guitar Solo) 등 메타태그 및 음악 지시어 스마트 정제
        lyrics_lines = []
        meta_line_pattern = re.compile(
            r'^\s*\[.*?\]\s*$|^\s*\((?:intro|verse|chorus|outro|bridge|hook|solo|guitar|piano|instrumental|간주|후렴|전주|후주).*?\)\s*$',
            re.IGNORECASE
        )
        for line in raw_lyrics.splitlines():
            l_str = line.strip()
            if not l_str or meta_line_pattern.match(l_str):
                continue
            # 라인 내부에 섞인 [Chorus] 등 대괄호 및 소괄호 지시어 제거
            clean_l = re.sub(r'\[.*?\]', '', l_str)
            clean_l = re.sub(r'\((?:intro|verse|chorus|outro|bridge|hook|solo|guitar|piano|instrumental|간주|후렴|전주|후주).*?\)', '', clean_l, flags=re.IGNORECASE).strip()
            if clean_l:
                lyrics_lines.append(clean_l)

        if not lyrics_lines:
            raise ValueError("가사 본문 줄이 존재하지 않습니다. ([Intro] 등 설명어 외에 실제 가사를 입력해 주세요)")

        # 노랫말 최신 상태 ManuscriptManager에 영구 동기화
        if work:
            work.lyrics = raw_lyrics
            mgr.save_work(work)

        # 2. 삽화 이미지 찾기
        img_path = None
        if work and getattr(work, 'image_file', '') and (project_dir / work.image_file).exists():
            img_path = str(project_dir / work.image_file)
        else:
            for ext in ["jpg", "jpeg", "png"]:
                cand = images_dir / f"{ep_str}_삽화.{ext}"
                if cand.exists():
                    img_path = str(cand)
                    break
            if not img_path:
                for cand in sorted(images_dir.glob(f"{ep_str}_*")):
                    if cand.suffix.lower() in [".jpg", ".jpeg", ".png"] and not cand.name.endswith("_preview.png"):
                        img_path = str(cand)
                        break

        if not img_path:
            raise FileNotFoundError(f"제{ep_num}화의 삽화 이미지가 없습니다.")

        # 3. 노래 음원 찾기
        audio_path = None
        if req.custom_audio_path and os.path.exists(req.custom_audio_path):
            audio_path = req.custom_audio_path
        elif work and getattr(work, "music_file", "") and (project_dir / work.music_file).exists():
            audio_path = str(project_dir / work.music_file)

        if not audio_path:
            for ext in ["mp3", "wav", "m4a", "webm"]:
                cand = music_dir / f"{ep_str}_노래.{ext}"
                if cand.exists():
                    audio_path = str(cand)
                    break
        if not audio_path:
            for ext in ["mp3", "wav", "m4a", "webm"]:
                cand = music_dir / f"{ep_str}_음악.{ext}"
                if cand.exists():
                    audio_path = str(cand)
                    break
        if not audio_path:
            for cand in sorted(music_dir.glob(f"{ep_str}_*")):
                if cand.suffix.lower() in [".mp3", ".wav", ".m4a", ".webm"] and not cand.name.endswith("_backup.mp3") and "낭송" not in cand.name and "육성" not in cand.name:
                    audio_path = str(cand)
                    break

        if not audio_path:
            raise FileNotFoundError(f"제{ep_num}화의 노래 음원 파일이 없습니다. (Suno 생성 음원 또는 작곡 음원을 등록해 주세요)")

        res = video_director_bridge.render_song_video(
            project_name=project_name,
            episode_num=ep_num,
            title=title,
            lyrics_lines=lyrics_lines,
            image_path=img_path,
            audio_path=audio_path,
            custom_srt_path=req.custom_srt_path,
            aspect_ratio=req.aspect_ratio,
            spectrum_style=req.spectrum_style,
            lyric_mode=req.lyric_mode,
            is_async=True
        )

        return {
            "success": True,
            "task_id": res.get("task_id"),
            "title": title,
            "audio_used": os.path.basename(audio_path)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
