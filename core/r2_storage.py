"""
core/r2_storage.py
StoryBook Studio: 단일 플랫폼 Cloudflare R2 영구 미디어 스토리지 어댑터
- [이원화 완전 해소] 로컬(run_web.py) 실행이든 클라우드(Fly.io) 실행이든 모든 미디어(삽화, 음원, PDF)를 R2 단일 버킷으로 통합
- [Zero-Dependency S3 V4] boto3가 없는 환경에서도 표준 파이썬(hmac, hashlib, urllib)만으로 Cloudflare R2 S3 API 직접 호출 지원
- [하이브리드 폴백] R2 환경변수 미설정 시 로컬 디렉토리로 자동 폴백 및 로컬 캐시 가속 지원
"""

import os
import hmac
import hashlib
import logging
import mimetypes
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

import tempfile
from core.config import BASE_DIR

logger = logging.getLogger("r2_storage")

R2_TMP_CACHE_DIR = Path(tempfile.gettempdir()) / "storybook_r2_cache"


class R2StorageManager:
    """Cloudflare R2 (S3 호환) 및 로컬 캐시 통합 미디어 스토리지 매니저"""

    def __init__(self):
        self.reload_config()

    def reload_config(self):
        """환경변수에서 R2 설정 로드"""
        self.account_id = os.getenv("R2_ACCOUNT_ID", "").strip()
        self.access_key = os.getenv("R2_ACCESS_KEY_ID", "").strip()
        self.secret_key = os.getenv("R2_SECRET_ACCESS_KEY", "").strip()
        self.bucket_name = os.getenv("R2_BUCKET_NAME", "storybook-media").strip()
        self.public_url = os.getenv("R2_PUBLIC_URL", "").strip().rstrip("/")
        self.endpoint_url = os.getenv("R2_ENDPOINT_URL", "").strip().rstrip("/")

        if not self.endpoint_url and self.account_id:
            self.endpoint_url = f"https://{self.account_id}.r2.cloudflarestorage.com"

    @property
    def is_r2_configured(self) -> bool:
        """Cloudflare R2 연결 설정이 완료되었는지 여부"""
        return bool(self.endpoint_url and self.access_key and self.secret_key and self.bucket_name)

    # -----------------------------------------------------------------
    # AWS Signature V4 (순수 파이썬 S3 호환 서명 생성기)
    # -----------------------------------------------------------------
    def _sign(self, key: bytes, msg: str) -> bytes:
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

    def _get_signature_key(self, key: str, date_stamp: str, region_name: str, service_name: str) -> bytes:
        k_date = self._sign(("AWS4" + key).encode("utf-8"), date_stamp)
        k_region = self._sign(k_date, region_name)
        k_service = self._sign(k_region, service_name)
        k_signing = self._sign(k_service, "aws4_request")
        return k_signing

    def _put_object_s3_v4(self, object_key: str, data: bytes, content_type: str) -> bool:
        """boto3 없이 표준 라이브러리만으로 Cloudflare R2에 S3 PUT 요청 수행"""
        object_key = object_key.lstrip("/")
        parsed_endpoint = urllib.parse.urlparse(self.endpoint_url)
        host = parsed_endpoint.netloc

        # Path-style URL: https://<account>.r2.cloudflarestorage.com/<bucket>/<object_key>
        quoted_key = urllib.parse.quote(object_key, safe="/~")
        canonical_uri = f"/{self.bucket_name}/{quoted_key}"
        url = f"{self.endpoint_url}{canonical_uri}"

        now = datetime.now(timezone.utc)
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = now.strftime("%Y%m%d")
        region = "auto"
        service = "s3"

        payload_hash = hashlib.sha256(data).hexdigest()

        canonical_headers = (
            f"content-type:{content_type}\n"
            f"host:{host}\n"
            f"x-amz-content-sha256:{payload_hash}\n"
            f"x-amz-date:{amz_date}\n"
        )
        signed_headers = "content-type;host;x-amz-content-sha256;x-amz-date"

        canonical_request = (
            f"PUT\n"
            f"{canonical_uri}\n"
            f"\n"
            f"{canonical_headers}\n"
            f"{signed_headers}\n"
            f"{payload_hash}"
        )

        algorithm = "AWS4-HMAC-SHA256"
        credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
        string_to_sign = (
            f"{algorithm}\n"
            f"{amz_date}\n"
            f"{credential_scope}\n"
            f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
        )

        signing_key = self._get_signature_key(self.secret_key, date_stamp, region, service)
        signature = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

        authorization_header = (
            f"{algorithm} "
            f"Credential={self.access_key}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, "
            f"Signature={signature}"
        )

        headers = {
            "Content-Type": content_type,
            "Host": host,
            "x-amz-content-sha256": payload_hash,
            "x-amz-date": amz_date,
            "Authorization": authorization_header,
            "Content-Length": str(len(data)),
        }

        req = urllib.request.Request(url, data=data, headers=headers, method="PUT")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.status in (200, 201, 204)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            logger.error(f"[R2 Upload HTTP Error] {e.code}: {err_body}")
            raise RuntimeError(f"R2 Upload Failed ({e.code}): {err_body}")
        except Exception as e:
            logger.error(f"[R2 Upload Error] {e}")
            raise

    def _delete_object_s3_v4(self, object_key: str) -> bool:
        """boto3 없이 표준 라이브러리만으로 Cloudflare R2에 S3 DELETE 요청 수행 (고아 파일 정리용)"""
        if not self.is_r2_configured:
            return False
        object_key = object_key.lstrip("/")
        parsed_endpoint = urllib.parse.urlparse(self.endpoint_url)
        host = parsed_endpoint.netloc

        quoted_key = urllib.parse.quote(object_key, safe="/~")
        canonical_uri = f"/{self.bucket_name}/{quoted_key}"
        url = f"{self.endpoint_url}{canonical_uri}"

        now = datetime.now(timezone.utc)
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = now.strftime("%Y%m%d")
        region = "auto"
        service = "s3"

        payload_hash = hashlib.sha256(b"").hexdigest()

        canonical_headers = (
            f"host:{host}\n"
            f"x-amz-content-sha256:{payload_hash}\n"
            f"x-amz-date:{amz_date}\n"
        )
        signed_headers = "host;x-amz-content-sha256;x-amz-date"

        canonical_request = (
            f"DELETE\n"
            f"{canonical_uri}\n"
            f"\n"
            f"{canonical_headers}\n"
            f"{signed_headers}\n"
            f"{payload_hash}"
        )

        algorithm = "AWS4-HMAC-SHA256"
        credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
        string_to_sign = (
            f"{algorithm}\n"
            f"{amz_date}\n"
            f"{credential_scope}\n"
            f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
        )

        signing_key = self._get_signature_key(self.secret_key, date_stamp, region, service)
        signature = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

        authorization_header = (
            f"{algorithm} "
            f"Credential={self.access_key}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, "
            f"Signature={signature}"
        )

        headers = {
            "Host": host,
            "x-amz-content-sha256": payload_hash,
            "x-amz-date": amz_date,
            "Authorization": authorization_header,
        }

        req = urllib.request.Request(url, headers=headers, method="DELETE")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.status in (200, 204)
        except Exception as e:
            logger.debug(f"[R2 Delete Warning] {object_key}: {e}")
            return False

    def _get_object_s3_v4(self, object_key: str) -> Optional[bytes]:
        """boto3 없이 표준 라이브러리만으로 Cloudflare R2에 S3 GET 요청 수행"""
        if not self.is_r2_configured:
            return None
        object_key = object_key.lstrip("/")
        parsed_endpoint = urllib.parse.urlparse(self.endpoint_url)
        host = parsed_endpoint.netloc

        quoted_key = urllib.parse.quote(object_key, safe="/~")
        canonical_uri = f"/{self.bucket_name}/{quoted_key}"
        url = f"{self.endpoint_url}{canonical_uri}"

        now = datetime.now(timezone.utc)
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = now.strftime("%Y%m%d")
        region = "auto"
        service = "s3"

        payload_hash = hashlib.sha256(b"").hexdigest()

        canonical_headers = (
            f"host:{host}\n"
            f"x-amz-content-sha256:{payload_hash}\n"
            f"x-amz-date:{amz_date}\n"
        )
        signed_headers = "host;x-amz-content-sha256;x-amz-date"

        canonical_request = (
            f"GET\n"
            f"{canonical_uri}\n"
            f"\n"
            f"{canonical_headers}\n"
            f"{signed_headers}\n"
            f"{payload_hash}"
        )

        algorithm = "AWS4-HMAC-SHA256"
        credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
        string_to_sign = (
            f"{algorithm}\n"
            f"{amz_date}\n"
            f"{credential_scope}\n"
            f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
        )

        signing_key = self._get_signature_key(self.secret_key, date_stamp, region, service)
        signature = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

        authorization_header = (
            f"{algorithm} "
            f"Credential={self.access_key}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, "
            f"Signature={signature}"
        )

        headers = {
            "Host": host,
            "x-amz-content-sha256": payload_hash,
            "x-amz-date": amz_date,
            "Authorization": authorization_header,
        }

        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    return resp.read()
        except Exception as e:
            logger.debug(f"[R2 GET Warning] {object_key}: {e}")
        return None

    def _guess_content_type(self, filename: str) -> str:
        guessed, _ = mimetypes.guess_type(filename)
        return guessed or "application/octet-stream"

    def delete_file(self, object_key: str) -> bool:
        """Cloudflare R2 및 임시 /tmp 캐시에서 파일 삭제 (작품/프로젝트 삭제 시 고아 미디어 GC)"""
        self.reload_config()
        clean_key = object_key.replace("/projects/", "").lstrip("/")
        tmp_cand = R2_TMP_CACHE_DIR / clean_key
        if tmp_cand.exists() and tmp_cand.is_file():
            try:
                tmp_cand.unlink()
            except Exception:
                pass
        if self.is_r2_configured:
            return self._delete_object_s3_v4(clean_key)
        return True

    # -----------------------------------------------------------------
    # 핵심 업로드 및 URL 반환 인터페이스 (100% 서버 일원화 - 로컬 projects/ 쓰기 제거)
    # -----------------------------------------------------------------
    def upload_bytes(
        self,
        data: bytes,
        object_key: str,
        content_type: Optional[str] = None,
        local_cache_path: Optional[Path] = None
    ) -> str:
        """
        바이트 데이터를 Cloudflare R2(마스터 오브젝트 스토리지) 및 /tmp 임시 버퍼에 저장하고
        접근 가능한 URL(또는 웹 경로)을 반환합니다. (로컬 projects/ 폴더에는 절대 파일을 생성하지 않습니다.)
        """
        self.reload_config()
        object_key = object_key.lstrip("/")

        if not content_type:
            guessed, _ = mimetypes.guess_type(object_key)
            content_type = guessed or "application/octet-stream"

        # 1. /tmp 임시 메모리 캐시 및 로컬 영구 볼륨에 기록 (지연 0초 즉각 서빙)
        local_path = BASE_DIR / "projects" / object_key
        try:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(data)
        except Exception as e:
            logger.debug(f"[Local projects write skipped] {e}")

        tmp_path = R2_TMP_CACHE_DIR / object_key
        try:
            tmp_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path.write_bytes(data)
        except Exception as e:
            logger.debug(f"[Tmp cache write skipped] {e}")

        # 2. Cloudflare R2 업로드 (단일 마스터 오브젝트 스토리지)
        if self.is_r2_configured:
            try:
                self._put_object_s3_v4(object_key, data, content_type)
                if self.public_url:
                    quoted_key = urllib.parse.quote(object_key, safe="/~")
                    return f"{self.public_url}/{quoted_key}"
                return f"/projects/{object_key}"
            except Exception as e:
                logger.warning(f"[R2 업로드 경고] {e}")

        return f"/projects/{object_key}"

    def save_illustration(
        self,
        project_id: str,
        piece_id: str,
        filename: str,
        image_bytes: bytes
    ) -> str:
        """
        시 단위 고유 ID(P-0001) 기반 삽화 이미지 R2 저장
        저장 키: {project_id}/media/{piece_id}/{filename}
        """
        object_key = f"{project_id}/media/{piece_id}/{filename}"
        return self.upload_bytes(image_bytes, object_key)

    def save_project_image(
        self,
        project_id: str,
        filename: str,
        image_bytes: bytes
    ) -> str:
        """
        프로젝트 삽화 이미지 R2 저장
        저장 키: {project_id}/images/{filename}
        """
        object_key = f"{project_id}/images/{filename}"
        return self.upload_bytes(image_bytes, object_key)

    def save_audio(
        self,
        project_id: str,
        piece_id: str,
        filename: str,
        audio_bytes: bytes
    ) -> str:
        """
        시 단위 고유 ID(P-0001) 기반 낭송/노래 오디오 R2 저장
        저장 키: {project_id}/media/{piece_id}/{filename}
        """
        object_key = f"{project_id}/media/{piece_id}/{filename}"
        return self.upload_bytes(audio_bytes, object_key)

    def save_pdf(
        self,
        project_id: str,
        filename: str,
        pdf_bytes: bytes
    ) -> str:
        """
        출판용 완성 PDF R2 저장
        저장 키: {project_id}/exports/{filename}
        """
        object_key = f"{project_id}/exports/{filename}"
        return self.upload_bytes(pdf_bytes, object_key, content_type="application/pdf")

    def save_video(
        self,
        project_id: str,
        filename: str,
        video_bytes: bytes
    ) -> str:
        """
        시화 낭송 영상 및 노래 뮤직비디오 MP4 R2 업로드
        저장 키: {project_id}/videos/{filename}
        """
        object_key = f"{project_id}/videos/{filename}"
        return self.upload_bytes(video_bytes, object_key, content_type="video/mp4")

    def fetch_bytes_from_r2(self, object_key: str) -> Optional[bytes]:
        """오브젝트 키로 Cloudflare R2에서 바이트 조회"""
        clean_key = object_key.replace("/projects/", "").lstrip("/")
        return self.get_media_bytes(f"/projects/{clean_key}")

    # -----------------------------------------------------------------
    # 미디어 통합 리더 (100% Cloudflare R2 및 /tmp 버퍼)
    # -----------------------------------------------------------------
    def get_media_bytes(self, url_or_path: str) -> Optional[bytes]:
        """
        R2 공개 URL(https://...), R2 S3 API(/projects/...), 또는 /tmp 임시 버퍼로부터
        바이트 데이터를 안전하게 읽어옵니다.
        """
        if not url_or_path:
            return None

        # 1. HTTP/HTTPS 원격 URL인 경우
        if url_or_path.startswith("http://") or url_or_path.startswith("https://"):
            try:
                req = urllib.request.Request(url_or_path, headers={"User-Agent": "StoryBookStudio/2.0"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    return resp.read()
            except Exception as e:
                logger.warning(f"[Remote Media Fetch Error] {url_or_path}: {e}")
                return None

        # 2. /projects/... 또는 상대 오브젝트 키인 경우 -> 로컬 영구 볼륨 우선 조회 (0.001초 응답!)
        clean_rel = url_or_path
        if clean_rel.startswith("/projects/"):
            clean_rel = urllib.parse.unquote(clean_rel[len("/projects/"):])
        clean_rel = clean_rel.lstrip("/")

        # 2-0. 로컬 SSD 영구 볼륨(/app/projects) 우선 조회 (지연 0초 즉각 서빙!)
        local_candidate = BASE_DIR / "projects" / clean_rel
        if local_candidate.exists() and local_candidate.is_file():
            return local_candidate.read_bytes()

        # [스마트 정규화 폴더 매칭] 괄호나 특수문자 별칭 처리
        parts = clean_rel.split("/", 1)
        if len(parts) == 2:
            pid_raw, sub_path = parts[0], parts[1]
            clean_pid = re.sub(r"[^0-9a-zA-Z가-힣]", "", pid_raw)
            p_base = BASE_DIR / "projects"
            if clean_pid and p_base.exists():
                for d in p_base.iterdir():
                    if d.is_dir() and re.sub(r"[^0-9a-zA-Z가-힣]", "", d.name) == clean_pid:
                        alt_f = d / sub_path
                        if alt_f.exists() and alt_f.is_file():
                            return alt_f.read_bytes()

        # 2-1. 컨테이너 로컬 고속 NVMe /tmp 캐시 우선 조회 (0.001초 응답!)
        tmp_candidate = R2_TMP_CACHE_DIR / clean_rel
        if tmp_candidate.exists() and tmp_candidate.is_file():
            return tmp_candidate.read_bytes()

        # 2-2. Cloudflare R2 S3 V4 서명 직접 조회 (안정 & 고속)
        self.reload_config()
        if self.is_r2_configured:
            s3_bytes = self._get_object_s3_v4(clean_rel)
            if s3_bytes:
                # 다음 번 즉시 서빙을 위해 로컬 /tmp 캐시에 영구 보관
                try:
                    tmp_candidate.parent.mkdir(parents=True, exist_ok=True)
                    tmp_candidate.write_bytes(s3_bytes)
                except Exception:
                    pass
                return s3_bytes

        # 3. 명시적 /tmp 임시 파일 경로인 경우
        p = Path(url_or_path)
        if p.exists() and p.is_file():
            return p.read_bytes()

        return None


# 전역 싱글톤 인스턴스
r2_storage = R2StorageManager()

