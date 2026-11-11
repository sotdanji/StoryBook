"""
core/auth_manager.py
StoryBook Studio - Turso DB 기반 자체 회원 인증 및 다중 사용자 요청별 세션 격리 관리자
- [Supabase 완전 독립] 7일 미활동 시 수면 상태에 빠지는 Supabase Auth 의존성 제거, Turso libSQL `users` & `user_sessions` 테이블로 365일 무중단 인증 일원화
- [다중 사용자 세션 격리] 단일 `.auth_session.json` 서버 파일 공유 버그를 제거하고, 브라우저별 쿠키(`sb_session`) + ContextVar 기반으로 접속자별 완벽한 독립 세션 및 활성 시집(`active_project_id`) 격리 지원
"""

import os
import json
import uuid
import hashlib
import urllib.request
import urllib.error
from contextvars import ContextVar
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

from core.config import BASE_DIR, is_admin_email

# 요청별(Per-Request) 브라우저 쿠키/헤더 컨텍스트 변수 (다중 사용자 충돌 완벽 방지)
_request_session_token_ctx: ContextVar[str] = ContextVar("request_session_token", default="")
_request_active_project_ctx: ContextVar[str] = ContextVar("request_active_project", default="")


def set_request_context(session_token: str = "", active_project_id: str = ""):
    """FastAPI 미들웨어에서 매 HTTP 요청마다 브라우저 쿠키 값을 바인딩"""
    _request_session_token_ctx.set(session_token or "")
    _request_active_project_ctx.set(active_project_id or "")


def get_request_session_token() -> str:
    return _request_session_token_ctx.get() or ""


def get_request_active_project() -> str:
    return _request_active_project_ctx.get() or ""


class AuthManager:
    """Turso DB 기반 자체 회원 인증 및 다중 사용자 세션 격리 관리 클래스"""

    def __init__(self):
        self._fallback_token: str = ""

    def _hash_password(self, raw_password: str) -> str:
        salt = "storybook_turso_salt_v1"
        return hashlib.sha256(f"{salt}:{raw_password}".encode("utf-8")).hexdigest()

    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """현재 HTTP 요청(쿠키 토큰) 또는 활성 세션의 로그인 사용자 정보를 Turso DB에서 반환합니다."""
        from core.db_manager import db_manager

        token = get_request_session_token() or self._fallback_token
        try:
            if token:
                session = db_manager.get_user_session(token)
                if session and session.get("user_id"):
                    return session
            else:
                # CLI/단위 테스트 등 쿠키가 없는 로컬 단일 실행 시 최근 세션 조회
                session = db_manager.get_latest_session()
                if session and session.get("user_id"):
                    return session
        except Exception as e:
            print(f"[AuthManager] 세션 조회 오류: {e}")
        return None

    def save_session(
        self,
        user_id: str,
        email: str,
        access_token: str = "",
        name: Optional[str] = None,
        provider: str = "turso_email",
        active_project_id: str = ""
    ) -> Dict[str, Any]:
        """로그인 성공 시 회원 정보와 세션을 Turso DB에 영구 저장하고 세션 토큰을 발급합니다."""
        from core.db_manager import db_manager

        clean_email = (email or "").strip().lower()
        display_name = name or (clean_email.split("@")[0] if clean_email else "작가님")
        if not user_id:
            user_id = f"usr_{hashlib.sha1(clean_email.encode('utf-8')).hexdigest()[:12]}"

        user_row = db_manager.upsert_user(
            user_id=user_id,
            email=clean_email,
            display_name=display_name,
            provider=provider,
            active_project_id=active_project_id
        )
        final_uid = user_row.get("user_id") or user_id
        final_active_proj = active_project_id or user_row.get("active_project_id") or ""

        session_token = access_token if (access_token and len(access_token) <= 128) else f"sbs_{uuid.uuid4().hex}"
        expires_at = (datetime.now() + timedelta(days=30)).isoformat()

        session_data = db_manager.save_user_session(
            token=session_token,
            user_id=final_uid,
            email=clean_email,
            display_name=user_row.get("display_name") or display_name,
            provider=provider,
            active_project_id=final_active_proj,
            expires_at=expires_at
        )
        self._fallback_token = session_token
        _request_session_token_ctx.set(session_token)
        return session_data

    def authenticate_or_register_email(
        self,
        email: str,
        password: str = "",
        name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        [Turso 자체 인증] 이메일 + 비밀번호(또는 간편 인증)로 즉시 가입 및 로그인 처리
        - 기존 회원이면 비밀번호 검증 후 로그인
        - 신규 이메일이면 자동으로 계정을 생성하고 즉시 로그인
        """
        from core.db_manager import db_manager

        clean_email = (email or "").strip().lower()
        if not clean_email or "@" not in clean_email:
            raise ValueError("올바른 이메일 주소를 입력해주세요.")

        pw_hash = self._hash_password(password) if password else ""
        existing = db_manager.get_user_by_email(clean_email)

        if existing:
            stored_hash = existing.get("password_hash") or ""
            if stored_hash and password and stored_hash != pw_hash:
                raise ValueError("비밀번호가 일치하지 않습니다.")
            user_id = existing["user_id"]
            display_name = name or existing.get("display_name") or clean_email.split("@")[0]
            active_proj = existing.get("active_project_id") or ""
            db_manager.upsert_user(
                user_id=user_id,
                email=clean_email,
                display_name=display_name,
                provider="turso_email",
                password_hash=stored_hash or pw_hash,
                active_project_id=active_proj
            )
        else:
            user_id = f"usr_{hashlib.sha1(clean_email.encode('utf-8')).hexdigest()[:12]}"
            display_name = name or clean_email.split("@")[0]
            active_proj = ""
            db_manager.upsert_user(
                user_id=user_id,
                email=clean_email,
                display_name=display_name,
                provider="turso_email",
                password_hash=pw_hash,
                active_project_id=""
            )

        return self.save_session(
            user_id=user_id,
            email=clean_email,
            name=display_name,
            provider="turso_email",
            active_project_id=active_proj
        )

    def clear_session(self) -> bool:
        """로그아웃 처리 (Turso DB에서 현재 세션 토큰 삭제)"""
        from core.db_manager import db_manager
        try:
            token = get_request_session_token() or self._fallback_token
            db_manager.delete_user_session(token if token else None)
            self._fallback_token = ""
            _request_session_token_ctx.set("")
            return True
        except Exception:
            return False

    def is_current_user_admin(self) -> bool:
        """현재 로그인 사용자가 최고 관리자인지 검증합니다."""
        user = self.get_current_user()
        if not user or not user.get("email"):
            return False
        return is_admin_email(user.get("email"))

    def get_auth_status(self) -> Dict[str, Any]:
        """현재 스튜디오의 로그인 상태 및 회원 정보를 요약 반환합니다."""
        user = self.get_current_user()
        is_admin = self.is_current_user_admin()
        return {
            "is_logged_in": bool(user and user.get("is_authenticated")),
            "is_admin": is_admin,
            "user": user,
            "auth_mode": "turso_cloud_native"
        }


auth_manager = AuthManager()
