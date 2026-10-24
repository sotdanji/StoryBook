# -*- coding: utf-8 -*-
"""
core/publishing_copier.py
시집 정식 출판을 위한 본문 외 구성 요소(Front & Back Matter) 전문 AI 카피라이팅 엔진
- 시인의 말 (서문 / Prologue): 수록된 시의 모티프와 감정선을 분석하여 집필하는 감동의 작가의 말
- 맺음말 (에필로그 / Epilogue): 시집을 갈무리하며 독자와 가족에게 건네는 따스한 소회
- 뒷표지 책 소개 카피 (Back Cover Blurb): 서가에서 시선을 사로잡는 핵심 추천사 및 감성 소개글
- 온라인(Google GenAI) 및 오프라인 고품격 서정 템플릿 폴백 완벽 지원
"""

import os
from typing import List, Optional
from core.config import GEMINI_API_KEY
from core.project_manager import ProjectInfo
from core.manuscript import PoemWork


class PublishingCopier:
    """시화집 출판 전용 카피라이팅 엔진"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "")

    def _summarize_works(self, works: List[PoemWork]) -> str:
        """수록된 시들의 제목과 기억의 중심을 간결하게 요약"""
        if not works:
            return "유년의 기억, 그리운 툇마루, 삶의 따스한 궤적"
        
        items = []
        for w in works[:20]:
            anchor = f" ({w.memory_anchor[:30]}...)" if getattr(w, 'memory_anchor', '') else ""
            items.append(f"- {w.title}{anchor}")
        return "\n".join(items)

    def generate_prologue(self, project_info: ProjectInfo, works: List[PoemWork]) -> str:
        """
        시인의 말 (서문 / Prologue) 생성
        - 12~18줄 내외의 품격 높은 서정 산문시/작가의 말 형태
        """
        works_summary = self._summarize_works(works)
        author_role = "엮은이" if getattr(project_info, 'author_type', 'single') == "collab" else "지은이"

        if self.api_key:
            try:
                from google import genai
                client = genai.Client(api_key=self.api_key)
                prompt = f"""당신은 한국 정통 서정문학(정지용, 백석, 박목월의 서정 미학)에 깊이 통달한 시집 출판 전문 편집위원입니다.
아래 시집의 정보와 수록된 시들을 깊이 공감하고, 시집의 맨 앞머리에 실릴 '시인의 말(서문)'을 집필해 주세요.

[시집 정보]
- 시집 제목: {project_info.name}
- 부제: {project_info.subtitle}
- {author_role}: {project_info.author}
- 기획 의도: {project_info.description}

[수록된 대표 작품들]
{works_summary}

[집필 원칙]
1. 분량: 12~18행 내외의 담담하고 깊이 있는 서정적 산문.
2. 어조: 허세를 부리거나 과장된 미사여구를 배제하고, 지나온 삶의 찰나와 소박한 기억의 온기를 담담히 읊조리는 어조.
3. 내용: 왜 이 시들을 엮게 되었는지, 차갑게 식어가던 기억 속 툇마루와 유년의 풍경이 어떻게 시와 그림이 되었는지를 진솔하게 고백.
4. 독자에게 건네는 따스한 소망으로 마무리.
5. 마지막 줄은 반드시 다음과 같이 끝맺을 것:
   "― {project_info.author} {author_role}"
6. 제목이나 다른 부연설명 없이 오직 시인의 말 본문 텍스트만 출력하세요.
"""
                resp = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )
                if resp and resp.text:
                    return resp.text.strip()
            except Exception as e:
                print(f"[PublishingCopier] Prologue GenAI error: {e}")

        # 오프라인 품격 폴백 서문
        return f"""가장 개인적인 기억이 가장 깊은 문학이자 예술이 된다.

이 시화집은 화려하게 꾸며낸 허구를 담지 않았습니다.
마음속 깊은 곳에 오래 고여 있던 찰나의 순간,
차갑게 식어가던 툇마루의 새벽과 그 시절 들었던 다정한 말 한마디를
온전한 나의 목소리와 은은한 수채의 빛깔로 빚어낸 삶의 기록입니다.

수록된 {len(works) if works else '여러'} 편의 시들은
세월의 강물에 씻겨 내려갈 뻔했던 유년의 뜰과
가족의 따스한 눈빛, 저녁 노을빛을 조용히 건져 올린 흔적입니다.

책장을 넘길 때마다 그날의 서정적 온기가
그리운 당신의 마음에 가만히 가닿기를 소망합니다.


― {project_info.author} {author_role}"""

    def generate_epilogue(self, project_info: ProjectInfo, works: List[PoemWork]) -> str:
        """
        맺음말 (에필로그 / Epilogue) 생성
        - 10~15줄 내외의 따스한 소회와 감사
        """
        author_role = "엮은이" if getattr(project_info, 'author_type', 'single') == "collab" else "지은이"

        if self.api_key:
            try:
                from google import genai
                client = genai.Client(api_key=self.api_key)
                prompt = f"""당신은 한국 정통 서정문학 전문 시집 편집인입니다.
시집의 대미를 장식할 '맺음말(에필로그)'을 집필해 주세요.

[시집 정보]
- 시집 제목: {project_info.name}
- 부제: {project_info.subtitle}
- {author_role}: {project_info.author}
- 기획 의도: {project_info.description}

[집필 원칙]
1. 분량: 10~15행 내외.
2. 내용:
   - 시집 한 권을 온전히 묶어내며 느낀 깊은 안도와 소회.
   - 지난 시절 곁을 지켜준 가족과 이웃, 그리고 이 시집을 펼쳐 든 이름 모를 독자를 향한 감사의 인사.
   - 삶은 저물어가는 것이 아니라, 기억 속에서 매일 새롭게 피어난다는 서정적 여운.
3. 마지막 줄: "어느 맑은 날, {project_info.author} 삼가 적음" 형태로 품격 있게 마무리.
4. 제목이나 기타 태그 없이 순수 본문 텍스트만 출력하세요.
"""
                resp = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )
                if resp and resp.text:
                    return resp.text.strip()
            except Exception as e:
                print(f"[PublishingCopier] Epilogue GenAI error: {e}")

        # 오프라인 품격 폴백 에필로그
        return f"""기억을 더듬어 한 줄의 시를 빚고
그 곁에 따스한 그림을 얹는 동안,
나는 몇 번이고 지나온 계절 속을 다시 걸었습니다.

잊힌 줄로만 알았던 어머니의 밥 짓는 냄새와
바람에 흔들리던 고향 마당의 감나무,
그리고 묵묵히 곁을 지켜준 소중한 이들의 숨결이
이 작은 책갈피마다 살아 숨 쉬고 있음을 깨닫습니다.

이 시집을 손에 쥐어주신 모든 분께,
그리고 각자의 그리움을 품고 살아가는 모든 다정한 이들에게
작은 위로와 평안이 깃들기를 빕니다.


어느 맑은 날, {project_info.author} 삼가 적음"""

    def generate_back_cover_blurb(self, project_info: ProjectInfo, works: List[PoemWork]) -> str:
        """
        뒷표지 책 소개 카피 (Back Cover Blurb) 생성
        - 서점에서 시선을 사로잡는 핵심 인용구(2~3행) + 소개 카피(4~6행)
        """
        works_summary = self._summarize_works(works)

        if self.api_key:
            try:
                from google import genai
                client = genai.Client(api_key=self.api_key)
                prompt = f"""당신은 출판계 최고의 서정시 전문 북 카피라이터입니다.
서점에서 독자가 책을 뒤집어 보았을 때 마음을 울릴 '뒷표지 추천 카피(Blurb)'를 작성해 주세요.

[시집 정보]
- 시집 제목: {project_info.name}
- 부제: {project_info.subtitle}
- 지은이: {project_info.author}
- 기획 의도: {project_info.description}
- 대표 시/모티프:
{works_summary}

[카피 작성 원칙]
1. 상단 인용 카피 (2~3행): 따옴표(“ ”) 안에 들어갈, 가슴을 저미는 묵직하고 서정적인 핵심 한 줄.
2. 본문 소개 카피 (4~5행): 시집 전체가 지닌 서정의 온도와 예술적 품격을 알리는 매력적인 안내문.
3. 총 6~8행 내외로 깔끔하고 정갈하게 정돈할 것.
4. 제목이나 설명 없이 순수 카피 텍스트만 출력하세요.
"""
                resp = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )
                if resp and resp.text:
                    return resp.text.strip()
            except Exception as e:
                print(f"[PublishingCopier] Blurb GenAI error: {e}")

        # 오프라인 품격 폴백 뒷표지 카피
        return """“가장 개인적인 기억이
가장 깊은 문학이자 예술이 된다.”

소박하지만 온기 넘치던 그 시절의 툇마루,
마음속 깊이 간직해 온 찰나의 순간들을
서정적인 시와 맑은 수채화로 엮었습니다.

세월이 흘러도 바래지 않는 삶의 정취가
당신의 지친 하루에 따스한 등불이 되어줄 것입니다."""


# 전역 인스턴스
publishing_copier = PublishingCopier()
