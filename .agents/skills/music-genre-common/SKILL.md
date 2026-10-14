---
name: music-genre-common
description: StoryBook Studio 시화집 노래/음악 공통 표준 지침. 시어의 운율화 원칙, Suno/Udio/YuE 메타태그([Intro], [Verse], [Chorus], [Outro - Fade Out]), 70~85 BPM 슬로우-미드 템포, 과도한 전자음/오토튠 배제, 따스한 아날로그 룸 어쿠스틱 사운드 표준.
---

# 🎵 시화집 작곡 공통 표준 스킬 (Music Genre: Common Standards)

StoryBook Studio의 모든 음악 장르(민요, 포크, 가곡, 동요)에 공통으로 적용되는 **시어의 노랫말 운율화 규격, AI 작곡 메타태그 표준, 믹싱 템포 및 금기 사항(Negative Tags)** 지침입니다.

---

## 1. 시어의 노랫말 운율화 및 메타태그 규격 (Lyrics Structure)

시를 그대로 AI에 전달하면 글자 수 불일치로 인해 랩처럼 부르거나 박자가 무너질 수 있습니다. 반드시 아래의 기승전결 메타태그 구조로 운율을 정돈합니다:

```text
[Intro - 잔잔한 악기 선율 및 분위기 형성]
(선율이 아련하게 흐르며 시의 배경을 염)

[Verse 1 - 시의 전반부 정경 묘사]
(3·4조 또는 4·4조 한국어 자연스러운 호흡)

[Chorus - 시의 핵심 정서 및 클라이맥스 훅]
(가장 기억에 남는 시구와 감성적인 후렴구)

[Verse 2 - 시의 후반부 여운과 회상]
(점점 깊어지는 사유와 감정선)

[Chorus - 온화한 하모니로 반복]
(코러스 화음과 함께 따스하게 고조)

[Outro - 아련한 페이드 아웃]
(마지막 한 줄의 여운을 읊조린 뒤 서서히 사라짐)
```

---

## 2. 사운드 믹싱 및 프로덕션 공통 규격 (Production Standards)

1. **시화 낭독에 최적화된 템포 (70 ~ 85 BPM)**:
   - 시의 행간에 담긴 생각과 여운을 충분히 음미할 수 있도록 **Slow to Mid-tempo**를 유지합니다.
2. **따스한 아날로그 어쿠스틱 공간감 (Warm Analog & Gentle Reverb)**:
   - 인위적이고 차가운 디지털 음색 대신, 조용한 방 안이나 작은 소극장에서 연주하는 듯한 포근한 잔향(Room Reverb)을 부여합니다.
3. **자연스러운 엔딩 페이드아웃 (Outro Fade-out)**:
   - 노래의 끝은 급작스럽게 끊기지 않고, 마지막 현이나 피아노의 울림이 공기 중으로 서서히 사라지도록 구성합니다.

---

## 3. 금기 사항 및 네거티브 태그 (Negative Sound Tags)

시화집의 격조와 서정성을 해치는 자극적인 요소는 프롬프트에서 원천 배제합니다.

```text
harsh electronic synth, heavy autotune, aggressive drums, loud EDM, screaming metal vocals, distorted electric guitar, rap, trap beat, hyperpop, chaotic sound
```

---

## 4. 슬림 골든 스타일 프롬프트 공식 (Golden Music Prompt)

Suno, Udio, YuE 등의 `Style of Music` 칸에 입력되는 프롬프트는 아래 공식을 따릅니다:

```text
[장르 고유 악기 편성 & 보컬 톤], [서정적 분위기 키워드], warm acoustic room reverb, 75 bpm, emotional, nostalgic, poetic melody, 4/4 time
```
