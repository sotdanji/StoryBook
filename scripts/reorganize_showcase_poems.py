# -*- coding: utf-8 -*-
"""
scripts/reorganize_showcase_poems.py
스튜디오 기본 시범선집 [노을빛 기억] 6편 재구성 스크립트
- 6편 정예 시선 (04 밍밭에서, 06 물레질, 09 다듬이질, 11 따순굼턱, 12 아리랑 쓰리랑, 10 도토리 묵)
- 01화~06화 번호 체계 재매핑
- 이미지, 음원(낭송/노래), 리비전 파일 동기화
- 작품집_원고.md, project.json 갱신
- CSV 및 갤러리 HTML 빌드
"""

import os
import re
import sys
import json
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
PROJECT_DIR = BASE_DIR / "projects" / "노을빛_기억"

def run():
    print("=" * 60)
    print("🌾 [노을빛 기억] 시범선집 6편 스튜디오 기본 프로젝트 재구성 시작")
    print("=" * 60)

    # 1. 원본 전체 원고 읽기 (노을빛_기억_전편에서)
    backup_manuscript = BASE_DIR / "projects" / "노을빛_기억_전편" / "작품집_원고.md"
    if not backup_manuscript.exists():
        backup_manuscript = PROJECT_DIR / "작품집_원고.md"
    
    full_content = backup_manuscript.read_text(encoding="utf-8")
    sections = re.split(r'\n(?=##\s*\[(?:제)?\d+화?\])', full_content)

    sec_map = {}
    for s in sections:
        m = re.search(r'##\s*\[(?:제)?(\d+)화?\]', s)
        if m:
            sec_map[m.group(1)] = s

    # 6편 순서 정의: (원작번호, 새제목, 새이미지이름)
    order = [
        ("04", "밍밭에서", "01_밍밭에서.jpg"),
        ("06", "물레질", "02_물레질.jpg"),
        ("09", "다듬이질", "03_다듬이질.jpg"),
        ("11", "따순굼턱", "04_따순굼턱.jpg"),
        ("12", "아리랑 쓰리랑", "05_아리랑쓰리랑.jpg"),
        ("10", "도토리 묵", "06_도토리묵.jpg"),
    ]

    images_dir = PROJECT_DIR / "images"
    music_dir = PROJECT_DIR / "music"
    revisions_dir = PROJECT_DIR / "revisions"

    images_dir.mkdir(parents=True, exist_ok=True)
    music_dir.mkdir(parents=True, exist_ok=True)
    revisions_dir.mkdir(parents=True, exist_ok=True)

    new_sections = []

    for new_idx, (old_num, title, target_img_name) in enumerate(order, 1):
        new_ep_no = f"제{new_idx:02d}화"
        old_ep_no = f"제{old_num}화"
        old_sec = sec_map.get(old_num)
        if not old_sec:
            print(f"❌ 원작 {old_num}화를 찾을 수 없습니다.")
            continue

        print(f"\n[{new_ep_no}] {title} (원작 {old_ep_no}) 변환 중...")

        # 1) 파일 복사 (이미지)
        # 소스 이미지 탐색
        cand_imgs = [
            images_dir / f"{old_num}_{title}.jpg",
            images_dir / f"{old_num}_삽화.jpg",
            images_dir / f"{old_num}_{title}.png",
        ]
        src_img = None
        for cand in cand_imgs:
            if cand.exists():
                src_img = cand
                break
        
        target_img_path = images_dir / target_img_name
        if src_img and src_img.exists():
            shutil.copy2(src_img, target_img_path)
            # 호환용 01_삽화.jpg 도 생성
            shutil.copy2(src_img, images_dir / f"{new_idx:02d}_삽화.jpg")
            print(f"  📸 삽화 복사: {src_img.name} -> {target_img_name}")

        # 2) 파일 복사 (낭송 음원)
        cand_recites = [
            music_dir / f"{old_num}_낭송.wav",
            music_dir / f"{old_num}_낭송.mp3",
        ]
        for c in cand_recites:
            if c.exists():
                shutil.copy2(c, music_dir / f"{new_idx:02d}_낭송{c.suffix}")
                print(f"  🎙️ 낭송 음원 복사: {c.name} -> {new_idx:02d}_낭송{c.suffix}")
                break

        # 3) 파일 복사 (노래 음원)
        cand_musics = [
            music_dir / f"{old_num}_음원.mp3",
            music_dir / f"{old_num}_음원.m4a",
            music_dir / f"{old_num}_음원.wav",
        ]
        for c in cand_musics:
            if c.exists():
                shutil.copy2(c, music_dir / f"{new_idx:02d}_음원{c.suffix}")
                print(f"  🎵 노래 음원 복사: {c.name} -> {new_idx:02d}_음원{c.suffix}")
                break

        # 4) 리비전 복사
        old_rev = revisions_dir / f"제{old_num}화.json"
        new_rev = revisions_dir / f"제{new_idx:02d}화.json"
        if old_rev.exists():
            shutil.copy2(old_rev, new_rev)
            print(f"  📜 리비전 복사: 제{old_num}화.json -> 제{new_idx:02d}화.json")

        # 5) 섹션 텍스트 업데이트
        s_text = old_sec

        # 헤더 치환
        s_text = re.sub(r'##\s*\[(?:제)?\d+화?\]\s*(.+)', f'## [{new_ep_no}] {title}', s_text, count=1)

        # 삽화 파일 경로 치환
        s_text = re.sub(r'- \*\*삽화 파일\*\*:\s*`?[^\n`]+`?', f'- **삽화 파일**: `images/{target_img_name}`', s_text)

        # 낭송 음원 경로 치환
        s_text = re.sub(r'- \*\*낭송 음원\*\*:\s*`?[^\n`]+`?', f'- **낭송 음원**: `music/{new_idx:02d}_낭송.wav`', s_text)

        # 노래 음원 경로 치환
        s_text = re.sub(r'- \*\*노래 음원\*\*:\s*`?[^\n`]+`?', f'- **노래 음원**: `music/{new_idx:02d}_음원.mp3`', s_text)

        # 조판 설정 JSON 내 이미지 경로 치환
        m_cfg = re.search(r'- \*\*조판 설정\*\*:\s*`(\{.*?\})`', s_text)
        if m_cfg:
            try:
                cfg_obj = json.loads(m_cfg.group(1))
                # pages 내 image_file 치환
                for p in cfg_obj.get("pages", []):
                    img_f = p.get("image_file", "")
                    if img_f:
                        p["image_file"] = f"images/{target_img_name}"
                # image_settings 치환
                img_sets = cfg_obj.get("image_settings", {})
                for k, v in img_sets.items():
                    if isinstance(v, dict) and "file" in v:
                        v["file"] = f"images/{target_img_name}"
                new_cfg_str = json.dumps(cfg_obj, ensure_ascii=False)
                s_text = s_text.replace(m_cfg.group(1), new_cfg_str)
            except Exception as e:
                print(f"  ⚠️ 조판 설정 JSON 치환 오류: {e}")

        new_sections.append(s_text.strip())

    # 2. 작품집_원고.md 파일 작성
    header = (
        "# 📖 [시범 선집 6편] 노을빛 기억 대표 서정시선 (定草本)\n\n"
        "> **지은이**: 임종훈  \n"
        "> **부제**: 흙과 솜꽃, 그리고 어머니의 온기  \n"
        "> **기획**: 유년의 기억과 향토적 정서, 그리고 전통 직조의 미학을 담은 대표 시선집 (진행 현황: 6 / 6편 완료)  \n\n"
        "---\n\n"
    )

    full_new_manuscript = header + "\n\n---\n\n".join(new_sections) + "\n"
    (PROJECT_DIR / "작품집_원고.md").write_text(full_new_manuscript, encoding="utf-8")
    print(f"\n✅ [작품집_원고.md] 6편 전용 원고로 재작성 완료!")

    # 3. project.json 갱신
    proj_meta = {
        "id": "노을빛_기억",
        "name": "노을빛 기억",
        "subtitle": "흙과 솜꽃, 그리고 어머니의 온기",
        "author": "임종훈",
        "target_count": 6,
        "description": "유년의 기억과 향토적 정서, 그리고 전통 직조의 미학을 담은 대표 서정시선 6편",
        "book_type": "illustrated",
        "owner_id": "377330e8-661b-4b2e-9ba8-7d0bd4636edb",
        "owner_email": "sotdanjii@gmail.com",
        "created_at": "2026-09-24",
        "updated_at": "2026-11-08"
    }
    (PROJECT_DIR / "project.json").write_text(json.dumps(proj_meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ [project.json] target_count: 6 설정 완료!")

    # 4. CSV 및 갤러리 HTML 빌드
    from core.project_manager import project_manager
    from core.csv_builder import build_canva_csv
    from core.gallery_builder import sync_project_gallery_html

    project_manager.set_active_project_id("노을빛_기억")
    count, csv_path = build_canva_csv(output_file=PROJECT_DIR / "시화집_본문데이터.csv")
    print(f"✅ [시화집_본문데이터.csv] {count}편 빌드 완료 -> {csv_path.name}")

    ok = sync_project_gallery_html(project_id="노을빛_기억")
    print(f"✅ [시화집_갤러리.html] 동기화 결과: {ok}")

    print("\n🎉 모든 교체 및 동기화 작업이 성공적으로 완료되었습니다!")

if __name__ == "__main__":
    run()
