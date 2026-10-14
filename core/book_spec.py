from pathlib import Path
from typing import Dict, List, Any, Optional
from PIL import Image
from core.config import IMAGES_DIR, PAPER_THICKNESS
from core.project_manager import project_manager


def calculate_spine_and_cover(pages_count: int = 80, paper_type: str = "white_100g") -> Dict[str, Any]:
    """
    페이지 수와 용지 종류에 따른 부크크 책등(세네카) 두께 및 표지 펼침면 캔버스 규격 산출
    """
    thickness_factor = PAPER_THICKNESS.get(paper_type, 0.060)
    sheets_count = pages_count / 2
    spine_thickness = round(sheets_count * thickness_factor, 2)

    # A5 기본 판형: 148 x 210 mm
    # 사방 도련: 각 3mm (양쪽 6mm)
    cover_width = round(148 + spine_thickness + 148 + 6, 2)
    cover_height = 210 + 6  # 216 mm

    return {
        "pages_count": pages_count,
        "sheets_count": int(sheets_count),
        "paper_type": paper_type,
        "spine_thickness_mm": spine_thickness,
        "cover_canvas_width_mm": cover_width,
        "cover_canvas_height_mm": cover_height,
        "bleed_margin_mm": 3,
        "inner_safe_margin_mm": 20,
        "outer_safe_margin_mm": 15,
        "barcode_box": "우측 하단 (50 x 35 mm)"
    }

def inspect_images(images_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """
    images 디렉토리 내의 이미지들을 분석하여 인쇄 규격(DPI, 해상도) 적합성을 검증합니다.
    A5 인쇄 권장 해상도(300 DPI 기준): 약 1748 x 2480 px 이상
    """
    if images_dir is None:
        images_dir = project_manager.get_active_images_dir()

    results = []
    if not images_dir.exists():
        return results

    supported_exts = {".png", ".jpg", ".jpeg", ".webp"}
    image_files = sorted([f for f in images_dir.iterdir() if f.suffix.lower() in supported_exts])


    for img_path in image_files:
        try:
            with Image.open(img_path) as img:
                width, height = img.size
                dpi = img.info.get("dpi", (72, 72))
                # x_dpi, y_dpi
                x_dpi = round(dpi[0]) if isinstance(dpi, tuple) else 72

                # 300 DPI 또는 픽셀 크기 기준 (최소 1500px 이상 권장)
                is_high_res = width >= 1500 and height >= 1500
                is_print_ready = is_high_res or x_dpi >= 300

                status = "적합" if is_print_ready else "주의 (저해상도)"

                results.append({
                    "filename": img_path.name,
                    "resolution": f"{width} x {height} px",
                    "dpi": f"{x_dpi} DPI",
                    "status": status,
                    "is_ready": is_print_ready
                })
        except Exception as e:
            results.append({
                "filename": img_path.name,
                "resolution": "읽기 실패",
                "dpi": "-",
                "status": f"오류: {str(e)}",
                "is_ready": False
            })

    return results
