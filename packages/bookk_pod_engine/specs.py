# -*- coding: utf-8 -*-
"""
packages/bookk_pod_engine/specs.py
독립형 POD 출판 판형(A5 국판 / B6 변형 사륙판) 및 책등(Spine) 두께·표지 펼침면 규격 계산기
- 외부 전역 설정(core.config) 의존성 0% (타 프로젝트 단독 이식 가능)
"""
from pathlib import Path
from typing import Dict, Any, Union
from PIL import Image

PAPER_THICKNESS_MAP = {
    "미색 모조지 80g": 0.052,
    "백색 모조지 80g": 0.050,
    "백색 모조지 100g": 0.062,
    "미색 모조지 100g": 0.064,
    "스노우지 120g": 0.055,
    "스노우지 150g": 0.070,
    "아르떼 105g": 0.075,
    "white_100g": 0.062,
    "cream_80g": 0.052,
}

BOOKK_FORMATS = {
    "a5": {
        "name": "국판 (A5)",
        "trim_w_mm": 148.0,
        "trim_h_mm": 210.0,
        "bleed_mm": 3.0,
        "desc": "시화집·에세이 표준 판형 (148×210mm)"
    },
    "b6_mod": {
        "name": "사륙판 (B6 변형)",
        "trim_w_mm": 128.0,
        "trim_h_mm": 188.0,
        "bleed_mm": 3.0,
        "desc": "휴대성 좋은 전통 시집 판형 (128×188mm)"
    }
}


def calculate_spine_and_cover(
    pages: int,
    paper_type: str = "미색 모조지 80g",
    format_key: str = "a5"
) -> Dict[str, Any]:
    """페이지 수, 용지 종류, 판형에 따른 책등(세네카) 두께 및 표지 전체 펼침면 크기(mm/px) 계산"""
    fmt = BOOKK_FORMATS.get(format_key, BOOKK_FORMATS["a5"])
    trim_w = fmt["trim_w_mm"]
    trim_h = fmt["trim_h_mm"]
    bleed = fmt["bleed_mm"]

    factor = PAPER_THICKNESS_MAP.get(paper_type, 0.052)
    spine_mm = round(pages * factor, 2)

    cover_total_width_mm = round((trim_w * 2) + spine_mm + (bleed * 2), 2)
    cover_total_height_mm = round(trim_h + (bleed * 2), 2)

    px_per_mm = 300.0 / 25.4
    width_px = int(round(cover_total_width_mm * px_per_mm))
    height_px = int(round(cover_total_height_mm * px_per_mm))
    inner_width_px = int(round((trim_w + bleed * 2) * px_per_mm))
    inner_height_px = int(round((trim_h + bleed * 2) * px_per_mm))

    return {
        "format_key": format_key,
        "format_name": fmt["name"],
        "pages": pages,
        "paper_type": paper_type,
        "spine_thickness_mm": spine_mm,
        "bleed_margin_mm": int(bleed),
        "trim_width_mm": trim_w,
        "trim_height_mm": trim_h,
        "cover_canvas_width_mm": cover_total_width_mm,
        "cover_canvas_height_mm": cover_total_height_mm,
        "cover_canvas_px": (width_px, height_px),
        "inner_page_bleed_mm": (trim_w + bleed * 2, trim_h + bleed * 2),
        "inner_page_px": (inner_width_px, inner_height_px),
    }


def inspect_images_directory(images_dir: Union[str, Path]) -> Dict[str, Any]:
    """지정된 이미지 폴더 내 삽화들의 해상도 및 300 DPI 인쇄 적격 여부 검사"""
    target_dir = Path(images_dir)
    if not target_dir.exists():
        return {"count": 0, "files": []}

    valid_exts = {".png", ".jpg", ".jpeg", ".webp"}
    files_info = []
    for f in sorted(target_dir.iterdir()):
        if f.is_file() and f.suffix.lower() in valid_exts:
            try:
                with Image.open(f) as img:
                    w, h = img.size
                    dpi = img.info.get("dpi", (72, 72))
                    is_high_res = (w >= 1400 and h >= 2000)
                    files_info.append({
                        "name": f.name,
                        "size": f"{w}x{h}",
                        "dpi": dpi[0] if isinstance(dpi, tuple) else dpi,
                        "print_ready": is_high_res,
                        "status": "✅ 인쇄 적합 (고해상도)" if is_high_res else "⚠️ 해상도 보완 권장 (1748x2480px 이상 권장)"
                    })
            except Exception as e:
                files_info.append({
                    "name": f.name,
                    "size": "읽기 오류",
                    "dpi": 0,
                    "print_ready": False,
                    "status": f"❌ 파일 손상 ({e})"
                })
    return {"count": len(files_info), "files": files_info}
