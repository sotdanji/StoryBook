# -*- coding: utf-8 -*-
"""
core/gemini_guard.py
StoryBook Studio - Google Gemini 3중 지능형 안티-폴백(Anti-Degradation) 가드
- 1차 방어: 지능형 모델 캐스케이딩 (3.8 Flash ➔ 3.7 Flash ➔ 2.5 Flash ➔ 2.5 Flash-Lite)
- 2차 방어: 429 한도 초과 감지 시 지수 백오프(Exponential Backoff: 1.5~2.5초) 자동 재시도
- 3차 방어: 조악한 룰베이스 더미 추락 금지 및 명확한 품질 보장 에러 핸들링
"""

import os
import time
import logging
from typing import List, Optional, Any, Dict

logger = logging.getLogger("gemini_guard")

# 캐스케이딩 대상 모델 우선순위 풀
CASCADING_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite"
]


class GeminiQuotaExhaustedError(Exception):
    """Google Gemini 무료 티어 일시적 분당 할당량(RPM) 초과 예외"""
    def __init__(self, message: str = "구글 무료 AI 분당 호출 한도(15회)에 도달했습니다. 약 15~30초 후 다시 시도해 주세요.", retry_after: int = 15):
        super().__init__(message)
        self.message = message
        self.retry_after = retry_after


def is_quota_or_rate_limit_error(err: Exception) -> bool:
    """에러가 429 할당량 초과 또는 속도 제한인지 식별합니다."""
    err_str = str(err).lower()
    quota_keywords = [
        "429", "resource_exhausted", "quota", "rate limit", "ratelimit",
        "too many requests", "exceeded", "credits", "exhausted"
    ]
    return any(k in err_str for k in quota_keywords)


def call_gemini_with_cascading(
    client: Any,
    contents: Any,
    preferred_model: Optional[str] = None,
    config: Optional[Any] = None,
    max_retries_per_model: int = 1
) -> Any:
    """
    Gemini 3중 방어막 호출:
    - 선호 모델부터 시작하여 429 발생 시 다음 고지능 모델로 자동 토스
    - 일시적 429 발생 시 1.5초 대기 후 재시도
    - 모든 모델 소진 시 GeminiQuotaExhaustedError 예외 발생 (조악한 룰베이스 추락 방지)
    """
    if preferred_model is None:
        preferred_model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

    # 호출 시도 모델 순서 구성 (선호 모델 최우선, 중복 제거)
    models_to_try: List[str] = [preferred_model]
    for m in CASCADING_MODELS:
        if m not in models_to_try:
            models_to_try.append(m)

    last_error: Optional[Exception] = None

    for model_name in models_to_try:
        for attempt in range(max_retries_per_model + 1):
            try:
                # print(f"[GeminiGuard] 시도 모델: {model_name} (시도 {attempt + 1})")
                call_kwargs = {
                    "model": model_name,
                    "contents": contents,
                }
                if config is not None:
                    call_kwargs["config"] = config

                response = client.models.generate_content(**call_kwargs)
                if response:
                    # 성공적으로 응답 획득
                    return response

            except Exception as e:
                last_error = e
                err_str = str(e)
                logger.warning(f"[GeminiGuard] {model_name} 호출 오류 (시도 {attempt + 1}): {err_str[:120]}")

                if is_quota_or_rate_limit_error(e):
                    # 429 할당량 초과 시: 백오프 대기 후 동일 모델 재시도 또는 다음 모델로 캐스케이딩
                    if attempt < max_retries_per_model:
                        time.sleep(1.5)
                        continue
                    else:
                        logger.info(f"[GeminiGuard] {model_name} 한도 초과 -> 다음 모델로 지능형 캐스케이딩 전환...")
                        time.sleep(1.0)
                        break  # 다음 모델로 넘어감
                else:
                    # 503 일시 서버 오류 등
                    if "503" in err_str or "unavailable" in err_str.lower():
                        time.sleep(1.2)
                        continue
                    # 기타 치명적 파라미터 에러 등은 다음 모델 시도
                    break

    # 모든 모델이 소진된 경우
    if last_error and is_quota_or_rate_limit_error(last_error):
        raise GeminiQuotaExhaustedError(
            message="Google 무료 AI 분당 호출 한도(15회)에 도달했습니다. 잠시(약 15~30초) 후 다시 눌러주시면 고품질 시가 완성됩니다."
        )

    # 그 외 일반 에러
    raise last_error or RuntimeError("Gemini AI 응답 생성에 실패했습니다.")
