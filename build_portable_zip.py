"""
build_portable_zip.py
StoryBook Studio 배포용 무설치 포터블 패키지(StoryBook_Studio_v1.0.zip) 자동 빌더
- 개인 API 키(.env) 및 관리자 로그인 세션(.auth_session.json) 완벽 제외
- 개발용 캐시(__pycache__, .pytest_cache, .git, .venv, scratch, tests) 자동 배제
- 시니어/초보자가 압축 해제 후 [시집만들기.bat]만 누르면 즉시 실행되도록 클린 패키징
"""

import sys
import zipfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_ZIP = OUTPUT_DIR / "StoryBook_Studio_v1.0.zip"

# 배포판에서 절대 제외해야 할 폴더 및 파일 목록 (보안 및 경량화)
EXCLUDE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".exports",
    "outputs",
    "scratch",
    "tests",
    "docs",
    "scripts",
}

EXCLUDE_FILES = {
    ".env",
    ".auth_session.json",
    ".active_project",
    ".gitignore",
    "폴더명_StoryBook으로_변경.bat",
    "노을빛기억_시화집.lnk",
    "debug_failures.py",
    "test_backend_full.py",
    "test_python_syntax.py",
    "test_static_integrity.py",
    "build_portable_zip.py",
}


def build_clean_portable_zip(output_path: Path = OUTPUT_ZIP) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    added_count = 0

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for item in BASE_DIR.rglob("*"):
            rel_parts = item.relative_to(BASE_DIR).parts
            if any(part in EXCLUDE_DIRS for part in rel_parts):
                continue
            if item.is_file():
                if item.name in EXCLUDE_FILES or item.suffix == ".pyc":
                    continue
                arcname = Path("StoryBook_Studio") / item.relative_to(BASE_DIR)
                zf.write(item, arcname)
                added_count += 1

    size_mb = round(output_path.stat().st_size / (1024 * 1024), 2)
    print("=" * 65)
    print(f"✅ 클린 포터블 패키지 빌드 완료: {output_path}")
    print(f"   - 수록 파일 수: {added_count}개 (개인 .env 및 세션 파일 100% 제외)")
    print(f"   - 압축 파일 크기: {size_mb} MB")
    print("=" * 65)
    return output_path


if __name__ == "__main__":
    build_clean_portable_zip()
