import asyncio
import pytest
from fastapi import HTTPException
from web.routers.projects import get_status, get_projects
from web.routers.publishing import get_book_spec
from web.routers.studio_poem import save_work_layout_config_endpoint, SaveLayoutConfigRequest


def test_api_status_endpoint():
    """GET /api/status가 정상적으로 프로젝트 및 작품 목록을 반환해야 한다."""
    data = asyncio.run(get_status())
    assert "project" in data
    assert "works" in data
    assert isinstance(data["works"], list)


def test_api_book_spec_endpoint():
    """GET /api/book_spec이 정상적으로 책 규격 정보를 반환해야 한다."""
    data = asyncio.run(get_book_spec())
    assert "cover_canvas_width_mm" in data
    assert "spine_thickness_mm" in data
    assert data.get("bleed_margin_mm") == 3


def test_api_projects_endpoint():
    """GET /api/projects가 프로젝트 목록을 정상 반환해야 한다."""
    data = asyncio.run(get_projects())
    assert "projects" in data
    assert len(data["projects"]) >= 1


def test_api_save_work_layout_config_normal(monkeypatch):
    """POST /api/save_work_layout_config 정상 호출 시 200과 success: True를 반환해야 한다 (실제 데이터 변조 방지)."""
    from core.project_manager import project_manager
    mgr = project_manager.get_active_manuscript_manager()
    monkeypatch.setattr(mgr, "update_work_layout_config", lambda *args, **kwargs: True)
    req = SaveLayoutConfigRequest(
        episode_no="01",
        layout_config={
            "page_count": 4,
            "slots": ["image", "text", "text", "text"],
            "image_settings": {
                "page_1": {"mode": "image", "file": "./images/01_새벽대청.jpg"}
            }
        }
    )
    data = asyncio.run(save_work_layout_config_endpoint(req))
    assert data.get("success") is True


def test_api_save_work_layout_config_invalid_episode():
    """존재하지 않는 회차 번호 전달 시 404 에러를 반환해야 한다."""
    req = SaveLayoutConfigRequest(
        episode_no="99999",
        layout_config={"page_count": 2, "slots": ["image", "text"]}
    )
    with pytest.raises(HTTPException) as exc:
        asyncio.run(save_work_layout_config_endpoint(req))
    assert exc.value.status_code == 404
