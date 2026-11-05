# -*- coding: utf-8 -*-
"""
packages/korean_poetic_ai
한국 정통 서정시 AI 작시·인터뷰·퇴고 엔진, 고유어 시소러스 사전, 13종 문학/화풍/음악 스킬팩 독립 패키지
"""
from typing import Optional, List, Dict, Any
from core.poetic_thesaurus import (
    POETIC_THESAURUS_DB,
    lookup_poetic_words,
    get_all_categories_summary,
    suggest_poetic_synonyms_ai,
)
from core.poetic_engine import PoeticEngine, poetic_engine
from core.skill_pack import (
    SKILL_POETIC_INTERVIEW,
    SKILL_POETIC_COMPOSITION,
    SKILL_POETIC_REFINEMENT,
    ART_STYLE_COMMON_RULES,
    MUSIC_COMMON_RULES,
    get_art_style_prompt_bundle,
    get_music_genre_bundle,
    build_modular_song_package,
)


class KoreanPoeticAI:
    """전역 설정 없이 API 키와 모델을 주입받아 즉시 사용하는 독립형 한국어 서정 문학 AI SDK"""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-3.8-flash"):
        self.api_key = api_key
        self.model = model
        self._engine = PoeticEngine()

    def compose_dual_drafts(
        self,
        core_memory: str,
        sensory_details: str = "",
        spoken_words: str = "",
        style_seed: Optional[int] = None,
        deep_interview_answer: str = "",
    ) -> Dict[str, Any]:
        return self._engine.compose_dual_drafts(
            core_memory=core_memory,
            sensory_details=sensory_details,
            spoken_words=spoken_words,
            style_seed=style_seed,
            deep_interview_answer=deep_interview_answer,
        )

    def refine_poem(self, title: str, poem_body: str, mode: str = "subdued", instruction: str = "") -> Dict[str, Any]:
        return self._engine.refine_poem_with_gemini(
            title=title,
            poem_body=poem_body,
            mode=mode,
            custom_instruction=instruction,
        )

    @staticmethod
    def lookup_thesaurus(word: str) -> Dict[str, Any]:
        return lookup_poetic_words(word)

    @staticmethod
    def list_thesaurus_categories() -> List[Dict[str, Any]]:
        return get_all_categories_summary()


__all__ = [
    "KoreanPoeticAI",
    "PoeticEngine",
    "poetic_engine",
    "POETIC_THESAURUS_DB",
    "lookup_poetic_words",
    "get_all_categories_summary",
    "suggest_poetic_synonyms_ai",
    "SKILL_POETIC_INTERVIEW",
    "SKILL_POETIC_COMPOSITION",
    "SKILL_POETIC_REFINEMENT",
    "ART_STYLE_COMMON_RULES",
    "MUSIC_COMMON_RULES",
    "get_art_style_prompt_bundle",
    "get_music_genre_bundle",
    "build_modular_song_package",
]
