# -*- coding: utf-8 -*-
"""
core/book_spec.py
packages.bookk_pod_engine.specs 모듈을 래핑하여 현재 활성 프로젝트와 연동하는 브리지 모듈
"""
from typing import Dict, Any
from core.config import PAPER_TYPE, IMAGES_DIR
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
    try:
        active_img_dir = project_manager.get_active_images_dir()
    except Exception:
        active_img_dir = IMAGES_DIR
    return inspect_images_directory(active_img_dir)
