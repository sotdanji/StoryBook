"""
tests/test_gallery_export.py
시화집 웹 배포용 온라인 갤러리 ZIP 패키징 기능 테스트
"""

import tempfile
import zipfile
from pathlib import Path
import pytest

from core.project_manager import ProjectManager


def test_export_gallery_web_zip():
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        mgr = ProjectManager(projects_dir=base_dir)

        proj = mgr.create_project(
            name="테스트_시화집",
            subtitle="기억의 노래",
            author="홍길동",
            description="온라인 갤러리 테스트"
        )

        pdir = mgr._safe_project_dir(proj.id)

        # 갤러리 HTML 파일 수동 생성 (테스트용)
        gallery_file = pdir / "시화집_갤러리.html"
        gallery_file.write_text("<!DOCTYPE html><html><body><h1>테스트 갤러리</h1></body></html>", encoding="utf-8")

        # 더미 미디어 파일 추가
        img_dir = pdir / "images"
        music_dir = pdir / "music"
        img_dir.mkdir(parents=True, exist_ok=True)
        music_dir.mkdir(parents=True, exist_ok=True)

        (img_dir / "01_test.png").write_text("dummy image", encoding="utf-8")
        (music_dir / "01_test.mp3").write_text("dummy music", encoding="utf-8")

        zip_path = mgr.export_gallery_web_zip(proj.id)

        assert zip_path.exists()
        assert zip_path.name == f"{proj.id}_web_gallery.zip"

        # ZIP 내용 검증
        with zipfile.ZipFile(zip_path, "r") as zf:
            namelist = zf.namelist()
            assert "index.html" in namelist
            assert "배포가이드_클릭하여열기.html" in namelist
            assert "README_웹배포_안내.txt" in namelist

            guide_content = zf.read("배포가이드_클릭하여열기.html").decode("utf-8")
            assert "Netlify Drop" in guide_content
            assert "GitHub Pages" in guide_content

            txt_content = zf.read("README_웹배포_안내.txt").decode("utf-8")
            assert "app.netlify.com/drop" in txt_content
