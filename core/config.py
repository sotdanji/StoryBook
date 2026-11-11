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
# [완전 이전] Turso DB Cloud 및 회원 인증 (Supabase 완전 제거)
# -------------------------------------------------------------
def get_supabase_config() -> dict:
    """[하위 호환] Supabase는 Turso DB Cloud로 100% 이전되어 완전 비활성화되었습니다."""
    return {"url": "", "anon_key": "", "configured": False}

# -------------------------------------------------------------
# 관리자(Admin) 권한 설정
# -------------------------------------------------------------
ADMIN_EMAILS = [
    email.strip().lower()
    for email in os.getenv("ADMIN_EMAILS", "").split(",")
    if email.strip()
]

def is_admin_email(email: Optional[str]) -> bool:
    """주어진 이메일이 최고 관리자 권한을 가졌는지 검증합니다."""
    if not email:
        return False
    return email.strip().lower() in ADMIN_EMAILS


# -------------------------------------------------------------
# 단일 플랫폼 클라우드 인프라 (Turso libSQL & Cloudflare R2) 설정
# -------------------------------------------------------------
def get_cloud_infrastructure_status() -> dict:
    """현재 Turso DB 및 Cloudflare R2 연동 상태를 반환합니다."""
    turso_url = os.getenv("TURSO_DATABASE_URL", "").strip()
    turso_token = os.getenv("TURSO_AUTH_TOKEN", "").strip()
    r2_endpoint = os.getenv("R2_ENDPOINT_URL", "").strip() or os.getenv("R2_ACCOUNT_ID", "").strip()
    r2_access = os.getenv("R2_ACCESS_KEY_ID", "").strip()
    r2_secret = os.getenv("R2_SECRET_ACCESS_KEY", "").strip()
    r2_public = os.getenv("R2_PUBLIC_URL", "").strip()

    return {
        "turso_configured": bool(turso_url and turso_token),
        "turso_url_masked": f"{turso_url[:24]}..." if turso_url else "로컬 SQLite 모드 (storybook_master.sqlite)",
        "r2_configured": bool(r2_endpoint and r2_access and r2_secret),
        "r2_public_url": r2_public or "로컬 정적 서빙 모드 (/projects)",
    }



