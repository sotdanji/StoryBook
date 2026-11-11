# -*- coding: utf-8 -*-
import os
from pathlib import Path
from datetime import datetime

search_dirs = [
    Path(r"C:\Users\JHLIM\Downloads"),
    Path(r"C:\Users\JHLIM\Desktop"),
    Path(r"d:\AG\StoryBook"),
    Path(r"d:\AG")
]

found = []
for sdir in search_dirs:
    if not sdir.exists():
        continue
    for root, dirs, files in os.walk(sdir):
        if any(k in dirs for k in [".git", "node_modules", ".venv", "__pycache__", "AppData"]):
            for k in [".git", "node_modules", ".venv", "__pycache__", "AppData"]:
                if k in dirs:
                    dirs.remove(k)
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in [".mp3", ".m4a", ".wav"]:
                fp = Path(root) / f
                try:
                    mtime = datetime.fromtimestamp(fp.stat().st_mtime)
                    sz = fp.stat().st_size
                    # 따순, 굼턱, 11, 다듬이, 09, 03 키워드 검색
                    name_l = f.lower()
                    if any(k in name_l for k in ["따순", "굼턱", "11", "다듬", "09", "03", "suno", "music"]):
                        found.append((fp, sz, mtime))
                except:
                    pass

# 중복 제거 및 시간순 정렬
seen = set()
unique_found = []
for fp, sz, mt in found:
    if str(fp) not in seen:
        seen.add(str(fp))
        unique_found.append((fp, sz, mt))

unique_found.sort(key=lambda x: x[2], reverse=True)
print(f"총 발견된 관련 오디오: {len(unique_found)}개\n")
for fp, sz, mt in unique_found[:40]:
    t_str = mt.strftime("%Y-%m-%d %H:%M")
    print(f"{t_str} | {sz:9d} bytes | {fp.name:35s} | {fp}")

