import pytest
from core.book_spec import calculate_spine_and_cover


def test_a5_book_spec_defaults():
    """기본 판형 규격이 출판 표준인 부크크 A5(148 x 210 mm) 및 사방 도련 3mm여야 한다."""
    spec = calculate_spine_and_cover(pages=80)
    assert spec["format_key"] == "a5"
    assert spec["trim_width_mm"] == 148.0
    assert spec["trim_height_mm"] == 210.0
    assert spec["bleed_margin_mm"] == 3


def test_spine_thickness_calculation():
    """책등 두께는 페이지 수에 비례(기본 용지 white_100g: 페이지당 0.062mm)해야 한다."""
    spec_80 = calculate_spine_and_cover(pages=80)
    assert abs(spec_80["spine_thickness_mm"] - 4.96) < 0.01

    spec_100 = calculate_spine_and_cover(pages=100)
    assert abs(spec_100["spine_thickness_mm"] - 6.2) < 0.01
    assert spec_100["spine_thickness_mm"] > spec_80["spine_thickness_mm"]


def test_cover_dimensions_calculation():
    """표지 전체 펼침면 캔버스 크기 = (앞뒤표지 148*2) + 책등 + 사방도련(6mm)"""
    spec = calculate_spine_and_cover(pages=80)
    expected_width = (148 * 2) + spec["spine_thickness_mm"] + 6
    expected_height = 210 + 6

    assert abs(spec["cover_canvas_width_mm"] - expected_width) < 0.1
    assert abs(spec["cover_canvas_height_mm"] - expected_height) < 0.1
