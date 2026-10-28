import os
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 프로젝트 루트 디렉토리
BASE_DIR = Path(__file__).resolve().parent.parent

# 주요 파일 및 폴더 경로
MANUSCRIPT_FILE = BASE_DIR / "작품집_원고.md"
IMAGES_DIR = BASE_DIR / "images"
PLAN_FILE = BASE_DIR / "시화집_출판_계획서.md"
CANVA_CSV_FILE = BASE_DIR / "시화집_본문데이터.csv"

# 기본 출판 설정값
TARGET_POEMS_COUNT = int(os.getenv("BOOK_TARGET_POEMS", "35"))
PAPER_TYPE = os.getenv("BOOK_PAPER_TYPE", "white_100g")
DEFAULT_ART_STYLE = os.getenv("DEFAULT_ART_STYLE", "한국적 서정 수채화 (Korean Ink Watercolor)")

# 부크크 용지별 장당(2페이지) 두께 (mm 기준)
# 80페이지 = 40장
PAPER_THICKNESS = {
    "white_80g": 0.048,   # 백색모조 80g
    "white_100g": 0.060,  # 백색모조 100g (표준 권장)
    "snow_100g": 0.055,   # 스노우/아르떼 100g
}

# API 키 및 기본 AI 모델 설정
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

def _update_env_file(key_name: str, value: str) -> None:
    """지정한 환경변수를 .env 파일에 안전하게 저장하거나 갱신합니다."""
    env_path = BASE_DIR / ".env"
    existing_lines = []
    found = False

    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith(f"{key_name}="):
                    existing_lines.append(f"{key_name}={value}\n")
                    found = True
                else:
                    existing_lines.append(line)

    if not found:
        existing_lines.append(f"{key_name}={value}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(existing_lines)

def save_gemini_api_key(new_key: str) -> bool:
    """Gemini API 키를 .env 파일에 영구 저장하고 런타임 환경변수를 즉시 갱신합니다."""
    global GEMINI_API_KEY
    clean_key = new_key.strip()
    GEMINI_API_KEY = clean_key
    os.environ["GEMINI_API_KEY"] = clean_key
    _update_env_file("GEMINI_API_KEY", clean_key)
    return True

def save_gemini_model(new_model: str) -> bool:
    """선택한 Gemini 모델을 .env에 영구 저장하고 런타임 환경변수를 갱신합니다."""
    global GEMINI_MODEL
    clean_model = new_model.strip()
    GEMINI_MODEL = clean_model
    os.environ["GEMINI_MODEL"] = clean_model
    _update_env_file("GEMINI_MODEL", clean_model)
    return True

def get_gemini_api_key_status() -> dict:
    """현재 API 키 등록 상태 및 마스킹된 키를 반환합니다."""
    key = GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")
    has_key = bool(key and len(key) >= 10)
    masked = f"{key[:6]}...{key[-4:]}" if has_key else ""
    return {
        "has_key": has_key,
        "configured": has_key,
        "masked_key": masked
    }

def get_gemini_api_key() -> str:
    """현재 유효한 Gemini API 키 문자열을 반환합니다."""
    return GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")

from typing import Optional

# -------------------------------------------------------------
# Supabase 중앙 회원 인증 설정
# -------------------------------------------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")

def get_supabase_config() -> dict:
    """프론트엔드 및 백엔드에서 사용할 Supabase 공개 연결 정보를 반환합니다."""
    url = os.getenv("SUPABASE_URL", "") or SUPABASE_URL
    anon_key = os.getenv("SUPABASE_ANON_KEY", "") or SUPABASE_ANON_KEY
    return {
        "url": url.strip(),
        "anon_key": anon_key.strip(),
        "configured": bool(url and anon_key)
    }

# -------------------------------------------------------------
# 관리자(Admin) 권한 설정
# -------------------------------------------------------------
ADMIN_EMAILS = [
    email.strip().lower()
    for email in os.getenv("ADMIN_EMAILS", "sotdanjii@gmail.com,sotdanji@gmail.com").split(",")
    if email.strip()
]

def is_admin_email(email: Optional[str]) -> bool:
    """주어진 이메일이 최고 관리자 권한을 가졌는지 검증합니다."""
    if not email:
        return False
    return email.strip().lower() in ADMIN_EMAILS


