# -*- coding: utf-8 -*-
import json
from pathlib import Path

p9 = Path(r"d:\AG\StoryBook\projects\노을빛_기억\revisions\제09화.json")
if p9.exists():
    data9 = json.loads(p9.read_text(encoding="utf-8"))
    print("================== [제09화 다듬이질 리비전] ==================")
    for idx, rev in enumerate(data9):
        print(f"--- Rev {idx+1} ({rev.get('version_name')}, {rev.get('timestamp')}) ---")
        print("poem_body:\n", rev.get("poem_body", "").strip())
        if rev.get("lyrics"):
            print("lyrics:\n", rev.get("lyrics").strip())

p11 = Path(r"d:\AG\StoryBook\projects\노을빛_기억\revisions\제11화.json")
if p11.exists():
    data11 = json.loads(p11.read_text(encoding="utf-8"))
    print("\n================== [제11화 따순굼턱 리비전] ==================")
    for idx, rev in enumerate(data11):
        print(f"--- Rev {idx+1} ({rev.get('version_name')}, {rev.get('timestamp')}) ---")
        print("poem_body:\n", rev.get("poem_body", "").strip())
        if rev.get("lyrics"):
            print("lyrics:\n", rev.get("lyrics").strip())

