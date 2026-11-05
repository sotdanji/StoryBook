"""300 DPI 서정 삽화 프롬프트, 무료/Gemini 이미지 생성(1부/2부), 시안 선택, 업로드 및 해상도 검사 라우터"""

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
from core.book_spec import inspect_images
from core.image_optimizer import ensure_300dpi_image
from core.poetic_engine import poetic_engine
from core.colab_image_builder import build_sdxl_image_notebook_dict

WEB_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = WEB_DIR / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter()


class ImagePromptRequest(BaseModel):
    title: str
    poem_body: str
    core_memory: Optional[str] = ""
    sensory_details: Optional[str] = ""
    style_mode: Optional[str] = "literal"
    art_style: Optional[str] = "watercolor"
    custom_guide: Optional[str] = ""

class ColabImageNotebookRequest(BaseModel):
    episode_no: str
    title: str
    prompt: Optional[str] = ""
    art_style: Optional[str] = "watercolor"
    width: Optional[int] = 768
    height: Optional[int] = 1024

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
    page_num: Optional[int] = None
    frame_idx: Optional[int] = None

class GeneratePart2ImageRequest(BaseModel):
    episode_no: str
    title: Optional[str] = ""
    memory_anchor: Optional[str] = ""
    prompt: Optional[str] = ""
    custom_guide: Optional[str] = ""
    reference_image: Optional[str] = None
    direct_use_photo: Optional[bool] = False
    art_style: Optional[str] = "watercolor"
    base_image_filename: Optional[str] = None
    use_current_as_base: Optional[bool] = True

@router.post("/api/generate_image_prompt")
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

@router.post("/api/export_colab_image_notebook")
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
@router.post("/api/generate_image_free")
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

def _generate_art_image_bytes(
    prompt_str: str,
    seed_val: int,
    art_style: str = "watercolor",
    ref_image_bytes: Optional[bytes] = None,
    custom_guide: str = "",
    title: str = "",
    memory_anchor: str = "",
    modular_dict: Optional[Dict[str, Any]] = None
) -> bytes:
    """
    300 DPI 출판용 마스터 삽화를 비동기/고속으로 생성합니다.
    ★ 1순위 (최우선 직행) : Google Gemini / Imagen 3 (API 키 연결 시 한국어/정서 1위 엔진 즉시 가동)
    ★ 2순위 (무료 폴백) : Pollinations AI flux/default (API 키 미등록자 또는 할당량 초과 시 오픈 서버)
    ★ 3순위 (보조 폴백) : Pollinations AI turbo
    """
    from core.skill_pack import build_modular_art_prompt
    import io
    from PIL import Image

    if modular_dict:
        modular = modular_dict
    else:
        modular = build_modular_art_prompt(
            prompt_str,
            art_style=art_style,
            custom_guide=custom_guide,
            title=title,
            memory_anchor=memory_anchor
        )
    style_name_ko = modular["name_ko"]
    clean_scene = modular["clean_scene"]
    gemini_contents = modular["gemini_ko_content"]
    guarded_prompt = modular["guarded_en_prompt"]
    negative_en = modular["negative_en"]

    # ========================================================
    # ★ 1순위 (최우선) : Google Gemini / Imagen 3 (API 키 연결 시)
    # ========================================================
    api_key = os.getenv("GEMINI_API_KEY") or GEMINI_API_KEY
    if api_key and genai:
        print(f"[1순위 Google Gemini/Imagen: 화풍={style_name_ko}] 모듈러 스킬 블록으로 [{style_name_ko}] 삽화를 생성합니다.")
        try:
            client = genai.Client(api_key=api_key)

            # A. Imagen 3 공식 생성 시도 (순수 텍스트 프롬프트인 경우)
            if not ref_image_bytes:
                try:
                    res = client.models.generate_images(
                        model="imagen-3.0-generate-002",
                        prompt=guarded_prompt,
                        config=dict(
                            number_of_images=1,
                            output_mime_type="image/jpeg",
                            aspect_ratio="3:4"
                        )
                    )
                    if res and res.generated_images:
                        img_bytes = res.generated_images[0].image.image_bytes
                        print(f"[Google Imagen 3 성공] [{style_name_ko}] 삽화 생성 완료 ({len(img_bytes)} bytes)")
                        return img_bytes
                except Exception as img_err:
                    print(f"[Google Imagen 3 미지원/호출 실패, 다음 시도]: {img_err}")

            # B. Multimodal Image-to-Image 또는 Gemini Flash Image 시도
            image_models = ["imagen-3.0-generate-002", "gemini-2.5-flash-image", "gemini-3.1-flash-image", "gemini-2.0-flash-exp"]
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
                    continue
        except Exception as gemini_err:
            print(f"[Gemini 1순위 일시 불가, 2순위 무료 오픈 AI로 자동 전환]: {gemini_err}")

    # ========================================================
    # ★ 2순위 (무료 폴백) : Pollinations AI (Flux 우선 고화질)
    # 화풍 고유의 Negative 프롬프트(타 화풍 배제)를 주입하여 화풍 혼입을 원천 차단
    # ========================================================
    print(f"[2순위 무료 오픈 AI 전환: 화풍={style_name_ko}] Pollinations 엔진으로 모듈러 블록 삽화를 생성합니다.")
    encoded = urllib.parse.quote(guarded_prompt)
    neg_param = urllib.parse.quote(negative_en)

    candidate_urls = [
        f"https://image.pollinations.ai/prompt/{encoded}?width=768&height=1024&nologo=true&seed={seed_val}&model=flux&negative={neg_param}",
        f"https://image.pollinations.ai/prompt/{encoded}?width=768&height=1024&nologo=true&seed={seed_val}&negative={neg_param}",
        f"https://image.pollinations.ai/prompt/{encoded}?width=768&height=1024&nologo=true&seed={seed_val}&model=turbo&negative={neg_param}"
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

def _download_and_save_candidate(
    prompt_str: str,
    seed_val: int,
    file_path: Path,
    art_style: str = "watercolor",
    ref_image_bytes: Optional[bytes] = None,
    custom_guide: str = "",
    title: str = "",
    memory_anchor: str = "",
    modular_dict: Optional[Dict[str, Any]] = None
):
    img_bytes = _generate_art_image_bytes(
        prompt_str,
        seed_val,
        art_style=art_style,
        ref_image_bytes=ref_image_bytes,
        custom_guide=custom_guide,
        title=title,
        memory_anchor=memory_anchor,
        modular_dict=modular_dict
    )
    ensure_300dpi_image(img_bytes, file_path)

@router.post("/api/generate_image_candidates")
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
        custom_guide = (req.custom_guide or "").strip()

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
        from core.skill_pack import build_modular_art_prompt
        
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
        await asyncio.to_thread(
            _download_and_save_candidate,
            modular["clean_scene"],
            seed,
            target_path,
            art_style=art_style,
            ref_image_bytes=ref_bytes,
            custom_guide=custom_guide,
            title=p_title,
            memory_anchor=p_memory,
            modular_dict=modular
        )

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

@router.post("/api/select_image_candidate")
async def select_image_candidate(req: SelectImageCandidateRequest):
    """
    모달 팝업에서 사용자가 선택한 시안을 최종 공식 삽화로 확정 반영합니다.
    (1면, 2면, 3면, 4면 및 1번/2번 분할 프레임 독립 저장 지원)
    """
    clean_ep = re.sub(r'[^0-9]', '', req.episode_no).zfill(2)
    images_dir = project_manager.get_active_images_dir()
    cand_path = images_dir / req.candidate_filename

    if not cand_path.exists():
        raise HTTPException(status_code=404, detail="선택한 시안 이미지 파일을 찾을 수 없습니다.")

    p_num = req.page_num
    f_idx = req.frame_idx or 1
    is_part2 = (req.target_slot == "part2") or (p_num is not None and p_num >= 3)

    if p_num == 1 and f_idx == 1:
        final_filename = f"{clean_ep}_삽화.jpg"
    elif p_num == 3 and f_idx == 1:
        final_filename = f"{clean_ep}_삽화_후반.jpg"
    elif p_num is not None:
        suffix = f"_{p_num}면" + (f"_{f_idx}" if f_idx > 1 else "")
        final_filename = f"{clean_ep}_삽화{suffix}.jpg"
    else:
        final_filename = f"{clean_ep}_삽화_후반.jpg" if is_part2 else f"{clean_ep}_삽화.jpg"

    final_path = images_dir / final_filename

    # 선택된 시안을 최종 삽화 파일로 복사
    shutil.copyfile(cand_path, final_path)

    # 원고(작품집_원고.md)의 해당 회차 이미지 파일명 및 layout_config.pages 갱신
    mgr = project_manager.get_active_manuscript_manager()
    works = mgr.load_works()
    for w in works:
        if clean_ep in w.episode_no or w.episode_no.strip() == req.episode_no.strip():
            cfg = dict(w.layout_config) if getattr(w, 'layout_config', None) else {}
            pages = list(cfg.get("pages", []))
            target_idx = (p_num - 1) if (p_num is not None and p_num > 0) else (2 if is_part2 else 0)

            while len(pages) <= target_idx:
                curr_p = len(pages) + 1
                pages.append({
                    "page_num": curr_p,
                    "usage": "image" if curr_p == 1 else ("image_text" if curr_p == 3 else "text"),
                    "role": "none" if curr_p == 1 else ("start" if curr_p == 2 else "continue"),
                    "image_file": "",
                    "custom_text": ""
                })

            if f_idx == 2:
                pages[target_idx]["image_file_b"] = f"./images/{final_filename}"
            else:
                pages[target_idx]["image_file"] = f"./images/{final_filename}"

            if pages[target_idx].get("usage") == "text":
                pages[target_idx]["usage"] = "image_text"

            cfg["pages"] = pages
            if "slots" in cfg and len(cfg["slots"]) > target_idx:
                cfg["slots"][target_idx] = pages[target_idx]["usage"]

            w.layout_config = cfg

            if target_idx == 0 and f_idx == 1:
                w.image_file = f"./images/{final_filename}"
            elif target_idx == 2 and f_idx == 1:
                w.image_file_2 = f"./images/{final_filename}"
                w.part2_mode = "image"
                w.layout_mode = "multi_page"
            elif is_part2 and not getattr(w, "image_file_2", None):
                w.image_file_2 = f"./images/{final_filename}"
                w.part2_mode = "image"
                w.layout_mode = "multi_page"

            mgr.save_work(w)
            break

    try:
        build_canva_csv()
    except Exception:
        pass

    now_t = int(time.time())
    page_desc = f"{p_num}면 {f_idx}번 " if p_num else ("2부 연작 삽화(4면)" if is_part2 else "1부 본 삽화(2면)")
    return {
        "success": True,
        "filename": final_filename,
        "target_slot": req.target_slot or "part1",
        "page_num": p_num,
        "frame_idx": f_idx,
        "image_url": f"/images/{final_filename}?t={now_t}",
        "message": f"[{req.episode_no}] 선택하신 그림이 {page_desc}삽화로 성공적으로 반영되었습니다!"
    }

@router.post("/api/upload_image")
async def upload_image(
    file: UploadFile = File(...),
    episode_no: str = Form(...),
    target_slot: str = Form("main"),
    page_num: Optional[int] = Form(None),
    frame_idx: Optional[int] = Form(None)
):
    """
    외부 생성 이미지를 드래그 앤 드롭 또는 파일 선택으로 업로드
    (1면, 2면, 3면, 4면 및 분할 프레임 독립 파일 저장 지원)
    """
    clean_ep = re.sub(r'[^0-9]', '', episode_no).zfill(2)
    f_idx = frame_idx or 1
    is_part2 = (target_slot == "part2") or (page_num is not None and page_num >= 3)

    if page_num == 1 and f_idx == 1:
        filename = f"{clean_ep}_삽화.jpg"
    elif page_num == 3 and f_idx == 1:
        filename = f"{clean_ep}_삽화_후반.jpg"
    elif page_num is not None:
        suffix = f"_{page_num}면" + (f"_{f_idx}" if f_idx > 1 else "")
        filename = f"{clean_ep}_삽화{suffix}.jpg"
    else:
        filename = f"{clean_ep}_삽화_후반.jpg" if is_part2 else f"{clean_ep}_삽화.jpg"

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
                cfg = dict(w.layout_config) if getattr(w, 'layout_config', None) else {}
                pages = list(cfg.get("pages", []))
                target_idx = (page_num - 1) if (page_num is not None and page_num > 0) else (2 if is_part2 else 0)

                while len(pages) <= target_idx:
                    curr_p = len(pages) + 1
                    pages.append({
                        "page_num": curr_p,
                        "usage": "image" if curr_p == 1 else ("image_text" if curr_p == 3 else "text"),
                        "role": "none" if curr_p == 1 else ("start" if curr_p == 2 else "continue"),
                        "image_file": "",
                        "custom_text": ""
                    })

                if f_idx == 2:
                    pages[target_idx]["image_file_b"] = f"./images/{filename}"
                else:
                    pages[target_idx]["image_file"] = f"./images/{filename}"

                if pages[target_idx].get("usage") == "text":
                    pages[target_idx]["usage"] = "image_text"

                cfg["pages"] = pages
                if "slots" in cfg and len(cfg["slots"]) > target_idx:
                    cfg["slots"][target_idx] = pages[target_idx]["usage"]

                w.layout_config = cfg

                if target_idx == 0 and f_idx == 1:
                    w.image_file = f"./images/{filename}"
                elif target_idx == 2 and f_idx == 1:
                    w.image_file_2 = f"./images/{filename}"
                    w.part2_mode = "image"
                    w.layout_mode = "multi_page"
                elif is_part2 and not getattr(w, "image_file_2", None):
                    w.image_file_2 = f"./images/{filename}"
                    w.part2_mode = "image"
                    w.layout_mode = "multi_page"

                mgr.save_work(w)
                break
        try:
            build_canva_csv()
        except Exception:
            pass

        t_rand = random.randint(1000, 9999)
        page_desc = f"{page_num}면 {f_idx}번 " if page_num else ("2부 연작 삽화" if target_slot == "part2" else "삽화")
        return {
            "success": True,
            "filename": filename,
            "target_slot": target_slot,
            "page_num": page_num,
            "frame_idx": f_idx,
            "image_url": f"/images/{filename}?t={t_rand}",
            "message": f"[{episode_no}] {page_desc}삽화가 성공적으로 등록되었습니다!"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이미지 업로드 실패: {str(e)}")

@router.post("/api/generate_part2_image")
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

        p_title = getattr(req, "title", None) or (target_work.title if target_work else "고향의 추억")
        p_memory = getattr(req, "memory_anchor", None) or (target_work.memory_anchor if target_work else "")

        # [2부 모듈러 블록 조립] 추가 연출 및 시의 정경을 온전히 보존
        from core.skill_pack import build_modular_art_prompt
        modular_p2 = build_modular_art_prompt(
            raw_prompt=prompt_text,
            art_style=art_style,
            custom_guide=custom_guide,
            title=p_title,
            memory_anchor=p_memory
        )
        final_used_prompt = modular_p2["display_ko_prompt"]

        seed = random.randint(100000, 999999)

        # 다단계 무료 폴백 엔진 & 300 DPI 사방 10% 수채화 블러 비네팅 마스크 자동 적용 (ref_image_bytes 연동)
        await asyncio.to_thread(
            _download_and_save_candidate,
            modular_p2["clean_scene"],
            seed,
            target_path,
            art_style=art_style,
            ref_image_bytes=ref_bytes,
            custom_guide=custom_guide,
            title=p_title,
            memory_anchor=p_memory,
            modular_dict=modular_p2
        )

        # 원고 즉시 덮어쓰기는 수행하지 않음 (미리보기 창에서 사용자가 [삽화로 삽입]을 누를 때 반영)
        return {
            "success": True,
            "episode_no": req.episode_no,
            "filename": filename,
            "target_slot": "part2",
            "used_prompt": final_used_prompt,
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


@router.get('/api/images')
async def get_images_status():
    return inspect_images()

@router.post("/api/images/enhance_300dpi")
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
            res = await asyncio.to_thread(ensure_300dpi_image, img_path, img_path)
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

