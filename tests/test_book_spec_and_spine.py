import pytest
from core.book_spec import calculate_spine_and_cover

def test_a5_book_spec_defaults():
    """기본 판형 규격이 출판 표준인 부크크 A5(148 x 210 mm) 및 사방 도련 3mm여야 한다."""
    spec = calculate_spine_and_cover(pages_count=80)
    assert spec["bleed_margin_mm"] == 3
    assert spec["inner_safe_margin_mm"] == 20
    assert spec["outer_safe_margin_mm"] == 15
    assert spec["barcode_box"] == "우측 하단 (50 x 35 mm)"

def test_spine_thickness_calculation():
    """책등 두께 계산 공식: (총 페이지 / 2) * 장당 두께(0.060mm) 검증"""
    # 80페이지: (80 / 2) * 0.060 = 2.40 mm
    spec_80 = calculate_spine_and_cover(pages_count=80)
    assert abs(spec_80["spine_thickness_mm"] - 2.4) < 0.01

    # 100페이지: (100 / 2) * 0.060 = 3.00 mm
    spec_100 = calculate_spine_and_cover(pages_count=100)
    assert abs(spec_100["spine_thickness_mm"] - 3.0) < 0.01

def test_cover_dimensions_calculation():
    """표지 전체 펼침면 캔버스 크기 = (앞뒤표지 148*2) + 책등 + 사방도련(6mm)"""
    spec = calculate_spine_and_cover(pages_count=80)
    expected_width = (148 * 2) + 2.4 + 6  # 296 + 2.4 + 6 = 304.4 mm
    expected_height = 210 + 6             # 216.0 mm

    assert abs(spec["cover_canvas_width_mm"] - expected_width) < 0.1
    assert abs(spec["cover_canvas_height_mm"] - expected_height) < 0.1
