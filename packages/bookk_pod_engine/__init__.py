# -*- coding: utf-8 -*-
"""
packages/bookk_pod_engine
부크크(Bookk) POD 자가출판 규격 계산, 300 DPI 이미지 최적화, 인쇄용 PDF 조판 독립 패키지
"""
from packages.bookk_pod_engine.specs import (
    PAPER_THICKNESS_MAP,
    BOOKK_FORMATS,
    calculate_spine_and_cover,
    inspect_images_directory,
)
from core.image_optimizer import ensure_300dpi_image, apply_watercolor_edge_fade
from core.bookk_pdf_builder import BookkPDFBuilder, build_pdf_book

__all__ = [
    "PAPER_THICKNESS_MAP",
    "BOOKK_FORMATS",
    "calculate_spine_and_cover",
    "inspect_images_directory",
    "ensure_300dpi_image",
    "apply_watercolor_edge_fade",
    "BookkPDFBuilder",
    "build_pdf_book",
]
