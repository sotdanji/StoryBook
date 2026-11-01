# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path

content = Path("d:/AG/StoryBook/web/templates/index.html").read_text(encoding="utf-8")
lines = content.splitlines()
start = -1
for i, l in enumerate(lines):
    if 'class="book-spread"' in l:
        start = i
        break

if start != -1:
    for l in lines[start-5:start+120]:
        print(l)
