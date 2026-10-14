"""
core/revision_manager.py
시인의 집필실: 퇴고 판본(Revision) 관리 및 판본 간 비교(Diff) 지원 모듈
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any
import difflib


def _get_revisions_file(project_dir: Path, episode_no: str) -> Path:
    rev_dir = project_dir / "revisions"
    rev_dir.mkdir(parents=True, exist_ok=True)
    safe_ep = episode_no.replace(" ", "_").replace("/", "_")
    return rev_dir / f"{safe_ep}.json"


def save_revision_snapshot(
    project_dir: Path,
    episode_no: str,
    title: str,
    poem_body: str,
    note: str = ""
) -> Dict[str, Any]:
    """
    현재 시의 제목과 본문을 판본(Revision) 스냅샷으로 저장합니다.
    이전 최신 판본과 본문이 완전히 동일하면 중복 생성하지 않고 최신 정보를 반환합니다.
    """
    rev_file = _get_revisions_file(project_dir, episode_no)
    
    revisions: List[Dict[str, Any]] = []
    if rev_file.exists():
        try:
            with open(rev_file, "r", encoding="utf-8") as f:
                revisions = json.load(f)
        except Exception:
            revisions = []

    # 이전 판본과 본문이 동일한지 체크
    if revisions:
        latest = revisions[-1]
        if latest.get("poem_body", "").strip() == poem_body.strip() and latest.get("title", "").strip() == title.strip():
            return {
                "created": False,
                "message": "내용 변경이 없어 기존 판본을 유지합니다.",
                "revision_count": len(revisions),
                "revisions": revisions
            }

    rev_id = len(revisions) + 1
    version_name = "초고 (初稿)" if rev_id == 1 else f"{rev_id}고 (改作 {rev_id-1}차)"

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_rev = {
        "rev_id": rev_id,
        "version_name": version_name,
        "title": title,
        "poem_body": poem_body,
        "note": note,
        "timestamp": now_str,
        "line_count": len([ln for ln in poem_body.splitlines() if ln.strip()]),
        "char_count": len(poem_body)
    }

    revisions.append(new_rev)

    with open(rev_file, "w", encoding="utf-8") as f:
        json.dump(revisions, f, ensure_ascii=False, indent=2)

    return {
        "created": True,
        "message": f"[{version_name}] 판본이 안전하게 보관되었습니다.",
        "new_revision": new_rev,
        "revision_count": len(revisions),
        "revisions": revisions
    }


def get_revisions(project_dir: Path, episode_no: str) -> List[Dict[str, Any]]:
    """해당 회차의 모든 판본 목록을 반환합니다."""
    rev_file = _get_revisions_file(project_dir, episode_no)
    if not rev_file.exists():
        return []
    try:
        with open(rev_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
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
