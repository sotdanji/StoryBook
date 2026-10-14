import pytest
from fastapi.testclient import TestClient
from web.app import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_api_status_endpoint(client):
    """GET /api/status가 정상적으로 200과 프로젝트 및 작품 목록을 반환해야 한다."""
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert "project" in data
    assert "works" in data
    assert isinstance(data["works"], list)

def test_api_book_spec_endpoint(client):
    """GET /api/book_spec이 정상적으로 책 규격 정보를 반환해야 한다."""
    response = client.get("/api/book_spec")
    assert response.status_code == 200
    data = response.json()
    assert "cover_canvas_width_mm" in data
    assert "spine_thickness_mm" in data
    assert data.get("bleed_margin_mm") == 3

def test_api_projects_endpoint(client):
    """GET /api/projects가 프로젝트 목록을 200으로 반환해야 한다."""
    response = client.get("/api/projects")
    assert response.status_code == 200
    data = response.json()
    assert "projects" in data
    assert len(data["projects"]) >= 1

def test_api_save_work_layout_config_normal(client):
    """POST /api/save_work_layout_config 정상 호출 시 200과 success: True를 반환해야 한다."""
    payload = {
        "episode_no": "01",
        "layout_config": {
            "page_count": 4,
            "slots": ["image", "text", "text", "text"],
            "image_settings": {
                "page_1": {"mode": "image", "file": "./images/01_새벽대청.jpg"}
            }
        }
    }
    response = client.post("/api/save_work_layout_config", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data.get("success") is True

def test_api_save_work_layout_config_invalid_episode(client):
    """존재하지 않는 회차 번호 전달 시 404 에러를 반환해야 한다."""
    payload = {
        "episode_no": "99999",
        "layout_config": {"page_count": 2, "slots": ["image", "text"]}
    }
    response = client.post("/api/save_work_layout_config", json=payload)
    assert response.status_code == 404

def test_api_save_work_layout_config_missing_field(client):
    """필수 필드(episode_no)가 누락되면 422 에러를 반환해야 한다."""
    payload = {
        "layout_config": {"page_count": 2}
    }
    response = client.post("/api/save_work_layout_config", json=payload)
    assert response.status_code in [400, 422]
