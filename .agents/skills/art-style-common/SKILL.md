---
name: art-style-common
description: StoryBook Studio 시화집 삽화 공통 규격 및 출판 품질 지침. 외곽 10% 자연스러운 페이드아웃 여백(Soft Vignette), 순백/미색 종이 자연 융합, 텍스트/낙관/액자 절대 배제, 300 DPI 출판 인쇄 표준.
---

# 📜 시화집 삽화 공통 출판 표준 스킬 (Art Style: Common Standards)

StoryBook Studio의 모든 화풍(수채화, 수묵담채, 파스텔, 만화/스케치)에 공통으로 적용되는 **출판 규격, 종이 결 융합, 안전 여백 및 금기 사항(Negative Constraints)** 지침입니다.

---

## 1. 캔버스 외곽 5% 미세 페이드아웃 (Edge Bleed & Subtle Vignette)

1. **테두리 경계 소멸 및 중심 피사체 95% 온전 보존**:
   - 사각형 캔버스 모서리에 날카로운 칼선(Hard Rectangular Border)이 남지 않도록 합니다.
   - 단, 중심 인물이나 사물이 잘려나가지 않도록 **외곽 5% 미세 영역만 은은하게 페이드아웃**하고, **중심부 95% 영역은 인물과 사물의 디테일이 온전히 보존**되도록 연출합니다.
2. **시화집 본문 종이와의 자연스러운 융합 (Paper Texture Integration)**:
   - 그림이 인쇄될 책의 순백색 또는 미색 본문 종이(Textured white/cream book paper)와 경계 없이 이어져, 시의 텍스트가 놓일 여백과 하나의 호흡을 이룹니다.
3. **시그니처 표현 문구 (Prompt Suffix Tokens)**:
   - `subtle 5% edge vignette fading gently into pure paper margin, full rich central composition, 300 dpi`

---

## 2. 텍스트 및 인쇄 불순물 절대 배제 (Zero Text & Artifacts)

시화집에서 시 텍스트는 조판 엔진(PDF 빌더)이 정밀하게 배치하므로, 생성되는 그림 자체에는 어떠한 글자나 기호도 들어가서는 안 됩니다.

* **금기 요소 (Forbidden Elements)**:
  - 한글, 한자, 알파벳, 숫자, 시 구절, 제목
  - 작가 서명(Signature), 워터마크(Watermark)
  - 붉은 낙관(Red seal / stamp), 도장
  - 테두리 액자(Frame, Border, Outer line)
  - 만화 칸 구분선(Panels), 말풍선(Speech bubbles)
* **공통 네거티브 프롬프트 (Common Negative Tokens)**:
  ```text
  text, letters, words, hangul, calligraphy, watermark, signature, artist stamp, red seal, frame, border, outer edge lines, hard rectangular border
  ```

---

## 3. 고해상도 출판 규격 (Publishing Standards)

1. **300 DPI 인쇄 규격 보장**:
   - 프롬프트 말미에 반드시 `300 dpi` 규격을 명시하여 POD(부크크 등) 인쇄 시 픽셀 깨짐이나 뭉개짐을 방지합니다.
2. **시선의 집중 (Focal Point Clarity)**:
   - 중앙 또는 3분할 교차점에 시의 핵심 피사체가 선명하게 안착하고, 주변부는 은은한 여백으로 처리하여 시의 낭독과 사유를 방해하지 않습니다.

---

## 4. 슬림 골든 프롬프트 조립 공식 (Golden Prompt Formula)

모든 화풍 프롬프트는 아래의 3단 구조로 간결하게 조립(총 25~35단어 내외)합니다:

```text
[화풍별 고유 기법 & 피사체] + [빛과 정서] + [공통 페이드아웃 여백 & 출판 규격]
```

* **공통 권장 접미사 (Common Suffix)**:
  ```text
  soft vignette fading into pure paper margin, peaceful poetic space, textured paper, 300 dpi
  ```
