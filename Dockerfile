# =====================================================================
# StoryBook Studio: Fly.io 서울 리전(icn) 상시대기 단일 플랫폼 Dockerfile
# - 한국 정통 서정 폰트(나눔명조 풀 세트) 기본 내장
# - 300 DPI 부크크(Bookk) 완제본 PDF 조판 및 오디오 처리 완벽 지원
# =====================================================================

FROM python:3.11-slim

# 파이썬 런타임 최적화 환경변수
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080

WORKDIR /app

# 1. 한국 정통 서정 명조 폰트(fonts-nanum) 및 오디오 처리 도구(ffmpeg) 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-nanum \
    fontconfig \
    ffmpeg \
    && fc-cache -fv \
    && rm -rf /var/lib/apt/lists/*

# 2. 파이썬 의존성 설치 (레이어 캐싱 극대화)
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# 3. 애플리케이션 소스 코드 복사
COPY . .

# 4. 기본 런타임 디렉토리 보장
RUN mkdir -p /app/.exports /app/core/fonts

# 5. Fly.io 표준 포트 노출 및 Uvicorn 상시대기 서버 기동
EXPOSE 8080

CMD ["uvicorn", "web.app:app", "--host", "0.0.0.0", "--port", "8080", "--timeout-keep-alive", "120"]

