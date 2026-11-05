# ✍️ `korean_poetic_ai` (한국어 서정 문학 AI & 고유어 시소러스 엔진)

정지용·백석·박목월 전통 서정 미학 기반의 **기억 인터뷰, 2종 시안(A/B) 작시, 클리셰 제거 퇴고, 한국어 시어·방언 시소러스 사전, 서정 삽화/음악 프롬프트 빌더**를 제공하는 독립 패키지입니다.

## 🚀 다른 프로젝트에서 바로 사용하기

```python
from packages.korean_poetic_ai import KoreanPoeticAI, build_publication_illustration_prompt

ai = KoreanPoeticAI()

# 1. 기억 조각으로부터 A/B 2가지 서정시 초안 생성 (API 키 없이도 동작하는 하이브리드 엔진 탑재)
drafts = ai.compose_dual_drafts(
    core_memory="비 오는 날 외갓집 대청마루",
    sensory_details="처마 끝 낙숫물 소리, 젖은 흙냄새",
    spoken_words="비 그치면 무지개 뜨겠네"
)
print(drafts["draft_a"]["title"], drafts["draft_a"]["body"])

# 2. 시어 감각 사전 및 토속어/방언 조회
syns = ai.lookup_thesaurus("어머니")
print(syns["alternatives"])

# 3. 300 DPI 출판 삽화 프롬프트 생성
prompt_info = build_publication_illustration_prompt(
    scene_description="Quiet Korean traditional wooden porch in gentle rain",
    style_key="watercolor"
)
print(prompt_info["positive_prompt"])
```
