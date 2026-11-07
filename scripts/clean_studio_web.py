import re
from pathlib import Path

index_path = Path("d:/AG/EduAI_Hub/public/studio/index.html")
modals_path = Path("d:/AG/StoryBook/web/templates/partials/_modals.html")

html = index_path.read_text(encoding="utf-8")
modals_html = modals_path.read_text(encoding="utf-8")

# 1. include _modals.html 치환
html = html.replace('{% include "partials/_modals.html" %}', modals_html)

# 2. Jinja if admin / current_user 태그 제거 및 정돈
clean_header_user = """
            <div style="display: flex; align-items: center; gap: 6px; padding: 4px 10px; background: #FFF9F2; border: 1px solid #EBD5C2; border-radius: 6px; font-size: 0.8rem;">
              <span>👤 <strong>나만의 집필실</strong> (이야기솥 글솥)</span>
            </div>
"""
html = re.sub(r'\{%\s*if\s+is_admin\s*%\}.*?\{%\s*endif\s*%\}', '', html, flags=re.DOTALL)
html = re.sub(r'\{%\s*if\s+current_user\s*%\}.*?\{%\s*endif\s*%\}', clean_header_user, html, flags=re.DOTALL)

# 남은 진자 태그 검사
remaining_tags = re.findall(r'(\{%[^%]+%\}|\{\{[^}]+\}\})', html)
print("남은 진자 태그:", remaining_tags)

index_path.write_text(html, encoding="utf-8")
print("✅ studio/index.html 정돈 완료!")

