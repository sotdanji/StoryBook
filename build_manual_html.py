# -*- coding: utf-8 -*-
"""
user_manual.md 파일을 어르신/초보자 맞춤형 고품격 '큰 글씨 웹 설명서' 템플릿(manual.html)으로 변환하는 스크립트
"""
import re
import html
from pathlib import Path

def convert_md_to_html(md_text: str) -> str:
    lines = md_text.splitlines()
    html_lines = []
    
    in_code_block = False
    in_table = False
    table_lines = []
    
    def flush_table():
        nonlocal table_lines, in_table
        if not table_lines:
            return ""
        out = ["<div class='table-responsive'><table class='manual-table'>"]
        header_done = False
        for idx, row in enumerate(table_lines):
            if re.match(r'^\s*\|?\s*:?-+:?\s*\|', row):
                header_done = True
                continue
            cells = [c.strip() for c in row.strip().strip('|').split('|')]
            if not header_done and idx == 0:
                out.append("<thead><tr>")
                for c in cells:
                    out.append(f"<th>{inline_format(c)}</th>")
                out.append("</tr></thead><tbody>")
            else:
                out.append("<tr>")
                for c in cells:
                    out.append(f"<td>{inline_format(c)}</td>")
                out.append("</tr>")
        if header_done:
            out.append("</tbody>")
        out.append("</table></div>")
        table_lines = []
        in_table = False
        return "\n".join(out)

    def inline_format(text: str) -> str:
        t = text
        t = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', t)
        t = re.sub(r'\*(.+?)\*', r'<em>\1</em>', t)
        t = re.sub(r'`(.+?)`', r'<code>\1</code>', t)
        t = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2" class="manual-link">\1</a>', t)
        return t

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_code_block:
                in_code_block = False
                html_lines.append("</pre></div>")
            else:
                if in_table:
                    html_lines.append(flush_table())
                in_code_block = True
                html_lines.append("<div class='manual-box-wrapper'><pre class='manual-box'>")
            continue

        if in_code_block:
            html_lines.append(html.escape(line))
            continue

        if stripped.startswith("|") and stripped.endswith("|"):
            in_table = True
            table_lines.append(stripped)
            continue
        elif in_table:
            html_lines.append(flush_table())

        if not stripped:
            html_lines.append("<div class='manual-spacer'></div>")
            continue

        if stripped.startswith("# "):
            h_text = inline_format(stripped[2:])
            html_lines.append(f"<h1 class='manual-h1'>{h_text}</h1>")
        elif stripped.startswith("## "):
            h_text = inline_format(stripped[3:])
            html_lines.append(f"<h2 class='manual-h2'>{h_text}</h2>")
        elif stripped.startswith("### "):
            h_text = inline_format(stripped[4:])
            html_lines.append(f"<h3 class='manual-h3'>{h_text}</h3>")
        elif stripped.startswith("#### "):
            h_text = inline_format(stripped[5:])
            html_lines.append(f"<h4 class='manual-h4'>{h_text}</h4>")
        elif stripped.startswith("> "):
            q_text = inline_format(stripped[2:])
            html_lines.append(f"<blockquote class='manual-quote'>{q_text}</blockquote>")
        elif stripped.startswith("---") or stripped.startswith("***"):
            html_lines.append("<hr class='manual-divider'>")
        elif stripped.startswith("- ") or stripped.startswith("* "):
            li_text = inline_format(stripped[2:])
            html_lines.append(f"<li class='manual-li'>{li_text}</li>")
        elif re.match(r'^\d+\.\s', stripped):
            num_match = re.match(r'^(\d+\.)\s*(.+)$', stripped)
            num_prefix = num_match.group(1)
            rest_text = inline_format(num_match.group(2))
            html_lines.append(f"<div class='manual-num-item'><span class='num-badge'>{num_prefix}</span><div class='num-content'>{rest_text}</div></div>")
        else:
            p_text = inline_format(stripped)
            html_lines.append(f"<p class='manual-p'>{p_text}</p>")

    if in_table:
        html_lines.append(flush_table())

    return "\n".join(html_lines)


def build_manual_html():
    base_dir = Path(r"d:\AG\StoryBook")
    md_path = base_dir / "user_manual.md"
    out_path = base_dir / "web" / "templates" / "manual.html"

    if not md_path.exists():
        print(f"Error: {md_path} not found")
        return

    raw_md = md_path.read_text(encoding="utf-8")
    body_html = convert_md_to_html(raw_md)

    template = f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>StoryBook Studio 공식 사용 설명서 (큰 글씨)</title>
  <style>
    :root {{
      --bg-page: #FAF7F2;
      --bg-card: #FFFFFF;
      --primary-brown: #643E19;
      --primary-dark: #3F2305;
      --accent-gold: #C68B59;
      --accent-soft: #F4EAD4;
      --text-main: #2C2520;
      --text-muted: #665F57;
      --border-color: #EBDCCB;
      --quote-bg: #F8F3EC;
      --base-font-size: 17px;
    }}

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}

    body {{
      background: var(--bg-page);
      color: var(--text-main);
      font-family: "Pretendard", "Noto Sans KR", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Malgun Gothic", sans-serif;
      font-size: var(--base-font-size);
      line-height: 1.85;
      padding-bottom: 80px;
      -webkit-font-smoothing: antialiased;
    }}

    /* 상단 고정 제어 바 */
    .manual-topbar {{
      position: sticky;
      top: 0;
      z-index: 100;
      background: rgba(255, 255, 255, 0.96);
      backdrop-filter: blur(8px);
      border-bottom: 2px solid var(--border-color);
      padding: 12px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      box-shadow: 0 2px 10px rgba(100, 62, 25, 0.06);
    }}

    .manual-brand {{
      display: flex;
      align-items: center;
      gap: 10px;
    }}

    .manual-brand-icon {{
      font-size: 1.6rem;
    }}

    .manual-brand-title {{
      font-size: 1.15rem;
      font-weight: 700;
      color: var(--primary-dark);
      letter-spacing: -0.3px;
    }}

    .manual-controls {{
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    .btn-ctrl {{
      padding: 8px 14px;
      font-size: 0.92rem;
      font-weight: 600;
      border: 1.5px solid var(--border-color);
      background: #FFFFFF;
      color: var(--primary-brown);
      border-radius: 8px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: all 0.2s ease;
    }}

    .btn-ctrl:hover {{
      background: var(--accent-soft);
      border-color: var(--accent-gold);
    }}

    .btn-ctrl.btn-primary {{
      background: var(--primary-brown);
      color: #FFFFFF;
      border-color: var(--primary-brown);
    }}

    .btn-ctrl.btn-primary:hover {{
      background: var(--primary-dark);
    }}

    /* 본문 레이아웃 */
    .manual-container {{
      max-width: 900px;
      margin: 36px auto;
      background: var(--bg-card);
      border: 2px solid var(--border-color);
      border-radius: 16px;
      padding: 48px 56px;
      box-shadow: 0 4px 20px rgba(100, 62, 25, 0.05);
    }}

    @media (max-width: 768px) {{
      .manual-container {{
        margin: 16px;
        padding: 24px 20px;
      }}
      .manual-topbar {{
        padding: 10px 14px;
      }}
    }}

    /* 글자 크기 모드 */
    body.font-large {{
      --base-font-size: 19px;
    }}
    body.font-xlarge {{
      --base-font-size: 21px;
    }}

    /* 제목 스타일 */
    .manual-h1 {{
      font-size: 2rem;
      color: var(--primary-dark);
      font-weight: 800;
      margin-bottom: 24px;
      padding-bottom: 16px;
      border-bottom: 3px solid var(--primary-brown);
      letter-spacing: -0.5px;
      line-height: 1.35;
    }}

    .manual-h2 {{
      font-size: 1.55rem;
      color: var(--primary-brown);
      font-weight: 700;
      margin-top: 40px;
      margin-bottom: 18px;
      padding-bottom: 10px;
      border-bottom: 1.5px solid var(--border-color);
      display: flex;
      align-items: center;
      gap: 8px;
      line-height: 1.4;
    }}

    .manual-h3 {{
      font-size: 1.25rem;
      color: #4A3525;
      font-weight: 700;
      margin-top: 28px;
      margin-bottom: 12px;
      line-height: 1.45;
    }}

    .manual-h4 {{
      font-size: 1.08rem;
      color: var(--primary-brown);
      font-weight: 700;
      margin-top: 20px;
      margin-bottom: 8px;
    }}

    /* 본문 문단 */
    .manual-p {{
      font-size: 1em;
      color: var(--text-main);
      margin-bottom: 16px;
      word-break: keep-all;
    }}

    .manual-spacer {{
      height: 10px;
    }}

    .manual-divider {{
      border: none;
      height: 1.5px;
      background: var(--border-color);
      margin: 36px 0;
    }}

    /* 인용구 및 하이라이트 박스 */
    .manual-quote {{
      background: var(--quote-bg);
      border-left: 5px solid var(--accent-gold);
      padding: 16px 20px;
      border-radius: 0 10px 10px 0;
      margin: 20px 0;
      font-size: 1.02em;
      color: #4A3525;
      font-weight: 500;
      line-height: 1.75;
    }}

    /* 목록 스타일 */
    .manual-li {{
      list-style-type: none;
      position: relative;
      padding-left: 24px;
      margin-bottom: 10px;
      color: var(--text-main);
      word-break: keep-all;
    }}

    .manual-li::before {{
      content: "•";
      color: var(--accent-gold);
      font-size: 1.4em;
      position: absolute;
      left: 6px;
      top: -3px;
    }}

    /* 번호형 아이템 */
    .manual-num-item {{
      display: flex;
      align-items: flex-start;
      gap: 12px;
      margin-bottom: 12px;
      word-break: keep-all;
    }}

    .num-badge {{
      background: var(--accent-soft);
      color: var(--primary-brown);
      font-weight: 700;
      padding: 2px 8px;
      border-radius: 6px;
      font-size: 0.9em;
      flex-shrink: 0;
      margin-top: 3px;
    }}

    .num-content {{
      flex: 1;
    }}

    /* 코드 및 강조 블록 */
    .manual-box-wrapper {{
      margin: 22px 0;
    }}

    .manual-box {{
      background: #FDFBF7;
      border: 1.5px solid #E6D7C3;
      border-radius: 10px;
      padding: 18px 20px;
      font-family: inherit;
      font-size: 0.93em;
      line-height: 1.7;
      color: #3C3026;
      white-space: pre-wrap;
      overflow-x: auto;
      box-shadow: inset 0 1px 3px rgba(0,0,0,0.02);
    }}

    code {{
      background: #F5EDE0;
      color: #8C4303;
      padding: 2px 6px;
      border-radius: 5px;
      font-size: 0.92em;
      font-family: inherit;
      font-weight: 600;
    }}

    strong {{
      color: #1A1410;
      font-weight: 700;
    }}

    .manual-link {{
      color: var(--primary-brown);
      text-decoration: underline;
      font-weight: 600;
    }}

    /* 표(Table) 스타일 */
    .table-responsive {{
      overflow-x: auto;
      margin: 24px 0;
      border-radius: 10px;
      border: 1.5px solid var(--border-color);
      box-shadow: 0 2px 6px rgba(0,0,0,0.03);
    }}

    .manual-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.94em;
      background: #FFFFFF;
    }}

    .manual-table th {{
      background: #F5ECE0;
      color: var(--primary-dark);
      padding: 14px 16px;
      font-weight: 700;
      border-bottom: 2px solid var(--border-color);
      text-align: left;
    }}

    .manual-table td {{
      padding: 14px 16px;
      border-bottom: 1px solid #F0E6D8;
      color: var(--text-main);
      vertical-align: top;
      line-height: 1.7;
    }}

    .manual-table tr:last-child td {{
      border-bottom: none;
    }}

    .manual-table tr:nth-child(even) {{
      background: #FCFAF6;
    }}

    /* 인쇄 최적화 */
    @media print {{
      .manual-topbar {{
        display: none !important;
      }}
      body {{
        background: #FFFFFF;
        color: #000000;
      }}
      .manual-container {{
        border: none;
        box-shadow: none;
        padding: 0;
        margin: 0;
        max-width: 100%;
      }}
    }}
  </style>
</head>
<body>

  <!-- 상단 제어 바 -->
  <header class="manual-topbar">
    <div class="manual-brand">
      <span class="manual-brand-icon">📖</span>
      <span class="manual-brand-title">StoryBook Studio 공식 사용 설명서</span>
    </div>
    <div class="manual-controls">
      <button type="button" class="btn-ctrl" onclick="cycleFontSize()" title="어르신을 위한 글자 크기 변경">
        <span>🔍 글자 크기: <strong id="fontSizeLabel">보통 (17px)</strong></span>
      </button>
      <button type="button" class="btn-ctrl" onclick="window.print()" title="설명서 종이 인쇄하기">
        <span>🖨️ 인쇄하기</span>
      </button>
      <button type="button" class="btn-ctrl btn-primary" onclick="window.close()" title="설명서 창 닫기">
        <span>닫기 ✕</span>
      </button>
    </div>
  </header>

  <!-- 본문 컨테이너 -->
  <main class="manual-container">
    {body_html}
  </main>

  <script>
    let currentFontSizeIdx = 0;
    const fontSizes = [
      {{ name: "보통 (17px)", cls: "" }},
      {{ name: "크게 (19px)", cls: "font-large" }},
      {{ name: "아주 크게 (21px)", cls: "font-xlarge" }}
    ];

    function cycleFontSize() {{
      currentFontSizeIdx = (currentFontSizeIdx + 1) % fontSizes.length;
      const target = fontSizes[currentFontSizeIdx];
      
      document.body.classList.remove("font-large", "font-xlarge");
      if (target.cls) {{
        document.body.classList.add(target.cls);
      }}
      document.getElementById("fontSizeLabel").innerText = target.name;
    }}
  </script>
</body>
</html>
"""

    out_path.write_text(template, encoding="utf-8")
    print(f"Success! manual.html generated at {out_path} ({len(template):,} bytes)")

if __name__ == "__main__":
    build_manual_html()
