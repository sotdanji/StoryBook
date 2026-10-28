"""시화 창작 스튜디오: 심층 인터뷰, 초안 생성, 시 퇴고, 원고 저장/목차 정렬, 판본 비교 및 대량 원고 임포트 라우터"""

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

class RefinePoemRequest(BaseModel):
    poem_body: str
    mode: Optional[str] = "custom"  # "shorten", "subdued", "rhythm", "custom"
    instruction: Optional[str] = ""  # 사용자 자유 수정 요청문
    title: Optional[str] = ""

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
    recite_file: Optional[str] = ""
    music_file: Optional[str] = ""
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

class BulkParseRequest(BaseModel):
    raw_text: str

class BulkImportRequest(BaseModel):
    raw_text: str
    mode: str = "overwrite"  # "overwrite" or "append"
    auto_prompts: bool = True


@router.post("/api/interview/deep_questions")
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

@router.post("/api/generate_drafts")
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

@router.post("/api/refine_poem")
async def refine_poem_endpoint(req: RefinePoemRequest):
    """현재 시 본문을 사용자가 원하는 방향(압축, 절제, 운율 또는 자유 지시문)으로 즉시 다듬기 (Gemini 퇴고 스킬 지원)"""
    res = poetic_engine.refine_poem_with_gemini(
        title=req.title or "시",
        poem_body=req.poem_body,
        mode=req.mode or "custom",
        custom_instruction=req.instruction or ""
    )
    return {
        "success": True,
        "refined_body": res.get("refined_body", req.poem_body),
        "commentary": res.get("commentary", "")
    }


@router.post("/api/smart_prompt")
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

@router.post("/api/save_work")
async def save_work(req: SaveWorkRequest):
    mgr = project_manager.get_active_manuscript_manager()
    recite_f = req.recite_file or ""
    music_f = req.music_file or ""
    audio_f = req.audio_file or music_f or recite_f or ""

    # 기존 work가 있다면 2부 삽화, 조판 설정 등 기존 값 보존
    existing_works = mgr.load_works()
    clean_ep = re.sub(r'[^0-9]', '', req.episode_no).zfill(2) if req.episode_no else "01"
    old_work = next((w for w in existing_works if clean_ep in w.episode_no or w.episode_no.strip() == req.episode_no.strip()), None)

    work = PoemWork(
        episode_no=req.episode_no,
        title=req.title,
        status=req.status,
        memory_anchor=req.memory_anchor,
        image_file=req.image_file or (old_work.image_file if old_work else ""),
        art_direction=req.art_direction,
        poem_body=req.poem_body,
        audio_file=audio_f or (old_work.audio_file if old_work else ""),
        recite_file=recite_f or (old_work.recite_file if old_work else ""),
        music_file=music_f or (old_work.music_file if old_work else ""),
        lyrics=req.lyrics or (old_work.lyrics if old_work else ""),
        author=req.author or (old_work.author if old_work else ""),
        layout_mode=req.layout_mode or (old_work.layout_mode if old_work else "compact"),
        chapter=old_work.chapter if old_work else "",
        part2_mode=old_work.part2_mode if old_work else "motif_symbol",
        image_file_2=old_work.image_file_2 if old_work else "",
        layout_config=old_work.layout_config if old_work else None
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

@router.post("/api/save_work_layout")
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

@router.post("/api/save_work_layout_config")
async def save_work_layout_config_endpoint(req: SaveLayoutConfigRequest):
    """2P/4P 매트릭스 슬롯 조판 설정 영구 저장"""
    mgr = project_manager.get_active_manuscript_manager()
    success = mgr.update_work_layout_config(req.episode_no, req.layout_config)
    if not success:
        raise HTTPException(status_code=404, detail=f"{req.episode_no} 작품을 찾을 수 없습니다.")
    return {
        "success": True,
        "message": f"'{req.episode_no}'의 조판 설정이 성공적으로 저장되었습니다.",
        "episode_no": req.episode_no,
        "layout_config": req.layout_config
    }


# -------------------------------------------------------------
# 시인의 집필실: 퇴고 판본(Revision) & 육성 낭송 API
# -------------------------------------------------------------
@router.get("/api/revisions/{episode_no}")
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

@router.post("/api/compare_revisions")
async def compare_work_revisions(req: CompareRevisionsRequest):
    from core.revision_manager import compare_revisions
    diff_res = compare_revisions(req.body_a, req.body_b, req.name_a, req.name_b)
    return {"success": True, "diff": diff_res}



@router.post("/api/delete_work")
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

@router.post("/api/reorder_works")
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

@router.post("/api/preview_bulk_manuscript")
async def preview_bulk_manuscript(req: BulkParseRequest):
    """붙여넣은 원고를 분석하여 분리된 시 목록을 미리보기로 반환"""
    items = parse_bulk_manuscript(req.raw_text)
    return {
        "success": True,
        "count": len(items),
        "items": items
    }

@router.post("/api/import_bulk_manuscript")
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

