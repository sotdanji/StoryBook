"""
tests/test_inquiries.py
1:1 비밀 상담 및 시화집 백업 자동 첨부 코칭 기능 단위 테스트
"""

import shutil
import tempfile
from pathlib import Path
import pytest

from core.inquiry_manager import InquiryManager


@pytest.fixture
def temp_inquiry_mgr():
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        mgr = InquiryManager(base_dir=base)
        yield mgr


def test_create_and_get_inquiry(temp_inquiry_mgr):
    mgr = temp_inquiry_mgr

    item = mgr.create_inquiry(
        category="coaching",
        title="조판 여백 질문입니다",
        content="4화 삽화와 글상자 여백을 어떻게 다듬어야 할지 고민입니다.",
        author_name="김시인",
        author_email="poet@example.com",
        user_id="user_123",
        attach_type="none"
    )

    assert item.id.startswith("inq_")
    assert item.status == "pending"
    assert item.category_label == "🎨 시화집 편집 및 조판 코칭"
    assert item.title == "조판 여백 질문입니다"

    # 조회
    loaded = mgr.get_inquiry(item.id)
    assert loaded is not None
    assert loaded.author_email == "poet@example.com"


def test_reply_inquiry(temp_inquiry_mgr):
    mgr = temp_inquiry_mgr

    item = mgr.create_inquiry(
        category="bug",
        title="PDF 도련 여백 문의",
        content="출판용 PDF 도련이 궁금합니다.",
        author_name="박시인",
        author_email="park@example.com",
        attach_type="none"
    )

    answered = mgr.reply_inquiry(
        inquiry_id=item.id,
        reply_content="사방 도련 3mm는 부크크 POD 표준 인쇄 규격으로 자동 적용되어 있습니다.",
        status="answered"
    )

    assert answered is not None
    assert answered.status == "answered"
    assert "사방 도련 3mm" in answered.reply_content
    assert answered.answered_at != ""


def test_list_inquiries_filtering(temp_inquiry_mgr):
    mgr = temp_inquiry_mgr

    # 유저 A
    mgr.create_inquiry(
        category="general",
        title="감사 인사",
        content="정말 좋은 프로그램입니다.",
        author_name="유저A",
        author_email="userA@example.com",
        user_id="uid_A"
    )
    # 유저 B
    mgr.create_inquiry(
        category="feature",
        title="기능 제안",
        content="폰트 추가해주세요.",
        author_name="유저B",
        author_email="userB@example.com",
        user_id="uid_B"
    )

    # 전체 조회
    all_items = mgr.list_inquiries()
    assert len(all_items) == 2

    # 유저 A 필터링
    a_items = mgr.list_inquiries(user_id="uid_A")
    assert len(a_items) == 1
    assert a_items[0]["author_name"] == "유저A"

    # 유저 B 이메일 필터링
    b_items = mgr.list_inquiries(user_email="userB@example.com")
    assert len(b_items) == 1
    assert b_items[0]["title"] == "기능 제안"


def test_custom_file_attachment(temp_inquiry_mgr):
    mgr = temp_inquiry_mgr

    dummy_csv = "Episode,Title\n1,새벽".encode("utf-8")
    item = mgr.create_inquiry(
        category="coaching",
        title="CSV 첨부 상담",
        content="제 시 목록입니다.",
        author_name="이시인",
        author_email="lee@example.com",
        attach_type="custom_file",
        custom_file_bytes=dummy_csv,
        custom_filename="my_poem.csv"
    )

    assert item.attachment_type == "custom_file"
    assert item.attachment_filename == "my_poem.csv"

    # 첨부파일 경로 검증
    abs_path = mgr.get_attachment_abs_path(item.id)
    assert abs_path is not None
    assert abs_path.exists()
    assert abs_path.read_bytes() == dummy_csv

