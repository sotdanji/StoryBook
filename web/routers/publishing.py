"""부크크(Bookk) 300 DPI 내지/표지 PDF, 서문·판권지(Book Extras), Canva 대량 조판 CSV 및 책등 계산기 라우터"""

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


@router.get("/api/export_csv")
async def export_csv():
    info = project_manager.get_active_project_info()
    count, path = build_canva_csv()
    if not path.exists():
        raise HTTPException(status_code=404, detail="CSV 파일을 생성할 수 없습니다.")
    
    safe_name = urllib.parse.quote(f"{info.name}_본문데이터.csv")
    return FileResponse(
        path=str(path),
        filename=f"{info.name}_본문데이터.csv",
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_name}"}
    )

@router.get("/api/book_spec")
async def get_book_spec(pages: int = 80):
    return calculate_spine_and_cover(pages)


@router.get("/api/export_pdf")
async def export_pdf():
    try:
        info = project_manager.get_active_project_info()
        pdf_path = await asyncio.to_thread(build_pdf_book)
        if not pdf_path.exists():
            raise HTTPException(status_code=500, detail="PDF 파일 생성에 실패했습니다.")
        
        safe_name = urllib.parse.quote(f"{info.name}_완성본.pdf")
        return FileResponse(
            path=str(pdf_path),
            filename=f"{info.name}_완성본.pdf",
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_name}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF 생성 오류: {str(e)}")

# -------------------------------------------------------------
# 부크크(Bookk) POD 출판 규격 300DPI 인쇄 PDF API
# -------------------------------------------------------------
@router.get("/api/bookk/formats")
async def get_bookk_formats():
    """부크크 지원 판형 목록 및 상세 규격 반환"""
    return {"formats": BOOKK_FORMATS}

@router.get("/api/bookk/export_interior")
async def export_bookk_interior(format_key: str = "a5", paper_type: str = "white_100g"):
    """부크크 300DPI 사방 3mm 도련 및 20mm 제본 여백 내지 완제본 PDF 생성 및 다운로드"""
    try:
        info = project_manager.get_active_project_info()
        p_dir = project_manager.get_project_dir()
        builder = BookkPDFBuilder(format_key=format_key, paper_type=paper_type)

        format_label = "사륙판" if format_key == "b6_mod" else "국판"
        out_filename = f"{info.name}_부크크_내지_{format_label}_300DPI.pdf"
        out_path = p_dir / out_filename

        await asyncio.to_thread(builder.build_interior_pdf, output_path=out_path)
        if not out_path.exists():
            raise HTTPException(status_code=500, detail="부크크 내지 PDF 생성에 실패했습니다.")

        safe_name = urllib.parse.quote(out_filename)
        return FileResponse(
            path=str(out_path),
            filename=out_filename,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_name}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"부크크 내지 PDF 생성 오류: {str(e)}")

@router.get("/api/bookk/export_cover")
async def export_bookk_cover(format_key: str = "b6_mod", paper_type: str = "white_100g", total_pages: int = 0):
    """부크크 표지 펼침면(뒤표지 + 책등 세네카 + 앞표지 + 도련 3mm) PDF 생성 및 다운로드"""
    try:
        info = project_manager.get_active_project_info()
        p_dir = project_manager.get_project_dir()
        builder = BookkPDFBuilder(format_key=format_key, paper_type=paper_type)

        # 총 페이지 수 자동 산출 (미지정 또는 기본값일 때)
        if total_pages <= 0 or total_pages == 28:
            mgr = project_manager.get_active_manuscript_manager()
            episodes = mgr.load_works()
            # 본문(작품당 2P) + 권두(도비라/서문/목차) + 권말(맺음말/판권지) = 최소 40~80쪽 표준
            actual_pages = len(episodes) * 2 + 8
            total_pages = max(actual_pages, 80)

        format_label = "사륙판" if format_key == "b6_mod" else "국판"
        out_filename = f"{info.name}_부크크_표지_{format_label}_300DPI.pdf"
        out_path = p_dir / out_filename

        await asyncio.to_thread(builder.build_cover_spread_pdf, output_path=out_path, total_pages=total_pages)
        if not out_path.exists():
            raise HTTPException(status_code=500, detail="부크크 표지 PDF 생성에 실패했습니다.")

        safe_name = urllib.parse.quote(out_filename)
        return FileResponse(
            path=str(out_path),
            filename=out_filename,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_name}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"부크크 표지 PDF 생성 오류: {str(e)}")


# -------------------------------------------------------------
# 시집 출판 본문 외 구성 요소 (Front & Back Matter) 관리 API
# -------------------------------------------------------------
class BookExtrasSaveRequest(BaseModel):
    prologue: Optional[str] = ""
    epilogue: Optional[str] = ""
    back_cover_blurb: Optional[str] = ""
    cover_image: Optional[str] = ""
    publisher: Optional[str] = "부크크 (Bookk) 자가출판"
    published_date: Optional[str] = ""
    price: Optional[str] = "13,000원"
    isbn: Optional[str] = ""

class BookExtrasGenerateRequest(BaseModel):
    target: str  # "prologue" | "epilogue" | "back_cover_blurb"

@router.get("/api/book_extras")
async def get_book_extras():
    """현재 활성 시집의 본문 외 출판 구성 요소(서문, 에필로그, 뒷표지카피, 판권) 조회"""
    try:
        info = project_manager.get_active_project_info()
        images_dir = project_manager.get_active_images_dir()
        
        # 프로젝트 내 사용 가능한 삽화 목록
        available_images = []
        if images_dir.exists():
            for f in images_dir.glob("*.*"):
                if f.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]:
                    available_images.append(f.name)
            available_images.sort()

        return {
            "success": True,
            "extras": {
                "prologue": getattr(info, 'prologue', ''),
                "epilogue": getattr(info, 'epilogue', ''),
                "back_cover_blurb": getattr(info, 'back_cover_blurb', ''),
                "cover_image": getattr(info, 'cover_image', ''),
                "publisher": getattr(info, 'publisher', '부크크 (Bookk) 자가출판'),
                "published_date": getattr(info, 'published_date', ''),
                "price": getattr(info, 'price', '13,000원'),
                "isbn": getattr(info, 'isbn', '')
            },
            "project_name": info.name,
            "project_subtitle": info.subtitle,
            "project_author": info.author,
            "available_images": available_images
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"출판 데이터 조회 실패: {str(e)}")

@router.post("/api/book_extras/save")
async def save_book_extras(req: BookExtrasSaveRequest):
    """시집의 본문 외 출판 구성 요소(서문, 에필로그, 뒷표지카피, 판권 정보) 저장"""
    try:
        info = project_manager.update_book_extras(None, req.dict())
        return {"success": True, "message": "출판 구성 요소가 안전하게 저장되었습니다.", "info": asdict(info)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"출판 데이터 저장 실패: {str(e)}")

@router.post("/api/book_extras/generate")
async def generate_book_extras(req: BookExtrasGenerateRequest):
    """수록된 시와 시집 기획 의도를 분석하여 AI 시인의 말 / 맺음말 / 뒷표지 카피 자동 생성"""
    try:
        info = project_manager.get_active_project_info()
        mgr = project_manager.get_active_manuscript_manager()
        works = mgr.load_works()

        if req.target == "prologue":
            generated_text = publishing_copier.generate_prologue(info, works)
        elif req.target == "epilogue":
            generated_text = publishing_copier.generate_epilogue(info, works)
        elif req.target == "back_cover_blurb":
            generated_text = publishing_copier.generate_back_cover_blurb(info, works)
        else:
            raise HTTPException(status_code=400, detail="유효하지 않은 생성 요청 대상입니다.")

        return {
            "success": True,
            "target": req.target,
            "generated_text": generated_text
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 출판 문구 생성 실패: {str(e)}")

@router.get("/api/canva/export_publishing_csv")
async def export_canva_publishing_csv():
    """Canva 표지/서문/목차/에필로그/판권지 일괄 바인딩용 메타데이터 CSV 다운로드"""
    try:
        info = project_manager.get_active_project_info()
        p_dir = project_manager.get_project_dir()
        out_path = p_dir / f"{info.name}_출판구성데이터.csv"
        build_canva_publishing_metadata_csv(output_file=out_path)

        safe_name = urllib.parse.quote(out_path.name)
        return FileResponse(
            path=str(out_path),
            filename=out_path.name,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_name}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Canva 출판 메타데이터 CSV 생성 실패: {str(e)}")

