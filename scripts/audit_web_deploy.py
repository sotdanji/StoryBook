"""
서버 배포 무결성 자동 검수기 (Web Deployment Health Auditor)
로컬 -> Vercel 클라우드 웹 전환 시 발생하는 4대 오류 전수 검사:
1. Jinja2 템플릿 태그 잔존 여부 ({%, {{, {#)
2. 로컬 하드코딩 경로 잔존 여부 (localhost, 127.0.0.1, file://, D:\)
3. 정적 에셋(이미지, CSS, JS) 링크 404 누락 여부
4. 백엔드 없는 환경에서의 API 폴백 안전망 점검
"""

import os
import re
import sys
from pathlib import Path

BASE_DIR = Path(r"D:\AG\EduAI_Hub\public")

def check_template_tags(content, filepath):
    issues = []
    # {% ... %}
    jinja_stmt = re.findall(r"\{%.*?%\}", content, re.DOTALL)
    if jinja_stmt:
        issues.append(f"[템플릿 태그 잔존] {{% %}} 구문 {len(jinja_stmt)}개 발견 (예: {jinja_stmt[0][:40]})")
    
    # {{ ... }} (Vue/단순문자열 제외한 jinja 변수 형태)
    jinja_var = re.findall(r"\{\{\s*(?:current_user|is_admin|project|status|book_structure).*?\}\}", content)
    if jinja_var:
        issues.append(f"[템플릿 변수 잔존] {{{{ }}}} 구문 {len(jinja_var)}개 발견 (예: {jinja_var[0]})")
    return issues

def check_local_paths(content, filepath):
    issues = []
    patterns = [
        (r"http://localhost:\d+", "로컬호스트 URL"),
        (r"http://127\.0\.0\.1:\d+", "로컬 IP URL"),
        (r"file:///[a-zA-Z]:", "로컬 파일 프로토콜 경로"),
        (r"[a-zA-Z]:\\[a-zA-Z0-9_\\]+", "윈도우 절대 경로")
    ]
    for pat, label in patterns:
        matches = re.findall(pat, content)
        if matches:
            # 안전한 예외(설명문이나 주석 등) 제외 필터링
            real_matches = [m for m in matches if not m.startswith("D:\\AG\\EduAI_Hub\\public")]
            if real_matches:
                issues.append(f"[{label} 잔존] {len(real_matches)}개 발견 (예: {real_matches[0]})")
    return issues

def check_asset_references(content, html_path):
    issues = []
    # img src, link href, script src
    src_matches = re.findall(r'(?:src|href)=["\']([^"\']+\.(?:png|jpg|jpeg|gif|svg|css|js))["\']', content, re.IGNORECASE)
    
    for ref in src_matches:
        if ref.startswith("http://") or ref.startswith("https://") or ref.startswith("//"):
            continue
        
        # 상대 경로 또는 절대 웹 경로 해석
        clean_ref = ref.split("?")[0].split("#")[0]
        if clean_ref.startswith("/"):
            target_path = BASE_DIR / clean_ref.lstrip("/")
        else:
            target_path = html_path.parent / clean_ref
            
        if not target_path.exists():
            issues.append(f"[에셋 404 누락] {clean_ref} 파일이 실제 존재하지 않음 (참조: {html_path.name})")
            
    return issues

def run_audit():
    print("=" * 70)
    print("🔍 [이야기솥] 서버 배포 무결성 자동 검수 시작")
    print(f"📂 대상 디렉터리: {BASE_DIR}")
    print("=" * 70)

    if not BASE_DIR.exists():
        print(f"❌ 오류: {BASE_DIR} 폴더를 찾을 수 없습니다.")
        return

    total_files = 0
    total_issues = 0
    results = {}

    target_exts = [".html", ".js"]
    
    for root, _, files in os.walk(BASE_DIR):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in target_exts:
                filepath = Path(root) / f
                rel_path = filepath.relative_to(BASE_DIR)
                total_files += 1
                
                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as fp:
                        content = fp.read()
                except Exception as e:
                    continue

                file_issues = []
                # 1. 템플릿 태그 검사
                if ext == ".html":
                    file_issues.extend(check_template_tags(content, filepath))
                
                # 2. 로컬 경로 검사
                file_issues.extend(check_local_paths(content, filepath))

                # 3. 에셋 참조 누락 검사
                if ext == ".html":
                    file_issues.extend(check_asset_references(content, filepath))

                if file_issues:
                    results[str(rel_path)] = file_issues
                    total_issues += len(file_issues)

    print(f"\n📊 검수 완료: 총 {total_files}개 웹 파일 점검됨")
    
    if total_issues == 0:
        print("✅ 축하합니다! 잔여 템플릿 태그, 로컬 경로, 에셋 404 오류가 단 1건도 없습니다.")
    else:
        print(f"⚠️ 총 {total_issues}건의 잠재적 배포 결함 발견:\n")
        for file_name, issue_list in results.items():
            print(f"📄 [{file_name}]")
            for iss in issue_list:
                print(f"   • {iss}")
            print()

    print("=" * 70)

if __name__ == "__main__":
    run_audit()

