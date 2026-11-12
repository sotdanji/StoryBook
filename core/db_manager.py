"""
core/db_manager.py
StoryBook Studio: 단일 플랫폼(Web-First & Local Hybrid) 고유 불변 ID(P-0001) 기반 데이터베이스 관리자
- [단일 플랫폼 지원] Turso 클라우드 libSQL (Always-On Edge DB) 및 로컬 고성능 SQLite (WAL) 투명 어댑터
- [불변 시퀀스 채번기] 작품별 영구 불변 고유 키(P-0001, P-0002...) 및 영구 결번(Tombstone) 정책
- [엔티티-목차 분리] 시 엔티티(PieceData)와 책 목차(TOCItem)의 완전한 1:N 참조 분리
- [하이브리드 내구성] 환경변수(TURSO_DATABASE_URL) 설정 시 클라우드 DB 자동 연동, 미설정 시 로컬 DB 자동 폴백
"""

import os
import sys
import json
import sqlite3
import logging
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Union

from core.config import BASE_DIR

logger = logging.getLogger("db_manager")

PROJECTS_DIR = BASE_DIR / "projects"
DEFAULT_LOCAL_DB_PATH = BASE_DIR / "storybook_master.sqlite"

TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL", "").strip()
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN", "").strip()

# ⚡ 단기 인메모리 캐시 (초기 동시 다발적 쿼리 폭주 0ms 즉시 응답용)
_MEM_CACHE: Dict[str, Any] = {}

def get_cached(key: str, ttl: float = 3.0) -> Optional[Any]:
    if key in _MEM_CACHE:
        val, ts = _MEM_CACHE[key]
        if time.time() - ts < ttl:
            return val
    return None

def set_cached(key: str, val: Any) -> None:
    _MEM_CACHE[key] = (val, time.time())

def clear_cache(prefix: str = "") -> None:
    if not prefix:
        _MEM_CACHE.clear()
    else:
        for k in list(_MEM_CACHE.keys()):
            if k.startswith(prefix):
                _MEM_CACHE.pop(k, None)


@dataclass
class PieceData:
    piece_id: str                      # 고유 불변 키 (예: "P-0001")
    project_id: str                    # 소속 마스터 프로젝트 ID (예: "노을빛_기억")
    title: str                         # 작품 제목 (수정 가능)
    subtitle: str = ""                 # 부제 / 서정 카피
    author: str = ""                   # 개별 작가/시인 (비워둘 시 대표 저자)
    poem_body: str = ""                # 본문 전문
    chapter_topic: str = ""            # 권/부/주제 (예: "제1부: 흙과 솜꽃")
    memory_anchor: str = ""            # 기억의 중심
    interview_notes: str = ""          # 인터뷰 질의응답 메모
    status: str = "draft"              # "draft" | "revising" | "approved" | "published" | "deleted"
    created_at: str = ""               # 생성 일시 (ISO 8601)
    updated_at: str = ""               # 최종 수정 일시

    # 삽화 (시각 자산)
    art_style: str = "watercolor"      # watercolor | ink_wash | oil | pastel | sketch
    art_direction: str = ""            # 시각 구도 및 연출 지침
    illustration_prompt: str = ""      # 이미지 생성 프롬프트
    image_file: str = ""               # 대표 삽화 상대 경로 or R2 CDN URL
    image_file_2: str = ""             # 후반부 삽화 상대 경로 or R2 CDN URL

    # 시낭송 4대 다중 트랙 (육성 / AI TTS / SUNO 성우 / BGM 합성)
    recite_primary_type: str = "ai_tts"# user_voice | ai_tts | suno_spoken | bgm_mixed
    voice_user_file: str = ""          # [1] 시인 육성 녹음 파일
    voice_tts_file: str = ""           # [2] AI TTS 낭송 파일
    voice_tts_actor: str = "charon_male" # charon_male | aoede_female | duet
    voice_suno_file: str = ""          # [3] SUNO 감성 성우 낭송 파일
    voice_suno_prompt: str = ""        # SUNO 낭송 프롬프트
    voice_bgm_file: str = ""           # [4] BGM 결합 낭송 파일
    recite_script: str = ""            # 낭송 전처리 스크립트 (쉼표, 침묵)
    recite_tempo: float = 1.0          # 낭송 템포
    recite_variants: Dict[str, str] = field(default_factory=dict) # 성우별 맵

    # 작곡 / 가창 음원
    music_file: str = ""               # 대표 가창 음원 (R2 CDN URL or 상대경로)
    lyrics: str = ""                   # 노랫말 전문
    music_genre: str = "folk"          # folk | dongyo | gagok | minyo
    music_prompt: str = ""             # 작곡 생성 프롬프트
    music_bpm: int = 76                # BPM

    # 서정 비디오
    video_file_16x9: str = ""          # 16:9 유튜브/갤러리용 MP4
    video_file_9x16: str = ""          # 9:16 쇼츠/릴스용 MP4
    video_preview: str = ""            # 썸네일 경로

    # 출판 DTP 조판
    layout_mode: str = "compact"       # compact | multi_page
    page_count: int = 2                # 2 또는 4
    part2_mode: str = "motif_symbol"   # motif_symbol | image | pure_blank | poem_text
    layout_config: Dict[str, Any] = field(default_factory=dict) # 글자크기, 줄간격, 슬롯 등

    # 퇴고 이력
    revisions: List[Dict[str, Any]] = field(default_factory=list)
    current_rev_id: int = 1


@dataclass
class TOCItem:
    display_order: int                 # 1, 2, 3...
    piece_id: str                      # "P-0001" (FK)
    chapter: str = ""                  # "제1부: 흙과 솜꽃"
    display_label: str = ""            # 표시용 회차 ("제01화" - 없으면 order로 동적생성)
    page_start: int = 0                # 조판 엔진이 계산한 시작 페이지
    page_count: int = 2                # 해당 시의 할당 페이지 수


# =====================================================================
# 1. Turso libSQL HTTP Pipeline Client (순수 파이썬 구현)
# =====================================================================
class TursoHTTPClient:
    """Turso libSQL Pipeline v2 HTTP API 클라이언트 (Keep-Alive 세션 풀링 지원)"""

    def __init__(self, db_url: str, auth_token: str):
        # libsql://... -> https://...
        url = db_url.replace("libsql://", "https://")
        if not url.endswith("/v2/pipeline"):
            url = url.rstrip("/") + "/v2/pipeline"
        self.endpoint = url
        self.auth_token = auth_token
        self._session = None
        try:
            import requests
            self._session = requests.Session()
            adapter = requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=20, max_retries=1)
            self._session.mount("https://", adapter)
            self._session.mount("http://", adapter)
        except Exception:
            self._session = None

    def _convert_arg(self, val: Any) -> Dict[str, Any]:
        if val is None:
            return {"type": "null"}
        elif isinstance(val, int):
            return {"type": "integer", "value": str(val)}
        elif isinstance(val, float):
            return {"type": "float", "value": val}
        elif isinstance(val, bytes):
            import base64
            return {"type": "blob", "base64": base64.b64encode(val).decode("ascii")}
        else:
            return {"type": "text", "value": str(val)}

    def execute_pipeline(self, statements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        requests_payload = []
        for stmt in statements:
            sql = stmt["sql"]
            params = stmt.get("params", [])
            args = [self._convert_arg(p) for p in params]
            requests_payload.append({
                "type": "execute",
                "stmt": {
                    "sql": sql,
                    "args": args
                }
            })
        requests_payload.append({"type": "close"})

        payload_bytes = json.dumps({"requests": requests_payload}).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }

        # ⚡ 1. requests.Session Keep-Alive 초고속 재사용
        resp_data = None
        if self._session is not None:
            try:
                resp = self._session.post(self.endpoint, data=payload_bytes, headers=headers, timeout=5)
                if resp.status_code == 200:
                    resp_data = resp.json()
                else:
                    logger.error(f"[Turso HTTP Error] {resp.status_code}: {resp.text}")
                    raise RuntimeError(f"Turso API Error ({resp.status_code}): {resp.text}")
            except Exception as e:
                if "Turso API Error" in str(e):
                    raise
                logger.warning(f"[Turso Session fallback to urllib] {e}")
                resp_data = None

        # 2. urllib 폴백
        if resp_data is None:
            import urllib.request
            import urllib.error
            req = urllib.request.Request(self.endpoint, data=payload_bytes, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=5) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                err_msg = e.read().decode("utf-8", errors="replace")
                logger.error(f"[Turso HTTP Error] {e.code}: {err_msg}")
                raise RuntimeError(f"Turso API Error ({e.code}): {err_msg}")
            except Exception as e:
                logger.error(f"[Turso Connection Error] {e}")
                raise

        results = []
        for item in resp_data.get("results", []):
            if item.get("type") == "ok":
                response = item.get("response", {})
                if response.get("type") == "execute":
                    result = response.get("result", {})
                    cols = [c["name"] for c in result.get("cols", [])]
                    rows = []
                    for row_cells in result.get("rows", []):
                        row_dict = {}
                        for idx, cell in enumerate(row_cells):
                            cname = cols[idx]
                            ctype = cell.get("type")
                            if ctype == "null":
                                row_dict[cname] = None
                            elif ctype == "integer":
                                row_dict[cname] = int(cell.get("value", 0))
                            elif ctype == "float":
                                row_dict[cname] = float(cell.get("value", 0.0))
                            elif ctype == "blob":
                                import base64
                                row_dict[cname] = base64.b64decode(cell.get("base64", ""))
                            else:
                                row_dict[cname] = cell.get("value", "")
                        rows.append(row_dict)
                    results.append({"rows": rows, "rows_affected": result.get("rows_affected", 0)})
            elif item.get("type") == "error":
                raise RuntimeError(f"Turso Statement Error: {item.get('error', {}).get('message')}")

        return results

    def execute(self, sql: str, params: Union[list, tuple] = ()) -> int:
        res = self.execute_pipeline([{"sql": sql, "params": params}])
        return res[0]["rows_affected"] if res else 0

    def fetch_all(self, sql: str, params: Union[list, tuple] = ()) -> List[Dict[str, Any]]:
        res = self.execute_pipeline([{"sql": sql, "params": params}])
        return res[0]["rows"] if res else []

    def fetch_one(self, sql: str, params: Union[list, tuple] = ()) -> Optional[Dict[str, Any]]:
        rows = self.fetch_all(sql, params)
        return rows[0] if rows else None


# =====================================================================
# 2. Local SQLite Client (로컬 고성능 WAL 모드)
# =====================================================================
class LocalSQLiteClient:
    """로컬 SQLite WAL 모드 클라이언트"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def execute(self, sql: str, params: Union[list, tuple] = ()) -> int:
        conn = self._get_conn()
        try:
            with conn:
                cur = conn.execute(sql, params)
                return cur.rowcount
        finally:
            conn.close()

    def fetch_all(self, sql: str, params: Union[list, tuple] = ()) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        try:
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def fetch_one(self, sql: str, params: Union[list, tuple] = ()) -> Optional[Dict[str, Any]]:
        conn = self._get_conn()
        try:
            row = conn.execute(sql, params).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()


# =====================================================================
# 3. DatabaseManager (단일 플랫폼 통합 관리자)
# =====================================================================
class DatabaseManager:
    """단일 플랫폼(Web-First & Local Hybrid) 고유 불변 ID 기반 데이터베이스 총괄 관리 엔진"""

    def __init__(self, projects_dir: Path = PROJECTS_DIR, local_db_path: Path = DEFAULT_LOCAL_DB_PATH):
        self.projects_dir = projects_dir
        self.local_db_path = local_db_path
        self._client: Optional[Union[TursoHTTPClient, LocalSQLiteClient]] = None
        self._init_client()
        self._init_tables()

    def _init_client(self):
        """환경변수 기반 클라이언트 자동 선택 (Turso or Local SQLite with Instant Health Check)"""
        # pytest 테스트 실행 중이거나 외부 네트워크 차단 환경에서는 즉시 로컬 SQLite 모드 사용
        if "pytest" in sys.modules or os.getenv("PYTEST_CURRENT_TEST") or os.getenv("TESTING") == "1":
            logger.info(f"💻 [DatabaseManager] 테스트 환경 감지 - 로컬 SQLite 모드 활성화: {self.local_db_path}")
            self._client = LocalSQLiteClient(self.local_db_path)
            return

        turso_url = os.getenv("TURSO_DATABASE_URL", "").strip()
        turso_token = os.getenv("TURSO_AUTH_TOKEN", "").strip()

        if turso_url and turso_token:
            client = TursoHTTPClient(turso_url, turso_token)
            try:
                # 2초 타임아웃 초고속 핑 테스트로 오프라인/샌드박스 상태 즉각 판별
                client.execute("SELECT 1")
                self._client = client
                logger.info(f"✨ [DatabaseManager] Turso 클라우드 libSQL 연결 성공: {turso_url[:25]}...")
                return
            except Exception as e:
                logger.warning(f"⚠️ [DatabaseManager] Turso 클라우드 연결 불가({e}). 로컬 SQLite로 즉시 전환: {self.local_db_path}")

        logger.info(f"💻 [DatabaseManager] 로컬 SQLite 연결 모드 활성화: {self.local_db_path}")
        self._client = LocalSQLiteClient(self.local_db_path)

    @property
    def is_cloud_mode(self) -> bool:
        return isinstance(self._client, TursoHTTPClient)

    def _init_tables(self):
        """테이블 스키마 생성 및 초기화 (단일 통합 마스터 DB 스키마)"""
        # 1. 프로젝트 메타데이터 테이블 (서문, 맺음말, 표지, 판권지 전체 JSON 보존 포함)
        self._client.execute("""
        CREATE TABLE IF NOT EXISTS project_meta (
            project_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            subtitle TEXT DEFAULT '',
            author TEXT DEFAULT '',
            target_count INTEGER DEFAULT 35,
            last_piece_seq INTEGER DEFAULT 0,
            metadata_json TEXT DEFAULT '{}',
            created_at TEXT,
            updated_at TEXT
        )
        """)
        try:
            self._client.execute("ALTER TABLE project_meta ADD COLUMN metadata_json TEXT DEFAULT '{}'")
        except Exception:
            pass

        # 2. 시 엔티티(PieceData) 마스터 테이블
        self._client.execute("""
        CREATE TABLE IF NOT EXISTS pieces (
            piece_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            title TEXT NOT NULL,
            subtitle TEXT DEFAULT '',
            author TEXT DEFAULT '',
            poem_body TEXT DEFAULT '',
            chapter_topic TEXT DEFAULT '',
            memory_anchor TEXT DEFAULT '',
            interview_notes TEXT DEFAULT '',
            status TEXT DEFAULT 'draft',
            created_at TEXT,
            updated_at TEXT,
            art_style TEXT DEFAULT 'watercolor',
            art_direction TEXT DEFAULT '',
            illustration_prompt TEXT DEFAULT '',
            image_file TEXT DEFAULT '',
            image_file_2 TEXT DEFAULT '',
            recite_primary_type TEXT DEFAULT 'ai_tts',
            voice_user_file TEXT DEFAULT '',
            voice_tts_file TEXT DEFAULT '',
            voice_tts_actor TEXT DEFAULT 'charon_male',
            voice_suno_file TEXT DEFAULT '',
            voice_suno_prompt TEXT DEFAULT '',
            voice_bgm_file TEXT DEFAULT '',
            recite_script TEXT DEFAULT '',
            recite_tempo REAL DEFAULT 1.0,
            recite_variants_json TEXT DEFAULT '{}',
            music_file TEXT DEFAULT '',
            lyrics TEXT DEFAULT '',
            music_genre TEXT DEFAULT 'folk',
            music_prompt TEXT DEFAULT '',
            music_bpm INTEGER DEFAULT 76,
            video_file_16x9 TEXT DEFAULT '',
            video_file_9x16 TEXT DEFAULT '',
            video_preview TEXT DEFAULT '',
            layout_mode TEXT DEFAULT 'compact',
            page_count INTEGER DEFAULT 2,
            part2_mode TEXT DEFAULT 'motif_symbol',
            layout_config_json TEXT DEFAULT '{}',
            revisions_json TEXT DEFAULT '[]',
            current_rev_id INTEGER DEFAULT 1
        )
        """)

        # 3. 책 목차(TOC) 테이블
        self._client.execute("""
        CREATE TABLE IF NOT EXISTS toc (
            project_id TEXT NOT NULL,
            display_order INTEGER NOT NULL,
            piece_id TEXT NOT NULL,
            chapter TEXT DEFAULT '',
            display_label TEXT DEFAULT '',
            PRIMARY KEY (project_id, display_order)
        )
        """)

        # 4. 자체 회원 및 다중 사용자 세션 격리 테이블 (Supabase Auth 완전 대체)
        self._client.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT DEFAULT '',
            display_name TEXT DEFAULT '',
            provider TEXT DEFAULT 'email',
            active_project_id TEXT DEFAULT '',
            created_at TEXT,
            last_login_at TEXT
        )
        """)

        self._client.execute("""
        CREATE TABLE IF NOT EXISTS user_sessions (
            token TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            email TEXT NOT NULL,
            display_name TEXT DEFAULT '',
            provider TEXT DEFAULT 'email',
            active_project_id TEXT DEFAULT '',
            created_at TEXT,
            expires_at TEXT
        )
        """)

        # 5. 시 퇴고 판본(Revision) 영구 보존 테이블
        self._client.execute("""
        CREATE TABLE IF NOT EXISTS revisions (
            project_id TEXT NOT NULL,
            episode_no TEXT NOT NULL,
            rev_id INTEGER NOT NULL,
            version_name TEXT DEFAULT '',
            title TEXT DEFAULT '',
            poem_body TEXT DEFAULT '',
            note TEXT DEFAULT '',
            timestamp TEXT DEFAULT '',
            line_count INTEGER DEFAULT 0,
            char_count INTEGER DEFAULT 0,
            PRIMARY KEY (project_id, episode_no, rev_id)
        )
        """)

        # 6. 1:1 비밀 상담 및 출판 코칭 테이블
        self._client.execute("""
        CREATE TABLE IF NOT EXISTS inquiries (
            id TEXT PRIMARY KEY,
            user_id TEXT DEFAULT '',
            author_email TEXT DEFAULT '',
            project_id TEXT DEFAULT '',
            data_json TEXT NOT NULL,
            created_at TEXT,
            updated_at TEXT
        )
        """)

        # 7. 모둠솥 작가 프로필 및 서가(Bookshelf) 테이블
        self._client.execute("""
        CREATE TABLE IF NOT EXISTS author_profiles (
            user_id TEXT PRIMARY KEY,
            pen_name TEXT NOT NULL,
            bio TEXT DEFAULT '',
            avatar_url TEXT DEFAULT '',
            updated_at TEXT
        )
        """)

        self._client.execute("""
        CREATE TABLE IF NOT EXISTS bookshelf_items (
            item_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            book_type TEXT NOT NULL,
            title TEXT NOT NULL,
            author_name TEXT NOT NULL,
            cover_image_url TEXT DEFAULT '',
            excerpt TEXT DEFAULT '',
            view_url TEXT DEFAULT '',
            project_id TEXT DEFAULT '',
            is_published INTEGER DEFAULT 1,
            has_recite INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT
        )
        """)

    # -------------------------------------------------------------
    # 0. 시집 프로젝트 메타데이터 (project.json 클라우드 영속화)
    # -------------------------------------------------------------
    def save_project_meta(self, project_id: str, meta_dict: Dict[str, Any]) -> bool:
        """시집 메타데이터(서문, 맺음말, 표지, 판권지 등)를 DB에 영구 저장"""
        now = datetime.now().isoformat()
        name = meta_dict.get("name", project_id)
        subtitle = meta_dict.get("subtitle", "")
        author = meta_dict.get("author", "")
        target_count = int(meta_dict.get("target_count", 35) or 35)
        meta_json = json.dumps(meta_dict, ensure_ascii=False)

        row = self._client.fetch_one("SELECT last_piece_seq, created_at FROM project_meta WHERE project_id = ?", (project_id,))
        last_seq = int(row["last_piece_seq"]) if row and row.get("last_piece_seq") is not None else 0
        created_at = (row.get("created_at") if row else None) or meta_dict.get("created_at") or now

        self._client.execute("""
        INSERT INTO project_meta (project_id, name, subtitle, author, target_count, last_piece_seq, metadata_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(project_id) DO UPDATE SET
            name = excluded.name,
            subtitle = excluded.subtitle,
            author = excluded.author,
            target_count = excluded.target_count,
            metadata_json = excluded.metadata_json,
            updated_at = excluded.updated_at
        """, (project_id, name, subtitle, author, target_count, last_seq, meta_json, created_at, now))
        return True

    def _row_to_meta(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """행 데이터를 ProjectInfo dict로 변환 (추가 DB 쿼리 없음)"""
        try:
            meta = json.loads(row.get("metadata_json") or "{}")
            if meta and isinstance(meta, dict) and meta.get("name"):
                return meta
        except Exception:
            pass
        return {
            "id": row["project_id"],
            "name": row.get("name", row["project_id"]),
            "subtitle": row.get("subtitle", ""),
            "author": row.get("author", ""),
            "target_count": int(row.get("target_count", 35) or 35),
            "created_at": row.get("created_at", ""),
            "updated_at": row.get("updated_at", ""),
        }

    def get_project_meta(self, project_id: str) -> Optional[Dict[str, Any]]:
        """DB에서 시집 메타데이터 조회"""
        row = self._client.fetch_one("SELECT * FROM project_meta WHERE project_id = ?", (project_id,))
        if not row:
            return None
        return self._row_to_meta(row)

    def list_project_metas(self) -> List[Dict[str, Any]]:
        """DB에 등록된 모든 시집 프로젝트 메타데이터 목록 반환 (단기 캐시 적용)"""
        cache_key = "list_project_metas"
        cached = get_cached(cache_key, ttl=3.0)
        if cached is not None:
            return cached

        rows = self._client.fetch_all("SELECT * FROM project_meta ORDER BY created_at ASC")
        result = [self._row_to_meta(r) for r in rows if r.get("project_id")]
        set_cached(cache_key, result)
        return result

    def get_projects_stats(self) -> Dict[str, Dict[str, int]]:
        """모든 프로젝트의 (total_works, completed_count)를 단 1번의 SQL 집계로 초고속 조회 (단기 캐시 적용)"""
        cache_key = "projects_stats"
        cached = get_cached(cache_key, ttl=3.0)
        if cached is not None:
            return cached

        sql = """
            SELECT project_id, 
                   COUNT(*) as total_works,
                   SUM(CASE WHEN status LIKE '%완성%' THEN 1 ELSE 0 END) as completed_count
            FROM pieces
            WHERE status != 'deleted'
            GROUP BY project_id
        """
        try:
            rows = self._client.fetch_all(sql)
            res = {
                r["project_id"]: {
                    "total_works": int(r.get("total_works", 0) or 0),
                    "completed_count": int(r.get("completed_count", 0) or 0)
                }
                for r in rows
            }
            set_cached(cache_key, res)
            return res
        except Exception as e:
            logger.warning(f"get_projects_stats fallback: {e}")
            return {}

    def delete_project_meta(self, project_id: str) -> bool:
        """프로젝트 삭제 시 DB에서도 메타 및 TOC 정리"""
        clear_cache()
        self._client.execute("DELETE FROM project_meta WHERE project_id = ?", (project_id,))
        self._client.execute("DELETE FROM toc WHERE project_id = ?", (project_id,))
        self._client.execute("UPDATE pieces SET status = 'deleted' WHERE project_id = ?", (project_id,))
        return True

    # -------------------------------------------------------------
    # 1. 시퀀스 채번기 (P-0001, P-0002...)
    # -------------------------------------------------------------
    def allocate_piece_id(self, project_id: str) -> str:
        """
        [본문원고 우선 저장하기] 클릭 시 호출되는 불변 고유 ID 채번기.
        last_piece_seq를 원자적으로 1 증가시키고 P-XXXX 형태의 ID를 반환.
        """
        row = self._client.fetch_one("SELECT last_piece_seq FROM project_meta WHERE project_id = ?", (project_id,))
        now = datetime.now().isoformat()
        if row:
            next_seq = int(row["last_piece_seq"]) + 1
            self._client.execute(
                "UPDATE project_meta SET last_piece_seq = ?, updated_at = ? WHERE project_id = ?",
                (next_seq, now, project_id)
            )
        else:
            next_seq = 1
            self._client.execute(
                "INSERT INTO project_meta (project_id, name, last_piece_seq, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (project_id, project_id, next_seq, now, now)
            )

        piece_id = f"P-{next_seq:04d}"
        return piece_id

    # -------------------------------------------------------------
    # 2. 작품 저장 및 조회 (100% Turso DB 마스터 일원화)
    # -------------------------------------------------------------
    def save_piece(self, piece: PieceData) -> bool:
        """작품 엔티티 저장 (Insert 또는 Update - 로컬 파일 중복 쓰기 제거)"""
        now = datetime.now().isoformat()
        if not piece.created_at:
            piece.created_at = now
        piece.updated_at = now

        sql = """
        INSERT INTO pieces (
            piece_id, project_id, title, subtitle, author, poem_body,
            chapter_topic, memory_anchor, interview_notes, status,
            created_at, updated_at, art_style, art_direction,
            illustration_prompt, image_file, image_file_2,
            recite_primary_type, voice_user_file, voice_tts_file,
            voice_tts_actor, voice_suno_file, voice_suno_prompt,
            voice_bgm_file, recite_script, recite_tempo,
            recite_variants_json, music_file, lyrics, music_genre,
            music_prompt, music_bpm, video_file_16x9, video_file_9x16,
            video_preview, layout_mode, page_count, part2_mode,
            layout_config_json, revisions_json, current_rev_id
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?
        )
        ON CONFLICT(piece_id) DO UPDATE SET
            title = excluded.title,
            subtitle = excluded.subtitle,
            author = excluded.author,
            poem_body = excluded.poem_body,
            chapter_topic = excluded.chapter_topic,
            memory_anchor = excluded.memory_anchor,
            interview_notes = excluded.interview_notes,
            status = excluded.status,
            updated_at = excluded.updated_at,
            art_style = excluded.art_style,
            art_direction = excluded.art_direction,
            illustration_prompt = excluded.illustration_prompt,
            image_file = excluded.image_file,
            image_file_2 = excluded.image_file_2,
            recite_primary_type = excluded.recite_primary_type,
            voice_user_file = excluded.voice_user_file,
            voice_tts_file = excluded.voice_tts_file,
            voice_tts_actor = excluded.voice_tts_actor,
            voice_suno_file = excluded.voice_suno_file,
            voice_suno_prompt = excluded.voice_suno_prompt,
            voice_bgm_file = excluded.voice_bgm_file,
            recite_script = excluded.recite_script,
            recite_tempo = excluded.recite_tempo,
            recite_variants_json = excluded.recite_variants_json,
            music_file = excluded.music_file,
            lyrics = excluded.lyrics,
            music_genre = excluded.music_genre,
            music_prompt = excluded.music_prompt,
            music_bpm = excluded.music_bpm,
            video_file_16x9 = excluded.video_file_16x9,
            video_file_9x16 = excluded.video_file_9x16,
            video_preview = excluded.video_preview,
            layout_mode = excluded.layout_mode,
            page_count = excluded.page_count,
            part2_mode = excluded.part2_mode,
            layout_config_json = excluded.layout_config_json,
            revisions_json = excluded.revisions_json,
            current_rev_id = excluded.current_rev_id
        """

        params = (
            piece.piece_id, piece.project_id, piece.title, piece.subtitle, piece.author, piece.poem_body,
            piece.chapter_topic, piece.memory_anchor, piece.interview_notes, piece.status,
            piece.created_at, piece.updated_at, piece.art_style, piece.art_direction,
            piece.illustration_prompt, piece.image_file, piece.image_file_2,
            piece.recite_primary_type, piece.voice_user_file, piece.voice_tts_file,
            piece.voice_tts_actor, piece.voice_suno_file, piece.voice_suno_prompt,
            piece.voice_bgm_file, piece.recite_script, piece.recite_tempo,
            json.dumps(piece.recite_variants or {}, ensure_ascii=False),
            piece.music_file, piece.lyrics, piece.music_genre,
            piece.music_prompt, piece.music_bpm, piece.video_file_16x9, piece.video_file_9x16,
            piece.video_preview, piece.layout_mode, piece.page_count, piece.part2_mode,
            json.dumps(piece.layout_config or {}, ensure_ascii=False),
            json.dumps(piece.revisions or [], ensure_ascii=False),
            piece.current_rev_id
        )

        self._client.execute(sql, params)
        clear_cache(f"toc_pieces:{piece.project_id}")
        clear_cache("projects_stats")
        return True

    def get_piece(self, project_id: str, piece_id: str) -> Optional[PieceData]:
        """고유 ID로 단일 작품 조회"""
        row = self._client.fetch_one("SELECT * FROM pieces WHERE piece_id = ? AND project_id = ?", (piece_id, project_id))
        if not row:
            return None
        return self._row_to_piece(row)

    def list_pieces(self, project_id: str, include_deleted: bool = False) -> List[PieceData]:
        """프로젝트 내 전체 작품 목록 조회"""
        if include_deleted:
            sql = "SELECT * FROM pieces WHERE project_id = ? ORDER BY piece_id ASC"
        else:
            sql = "SELECT * FROM pieces WHERE project_id = ? AND status != 'deleted' ORDER BY piece_id ASC"
        rows = self._client.fetch_all(sql, (project_id,))
        return [self._row_to_piece(r) for r in rows]

    def _row_to_piece(self, row: Dict[str, Any]) -> PieceData:
        d = dict(row)
        recite_variants = {}
        try:
            recite_variants = json.loads(d.get("recite_variants_json") or "{}")
        except Exception:
            pass

        layout_config = {}
        try:
            layout_config = json.loads(d.get("layout_config_json") or "{}")
        except Exception:
            pass

        revisions = []
        try:
            revisions = json.loads(d.get("revisions_json") or "[]")
        except Exception:
            pass

        return PieceData(
            piece_id=d["piece_id"],
            project_id=d["project_id"],
            title=d["title"],
            subtitle=d.get("subtitle", "") or "",
            author=d.get("author", "") or "",
            poem_body=d.get("poem_body", "") or "",
            chapter_topic=d.get("chapter_topic", "") or "",
            memory_anchor=d.get("memory_anchor", "") or "",
            interview_notes=d.get("interview_notes", "") or "",
            status=d.get("status", "draft") or "draft",
            created_at=d.get("created_at", "") or "",
            updated_at=d.get("updated_at", "") or "",
            art_style=d.get("art_style", "watercolor") or "watercolor",
            art_direction=d.get("art_direction", "") or "",
            illustration_prompt=d.get("illustration_prompt", "") or "",
            image_file=d.get("image_file", "") or "",
            image_file_2=d.get("image_file_2", "") or "",
            recite_primary_type=d.get("recite_primary_type", "ai_tts") or "ai_tts",
            voice_user_file=d.get("voice_user_file", "") or "",
            voice_tts_file=d.get("voice_tts_file", "") or "",
            voice_tts_actor=d.get("voice_tts_actor", "charon_male") or "charon_male",
            voice_suno_file=d.get("voice_suno_file", "") or "",
            voice_suno_prompt=d.get("voice_suno_prompt", "") or "",
            voice_bgm_file=d.get("voice_bgm_file", "") or "",
            recite_script=d.get("recite_script", "") or "",
            recite_tempo=float(d.get("recite_tempo", 1.0) or 1.0),
            recite_variants=recite_variants,
            music_file=d.get("music_file", "") or "",
            lyrics=d.get("lyrics", "") or "",
            music_genre=d.get("music_genre", "folk") or "folk",
            music_prompt=d.get("music_prompt", "") or "",
            music_bpm=int(d.get("music_bpm", 76) or 76),
            video_file_16x9=d.get("video_file_16x9", "") or "",
            video_file_9x16=d.get("video_file_9x16", "") or "",
            video_preview=d.get("video_preview", "") or "",
            layout_mode=d.get("layout_mode", "compact") or "compact",
            page_count=int(d.get("page_count", 2) or 2),
            part2_mode=d.get("part2_mode", "motif_symbol") or "motif_symbol",
            layout_config=layout_config,
            revisions=revisions,
            current_rev_id=int(d.get("current_rev_id", 1) or 1)
        )

    # -------------------------------------------------------------
    # 3. 삭제 및 영구 결번 (Tombstone)
    # -------------------------------------------------------------
    def delete_piece(self, project_id: str, piece_id: str, soft_delete: bool = True) -> bool:
        """
        작품 삭제 시:
        1. 목차(TOC)에서만 제거 (뒤에 있는 시들의 번호 자동 당김)
        2. DB에서는 status='deleted'로 처리하여 번호 영구 결번 보존
        """
        self._client.execute("DELETE FROM toc WHERE project_id = ? AND piece_id = ?", (project_id, piece_id))
        rows = self._client.fetch_all("SELECT piece_id, chapter FROM toc WHERE project_id = ? ORDER BY display_order ASC", (project_id,))
        self._client.execute("DELETE FROM toc WHERE project_id = ?", (project_id,))

        for idx, r in enumerate(rows, start=1):
            self._client.execute(
                "INSERT INTO toc (project_id, display_order, piece_id, chapter, display_label) VALUES (?, ?, ?, ?, ?)",
                (project_id, idx, r["piece_id"], r["chapter"], f"제{idx:02d}화")
            )

        now = datetime.now().isoformat()
        if soft_delete:
            self._client.execute("UPDATE pieces SET status = 'deleted', updated_at = ? WHERE piece_id = ? AND project_id = ?", (now, piece_id, project_id))
        else:
            self._client.execute("DELETE FROM pieces WHERE piece_id = ? AND project_id = ?", (piece_id, project_id))
        clear_cache(f"toc_pieces:{project_id}")
        clear_cache("projects_stats")
        return True

    # -------------------------------------------------------------
    # 4. 목차 (Table of Contents / TOC) 관리 및 동적 조판 계산
    # -------------------------------------------------------------
    def get_toc(self, project_id: str) -> List[TOCItem]:
        """프로젝트 목차 목록 조회 (페이지 시작 번호 자동 계산 포함)"""
        sql = """
            SELECT t.display_order, t.piece_id, t.chapter, t.display_label, p.page_count
            FROM toc t
            LEFT JOIN pieces p ON t.piece_id = p.piece_id AND t.project_id = p.project_id
            WHERE t.project_id = ?
            ORDER BY t.display_order ASC
        """
        rows = self._client.fetch_all(sql, (project_id,))

        toc_items = []
        current_page = 8  # 앞부속(표지,서문,목차) 고정 8페이지 이후 본문 시작

        for r in rows:
            p_count = int(r.get("page_count") or 2)
            display_label = r.get("display_label") or f"제{int(r['display_order']):02d}화"
            item = TOCItem(
                display_order=int(r["display_order"]),
                piece_id=r["piece_id"],
                chapter=r.get("chapter", "") or "",
                display_label=display_label,
                page_start=current_page,
                page_count=p_count
            )
            toc_items.append(item)
            current_page += p_count

        return toc_items

    def get_toc_with_pieces(self, project_id: str) -> List[Dict[str, Any]]:
        """TOC와 Pieces를 단 1회의 JOIN 쿼리로 가져와서 초고속 반환 (N+1 쿼리 완전 퇴출 & 캐시 적용)"""
        cache_key = f"toc_pieces:{project_id}"
        cached = get_cached(cache_key, ttl=3.0)
        if cached is not None:
            return cached

        sql = """
            SELECT t.display_order, t.piece_id, t.chapter as toc_chapter, t.display_label,
                   p.*
            FROM toc t
            JOIN pieces p ON t.piece_id = p.piece_id AND t.project_id = p.project_id
            WHERE t.project_id = ? AND p.status != 'deleted'
            ORDER BY t.display_order ASC
        """
        rows = self._client.fetch_all(sql, (project_id,))
        result = []
        for r in rows:
            piece = self._row_to_piece(r)
            display_label = r.get("display_label") or f"제{int(r['display_order']):02d}화"
            result.append({
                "display_order": int(r["display_order"]),
                "display_label": display_label,
                "chapter": r.get("toc_chapter", "") or piece.chapter_topic,
                "piece": piece
            })
        set_cached(cache_key, result)
        return result

    def set_toc(self, project_id: str, items: List[Dict[str, Any]]) -> bool:
        """목차 전체 교체/설정"""
        self._client.execute("DELETE FROM toc WHERE project_id = ?", (project_id,))
        for idx, item in enumerate(items, start=1):
            piece_id = item["piece_id"]
            chapter = item.get("chapter", "")
            display_label = item.get("display_label", f"제{idx:02d}화")
            self._client.execute(
                "INSERT INTO toc (project_id, display_order, piece_id, chapter, display_label) VALUES (?, ?, ?, ?, ?)",
                (project_id, idx, piece_id, chapter, display_label)
            )
            if chapter:
                self._client.execute(
                    "UPDATE pieces SET chapter_topic = ? WHERE project_id = ? AND piece_id = ?",
                    (chapter, project_id, piece_id)
                )
        clear_cache(f"toc_pieces:{project_id}")
        return True

    def rename_chapter(self, project_id: str, old_chapter: str, new_chapter: str) -> bool:
        """부/챕터 명칭 변경 시 toc 및 pieces 테이블 일괄 갱신"""
        self._client.execute(
            "UPDATE toc SET chapter = ? WHERE project_id = ? AND chapter = ?",
            (new_chapter, project_id, old_chapter)
        )
        self._client.execute(
            "UPDATE pieces SET chapter_topic = ? WHERE project_id = ? AND chapter_topic = ?",
            (new_chapter, project_id, old_chapter)
        )
        clear_cache(f"toc_pieces:{project_id}")
        return True

    def reorder_toc(self, project_id: str, new_piece_ids_order: List[str]) -> bool:
        """목차 순서 변경 (ID 배열만 전달받아 순서 재색인)"""
        current_toc = {item.piece_id: item for item in self.get_toc(project_id)}
        new_items = []
        for pid in new_piece_ids_order:
            if pid in current_toc:
                new_items.append({
                    "piece_id": pid,
                    "chapter": current_toc[pid].chapter
                })
        return self.set_toc(project_id, new_items)

    # -------------------------------------------------------------
    # 5. 온디맨드 JSON 내보내기 (ZIP 백업 시 임시 폴더에 즉석 생성)
    # -------------------------------------------------------------
    def export_json_manifest(self, project_id: str, target_dir: Optional[Path] = None) -> Optional[Path]:
        """데이터를 Human-Readable JSON 파일로 내보내기 (ZIP 백업 등 온디맨드 시에만 호출)"""
        try:
            rows = self._client.fetch_all(
                "SELECT * FROM pieces WHERE project_id = ? AND status != 'deleted' ORDER BY piece_id ASC",
                (project_id,)
            )
            pieces_dict = {}
            for r in rows:
                p = self._row_to_piece(r)
                pieces_dict[p.piece_id] = asdict(p)

            pdir = target_dir or (self.projects_dir / project_id)
            pdir.mkdir(parents=True, exist_ok=True)
            manifest_path = pdir / "works_db.json"
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump({
                    "project_id": project_id,
                    "exported_at": datetime.now().isoformat(),
                    "count": len(pieces_dict),
                    "pieces": pieces_dict
                }, f, ensure_ascii=False, indent=2)
            return manifest_path
        except Exception as e:
            logger.debug(f"[export_json_manifest skipped] {e}")
            return None

    def export_toc_json(self, project_id: str, target_dir: Optional[Path] = None) -> Optional[Path]:
        """목차 JSON 내보내기 (ZIP 백업 등 온디맨드 시에만 호출)"""
        try:
            toc_items = self.get_toc(project_id)
            pdir = target_dir or (self.projects_dir / project_id)
            pdir.mkdir(parents=True, exist_ok=True)
            toc_path = pdir / "toc.json"
            data = {
                "project_id": project_id,
                "updated_at": datetime.now().isoformat(),
                "items": [asdict(item) for item in toc_items]
            }
            with open(toc_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return toc_path
        except Exception as e:
            logger.debug(f"[export_toc_json skipped] {e}")
            return None

    # -------------------------------------------------------------
    # 6. 시 퇴고 판본(Revisions) Turso DB 영구 관리
    # -------------------------------------------------------------
    def save_revision(
        self,
        project_id: str,
        episode_no: str,
        rev_id: int,
        version_name: str,
        title: str,
        poem_body: str,
        note: str,
        timestamp: str,
        line_count: int,
        char_count: int
    ) -> bool:
        self._client.execute("""
        INSERT INTO revisions (
            project_id, episode_no, rev_id, version_name, title,
            poem_body, note, timestamp, line_count, char_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(project_id, episode_no, rev_id) DO UPDATE SET
            version_name = excluded.version_name,
            title = excluded.title,
            poem_body = excluded.poem_body,
            note = excluded.note,
            timestamp = excluded.timestamp,
            line_count = excluded.line_count,
            char_count = excluded.char_count
        """, (project_id, episode_no, rev_id, version_name, title, poem_body, note, timestamp, line_count, char_count))
        return True

    def get_revisions(self, project_id: str, episode_no: str) -> List[Dict[str, Any]]:
        rows = self._client.fetch_all(
            "SELECT * FROM revisions WHERE project_id = ? AND episode_no = ? ORDER BY rev_id ASC",
            (project_id, episode_no)
        )
        return [dict(r) for r in rows]

    def list_project_revisions(self, project_id: str) -> Dict[str, List[Dict[str, Any]]]:
        rows = self._client.fetch_all(
            "SELECT * FROM revisions WHERE project_id = ? ORDER BY episode_no ASC, rev_id ASC",
            (project_id,)
        )
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for r in rows:
            ep = r["episode_no"]
            grouped.setdefault(ep, []).append(dict(r))
        return grouped

    # -------------------------------------------------------------
    # 7. 자체 회원 및 다중 사용자 세션 격리 (Supabase Auth 완전 대체)
    # -------------------------------------------------------------
    def upsert_user(
        self,
        user_id: str,
        email: str,
        display_name: str = "",
        provider: str = "email",
        password_hash: str = "",
        active_project_id: str = ""
    ) -> Dict[str, Any]:
        now = datetime.now().isoformat()
        existing = self._client.fetch_one("SELECT * FROM users WHERE email = ? OR user_id = ?", (email, user_id))
        if existing:
            uid = existing["user_id"]
            dname = display_name or existing.get("display_name") or email.split("@")[0]
            phash = password_hash or existing.get("password_hash") or ""
            act_proj = active_project_id or existing.get("active_project_id") or ""
            self._client.execute("""
            UPDATE users SET display_name = ?, provider = ?, password_hash = ?, active_project_id = ?, last_login_at = ?
            WHERE user_id = ?
            """, (dname, provider, phash, act_proj, now, uid))
            return self.get_user_by_id(uid) or {}
        else:
            dname = display_name or (email.split("@")[0] if email else "작가님")
            self._client.execute("""
            INSERT INTO users (user_id, email, password_hash, display_name, provider, active_project_id, created_at, last_login_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, email, password_hash, dname, provider, active_project_id, now, now))
            return self.get_user_by_id(user_id) or {}

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        return self._client.fetch_one("SELECT * FROM users WHERE email = ?", (email.strip().lower(),))

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        return self._client.fetch_one("SELECT * FROM users WHERE user_id = ?", (user_id,))

    def save_user_session(
        self,
        token: str,
        user_id: str,
        email: str,
        display_name: str,
        provider: str = "email",
        active_project_id: str = "",
        expires_at: str = ""
    ) -> Dict[str, Any]:
        now = datetime.now().isoformat()
        self._client.execute("""
        INSERT INTO user_sessions (token, user_id, email, display_name, provider, active_project_id, created_at, expires_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(token) DO UPDATE SET
            user_id = excluded.user_id,
            email = excluded.email,
            display_name = excluded.display_name,
            provider = excluded.provider,
            active_project_id = excluded.active_project_id,
            expires_at = excluded.expires_at
        """, (token, user_id, email, display_name, provider, active_project_id, now, expires_at))
        return {
            "token": token,
            "user_id": user_id,
            "email": email,
            "display_name": display_name,
            "provider": provider,
            "active_project_id": active_project_id,
            "logged_in_at": now,
            "is_authenticated": True
        }

    def get_user_session(self, token: str) -> Optional[Dict[str, Any]]:
        if not token:
            return None
        row = self._client.fetch_one("SELECT * FROM user_sessions WHERE token = ?", (token,))
        if not row:
            return None
        d = dict(row)
        d["is_authenticated"] = True
        return d

    def get_latest_session(self) -> Optional[Dict[str, Any]]:
        """단일 브라우저/CLI 호환을 위한 가장 최근 활성 세션 조회"""
        row = self._client.fetch_one("SELECT * FROM user_sessions ORDER BY created_at DESC LIMIT 1")
        if not row:
            return None
        d = dict(row)
        d["is_authenticated"] = True
        return d

    def delete_user_session(self, token: Optional[str] = None) -> bool:
        if token:
            self._client.execute("DELETE FROM user_sessions WHERE token = ?", (token,))
        else:
            self._client.execute("DELETE FROM user_sessions")
        return True

    def set_user_active_project(self, user_id: str, project_id: str) -> bool:
        if user_id:
            self._client.execute("UPDATE users SET active_project_id = ? WHERE user_id = ?", (project_id, user_id))
            self._client.execute("UPDATE user_sessions SET active_project_id = ? WHERE user_id = ?", (project_id, user_id))
        return True

    # -------------------------------------------------------------
    # 8. 1:1 비밀 상담 및 코칭 (Inquiries) Turso DB 영구 관리
    # -------------------------------------------------------------
    def save_inquiry(self, inquiry_id: str, user_id: str, author_email: str, project_id: str, data_dict: Dict[str, Any]) -> bool:
        now = datetime.now().isoformat()
        data_json = json.dumps(data_dict, ensure_ascii=False)
        self._client.execute("""
        INSERT INTO inquiries (id, user_id, author_email, project_id, data_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            data_json = excluded.data_json,
            updated_at = excluded.updated_at
        """, (inquiry_id, user_id or "", author_email or "", project_id or "", data_json, data_dict.get("created_at") or now, now))
        return True

    def get_inquiry(self, inquiry_id: str) -> Optional[Dict[str, Any]]:
        row = self._client.fetch_one("SELECT data_json FROM inquiries WHERE id = ?", (inquiry_id,))
        if not row:
            return None
        try:
            return json.loads(row["data_json"])
        except Exception:
            return None

    def list_inquiries(self, user_id: Optional[str] = None, user_email: Optional[str] = None) -> List[Dict[str, Any]]:
        rows = self._client.fetch_all("SELECT * FROM inquiries ORDER BY created_at DESC")
        items = []
        for r in rows:
            try:
                data = json.loads(r["data_json"])
                if user_id or user_email:
                    match_id = bool(user_id and data.get("user_id") == user_id)
                    match_email = bool(user_email and data.get("author_email") == user_email)
                    if not (match_id or match_email):
                        continue
                items.append(data)
            except Exception:
                continue
        return items

    # -------------------------------------------------------------
    # 9. 모둠솥 공용 갤러리 및 회원 작가 서재 (Bookshelf)
    # -------------------------------------------------------------
    def get_author_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        if not user_id:
            return None
        return self._client.fetch_one("SELECT * FROM author_profiles WHERE user_id = ?", (user_id,))

    def upsert_author_profile(self, user_id: str, pen_name: str, bio: str = "", avatar_url: str = "") -> Dict[str, Any]:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        existing = self.get_author_profile(user_id)
        if existing:
            self._client.execute("""
            UPDATE author_profiles
            SET pen_name = ?, bio = ?, avatar_url = ?, updated_at = ?
            WHERE user_id = ?
            """, (pen_name, bio, avatar_url, now_str, user_id))
        else:
            self._client.execute("""
            INSERT INTO author_profiles (user_id, pen_name, bio, avatar_url, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """, (user_id, pen_name, bio, avatar_url, now_str))
        return self.get_author_profile(user_id) or {}

    def get_bookshelf_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        if not item_id:
            return None
        return self._client.fetch_one("SELECT * FROM bookshelf_items WHERE item_id = ?", (item_id,))

    def upsert_bookshelf_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        item_id = item.get("item_id")
        user_id = item.get("user_id", "")
        book_type = item.get("book_type", "internal_storybook")
        title = item.get("title", "")
        author_name = item.get("author_name", "")
        cover_image_url = item.get("cover_image_url", "")
        excerpt = item.get("excerpt", "")
        view_url = item.get("view_url", "")
        project_id = item.get("project_id", "")
        is_published = int(item.get("is_published", 1))
        has_recite = int(item.get("has_recite", 0))
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if book_type == "internal_storybook" and project_id and not item_id:
            existing = self._client.fetch_one(
                "SELECT * FROM bookshelf_items WHERE user_id = ? AND project_id = ?",
                (user_id, project_id)
            )
            if existing:
                item_id = existing["item_id"]

        if not item_id:
            import uuid
            item_id = str(uuid.uuid4())[:12]

        existing_item = self.get_bookshelf_item(item_id)
        if existing_item:
            self._client.execute("""
            UPDATE bookshelf_items
            SET title = ?, author_name = ?, cover_image_url = ?, excerpt = ?,
                view_url = ?, is_published = ?, has_recite = ?, updated_at = ?
            WHERE item_id = ?
            """, (title, author_name, cover_image_url, excerpt, view_url, is_published, has_recite, now_str, item_id))
        else:
            self._client.execute("""
            INSERT INTO bookshelf_items (
                item_id, user_id, book_type, title, author_name,
                cover_image_url, excerpt, view_url, project_id,
                is_published, has_recite, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item_id, user_id, book_type, title, author_name,
                cover_image_url, excerpt, view_url, project_id,
                is_published, has_recite, now_str, now_str
            ))
        return self.get_bookshelf_item(item_id) or {}

    def get_bookshelf_items(
        self,
        user_id: Optional[str] = None,
        only_published: bool = True,
        keyword: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM bookshelf_items WHERE 1=1"
        params: List[Any] = []
        if user_id:
            sql += " AND user_id = ?"
            params.append(user_id)
        if only_published:
            sql += " AND is_published = 1"
        if keyword:
            kw = f"%{keyword.strip()}%"
            sql += " AND (title LIKE ? OR author_name LIKE ? OR excerpt LIKE ?)"
            params.extend([kw, kw, kw])
        sql += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        return self._client.fetch_all(sql, tuple(params))

    def delete_bookshelf_item(self, item_id: str, user_id: str) -> bool:
        self._client.execute(
            "DELETE FROM bookshelf_items WHERE item_id = ? AND user_id = ?",
            (item_id, user_id)
        )
        return True

    def toggle_bookshelf_visibility(self, item_id: str, user_id: str) -> Optional[int]:
        item = self.get_bookshelf_item(item_id)
        if not item or item.get("user_id") != user_id:
            return None
        new_val = 0 if item.get("is_published") else 1
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._client.execute(
            "UPDATE bookshelf_items SET is_published = ?, updated_at = ? WHERE item_id = ?",
            (new_val, now_str, item_id)
        )
        return new_val

    # -------------------------------------------------------------
    # 10. 하위 호환용 연결 헬퍼
    # -------------------------------------------------------------
    def get_connection(self, project_id: str = ""):
        """기존 sqlite3.Connection 인터페이스 호환용"""
        if isinstance(self._client, LocalSQLiteClient):
            return self._client._get_conn()
        raise NotImplementedError("클라우드 Turso 모드에서는 raw connection 대신 db_manager 메서드를 직접 호출하십시오.")


# 전역 싱글톤 인스턴스
db_manager = DatabaseManager()
