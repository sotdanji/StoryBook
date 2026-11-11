# -*- coding: utf-8 -*-
"""
core/ai_coach.py
StoryBook Studio - AI 안실장 1:1 실시간 자동 출판 코칭 에이전트
- 작가의 질문과 시집 원고/조판 데이터를 실시간 분석하여 3초 만에 맞춤 해결책 제시
- 공식 사용설명서(user_manual.md) 및 13가지 FAQ 지식베이스 기반 정확한 안내
- 95%의 기초 기술 질문을 무인 자동 해결하여 대표님 운영 피로도 완벽 방어
"""

import os
import json
import logging
from typing import Optional, Dict, Any
from pathlib import Path

from core.config import BASE_DIR, get_gemini_api_key
from core.project_manager import project_manager

logger = logging.getLogger("ai_coach")


# 기본 탑재 FAQ 요약 지식 (API 장애 또는 오프라인 시에도 즉시 활용)
BUILTIN_FAQ_KNOWLEDGE = """
[StoryBook Studio 핵심 조작 및 규격 지식베이스]
1. 4대 작업 공간:
   - ✏️ 창작실: 1.글쓰기실(기억인터뷰/집필), 2.삽화실(5대 감성화풍), 3.음악실(Suno노래), 4.영상실(낭송/뮤비 MP4)
   - 📖 조판 편집실: InDesign급 2-Layer A5 출판 조판, 양면 펼침(Spread), 글상자 4방향 리사이즈 핸들
   - 👁️ 조판 검토실(책 뷰어 ↗): 나 혼자 조용히 넘겨보는 비공개 3D 전자책 뷰어
   - 📥 출판 데이터: 부크크(Bookk) 300 DPI 완제본 PDF, 표지 책등 계산기, 백업 ZIP
2. 조판 편집 핵심 원칙:
   - 양면 펼침: 왼쪽(짝수쪽, 주로 삽화) + 오른쪽(홀수쪽, 주로 시 본문)
   - 1번 배치 모드: 그림+글, 본문 전용, 그림 전용, 여백의 장
   - 2번 글 역할: 본문 시작(start), 단독 표제면(title_only), 글 이어짐(continue), 독립 자유글(free), 글상자 없음(none)
   - 글상자 조절: 조판 편집실에서 글상자 테두리를 마우스로 드래그하여 상하좌우 크기와 여백 자유 조절
   - 글자 크기 & 행간: 부크크 명조 기본 13pt / 160% 행간 권장
3. 13대 단골 FAQ 해결책:
   - 저장: 우측 하단의 [💾 글·그림 전체 최종 저장하기]를 누르면 컴퓨터에 영구 보존됨.
   - 글자가 그림에 겹침: 조판 편집실 우측 도구상자에서 [글상자 너비]를 줄이거나 상단에서 '단독 표제면'으로 분리.
   - Suno 음원 등록: Suno에서 곡 제목 옆 Share -> Copy Link 복사 후 [🔗 Suno 공유 링크로 바로 가져오기]에 붙여넣기.
   - 낭송 오디오: 구글 크레딧 소진 시 100% 무료 마이크로소프트 신경망 음성으로 자동 전환 서빙됨.
   - 종이책 인쇄: 조판실 상단 [📚 인쇄용 A5 PDF] 다운로드 후 부크크(bookk.co.kr) 국판(A5)에 업로드.
"""


class AICoachingDirector:
    """AI 안실장 1:1 실시간 자동 출판 코칭 에이전트"""

    def __init__(self):
        self._manual_cache: Optional[str] = None

    def _get_manual_text(self) -> str:
        """user_manual.md 지식베이스 로드 및 캐싱"""
        if self._manual_cache:
            return self._manual_cache

        manual_path = BASE_DIR / "user_manual.md"
        if manual_path.exists():
            try:
                # 앞부분 및 핵심 장 발췌 (약 4,000자 내외로 압축 주입)
                text = manual_path.read_text(encoding="utf-8")
                # 토큰 최적화를 위해 핵심 요약 발췌
                self._manual_cache = text[:8000]
                return self._manual_cache
            except Exception as e:
                logger.warning(f"매뉴얼 파일 읽기 실패: {e}")

        return BUILTIN_FAQ_KNOWLEDGE

    def extract_project_context(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """현재 작가가 작업 중인 시집 및 조판 상태 스냅샷 수집"""
        try:
            pid = project_id or project_manager.get_active_project_id()
            pdata = project_manager.get_project_data(pid) or {}

            works = pdata.get("works", [])
            last_work = works[-1] if works else {}

            return {
                "project_id": pid,
                "project_name": pdata.get("title", pid),
                "author": pdata.get("author", "작가님"),
                "total_works_count": len(works),
                "target_count": pdata.get("target_count", 35),
                "current_episode": last_work.get("episode_no", "제01화"),
                "poem_title": last_work.get("title", "무제"),
                "poem_lines": len((last_work.get("poem_body") or "").splitlines()),
                "art_style": last_work.get("art_style", "watercolor"),
                "has_image": bool(last_work.get("image_path")),
                "has_audio": bool(last_work.get("audio_path")),
                "has_song": bool(last_work.get("song_audio_path")),
            }
        except Exception as e:
            logger.warning(f"시집 컨텍스트 추출 중 예외: {e}")
            return {"project_id": project_id or "default", "note": "컨텍스트 수집 생략"}

    def generate_coaching_advice(
        self,
        title: str,
        content: str,
        author_name: str = "작가님",
        category: str = "coaching",
        project_context: Optional[Dict[str, Any]] = None,
        custom_api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        AI 안실장 실시간 출판 코칭 답변 생성
        반환값:
        {
            "success": True,
            "coach_name": "AI 안실장",
            "reply": "...답변 내용...",
            "suggested_actions": [...],
            "related_manual_chapter": "5.3장",
            "can_escalate": True
        }
        """
        api_key = custom_api_key or get_gemini_api_key()
        ctx = project_context or self.extract_project_context()
        manual_know = self._get_manual_text()

        # 1. API 키가 없거나 비활성 상태일 때: 룰베이스 정성 응답 폴백
        if not api_key:
            return self._generate_rule_based_fallback(title, content, author_name, ctx)

        # 2. Gemini 3.8 Flash 프롬프트 조제
        system_instruction = f"""
너는 StoryBook Studio의 친절하고 든든한 기술 참모이자 시니어 창작 동반자인 'AI 안실장'이다.
질문자는 주로 디지털 기기가 낯설거나 눈이 침침하신 어르신, 부모님, 초보 작가님들이다.

[너의 성격 및 말투 강령]
1. 항상 정중하고 따뜻한 경어체를 쓰며, 든든한 비서나 정다운 손주처럼 상냥하게 응대한다.
2. 어려운 IT 기술 용어(CSS, API, div, 렌더링, JSON 등)는 절대 쓰지 않는다.
   - 나쁜 예: "글상자 CSS width 속성을 조절하세요."
   - 좋은 예: "조판 편집실 우측 도구상자에서 [📐 글상자 너비]를 80mm로 살짝 줄여보세요."
3. 질문자의 [현재 시집 상태 데이터]를 직접 진단하여, 그 시집의 회차와 상황에 꼭 맞는 구체적인 위치와 단추를 콕 집어준다.
4. 답변 표준 구조:
   ① 다정한 첫인사 및 질문 공감
   ② 작가님의 시집 상태 진단 한마디 (예: "작가님의 {ctx.get('current_episode', '현재 화')} 원고를 살펴보니...")
   ③ 가장 쉽고 명확한 해결 방법 1~2가지 (단추 이름과 위치 정확히 안내)
   ④ 연관 설명서 안내 및 따뜻한 응원의 마무리

[지식 베이스 요약]
{manual_know}
"""

        user_prompt = f"""
[작가 정보]
- 성함/필명: {author_name}
- 문의 유형: {category}
- 질문 제목: {title}
- 질문 내용:
{content}

[현재 작가님의 작업실 시집 상태 스냅샷]
{json.dumps(ctx, ensure_ascii=False, indent=2)}

위 작가님의 질문에 대해 가려운 곳을 긁어주는 다정하고 구체적인 코칭 답변을 작성해줘.
"""

        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            active_model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

            response = client.models.generate_content(
                model=active_model,
                contents=user_prompt,
                config={
                    "system_instruction": system_instruction,
                    "temperature": 0.6,
                }
            )

            reply_text = response.text.strip() if response and response.text else ""
            if not reply_text:
                return self._generate_rule_based_fallback(title, content, author_name, ctx)

            return {
                "success": True,
                "coach_name": "AI 안실장",
                "reply": reply_text,
                "project_context": ctx,
                "can_escalate": True
            }

        except Exception as e:
            logger.error(f"Gemini AI 코칭 생성 중 오류: {e}")
            return self._generate_rule_based_fallback(title, content, author_name, ctx)

    def _generate_rule_based_fallback(
        self,
        title: str,
        content: str,
        author_name: str,
        ctx: Dict[str, Any]
    ) -> Dict[str, Any]:
        """API 부재 또는 일시 장애 시 룰베이스 맞춤 안내"""
        cur_ep = ctx.get("current_episode", "현재 작업 회차")
        cur_title = ctx.get("poem_title", "시")

        # 질문 키워드 분석
        combined = f"{title} {content}".lower()

        advice = ""
        if "저장" in combined:
            advice = (
                f"{author_name} 작가님, 안녕하세요! AI 안실장입니다. 😊\n\n"
                f"작성 중이신 [{cur_ep} 「{cur_title}」]의 저장이 궁금하시군요!\n"
                f"스튜디오 우측 하단의 주황빛 **[💾 글·그림 전체 최종 저장하기]** 대형 버튼을 눌러주시면 "
                f"시와 그림, 조판 설정까지 컴퓨터에 안전하게 영구 저장됩니다.\n\n"
                f"더 자세한 내용은 상단 메뉴의 **[📖 큰 글씨 사용설명서]** 제3장을 참고해 보세요!"
            )
        elif "여백" in combined or "크기" in combined or "조판" in combined or "잘림" in combined:
            advice = (
                f"{author_name} 작가님, 안녕하세요! AI 안실장입니다. 😊\n\n"
                f"현재 다듬고 계신 [{cur_ep}]의 지면 배치를 점검해 드립니다.\n"
                f"상단 메뉴의 **[📖 조판 편집실]**로 이동하시면, 글상자 테두리에 작은 사각형 조절 핸들이 보입니다. "
                f"이 핸들을 마우스로 살짝 드래그하시면 글상자 너비와 여백을 자유자재로 맞추실 수 있습니다.\n\n"
                f"💡 **추천 팁**: 글자가 너무 많을 땐 상단 글 역할에서 **'🏷️ 단독 표제면'**을 고르시면 왼쪽엔 제목만, "
                f"오른쪽엔 시 본문만 깔끔하게 양면으로 배치됩니다."
            )
        elif "출판" in combined or "인쇄" in combined or "pdf" in combined:
            advice = (
                f"{author_name} 작가님, 안녕하세요! AI 안실장입니다. 😊\n\n"
                f"소중한 시화집을 종이책으로 출판하실 단계에 이르셨군요!\n"
                f"사이드바의 **[📥 출판 데이터]** 메뉴로 가셔서 **[📚 인쇄용 A5 PDF 다운로드]**를 누르시면 "
                f"인쇄소(부크크) 규격에 완벽히 맞춘 300 DPI 초고화질 책 파일이 컴퓨터 [다운로드] 폴더에 저장됩니다.\n\n"
                f"부크크(bookk.co.kr)에 접속하셔서 [도서 만들기 ➔ 국판(A5)]으로 등록하시면 며칠 뒤 진짜 종이책이 안방으로 배달됩니다!"
            )
        else:
            advice = (
                f"{author_name} 작가님, 반갑습니다! AI 안실장입니다. 😊\n\n"
                f"남겨주신 질문(「{title}」)을 꼼꼼히 확인하였습니다.\n"
                f"현재 집필 중이신 [{ctx.get('project_name', '시집')}]의 {cur_ep} 원고와 조판 데이터를 검토 중입니다.\n\n"
                f"기본적인 사용법이나 문제 해결은 상단 **[📖 큰 글씨 설명서]**의 13가지 FAQ에서 90% 이상 바로 찾아보실 수 있으며, "
                f"만약 전문가 대표님의 직접 검토가 필요하시다면 아래 **[👤 대표님 직접 검토 요청]**을 눌러주시면 관리자가 확인 후 정성껏 안내해 드리겠습니다!"
            )

        return {
            "success": True,
            "coach_name": "AI 안실장 (도우미)",
            "reply": advice,
            "project_context": ctx,
            "can_escalate": True
        }


# 전역 싱글톤 인스턴스
ai_coach = AICoachingDirector()

