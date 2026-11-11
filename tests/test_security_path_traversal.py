"""경로 탈출(Path Traversal) 방어 회귀 테스트 (임시 폴더만 사용, 실제 프로젝트 데이터 무변경)"""
import pytest
from fastapi import HTTPException

import core.project_manager as pm
from core.project_manager import ProjectManager

BAD_IDS = ["../victim", "..\\victim", "..", ".", "C:/Windows", "a/../../victim", "a/b", "x:y"]


@pytest.fixture
def mgr(tmp_path, monkeypatch):
    monkeypatch.setattr(pm, "ACTIVE_PROJECT_FILE", tmp_path / ".active")
    (tmp_path / "projects" / "a").mkdir(parents=True)
    (tmp_path / "projects" / "b").mkdir()
    (tmp_path / "victim").mkdir()
    (tmp_path / "victim" / "f.txt").write_text("x")
    return ProjectManager(tmp_path / "projects")


@pytest.mark.parametrize("bad", BAD_IDS)
def test_delete_project_rejects_traversal(mgr, bad, tmp_path):
    with pytest.raises(ValueError):
        mgr.delete_project(bad)
    assert (tmp_path / "victim" / "f.txt").exists()
    assert (tmp_path / "projects" / "a").exists()


@pytest.mark.parametrize("bad", BAD_IDS)
def test_set_active_and_get_dir_reject_traversal(mgr, bad):
    with pytest.raises(ValueError):
        mgr.set_active_project_id(bad)
    with pytest.raises(ValueError):
        mgr.get_project_dir(bad)


def test_delete_project_normal_still_works(mgr, tmp_path):
    p_b = mgr.create_project(name="테스트_삭제용_시집", subtitle="테스트 부제", author="테스트 작가", description="정상 삭제 검증")
    assert mgr.delete_project(p_b.id) is True


def _run(coro):
    """샌드박스 소켓 제한과 무관하게 async 라우트를 동기 호출"""
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value


FILE_BAD = [
    "C:/Windows/win.ini", "C:\\Windows\\win.ini", "/C:/Windows/win.ini",
    "../../.env", "..\\..\\.env", "....//....//.env", "../../core/config.py",
]


@pytest.mark.parametrize("bad", FILE_BAD)
def test_file_serving_rejects_escape(bad):
    from web.routers import projects as pr
    from fastapi.responses import RedirectResponse
    for fn in (pr.serve_image, pr.serve_audio):
        res = None
        try:
            res = _run(fn(bad))
        except HTTPException as ei:
            assert ei.status_code == 404
            continue
        # R2 클라우드 모드일 경우: 상위 디렉터리 탈출 없이 파일명만 안전하게 R2 키로 격리되어 리다이렉트됨
        assert isinstance(res, RedirectResponse)
        assert "../" not in res.headers["location"]
        assert ".." not in res.headers["location"]
        assert "C:" not in res.headers["location"]
        assert "Windows" not in res.headers["location"]


def test_safe_child_allows_inside_only(tmp_path):
    from web.routers.projects import _safe_child
    (tmp_path / "sub").mkdir()
    f = tmp_path / "sub" / "ok.txt"
    f.write_text("1")
    assert _safe_child(tmp_path, "sub/ok.txt") == f.resolve()
    assert _safe_child(tmp_path, "../ok.txt") is None
    assert _safe_child(tmp_path, "C:/Windows/win.ini") is None
    assert _safe_child(tmp_path, "") is None

