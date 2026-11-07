# -*- coding: utf-8 -*-
"""
scripts/build_web_optimized_gallery.py
온라인 시화 갤러리를 Vercel 100MB 무료 한도 내에 맞추기 위해
304MB 원본 미디어를 고화질/고음질 유지하면서 웹 최적화(30~35MB)하여
D:/AG/EduAI_Hub/public/gallery/ 에 완벽하게 구축하는 자동화 스크립트.
"""

import os
import re
import sys
import shutil
import subprocess
from pathlib import Path
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BASE_DIR / "projects" / "노을빛_기억"
TARGET_DIR = Path("D:/AG/EduAI_Hub/public/gallery")

def optimize_image(src_path: Path, dst_path: Path, max_dim=1440, quality=82):
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with Image.open(src_path) as img:
            img = img.convert("RGB")
            w, h = img.size
            if max(w, h) > max_dim:
                scale = max_dim / max(w, h)
                new_w = int(w * scale)
                new_h = int(h * scale)
                img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            img.save(dst_path, "JPEG", quality=quality, optimize=True)
        return True
    except Exception as e:
        print(f"  [Image Error] {src_path.name}: {e}")
        shutil.copy2(src_path, dst_path)
        return False

def optimize_audio(src_path: Path, dst_path: Path, bitrate="96k"):
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    # ffmpeg를 통해 96kbps MP3로 인코딩 (음성 낭송 및 서정 BGM에 완벽한 음질)
    cmd = [
        "ffmpeg", "-y", "-i", str(src_path),
        "-vn", "-codec:a", "libmp3lame", "-b:a", bitrate,
        "-ar", "44100", str(dst_path)
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except Exception as e:
        print(f"  [Audio Error] {src_path.name}: {e}")
        shutil.copy2(src_path, dst_path)
        return False

def optimize_video(src_path: Path, dst_path: Path):
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    # 720p H.264 CRF 28, faststart (웹 스트리밍 최적화)
    cmd = [
        "ffmpeg", "-y", "-i", str(src_path),
        "-vf", "scale=-2:'min(720,ih)'",
        "-c:v", "libx264", "-crf", "28", "-preset", "fast",
        "-c:a", "aac", "-b:a", "96k",
        "-movflags", "+faststart",
        str(dst_path)
    ]
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except Exception as e:
        print(f"  [Video Error] {src_path.name}: {e}")
        shutil.copy2(src_path, dst_path)
        return False

def build():
    print("=" * 70)
    print("🚀 [Vercel 100MB 한도 최적화] 온라인 시화 갤러리 배포 빌드 시작")
    print(f"📁 소스: {PROJECT_DIR}")
    print(f"🎯 타깃: {TARGET_DIR}")
    print("=" * 70)

    if TARGET_DIR.exists():
        shutil.rmtree(TARGET_DIR)
    TARGET_DIR.mkdir(parents=True, exist_ok=True)

    gallery_html_path = PROJECT_DIR / "시화집_갤러리.html"
    if not gallery_html_path.exists():
        print(f"❌ 갤러리 HTML 파일이 없습니다: {gallery_html_path}")
        return

    html_content = gallery_html_path.read_text(encoding="utf-8")

    # 1. 실제 사용 이미지 수집 및 압축
    used_images = set(re.findall(r'images/[a-zA-Z0-9_\uac00-\ud7a3\.\-]+', html_content))
    print(f"\n📸 [1/3] 이미지 최적화 ({len(used_images)}개)...")
    for img_rel in used_images:
        src = PROJECT_DIR / img_rel
        dst = TARGET_DIR / img_rel
        if src.exists() and src.is_file():
            optimize_image(src, dst)
            print(f"  ✓ {src.name} ➔ {dst.stat().st_size / 1024:.1f} KB")

    # 2. 실제 사용 음원 수집 및 96k MP3 압축
    used_music = set(re.findall(r'music/[a-zA-Z0-9_\uac00-\ud7a3\.\-]+', html_content))
    print(f"\n🎵 [2/3] 음원 최적화 ({len(used_music)}개)...")
    for music_rel in used_music:
        src = PROJECT_DIR / music_rel
        if src.exists() and src.is_file():
            # wav 파일은 mp3로 변환
            is_wav = src.suffix.lower() == ".wav"
            target_name = src.stem + ".mp3" if is_wav else src.name
            dst = TARGET_DIR / "music" / target_name

            optimize_audio(src, dst)
            print(f"  ✓ {src.name} ➔ {target_name} ({dst.stat().st_size / 1024:.1f} KB)")
            if is_wav:
                # HTML 내 경로를 .mp3로 치환
                html_content = html_content.replace(music_rel, f"music/{target_name}")

    # 3. 실제 사용 동영상 수집 및 720p H.264 웹 압축
    used_videos = set(re.findall(r'videos/[a-zA-Z0-9_\uac00-\ud7a3\.\-]+', html_content))
    print(f"\n🎬 [3/3] 시화 영상 최적화 ({len(used_videos)}개)...")
    for vid_rel in used_videos:
        src = PROJECT_DIR / vid_rel
        dst = TARGET_DIR / vid_rel
        if src.exists() and src.is_file():
            optimize_video(src, dst)
            print(f"  ✓ {src.name} ➔ {dst.stat().st_size / (1024*1024):.2f} MB")

    # 4. index.html 저장
    dst_html = TARGET_DIR / "index.html"
    dst_html.write_text(html_content, encoding="utf-8")
    print(f"\n📄 index.html 생성 완료 ({dst_html.stat().st_size / 1024:.1f} KB)")

    # 5. 총 용량 계산
    total_bytes = sum(f.stat().st_size for f in TARGET_DIR.rglob("*") if f.is_file())
    total_mb = total_bytes / (1024 * 1024)
    print("=" * 70)
    print(f"🎉 Vercel 배포용 초경량 갤러리 구축 완료!")
    print(f"📦 총 용량: {total_mb:.2f} MB (Vercel 100MB 한도의 {total_mb/100*100:.1f}%)")
    print(f"📂 배포 폴더: {TARGET_DIR}")
    print("=" * 70)

if __name__ == "__main__":
    build()
