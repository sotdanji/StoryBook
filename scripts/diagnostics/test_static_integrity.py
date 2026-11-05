import os
import sys
import glob
import py_compile
import subprocess

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

print("=== [1단계] Python 백엔드 & 독립 패키지 정적 구문 컴파일 검사 ===")
py_files = (
    glob.glob("core/**/*.py", recursive=True)
    + glob.glob("web/**/*.py", recursive=True)
    + glob.glob("packages/**/*.py", recursive=True)
    + ["run_web.py", "main.py"]
)
py_errors = []

for py_path in py_files:
    if "__pycache__" in py_path:
        continue
    try:
        py_compile.compile(py_path, doraise=True)
        print(f"  ✓ {py_path}: 문법 정상")
    except Exception as e:
        py_errors.append((py_path, str(e)))
        print(f"  ✕ {py_path}: 오류 발생 -> {e}")

print(f"\nPython 검사 결과: 총 {len(py_files)}개 파일 중 에러 {len(py_errors)}건")

print("\n=== [2단계] Frontend JS 문법 컴파일 검사 (Node.js) ===")
js_files = [
    "web/static/js/app.js",
    "web/static/js/modules/project_shelf.js",
    "web/static/js/modules/illustration_studio.js",
    "web/static/js/modules/audio_music_studio.js",
    "web/static/js/modules/thesaurus_palette.js",
    "web/static/js/modules/publishing_export.js",
    "web/static/js/poem_video.js",
    "web/static/js/dtp_matter_templates.js",
    "web/static/js/dtp_editor_core.js",
    "web/static/js/components/storybook_dtp_spread.esm.js",
    "web/static/js/main.esm.js",
    "packages/dtp_spread_ui/dtp_spread_ui.js",
    "packages/dtp_spread_ui/dtp_spread_ui.esm.js",
    "vite.config.js",
]
for js_path in js_files:
    try:
        res = subprocess.run(["node", "-c", js_path], capture_output=True, text=True, check=True)
        print(f"  ✓ {js_path}: Node.js 구문 검사 통과 (문법 오류 없음)")
    except Exception as e:
        print(f"  ✕ {js_path}: 구문 오류 -> {e}")

print("\n=== [3단계] HTML 태그 밸런스 검사 (index.html + partials/_modals.html) ===")
html_path = "web/templates/index.html"
with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()
modals_partial = "web/templates/partials/_modals.html"
if os.path.exists(modals_partial):
    with open(modals_partial, "r", encoding="utf-8") as mf:
        html = html.replace('{% include "partials/_modals.html" %}', mf.read())

# 주요 모달 및 컨테이너 div 쌍 검사
open_divs = html.count("<div")
close_divs = html.count("</div")
print(f"  - 전체 <div> 개수: {open_divs}개 / </div> 개수: {close_divs}개 (차이: {open_divs - close_divs})")

# 모든 modal-overlay 태그 닫힘 검사
import re
modals = re.findall(r'id=\"([a-zA-Z0-9_-]*modal[a-zA-Z0-9_-]*)\"', html, re.I)
print(f"  - 감지된 주요 모달 ID ({len(modals)}개): {modals}")
for m_id in modals:
    pos = html.find(f'id="{m_id}"')
    if pos != -1:
        # 모달 시작부터 다음 modal-overlay 또는 스크립트 전까지 div 밸런스 검사
        next_pos = html.find('class="modal-overlay"', pos + 20)
        if next_pos == -1:
            next_pos = html.find('<script', pos + 20)
        sub = html[pos:next_pos]
        o_cnt = sub.count("<div")
        c_cnt = sub.count("</div")
        status = "✓ 정상" if o_cnt == c_cnt else f"⚠️ 불일치 (열림 {o_cnt} / 닫힘 {c_cnt})"
        print(f"    * [{m_id}]: {status}")
