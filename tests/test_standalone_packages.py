# -*- coding: utf-8 -*-
"""
tests/test_standalone_packages.py
4대 독립 패키지(packages/) 단독 동작 및 인터페이스 검증 테스트
"""
from pathlib import Path
from packages.bookk_pod_engine import calculate_spine_and_cover, BOOKK_FORMATS
from packages.lyric_video_maker import LyricVideoMaker, parse_time_to_seconds, format_seconds
from packages.korean_poetic_ai import KoreanPoeticAI, get_art_style_prompt_bundle, build_modular_song_package


def test_bookk_pod_engine_standalone():
    spec_a5 = calculate_spine_and_cover(pages=100, paper_type="백색 모조지 100g", format_key="a5")
    assert spec_a5["format_key"] == "a5"
    assert spec_a5["spine_thickness_mm"] == 6.2
    assert spec_a5["bleed_margin_mm"] == 3
    assert "b6_mod" in BOOKK_FORMATS


def test_lyric_video_maker_standalone():
    maker = LyricVideoMaker()
    assert maker is not None
    assert parse_time_to_seconds("01:30") == 90.0
    assert format_seconds(90.0) == "01:30"


def test_korean_poetic_ai_standalone():
    ai = KoreanPoeticAI()
    drafts = ai.compose_dual_drafts(
        core_memory="외갓집 마당의 저녁노을",
        sensory_details="가마솥 연기, 장독대",
        spoken_words="아가, 저녁 먹어라"
    )
    assert "draft_a" in drafts and "draft_b" in drafts
    assert len(drafts["draft_a"]["body"]) > 10

    thes = ai.lookup_thesaurus("어머니")
    assert thes["matched_key"] == "어머니"
    assert "categories" in thes["data"]

    style_pkg = get_art_style_prompt_bundle("watercolor")
    assert "prefix" in style_pkg

    song_pkg = build_modular_song_package(
        poem_body="외갓집 마당에 저녁노을 내려앉고\n가마솥 연기 피어오르네",
        title="외갓집 저녁노을",
        genre_key="folk",
        api_key=""
    )
    assert song_pkg["success"] is True
    assert "[Verse 1]" in song_pkg["lyrics"]


def test_dtp_spread_ui_package_exists():
    base_dir = Path(__file__).resolve().parent.parent
    js_file = base_dir / "packages" / "dtp_spread_ui" / "dtp_spread_ui.js"
    esm_file = base_dir / "packages" / "dtp_spread_ui" / "dtp_spread_ui.esm.js"
    web_esm_entry = base_dir / "web" / "static" / "js" / "main.esm.js"
    vite_cfg = base_dir / "vite.config.js"
    assert js_file.exists() and esm_file.exists()
    assert web_esm_entry.exists() and vite_cfg.exists()
    content = js_file.read_text(encoding="utf-8")
    assert "DtpSpreadUI" in content
    assert "DtpSpreadViewer" in content
    assert "storybook-dtp-spread" in content
    assert "StorybookDtpSpreadElement" in content
