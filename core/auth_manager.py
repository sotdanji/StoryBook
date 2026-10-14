"""
core/auth_manager.py
StoryBook Studio - Supabase 기반 중앙 회원 인증 및 로컬 세션 관리자
- 사용자의 로그인 세션(.auth_session.json) 보관 및 검증
- Supabase Auth API를 통한 유효 회원 여부 0.1초 원격 검증
- 오프라인 게스트 모드 및 정식 회원 모드 분기 처리
"""

import os
import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, Dict, Any

from core.config import BASE_DIR, get_supabase_config, is_admin_email

SESSION_FILE = BASE_DIR / ".auth_session.json"


class AuthManager:
    """중앙 Supabase 인증 및 로컬 스튜디오 세션 관리 클래스"""

    def __init__(self):
        self.session_path = SESSION_FILE

    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """로컬에 저장된 현재 로그인 사용자 정보를 반환합니다."""
        if not self.session_path.exists():
            return None
        try:
            with open(self.session_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data and isinstance(data, dict) and data.get("user_id"):
                    return data
        except Exception:
            pass
        return None

    def save_session(
        self,
        user_id: str,
        email: str,
        access_token: str,
        name: Optional[str] = None,
        provider: str = "google"
    ) -> Dict[str, Any]:
        """로그인 성공 시 세션을 로컬에 안전하게 영구 저장합니다."""
        import datetime
        display_name = name or email.split("@")[0] if email else "작가님"
        session_data = {
            "user_id": user_id,
            "email": email,
            "display_name": display_name,
            "access_token": access_token,
            "provider": provider,
            "logged_in_at": datetime.datetime.now().isoformat(),
            "is_authenticated": True
        }
        with open(self.session_path, "w", encoding="utf-8") as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)

        return session_data

    def clear_session(self) -> bool:
        """로그아웃 처리 (로컬 세션 파일 삭제)"""
        try:
            if self.session_path.exists():
                self.session_path.unlink()
            return True
        except Exception:
            return False

    def verify_token_remote(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Supabase Auth API(/auth/v1/user)를 원격 호출하여 
        발급된 토큰이 실제 가입된 정상 회원의 것인지 0.1초 만에 검증합니다.
        """
        config = get_supabase_config()
        if not config["configured"] or not access_token:
            return None

        url = f"{config['url'].rstrip('/')}/auth/v1/user"
        headers = {
            "apikey": config["anon_key"],
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        try:
            req = urllib.request.Request(url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=4.0) as response:
                if response.status == 200:
                    user_data = json.loads(response.read().decode("utf-8"))
                    return user_data
        except urllib.error.HTTPError as e:
            print(f"Supabase Token Verification HTTP Error: {e.code}")
        except Exception as e:
            print(f"Supabase Token Verification Error: {e}")

        return None

    def is_current_user_admin(self) -> bool:
        """현재 로그인 사용자가 최고 관리자인지 검증합니다."""
        user = self.get_current_user()
        if not user or not user.get("email"):
            return False
        return is_admin_email(user.get("email"))

    def get_auth_status(self) -> Dict[str, Any]:
        """현재 스튜디오의 로그인 상태 및 회원 정보를 요약 반환합니다."""
        user = self.get_current_user()
        config = get_supabase_config()
        is_admin = self.is_current_user_admin()
        return {
            "is_logged_in": bool(user and user.get("is_authenticated")),
            "is_admin": is_admin,
            "user": user,
            "supabase_configured": config["configured"],
            "supabase_url": config["url"]
        }


auth_manager = AuthManager()
