"""
tests/test_ai_coach.py
AI 안실장 1:1 실시간 출판 코칭 에이전트 단위 테스트
"""

import tempfile
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch

from core.ai_coach import AICoachingDirector, ai_coach
from core.inquiry_manager import InquiryManager, InquiryItem


@pytest.fixture
def temp_inquiry_mgr():
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        mgr = InquiryManager(base_dir=base)
        yield mgr


def test_ai_coach_extract_project_context():
    """시집 프로젝트 스냅샷 정보 추출 검증"""
    coach = AICoachingDirector()
    ctx = coach.extract_project_context("non_existent_project_id")
    assert isinstance(ctx, dict)
    assert "project_id" in ctx


def test_ai_coach_knowledge_base_fallback():
    """지식베이스 및 룰베이스 폴백 응답 검증 (API 키 없을 때도 친절히 응답)"""
    coach = AICoachingDirector()

    # 1. 2페이지 1작품 질문
    res1 = coach._generate_rule_based_fallback(
        title="조판이 2페이지로 안 나와요",
        content="삽화랑 시가 한 면에 나오는 것 같아요. 어떻게 하나요?",
        author_name="김시인",
        ctx={"chapter_count": 5}
    )
    assert res1["success"] is True
    reply1 = res1["reply"]
    assert "안실장" in reply1
    assert "김시인" in reply1

    # 2. 여백 조판 질문
    res2 = coach._generate_rule_based_fallback(
        title="조판 여백과 글상자 핸들",
        content="글상자 테두리 여백을 넓히고 싶어요.",
        author_name="박시인",
        ctx={"project_name": "유년의 뜰", "current_episode": "제03화"}
    )
    assert res2["success"] is True
    reply2 = res2["reply"]
    assert "조판 편집실" in reply2 or "글상자" in reply2

    # 3. 부크크 종이책 인쇄 규격 질문
    res3 = coach._generate_rule_based_fallback(
        title="부크크 종이책 출판 인쇄 질문",
        content="PDF 다운로드 받아서 어떻게 출판하나요?",
        author_name="최시인",
        ctx={}
    )
    assert res3["success"] is True
    reply3 = res3["reply"]
    assert "부크크" in reply3 or "PDF" in reply3


def test_inquiry_manager_ai_lifecycle(temp_inquiry_mgr):
    """문의 접수 -> AI 안실장 처방 저장 -> 후속 에스컬레이션 -> 종결 라이프사이클 검증"""
    mgr = temp_inquiry_mgr

    # 1. 접수
    item = mgr.create_inquiry(
        category="coaching",
        title="제목 줄바꿈 조판 코칭 부탁드립니다",
        content="시 제목이 두 줄로 넘어가서 어색합니다.",
        author_name="이시인",
        author_email="lee@example.com",
        attach_type="none"
    )
    assert item.status == "pending"
    assert item.ai_reply == ""

    # 2. AI 답변 저장
    ai_text = "이시인 작가님, 안녕하세요! AI 안실장입니다. 제목이 길 때는 크기를 한 단계 낮추시거나..."
    saved = mgr.save_ai_reply(
        inquiry_id=item.id,
        ai_reply=ai_text,
        project_context={"chapter_count": 10}
    )
    assert saved is not None
    assert saved.status == "ai_answered"
    assert saved.ai_reply == ai_text
    assert saved.ai_answered_at != ""
    assert saved.project_context.get("chapter_count") == 10

    # 3. 대표님 직접 검토 요청(에스컬레이션)
    escalated = mgr.escalate_inquiry(item.id)
    assert escalated is not None
    assert escalated.status == "escalated"

    # 4. 종결(해결)
    resolved = mgr.resolve_inquiry(item.id, satisfaction=5)
    assert resolved is not None
    assert resolved.status == "resolved"
    assert resolved.satisfaction == 5


def test_ai_coach_generate_advice_structure(monkeypatch):
    """AI 안실장 generate_coaching_advice 반환 구조 검증"""
    import core.config as config_mod
    monkeypatch.setattr(config_mod, "get_gemini_api_key", lambda: "")

    advice = ai_coach.generate_coaching_advice(
        title="조판 편집기 글상자 크기 조절",
        content="글상자 테두리를 어떻게 늘리고 줄이나요?",
        author_name="정작가",
        category="coaching"
    )

    assert advice["success"] is True
    assert "reply" in advice
    assert len(advice["reply"]) > 20
    assert "안실장" in advice["coach_name"]
    assert advice["can_escalate"] is True
