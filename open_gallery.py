# -*- coding: utf-8 -*-
import sys
import webbrowser
from pathlib import Path

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
TARGET_HTML = BASE_DIR / "projects" / "노을빛_기억" / "시화집_갤러리.html"

if TARGET_HTML.exists():
    print(f"[Open Gallery] Opening: {TARGET_HTML}")
    webbrowser.open(TARGET_HTML.as_uri())
else:
    print(f"[Error] File not found: {TARGET_HTML}")
