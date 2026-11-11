# -*- coding: utf-8 -*-
from pathlib import Path

targets = [
    Path(r"d:\AG\StoryBook\projects\샘플_기억상자\시화집_갤러리.html"),
    Path(r"d:\AG\StoryBook\projects\노을빛_기억\시화집_갤러리.html"),
    Path(r"D:\AG\EduAI_Hub\public\gallery\index.html")
]

for f in targets:
    if not f.exists():
        continue
    txt = f.read_text(encoding="utf-8")
    
    # resolveMediaUrl 내의 리턴문에 캐시 버스터 추가
    old_fragment = "return `/gallery/${p}`;"
    new_fragment = "const cb = (p.includes('music/') || p.endsWith('.mp3') || p.endsWith('.wav')) ? '?v=' + Date.now() : '';\n        return `/gallery/${p}${cb}`;"
    
    if old_fragment in txt:
        txt = txt.replace(old_fragment, new_fragment)
        txt = txt.replace("return p;\n      }", "return p + cb;\n      }")
        txt = txt.replace("return `/projects/${safeProj}/${p}`;", "return `/projects/${safeProj}/${p}${cb}`;")
        f.write_text(txt, encoding="utf-8")
        print(f"✅ 캐시 버스터 적용 성공: {f.name} ({f.parent.name})")
    else:
        print(f"⚠️ 이미 적용되었거나 조각 미발견: {f.name} ({f.parent.name})")

