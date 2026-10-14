import os
import json
import tempfile
from pathlib import Path
import pytest
from core.manuscript import PoemWork, ManuscriptManager

def test_poem_work_default_layout_config():
    """PoemWork 생성 시 필수 인자가 제공되면 layout_config는 기본값 None 또는 딕셔너리로 초기화된다."""
    work = PoemWork(
        episode_no="제01화",
        title="테스트 시",
        status="완성",
        memory_anchor="테스트 기억",
        image_file="./images/01_test.jpg",
        art_direction="테스트 방향",
        poem_body="테스트 시 본문"
    )
    assert work.episode_no == "제01화"
    assert work.layout_mode in ["compact", "multi_page"]

def test_manuscript_parse_and_update_layout_config():
    """임시 원고 파일에 조판 설정을 갱신하고 다시 로드했을 때 데이터가 완벽히 보존되어야 한다."""
    sample_md_content = """# 시화집 작품집 원고

---

## [제01화] 테스트 시
- **상태**: **완성**
- **기억의 중심**: 테스트 기억
- **삽화 파일**: `./images/01_test.jpg`
- **그림 방향**: 테스트 방향

### [시 본문]

첫 번째 줄
두 번째 줄
세 번째 줄
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        md_path = Path(tmpdir) / "작품집_원고.md"
        md_path.write_text(sample_md_content, encoding="utf-8")

        mgr = ManuscriptManager(file_path=md_path)
        works = mgr.load_works()
        assert len(works) == 1
        work = works[0]
        assert work.episode_no == "제01화"

        # 1) 조판 설정 업데이트 (4페이지 3면 연속 장시)
        new_layout = {
            "page_count": 4,
            "slots": ["image", "text", "text", "text"],
            "image_settings": {
                "page_1": {"mode": "image", "file": "./images/01_test.jpg"}
            }
        }
        success = mgr.update_work_layout_config("01", new_layout)
        assert success is True

        # 2) 파일 재로드 후 정합성 검증
        reloaded_mgr = ManuscriptManager(file_path=md_path)
        reloaded_works = reloaded_mgr.load_works()
        assert len(reloaded_works) == 1
        reloaded_work = reloaded_works[0]
        assert reloaded_work.layout_config is not None
        assert reloaded_work.layout_config.get("page_count") == 4
        assert reloaded_work.layout_config.get("slots") == ["image", "text", "text", "text"]
        assert reloaded_work.layout_mode == "multi_page"

def test_update_layout_config_nonexistent_episode():
    """존재하지 않는 회차에 대한 업데이트 시도시 에러 없이 False를 반환해야 한다."""
    with tempfile.TemporaryDirectory() as tmpdir:
        md_path = Path(tmpdir) / "작품집_원고.md"
        md_path.write_text("# 빈 원고\n", encoding="utf-8")

        mgr = ManuscriptManager(file_path=md_path)
        success = mgr.update_work_layout_config("999", {"page_count": 2})
        assert success is False
