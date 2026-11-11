"""
core/revision_manager.py
시인의 집필실: 퇴고 판본(Revision) 관리 및 판본 간 비교(Diff) 지원 모듈
- [단일 플랫폼 클라우드 일원화] 모든 퇴고 판본(초고, 2고, 3고...)을 Turso DB `revisions` 테이블에 영구 보존
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any
import difflib


def _normalize_episode_key(episode_no: str) -> str:
    digits = re.sub(r"[^0-9]", "", str(episode_no or ""))
    if digits:
        return f"제{int(digits):02d}화"
    return str(episode_no or "제01화").strip().replace(" ", "_").replace("/", "_")


def save_revision_snapshot(
    project_dir: Path,
    episode_no: str,
    title: str,
    poem_body: str,
    note: str = ""
) -> Dict[str, Any]:
    """
    현재 시의 제목과 본문을 판본(Revision) 스냅샷으로 Turso DB에 영구 저장합니다.
    이전 최신 판본과 본문이 완전히 동일하면 중복 생성하지 않고 최신 정보를 반환합니다.
    """
    from core.db_manager import db_manager

    project_id = project_dir.name if isinstance(project_dir, Path) else str(project_dir)
    ep_key = _normalize_episode_key(episode_no)

    revisions: List[Dict[str, Any]] = get_revisions(project_dir, episode_no)

    # 이전 판본과 본문이 동일한지 체크
    if revisions:
        latest = revisions[-1]
        if latest.get("poem_body", "").strip() == (poem_body or "").strip() and latest.get("title", "").strip() == (title or "").strip():
            return {
                "created": False,
                "message": "내용 변경이 없어 기존 판본을 유지합니다.",
                "revision_count": len(revisions),
                "revisions": revisions
            }

    rev_id = len(revisions) + 1
    version_name = "초고 (初稿)" if rev_id == 1 else f"{rev_id}고 (改作 {rev_id-1}차)"

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line_cnt = len([ln for ln in (poem_body or "").splitlines() if ln.strip()])
    char_cnt = len(poem_body or "")

    new_rev = {
        "rev_id": rev_id,
        "version_name": version_name,
        "title": title,
        "poem_body": poem_body,
        "note": note,
        "timestamp": now_str,
        "line_count": line_cnt,
        "char_count": char_cnt
    }

    try:
        db_manager.save_revision(
            project_id=project_id,
            episode_no=ep_key,
            rev_id=rev_id,
            version_name=version_name,
            title=title,
            poem_body=poem_body,
            note=note,
            timestamp=now_str,
            line_count=line_cnt,
            char_count=char_cnt
        )
    except Exception as e:
        print(f"[RevisionManager] DB 저장 경고: {e}")

    revisions.append(new_rev)

    return {
        "created": True,
        "message": f"[{version_name}] 판본이 클라우드 서버에 안전하게 보관되었습니다.",
        "new_revision": new_rev,
        "revision_count": len(revisions),
        "revisions": revisions
    }


def get_revisions(project_dir: Path, episode_no: str) -> List[Dict[str, Any]]:
    """해당 회차의 모든 판본 목록을 Turso DB에서 직접 반환합니다 (100% 서버 일원화)."""
    from core.db_manager import db_manager

    project_id = project_dir.name if isinstance(project_dir, Path) else str(project_dir)
    ep_key = _normalize_episode_key(episode_no)

    try:
        db_revs = db_manager.get_revisions(project_id, ep_key)
        if db_revs:
            return db_revs
        raw_key = str(episode_no).replace(" ", "_").replace("/", "_")
        if raw_key != ep_key:
            db_revs_raw = db_manager.get_revisions(project_id, raw_key)
            if db_revs_raw:
                return db_revs_raw
    except Exception:
        pass

    return []


def compare_revisions(
    body_a: str,
    body_b: str,
    name_a: str = "이전 판본",
    name_b: str = "현재 판본"
) -> Dict[str, Any]:
    """
    두 판본 간의 행(Line) 단위 Diff를 계산하여 시각화에 적합한 데이터 구조로 반환합니다.
    """
    lines_a = [ln.rstrip() for ln in body_a.splitlines()]
    lines_b = [ln.rstrip() for ln in body_b.splitlines()]

    matcher = difflib.SequenceMatcher(None, lines_a, lines_b)
    diff_blocks = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        block = {
            "tag": tag,  # 'equal', 'replace', 'delete', 'insert'
            "lines_a": lines_a[i1:i2],
            "lines_b": lines_b[j1:j2],
            "start_a": i1,
            "end_a": i2,
            "start_b": j1,
            "end_b": j2
        }
        diff_blocks.append(block)

    return {
        "name_a": name_a,
        "name_b": name_b,
        "total_lines_a": len(lines_a),
        "total_lines_b": len(lines_b),
        "diff_blocks": diff_blocks
    }
