import os
import sys
import py_compile
import ast
from pathlib import Path

BASE_DIR = Path("d:/AG/StoryBook")

print("=" * 60)
print("1. PYTHON SYNTAX & AST VALIDATION")
print("=" * 60)

py_files = list(BASE_DIR.glob("**/*.py"))
py_errors = []

for py_file in py_files:
    parts = py_file.parts
    if any(p in parts for p in (".git", "__pycache__", ".gemini", ".venv", "venv", "_internal", "python")):
        continue
    rel_path = py_file.relative_to(BASE_DIR)
    try:
        py_compile.compile(str(py_file), doraise=True)
        with open(py_file, "r", encoding="utf-8") as f:
            ast.parse(f.read(), filename=str(rel_path))
        print(f"[OK] {rel_path}")
    except Exception as e:
        print(f"[FAIL] {rel_path}: {e}")
        py_errors.append((str(rel_path), str(e)))

print(f"\nTotal Python files checked: {len(py_files) - len(py_errors)}")
if py_errors:
    print(f"FAILED FILES: {len(py_errors)}")
    for f, err in py_errors:
        print(f"  - {f}: {err}")
else:
    print("ALL PYTHON FILES PASSED SYNTAX & AST CHECK!")
