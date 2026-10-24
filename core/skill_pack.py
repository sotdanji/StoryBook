# -*- coding: utf-8 -*-
"""
core/skill_pack.py
StoryBook Studio - AI 에이전트 스킬팩(Skill Pack) 통합 로더 모듈

.agents/skills/ 에 정립된 13종의 전문 지침을 파이썬 런타임에서 즉시 로드하여,
Gemini API (google.genai) 호출 시 `system_instruction`으로 주입해 주는 중추 엔진입니다.

[지원 스킬 체계]
1. 문학 스킬 (3종):
   - poetic-interview: 기억 발굴 심층 인터뷰
   - poetic-composition: 한국 정통 서정 작시
   - poetic-refinement: 시적 퇴고 및 윤문

2. 화풍 스킬 (5종):
   - art-style-common: 출판 삽화 공통 규격 (10% 소프트 비네트, 300 DPI, 순백 융합, 텍스트 배제)
   - art-style-ink-wash: 한국 전통 먹빛 수묵담채
   - art-style-watercolor: 한국 정통 서정 투명 수채화
   - art-style-pastel: 따스한 파스텔 동화
   - art-style-sketch: 서정 만화 펜화 & 연필 스케치

3. 음악 스킬 (5종):
   - music-genre-common: 시화집 음원 공통 표준 (Suno/YuE 메타태그, 70~85 BPM, 룸 어쿠스틱)
   - music-genre-gagok: 한국 서정 예술 가곡
   - music-genre-dongyo: 서정 동요/동심
   - music-genre-folk: 어쿠스틱 포크
   - music-genre-minyo: 남도/경기 서정 민요
"""

from typing import Dict, Any, Optional

# ==============================================================================
# 1. 문학 스킬 시스템 지침 (Literature Skills)
# ==============================================================================

SKILL_POETIC_INTERVIEW = """
You are a warm, deeply empathetic literary interviewer and poet mentor for traditional Korean lyric poetry.
Your mission is to help the user unearth hidden, precious memories from their past and discover the "poetic seeds" for a timeless Korean lyric poem.

STRICT INTERVIEW PRINCIPLES:
1. Empathy First: Always begin your response by warmly acknowledging and validating the emotional essence of the user's memory in 1-2 lyrical, gentle Korean sentences.
2. Ban Abstract Emotion Questions: NEVER ask abstract questions like "기분이 어떠셨나요?" or "행복하셨나요?".
3. Focus on Concrete Senses & Objects: Ask about specific textures, sounds, rustic smells, weather, fading light, and everyday physical objects (e.g., 문풍지, 놋숟가락, 무명 앞치마, 찌그러진 주전자, 몽돌).
4. Uncover the Voice: Ask what specific words or phrases (in native Korean dialect if any) were spoken in that exact moment.
5. Limit to 1-2 Evocative Questions at a time so the user does not feel overwhelmed.
6. Language: Pure, gentle, respectful Korean (존댓말, 따스하고 품격 있는 문체).
""".strip()

SKILL_POETIC_COMPOSITION = """
You are a master Korean lyric poet, inheriting the deep literary traditions of Jeong Ji-yong, Baek Seok, and Park Mok-wol.
Your task is to transform the user's personal memory, sensory details, and interview fragments into a breathtaking, publication-grade Korean lyric poem.

MANDATORY POETIC RULES:
1. Strict Emotional Restraint: NEVER use direct emotional adjectives like "슬프다", "행복하다", "그립다", "외롭다". Show the emotion purely through concrete physical objects, rustic textures, sounds, and fading natural light (Objective Correlative).
2. Rhythm & Brevity: Use concise lines (typically 2 to 4 poetic words per line). Structure the poem into 3-4 distinct stanzas (기-승-전-결: Scene setting -> Sensory deepening -> Echoing voice/turning point -> Quiet contemplation).
3. Poetic Korean Endings: Avoid prose endings like "~했다", "~한다". Use rich lyrical endings (~하네, ~했었지, ~이던가, ~이어라, or ending with a resonant noun).
4. Preserve Dialect & Authentic Voice: Keep the user's authentic local dialect, childhood nicknames, or spoken phrases intact as vital poetic anchors.
5. Title: Create an evocative, deeply lyrical title (2-4 Korean words).
6. Output Format:
   [제목: ...]
   (본문: 3~4연의 시)
""".strip()

SKILL_POETIC_REFINEMENT = """
You are a meticulous poetry editor and master of Korean lyricism.
Your task is to refine and elevate a draft poem into an exquisite, publication-ready masterpiece while strictly preserving the author's original soul, memories, and intended emotion.

REFINEMENT PROTOCOL:
1. Strip Clichés: Eliminate trite, sentimental clichés (e.g., "눈부신", "따스한", "슬픈 눈물", "아름다운 사랑"). Replace them with grounded, visceral textures and vivid imagery.
2. Prune Connectors & Particles: Delete narrative conjunctions ("그리고", "그러나", "하지만") and redundant particles ("~의", "~을/를") to sharpen poetic tension.
3. Poetic Word Choice: Substitute flat everyday prose with evocative, sensory Korean terms (참신한 고유어, 감각적 시어).
4. Maintain Brevity & Rhythm: Ensure clean line breaks and lyrical cadences that roll off the tongue naturally when read aloud.
5. Provide Brief Editor's Commentary: After presenting the refined poem, add a concise 2-3 bullet explanation highlighting key improvements (e.g., which clichés were removed, how sensory imagery was enhanced).
""".strip()


# ==============================================================================
# 2. 화풍 스킬 규격 및 지침 (Art Style Skills)
# ==============================================================================

ART_STYLE_COMMON_RULES = """
MANDATORY PUBLISHING STANDARDS FOR ALL ILLUSTRATIONS:
1. Subtle 5% Edge Vignette Margin: The outer 5% edge fades gently into pure white paper to eliminate hard rectangular borders, while preserving 95% of the central canvas with full detail and richness.
2. Pure Artwork Only: ABSOLUTELY NO letters, words, typography, Korean Hangul, Chinese Hanja, signature, artist stamp, seal, frames, or borders.
3. High Resolution: Always append '300 dpi, publication quality, masterpiece'.
4. Aspect Ratio: Vertical portrait orientation (3:4 or 4:5 tall aspect ratio for poetry book pages).
""".strip()

ART_STYLE_PROMPTS = {
    "watercolor": {
        "name": "한국 정통 서정 수채화 (Transparent Watercolor)",
        "prefix": (
            "Delicate Korean lyric transparent watercolor illustration, masterfully rendered wet-on-wet watercolor washes, "
            "clear luminous glazing, gentle warm morning sunlight, natural authentic cold-press watercolor paper texture"
        ),
        "guidance": (
            "Emphasize the clean transparency of water, delicate gradients, and warmth. "
            "Depict rustic Korean rural landscapes, quiet courtyards, earthen walls, and nostalgic natural elements."
        ),
        "negative": "oil paint, heavy impasto, harsh black outlines, neon digital colors, 3D render, dark muddy shading, text, frame"
    },
    "ink_wash": {
        "name": "전통 먹빛 수묵담채화 (Ink & Wash Painting)",
        "prefix": (
            "Authentic East Asian sumuk monochrome black ink wash painting, traditional sumi-e aesthetic, "
            "95% black charcoal ink wash and monochrome nongdam gradients, stark black calligraphy ink brushstrokes, "
            "raw fibrous handmade Korean hanji mulberry paper texture, strictly NO colorful red or orange paint, "
            "strictly NO vibrant autumn foliage colors, only subtle pale tea wash tint, "
            "meditative empty space, NOT watercolor, NO western watercolor washes"
        ),
        "guidance": (
            "Focus on philosophical serenity, flowing calligraphic black ink strokes, misty mountains, solitary trees, quiet pavilions, and the beauty of void. Strictly avoid vibrant autumn colors or western full-color watercolor."
        ),
        "negative": "Western watercolor, colorful red orange yellow washes, colorful autumn trees, colorful paint, oil paint, glossy digital illustration, neon colors, heavy acrylic, geometric lines, 3D, text, seal, stamp, calligraphy, frame"
    },
    "pastel": {
        "name": "포근한 파스텔 동화 (Pastel Storybook)",
        "prefix": (
            "Heartwarming fairytale children's storybook illustration, distinct powdery soft chalk pastel and heavy colored pencil crayon textures, "
            "visible chalk dust and wax pencil strokes on rough drawing craft paper, cozy warm golden fairy tale glow, "
            "sweet nostalgic childhood aesthetic, NOT watercolor, NO transparent water washes"
        ),
        "guidance": (
            "Infuse warmth, innocence, and wonder with tactile powdery pastel textures and colored pencil lines. Strictly avoid wet watercolor washes."
        ),
        "negative": "watercolor, watery transparent wash, dark grotesque mood, sharp metallic outlines, photorealism, glossy plastic texture, text, watermark, frame"
    },
    "sketch": {
        "name": "서정 만화 펜화 & 스케치 (Manga Sketch & Drawing)",
        "prefix": (
            "Lyrical slice-of-life manga sketch drawing, prominent black dip-pen ink contour linework, "
            "meticulous graphite pencil cross-hatching shading, very subtle muted watercolor tint wash, "
            "Ghibli-inspired graphic novel line art, clearly defined hand-drawn ink outlines"
        ),
        "guidance": (
            "Capture intimate details through visible hand-drawn ink outlines and pencil hatching. Ensure clear linear definition."
        ),
        "negative": "action anime, neon cyber colors, thick heavy marker lines, 3D CGI, grotesque deformation, speech bubbles, sound effects, text, frame"
    },
    "oil_painting": {
        "name": "따뜻한 질감의 서정 유화 (Lyrical Impressionist Oil)",
        "prefix": (
            "Lyrical impressionist oil painting, thick textured impasto palette knife strokes, "
            "heavy physical oil paint textures, glowing golden hour light, coarse woven canvas cloth margin, "
            "visible oily brush marks, NOT watercolor"
        ),
        "guidance": (
            "Express the gentle vibration of warm light, tactile palette knife textures, and nostalgic rural tranquility with heavy impasto paint."
        ),
        "negative": "flat digital vector, glossy 3D CGI, watercolor wash, harsh cartoon outlines, neon colors, text, frame"
    }
}


# ==============================================================================
# 3. 음악 장르 스킬 규격 및 지침 (Music Genre Skills) & 다채로운 악기/감성 변주 엔진
# ==============================================================================

import random

MUSIC_COMMON_RULES = """
MUSIC PRODUCTION STANDARDS FOR POETRY SONGS:
1. Metered Lyrics: Adapt the poem's lines into singing cadence (3-4 or 4-4 beat feeling) with structured tags:
   [Intro] -> [Verse 1] -> [Chorus] -> [Verse 2] -> [Chorus] -> [Bridge] -> [Chorus] -> [Outro - Fade Out]
2. Acoustic Room Warmth: Avoid aggressive EDM, heavy synths, autotune, or metallic digital distortion. Keep warm analog room acoustics.
3. Natural Tempo: Maintain a slow to mid tempo (66 - 82 BPM) suitable for deeply contemplative poetry listening.
""".strip()

# [장르별 다채로운 서브스타일 및 악기 조합 풀 (Dynamic Instrument & Mood Variations)]
GENRE_VARIATION_POOLS = {
    "folk": [
        {
            "mood": "애잔하고 쓸쓸한 회상 (Sorrowful Nostalgia)",
            "keywords": ["노을", "저녁", "눈물", "슬픔", "어머니", "고무신", "이별", "떠나", "그리움", "상여"],
            "bpm": "68-72 BPM",
            "instruments": "Fingerstyle Nylon Guitar, Weeping Harmonica, Soft Upright Piano, Subdued Acoustic Cello",
            "vocal": "Heartfelt husky acoustic male or whisper-like sincere female vocal, Kim Kwang-seok style, melancholic intimacy",
            "prompt": "Korean Acoustic Folk Ballad, delicate fingerstyle nylon acoustic guitar, weeping soft harmonica fills, gentle acoustic cello undertones, warm upright piano, nostalgic and bittersweet, 70 BPM, raw analog room acoustic"
        },
        {
            "mood": "따스한 햇살과 봄날의 서정 (Warm & Gentle Breeze)",
            "keywords": ["봄", "햇살", "꽃", "아침", "바람", "미소", "시냇물", "사랑", "초록"],
            "bpm": "74-78 BPM",
            "instruments": "Crisp Steel String Acoustic Guitar, Warm Felt Piano, Gentle Tin Whistle, Subtle Brush Snare",
            "vocal": "Clear, tender, poetic male/female folk vocal, warm smile in voice, soothing storytelling",
            "prompt": "Korean Lyrical Acoustic Folk, warm steel-string acoustic guitar strumming, upright felt piano arpeggios, sweet airy tin whistle, soft brush snare rhythm, peaceful morning warmth, 76 BPM, intimate studio acoustic"
        },
        {
            "mood": "고즈넉한 밤길과 사색 (Quiet Midnight Contemplation)",
            "keywords": ["밤", "달", "별", "어둠", "창문", "고요", "꿈", "기억", "홀로"],
            "bpm": "66-70 BPM",
            "instruments": "12-String Acoustic Guitar, Warm Accordion, Classical Nylon Guitar, Deep Upright Bass",
            "vocal": "Quiet recitative whisper vocal, deep baritone or calm alto, late night poetic introspection",
            "prompt": "Korean Folk Nocturne, rich 12-string acoustic guitar fingerpicking, subtle nostalgic accordion pads, warm wooden upright bass, intimate poetic whisper vocal, calm starry night mood, 68 BPM, warm tape saturation"
        },
        {
            "mood": "정겨운 시골길과 유년의 뜰 (Rural Countryside Memories)",
            "keywords": ["길", "마을", "시골", "고향", "장터", "흙", "들판", "친구", "담장"],
            "bpm": "72-76 BPM",
            "instruments": "Acoustic Guitar, Melodica / Harmonica, Gentle Banjo Fingerstyle, Wooden Shaker, Warm Bass",
            "vocal": "Rustic, warm, honest acoustic folk vocal, Poet and Village (시인과 촌장) aesthetic, gentle sing-along feel",
            "prompt": "Korean Nostalgic Countryside Folk, gentle acoustic guitar arpeggios, sweet melodica counter-melody, warm wooden shaker and acoustic bass, honest sincere folk vocal, heartwarming childhood reminiscence, 74 BPM, cozy wooden cabin room sound"
        }
    ],
    "minyo": [
        {
            "mood": "구슬픈 한(恨)과 애절한 계면조 (Deep Han & Sorrowful Minyo)",
            "keywords": ["노을", "눈물", "슬픔", "어머니", "이별", "통곡", "강물", "상여", "한", "넋"],
            "bpm": "66-70 BPM (Slow Gutgeori rhythm)",
            "instruments": "Deep Mournful Haegeum solo, 12-string Gayageum, Breathy Bamboo Daegum, Subdued Janggu & Buk, Acoustic Cello",
            "vocal": "Soulful traditional Gugak female vocal with emotional Sigimsae vibrato, sorrowful Han, sorrowfully resonant",
            "prompt": "Korean Traditional Lyrical Minyo Ballad, mournful weeping Haegeum solo, deep 12-string Gayageum, breathy low Daegum, gentle slow Gutgeori Janggu rhythm, emotional Gugak female vocal filled with Han, 68 BPM, spacious temple hall reverb"
        },
        {
            "mood": "청아하고 맑은 경기 우조 (Clear & Graceful Gyeonggi Melody)",
            "keywords": ["봄", "꽃", "달", "맑은", "시냇물", "새", "바람", "푸른", "햇살"],
            "bpm": "72-76 BPM (Lyrical Semachi rhythm)",
            "instruments": "Crisp 25-string Gayageum, Clear Bamboo Piri, Resonant Yanggeum (Dulcimer), Semachi Janggu",
            "vocal": "Pure, elegant, crystalline traditional Korean female vocal, light and uplifting Sigimsae, refined courtly grace",
            "prompt": "Korean Gyeonggi Lyrical Minyo, crystalline 25-string Gayageum arpeggios, lyrical Bamboo Piri, sparkling Yanggeum hammer dulcimer, flowing Semachi Janggu pulse, pure clear traditional vocal, 74 BPM, serene nature acoustics"
        },
        {
            "mood": "달빛 아래 국악 크로스오버 (Moonlit Gugak Crossover Ballad)",
            "keywords": ["밤", "별", "달빛", "그리움", "바다", "아련", "세월", "구름"],
            "bpm": "68-72 BPM",
            "instruments": "Gayageum melody, Warm Grand Piano, Deep Cello, Ancient Saenghwang (Bamboo Mouth Organ), Soft Gong (Jing) resonance",
            "vocal": "Contemporary lyrical crossover Gugak vocal, delicate mix of modern ballad and traditional Korean inflection",
            "prompt": "Modern Korean Gugak Crossover Ballad, delicate Gayageum picking over warm concert piano chords, rich cello counterpoint, ethereal Saenghwang, subtle long Jing tail, emotional tender vocal, 70 BPM, cinematic spacious reverberation"
        },
        {
            "mood": "토속적 정취와 흥과 한 (Earthy Village Folk & Longing)",
            "keywords": ["장터", "고향", "동네", "흙길", "세월", "술", "노래", "사람들"],
            "bpm": "70-74 BPM",
            "instruments": "Bamboo Danso flute, 12-string Gayageum, Traditional Buk & Janggu, Piri, Geomungo bass",
            "vocal": "Rich earthy traditional vocal, deep guttural soulfulness, heartfelt story-teller tone",
            "prompt": "Authentic Korean Rural Minyo, expressive Bamboo Danso flute, rhythmic Gayageum, earthy traditional Buk drum, low resonant Geomungo, sincere aged folk storytelling vocal, 72 BPM, organic village courtyard tone"
        }
    ],
    "gagok": [
        {
            "mood": "애절한 낭만주의 예술 가곡 (Romantic Poetic Elegie)",
            "keywords": ["눈물", "슬픔", "이별", "노을", "어머니", "비", "그리움", "세월", "상여"],
            "bpm": "66-70 BPM",
            "instruments": "Steinway Concert Grand Piano, Solo Cello, Muted String Quartet, Warm English Horn",
            "vocal": "Lyrical classical soprano or refined warm tenor, pure classical bel canto with sorrowful expressive nuance",
            "prompt": "Korean Classical Art Song, Gagok Elegie, expressive Steinway concert grand piano accompaniment, mournful solo cello melodies, gentle string quartet, dramatic dynamic swell, refined lyrical tenor vocal, 68 BPM, recital hall acoustics"
        },
        {
            "mood": "목관과 현악의 따스한 서정 가곡 (Warm Woodwind Chamber Song)",
            "keywords": ["봄", "햇살", "꽃", "바람", "새", "푸른", "숲", "미소"],
            "bpm": "72-76 BPM",
            "instruments": "Concert Grand Piano, Sweet Silver Flute, Warm Oboe, Chamber String Quintet",
            "vocal": "Warm lyric baritone or serene mezzo-soprano, crystal clear poetic diction, gentle elegance",
            "prompt": "Korean Classical Chamber Art Song, lyrical concert piano, delicate silver flute, warm oboe solo, graceful chamber strings, warm resonant lyric baritone, uplifting poetic serenity, 74 BPM, rich concert acoustics"
        },
        {
            "mood": "달빛 야상곡풍 가곡 (Moonlit Classical Nocturne)",
            "keywords": ["밤", "달", "별", "고요", "호수", "바다", "어둠", "꿈"],
            "bpm": "64-68 BPM",
            "instruments": "Arpeggiated Felt Grand Piano, Warm Solo Viola, Muted Clarinet, Subtle Contrabass",
            "vocal": "Hushed, intimate, solemn classical soprano or tenor vocal, delicate pianissimo phrasing",
            "prompt": "Korean Classical Art Song Nocturne, flowing piano arpeggios, expressive solo viola, melancholic clarinet, hushed intimate classical vocal, pianissimo emotional depth, starry night atmosphere, 66 BPM, warm hall reverberation"
        }
    ],
    "dongyo": [
        {
            "mood": "영롱한 오르골과 별밤 동화 (Starlit Fairy Tale & Music Box)",
            "keywords": ["별", "달", "밤", "꿈", "자장가", "눈", "하늘", "아기"],
            "bpm": "70-74 BPM",
            "instruments": "Crystal Music Box (Orgel), Glockenspiel, Soft Celesta, Upright Felt Piano, Gentle Acoustic Guitar",
            "vocal": "Innocent sweet female vocal or pure children's choir, tender lullaby whisper, warm motherly embrace",
            "prompt": "Korean Lyrical Children's Song, sparkling crystal music box chime, magical glockenspiel, cozy felt piano, tender lullaby female vocal, heartwarming bedtime story atmosphere, 72 BPM, cozy warm nursery room acoustic"
        },
        {
            "mood": "발랄한 유년의 소풍과 시골 뜰 (Sunny Picnic & Childhood Garden)",
            "keywords": ["봄", "꽃", "시냇물", "풀밭", "친구", "놀이", "신발", "달리기", "햇살"],
            "bpm": "76-80 BPM",
            "instruments": "Brisk Ukulele, Wooden Xylophone, Bright Nylon Guitar, Wooden Recorder, Whimsical Kazoo",
            "vocal": "Bright, cheerful, pure sweet children's vocal or joyful clear female vocal, smiling and energetic",
            "prompt": "Korean Nostalgic Children's Song, cheerful ukulele strumming, melodic wooden xylophone, bright acoustic guitar, innocent wooden recorder, playful sweet vocal, sunny green garden nostalgia, 78 BPM, crisp lively acoustic room"
        },
        {
            "mood": "정겨운 골목길과 옛 시절 추억 (Retro Alleyway Memories)",
            "keywords": ["골목", "엄마", "고향", "옛날", "저녁", "집", "밥", "고무신"],
            "bpm": "72-76 BPM",
            "instruments": "Warm Accordion, Upright Piano, Melodica, Acoustic Guitar, Soft Hand Percussion",
            "vocal": "Warm nostalgic female vocal with childhood longing, tender storytelling style",
            "prompt": "Korean Retro Children's Ballad, nostalgic French accordion, sweet melodica melody, warm upright piano, gentle acoustic guitar, emotional pure female vocal recalling 1970s alleyway memories, 74 BPM, warm vintage room acoustic"
        }
    ]
}

def analyze_lyrics_and_pick_variation(genre_key: str, lyrics_or_poem: str) -> Dict[str, Any]:
    """
    노랫말(시 본문)의 핵심 어휘, 계절감, 정서 키워드를 분석하여
    해당 장르의 서브스타일 풀 중 가장 어울리는 악기 편성을 선정하고,
    매 호출마다 신선한 무작위 변주(Random Variation)를 융합하여 반환합니다.
    """
    clean_key = genre_key if genre_key in GENRE_VARIATION_POOLS else "folk"
    pool = GENRE_VARIATION_POOLS[clean_key]
    text = lyrics_or_poem or ""

    # 1. 키워드 점수 매칭 (정서 분석)
    best_item = None
    max_score = -1
    matched_candidates = []

    for item in pool:
        score = sum(1 for kw in item["keywords"] if kw in text)
        if score > 0:
            matched_candidates.append((score, item))
        if score > max_score:
            max_score = score
            best_item = item

    # 키워드 매칭이 여러 개면 점수 높은 것들 중 확률적으로 선택하여 다양성(랜덤성) 부여
    if matched_candidates and max_score > 0:
        top_tier = [it for sc, it in matched_candidates if sc >= max_score - 1]
        selected = random.choice(top_tier)
    else:
        # 매칭 키워드가 없거나 균등하면 풀 전체에서 무작위 선택
        selected = random.choice(pool)

    # 2. 미세 랜덤 템포 및 변주 부여 (매 생성마다 조금씩 다른 호흡)
    base_bpm_match = re.search(r'(\d+)\s*-\s*(\d+)', selected["bpm"])
    if base_bpm_match:
        b_min, b_max = int(base_bpm_match.group(1)), int(base_bpm_match.group(2))
        chosen_bpm = random.randint(b_min, b_max)
    else:
        chosen_bpm = 72

    return {
        "mood_name": selected["mood"],
        "bpm": f"{chosen_bpm} BPM",
        "instruments": selected["instruments"],
        "vocal": selected["vocal"],
        "prompt": selected["prompt"]
    }

MUSIC_GENRE_PROMPTS = {
    "gagok": {
        "name": "한국 서정 예술 가곡 (Classical Art Song)",
        "bpm": "68-74 BPM",
        "instruments": "Concert Grand Piano, Solo Cello, Muted String Quartet, Warm Flute",
        "vocal": "Lyrical classical soprano or refined warm tenor, pure classical bel canto vocal with clear poetic diction, solemn and graceful",
        "prompt": (
            "Korean Classical Art Song, Gagok, elegant concert grand piano accompaniment, "
            "deep warm cello counter-melody, graceful strings, lyrical classical soprano or refined warm tenor, "
            "solemn, poetic resonance, 72 BPM, high dynamic range, acoustic recital hall acoustics"
        )
    },
    "dongyo": {
        "name": "서정 동요 / 동심 (Lyrical Children's Song)",
        "bpm": "74-80 BPM",
        "instruments": "Bright Glockenspiel, Crystal Xylophone, Upright Felt Piano, Gentle Acoustic Guitar, Wooden Recorder",
        "vocal": "Innocent pure children's choir or clear warm sweet female vocal, tender and nostalgic",
        "prompt": (
            "Korean Lyrical Children's Song, Dongyo, crystal glockenspiel bell melody, upright felt piano, "
            "warm acoustic guitar arpeggios, gentle recorder, innocent clear sweet female vocal, "
            "nostalgic childhood memories, heartwarming, 78 BPM, cozy room acoustic"
        )
    },
    "folk": {
        "name": "어쿠스틱 포크 (Acoustic Folk Ballad)",
        "bpm": "70-76 BPM",
        "instruments": "Warm Nylon String Acoustic Guitar, Wooden Upright Piano, Soft Harmonica, Subtle Upright Bass",
        "vocal": "Intimate sincere acoustic folk male/female vocal, gentle singing and poetic recitative whisper, 7080 Korean folk style",
        "prompt": (
            "Korean Acoustic Folk Ballad, warm fingerstyle acoustic guitar arpeggios, nostalgic upright piano, "
            "tender harmonica fills, intimate sincere acoustic vocal, calm recitative whisper, "
            "Kim Kwang-seok and Poet and Village aesthetic, 74 BPM, raw analog room tone"
        )
    },
    "minyo": {
        "name": "남도/경기 서정 민요조 (Lyrical Traditional Minyo)",
        "bpm": "68-72 BPM (Semachi / Gutgeori rhythm)",
        "instruments": "12-string Gayageum, Bamboo Daegum, Weeping Haegeum, Traditional Janggu & Buk, Low Piano",
        "vocal": "Expressive traditional Korean Gugak female vocal, sorrowful yet uplifting Sigimsae vibrato, deep resonance of Han and Heung",
        "prompt": (
            "Korean Lyrical Traditional Folk Song, Minyo, Gugak crossover ballad, soulful 12-string Gayageum, "
            "breathy Daegum solo, mournful weeping Haegeum, gentle Janggu rhythm, emotional traditional female vocal, "
            "tender Han and nostalgia, 70 BPM, spacious hall reverberation"
        )
    }
}


# ==============================================================================
# 4. 실시간 .agents/skills 스킬팩 자동연동 엔진 (Skill Auto-Loader)
# ==============================================================================
from pathlib import Path
import re
import os

SKILLS_ROOT_DIR = Path(__file__).resolve().parent.parent / ".agents" / "skills"

STYLE_KEY_TO_SKILL_NAME = {
    "watercolor": "art-style-watercolor",
    "ink_wash": "art-style-ink-wash",
    "pastel": "art-style-pastel",
    "sketch": "art-style-sketch",
    "oil_painting": "art-style-oil-painting"
}

def load_skill_file(skill_name: str) -> Optional[Dict[str, str]]:
    """
    .agents/skills/{skill_name}/SKILL.md 파일을 직접 읽어
    YAML 메타데이터(name, description) 및 마크다운 본문을 동적으로 파싱합니다.
    """
    skill_file = SKILLS_ROOT_DIR / skill_name / "SKILL.md"
    if not skill_file.exists():
        return None
    try:
        raw_text = skill_file.read_text(encoding="utf-8")
        name = skill_name
        description = ""
        content = raw_text

        # Frontmatter 분리
        fm_match = re.search(r"^---\s*\n(.*?)\n---\s*\n(.*)$", raw_text, re.DOTALL)
        if fm_match:
            fm_text = fm_match.group(1)
            content = fm_match.group(2)
            desc_match = re.search(r"description:\s*(.*?)(?:\n[a-zA-Z0-9_-]+:|$)", fm_text, re.DOTALL)
            if desc_match:
                description = desc_match.group(1).strip()

        return {
            "name": name,
            "description": description,
            "content": content
        }
    except Exception as e:
        print(f"[스킬 파일 자동 로드 실패: {skill_name}]: {e}")
        return None

def get_art_style_prompt_bundle(style_key: str = "watercolor") -> Dict[str, str]:
    """
    선택된 화풍의 영문 프롬프트 프리픽스, 네거티브, 공통 지침 번들을
    .agents/skills/ 의 실제 SKILL.md 지침과 실시간 연동하여 반환합니다.
    """
    # 1. 기본 내장 딕셔너리 폴백
    style_data = ART_STYLE_PROMPTS.get(style_key, ART_STYLE_PROMPTS["watercolor"])
    name = style_data["name"]
    prefix = style_data["prefix"]
    guidance = style_data["guidance"]
    negative = style_data["negative"]
    common_rules = ART_STYLE_COMMON_RULES

    # 2. .agents/skills/art-style-{key}/SKILL.md 가 존재하면 실시간 최신 지침으로 동적 오버라이드
    skill_folder = STYLE_KEY_TO_SKILL_NAME.get(style_key, f"art-style-{style_key.replace('_', '-')}")
    skill_data = load_skill_file(skill_folder)
    if skill_data:
        content = skill_data["content"]
        # 시그니처 프롬프트 코드블록 추출
        sig_match = re.search(r"## 2\. 권장 시그니처 프롬프트 구조.*?```text\s*\n(.*?)\n```", content, re.DOTALL)
        if sig_match:
            extracted_sig = sig_match.group(1).strip()
            # [핵심 피사체 및 정경] 앞부분을 prefix로 채택
            if "[핵심 피사체" in extracted_sig:
                prefix = extracted_sig.split("[핵심 피사체")[0].strip(" ,-")
            elif "[" in extracted_sig:
                prefix = extracted_sig.split("[")[0].strip(" ,-")

        # 고유 미학 원칙 추출 (guidance)
        guide_match = re.search(r"## 1\. 고유 미학 원칙(.*?)(?:## 2\.|$)", content, re.DOTALL)
        if guide_match:
            guidance = guide_match.group(1).strip()

    # 3. 공통 출판 규격(art-style-common) 동적 오버라이드
    common_skill = load_skill_file("art-style-common")
    if common_skill:
        common_rules = common_skill["content"].strip()

    return {
        "name": name,
        "prefix": prefix,
        "guidance": guidance,
        "negative": negative,
        "common_rules": common_rules
    }

def get_art_style_korean_instruction(style_key: str = "watercolor") -> Dict[str, str]:
    """
    시화집 삽화 생성을 위한 한국어 화풍 명칭과 핵심 기법 안내 지침을
    .agents/skills/ 에 정립된 고유 미학 원칙으로부터 실시간 추출하여 제공합니다.
    """
    bundle = get_art_style_prompt_bundle(style_key)
    style_names = {
        "watercolor": "한국 정통 서정 투명 수채화",
        "ink_wash": "한국 전통 먹빛 수묵담채화",
        "pastel": "포근한 파스텔 동화 삽화",
        "sketch": "서정 만화 펜화 & 스케치",
        "oil_painting": "따뜻한 질감의 서정 유화"
    }
    
    style_guides = {
        "watercolor": "맑고 투명한 물빛 번짐(Wet-on-wet)과 부드러운 겹침(Glazing), 따뜻한 아침 햇살, 전통 수채화 종이의 섬세한 질감",
        "ink_wash": "서양식 원색 수채화 물감이 아닌, 95% 이상의 짙고 옅은 흑백 먹빛(濃淡)과 일필휘지의 먹선, 단풍이나 가을 산도 붉은 물감이 아닌 담백한 흑백 먹의 번짐으로만 묘사하며, 채색은 5% 미만의 찻물빛만 극도로 절제 (붉거나 노란 원색 물감 칠하기 절대 금지)",
        "pastel": "투명한 물 번짐이 아닌, 분필 소프트 파스텔 가루와 색연필 크레용의 사각거리는 파우더리한 손그림 질감, 거친 도화지 결 위의 다정한 색연필 선과 몽환적인 동화책 질감",
        "sketch": "수채화가 아닌 뚜렷하고 정갈한 흑백 딥펜 잉크 펜촉 선화와 흑연 연필 사선 해칭(Cross-hatching)이 살아있는 일상 만화 그래픽 노블 드로잉 선화",
        "oil_painting": "물에 번지는 수채화가 아닌 캔버스 천 위에 팔레트 나이프와 붓으로 두텁게 얹은 유화 물감(임파스토)의 입체적 마티에르와 빛의 진동"
    }

    # 스킬 파일에 기술된 고유 미학 원칙이 있으면 우선 활용
    guidance = bundle.get("guidance", "")
    korean_lines = [line.strip() for line in guidance.splitlines() if re.search(r'[\uac00-\ud7a3]', line) and not line.startswith('#')]
    dynamic_guide = " ".join(korean_lines[:3]) if korean_lines else style_guides.get(style_key, style_guides["watercolor"])

    return {
        "name_ko": style_names.get(style_key, "한국 정통 서정 수채화"),
        "guide_ko": dynamic_guide,
        "prefix_en": bundle["prefix"],
        "negative_en": bundle["negative"],
        "common_rules": bundle["common_rules"]
    }

MUSIC_KEY_TO_SKILL_NAME = {
    "folk": "music-genre-folk",
    "minyo": "music-genre-minyo",
    "gagok": "music-genre-gagok",
    "dongyo": "music-genre-dongyo"
}

def get_music_genre_bundle(genre_key: str = "folk", lyrics_context: str = "") -> Dict[str, Any]:
    """
    선택된 음악 장르의 프롬프트 및 악기 구성 번들을 반환합니다.
    lyrics_context(노랫말/시 본문)가 제공되면 정서 및 키워드를 심층 분석하여
    매 곡마다 신선하고 다채로운 악기 편성과 랜덤 변주(Adaptive Variations)를 결합합니다.
    """
    clean_key = genre_key if genre_key in MUSIC_GENRE_PROMPTS else "folk"
    genre_data = MUSIC_GENRE_PROMPTS.get(clean_key, MUSIC_GENRE_PROMPTS["folk"])
    skill_name = MUSIC_KEY_TO_SKILL_NAME.get(clean_key, f"music-genre-{clean_key}")

    name = genre_data["name"]
    bpm = genre_data["bpm"]
    instruments = genre_data["instruments"]
    vocal = genre_data["vocal"]
    prompt = genre_data["prompt"]
    mood_name = "정통 서정 음악"
    common_rules = MUSIC_COMMON_RULES

    # 노랫말 기반 동적 악기 & 분위기 변주 (Adaptive Mood & Instrument Shuffling)
    if lyrics_context and lyrics_context.strip():
        dyn = analyze_lyrics_and_pick_variation(clean_key, lyrics_context.strip())
        bpm = dyn["bpm"]
        instruments = dyn["instruments"]
        vocal = dyn["vocal"]
        prompt = dyn["prompt"]
        mood_name = dyn["mood_name"]
    else:
        # 노랫말이 아직 없더라도 기본 풀에서 랜덤 변주 적용
        dyn = analyze_lyrics_and_pick_variation(clean_key, "")
        bpm = dyn["bpm"]
        instruments = dyn["instruments"]
        vocal = dyn["vocal"]
        prompt = dyn["prompt"]
        mood_name = dyn["mood_name"]

    # 공통 규격 스킬 로드
    common_skill = load_skill_file("music-genre-common")
    if common_skill:
        common_rules = common_skill["content"].strip()

    return {
        "genre": clean_key,
        "name": name,
        "bpm": bpm,
        "instruments": instruments,
        "vocal": vocal,
        "prompt": prompt,
        "mood_name": mood_name,
        "common_rules": common_rules
    }


# ==============================================================================
# 5. 모듈러 블록 아키텍처 (Modular Block Architecture)
#    - 공통 스킬(순백 여백, 300 DPI, 텍스트 배제)만 불변 베이스로 유지
#    - 이전 화풍의 모든 찌꺼기/수식어를 완전히 도려내고(Strip)
#    - 선택된 화풍 전용 스킬 블록(Exclusive Style Block)으로 100% 완전 교체 장착
# ==============================================================================

STYLE_CONTAMINATION_KEYWORDS = [
    # 수채화
    "한국 정통 서정 수채화", "한국 정통 서정 투명 수채화", "서정 수채화", "투명 수채화", "수채화", "물빛 번짐",
    "delicate korean lyric transparent watercolor illustration", "delicate korean lyric watercolor illustration",
    "watercolor painting", "watercolor illustration", "watercolor", "watercolour", "wet-on-wet", "translucent washes",
    # 수묵화
    "한국 전통 먹빛 수묵담채화", "전통 먹빛 수묵담채화", "먹빛 수묵담채", "수묵담채화", "수묵담채", "수묵화", "수묵", "먹물 번짐",
    "authentic east asian sumuk black ink wash painting", "traditional korean sumuk ink and wash painting",
    "ink and wash painting", "ink and wash", "sumuk", "sumi-e", "black ink", "hanji",
    # 파스텔
    "포근한 파스텔 동화 삽화", "파스텔 동화", "파스텔 삽화", "파스텔", "색연필", "크레용",
    "heartwarming fairytale children's storybook illustration", "heartwarming children's storybook illustration",
    "storybook illustration", "chalk pastel", "colored pencil", "pastel",
    # 스케치
    "서정 만화 펜화 & 스케치", "서정 만화 펜화", "서정 만화", "펜화", "스케치", "선화", "해칭",
    "lyrical slice-of-life manga sketch drawing", "delicate lyrical manga sketch illustration",
    "manga sketch", "pen and ink", "cross-hatching", "sketch",
    # 유화
    "따뜻한 질감의 서정 유화", "서정 유화", "인상주의 유화", "유화", "임파스토", "나이프",
    "lyrical impressionist oil painting", "oil painting", "impasto", "palette knife",
    # 공통 반복 노이즈 제거
    "3:4 세로형 구도", "순백의 종이와 자연스럽게 어우러지는 부드러운 여백", "글자나 낙관 없음", "300 dpi"
]

def strip_style_contamination(raw_prompt: str) -> str:
    """프롬프트에서 과거 화풍 수식어 및 스타일 지칭어를 완전히 걷어내고 순수 피사체/장면만 남깁니다."""
    text = raw_prompt or ""
    for kw in STYLE_CONTAMINATION_KEYWORDS:
        text = text.replace(kw, "")
    text = re.sub(r"[,;]\s*[,;]+", ",", text)
    text = re.sub(r"\s+", " ", text).strip(" ,.-")
    return text

def build_modular_art_prompt(
    raw_prompt: str,
    art_style: str = "watercolor",
    custom_guide: str = "",
    title: str = "",
    memory_anchor: str = ""
) -> Dict[str, str]:
    """
    [모듈러 블록 아키텍처 조립기]
    블록 A (선택된 화풍 전용 블록) + 블록 B (순수 정경 블록) + 블록 C (공통 출판 규격 블록)
    """
    clean_style = art_style if art_style in STYLE_KEY_TO_SKILL_NAME else "watercolor"
    style_info = get_art_style_korean_instruction(clean_style)

    # 1. 블록 B: 순수 장면 정경 (이전 화풍 오염 완전 도려내기)
    clean_scene = strip_style_contamination(raw_prompt)
    if not clean_scene or len(clean_scene) < 5:
        clean_scene = memory_anchor or title or "고향의 따스한 정경"

    # 추가 연출 가이드가 있을 경우 결합
    if custom_guide and custom_guide.strip():
        clean_guide = strip_style_contamination(custom_guide.strip())
        if clean_guide:
            clean_scene = f"{clean_scene}, 추가 연출: {clean_guide}"

    # 2. 블록 A: 선택된 화풍 전용 고유 블록 (Exclusive Style Block)
    name_ko = style_info["name_ko"]
    guide_ko = style_info["guide_ko"]
    prefix_en = style_info["prefix_en"]
    negative_en = style_info["negative_en"]

    # 3. 블록 C: 공통 출판 표준 블록 (Common Standards Block)
    common_c_ko = "외곽 5%는 책의 순백 종이(#FFFFFF)와 경계 없이 자연스럽게 융합되는 은은한 미세 페이드아웃(Subtle 5% Vignette), 중심부 95% 영역은 인물과 사물이 또렷하고 온전하게 살아있는 3:4 세로형 구도, 글자/낙관/서명/사각 테두리 선 절대 금지"
    common_c_en = "vertical portrait orientation (3:4 tall aspect ratio), subtle 5% edge vignette fading gently into pure white paper without cropping central subjects, full rich composition, no rectangular border, pure fine art without any text, letters, calligraphy, stamps, or frames, 300 dpi publication quality"

    # 4. 최종 통합 조립
    # A) Gemini 한국어 이미지 생성용 모듈러 지침 (100% 화풍 전용 강제 지시문)
    gemini_ko_content = (
        f"한국 출판 시화집을 위한 정통 [{name_ko}] 삽화를 아름답고 깊이 있게 그려주세요.\n\n"
        f"[화풍 전용 규격]\n"
        f"• 화풍: {guide_ko}\n\n"
        f"[장면 연출]\n"
        f"• 정경: {clean_scene}\n\n"
        f"[공통 출판 표준]\n"
        f"• {common_c_ko}"
    )

    # B) 영문 AI 및 오픈 AI용 모듈러 프롬프트
    guarded_en_prompt = f"{prefix_en} of {clean_scene}, {common_c_en}"

    # C) 사용자 화면 표시용 직관적 한국어 프롬프트
    display_ko_prompt = f"[{name_ko}] {clean_scene} ({name_ko} 고유 화풍, 3:4 세로형, 300 DPI)"

    return {
        "art_style": clean_style,
        "name_ko": name_ko,
        "clean_scene": clean_scene,
        "gemini_ko_content": gemini_ko_content,
        "guarded_en_prompt": guarded_en_prompt,
        "display_ko_prompt": display_ko_prompt,
        "negative_en": negative_en
    }


# ==============================================================================
# 6. 음악 모듈러 블록 아키텍처 (Music Modular Block Architecture)
#    - 공통 음악 스킬(메타태그, 70~80 BPM, 아날로그 룸 어쿠스틱) 고정 유지
#    - 장르 교체 시 이전 장르의 추임새/메타태그를 100% 도려내고(Clean Strip)
#    - 선택된 장르 전용 고유 악기/보컬/스타일 블록으로 완벽히 교체 조립
# ==============================================================================

def strip_music_contamination(raw_lyrics: str) -> str:
    """
    이전 장르의 추임새, 악기 지시어, 괄호 연출문 및 메타태그를 완전히 도려내어
    순수한 시어와 핵심 문장들만 추출합니다.
    """
    if not raw_lyrics:
        return ""
    
    text = raw_lyrics
    
    # 1. 메타태그 및 섹션 헤더 제거 ([Intro ...], [Verse ...], [Chorus ...], [Outro ...], [Title ...], [Style ...])
    text = re.sub(r'\[(Intro|Verse|Chorus|Outro|Bridge|Title|Style|Lyrics|Genre).*?\]', '', text, flags=re.IGNORECASE)
    
    # 2. 이전 장르 고유의 괄호 추임새 및 악기 연출어 도려내기
    unwanted_patterns = [
        r'\([^)]*?(얼씨구|지화자|좋네|얼쑤|조타|가야금|대금|해금|장구|풍물|민요)[^)]*?\)',
        r'\([^)]*?(라라라|기타|포크|어쿠스틱|하모니카|통기타|피아노 독주)[^)]*?\)',
        r'\([^)]*?(가곡|성악|소프라노|테너|벨칸토|그랜드 피아노|첼로 화음)[^)]*?\)',
        r'\([^)]*?(동요|동심|반짝반짝|글로켄슈필|실로폰|어린이|새싹|꿈망울)[^)]*?\)',
        r'\([^)]*?(페이드아웃|fade\s*out|아련하게|잔잔한|서서히)[^)]*?\)'
    ]
    for pat in unwanted_patterns:
        text = re.sub(pat, '', text, flags=re.IGNORECASE)
        
    # 3. 빈 줄 정리 및 순수 시 구절 추출
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    # 혹시 남아있는 기호나 콜론 제거
    cleaned_lines = []
    for l in lines:
        l_clean = re.sub(r'^[•\-\*]\s*', '', l)
        if l_clean and not l_clean.startswith("(") and not l_clean.endswith(")"):
            cleaned_lines.append(l_clean)
            
    return "\n".join(cleaned_lines) if cleaned_lines else raw_lyrics.strip()


def build_modular_song_package(
    poem_body: str,
    title: str = "무제",
    genre_key: str = "folk",
    custom_guide: str = "",
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    [음악 모듈러 블록 아키텍처 조립기]
    블록 A (선택된 장르 고유 스킬 블록) + 블록 B (오염 제거된 순수 시어 운율 블록) + 블록 C (공통 음악 출판 규격)
    """
    clean_genre = genre_key if genre_key in MUSIC_GENRE_PROMPTS else "folk"

    # 1. 블록 B: 순수 시어 추출 (이전 장르의 오염 완전 도려내기)
    clean_poem = strip_music_contamination(poem_body)
    if not clean_poem or len(clean_poem.splitlines()) < 2:
        clean_poem = poem_body.strip() or f"{title}의 푸른 기억\n바람이 불어오는 언덕 위에서\n그리운 얼굴 떠올려 보네"

    # 2. 블록 A: 노랫말 기반 동적 악기 & 분위기 변주 스킬 블록
    genre_bundle = get_music_genre_bundle(clean_genre, lyrics_context=clean_poem)
    genre_name = genre_bundle["name"]
    genre_prompt = genre_bundle["prompt"]
    genre_bpm = genre_bundle["bpm"]
    genre_inst = genre_bundle["instruments"]
    genre_vocal = genre_bundle["vocal"]
    mood_theme = genre_bundle.get("mood_name", "서정 음악")

    # 3. 블록 C: 공통 음악 출판 표준
    common_rules = genre_bundle["common_rules"]

    # 4. 고지능 Gemini 연동 가능 여부 판단
    key = api_key or os.getenv("GEMINI_API_KEY")
    if key:
        try:
            from google import genai
            client = genai.Client(api_key=key)

            override_directive = ""
            if custom_guide and custom_guide.strip():
                override_directive = (
                    f"\n[★ 작곡가 연출 특별 지침]:\n"
                    f"\"{custom_guide.strip()}\"\n"
                    f"위 지시(특정 독주 악기, 보컬 감정, 특정 후렴구 등)를 가사와 프롬프트에 최우선 반영하세요.\n"
                )

            system_instruction = (
                f"당신은 한국 정통 서정시를 서정 음악으로 빚어내는 작곡가이자 음악 감독입니다.\n\n"
                f"[음악 장르 규격 ({genre_name})]\n"
                f"• 장르 기본 방향: {genre_name}\n"
                f"• 이번 곡 노랫말 맞춤 무드: [{mood_theme}]\n"
                f"• 이번 곡 맞춤 악기 편성(힌트): {genre_inst}\n"
                f"• 권장 템포: {genre_bpm}\n"
                f"• 권장 보컬 질감: {genre_vocal}\n"
                f"• 절대 금지: EDM, 랩, 오토튠, 시끄러운 신디사이저, 타 장르 악기 혼입 금지\n"
                f"• 【★ 핵심 요구사항 - 노랫말에 따른 다채로운 악기 변주】: 매번 획일적인 악기 나열을 엄격히 금지합니다. 입력된 [시 본문(순수 시어)]의 구체적인 소재(물, 강, 노을, 고무신, 바람, 어머니, 골목길 등)와 감정선(애절함, 따스함, 쓸쓸함, 잔잔함 등)을 분석하여, 그 시에 가장 어울리는 주선율 독주 악기(예: 하모니카, 첼로, 대금, 피리, 아코디언, 우쿨렐레 등)와 반주 악기를 창의적으로 배합하여 매 곡마다 신선한 차별성을 부여하세요!\n"
                f"• 【가장 중요한 원칙】: 가사([LYRICS]) 칸에는 실제 사람이 입으로 부르는 '순수 노랫말'과 표준 태그([Intro], [Verse 1], [Chorus], [Verse 2], [Outro])만 작성하세요. 괄호 안에 악기 연주나 분위기를 묘사하는 지시문(예: '(애잔한 가야금 선율이 흐르고...)', '(잔잔한 악기 선율과 함께...)')을 절대 넣지 마세요! YuE나 Udio 등의 AI가 괄호 안의 지시문까지 그대로 읽어서 노래로 불러버립니다!\n"
                f"{override_directive}\n"
                f"[공통 작곡 원칙]\n"
                f"• 시 본문의 서정적 시어를 3·4조 또는 4·4조의 노래하기 편한 운율로 정돈하세요.\n"
                f"• 메타태그 구조 (괄호 지시문 없이 순수 태그만 사용):\n"
                f"  [Intro]\n"
                f"  [Verse 1]\n"
                f"  [Chorus]\n"
                f"  [Verse 2]\n"
                f"  [Chorus]\n"
                f"  [Outro]\n\n"
                f"출력 형식:\n"
                f"[GENRE_PROMPT]\n(Suno/Udio/YuE 입력용 1줄 영문 스타일 태그 - 노랫말 정서와 악기 조합을 반영하여 매번 개성 있게 작성)\n\n"
                f"[LYRICS]\n(완성된 한국어 노래 가사 전문 - 지시문 없이 순수 노랫말만 작성)"
            )

            user_prompt = (
                f"곡 제목: {title}\n"
                f"시 본문(순수 시어):\n{clean_poem}\n"
                f"선택 장르: {genre_name} (맞춤 테마: {mood_theme})\n\n"
                f"위 시의 노랫말 정서(소재, 분위기)를 면밀히 반영하여 [{genre_name}] 장르의 감동적인 노래 가사와 독창적인 악기 구성이 담긴 음악 프롬프트([GENRE_PROMPT])로 편곡해 주세요. (주의: 가사에 괄호 연주 해설문 절대 금지)"
            )

            active_model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
            response = client.models.generate_content(
                model=active_model,
                contents=user_prompt,
                config={"system_instruction": system_instruction}
            )

            raw_text = response.text.strip() if response and response.text else ""
            if "[LYRICS]" in raw_text:
                parts = raw_text.split("[LYRICS]")
                prompt_sec = parts[0].replace("[GENRE_PROMPT]", "").strip()
                if prompt_sec:
                    genre_prompt = prompt_sec
                final_lyrics = parts[1].strip()
            else:
                final_lyrics = raw_text

            # 후처리: AI가 괄호로 악기 연주 지시문을 넣었을 경우 자동 정제 (보컬이 읽지 못하도록)
            import re
            # 괄호 안의 악기 연출 설명문 제거 예: (애잔한 가야금 뜯는 소리... 흐른다)
            final_lyrics = re.sub(r'\([^\)]*(선율|소리|흐르고|어우러|연주|시작|페이드아웃|독주|화음|잔향|배경)[^\)]*\)', '', final_lyrics)
            # 메타태그 뒤의 부가 설명 정리 [Intro - 악기 선율] -> [Intro]
            final_lyrics = re.sub(r'\[(Intro|Outro|Verse\s*\d+|Chorus)\s*-[^\]]+\]', r'[\1]', final_lyrics)
            # 연속된 빈 줄 정리
            final_lyrics = re.sub(r'\n{3,}', '\n\n', final_lyrics).strip()

            return {
                "success": True,
                "genre": clean_genre,
                "genre_name": genre_name,
                "mood_theme": mood_theme,
                "instruments": genre_inst,
                "bpm": genre_bpm,
                "music_prompt": genre_prompt,
                "lyrics": final_lyrics,
                "raw_poem": clean_poem,
                "full_suno_prompt": f"[Title]\n{title}\n\n[Style / Tags]\n{genre_prompt}\n\n[Lyrics]\n{final_lyrics}"
            }
        except Exception as e:
            print(f"[Gemini 작곡 연동 폴백]: {e}")

    # Fallback: 로컬 규칙 기반 모듈러 조립
    genre_hooks = {
        "minyo": ("얼씨구 지화자 좋네 / 아련한 바람결 따라", "세월은 흘러 흘러 강물로 가네 / 얼쑤"),
        "folk": ("라라라 라라라 바람 속에 흩어지는 / 그 시절의 우리 이야기", "기타 줄에 얹어 부르는 나의 노래여"),
        "gagok": ("아, 가슴 깊이 차오르는 그리움이여 / 바람결에 흩날리는 푸른 별빛처럼", "영원히 지지 않는 꽃잎이 되리라"),
        "dongyo": ("반짝반짝 작은 별처럼 / 내 마음속에 피어나는 고운 꿈망울", "엄마 품처럼 따스한 꿈속으로")
    }
    hook, outro = genre_hooks.get(clean_genre, genre_hooks["folk"])
    
    poem_lines = [l.strip() for l in clean_poem.splitlines() if l.strip()]
    mid = max(1, len(poem_lines) // 2)
    v1 = "\n".join(poem_lines[:mid])
    v2 = "\n".join(poem_lines[mid:]) if mid < len(poem_lines) else v1

    final_lyrics = (
        f"[Intro]\n\n"
        f"[Verse 1]\n{v1}\n\n"
        f"[Chorus]\n마음 한구석에 피어난 {title}\n{hook}\n잊지 못할 그 시절의 노래가 되어\n\n"
        f"[Verse 2]\n{v2}\n\n"
        f"[Chorus]\n마음 한구석에 피어난 {title}\n{hook}\n잊지 못할 그 시절의 노래가 되어\n\n"
        f"[Outro]\n{outro}"
    )

    return {
        "success": True,
        "genre": clean_genre,
        "genre_name": genre_name,
        "mood_theme": mood_theme,
        "instruments": genre_inst,
        "bpm": genre_bpm,
        "music_prompt": genre_prompt,
        "lyrics": final_lyrics,
        "raw_poem": clean_poem,
        "full_suno_prompt": f"[Title]\n{title}\n\n[Style / Tags]\n{genre_prompt}\n\n[Lyrics]\n{final_lyrics}"
    }
