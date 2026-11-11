# -*- coding: utf-8 -*-
import json
import re
import time
from dataclasses import asdict
from pathlib import Path
from typing import Optional, Dict, Any

from core.project_manager import project_manager

BASE_DIR = Path(__file__).resolve().parent.parent
GALLERY_TEMPLATE_FILE = BASE_DIR / "web" / "templates" / "gallery_standalone.html"

# 🌟 [0.001초 응답] 인메모리 HTML 렌더링 캐시 (TTL 60초)
_GALLERY_HTML_CACHE: Dict[str, tuple[float, str]] = {}
CACHE_TTL_SECONDS = 60.0

def invalidate_gallery_cache(project_id: Optional[str] = None):
    """원고 수정 또는 출품 시 캐시 즉시 무효화"""
    global _GALLERY_HTML_CACHE
    if project_id:
        keys_to_del = [k for k in _GALLERY_HTML_CACHE if k.startswith(f"{project_id}_")]
        for k in keys_to_del:
            _GALLERY_HTML_CACHE.pop(k, None)
    else:
        _GALLERY_HTML_CACHE.clear()


def build_project_gallery_payload(project_id: Optional[str] = None, relative_paths: bool = False) -> Dict[str, Any]:
    """
    [100% 서버 일원화]
    지정된 프로젝트의 최신 원고(works), DTP 조판 설정(layout_config), 음원/영상,
    책 전체 구조(book_structure)를 Turso DB에서 직접 추출하여 갤러리 렌더링용 데이터 딕셔너리를 반환합니다.
    """
    pid = project_id or project_manager.get_active_project_id()
    info = project_manager.get_project_info(pid)
    mgr = project_manager.get_manuscript_manager(pid)
    works = mgr.load_works()

    safe_name = (info.id or info.name).replace(" ", "_")

    def _fmt_path(rel_p: str) -> str:
        if not rel_p:
            return ""
        clean = str(rel_p).replace("./", "").lstrip("/")
        if clean.startswith("http://") or clean.startswith("https://"):
            return clean
        if clean.startswith(f"projects/{safe_name}/"):
            clean = clean[len(f"projects/{safe_name}/"):]
        if relative_paths:
            return clean
        return f"/projects/{safe_name}/{clean}"

    episodes = []
    for w in works:
        pid_code = getattr(w, "piece_id", "")
        img_path = _fmt_path(w.image_file)
        img_path_2 = _fmt_path(getattr(w, "image_file_2", ""))

        voice_f = getattr(w, "voice_user_file", "")
        ai_recite_f = getattr(w, "voice_tts_file", "") or getattr(w, "recite_file", "")
        
        # [초경량 서정 낭송 전용화] 육성 우선, 없으면 AI 서정 낭송
        recite_f = voice_f or ai_recite_f
        recite_type = "voice" if voice_f else ("ai" if ai_recite_f else "")
        recite_path = _fmt_path(recite_f)

        # [조판 설정 이미지 경로 절대경로 일원화 (지연 0ms 보장)]
        l_cfg = getattr(w, "layout_config", None)
        if isinstance(l_cfg, dict) and "pages" in l_cfg and isinstance(l_cfg["pages"], list):
            import copy
            l_cfg = copy.deepcopy(l_cfg)
            for page in l_cfg["pages"]:
                if isinstance(page, dict) and page.get("image_file"):
                    page["image_file"] = _fmt_path(page["image_file"])

        episodes.append({
            "piece_id": pid_code,
            "ep": w.episode_no,
            "episode_no": w.episode_no,
            "title": w.title,
            "status": getattr(w, "status", "완성"),
            "image": img_path,
            "image_file": img_path,
            "image2": img_path_2,
            "image_file_2": img_path_2,
            "memory": w.memory_anchor,
            "body": w.poem_body,
            "poem_body": w.poem_body,
            "hasRecite": bool(recite_f),
            "recite": recite_path,
            "recite_type": recite_type,
            "hasVoice": bool(voice_f),
            "voice": _fmt_path(voice_f),
            "hasAiRecite": bool(ai_recite_f),
            "aiRecite": _fmt_path(ai_recite_f),
            "layout_mode": getattr(w, "layout_mode", "compact") or "compact",
            "part2_mode": getattr(w, "part2_mode", "motif_symbol") or "motif_symbol",
            "layout_config": l_cfg,
            "chapter": getattr(w, "chapter", "") or "",
            "author": getattr(w, "author", "") or info.author
        })

    book_structure = project_manager.get_book_structure(pid)

    return {
        "success": True,
        "project": asdict(info),
        "projects": project_manager.list_projects(),
        "episodes": episodes,
        "book_structure": book_structure
    }


def render_project_gallery_html(project_id: Optional[str] = None, relative_paths: bool = False, bypass_cache: bool = False) -> str:
    """
    [100% 서버 메모리 렌더링 - 0.001초 초고속 캐시 지원]
    로컬 projects/ 폴더의 파일에 의존하지 않고, 마스터 갤러리 템플릿(`web/templates/gallery_standalone.html`)에
    Turso DB 최신 데이터를 인메모리로 주입하여 완성된 HTML 문자열을 반환합니다.
    """
    pid = project_id or project_manager.get_active_project_id()
    cache_key = f"{pid}_{relative_paths}"
    now = time.time()

    if not bypass_cache and cache_key in _GALLERY_HTML_CACHE:
        cached_time, cached_html = _GALLERY_HTML_CACHE[cache_key]
        if now - cached_time < CACHE_TTL_SECONDS:
            return cached_html

    payload = build_project_gallery_payload(pid, relative_paths=relative_paths)
    episodes_json = json.dumps(payload["episodes"], ensure_ascii=False, indent=2)
    struct_json = json.dumps(payload["book_structure"], ensure_ascii=False, indent=2)
    proj_json = json.dumps(payload["project"], ensure_ascii=False, indent=2)

    if GALLERY_TEMPLATE_FILE.exists():
        html_text = GALLERY_TEMPLATE_FILE.read_text(encoding="utf-8")
    else:
        html_text = (
            "<!DOCTYPE html><html lang='ko'><head><meta charset='utf-8'><title>시화 갤러리</title></head>"
            "<body><script>\n// [AUTO-SYNC-GALLERY-DATA-START]\n// [AUTO-SYNC-GALLERY-DATA-END]\n</script></body></html>"
        )

    marker_start = "// [AUTO-SYNC-GALLERY-DATA-START]"
    marker_end = "// [AUTO-SYNC-GALLERY-DATA-END]"
    new_data_block = (
        f"{marker_start}\n"
        f"    const EPISODES_DATA = {episodes_json};\n"
        f"    const BOOK_STRUCTURE = {struct_json};\n"
        f"    const PROJECT_INFO = {proj_json};\n"
        f"    {marker_end}"
    )

    if marker_start in html_text and marker_end in html_text:
        pattern = re.compile(rf"{re.escape(marker_start)}.*?{re.escape(marker_end)}", re.DOTALL)
        html_text = pattern.sub(lambda _: new_data_block, html_text)

    _GALLERY_HTML_CACHE[cache_key] = (now, html_text)
    return html_text


def sync_project_gallery_html(project_id: Optional[str] = None) -> bool:
    """
    [서버 일원화 호환 래퍼]
    더 이상 로컬 projects/ 폴더에 시화집_갤러리.html을 기록하지 않으며,
    요청 시점에 render_project_gallery_html()이 실시간으로 최신 DB를 렌더링합니다.
    """
    return True
