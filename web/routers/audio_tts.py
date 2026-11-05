"""시낭송(Gemini/Edge 신경망 TTS · 내 목소리 육성 녹음) 및 성우 상태 관리 라우터"""

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


@router.get("/api/tts/status")
async def get_tts_status():
    """현재 TTS 엔진 상태 및 Google 크레딧 만료 여부 반환"""
    return {
        "engine": TTS_STATE["engine"],
        "gemini_credit_expired": TTS_STATE["gemini_credit_expired"],
        "last_error": TTS_STATE["last_error"],
        "error_type": TTS_STATE["error_type"]
    }

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
