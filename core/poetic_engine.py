# -*- coding: utf-8 -*-
"""
지능형 서정 시 작시 엔진 (Intelligent Korean Poetic Composition Engine)
- API 키가 없거나 외부 통신이 차단된 오프라인 환경에서도,
  사용자의 [기억의 중심], [구체적 사물과 행동], [들은 말], [심층 인터뷰 답변]을 분석하여
  산문을 시적 행으로 분절하고 어미를 승화시켜
  한국 정통 서정시(담담한 정경 묘사, 깊은 여운과 은유)의 높은 완성도를 빚어냅니다.
"""

import random
import re
from typing import Dict, List, Optional, Any


class PoeticEngine:
    def __init__(self):
        self.connectors = ["너머로", "곁으로", "문득", "가만히", "이내", "끝내", "어느덧", "덧없이"]

    def _clean(self, text: str) -> str:
        return text.strip() if text else ""

    def poetize_prose(self, text: str) -> List[str]:
        """산문형 문장을 시적 호흡의 짧은 행들로 분절하고 건조한 어미를 서정적으로 변환합니다."""
        if not text:
            return []
        
        # 1차 문장/구 분절
        raw_chunks = [p.strip() for p in re.split(r'[,.\n!?;]+', text) if p.strip()]
        lines = []

        endings_rules = [
            (r'([가-힣]+)한다$', r'\1하네'),
            (r'([가-힣]+)했다$', r'\1했었지'),
            (r'([가-힣]+)간다$', r'\1가고'),
            (r'([가-힣]+)올린다$', r'\1올릴 때'),
            (r'([가-힣]+)있다$', r'\1있던'),
            (r'([가-힣]+)본다$', r'\1보던'),
            (r'([가-힣]+)이다$', r'\1이어라'),
            (r'([가-힣]+)진다$', r'\1지는'),
        ]

        for chunk in raw_chunks:
            # 어미 변환
            converted = chunk
            for pat, rep in endings_rules:
                converted = re.sub(pat, rep, converted)

            words = converted.split()
            # 6단어 이상으로 너무 긴 행은 2행으로 호흡 분절
            if len(words) >= 6:
                mid = len(words) // 2
                lines.append(" ".join(words[:mid]))
                lines.append(" ".join(words[mid:]))
            else:
                lines.append(converted)

        return lines

    def generate_deep_interview_questions(
        self,
        core_memory: str,
        sensory_details: str,
        spoken_words: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        입력된 기억 파편을 분석하여
        1) 따뜻한 기억 공감 요약,
        2) 시의 깊이를 더해줄 3가지 시적 꼬리 질문을 생성합니다.
        """
        core = self._clean(core_memory)
        sensory = self._clean(sensory_details)
        spoken = self._clean(spoken_words)

        # 핵심 소재 키워드 추출
        all_text = f"{core} {sensory} {spoken}".strip()
        keywords = re.findall(r'[가-힣]{2,}', all_text)
        
        # 공감 요약 생성
        if core and sensory:
            summary = f"「{core}」의 시간, 그리고 눈에 밟히는 「{sensory}」의 정경이 아련하게 다가옵니다."
        elif core:
            summary = f"마음에 고여 있는 「{core}」의 그 시절, 그 순간이 눈앞에 그려집니다."
        elif sensory:
            summary = f"유난히 선명하게 기억나는 「{sensory}」의 풍경이 마음에 와닿습니다."
        else:
            summary = "선생님께서 마음에 품고 계신 소중한 순간의 한 조각을 마주합니다."

        # 꼬리 질문 3가지 (소리/감각, 시선의 머무름, 내면의 정서)
        q_sense = "그때 귓가에 스치던 소리(바람, 발자국, 숨소리)나 손끝에 닿았던 온도는 어떠했나요?"
        q_gaze = "그 순간, 시선이 가장 오래 머물렀던 사물이나 뒷모습은 어떤 모습이었나요?"
        q_inner = "집으로 돌아가거나 그 자리를 떠날 때, 가슴 한구석에 남았던 감정은 무엇이었나요?"

        # 문맥 맞춤형 미세 조정
        if any(w in all_text for w in ["어머니", "엄마", "아버지", "아빠", "할머니", "할아버지", "아들", "딸"]):
            q_gaze = "앞서 걷거나 곁에 있던 그분의 표정이나 손길, 혹은 굽은 뒷모습은 어떠했나요?"
        if any(w in all_text for w in ["석양", "노을", "새벽", "밤", "어둠", "달빛", "햇살"]):
            q_sense = "그때 주변을 물들이던 빛깔의 농도와 차가워지던 저녁 공기의 느낌은 어떠했나요?"
        if any(w in all_text for w in ["바다", "섬", "강", "물", "파도"]):
            q_sense = "철썩이던 물소리나 바람결에 묻어오던 짠 내음은 어떤 기억으로 남아있나요?"

        return {
            "summary": summary,
            "questions": [
                {"id": "q_sense", "category": "소리와 감각", "icon": "👂", "question": q_sense},
                {"id": "q_gaze", "category": "시선의 머무름", "icon": "👁️", "question": q_gaze},
                {"id": "q_inner", "category": "마음의 결", "icon": "❤️", "question": q_inner}
            ]
        }

    def compose_dual_drafts(
        self, 
        core_memory: str, 
        sensory_details: str, 
        spoken_words: Optional[str] = None,
        style_seed: Optional[int] = None,
        deep_interview_answer: Optional[str] = None
    ) -> Dict[str, Dict[str, str]]:
        """
        기억 파편과 심층 인터뷰 답변을 융합하여
        A안(담담한 정경 묘사)과 B안(여운과 내면의 은유)을 창작합니다.
        """
        rng = random.Random(style_seed if style_seed is not None else random.randint(1, 99999))
        
        core = self._clean(core_memory)
        sensory = self._clean(sensory_details)
        spoken = self._clean(spoken_words) if spoken_words else ""
        deep_ans = self._clean(deep_interview_answer) if deep_interview_answer else ""

        # 산문을 시적 행으로 분절
        core_lines = self.poetize_prose(core)
        sensory_lines = self.poetize_prose(sensory)
        deep_lines = self.poetize_prose(deep_ans)

        # 키워드 추출
        anchor_text = core or sensory or spoken or "그리운 기억"
        keywords = re.findall(r'[가-힣]{2,}', anchor_text)
        main_subject = keywords[-1] if keywords else (anchor_text[:12] if anchor_text else "기억")
        
        sensory_anchor = sensory or core or spoken or "그 시간"
        sensory_keywords = re.findall(r'[가-힣]{2,}', sensory_anchor)
        sub_subject = sensory_keywords[0] if sensory_keywords else (sensory_anchor[:12] if sensory_anchor else "그 시간")

        # A안 창작
        draft_a = self._compose_style_a_v2(main_subject, sub_subject, spoken, core_lines, sensory_lines, deep_lines, rng)
        # B안 창작
        draft_b = self._compose_style_b_v2(main_subject, sub_subject, spoken, core_lines, sensory_lines, deep_lines, rng)

        return {
            "draft_a": draft_a,
            "draft_b": draft_b
        }

    def _compose_style_a_v2(
        self, main: str, sub: str, spoken: str, 
        core_lines: List[str], sensory_lines: List[str], deep_lines: List[str], 
        rng: random.Random
    ) -> Dict[str, str]:
        """A안: 담담하고 절제된 정경 묘사 (풍경과 사실 중심)"""
        titles = [
            f"{main}",
            f"{main}의 무늬",
            f"그 무렵, {main}",
            f"{sub}에 닿은 손길",
            f"노을빛 길목에서",
            f"기억의 풍경"
        ]
        title = rng.choice(titles)

        stanzas = []

        # 1연: 시간과 장소의 서막
        stanza1 = []
        if core_lines:
            stanza1.extend(core_lines)
        else:
            stanza1.append(f"{main}이 깃든 자리")
        stanzas.append(stanza1)

        # 2연: 구체적인 사물과 행동
        stanza2 = []
        if sensory_lines:
            stanza2.extend(sensory_lines)
        else:
            stanza2.append("바람결에 흔들리던 그림자 하나")
        
        # 심층 인터뷰 디테일 반영
        if deep_lines:
            stanza2.extend(deep_lines)
        stanzas.append(stanza2)

        # 3연: 들은 말 / 침묵의 여운과 종결
        stanza3 = []
        if spoken:
            stanza3.append(f'"{spoken}"')
            stanza3.append("나지막이 귓가에 맴돌던 소리")
        else:
            closing_thoughts = [
                "말없이 오가던 서글픈 눈빛",
                "어둠을 조금씩 밀어내던 손길",
                "그 침묵이 사랑이었음을 뒤늦게 알았네"
            ]
            stanza3.append(rng.choice(closing_thoughts))
        
        stanza3.append("가만히 서성이며 그 길을 건너가네")
        stanzas.append(stanza3)

        body = "\n\n".join(["\n".join(s) for s in stanzas if s])
        return {"title": title, "body": body}

    def _compose_style_b_v2(
        self, main: str, sub: str, spoken: str, 
        core_lines: List[str], sensory_lines: List[str], deep_lines: List[str], 
        rng: random.Random
    ) -> Dict[str, str]:
        """B안: 깊은 여운과 은유 (내면의 울림과 서정성)"""
        titles = [
            f"{sub}가 머문 자리",
            f"손끝에 남은 시간",
            f"어느 날의 {main}",
            f"바람이 두고 간 말",
            f"여백의 온기",
            f"남겨진 풍경"
        ]
        title = rng.choice(titles)

        stanzas = []

        # 1연: 아련한 회상과 풍경
        stanza1 = ["문득 돌아보면", "시간의 문턱에 멈추어 선 정경"]
        if core_lines:
            stanza1.extend(core_lines)
        stanzas.append(stanza1)

        # 2연: 감각의 전이와 심층 내면
        stanza2 = []
        if sensory_lines:
            stanza2.extend(sensory_lines)
        if deep_lines:
            stanza2.append("")
            stanza2.extend(deep_lines)
        else:
            stanza2.append("손끝으로 더듬어 보는 기억은")
            stanza2.append("언제나 같은 자리에 머물러 있네")
        stanzas.append(stanza2)

        # 3연: 여운과 은유의 수렴
        stanza3 = []
        if spoken:
            stanza3.append(f'"{spoken}"')
            stanza3.append("되뇌일수록 짙어지는 음성")
        else:
            stanza3.append("바람 소리에도 묻어나는 기척")
        
        stanza3.append("비워둔 가슴에 조용히 차오르네")
        stanzas.append(stanza3)

        body = "\n\n".join(["\n".join(s) for s in stanzas if s])
        return {"title": title, "body": body}

    def refine_poem(self, current_body: str, style_mode: str) -> str:
        """기존 시를 퇴고/수정 (3행 압축, 절제, 운율 정돈)"""
        lines = [line.strip() for line in current_body.strip().split("\n") if line.strip()]
        if not lines:
            return current_body

        if style_mode == "shorten":
            if len(lines) <= 3:
                return "\n".join(lines)
            return f"{lines[0]}\n{lines[len(lines)//2]}\n{lines[-1]}"
        elif style_mode == "subdued":
            subdued_lines = []
            for line in lines:
                l = re.sub(r'사랑|그리움|슬픔|눈물|아픔', '', line).strip()
                if l:
                    subdued_lines.append(l)
            return "\n".join(subdued_lines) if subdued_lines else "\n".join(lines[:3])
        elif style_mode == "rhythm":
            paired = []
            for i, line in enumerate(lines):
                paired.append(line)
                if (i + 1) % 2 == 0 and i != len(lines) - 1:
                    paired.append("")
            return "\n".join(paired)

        return current_body

    def generate_art_prompt_from_poem(
        self,
        title: str,
        poem_body: str,
        core_memory: str = "",
        sensory_details: str = "",
        style_mode: str = "literal",
        art_style: str = "watercolor",
        custom_guide: str = ""
    ) -> str:
        """
        다듬어진 시의 제목과 본문, 기억 데이터를 분석하여
        300 DPI 출판용 영문 서정 삽화 프롬프트를 자동 생성합니다.
        """
        # [전통 향토/문화/정경 한국어 키워드 매핑 대폭 보강]
        keyword_mappings = {
            # 향토 음식 및 민속 식기
            "도토리묵": "traditional Korean acorn jelly (dotori-muk) neatly sliced in a rustic earthenware dish with seasoned soy sauce garnish",
            "도토리 묵": "traditional Korean acorn jelly (dotori-muk) neatly sliced in a rustic earthenware dish with seasoned soy sauce garnish",
            "도토리": "plump autumn acorns and fallen oak leaves scattered peacefully",
            "묵": "traditional savory acorn jelly neatly arranged in a rustic earthenware bowl",
            "막걸리": "rustic brass bowl of traditional milky rice wine makgeolli, ceramic wine kettle",
            "질그릇": "rustic Korean earthenware dish, traditional unglazed dark pottery",
            "옹기": "traditional Korean earthenware pottery jars",
            "뚝배기": "traditional dark earthenware pot, rustic earthenware bowl",
            "소반": "traditional small Korean wooden tray dining table (soban) on wooden floor",
            "소쿠리": "woven bamboo basket (sokuri) with rustic country harvest",
            "채반": "round woven bamboo drying tray with autumn harvest",
            "시골밥상": "humble traditional Korean country meal setting with rustic tableware",
            "가마솥": "large traditional cast iron cauldron on clay cooking stove",
            "맷돌": "traditional stone hand mill (maetdol) in rustic kitchen courtyard",
            "부엌": "warm rustic Korean country kitchen with clay hearth and wood embers",
            "아궁이": "warm glowing embers in traditional clay fireplace hearth",
            "지게": "traditional Korean wooden A-frame carrying rack (jige) resting against wall",
            "고무신": "pair of nostalgic white rubber shoes (gomusin) on stone step",
            "다듬이": "traditional smooth beating stones and wooden laundry clubs",
            "디딜방아": "traditional wooden foot-operated mortar and pestle",
            "멍석": "woven straw mat spread under the sun with dried red peppers",

            # 실내 및 가옥 정경
            "호롱불": "warm glowing kerosene lamp, soft flicker in rustic room",
            "등불": "warm hanging lantern light casting gentle shadows",
            "베틀": "traditional wooden weaving loom with cotton threads",
            "물레": "wooden spinning wheel with fine thread silhouette",
            "대청": "traditional Korean wooden veranda, daecheongmaru with warm wood grain",
            "대청마루": "traditional wooden floor, daecheongmaru under soft daylight",
            "툇마루": "peaceful wooden porch of hanok, toetmaru with warm afternoon sunlight",
            "토방": "rustic clay house porch, earthen courtyard with stepping stone",
            "마당": "peaceful rustic courtyard with warm country sunlight",
            "골목": "nostalgic rustic village alleyway, quiet dirt path",
            "돌담": "traditional stone wall overgrown with subtle green moss and ivy",
            "장독대": "traditional Korean earthenware jars (jangdokdae) glistening in the morning light",
            "기와": "traditional curved tile hanok roof with mossy textures",
            "초가": "thatched roof cottage in tranquil rural village",
            "창문": "traditional paper sliding window, hanji door glowing with sunlight",
            "문살": "wooden lattice hanji door pattern with soft filtered light",
            "처마": "curved traditional eaves with hanging persimmons and gentle shadows",
            "감나무": "persimmon tree laden with bright orange ripe fruits against clear sky",

            # 자연, 갯가 및 토속 서정 정경
            "따순굼턱": "innocent Korean rural children huddled happily at the foot of a sunny, warm earthen mound and hillside that shelters from cold winter wind, playing house in the bright sunlight",
            "굼턱": "warm sunlit earthen mound and sheltered hillside slope, blocking cold winds",
            "빠끔살이": "nostalgic rural Korean children huddled warmly under a sunny earthen mound, playing make-believe house with smooth pebbles, abalone and sea snail shells using little mud-stained hands",
            "소꿉놀이": "sweet innocent village children sitting together on dry ground under a sunny earthen mound, playing house with smooth pebbles and shells in warm sunlight",
            "갱본": "peaceful rustic seashore pebble beach and coastal tide margin",
            "소라": "weathered sea snail shells used as humble play dishes on the ground",
            "전복": "smooth rustic abalone shells glistening on sunlit soil",
            "몽돌": "smooth rounded seashore pebbles, wet stones glistening softly in sunlight",
            "도랑": "small clear countryside brook with fresh water and gentle ripples",
            "흙": "soft warm countryside earth and dry soil in afternoon light",
            "검불": "delicate dried grass blades and fallen twigs scattered on dirt",
            "쑥": "tender green wild mugwort sprouts peeking through spring ground",
            "노을": "warm golden sunset, crimson evening glow across the hills",
            "석양": "warm golden hour sunset glow, serene long shadows",
            "새벽": "quiet dawn mist, faint morning twilight over the village",
            "아침": "serene morning sunlight, gentle fresh breeze, clear light",
            "달빛": "soft silver moonlight, tranquil night sky over tiled roofs",
            "밤하늘": "deep indigo night sky with faint shimmering stars",
            "바다": "calm nostalgic ocean coastline, tranquil horizon",
            "파도": "gentle rhythmic shoreline waves with white foam",
            "갈대": "swaying reed grass in the autumn breeze",
            "억새": "golden silver grass fields glowing under autumn light",
            "봄": "gentle spring breeze, subtle wild blossom petals",
            "여름": "lush green summer leaves, quiet warmth and cool shade",
            "가을": "crisp autumn foliage, warm amber light, fallen dry leaves",
            "겨울": "peaceful winter stillness, cool soft light, pristine calm",
            "눈": "pure white falling snow, pristine quietude on rooftops",
            "비": "gentle mist rain, soft raindrops rippling on puddles",

            # 정서 및 인물
            "어머니": "tender nostalgic maternal warmth, loving shadow",
            "아버지": "warm paternal presence, quiet dignified silhouette",
            "할머니": "grandmother's gentle warmth, wrinkled loving hands",
            "이웃": "warm neighborhood neighborly sharing and kindness"
        }

        combined_text = f"{title} {poem_body} {core_memory} {sensory_details}".lower()
        extracted_elements = []
        for kw, en_desc in keyword_mappings.items():
            if kw in combined_text:
                extracted_elements.append(en_desc)

        if extracted_elements:
            seen = set()
            unique_elements = []
            for elem in extracted_elements:
                if elem not in seen:
                    seen.add(elem)
                    unique_elements.append(elem)
            scene_motif = ", ".join(unique_elements[:4])
        else:
            scene_motif = f"nostalgic Korean rustic scene of {title}, peaceful emotional mood"

        # [스마트 다이어트] 핵심 화풍을 간결하고 강력한 시그니처 스타일로 정돈
        # 이미지 AI(SDXL, FLUX, Gemini 등)는 앞쪽 20단어에 가장 강하게 집중하므로,
        # 수십 줄의 미사여구와 부정어(no text...)를 전면 제거하고 핵심 장면 + 서정 수채화 터치만 간결하게 조립합니다.
        style_key = (art_style or "watercolor").lower()
        if "수묵" in style_key or "ink" in style_key:
            base_style_prefix = "Korean sumuk ink and wash painting"
            base_style_suffix = "expressive brushwork on traditional hanji paper, serene meditative empty space"
        elif "파스텔" in style_key or "pastel" in style_key:
            base_style_prefix = "Heartwarming storybook illustration"
            base_style_suffix = "soft dreamy colored pencil texture, warm nostalgic childhood mood, gentle airy space"
        elif "만화" in style_key or "스케치" in style_key or "sketch" in style_key:
            base_style_prefix = "Delicate lyrical manga sketch illustration"
            base_style_suffix = "fine pen and ink lines, subtle warm watercolor wash, nostalgic slice-of-life graphic novel aesthetic"
        else:
            # 기본이자 가장 완성도 높은 [서정 투명 수채화]
            base_style_prefix = "Delicate Korean lyric watercolor illustration"
            base_style_suffix = "warm nostalgic morning sunlight, soft translucent washes, peaceful poetic negative space, textured white paper"

        guide_phrase = ""
        if custom_guide:
            cg = custom_guide.strip()
            guide_mappings = {
                "인물 제외": "pure tranquil landscape, no people",
                "풍경만": "serene uninhabited nature scenery",
                "인물 뒷모습": "quiet nostalgic silhouette seen from behind",
                "노을": "warm golden sunset glow",
                "정물": "intimate poetic still life close-up",
                "클로즈업": "tender close-up perspective",
                "안개": "dreamy morning mist",
                "여백": "vast tranquil empty space"
            }
            matched_guides = [v for k, v in guide_mappings.items() if k in cg]
            if matched_guides:
                guide_phrase = ", " + ", ".join(matched_guides)
            else:
                guide_phrase = f", {cg}"

        # [골든 프롬프트]: 핵심 모티프 최우선 + 화풍 디테일 + 공통 10% 페이드아웃 여백 & 300 DPI
        final_prompt = (
            f"{base_style_prefix} of {scene_motif}{guide_phrase}, {base_style_suffix}, "
            "soft vignette fading into pure paper margin, 300 dpi"
        )
        return final_prompt

    def generate_art_prompt_with_gemini(
        self,
        title: str,
        poem_body: str,
        core_memory: str = "",
        sensory_details: str = "",
        style_mode: str = "literal",
        art_style: str = "watercolor",
        custom_guide: str = "",
        api_key: Optional[str] = None,
        reference_image_bytes: Optional[bytes] = None
    ) -> str:
        """
        Gemini 모델을 활용하여 시의 본질과 참조 사진(있을 경우)의 구도/피사체를 
        정밀 시각 분석하고 최적의 300DPI 출판용 서정 삽화 프롬프트를 생성합니다.
        실패하거나 키가 없을 경우 내장 규칙 기반(Fallback) 엔진으로 안전하게 전환됩니다.
        """
        import os
        import io
        from PIL import Image

        key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not key:
            base = self.generate_art_prompt_from_poem(
                title=title, poem_body=poem_body, core_memory=core_memory,
                sensory_details=sensory_details, style_mode=style_mode,
                art_style=art_style, custom_guide=custom_guide
            )
            if reference_image_bytes:
                base = f"{base}, faithful to the composition of user's reference photo"
            return base

        try:
            from google import genai
            client = genai.Client(api_key=key)

            # 스타일 정의
            style_desc_map = {
                "watercolor": "Delicate Korean lyric transparent watercolor illustration, soft translucent washes, warm morning light, gentle paper texture",
                "ink_wash": "Traditional Korean sumuk ink and wash painting, subtle expressive brushstrokes on textured hanji paper, meditative empty space",
                "pastel": "Heartwarming storybook illustration, soft colored pencil and pastel crayon textures, warm nostalgic childhood memory",
                "sketch": "Delicate lyrical manga sketch illustration with fine pen and ink lines, light earthy watercolor wash, gentle nostalgic slice-of-life aesthetic",
                "oil_painting": "Rich impressionistic Korean oil painting, warm layered palette knife strokes"
            }
            art_style_str = style_desc_map.get(art_style, style_desc_map["watercolor"])
            mode_desc = "Intimate evocative still life and tranquil focus" if style_mode == "atmospheric" else "Detailed heartwarming rural landscape and rustic nostalgic context"

            system_instruction = (
                "You are an expert art director and visual prompter for traditional Korean lyric poetry books. "
                "Analyze the provided Korean poem, title, memory, and any attached REFERENCE IMAGE, and craft a single concise, high-impact English image generation prompt (1-2 sentences). "
                "CRITICAL: Carefully interpret Korean dialects, folklore, and childhood motifs: "
                "- '따순굼턱' / '굼턱' means a cozy, sunlit earthen mound and sheltered hillside slope that blocks chilly winter winds—NEVER a dark cave, underground hole, tunnel, house, cabin, or cottage. It is an open, sunny outdoor spot at the foot of a protective earthen embankment. "
                "- '빠끔살이' is the nostalgic traditional Korean dialect for sweet innocent children playing house together (소꿉놀이). When the poem describes 따순굼턱 or 빠끔살이, ALWAYS depict innocent Korean rural children (동무들) huddled warmly together on the dry ground at the sunny foot of the protective earthen mound, cheerfully playing house with smooth seashore pebbles ('몽돌'), abalone and sea snail shells ('소라/전복 껍데기'), and little twigs in the bright warm sunshine using mud-stained small hands. Do NOT leave out the children! Do NOT draw dark caves or holes. "
                "- '갱본' means rustic seashore or pebble beach margin where children collected shells. "
                "- IF A REFERENCE IMAGE IS ATTACHED: Strictly analyze its actual visual composition, object arrangement, perspective, and lighting, and describe the scene recreating the reference photo's layout into the desired artistic watercolor/ink-wash style! "
                "- Focus on the concrete, authentic Korean subject (e.g., if the poem is about acorn jelly '도토리묵', describe neatly sliced brown acorn jelly in a rustic dish; if about children's memory, depict the heartwarming children). "
                "MANDATORY PUBLISHING STANDARDS: "
                "1) Pure visual artwork only: strictly no letters, words, hangul, hanja, calligraphy, signatures, artist seals, frames, borders, or cabins. "
                "2) Soft 12% edge fade: ensure the prompt specifies 'soft vignette fading into pure paper margin' so the outer edges fade seamlessly into the book page with zero rectangular borders. "
                "3) Vertical portrait orientation (3:4 tall aspect ratio). "
                "4) Always append '300 dpi' at the end. "
                "Output ONLY the English prompt without quotes, markdown, or greetings."
            )

            ref_note = "A reference photograph is attached. Faithfully reflect its composition, layout, and subject placement in the prompt." if reference_image_bytes else "No reference image attached."

            prompt_input = (
                f"Poem Title: {title}\n"
                f"Poem Content:\n{poem_body}\n"
                f"Core Memory: {core_memory}\n"
                f"Sensory Details: {sensory_details}\n"
                f"Art Style: {art_style_str}\n"
                f"Composition Mode: {mode_desc}\n"
                f"Reference Image Status: {ref_note}\n"
                f"Additional Director's Guide: {custom_guide or 'None'}\n\n"
                "Please compose the optimal English illustration prompt now:"
            )

            content_payload = [system_instruction, prompt_input]
            if reference_image_bytes:
                try:
                    ref_pil = Image.open(io.BytesIO(reference_image_bytes))
                    content_payload.append(ref_pil)
                    print("[Gemini Vision 가동] 사용자가 첨부한 참조 사진/그림을 멀티모달 비전으로 분석합니다.")
                except Exception as img_err:
                    print(f"[참조 이미지 로드 실패, 텍스트 전용으로 진행]: {img_err}")

            active_model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
            response = client.models.generate_content(
                model=active_model,
                contents=content_payload
            )

            if response and response.text:
                result = response.text.strip().strip('"').strip("'")
                result = " ".join([l.strip() for l in result.split("\n") if l.strip()])
                if len(result) > 20:
                    print(f"[{active_model} 스마트 프롬프트 추출 성공]: {result[:80]}...")
                    return result
        except Exception as e:
            print(f"[Gemini 2.5 Flash 프롬프트 추출 실패, 규칙 기반 폴백 전환]: {e}")

        # Gemini 실패 시 로컬 규칙 엔진으로 안전하게 폴백
        fallback_prompt = self.generate_art_prompt_from_poem(
            title=title, poem_body=poem_body, core_memory=core_memory,
            sensory_details=sensory_details, style_mode=style_mode,
            art_style=art_style, custom_guide=custom_guide
        )
        if reference_image_bytes:
            fallback_prompt = f"{fallback_prompt}, based closely on composition of reference photo"
        return fallback_prompt

    def generate_sequel_image_prompt(
        self,
        title: str,
        poem_body: str,
        core_memory: str = "",
        sensory_details: str = "",
        style_mode: str = "literal",
        art_style: str = "watercolor",
        custom_guide: str = ""
    ) -> str:
        """
        4P 연속 조판 2부(후반부)를 위한 연작 서정 삽화 프롬프트 생성.
        시 본문을 분석하여 '후반부'에 등장하는 정경, 시어, 여운을 중심 모티프로 추출하고
        앞선 1부와 화풍 및 정서가 유기적으로 이어지는 연작(companion sequel scene)으로 조립합니다.
        """
        lines = [l.strip() for l in (poem_body or "").split("\n") if l.strip()]
        if len(lines) > 4:
            mid = len(lines) // 2
            part2_lines = lines[mid:]
            part2_text = " ".join(part2_lines)
        else:
            part2_text = poem_body or ""

        combined_text = f"{title} {part2_text} {sensory_details}".lower()

        # 후반부에서 자주 등장하는 서정적 모티프 확장 매핑
        sequel_keywords = {
            "호롱불": "warm flickering kerosene lamp lantern glow, intimate traditional night interior",
            "등 뒤": "looking back into gentle glowing room, tender quiet footsteps",
            "잠자": "peaceful quiet bedroom, warm quilt, deep restful slumber",
            "오강": "traditional Korean room at late midnight, quiet rustic dawn",
            "찬바람": "cold winter night breeze outside traditional paper sliding hanji door",
            "동지섣달": "deep midwinter cold night, quiet rustic Korean room",
            "달": "soft silver moonlight streaming into quiet wooden floor",
            "별": "faint twinkling stars in midnight sky through paper lattice",
            "물레": "wooden spinning wheel silhouette resting quietly in corner",
            "어머니": "maternal warmth, quiet devoted shadow",
            "엄마": "tender maternal memory, gentle lingering warmth",
            "새벽": "quiet blue pre-dawn stillness, peaceful twilight",
            "밤": "deep tranquil Korean rustic night, serene shadows"
        }

        extracted_elements = []
        for kw, desc in sequel_keywords.items():
            if kw in combined_text:
                extracted_elements.append(desc)

        sequel_motif = ", ".join(extracted_elements[:4]) if extracted_elements else "quiet poetic aftermath, serene night atmosphere"
        sequel_guide = f"companion sequel continuation scene of '{title}', intimate lingering stillness, {custom_guide}".strip(", ")

        return self.generate_art_prompt_from_poem(
            title=f"{title} (연작 2부)",
            poem_body=part2_text,
            core_memory=core_memory,
            sensory_details=sequel_motif,
            style_mode=style_mode,
            art_style=art_style,
            custom_guide=sequel_guide
        )

    def generate_korean_art_prompt(
        self,
        title: str,
        poem_body: str,
        core_memory: str = "",
        sensory_details: str = "",
        style_mode: str = "literal",
        art_style: str = "watercolor",
        custom_guide: str = "",
        api_key: Optional[str] = None
    ) -> str:
        """
        사용자가 화면에서 직관적으로 읽고 직접 편집할 수 있는
        고품격 한국어 서정 삽화 연출 프롬프트 생성 (Gemini 지능형 연동)
        """
        import os
        key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        style_name_map = {
            "watercolor": "한국 정통 서정 투명 수채화",
            "ink_wash": "한국 전통 먹빛 수묵담채화",
            "pastel": "포근하고 따스한 파스텔 동화 삽화",
            "sketch": "서정적인 펜화 및 연필 드로잉 스케치",
            "oil_painting": "따뜻한 질감의 서정 유화"
        }
        chosen_style = style_name_map.get(art_style, "한국 정통 서정 수채화")

        if key:
            try:
                from google import genai
                client = genai.Client(api_key=key)
                prompt_sys = (
                    "당신은 한국 대표 시화집의 최고 아트 디렉터입니다. "
                    "주어진 시의 제목, 본문, 기억 데이터를 분석하여 이미지 생성 AI가 그릴 "
                    "한국어 서정 삽화 연출 프롬프트 1~2문장을 작성하세요.\n"
                    "핵심 원칙:\n"
                    "1. 토속어/방언의 진정한 정서를 완벽히 살리세요:\n"
                    "   - '따순굼턱': 어두운 굴(동굴)이나 땅구멍이 절대 아닙니다! 찬 바람을 막아주는 양지바른 언덕 비탈 밑의 아늑한 '흙 둔덕'입니다. 북풍을 막아주는 흙 둔덕 아래 따스한 햇볕이 쏟아지는 야외 흙터입니다.\n"
                    "   - '빠끔살이': 그 양지바른 흙 둔덕 아래에서 순박한 시골 아이들(동무들) 3~4명이 옹기종기 모여 앉아 조약돌(몽돌)과 소라·전복 껍데기, 풀잎으로 소꿉놀이를 하는 천진난만하고 따스한 유년의 정경. 결코 아이들을 빼놓지 마세요.\n"
                    "   - '도토리묵': 시골 툇마루나 소반 위 투박한 질그릇에 정갈하게 담긴 도토리묵과 막걸리 사발.\n"
                    "2. 스타일: 3:4 세로형 구도, 외곽 10% 순백 종이 여백 페이드아웃, 글자/낙관 배제.\n"
                    "3. 오직 1~2문장의 간결하고 아름다운 한국어 연출 지시문만 출력하세요 (설명이나 따옴표 없이)."
                )
                user_msg = f"시 제목: {title}\n시 본문:\n{poem_body}\n기억: {core_memory}\n화풍: {chosen_style}\n추가연출: {custom_guide or '없음'}"
                res = client.models.generate_content(
                    model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
                    contents=[prompt_sys, user_msg]
                )
                if res and res.text:
                    out = res.text.strip().strip('"').strip("'")
                    if len(out) > 15:
                        return out
            except Exception as e:
                print(f"[한국어 프롬프트 Gemini 생성 실패, 규칙 기반 전환]: {e}")

        # 로컬 규칙 기반 한국어 프롬프트 fallback
        combined = f"{title} {poem_body} {core_memory}"
        motif_desc = "고향의 따스한 풍경"
        if "따순굼턱" in combined or "굼턱" in combined or "빠끔살이" in combined:
            motif_desc = "찬 바람을 막아주는 양지바른 비탈 밑 아늑한 흙 둔덕 아래에서 순박한 시골 어린아이들이 옹기종기 모여 조약돌과 소라·전복 껍데기로 소꿉놀이를 하는 정겨운 유년의 기억"
        elif "도토리묵" in combined or "도토리 묵" in combined:
            motif_desc = "시골 툇마루 위 투박한 질그릇에 정갈하게 썰어 담은 도토리묵과 양념간장, 막걸리 사발이 놓인 단아한 정경"
        elif "장독대" in combined:
            motif_desc = "아침 햇살이 비치는 시골 뒤뜰 장독대와 돌담길"
        elif "억새" in combined or "노을" in combined:
            motif_desc = "붉은 노을빛이 물드는 언덕 위 바람에 흔들리는 은빛 억새밭"

        extra = f", 추가 연출: {custom_guide}" if custom_guide else ""
        return f"{chosen_style}, {motif_desc}{extra}, 3:4 세로형 구도, 순백의 종이와 자연스럽게 어우러지는 부드러운 여백, 글자나 낙관 없음"

    def get_image_generation_instruction_ko(
        self,
        title: str,
        poem_body: str,
        art_style: str = "watercolor",
        custom_guide: str = ""
    ) -> str:
        """
        외부 이미지 AI(ChatGPT DALL-E, Midjourney, 워크플로 등)에 그대로 전달할 수 있는
        '흰색 종이 10% 여백 & 단일 장면 수채화' 전문 한글 지시문 생성
        """
        style_name = "전통 투명 수채화"
        style_desc = (
            "실제 화가가 흰색 수채화 종이 위에 직접 붓으로 그린 듯한 전통적인 투명 수채화 작품으로 표현해줘.\n"
            "- 맑고 투명한 색의 겹침, 물감의 자연스러운 번짐, 부드럽고 불규칙한 붓 터치, 종이의 미세한 질감이 살아 있어야 해.\n"
            "- 습식 수채화(Wet-on-Wet)와 마른 붓(Dry Brush) 기법을 자연스럽게 활용하고, 가까운 사물은 비교적 선명하게, 먼 풍경은 은은하고 부드럽게 표현해줘.\n"
            "- 사진이나 디지털 일러스트처럼 지나치게 정교하지 않고, 사람이 직접 그린 듯한 따뜻하고 담백한 손그림 느낌을 유지해줘."
        )

        if "수묵" in art_style:
            style_name = "전통 한국 수묵담채화"
            style_desc = (
                "전통 한지 위에 먹선과 은은한 천연 담채 물감으로 그린 한국 수묵담채화로 표현해줘.\n"
                "- 유려한 먹물 번짐과 맑은 담채의 조화, 거친 한지의 섬유 질감이 은은하게 드러나야 해.\n"
                "- 절제된 붓질과 깊이 있는 여백의 미(餘白의 美)를 살려줘."
            )
        elif "파스텔" in art_style:
            style_name = "포근한 파스텔 동화 삽화"
            style_desc = (
                "부드러운 크레용과 색연필, 소프트 파스텔 질감이 살아있는 따스한 동화풍 그림으로 표현해줘.\n"
                "- 포근하고 몽환적인 감성, 어린 시절 동화책의 따뜻한 손그림 질감을 유지해줘."
            )
        elif "스케치" in art_style or "만화" in art_style:
            style_name = "서정적 펜&연필 스케치"
            style_desc = (
                "정감 있는 연필 드로잉과 펜선, 은은한 담채가 어우러진 서정적인 스케치 일러스트로 표현해줘.\n"
                "- 정갈한 손그림 선화와 담백하고 따뜻한 여운을 살려줘."
            )
        elif "유화" in art_style:
            style_name = "서정적 인상주의 유화"
            style_desc = (
                "빛의 떨림과 부드러운 유화 나이프/붓 터치가 돋보이는 서정적 인상파 회화로 표현해줘.\n"
                "- 따뜻한 질감과 서정적인 색채의 조화를 흰색 캔버스 여백과 함께 살려줘."
            )

        guide_note = f"\n- 추가 연출 희망사항: {custom_guide.strip()}" if custom_guide and custom_guide.strip() else ""

        return f"""**[시화 이미지 생성 지시문]**

제목: {title}
본문:
{poem_body}

위에 작성된 시의 제목과 본문을 읽고, 시의 주제와 중심 정서, 핵심 소재, 시간, 장소, 계절을 분석하여 시의 분위기에 가장 잘 어울리는 이미지를 생성해줘.

시의 모든 내용을 한 장에 담으려 하지 말고, 시의 마음을 가장 잘 전달할 수 있는 **하나의 인상적인 장면**을 선택해 그림으로 표현해줘.
시 속에 등장하는 인물, 사물, 장소, 자연환경을 중심으로 구성하고, 시에 없는 사건이나 불필요한 장식은 추가하지 마.
인물은 필요한 경우에만 등장시키고, 시의 분위기에 따라 뒷모습이나 옆모습, 자연스러운 행동으로 감정을 표현해줘.{guide_note}

**[{style_name} 스타일 — 고정]**
{style_desc}

**[흰색 종이와 여백 — 반드시 적용]**
- 전체 이미지는 깨끗한 순백색 종이 위에 그려줘.
- **상하좌우 각각 전체 화면 크기의 약 10%를 흰색 종이 여백으로 남겨줘.**
- 그림의 가장자리는 직선이나 사각형으로 자르지 말고, 물감이 종이 위에서 자연스럽게 번지고 스며들며 불규칙하게 사라지는 비네팅(Vignette) 형태로 표현해줘.
- 가장자리에는 연한 물감 자국과 투명한 붓 터치가 자연스럽게 남아 있어도 좋아.
- 그림 중심부는 비교적 선명하게 유지하고, 바깥쪽으로 갈수록 색이 옅어지면서 흰색 종이와 부드럽게 연결되도록 해줘.
- 흰색 여백에는 물감이 과도하게 번지지 않도록 하고, 종이 본연의 깨끗한 흰색을 충분히 살려줘.

**[이미지 구성]**
- 세로형 3:4 비율
- 시의 핵심 장면 중심 구성
- 자연스러운 원근감과 공간감
- 시의 정서에 어울리는 빛과 색채
- 과장되지 않은 인물과 풍경
- 여백이 살아 있는 서정적인 시화 작품

**[절대 금지 — 엄격 준수]**
- **이미지 안에는 어떠한 글자도 절대 넣지 마.** (한글, 영어, 숫자, 시 제목, 시 구절, 서명, 낙관, 도장, 간판 글씨, 로고, 워터마크 등 모든 문자 제외)
- 인위적인 액자, 테두리, 사각형 경계, 3D 렌더링, 사진 합성, 과장된 만화풍 표현도 사용하지 마.

**[최종 요청]**
위 시의 정서와 이야기를 가장 잘 표현하는 한 장의 수채화 이미지를 바로 생성해줘.
흰색 종이 위에 사람이 직접 그린 듯한 화풍과 **상하좌우 10% 여백, 자연스러운 물감 번짐 효과는 반드시 동일하게 유지해줘.**
글자가 전혀 없는 순수 회화 작품으로 완성해줘."""


    def get_external_ai_prompt(
        self,
        core_memory: str,
        sensory_details: str,
        spoken_words: Optional[str] = None,
        book_title: str = "시화집"
    ) -> str:
        """외부 무료 AI(ChatGPT, Claude, 뤼튼 등)에 붙여넣을 전문 서정시 창작 메가 프롬프트 생성"""
        core = self._clean(core_memory) or "유년 시절의 애틋한 기억"
        sensory = self._clean(sensory_details) or "차디찬 바람과 호롱불의 온기"
        spoken = f'"{self._clean(spoken_words)}"' if spoken_words else "침묵 속에 남은 온기"

        return f"""[역할 정의]
당신은 백석, 박목월, 정지용의 서정성과 담담한 정경 묘사를 계승한 대한민국 대표 서정 시인입니다.
독립출판 시화집 『{book_title}』에 수록될 원고 1편을 아래 구술 기억을 바탕으로 정제된 한국어 서정시로 창작해 주세요.

[창작 제약 원칙]
1. 진실성: 제공된 기억의 사실과 정경에 충실하되, 억지 교훈이나 작위적인 슬픔은 철저히 배제합니다.
2. 문체: 담담한 정경 묘사 뒤에 잔잔한 여운이 남도록 어미(~하네, ~했었지, ~이어라)를 조화롭게 빚어냅니다.
3. 분량: 3~4연 구성, 각 연 3~4행의 정갈한 호흡.

[제공된 기억 데이터]
- 기억의 중심: {core}
- 구체적 사물과 감각: {sensory}
- 귓가에 맴도는 말/소리: {spoken}

[출력 양식]
1. 시 제목: (상투적이지 않은 서정적 제목)
2. 시 본문: (연과 행이 정돈된 시 전문)
3. 시인의 한마디: (시의 모티프가 된 기억의 아름다움을 1문장으로 요약)"""

    def generate_song_lyrics(
        self,
        title: str,
        poem_body: str,
        genre: str = "minyo"
    ) -> Dict[str, Any]:
        """시 본문을 바탕으로 음악적 기승전결(Intro, Verse, Chorus, Outro)을 갖춘 노래 가사를 생성합니다."""
        lines = [line.strip() for line in poem_body.strip().split("\n") if line.strip()]
        if not lines:
            lines = [f"{title}의 푸른 기억", "바람이 불어오는 언덕 위에서", "그리운 얼굴 떠올려 보네"]

        genre_flavors = {
            "minyo": {
                "name": "서정 민요풍 (국악/세마치)",
                "hook": "(얼씨구 지화자 좋네 / 아련한 바람결 따라)",
                "outro_phrase": "세월은 흘러 흘러 강물로 가네 (얼쑤 / 잔잔한 가야금 여운과 함께 페이드아웃)",
                "style_prompt": "Korean traditional lyrical folk song, acoustic gayageum and bamboo daegeum flute, subtle haegum, emotional warm vocal, sorrowful yet uplifting Korean minyo style, traditional janggu percussion, warm acoustic sound, 75 bpm"
            },
            "folk": {
                "name": "통기타 어쿠스틱 포크",
                "hook": "(라라라 라라라 바람 속에 흩어지는 / 그 시절의 우리 이야기)",
                "outro_phrase": "기타 줄에 얹어 부르는 나의 노래여 (조용한 기타 독주와 함께 서서히 페이드아웃)",
                "style_prompt": "Korean warm acoustic folk song, delicate nylon acoustic guitar fingerpicking, soft upright piano, intimate emotional vocals, warm 1970s 1980s nostalgic storytelling, peaceful lyrical atmosphere, 78 bpm, warm analog sound"
            },
            "gagok": {
                "name": "한국 현대 서정 가곡",
                "hook": "(아, 가슴 깊이 차오르는 그리움이여 / 바람결에 흩날리는 푸른 별빛처럼)",
                "outro_phrase": "영원히 지지 않는 꽃잎이 되리라 (장엄하고 온화한 피아노 화음과 함께 페이드아웃)",
                "style_prompt": "Korean classical art song, elegant gagok style, expressive concert grand piano, warm cello counter-melody, graceful lyrical classical vocal, poetic and dramatic resonance, majestic and tender emotion, 72 bpm"
            },
            "dongyo": {
                "name": "서정 동요 (동심/회상)",
                "hook": "(반짝반짝 작은 별처럼 / 내 마음속에 피어나는 고운 꿈망울)",
                "outro_phrase": "엄마 품처럼 따스한 꿈속으로 (맑은 글로켄슈필 잔향과 함께 서서히 페이드아웃)",
                "style_prompt": "Korean lyrical children song, nostalgic dongyo, pure innocent vocal, bright glockenspiel bells, gentle acoustic piano, soft acoustic guitar, warm heartwarming childhood melody, peaceful and tender, 82 bpm"
            },
            "ballad": {
                "name": "감성 발라드",
                "hook": "(지울 수 없는 그 기억을 안고 / 가슴 시린 바람결 따라)",
                "outro_phrase": "다시 돌아갈 수 없는 그날의 우리 (스트링 콰르텟과 함께 페이드아웃)",
                "style_prompt": "Korean emotional acoustic ballad, delicate piano melody, tender string quartet, heartfelt warm vocal, nostalgic and cinematic soundscape, 70 bpm"
            }
        }
        flavor = genre_flavors.get(genre, genre_flavors["minyo"])

        v1 = lines[:min(len(lines), 3)]
        v2 = lines[min(len(lines), 3):min(len(lines), 6)] if len(lines) > 3 else lines[:2]
        chorus = [
            f"마음 한구석에 피어난 {title}",
            flavor["hook"],
            "잊지 못할 그 시절의 노래가 되어"
        ]

        lyrics_sections = [
            f"[Intro - {flavor['name']}]",
            "(잔잔한 선율과 함께 아련하게 시작)",
            "",
            "[Verse 1]",
            "\n".join(v1),
            "",
            "[Chorus]",
            "\n".join(chorus),
            "",
            "[Verse 2]",
            "\n".join(v2),
            "",
            "[Chorus]",
            "\n".join(chorus),
            "",
            "[Outro - Fade Out]",
            flavor["outro_phrase"],
            "(서서히 페이드아웃)"
        ]

        full_lyrics = "\n".join(lyrics_sections)
        return {
            "title": f"{title} ({flavor['name']})",
            "genre": genre,
            "genre_name": flavor["name"],
            "music_prompt": flavor.get("style_prompt", ""),
            "lyrics": full_lyrics
        }


poetic_engine = PoeticEngine()
