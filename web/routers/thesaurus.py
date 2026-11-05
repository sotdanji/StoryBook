"""시어(詩語) 감각 사전 조회 및 AI 문맥 맞춤 방언·유의어 추천 라우터"""

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

from core.poetic_thesaurus import lookup_poetic_words, get_all_categories_summary, suggest_poetic_synonyms_ai

WEB_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = WEB_DIR / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter()


# ========================================================
# [기둥 1] 시어(詩語) 감각 사전 & 토속·방언 API
# ========================================================
@router.get("/api/thesaurus/lookup")
async def api_thesaurus_lookup(word: str = ""):
    """단어에 매칭되는 시어 감각 사전 항목을 조회합니다."""
    query = (word or "").strip()
    if not query:
        return {"success": False, "found": False, "word": "", "data": None, "message": "검색할 단어를 입력해 주세요."}
    
    result = lookup_poetic_words(query)
    if not result:
        return {
            "success": True,
            "found": False,
            "word": query,
            "data": None,
            "message": f"'{query}'에 대한 시어 감각 데이터가 아직 없습니다. 아래 추천 테마를 둘러보세요."
        }

    return {
        "success": True,
        "found": True,
        "word": query,
        "matched_key": result["matched_key"],
        "data": result["data"]
    }


@router.get("/api/thesaurus/all")
async def api_thesaurus_all():
    """시어 사전 전체 등록 테마 목록과 미리보기를 반환합니다."""
    themes = get_all_categories_summary()
    return {
        "success": True,
        "categories": themes,
        "themes": themes,
        "total": len(themes)
    }


@router.get("/api/thesaurus/suggest")
async def api_thesaurus_suggest(word: str = "", context: str = ""):
    """
    선택한 단어와 시적 문맥(주변 시행)을 바탕으로,
    서정적 시어, 토속 방언, 은유적 유의어를 실시간 AI/사전 엔진으로 추천합니다.
    """
    query = (word or "").strip()
    if not query:
        return {"success": False, "word": "", "suggestions": [], "message": "단어를 입력해 주세요."}

    result = suggest_poetic_synonyms_ai(query, context)
    return {
        "success": True,
        "word": result.get("word", query),
        "matched_key": result.get("matched_key", query),
        "suggestions": result.get("suggestions", []),
        "source": result.get("source", "heuristic")
    }

