# -*- coding: utf-8 -*-
"""
scripts/rename_sample_box.py
1. projects/노을빛_기억 (6편 시범시집) -> projects/샘플_기억상자 로 이동 및 (샘플)기억 상자 명명
2. projects/노을빛_기억_전편 (14편 원작) -> projects/노을빛_기억 으로 복원 및 [노을빛 기억] 유지
3. .active_project 를 '샘플_기억상자'로 설정 (스튜디오 기본 시범시집 마무리용)
4. 양쪽 project.json, 작품집_원고.md, 시화집_본문데이터.csv, 시화집_갤러리.html 정돈
"""

import sys
import json
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
PROJECTS_DIR = BASE_DIR / "projects"

from core.project_manager import project_manager
from core.csv_builder import build_canva_csv
from core.gallery_builder import sync_project_gallery_html

def run():
    print("=" * 60)
    print("📦 시범시집 [(샘플)기억 상자] 분리 및 [노을빛 기억] 원작 복원 시작")
    print("=" * 60)

    p_sample_old = PROJECTS_DIR / "노을빛_기억"
    p_orig_backup = PROJECTS_DIR / "노을빛_기억_전편"
    p_sample_new = PROJECTS_DIR / "샘플_기억상자"

    # Step 1: projects/노을빛_기억 -> projects/샘플_기억상자 로 이름 변경
    if p_sample_old.exists() and not p_sample_new.exists():
        p_sample_old.rename(p_sample_new)
        print("✅ [노을빛_기억] (6편) ➔ [샘플_기억상자] 폴더명 변경 완료")

    # Step 2: projects/노을빛_기억_전편 -> projects/노을빛_기억 로 이름 변경
    if p_orig_backup.exists() and not p_sample_old.exists():
        p_orig_backup.rename(p_sample_old)
        print("✅ [노을빛_기억_전편] (14편) ➔ [노을빛_기억] 원작 복원 완료")

    # Step 3: 샘플_기억상자 메타데이터 갱신
    sample_meta = {
        "id": "샘플_기억상자",
        "name": "(샘플)기억 상자",
        "subtitle": "흙과 솜꽃, 그리고 어머니의 온기",
        "author": "임종훈",
        "target_count": 6,
        "description": "스튜디오 기능 시연 및 체험을 위한 이야기솥 대표 서정시선 6편 시범시집",
        "book_type": "illustrated",
        "owner_id": "377330e8-661b-4b2e-9ba8-7d0bd4636edb",
        "owner_email": "sotdanjii@gmail.com",
        "created_at": "2026-09-24",
        "updated_at": "2026-11-08"
    }
    (p_sample_new / "project.json").write_text(json.dumps(sample_meta, ensure_ascii=False, indent=2), encoding="utf-8")
    
    # 원고 상단 타이틀 갱신
    sample_manuscript = p_sample_new / "작품집_원고.md"
    if sample_manuscript.exists():
        txt = sample_manuscript.read_text(encoding="utf-8")
        txt = txt.replace("# 📖 [시범 선집 6편] 노을빛 기억 대표 서정시선", "# 📖 [(샘플)기억 상자] 대표 서정시선 6편")
        sample_manuscript.write_text(txt, encoding="utf-8")

    # Step 4: 노을빛_기억 (사용자 원작 14편) 메타데이터 갱신
    orig_meta = {
        "id": "노을빛_기억",
        "name": "노을빛 기억",
        "subtitle": "황혼과 유년의 서정 시집",
        "author": "임종훈",
        "target_count": 35,
        "description": "고향 마을의 저녁 노을과 유년기 따스한 추억들을 담은 원작 시화집",
        "book_type": "illustrated",
        "owner_id": "377330e8-661b-4b2e-9ba8-7d0bd4636edb",
        "owner_email": "sotdanjii@gmail.com",
        "created_at": "2026-09-24",
        "updated_at": "2026-11-08"
    }
    (p_sample_old / "project.json").write_text(json.dumps(orig_meta, ensure_ascii=False, indent=2), encoding="utf-8")

    orig_manuscript = p_sample_old / "작품집_원고.md"
    if orig_manuscript.exists():
        txt = orig_manuscript.read_text(encoding="utf-8")
        txt = txt.replace("# 📖 [시범 선집 6편] 노을빛 기억 대표 서정시선 (定草本)", "# 노을빛 기억 원고 (진행 현황: 14 / 35편 완료)")
        orig_manuscript.write_text(txt, encoding="utf-8")

    # Step 5: 활성 프로젝트를 '샘플_기억상자'로 지정
    project_manager.set_active_project_id("샘플_기억상자")
    print("✅ 현재 활성 프로젝트 ➔ [샘플_기억상자] 설정 완료")

    # Step 6: 양쪽 CSV 및 갤러리 HTML 빌드
    count_sample, _ = build_canva_csv(output_file=p_sample_new / "시화집_본문데이터.csv")
    sync_project_gallery_html(project_id="샘플_기억상자")
    print(f"✅ [(샘플)기억 상자] CSV({count_sample}편) 및 갤러리 동기화 완료")

    project_manager.set_active_project_id("노을빛_기억")
    count_orig, _ = build_canva_csv(output_file=p_sample_old / "시화집_본문데이터.csv")
    sync_project_gallery_html(project_id="노을빛_기억")
    print(f"✅ [노을빛 기억 (원작)] CSV({count_orig}편) 및 갤러리 동기화 완료")

    # 다시 샘플_기억상자를 활성 프로젝트로 복구
    project_manager.set_active_project_id("샘플_기억상자")

    print("\n🎉 모든 분리 및 명명 작업이 성공적으로 완료되었습니다!")

if __name__ == "__main__":
    run()

