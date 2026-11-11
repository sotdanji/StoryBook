# -*- coding: utf-8 -*-
"""
core/book_spec.py
packages.bookk_pod_engine.specs 모듈을 래핑하여 현재 활성 프로젝트(Turso DB + Cloudflare R2)와 연동하는 브리지 모듈
"""
import tempfile
from pathlib import Path
from typing import Dict, Any
from core.config import PAPER_TYPE
from core.project_manager import project_manager
from packages.bookk_pod_engine.specs import (
    PAPER_THICKNESS_MAP,
    BOOKK_FORMATS,
    calculate_spine_and_cover as _calc_spine_and_cover,
    inspect_images_directory,
)


def calculate_spine_and_cover(pages: int, paper_type: str = PAPER_TYPE, format_key: str = "a5") -> Dict[str, Any]:
    return _calc_spine_and_cover(pages=pages, paper_type=paper_type, format_key=format_key)


def inspect_images() -> Dict[str, Any]:
    """
    [100% 서버 일원화]
    Turso DB에 등록된 현재 시집의 삽화 목록을 Cloudflare R2에서 임시 버퍼(/tmp)로 가져와
    300 DPI 출판 해상도 적합성을 검수합니다.
    """
    from core.r2_storage import r2_storage

    pid = project_manager.get_active_project_id()
    mgr = project_manager.get_manuscript_manager(pid)
    works = mgr.load_works()

    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        for w in works:
            for img_f in (w.image_file, getattr(w, "image_file_2", "")):
                if not img_f:
                    continue
                img_name = Path(img_f.replace("\\", "/")).name
                raw = r2_storage.get_media_bytes(f"/projects/{pid}/images/{img_name}") or r2_storage.get_media_bytes(img_f)
                if raw:
                    (tmp_dir / img_name).write_bytes(raw)
        return inspect_images_directory(tmp_dir)
