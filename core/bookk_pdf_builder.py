"""
core/bookk_pdf_builder.py
부크크(Bookk) POD 자가출판 플랫폼 전용 300DPI 인쇄 완제본 및 표지 펼침면 PDF 빌더 엔진
- 사륙판 (128 x 188 mm) / 국판 (148 x 210 mm) 공식 규격 지원
- 사방 3mm 도련(Bleed) 및 20mm 제본 여백(Gutter) 자동 계산
- 폰트 100% 임베딩 및 300DPI 초고화질 출력
- 내지(본문) 완제본 PDF 및 표지(앞표지+책등+뒤표지) 펼침면 PDF 동시 지원
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from PIL import Image

from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from core.config import BASE_DIR, PAPER_THICKNESS
from core.manuscript import ManuscriptManager
from core.project_manager import project_manager, ProjectInfo
from core.image_optimizer import ensure_300dpi_image

# 1mm = 2.834645669291339 pt (ReportLab 포인트 단위)
MM_TO_PT = 2.834645669291339

# 폰트 등록 (최우선: 프로젝트 동봉 부크크 명조 -> 나눔명조 -> 시스템 폰트)
FONT_NAME = "BookkMyungjo"
FONT_BOLD_NAME = "BookkMyungjo-Bold"

LOCAL_FONTS_DIR = Path(__file__).parent / "fonts"

FONT_PATHS = [
    # 1. 프로젝트 내장 번들 폰트 (별도 폰트 설치 없는 완전 무설치 배포용)
    (str(LOCAL_FONTS_DIR / "BookkMyungjo-Lt.ttf"), str(LOCAL_FONTS_DIR / "BookkMyungjo-Bd.ttf")),
    (str(LOCAL_FONTS_DIR / "BookkMyungjo.ttf"), str(LOCAL_FONTS_DIR / "BookkMyungjo-Bold.ttf")),
    (str(LOCAL_FONTS_DIR / "NanumMyeongjo.ttf"), str(LOCAL_FONTS_DIR / "NanumMyeongjoBold.ttf")),
    # 2. 윈도우 시스템 설치 폰트
    ("C:/Windows/Fonts/BookkMyungjo-Lt.ttf", "C:/Windows/Fonts/BookkMyungjo-Bd.ttf"),
    ("C:/Windows/Fonts/NanumMyeongjo.ttf", "C:/Windows/Fonts/NanumMyeongjoBold.ttf"),
    ("C:/Windows/Fonts/batang.ttc", "C:/Windows/Fonts/batang.ttc"),
    ("C:/Windows/Fonts/malgun.ttf", "C:/Windows/Fonts/malgunbd.ttf"),
    ("C:/Windows/Fonts/gulim.ttc", "C:/Windows/Fonts/gulim.ttc"),
]

for regular_path, bold_path in FONT_PATHS:
    if os.path.exists(regular_path):
        try:
            pdfmetrics.registerFont(TTFont(FONT_NAME, regular_path))
            if os.path.exists(bold_path):
                pdfmetrics.registerFont(TTFont(FONT_BOLD_NAME, bold_path))
            else:
                pdfmetrics.registerFont(TTFont(FONT_BOLD_NAME, regular_path))
            break
        except Exception:
            pass

# 판형별 규격 정의 (mm 단위)
BOOKK_FORMATS = {
    "b6_mod": {
        "name": "사륙판 (B6 변형 / 감성 시집 추천)",
        "trim_w_mm": 128.0,
        "trim_h_mm": 188.0,
        "bleed_mm": 3.0,
        "gutter_mm": 20.0,   # 제본 여백 (안쪽)
        "safe_margin_mm": 15.0  # 안전 여백 (바깥쪽)
    },
    "a5": {
        "name": "국판 (A5 / 표준 단행본)",
        "trim_w_mm": 148.0,
        "trim_h_mm": 210.0,
        "bleed_mm": 3.0,
        "gutter_mm": 20.0,
        "safe_margin_mm": 15.0
    }
}


class BookkPDFBuilder:
    """부크크 인쇄 검수 100% 통과를 위한 정밀 PDF 빌더 클래스"""

    def __init__(self, format_key: str = "a5", paper_type: str = "white_100g"):
        self.format_key = format_key if format_key in BOOKK_FORMATS else "a5"
        self.spec = BOOKK_FORMATS[self.format_key]
        self.paper_type = paper_type

        # 도련(Bleed 3mm) 포함 캔버스 크기 계산 (mm -> pt)
        self.canvas_w_mm = self.spec["trim_w_mm"] + (self.spec["bleed_mm"] * 2)
        self.canvas_h_mm = self.spec["trim_h_mm"] + (self.spec["bleed_mm"] * 2)

        self.canvas_w_pt = self.canvas_w_mm * MM_TO_PT
        self.canvas_h_pt = self.canvas_h_mm * MM_TO_PT

        self.bleed_pt = self.spec["bleed_mm"] * MM_TO_PT
        self.gutter_pt = self.spec["gutter_mm"] * MM_TO_PT
        self.safe_margin_pt = self.spec["safe_margin_mm"] * MM_TO_PT

    def get_page_margins(self, page_num: int) -> Dict[str, float]:
        """
        페이지 번호(홀/짝)에 따른 정밀 제본 여백(Gutter) 및 안전 여백 계산
        - 짝수 페이지 (좌측면): 우측이 책등(제본선), 좌측이 바깥쪽
        - 홀수 페이지 (우측면): 좌측이 책등(제본선), 우측이 바깥쪽
        """
        is_odd = (page_num % 2 != 0)

        if is_odd:
            # 홀수 페이지: 좌측이 제본선
            margin_left = self.bleed_pt + self.gutter_pt
            margin_right = self.bleed_pt + self.safe_margin_pt
        else:
            # 짝수 페이지: 우측이 제본선
            margin_left = self.bleed_pt + self.safe_margin_pt
            margin_right = self.bleed_pt + self.gutter_pt

        margin_top = self.bleed_pt + (18.0 * MM_TO_PT)
        margin_bottom = self.bleed_pt + (16.0 * MM_TO_PT)

        return {
            "left": margin_left,
            "right": margin_right,
            "top": margin_top,
            "bottom": margin_bottom,
            "is_odd": is_odd,
            "content_w": self.canvas_w_pt - (margin_left + margin_right)
        }

    def build_interior_pdf(
        self,
        output_path: Path,
        manuscript_manager: Optional[ManuscriptManager] = None,
        project_info: Optional[ProjectInfo] = None,
        images_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        부크크 내지(본문) 완제본 PDF 빌드
        도비라(속표지) -> 서문 -> 목차 -> 본문 조판(삽화 전면 + 시 본문) -> 판권지
        """
        if project_info is None:
            project_info = project_manager.get_active_project_info()
        if manuscript_manager is None:
            manuscript_manager = project_manager.get_active_manuscript_manager()
        if images_dir is None:
            images_dir = project_manager.get_active_images_dir()

        works = manuscript_manager.load_works()
        distinct_authors = set(getattr(w, 'author', '').strip() for w in works if getattr(w, 'author', '').strip())
        is_collab = (getattr(project_info, 'author_type', 'single') == 'collab') or (len(distinct_authors) > 1)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        c = canvas.Canvas(str(output_path), pagesize=(self.canvas_w_pt, self.canvas_h_pt))
        current_page = 1

        # -------------------------------------------------------------------------
        # 1. 속표지 (도비라) - Page 1 (홀수)
        # -------------------------------------------------------------------------
        m1 = self.get_page_margins(current_page)
        self._draw_page_background(c)

        center_x = m1["left"] + (m1["content_w"] / 2)
        center_y = self.canvas_h_pt / 2

        c.setFillColorRGB(0.18, 0.16, 0.15)
        c.setFont(FONT_BOLD_NAME, 22)
        c.drawCentredString(center_x, center_y + 60, project_info.name)

        if project_info.subtitle:
            c.setFillColorRGB(0.42, 0.38, 0.35)
            c.setFont(FONT_NAME, 11)
            c.drawCentredString(center_x, center_y + 25, project_info.subtitle)

        # 서정 구분선
        c.setStrokeColorRGB(0.75, 0.65, 0.55)
        c.setLineWidth(0.8)
        c.line(center_x - 30, center_y, center_x + 30, center_y)

        c.setFillColorRGB(0.3, 0.28, 0.26)
        c.setFont(FONT_NAME, 11)
        author_type = getattr(project_info, 'author_type', 'single')
        author_role = "엮은이" if author_type == "collab" else "지은이"
        author_text = project_info.author
        if not any(k in author_text for k in ["지은이", "엮은이", "엮음", "지음"]):
            author_text = f"{author_role}  {author_text}"
        c.drawCentredString(center_x, center_y - 35, author_text)

        c.setFillColorRGB(0.55, 0.52, 0.48)
        c.setFont(FONT_NAME, 8.5)
        c.drawCentredString(center_x, m1["bottom"] + 20, "StoryBook Studio 출판본")

        c.showPage()
        current_page += 1

        # -------------------------------------------------------------------------
        # 2. 백면 또는 서문 준비 - Page 2 (짝수)
        # -------------------------------------------------------------------------
        self._draw_page_background(c)
        c.showPage()
        current_page += 1

        # -------------------------------------------------------------------------
        # 3. 시인의 말 (서문) - Page 3 (홀수)
        # -------------------------------------------------------------------------
        m3 = self.get_page_margins(current_page)
        self._draw_page_background(c)

        c.setFillColorRGB(0.2, 0.18, 0.17)
        c.setFont(FONT_BOLD_NAME, 16)
        c.drawString(m3["left"], self.canvas_h_pt - m3["top"], "시인의 말")

        c.setStrokeColorRGB(0.85, 0.8, 0.75)
        c.setLineWidth(0.8)
        c.line(m3["left"], self.canvas_h_pt - m3["top"] - 12, self.canvas_w_pt - m3["right"], self.canvas_h_pt - m3["top"] - 12)

        # 서문 텍스트: project_info.prologue가 있으면 사용, 없으면 품격 있는 기본 서문
        author_role = "엮음" if getattr(project_info, 'author_type', 'single') == "collab" else "지음"
        default_prologue = f"""가장 개인적인 기억이 가장 깊은 문학이자 예술이 된다.

이 시화집은 화려하게 꾸며낸 허구를 담지 않았습니다.
마음속 깊은 곳에 오래 고여 있던 찰나의 순간,
차갑게 식어가던 툇마루의 새벽과 그 시절 들었던 다정한 말 한마디를
온전한 나의 목소리와 수채의 빛깔로 빚어낸 삶의 기록입니다.

책장을 넘길 때마다 그날의 서정적 온기가
그리운 당신의 마음에 가만히 가닿기를 소망합니다.


― {project_info.author} {author_role}"""

        prologue_content = getattr(project_info, 'prologue', '').strip() or default_prologue
        prologue_lines = [l.rstrip() for l in prologue_content.split("\n")]

        p_font = 9.2 if len(prologue_lines) > 16 else 9.8
        p_line_h = 16.0 if len(prologue_lines) > 16 else 18.0
        c.setFont(FONT_NAME, p_font)
        c.setFillColorRGB(0.25, 0.23, 0.22)

        curr_y = self.canvas_h_pt - m3["top"] - 45
        for line in prologue_lines:
            c.drawString(m3["left"], curr_y, line)
            curr_y -= p_line_h

        self._draw_page_number(c, current_page, m3)
        c.showPage()
        current_page += 1

        # -------------------------------------------------------------------------
        # 4. 목차 (Contents) - Page 4 (및 작품 수에 따른 Page 5 확장)
        # -------------------------------------------------------------------------
        # 각 작품의 실제 본문 시작 페이지 사전 계산 (Page 6부터 시작)
        # 목차가 1페이지(15편 이하)면 Page 6 시작, 2페이지(16편 이상)여도 Page 6 시작
        work_pages = []
        body_start_p = 6
        accum_p = body_start_p
        for w in works:
            cfg = getattr(w, 'layout_config', None)
            lines_cnt = len((w.poem_body or "").split("\n"))
            if cfg and isinstance(cfg, dict) and "slots" in cfg and cfg.get("slots"):
                p_span = cfg.get("page_count", 2)
            elif getattr(w, 'layout_mode', 'compact') == "multi_page" and lines_cnt > 16:
                p_span = 4
            else:
                p_span = 2
            work_pages.append((w, accum_p))
            accum_p += p_span

        # 4-1) 목차 1페이지 (Page 4)
        m4 = self.get_page_margins(current_page)
        self._draw_page_background(c)

        c.setFillColorRGB(0.2, 0.18, 0.17)
        c.setFont(FONT_BOLD_NAME, 15)
        c.drawString(m4["left"], self.canvas_h_pt - m4["top"], "차 례")

        c.setStrokeColorRGB(0.85, 0.8, 0.75)
        c.setLineWidth(0.8)
        c.line(m4["left"], self.canvas_h_pt - m4["top"] - 12, self.canvas_w_pt - m4["right"], self.canvas_h_pt - m4["top"] - 12)

        curr_y = self.canvas_h_pt - m4["top"] - 45
        c.setFont(FONT_NAME, 9.2)

        page1_works = work_pages[:16]
        page2_works = work_pages[16:]

        for w, start_p in page1_works:
            c.setFillColorRGB(0.5, 0.38, 0.3)
            c.drawString(m4["left"], curr_y, f"{w.episode_no}")

            work_author = getattr(w, 'author', '').strip()
            display_title = f"{w.title} ({work_author})" if work_author else w.title

            c.setFillColorRGB(0.22, 0.2, 0.19)
            c.drawString(m4["left"] + 38, curr_y, display_title)

            # 점선 연결
            c.setFillColorRGB(0.72, 0.68, 0.64)
            title_w = c.stringWidth(display_title, FONT_NAME, 9.2)
            dots_x = m4["left"] + 42 + title_w
            target_x = self.canvas_w_pt - m4["right"] - 25
            if target_x > dots_x + 10:
                dots = ". " * int((target_x - dots_x) / 7.5)
                c.drawString(dots_x, curr_y, dots)

            c.drawRightString(self.canvas_w_pt - m4["right"], curr_y, str(start_p))
            curr_y -= 17.5

        self._draw_page_number(c, current_page, m4)
        c.showPage()
        current_page += 1

        # 4-2) Page 5 (목차 2페이지 또는 서정 여백면)
        m5 = self.get_page_margins(current_page)
        self._draw_page_background(c)

        if page2_works:
            # 목차가 16편 이상이어서 2페이지로 이어짐
            c.setFillColorRGB(0.2, 0.18, 0.17)
            c.setFont(FONT_BOLD_NAME, 15)
            c.drawString(m5["left"], self.canvas_h_pt - m5["top"], "차 례 (이어서)")

            c.setStrokeColorRGB(0.85, 0.8, 0.75)
            c.setLineWidth(0.8)
            c.line(m5["left"], self.canvas_h_pt - m5["top"] - 12, self.canvas_w_pt - m5["right"], self.canvas_h_pt - m5["top"] - 12)

            curr_y = self.canvas_h_pt - m5["top"] - 45
            c.setFont(FONT_NAME, 9.2)

            for w, start_p in page2_works[:16]:
                c.setFillColorRGB(0.5, 0.38, 0.3)
                c.drawString(m5["left"], curr_y, f"{w.episode_no}")

                work_author = getattr(w, 'author', '').strip()
                display_title = f"{w.title} ({work_author})" if work_author else w.title

                c.setFillColorRGB(0.22, 0.2, 0.19)
                c.drawString(m5["left"] + 38, curr_y, display_title)

                c.setFillColorRGB(0.72, 0.68, 0.64)
                title_w = c.stringWidth(display_title, FONT_NAME, 9.2)
                dots_x = m5["left"] + 42 + title_w
                target_x = self.canvas_w_pt - m5["right"] - 25
                if target_x > dots_x + 10:
                    dots = ". " * int((target_x - dots_x) / 7.5)
                    c.drawString(dots_x, curr_y, dots)

                c.drawRightString(self.canvas_w_pt - m5["right"], curr_y, str(start_p))
                curr_y -= 17.5
        else:
            # 목차가 15편 이하인 경우: 서정적 문학 심볼과 여백의 미
            center_x = m5["left"] + (m5["content_w"] / 2)
            center_y = self.canvas_h_pt / 2
            c.setFillColorRGB(0.75, 0.7, 0.65)
            c.setFont(FONT_NAME, 20)
            c.drawCentredString(center_x, center_y + 10, "❦")
            c.setFont(FONT_NAME, 9.0)
            c.setFillColorRGB(0.55, 0.52, 0.48)
            c.drawCentredString(center_x, center_y - 20, "기억의 문을 열며")

        self._draw_page_number(c, current_page, m5)
        c.showPage()
        current_page += 1

        # -------------------------------------------------------------------------
        # 5. 본문 렌더링 (2페이지 1작품: 좌측 삽화 전면 + 우측 시 본문)
        # -------------------------------------------------------------------------
        for work in works:
            cfg = getattr(work, 'layout_config', None)
            lines = [l.rstrip() for l in (work.poem_body or "").split("\n")]

            # -------------------------------------------------------------
            # [신규 통합 매트릭스 슬롯 & DTP 2-Layer 시스템 렌더링]
            # -------------------------------------------------------------
            if cfg and isinstance(cfg, dict) and (cfg.get("slots") or cfg.get("pages")):
                page_count = cfg.get("page_count", 2)
                text_align = cfg.get("text_align", "left")

                def draw_aligned_text(canvas, line_str, bx, cy, align_mode, bw):
                    if not line_str:
                        return
                    if align_mode == "center":
                        canvas.drawCentredString(bx + (bw / 2.0), cy, line_str)
                    elif align_mode == "right":
                        canvas.drawRightString(bx + bw, cy, line_str)
                    else:
                        canvas.drawString(bx, cy, line_str)
                pages_meta = cfg.get("pages", [])
                raw_slots = cfg.get("slots", [])
                raw_roles = cfg.get("page_roles", [])
                img_settings = cfg.get("image_settings", {})
                cfg_pt = float(cfg.get("font_size_pt", 13) or 13)
                backdrop_opacity = float(cfg.get("backdrop_opacity", 0.85))
                is_light_text = (cfg.get("text_color_mode") == "light")

                slots = []
                roles = []
                for idx in range(page_count):
                    p_obj = pages_meta[idx] if idx < len(pages_meta) and isinstance(pages_meta[idx], dict) else {}
                    s_val = p_obj.get("usage") or (raw_slots[idx] if idx < len(raw_slots) else ("image" if idx == 0 else "text"))
                    r_val = p_obj.get("role") or (raw_roles[idx] if idx < len(raw_roles) else ("none" if s_val in ("image", "blank") else ("start" if idx == 1 else "continue")))
                    slots.append(s_val)
                    roles.append(r_val)

                # 텍스트 슬롯 인덱스 & 순차 용량(Capacity) 배분
                text_slot_indices = [
                    idx for idx, s in enumerate(slots)
                    if s in ("text", "image_text", "image_top", "image_bottom", "mixed_top", "mixed_bottom")
                    and roles[idx] not in ("none", "independent")
                ]
                text_count = len(text_slot_indices)

                # DTP 코어와 동일한 순차 용량 기반 분할 (남는 행만 뒷면으로 이월)
                chunks = []
                cursor = 0
                for t_i, s_idx in enumerate(text_slot_indices):
                    role_here = roles[s_idx]
                    is_last_slot = (t_i == text_count - 1)
                    p_obj_here = pages_meta[s_idx] if s_idx < len(pages_meta) and isinstance(pages_meta[s_idx], dict) else {}
                    custom_cap = p_obj_here.get("max_lines")
                    if custom_cap and int(custom_cap) > 0:
                        cap = int(custom_cap)
                    elif cfg_pt >= 13:
                        cap = 13 if role_here == "start" else 16
                    elif cfg_pt >= 12:
                        cap = 15 if role_here == "start" else 18
                    elif cfg_pt >= 11:
                        cap = 17 if role_here == "start" else 20
                    else:
                        cap = 20 if role_here == "start" else 23
                    if is_last_slot:
                        chunks.append(lines[cursor:])
                        cursor = len(lines)
                    else:
                        chunks.append(lines[cursor:cursor + cap])
                        cursor += cap

                chunk_map = {slot_idx: i for i, slot_idx in enumerate(text_slot_indices)}

                for slot_idx, slot_type in enumerate(slots):
                    m = self.get_page_margins(current_page)
                    self._draw_page_background(c)
                    page_in_work = slot_idx + 1
                    role_here = roles[slot_idx]
                    p_obj = pages_meta[slot_idx] if slot_idx < len(pages_meta) and isinstance(pages_meta[slot_idx], dict) else {}

                    if slot_type in ("text", "image_text"):
                        # 1) image_text인 경우 배경 삽화 + 한지 가독성 필터 먼저 렌더링
                        if slot_type == "image_text":
                            img_cfg = img_settings.get(f"page_{page_in_work}", {})
                            img_file = p_obj.get("image_file") or img_cfg.get("file") or (work.image_file if page_in_work == 1 else (getattr(work, 'image_file_2', '') or work.image_file))
                            if img_file:
                                box_x = m["left"]
                                box_y = m["bottom"] + 15
                                box_w = m["content_w"]
                                box_h = self.canvas_h_pt - (m["top"] + m["bottom"] + 15)
                                self._draw_artwork(c, work, images_dir, box_x, box_y, box_w, box_h, img_override_file=img_file)
                            # 한지 가독성 필터 오버레이
                            c.saveState()
                            if hasattr(c, "setFillAlpha"):
                                c.setFillAlpha(max(0.0, min(1.0, backdrop_opacity)))
                            c.setFillColorRGB(0.996, 0.988, 0.973)
                            c.rect(m["left"] - 4, m["bottom"] + 10, m["content_w"] + 8, self.canvas_h_pt - (m["top"] + m["bottom"] + 5), fill=1, stroke=0)
                            c.restoreState()

                        # 2) 독립 자유글(independent) vs 시 본문(start/continue)
                        if role_here == "independent":
                            custom_txt = p_obj.get("custom_text") or ""
                            ind_lines = [l.rstrip() for l in custom_txt.split("\n")]
                            top_y = self.canvas_h_pt - m["top"] - 16
                            p_font_size = max(8.0, min(14.0, cfg_pt * 0.82))
                            line_h = p_font_size * float(cfg.get("line_height_ratio", 1.6))
                            if slot_type == "image_text" and is_light_text:
                                c.setFillColorRGB(0.99, 0.98, 0.96)
                            else:
                                c.setFillColorRGB(0.24, 0.22, 0.21)
                            c.setFont(FONT_NAME, p_font_size)
                            curr_y = top_y
                            box_avail_w = self.canvas_w_pt - m["right"] - body_x
                            for line in ind_lines:
                                if curr_y < m["bottom"] + 15:
                                    break
                                draw_aligned_text(c, line, body_x, curr_y, text_align, box_avail_w)
                                curr_y -= line_h
                        elif role_here != "none":
                            c_idx = chunk_map.get(slot_idx, 0)
                            chunk_lines = chunks[c_idx] if c_idx < len(chunks) else []
                            is_first = (role_here == "start") or (c_idx == 0 and "start" not in roles)
                            is_last = (c_idx == text_count - 1) or (c_idx + 1 < len(chunks) and len(chunks[c_idx + 1]) == 0)

                            top_y = self.canvas_h_pt - m["top"]
                            pages_list = cfg.get("pages", [])
                            page_info = pages_list[slot_idx] if slot_idx < len(pages_list) else {}
                            top_offset_pt = float(page_info.get("top_offset", 0)) * 0.75
                            left_offset_pt = float(page_info.get("left_offset", 0)) * 0.75
                            right_offset_pt = float(page_info.get("right_offset", 0)) * 0.75
                            body_x = m["left"] + left_offset_pt

                            if is_first:
                                # 첫 텍스트 면: 제목 및 시인 표기
                                if slot_type == "image_text" and is_light_text:
                                    c.setFillColorRGB(0.99, 0.98, 0.96)
                                else:
                                    c.setFillColorRGB(0.18, 0.16, 0.15)
                                c.setFont(FONT_BOLD_NAME, 16.0)
                                c.drawString(m["left"], top_y, work.title)

                                work_author = getattr(work, 'author', '').strip()
                                if is_collab and work_author:
                                    c.setFont(FONT_NAME, 9.5)
                                    c.setFillColorRGB(0.48, 0.42, 0.38)
                                    c.drawRightString(self.canvas_w_pt - m["right"], top_y + 2, f"{work_author}")

                                c.setStrokeColorRGB(0.86, 0.82, 0.78)
                                c.setLineWidth(0.8)
                                c.line(m["left"], top_y - 10, self.canvas_w_pt - m["right"], top_y - 10)
                                curr_y = top_y - 32 - top_offset_pt
                            else:
                                # 시 이어짐 면: 제목 영역(32pt)을 동일하게 확보하여 모든 면의 본문 시작선 완벽 통일
                                curr_y = top_y - 32 - top_offset_pt

                            p_font_size = max(8.0, min(14.0, cfg_pt * 0.80))
                            line_h = p_font_size * float(cfg.get("line_height_ratio", 1.6))
                            if slot_type == "image_text" and is_light_text:
                                c.setFillColorRGB(0.99, 0.98, 0.96)
                            else:
                                c.setFillColorRGB(0.24, 0.22, 0.21)
                            c.setFont(FONT_NAME, p_font_size)
                            box_avail_w = max(50.0, self.canvas_w_pt - m["right"] - right_offset_pt - body_x)
                            for line in chunk_lines:
                                if curr_y < m["bottom"] + 15:
                                    break
                                draw_aligned_text(c, line, body_x, curr_y, text_align, box_avail_w)
                                curr_y -= line_h

                            if not is_last and len(chunk_lines) > 0:
                                c.setFillColorRGB(0.55, 0.50, 0.45)
                                c.setFont(FONT_NAME, 8.2)
                                next_p = page_in_work + 1
                                c.drawRightString(self.canvas_w_pt - m["right"], m["bottom"] + 15, f"(다음 {next_p}면에 계속 ➔)")

                    elif slot_type in ("image_top", "mixed_top"):
                        # [상단 그림 + 하단 시 본문 (엽서형 / 첫머리형)]
                        img_cfg = img_settings.get(f"page_{page_in_work}", {})
                        img_file = img_cfg.get("file", work.image_file if page_in_work == 1 else getattr(work, 'image_file_2', ''))

                        avail_h = self.canvas_h_pt - (m["top"] + m["bottom"] + 20)
                        img_h = avail_h * 0.42
                        img_y = self.canvas_h_pt - m["top"] - img_h

                        # 1) 상단 삽화 배치
                        if img_file:
                            self._draw_artwork(c, work, images_dir, m["left"], img_y, m["content_w"], img_h, img_override_file=img_file)

                        # 2) 하단 시 본문 배치
                        c_idx = chunk_map.get(slot_idx, 0)
                        chunk_lines = chunks[c_idx] if c_idx < len(chunks) else []
                        is_first = (c_idx == 0)
                        is_last = (c_idx == text_count - 1)

                        top_y = img_y - 16
                        if is_first:
                            c.setFillColorRGB(0.18, 0.16, 0.15)
                            c.setFont(FONT_BOLD_NAME, 13.5)
                            c.drawString(m["left"], top_y, work.title)

                            work_author = getattr(work, 'author', '').strip()
                            if work_author:
                                c.setFont(FONT_NAME, 8.5)
                                c.setFillColorRGB(0.48, 0.42, 0.38)
                                c.drawRightString(self.canvas_w_pt - m["right"], top_y + 1, f"{work_author}")

                            c.setStrokeColorRGB(0.86, 0.82, 0.78)
                            c.setLineWidth(0.6)
                            c.line(m["left"], top_y - 7, self.canvas_w_pt - m["right"], top_y - 7)
                            curr_y = top_y - 20
                        else:
                            c.setFillColorRGB(0.55, 0.50, 0.45)
                            c.setFont(FONT_NAME, 7.5)
                            c.drawString(m["left"], top_y - 5, f"({slot_idx}면에 이어짐 ➔ {page_in_work}면 본문)")
                            curr_y = top_y - 18

                        p_font_size, line_h = 8.5, 14.5
                        c.setFillColorRGB(0.24, 0.22, 0.21)
                        c.setFont(FONT_NAME, p_font_size)
                        box_avail_w = self.canvas_w_pt - m["right"] - body_x
                        for line in chunk_lines:
                            if curr_y < m["bottom"] + 15:
                                break
                            draw_aligned_text(c, line, body_x, curr_y, text_align, box_avail_w)
                            curr_y -= line_h

                        if not is_last:
                            c.setFillColorRGB(0.55, 0.50, 0.45)
                            c.setFont(FONT_NAME, 7.5)
                            next_p = page_in_work + 1
                            c.drawRightString(self.canvas_w_pt - m["right"], m["bottom"] + 12, f"(다음 {next_p}면에 계속 ➔)")

                    elif slot_type in ("image_bottom", "mixed_bottom"):
                        # [상단 시 본문 + 하단 그림 (여운형)]
                        img_cfg = img_settings.get(f"page_{page_in_work}", {})
                        img_file = img_cfg.get("file", work.image_file if page_in_work == 1 else getattr(work, 'image_file_2', ''))

                        avail_h = self.canvas_h_pt - (m["top"] + m["bottom"] + 20)
                        img_h = avail_h * 0.40
                        img_y = m["bottom"] + 18
                        text_limit_y = img_y + img_h + 12

                        # 1) 상단 시 본문 배치
                        c_idx = chunk_map.get(slot_idx, 0)
                        chunk_lines = chunks[c_idx] if c_idx < len(chunks) else []
                        is_first = (c_idx == 0)
                        is_last = (c_idx == text_count - 1)

                        top_y = self.canvas_h_pt - m["top"]
                        if is_first:
                            c.setFillColorRGB(0.18, 0.16, 0.15)
                            c.setFont(FONT_BOLD_NAME, 13.5)
                            c.drawString(m["left"], top_y, work.title)

                            work_author = getattr(work, 'author', '').strip()
                            if work_author:
                                c.setFont(FONT_NAME, 8.5)
                                c.setFillColorRGB(0.48, 0.42, 0.38)
                                c.drawRightString(self.canvas_w_pt - m["right"], top_y + 1, f"{work_author}")

                            c.setStrokeColorRGB(0.86, 0.82, 0.78)
                            c.setLineWidth(0.6)
                            c.line(m["left"], top_y - 7, self.canvas_w_pt - m["right"], top_y - 7)
                            curr_y = top_y - 20
                        else:
                            c.setFillColorRGB(0.55, 0.50, 0.45)
                            c.setFont(FONT_NAME, 7.5)
                            c.drawString(m["left"], top_y - 5, f"({slot_idx}면에 이어짐 ➔ {page_in_work}면 본문)")
                            curr_y = top_y - 18

                        p_font_size, line_h = 8.5, 14.5
                        c.setFillColorRGB(0.24, 0.22, 0.21)
                        c.setFont(FONT_NAME, p_font_size)
                        box_avail_w = self.canvas_w_pt - m["right"] - body_x
                        for line in chunk_lines:
                            if curr_y < text_limit_y:
                                break
                            draw_aligned_text(c, line, body_x, curr_y, text_align, box_avail_w)
                            curr_y -= line_h

                        # 2) 하단 삽화 배치
                        if img_file:
                            self._draw_artwork(c, work, images_dir, m["left"], img_y, m["content_w"], img_h, img_override_file=img_file)

                        if not is_last:
                            c.setFillColorRGB(0.55, 0.50, 0.45)
                            c.setFont(FONT_NAME, 7.5)
                            next_p = page_in_work + 1
                            c.drawRightString(self.canvas_w_pt - m["right"], m["bottom"] + 12, f"(다음 {next_p}면에 계속 ➔)")

                    else:
                        # image 또는 blank 슬롯
                        img_cfg = img_settings.get(f"page_{page_in_work}", {})
                        img_file = p_obj.get("image_file") or img_cfg.get("file") or (work.image_file if page_in_work == 1 else (getattr(work, 'image_file_2', '') or work.image_file))
                        default_mode = "motif_symbol" if slot_type == "blank" else ("image" if img_file else "motif_symbol")
                        mode = "motif_symbol" if slot_type == "blank" else img_cfg.get("mode", default_mode)

                        if mode == "image" and img_file and slot_type != "blank":
                            box_x = m["left"]
                            box_y = m["bottom"] + 15
                            box_w = m["content_w"]
                            box_h = self.canvas_h_pt - (m["top"] + m["bottom"] + 15)
                            img_layout = p_obj.get("image_layout", "single")
                            img_file_2 = p_obj.get("image_file_2") or getattr(work, "image_file_2", "") or img_file

                            if img_layout == "split_vertical":
                                gap = 10
                                half_h = (box_h - gap) / 2
                                self._draw_artwork(c, work, images_dir, box_x, box_y + half_h + gap, box_w, half_h, img_override_file=img_file)
                                self._draw_artwork(c, work, images_dir, box_x, box_y, box_w, half_h, img_override_file=img_file_2)
                            elif img_layout == "split_horizontal":
                                gap = 10
                                half_w = (box_w - gap) / 2
                                self._draw_artwork(c, work, images_dir, box_x, box_y, half_w, box_h, img_override_file=img_file)
                                self._draw_artwork(c, work, images_dir, box_x + half_w + gap, box_y, half_w, box_h, img_override_file=img_file_2)
                            elif img_layout == "main_detail":
                                gap = 10
                                detail_h = (box_h - gap) * 0.30
                                main_h = (box_h - gap) * 0.70
                                self._draw_artwork(c, work, images_dir, box_x, box_y + detail_h + gap, box_w, main_h, img_override_file=img_file)
                                detail_w = min(box_w, detail_h * 1.3)
                                detail_x = box_x + (box_w - detail_w) / 2
                                self._draw_artwork(c, work, images_dir, detail_x, box_y, detail_w, detail_h, img_override_file=img_file_2)
                            else:
                                self._draw_artwork(c, work, images_dir, box_x, box_y, box_w, box_h, img_override_file=img_file)

                        elif mode == "pure_blank":
                            pass
                        else:
                            # motif_symbol
                            center_x = m["left"] + (m["content_w"] / 2)
                            center_y = self.canvas_h_pt / 2
                            c.setFillColorRGB(0.78, 0.73, 0.68)
                            c.setFont(FONT_NAME, 18)
                            c.drawCentredString(center_x, center_y + 10, "❦")
                            c.setFont(FONT_NAME, 8.8)
                            c.setFillColorRGB(0.60, 0.56, 0.52)
                            motif_txt = img_cfg.get("motif_text", "여백 속에 머무는 시의 숨결")
                            c.drawCentredString(center_x, center_y - 20, motif_txt)

                    self._draw_page_number(c, current_page, m)
                    c.showPage()
                    current_page += 1

                continue

            # -------------------------------------------------------------
            # [기존 2P/4P Fallback 조판]
            # -------------------------------------------------------------
            # 5-1) 좌측 페이지 (짝수면) - 전면 삽화
            m_left = self.get_page_margins(current_page)
            self._draw_page_background(c)

            img_box_x = m_left["left"]
            img_box_y = m_left["bottom"] + 15
            img_box_w = m_left["content_w"]
            img_box_h = self.canvas_h_pt - (m_left["top"] + m_left["bottom"] + 15)

            self._draw_artwork(c, work, images_dir, img_box_x, img_box_y, img_box_w, img_box_h)
            self._draw_page_number(c, current_page, m_left)
            c.showPage()
            current_page += 1

            # 5-2) 우측 페이지 (홀수면) - 시 본문
            m_right = self.get_page_margins(current_page)
            self._draw_page_background(c)

            top_y = self.canvas_h_pt - m_right["top"]

            # 작품 제목 (인쇄용 본문에서 [제01화] 제외하여 상단 공간 대폭 확보!)
            c.setFillColorRGB(0.18, 0.16, 0.15)
            c.setFont(FONT_BOLD_NAME, 16.0)
            c.drawString(m_right["left"], top_y, work.title)

            # 개별 시인 표기 (공동/가족 시집이거나 시인 정보가 있는 경우)
            work_author = getattr(work, 'author', '').strip()
            if work_author:
                c.setFont(FONT_NAME, 9.5)
                c.setFillColorRGB(0.48, 0.42, 0.38)
                author_str = f"{work_author}"
                c.drawRightString(self.canvas_w_pt - m_right["right"], top_y + 2, author_str)

            # 서정 구분선
            c.setStrokeColorRGB(0.86, 0.82, 0.78)
            c.setLineWidth(0.8)
            c.line(m_right["left"], top_y - 10, self.canvas_w_pt - m_right["right"], top_y - 10)

            # 시 본문 줄간격 및 연속 조판 판별
            lines = [l.rstrip() for l in (work.poem_body or "").split("\n")]
            layout_mode = getattr(work, 'layout_mode', 'compact')

            if layout_mode == "multi_page" and len(lines) > 16:
                part2_mode = getattr(work, 'part2_mode', 'motif_symbol')

                if part2_mode == "poem_text":
                    # -------------------------------------------------------------
                    # [3페이지 장시 연속 조판] 3면(우측 전반) ➔ 4면(좌측 중반) ➔ 5면(우측 후반)
                    # -------------------------------------------------------------
                    total = len(lines)
                    one_third = total // 3
                    two_third = (total * 2) // 3

                    split1 = one_third
                    for offset in range(max(one_third, total - one_third)):
                        if one_third - offset >= 3 and lines[one_third - offset].strip() == "":
                            split1 = one_third - offset
                            break
                        if one_third + offset < two_third and lines[one_third + offset].strip() == "":
                            split1 = one_third + offset
                            break

                    split2 = two_third
                    for offset in range(max(total - two_third, two_third - split1)):
                        if two_third - offset > split1 + 3 and lines[two_third - offset].strip() == "":
                            split2 = two_third - offset
                            break
                        if two_third + offset < total - 3 and lines[two_third + offset].strip() == "":
                            split2 = two_third + offset
                            break

                    part1 = lines[:split1]
                    part2 = lines[split1:split2]
                    part3 = lines[split2:]
                    if part2 and part2[0].strip() == "":
                        part2 = part2[1:]
                    if part3 and part3[0].strip() == "":
                        part3 = part3[1:]

                    p_font_size, line_h = 9.5, 17.5

                    # 1) 3페이지 (1차 펼침면 우측: 시 전반부)
                    c.setFillColorRGB(0.24, 0.22, 0.21)
                    c.setFont(FONT_NAME, p_font_size)
                    curr_y = top_y - 32
                    for line in part1:
                        c.drawString(m_right["left"], curr_y, line)
                        curr_y -= line_h

                    c.setFillColorRGB(0.55, 0.50, 0.45)
                    c.setFont(FONT_NAME, 8.2)
                    c.drawRightString(self.canvas_w_pt - m_right["right"], m_right["bottom"] + 15, "(다음 4면에 계속 ➔)")
                    self._draw_page_number(c, current_page, m_right)
                    c.showPage()
                    current_page += 1

                    # 2) 4페이지 (2차 펼침면 좌측: 시 중간부 연속 수록)
                    m_left2 = self.get_page_margins(current_page)
                    self._draw_page_background(c)
                    top_y2 = self.canvas_h_pt - m_left2["top"]

                    c.setFillColorRGB(0.55, 0.50, 0.45)
                    c.setFont(FONT_NAME, 7.8)
                    c.drawString(m_left2["left"], top_y2 - 10, "(3면에 이어짐 ➔ 4면 본문)")

                    c.setFillColorRGB(0.24, 0.22, 0.21)
                    c.setFont(FONT_NAME, p_font_size)
                    curr_y2 = top_y2 - 32
                    for line in part2:
                        c.drawString(m_left2["left"], curr_y2, line)
                        curr_y2 -= line_h

                    c.setFillColorRGB(0.55, 0.50, 0.45)
                    c.setFont(FONT_NAME, 8.2)
                    c.drawRightString(self.canvas_w_pt - m_left2["right"], m_left2["bottom"] + 15, "(다음 5면에 계속 ➔)")
                    self._draw_page_number(c, current_page, m_left2)
                    c.showPage()
                    current_page += 1

                    # 3) 5페이지 (2차 펼침면 우측: 시 후반부/결미)
                    m_right2 = self.get_page_margins(current_page)
                    self._draw_page_background(c)
                    top_y3 = self.canvas_h_pt - m_right2["top"]
                    curr_y3 = top_y3 - 32
                    c.setFillColorRGB(0.24, 0.22, 0.21)
                    c.setFont(FONT_NAME, p_font_size)
                    for line in part3:
                        c.drawString(m_right2["left"], curr_y3, line)
                        curr_y3 -= line_h

                    self._draw_page_number(c, current_page, m_right2)
                    c.showPage()
                    current_page += 1

                else:
                    # -------------------------------------------------------------
                    # 기존 2페이지 연속 조판 (3면 우측 + 5면 우측 / 4면 좌측은 삽화·심볼·여백)
                    # -------------------------------------------------------------
                    mid = len(lines) // 2
                    split_idx = mid
                    for offset in range(max(mid, len(lines) - mid)):
                        if mid - offset > 5 and lines[mid - offset].strip() == "":
                            split_idx = mid - offset
                            break
                        if mid + offset < len(lines) - 5 and lines[mid + offset].strip() == "":
                            split_idx = mid + offset
                            break

                    part1 = lines[:split_idx]
                    part2 = lines[split_idx:]
                    if part2 and part2[0].strip() == "":
                        part2 = part2[1:]

                    # 1) Part 1 렌더링 (현재 홀수면)
                    p_font_size, line_h = 9.5, 17.5
                    c.setFillColorRGB(0.24, 0.22, 0.21)
                    c.setFont(FONT_NAME, p_font_size)
                    curr_y = top_y - 32
                    for line in part1:
                        c.drawString(m_right["left"], curr_y, line)
                        curr_y -= line_h

                    c.setFillColorRGB(0.55, 0.50, 0.45)
                    c.setFont(FONT_NAME, 8.2)
                    c.drawRightString(self.canvas_w_pt - m_right["right"], m_right["bottom"] + 15, "(다음 면에 이어짐 ➔)")
                    self._draw_page_number(c, current_page, m_right)
                    c.showPage()
                    current_page += 1

                    # 2) 2차 펼침면 - 좌측 (짝수면: 작가가 결정한 2부 좌측면 연출)
                    m_left2 = self.get_page_margins(current_page)
                    self._draw_page_background(c)

                    image_file_2 = getattr(work, 'image_file_2', '')

                    if part2_mode == "image" and image_file_2:
                        img2_box_x = m_left2["left"]
                        img2_box_y = m_left2["bottom"] + 15
                        img2_box_w = m_left2["content_w"]
                        img2_box_h = self.canvas_h_pt - (m_left2["top"] + m_left2["bottom"] + 15)
                        self._draw_artwork(c, work, images_dir, img2_box_x, img2_box_y, img2_box_w, img2_box_h, img_override_file=image_file_2)
                    elif part2_mode == "pure_blank":
                        # 순백의 여백: 본문에만 온전히 몰입하는 깨끗한 백면
                        pass
                    else:
                        # 은은한 문학적 여백 심볼 (기본)
                        center_lx = m_left2["left"] + (m_left2["content_w"] / 2)
                        center_ly = self.canvas_h_pt / 2
                        c.setFillColorRGB(0.78, 0.73, 0.68)
                        c.setFont(FONT_NAME, 18)
                        c.drawCentredString(center_lx, center_ly + 10, "❦")
                        c.setFont(FONT_NAME, 8.8)
                        c.setFillColorRGB(0.60, 0.56, 0.52)
                        c.drawCentredString(center_lx, center_ly - 20, "여백 속에 머무는 시의 숨결")

                    self._draw_page_number(c, current_page, m_left2)
                    c.showPage()
                    current_page += 1

                    # 3) 2차 펼침면 - 우측 (홀수면: Part 2 시 후반부 - 상단 제목 제외하고 곧바로 본문 연결)
                    m_right2 = self.get_page_margins(current_page)
                    self._draw_page_background(c)
                    top_y2 = self.canvas_h_pt - m_right2["top"]
                    curr_y2 = top_y2 - 32
                    c.setFillColorRGB(0.24, 0.22, 0.21)
                    c.setFont(FONT_NAME, p_font_size)
                    for line in part2:
                        c.drawString(m_right2["left"], curr_y2, line)
                        curr_y2 -= line_h

                    self._draw_page_number(c, current_page, m_right2)
                    c.showPage()
                    current_page += 1

            else:
                # -------------------------------------------------------------
                # 1페이지 안착 (compact 최적 조판)
                # -------------------------------------------------------------
                line_count = len(lines)
                if line_count > 25:
                    p_font_size, line_h = 8.2, 13.8
                elif line_count > 18:
                    p_font_size, line_h = 8.8, 15.5
                elif line_count > 13:
                    p_font_size, line_h = 9.5, 17.5
                else:
                    p_font_size, line_h = 10.0, 19.5

                c.setFillColorRGB(0.24, 0.22, 0.21)
                c.setFont(FONT_NAME, p_font_size)

                curr_y = top_y - 32
                for line in lines:
                    c.drawString(m_right["left"], curr_y, line)
                    curr_y -= line_h

                self._draw_page_number(c, current_page, m_right)
                c.showPage()
                current_page += 1

        # -------------------------------------------------------------------------
        # 6. 맺음말 (에필로그 / Epilogue)
        # -------------------------------------------------------------------------
        # 본문이 홀수면 짝수 페이지로 백면을 넘기고 다음 면에서 정갈하게 시작
        if current_page % 2 == 0:
            self._draw_page_background(c)
            c.showPage()
            current_page += 1

        m_epi = self.get_page_margins(current_page)
        self._draw_page_background(c)

        c.setFillColorRGB(0.2, 0.18, 0.17)
        c.setFont(FONT_BOLD_NAME, 16)
        c.drawString(m_epi["left"], self.canvas_h_pt - m_epi["top"], "맺음말")

        c.setStrokeColorRGB(0.85, 0.8, 0.75)
        c.setLineWidth(0.8)
        c.line(m_epi["left"], self.canvas_h_pt - m_epi["top"] - 12, self.canvas_w_pt - m_epi["right"], self.canvas_h_pt - m_epi["top"] - 12)

        default_epilogue = f"""기억을 더듬어 한 줄의 시를 빚고
그 곁에 따스한 그림을 얹는 동안,
나는 몇 번이고 지나온 계절 속을 다시 걸었습니다.

잊힌 줄로만 알았던 어머니의 밥 짓는 냄새와
바람에 흔들리던 고향 마당의 감나무,
그리고 묵묵히 곁을 지켜준 소중한 이들의 숨결이
이 작은 책갈피마다 살아 숨 쉬고 있음을 깨닫습니다.

이 시집을 손에 쥐어주신 모든 분께,
그리고 각자의 그리움을 품고 살아가는 모든 다정한 이들에게
작은 위로와 평안이 깃들기를 빕니다.


어느 맑은 날, {project_info.author} 삼가 적음"""

        epilogue_content = getattr(project_info, 'epilogue', '').strip() or default_epilogue
        epilogue_lines = [l.rstrip() for l in epilogue_content.split("\n")]

        e_font = 9.2 if len(epilogue_lines) > 16 else 9.8
        e_line_h = 16.0 if len(epilogue_lines) > 16 else 18.0
        c.setFont(FONT_NAME, e_font)
        c.setFillColorRGB(0.25, 0.23, 0.22)

        curr_y = self.canvas_h_pt - m_epi["top"] - 45
        for line in epilogue_lines:
            c.drawString(m_epi["left"], curr_y, line)
            curr_y -= e_line_h

        self._draw_page_number(c, current_page, m_epi)
        c.showPage()
        current_page += 1

        # -------------------------------------------------------------------------
        # 7. 판권지 (Colophon - 부크크 검수 필수 규격)
        # -------------------------------------------------------------------------
        if current_page % 2 == 0:
            self._draw_page_background(c)
            c.showPage()
            current_page += 1

        m_col = self.get_page_margins(current_page)
        self._draw_page_background(c)

        col_box_y = m_col["bottom"] + 30
        col_box_h = 200
        c.setStrokeColorRGB(0.82, 0.78, 0.72)
        c.setLineWidth(0.8)
        c.rect(m_col["left"], col_box_y, m_col["content_w"], col_box_h, fill=0, stroke=1)

        c.setFillColorRGB(0.2, 0.18, 0.17)
        c.setFont(FONT_BOLD_NAME, 13)
        c.drawString(m_col["left"] + 20, col_box_y + col_box_h - 28, project_info.name)

        if project_info.subtitle:
            c.setFont(FONT_NAME, 9.0)
            c.setFillColorRGB(0.45, 0.42, 0.38)
            c.drawString(m_col["left"] + 20, col_box_y + col_box_h - 44, project_info.subtitle)

        c.setStrokeColorRGB(0.88, 0.85, 0.8)
        c.line(m_col["left"] + 20, col_box_y + col_box_h - 52, m_col["left"] + m_col["content_w"] - 20, col_box_y + col_box_h - 52)

        c.setFont(FONT_NAME, 8.8)
        c.setFillColorRGB(0.35, 0.32, 0.3)
        author_type = getattr(project_info, 'author_type', 'single')
        author_field_name = "엮 은 이" if author_type == "collab" else "지 은 이"
        publisher_name = getattr(project_info, 'publisher', '부크크 (Bookk) 자가출판')
        published_date = getattr(project_info, 'published_date', '2026년')
        price_val = getattr(project_info, 'price', '13,000원')
        isbn_val = getattr(project_info, 'isbn', '').strip()

        col_lines = [
            f"{author_field_name} : {project_info.author}",
            f"펴 낸 곳 : {publisher_name}",
            f"초판발행 : {published_date}",
            f"정    가 : {price_val}",
            "제작지원 : StoryBook Studio 독립출판 엔진",
            "출판형태 : POD (Publish On Demand) 주문형 종이책",
        ]
        if isbn_val:
            col_lines.append(f"I S B N  : {isbn_val}")
        col_lines.append("")
        col_lines.append("ⓒ 저작권자와의 협의에 의해 본 도서의 무단 전재 및 복제를 금합니다.")

        text_y = col_box_y + col_box_h - 70
        for line in col_lines:
            c.drawString(m_col["left"] + 20, text_y, line)
            text_y -= 14

        c.showPage()
        total_pages = current_page

        # 부크크 권장: 내지 총 페이지 수는 짝수여야 함
        if total_pages % 2 != 0:
            self._draw_page_background(c)
            c.showPage()
            total_pages += 1

        c.save()

        return {
            "success": True,
            "pdf_path": str(output_path),
            "format": self.spec["name"],
            "total_pages": total_pages,
            "trim_size": f"{self.spec['trim_w_mm']} x {self.spec['trim_h_mm']} mm",
            "bleed_canvas": f"{self.canvas_w_mm} x {self.canvas_h_mm} mm",
            "dpi": 300
        }

    def build_cover_spread_pdf(
        self,
        output_path: Path,
        total_pages: int,
        project_info: Optional[ProjectInfo] = None,
        images_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        부크크 표지 펼침면 PDF 생성 (뒤표지 + 책등 + 앞표지 + 사방 3mm 도련)
        부크크 표지 업로드 규격을 100% 준수
        """
        if project_info is None:
            project_info = project_manager.get_active_project_info()
        if images_dir is None:
            images_dir = project_manager.get_active_images_dir()

        # 책등(세네카) 두께 계산
        sheets = total_pages / 2
        thickness_factor = PAPER_THICKNESS.get(self.paper_type, 0.060)
        spine_w_mm = max(round(sheets * thickness_factor, 2), 2.5)  # 최소 2.5mm 이상

        # 펼침면 총 가로/세로 (mm)
        # [도련 3mm] + [뒤표지] + [책등] + [앞표지] + [도련 3mm]
        cover_w_mm = (self.spec["bleed_mm"] * 2) + (self.spec["trim_w_mm"] * 2) + spine_w_mm
        cover_h_mm = (self.spec["bleed_mm"] * 2) + self.spec["trim_h_mm"]

        cover_w_pt = cover_w_mm * MM_TO_PT
        cover_h_pt = cover_h_mm * MM_TO_PT
        bleed_pt = self.spec["bleed_mm"] * MM_TO_PT
        front_w_pt = self.spec["trim_w_mm"] * MM_TO_PT
        spine_w_pt = spine_w_mm * MM_TO_PT

        output_path.parent.mkdir(parents=True, exist_ok=True)
        c = canvas.Canvas(str(output_path), pagesize=(cover_w_pt, cover_h_pt))

        # 1) 전체 배경 크림색
        c.setFillColorRGB(0.97, 0.95, 0.92)
        c.rect(0, 0, cover_w_pt, cover_h_pt, fill=1, stroke=0)

        # 2) 책등(세네카) 영역 점선 가이드 및 시집제목 · 저자 · 출판사 정밀 인쇄
        spine_x1 = bleed_pt + front_w_pt
        spine_x2 = spine_x1 + spine_w_pt
        spine_center_x = spine_x1 + (spine_w_pt / 2)

        # 책등 테두리 음영 (인쇄 재단선 가이드)
        c.setFillColorRGB(0.95, 0.93, 0.89)
        c.rect(spine_x1, bleed_pt, spine_w_pt, self.spec["trim_h_mm"] * MM_TO_PT, fill=1, stroke=0)

        # 책등 정보 인쇄: 시집 제목(상단) + 저자(중앙) + 출판사(하단)
        if spine_w_mm >= 2.0:
            spine_font_size = min(max(spine_w_mm * 1.8, 5.5), 8.5)
            c.saveState()
            c.translate(spine_center_x, cover_h_pt / 2)
            c.rotate(270)

            v_offset = -spine_font_size * 0.35
            c.setFillColorRGB(0.2, 0.18, 0.16)

            # [1] 상단부: 시집 제목 (볼드)
            c.setFont(FONT_BOLD_NAME, spine_font_size)
            c.drawCentredString(-(cover_h_pt * 0.22), v_offset, project_info.name)

            # [2] 중앙부: 저자 (지은이 / 엮은이)
            author_type = getattr(project_info, 'author_type', 'single')
            author_role = "엮은이" if author_type == "collab" else "지은이"
            author_text = project_info.author
            if not any(k in author_text for k in ["지은이", "엮은이", "엮음", "지음"]):
                spine_author = f"{author_role} {author_text}"
            else:
                spine_author = author_text
            c.setFont(FONT_NAME, spine_font_size * 0.92)
            c.drawCentredString(10, v_offset, spine_author)

            # [3] 하단부: 출판사
            pub_raw = getattr(project_info, 'publisher', '부크크').strip()
            # 괄호나 부가설명 분리하여 간결한 출판사명 추출 (예: '부크크 (Bookk) 자가출판' -> '부크크')
            pub_clean = pub_raw.split("(")[0].strip() or pub_raw
            if not pub_clean:
                pub_clean = "부크크"
            c.setFont(FONT_NAME, spine_font_size * 0.85)
            c.drawCentredString(cover_h_pt * 0.32, v_offset, pub_clean)

            c.restoreState()

        # 3) 앞표지 (우측 영역)
        front_center_x = spine_x2 + (front_w_pt / 2)
        top_y = cover_h_pt - bleed_pt

        cover_img_file = getattr(project_info, 'cover_image', '').strip()
        has_cover_image = False
        cand_img = None
        if cover_img_file and images_dir:
            cand = images_dir / Path(cover_img_file).name
            if cand.exists() and cand.is_file():
                has_cover_image = True
                cand_img = cand

        if has_cover_image:
            # [A] 대표 삽화가 있는 경우: 상단 제목 -> 구분선 -> 중앙 삽화 -> 하단 저자
            title_y = top_y - (36 * MM_TO_PT)
            c.setFillColorRGB(0.18, 0.16, 0.15)
            c.setFont(FONT_BOLD_NAME, 22)
            c.drawCentredString(front_center_x, title_y, project_info.name)

            curr_y = title_y
            if project_info.subtitle:
                curr_y -= 20
                c.setFillColorRGB(0.42, 0.38, 0.35)
                c.setFont(FONT_NAME, 10.5)
                c.drawCentredString(front_center_x, curr_y, project_info.subtitle)

            curr_y -= 14
            c.setStrokeColorRGB(0.75, 0.65, 0.55)
            c.setLineWidth(0.8)
            c.line(front_center_x - 30, curr_y, front_center_x + 30, curr_y)

            # 대표 삽화 배치 (가로 65mm x 세로 65mm)
            img_w = 65 * MM_TO_PT
            img_h = 65 * MM_TO_PT
            img_x = front_center_x - (img_w / 2)
            img_y = curr_y - 16 - img_h
            try:
                c.drawImage(str(cand_img), img_x, img_y, width=img_w, height=img_h, preserveAspectRatio=True, mask='auto')
            except Exception:
                pass
        else:
            # [B] 삽화가 없는 경우: 단아한 타이포그래피 중심 표지
            mid_y = cover_h_pt / 2
            title_y = mid_y + (30 * MM_TO_PT)
            c.setFillColorRGB(0.18, 0.16, 0.15)
            c.setFont(FONT_BOLD_NAME, 24)
            c.drawCentredString(front_center_x, title_y, project_info.name)

            curr_y = title_y
            if project_info.subtitle:
                curr_y -= 24
                c.setFillColorRGB(0.42, 0.38, 0.35)
                c.setFont(FONT_NAME, 11)
                c.drawCentredString(front_center_x, curr_y, project_info.subtitle)

            curr_y -= 16
            c.setStrokeColorRGB(0.75, 0.65, 0.55)
            c.setLineWidth(1)
            c.line(front_center_x - 35, curr_y, front_center_x + 35, curr_y)

        # 하단 저자 및 출판사
        c.setFillColorRGB(0.3, 0.28, 0.26)
        c.setFont(FONT_NAME, 10.5)
        author_type = getattr(project_info, 'author_type', 'single')
        author_role = "엮은이" if author_type == "collab" else "지은이"
        author_text = project_info.author
        if not any(k in author_text for k in ["지은이", "엮은이", "엮음", "지음"]):
            author_text = f"{author_role}  {author_text}"
        c.drawCentredString(front_center_x, bleed_pt + (32 * MM_TO_PT), author_text)

        c.setFillColorRGB(0.5, 0.45, 0.4)
        c.setFont(FONT_NAME, 9)
        pub_name = getattr(project_info, 'publisher', '부크크 (Bookk) 자가출판')
        c.drawCentredString(front_center_x, bleed_pt + (16 * MM_TO_PT), f"{pub_name} 시화집")

        # 4) 뒤표지 (좌측 영역) - 책 소개문 및 바코드 영역
        back_center_x = bleed_pt + (front_w_pt / 2)
        c.setFillColorRGB(0.3, 0.28, 0.26)
        c.setFont(FONT_NAME, 9.5)

        default_blurb = [
            "“가장 개인적인 기억이",
            "가장 깊은 문학이자 예술이 된다.”",
            "",
            "소박하지만 온기 넘치던 그 시절의 툇마루,",
            "마음속 깊이 간직해 온 찰나의 순간들을",
            "서정적인 시와 맑은 수채화로 엮었습니다."
        ]
        blurb_raw = getattr(project_info, 'back_cover_blurb', '').strip()
        blurb_lines = [l.rstrip() for l in blurb_raw.split("\n")] if blurb_raw else default_blurb

        blurb_y = (cover_h_pt / 2) + 45
        for b_line in blurb_lines[:9]:
            c.drawCentredString(back_center_x, blurb_y, b_line)
            blurb_y -= 18

        # 부크크 바코드 가이드 박스 (우측 하단: 50 x 35 mm)
        barcode_w_pt = 50 * MM_TO_PT
        barcode_h_pt = 35 * MM_TO_PT
        barcode_x = (spine_x1 - barcode_w_pt) - (15 * MM_TO_PT)
        barcode_y = bleed_pt + (15 * MM_TO_PT)

        c.setStrokeColorRGB(0.75, 0.72, 0.68)
        c.setLineWidth(0.8)
        c.rect(barcode_x, barcode_y, barcode_w_pt, barcode_h_pt, stroke=1, fill=0)

        c.setFillColorRGB(0.6, 0.58, 0.55)
        c.setFont(FONT_NAME, 7.5)
        c.drawCentredString(barcode_x + (barcode_w_pt / 2), barcode_y + (barcode_h_pt / 2) - 3, "[ 부크크 바코드 인쇄 영역 ]")

        c.showPage()
        c.save()

        return {
            "success": True,
            "cover_path": str(output_path),
            "cover_spread_size_mm": f"{cover_w_mm} x {cover_h_mm} mm",
            "spine_thickness_mm": spine_w_mm,
            "bleed_mm": self.spec["bleed_mm"],
            "total_pages": total_pages
        }

    def _draw_page_background(self, c: canvas.Canvas):
        """본문 배경 미색(백색모조/미색모조 느낌) 채우기"""
        c.setFillColorRGB(0.99, 0.985, 0.97)
        c.rect(0, 0, self.canvas_w_pt, self.canvas_h_pt, fill=1, stroke=0)

    def _draw_page_number(self, c: canvas.Canvas, page_num: int, margins: Dict[str, float]):
        """페이지 번호 인쇄 (바깥쪽 하단)"""
        c.setFillColorRGB(0.6, 0.58, 0.55)
        c.setFont(FONT_NAME, 8)
        if margins["is_odd"]:
            # 홀수 페이지: 우측 하단
            c.drawRightString(self.canvas_w_pt - margins["right"], margins["bottom"] - 5, str(page_num))
        else:
            # 짝수 페이지: 좌측 하단
            c.drawString(margins["left"], margins["bottom"] - 5, str(page_num))

    def _draw_artwork(
        self,
        c: canvas.Canvas,
        work: Any,
        images_dir: Path,
        x: float,
        y: float,
        w: float,
        h: float,
        img_override_file: Optional[str] = None
    ):
        """삽화 고화질(300DPI) 비율 유지 렌더링"""
        img_drawn = False
        target_file = img_override_file if img_override_file else work.image_file
        if target_file:
            candidates = [
                images_dir / Path(target_file).name,
                images_dir / target_file,
                BASE_DIR / target_file,
                BASE_DIR / "images" / Path(target_file).name
            ]
            for cand in candidates:
                if cand.exists() and cand.is_file():
                    try:
                        try:
                            ensure_300dpi_image(cand, cand)
                        except Exception:
                            pass
                        with Image.open(cand) as im:
                            orig_w, orig_h = im.size
                        ratio = min(w / orig_w, h / orig_h)
                        target_w = orig_w * ratio
                        target_h = orig_h * ratio
                        pos_x = x + (w - target_w) / 2
                        pos_y = y + (h - target_h) / 2
                        c.drawImage(str(cand), pos_x, pos_y, width=target_w, height=target_h)
                        img_drawn = True
                        break
                    except Exception as e:
                        print(f"Bookk Image Draw Warning: {e}")

        if not img_drawn:
            c.setStrokeColorRGB(0.85, 0.82, 0.78)
            c.setLineWidth(0.8)
            c.roundRect(x + 10, y + 20, w - 20, h - 40, 6, stroke=1, fill=0)
            c.setFillColorRGB(0.6, 0.55, 0.5)
            c.setFont(FONT_NAME, 10)
            c.drawCentredString(x + w / 2, y + h / 2, f"[ {work.episode_no} 수채화 삽화 ]")

    def _split_poem_into_n_chunks(self, lines: List[str], count: int) -> List[List[str]]:
        """시 본문을 N개의 연(stanza) 단위 청크로 지능형 분할"""
        if count <= 1 or len(lines) <= 6:
            return [lines]
        total = len(lines)

        if count == 2:
            mid = total // 2
            split_idx = mid
            for offset in range(max(mid, total - mid)):
                if mid - offset > 4 and lines[mid - offset].strip() == "":
                    split_idx = mid - offset
                    break
                if mid + offset < total - 4 and lines[mid + offset].strip() == "":
                    split_idx = mid + offset
                    break
            part1 = lines[:split_idx]
            part2 = lines[split_idx:]
            if part2 and part2[0].strip() == "":
                part2 = part2[1:]
            return [part1, part2]

        if count == 3:
            one_third = total // 3
            two_third = (total * 2) // 3
            split1 = one_third
            for offset in range(max(one_third, total - one_third)):
                if one_third - offset >= 3 and lines[one_third - offset].strip() == "":
                    split1 = one_third - offset
                    break
                if one_third + offset < two_third and lines[one_third + offset].strip() == "":
                    split1 = one_third + offset
                    break
            split2 = two_third
            for offset in range(max(total - two_third, two_third - split1)):
                if two_third - offset > split1 + 3 and lines[two_third - offset].strip() == "":
                    split2 = two_third - offset
                    break
                if two_third + offset < total - 3 and lines[two_third + offset].strip() == "":
                    split2 = two_third + offset
                    break
            part1 = lines[:split1]
            part2 = lines[split1:split2]
            part3 = lines[split2:]
            if part2 and part2[0].strip() == "":
                part2 = part2[1:]
            if part3 and part3[0].strip() == "":
                part3 = part3[1:]
            return [part1, part2, part3]

        if count == 4:
            q1, q2, q3 = total // 4, total // 2, (total * 3) // 4
            s1, s2, s3 = q1, q2, q3
            for off in range(8):
                if q1 - off >= 2 and lines[q1 - off].strip() == "": s1 = q1 - off; break
                if q1 + off < q2 and lines[q1 + off].strip() == "": s1 = q1 + off; break
            for off in range(8):
                if q2 - off > s1 + 2 and lines[q2 - off].strip() == "": s2 = q2 - off; break
                if q2 + off < q3 and lines[q2 + off].strip() == "": s2 = q2 + off; break
            for off in range(8):
                if q3 - off > s2 + 2 and lines[q3 - off].strip() == "": s3 = q3 - off; break
                if q3 + off < total - 2 and lines[q3 + off].strip() == "": s3 = q3 + off; break
            p1 = lines[:s1]
            p2 = lines[s1:s2]
            p3 = lines[s2:s3]
            p4 = lines[s3:]
            if p2 and p2[0].strip() == "": p2 = p2[1:]
            if p3 and p3[0].strip() == "": p3 = p3[1:]
            if p4 and p4[0].strip() == "": p4 = p4[1:]
            return [p1, p2, p3, p4]

        return [lines]


def build_pdf_book(
    output_path: Optional[Path] = None,
    manuscript_manager=None,
    project_info=None,
    images_dir: Optional[Path] = None,
) -> Path:
    """열람용/기본 A5 PDF 생성 통합 래퍼 (BookkPDFBuilder 기반 100% DTP 조판 동기화)"""
    if output_path is None:
        output_path = project_manager.get_active_pdf_path()
    builder = BookkPDFBuilder(format_key="a5", paper_type="white_100g")
    return builder.build_interior_pdf(output_path=output_path)
