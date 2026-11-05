# -*- coding: utf-8 -*-
"""
scripts/build_distribution_zip.py
StoryBook Studio - 개인 PC 배포용 전체 프로그램 ZIP 패키징 스크립트
"""

import os
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / ".exports"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ZIP_NAME = "StoryBook_Studio_v1.0_무설치배포팩.zip"
ZIP_PATH = OUTPUT_DIR / ZIP_NAME

# 제외할 폴더 및 파일 패턴
EXCLUDE_DIRS = {
    ".git", ".pytest_cache", "__pycache__", ".vscode", ".idea",
    "node_modules", ".exports", "scratch", ".system_generated",
    ".venv", "venv", "env"
}
EXCLUDE_EXTS = {".pyc", ".pyo", ".pyd", ".log", ".tmp"}

README_TEXT = """================================================================================
   📖 StoryBook Studio (v1.0) - 나만의 기억 시화집 창작소
   "가장 개인적인 기억이 가장 깊은 문학이자 예술이 된다."
================================================================================

[처음 시작하는 방법]
1. 다운로드받은 이 압축 파일의 압축을 원하는 폴더(예: C:\\StoryBook 또는 문서 폴더)에 해제합니다.
2. 폴더 안에 있는 [실행하기.bat] 파일을 더블클릭합니다.
3. 최초 실행 시 윈도우 바탕화면에 [시화집 창작] 바로가기 아이콘이 자동으로 생성됩니다!
4. 잠시 후 기본 웹 브라우저가 자동으로 열리며 시화집 집필실이 시작됩니다.

[다음부터 실행할 때]
- 윈도우 바탕화면의 [시화집 창작] 아이콘을 더블클릭하시면 언제든 바로 시작됩니다!

[프로젝트 특징]
- 100% 무료 오픈소스 (AGPL-3.0)
- 서버 비용 0원, 내 컴퓨터에서 완전 독립 구동
- 개인의 소중한 기억과 원고가 외부 서버로 유출되지 않고 내 PC에만 안전하게 보관됩니다.

문의 및 편집 코칭: 스튜디오 상단의 [소통방 (1:1 상담실)]을 이용해 주세요.
================================================================================
"""

def build_zip():
    print(f"📦 StoryBook Studio 배포용 ZIP 패키징 시작: {ZIP_PATH}")
    count = 0
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        # 루트 안내문 추가
        zf.writestr("처음_실행_안내.txt", README_TEXT.encode("utf-8"))

        for root, dirs, files in os.walk(BASE_DIR):
            # 제외 폴더 필터링
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

            rel_root = Path(root).relative_to(BASE_DIR)
            if any(part in EXCLUDE_DIRS for part in rel_root.parts):
                continue

            for file in files:
                ext = Path(file).suffix.lower()
                if ext in EXCLUDE_EXTS or file.startswith("."):
                    continue

                file_path = Path(root) / file
                arcname = str(rel_root / file)
                zf.write(file_path, arcname)
                count += 1

    size_mb = ZIP_PATH.stat().st_size / (1024 * 1024)
    print(f"✅ 배포팩 생성 완료! 총 {count}개 파일 압축 (크기: {size_mb:.2f} MB)")
    print(f"📂 파일 위치: {ZIP_PATH}")
    return ZIP_PATH

if __name__ == "__main__":
    build_zip()
