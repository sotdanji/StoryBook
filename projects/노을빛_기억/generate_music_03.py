# -*- coding: utf-8 -*-
"""
[제03화] 마지막 상여 - sotdanjiAPI YuE2 음원 생성 실행 스크립트 (generate_music_03.py)

사용법:
1. Colab에서 sotdanjiAPI 서버(YuE2 엔드포인트 포함)를 실행하고 ngrok/localtunnel 공인 URL을 발급받습니다.
2. 환경 변수 SOTDANJI_BASE_URL (예: https://xxxx.ngrok-free.app) 및 SOTDANJI_API_KEY를 설정하거나 본 파일의 설정을 수정합니다.
3. 실행: python generate_music_03.py
"""
import os
import sys
import json
import requests
from pathlib import Path

# 콘솔 인코딩 설정
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 설정
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_AUDIO = BASE_DIR / "images" / "03_마지막상여.mp3"
LYRICS_JSON = BASE_DIR / "03_마지막상여_노랫말.json"

API_BASE_URL = os.getenv("SOTDANJI_BASE_URL", "http://localhost:8080").rstrip("/")
API_KEY = os.getenv("SOTDANJI_API_KEY", "sk-sotdanji-master-2026")

# YuE2 음악 생성 프롬프트 및 메타데이터
MUSIC_SPEC = {
    "title": "마지막 상여 (The Last Bier)",
    "chapter": "제03화",
    "genre_prompt": (
        "Korean Traditional Folk Ballad, Mournful Elegy, Han, Gugak Crossover, "
        "Haegeum, Daegum solo, Gayageum, Janggu, Deep Korean Buk, Soft Strings, Low Piano, "
        "Slow 68 BPM, Joongmori rhythm, sorrowful traditional female vocal, heartbreaking"
    ),
    "model": "yue-2",
    "duration_sec": 195,
    "lyrics": """[Genre: Korean Traditional Folk Ballad, Mournful Elegy, Han, Gugak Crossover]
[Instruments: Haegeum, Daegum, Gayageum, Janggu, Deep Korean Buk, Soft Strings]
[Tempo: Slow, 68 BPM, Joongmori rhythm]
[Mood: Heartbreaking, Tearful, Sorrowful, Poetic]

[Intro]
(구슬픈 대금 독주로 시작되어 빗소리와 함께 해금의 처연한 선율이 얹어진다. 장구의 느린 북편 소리가 가슴을 먹먹하게 두드린다.)

[Verse 1]
목화는 어느덧 전설이 되고
모시올 풀던 날 아득하여라
겨울엔 살 덥히는 무명베를 짜고
여름엔 숨통 틔울 올을 고르며
사철 우리 어머니 쉴 날 없었네

사대가 모여 사는 종갓집 맏며느리
환갑이 지나도록 층층시하라
서방님 손목 잡고 마실 문턱조차
한 번을 나선 적이 없던 사람아

[Verse 2]
전란의 포화 속에 뼈나 찾을까
점쟁이 말대로 살아는 왔으나
마당에 쏟아내던 기침 소리엔
아직도 화약 내음 묻어 있었지

산신령님 조왕님 감사하여라
두 손 모아 눈물로 빌고 빌어도
칠순의 문턱에서 숨이 꺾이어
애비 노릇 그만두고 눈을 감았네

[Chorus]
오뉴월 장대비는 억수로 퍼붓는데
장롱 속 오십 년 묵은 모시 수의
고이 접은 슬픔을 몸에 두르고
먼 길 떠나는 임을 배웅하누나
골목길 굽이돌아 꽃상여 나가니
빗물에 상여꽃이 녹아내리네

[Bridge]
(장구와 북소리가 중중모리로 고조되며, 해금이 애간장을 끊듯 솟구친다)
어허- 넘차 달구야
어허- 넘차 달구야
어른 노릇 그 삶이 그리 버거워
자기 어머니 등진 지 석 달 만에
홀로 이 빗속을 떠나가시오

[Chorus]
오뉴월 장대비는 억수로 퍼붓는데
장롱 속 오십 년 묵은 모시 수의
고이 접은 슬픔을 몸에 두르고
먼 길 떠나는 임을 배웅하누나
골목길 굽이돌아 꽃상여 나가니
빗물에 상여꽃이 녹아내리네

[Outro]
베틀 소리 끊긴 지 반백 년 세월
달구 소리만 구슬프게 골목을 도네
녹아내린 꽃잎 따라 길을 떠나는
우리 마을의, 아…… 마지막 상여여라.
(대금의 여운과 빗소리가 천천히 잦아들며 페이드아웃)"""
}

def save_spec_json():
    """노랫말과 음악 프롬프트 규격 JSON 저장"""
    with open(LYRICS_JSON, "w", encoding="utf-8") as f:
        json.dump(MUSIC_SPEC, f, ensure_ascii=False, indent=2)
    print(f"✅ 노랫말 메타데이터 저장 완료: {LYRICS_JSON}")

def generate_via_sotdanji():
    """sotdanjiAPI Hub (YuE2) 호출"""
    url = f"{API_BASE_URL}/v1/audio/music"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "prompt": MUSIC_SPEC["genre_prompt"],
        "lyrics": MUSIC_SPEC["lyrics"],
        "duration_sec": MUSIC_SPEC["duration_sec"],
        "model": MUSIC_SPEC["model"]
    }
    
    print("=" * 60)
    print(f"🎵 [sotdanjiAPI] YuE2 음원 생성 요청 시작")
    print(f"📍 대상 서버: {API_BASE_URL}")
    print(f"🎼 장르 스타일: {MUSIC_SPEC['genre_prompt'][:50]}...")
    print("=" * 60)

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=300)
        if response.status_code == 200:
            OUTPUT_AUDIO.parent.mkdir(parents=True, exist_ok=True)
            with open(OUTPUT_AUDIO, "wb") as f:
                f.write(response.content)
            print(f"🎉 음원 생성 및 저장 성공: {OUTPUT_AUDIO}")
            return True
        else:
            print(f"⚠️ 서버 응답 오류 [{response.status_code}]: {response.text}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"ℹ️ [안내] 현재 {API_BASE_URL} 서버가 오프라인 상태입니다.")
        print("💡 Colab 또는 원격 서버에서 sotdanjiAPI를 기동한 후 다시 실행해 주십시오.")
        return False
    except Exception as e:
        print(f"❌ 요청 중 오류 발생: {e}")
        return False

if __name__ == "__main__":
    save_spec_json()
    success = generate_via_sotdanji()
    if not success:
        print("\n[참고] 음원 규격 JSON 파일이 정상 준비되었으므로, Colab 서버 가동 시 즉시 호출 가능합니다.")
