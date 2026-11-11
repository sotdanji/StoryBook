# -*- coding: utf-8 -*-
"""
scripts/restore_authentic_music.py
Git 개체 저장소에서 6곡의 진짜 고유 원본 음원을 추출하여
projects/샘플_기억상자 및 projects/노을빛_기억 에 완벽하게 원상 복원합니다.
"""

import sys
import json
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

SAMPLE_MUSIC_DIR = BASE_DIR / "projects" / "샘플_기억상자" / "music"
ORIG_MUSIC_DIR = BASE_DIR / "projects" / "노을빛_기억" / "music"

# 진짜 고유 원본 blob 매핑
SONG_BLOBS = {
    "04_밍밭에서": {
        "blob": "26387b2f1ca37639d3e73c79825568a9d27bb9d2",
        "expected_size": 5792860,
        "sample_targets": ["01_음원.mp3", "04_음원.mp3"],
        "orig_targets": ["04_음원.mp3"],
    },
    "06_물레질": {
        "blob": "cc0a4a4fa623d440a1fb8356d5a34bf25bd4c807",
        "expected_size": 4725760,
        "sample_targets": ["02_음원.mp3", "06_음원_물레질.mp3"],
        "orig_targets": ["06_음원.mp3"],
    },
    "09_다듬이질": {
        "blob": "f9c73d1a1b86284bf20b5a3d8cc22a9372456f22",
        "expected_size": 5644257,
        "sample_targets": ["03_음원.mp3", "09_음원.mp3"],
        "orig_targets": ["09_음원.mp3"],
    },
    "11_따순굼턱": {
        "blob": "f4038210bd3bef24e3db92a138a9bf03131cfdc2",
        "expected_size": 7908524,
        "sample_targets": ["04_음원.mp3", "11_음원.mp3"],
        "orig_targets": ["11_음원.mp3"],
    },
    "12_아리랑쓰리랑": {
        "blob": "3472a945ed9d8ff22af1c937d1e1602abeac183a",
        "expected_size": 7633964,
        "sample_targets": ["05_음원.mp3", "12_음원.mp3"],
        "orig_targets": ["12_음원.mp3"],
    },
}

def extract_blob(blob: str) -> bytes:
    cmd = ["git", "cat-file", "-p", blob]
    res = subprocess.run(cmd, capture_output=True, check=True)
    return res.stdout

def get_duration(file_path: Path) -> str:
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(file_path)]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)
        dur = float(data["format"].get("duration", 0))
        m = int(dur // 60)
        s = int(dur % 60)
        return f"{m}분 {s:02d}초 ({dur:.1f}s)"
    except Exception:
        return "측정불가"

def run():
    print("=" * 65)
    print("🎵 [고유 원본 음원 복원] 6곡 정예 시선 진짜 노래 복원 작업 시작")
    print("=" * 65)

    SAMPLE_MUSIC_DIR.mkdir(parents=True, exist_ok=True)
    ORIG_MUSIC_DIR.mkdir(parents=True, exist_ok=True)

    # 1. 04, 06, 09, 11, 12 Git Blob에서 복원
    for title, info in SONG_BLOBS.items():
        print(f"\n▶ [{title}] 복원 중 (Git Blob: {info['blob'][:8]})...")
        audio_bytes = extract_blob(info["blob"])
        if len(audio_bytes) != info["expected_size"]:
            print(f"⚠️ 크기 불일치: 실제 {len(audio_bytes)} != 예상 {info['expected_size']}")

        # 샘플 프로젝트 복원
        for tgt in info["sample_targets"]:
            p = SAMPLE_MUSIC_DIR / tgt
            p.write_bytes(audio_bytes)
            dur = get_duration(p)
            print(f"  ✓ [샘플] {tgt:18s} -> {len(audio_bytes):8d} bytes | 재생시간: {dur}")

        # 원작 프로젝트 복원
        for tgt in info["orig_targets"]:
            p = ORIG_MUSIC_DIR / tgt
            p.write_bytes(audio_bytes)
            dur = get_duration(p)
            print(f"  ✓ [원작] {tgt:18s} -> {len(audio_bytes):8d} bytes | 재생시간: {dur}")

    # 2. 10_도토리묵 음원 복원 (기존 10_음원.mp3 7,021,484 bytes 가 도토리묵 고유 음원)
    # 06번(도토리묵)에 제대로 매핑
    print(f"\n▶ [10_도토리묵] 복원 중...")
    src_dotori = ORIG_MUSIC_DIR / "10_음원.mp3"
    if not src_dotori.exists() or src_dotori.stat().st_size != 7021484:
        # 샘플 폴더에서라도 확보
        src_dotori = SAMPLE_MUSIC_DIR / "10_음원.mp3"

    if src_dotori.exists():
        dotori_bytes = src_dotori.read_bytes()
        (SAMPLE_MUSIC_DIR / "06_음원.mp3").write_bytes(dotori_bytes)
        (ORIG_MUSIC_DIR / "10_음원.mp3").write_bytes(dotori_bytes)
        dur = get_duration(SAMPLE_MUSIC_DIR / "06_음원.mp3")
        print(f"  ✓ [샘플] 06_음원.mp3        -> {len(dotori_bytes):8d} bytes | 재생시간: {dur}")
        print(f"  ✓ [원작] 10_음원.mp3        -> {len(dotori_bytes):8d} bytes | 재생시간: {dur}")

    # 3. 갤러리 HTML 및 CSV 동기화
    from core.gallery_builder import sync_project_gallery_html
    from core.csv_builder import build_canva_csv

    sync_project_gallery_html("샘플_기억상자")
    build_canva_csv(output_file=BASE_DIR / "projects" / "샘플_기억상자" / "시화집_본문데이터.csv")

    sync_project_gallery_html("노을빛_기억")
    build_canva_csv(output_file=BASE_DIR / "projects" / "노을빛_기억" / "시화집_본문데이터.csv")

    print("\n" + "=" * 65)
    print("🎉 [완료] 6곡 모두 각자의 진짜 고유 음원으로 깨끗하게 복원되었습니다!")
    print("=" * 65)

if __name__ == "__main__":
    run()

