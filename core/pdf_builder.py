import os
import shutil
from pathlib import Path
from typing import Optional
from PIL import Image

from reportlab.lib.pagesizes import A5
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from core.config import BASE_DIR
from core.manuscript import ManuscriptManager
from core.project_manager import project_manager, ProjectInfo
from core.image_optimizer import ensure_300dpi_image

# 기본 폰트 등록
FONT_PATH = "C:/Windows/Fonts/malgun.ttf"
FONT_BOLD_PATH = "C:/Windows/Fonts/malgunbd.ttf"
FONT_NAME = "Malgun"
FONT_BOLD_NAME = "Malgun-Bold"

try:
    if os.path.exists(FONT_PATH):
        pdfmetrics.registerFont(TTFont(FONT_NAME, FONT_PATH))
    if os.path.exists(FONT_BOLD_PATH):
        pdfmetrics.registerFont(TTFont(FONT_BOLD_NAME, FONT_BOLD_PATH))
    else:
        pdfmetrics.registerFont(TTFont(FONT_BOLD_NAME, FONT_PATH))
except Exception as e:
    print(f"Font loading warning: {e}")

def build_pdf_book(
    output_path: Optional[Path] = None,
    manuscript_manager: Optional[ManuscriptManager] = None,
    project_info: Optional[ProjectInfo] = None,
    images_dir: Optional[Path] = None
) -> Path:
    """
    작품집 원고를 바탕으로 부크크 A5 규격(148 x 210 mm)의 
    고품질 시화집 PDF 전자책/인쇄용 파일을 생성합니다.
    (2페이지 1작품: 좌측 삽화 전면 + 우측 시 본문)
    """
    if project_info is None:
        project_info = project_manager.get_active_project_info()

    if manuscript_manager is None:
        manuscript_manager = project_manager.get_active_manuscript_manager()

    if output_path is None:
        output_path = project_manager.get_active_pdf_path()

    if images_dir is None:
        images_dir = project_manager.get_active_images_dir()

    works = manuscript_manager.load_works()

    # A5 규격 (포인트 단위: 가로 419.53 pt, 세로 595.28 pt)
    page_w, page_h = A5
    c = canvas.Canvas(str(output_path), pagesize=A5)

    # ----------------------------------------------------
    # 1. 겉표지 (Cover Page)
    # ----------------------------------------------------
    # 배경 크림색
    c.setFillColorRGB(0.97, 0.96, 0.93)
    c.rect(0, 0, page_w, page_h, fill=1, stroke=0)

    # 테두리 라인
    c.setStrokeColorRGB(0.62, 0.42, 0.33)
    c.setLineWidth(1.5)
    c.rect(25, 25, page_w - 50, page_h - 50, fill=0, stroke=1)

    # 표지 타이틀
    c.setFillColorRGB(0.18, 0.16, 0.15)
    c.setFont(FONT_BOLD_NAME, 24)
    c.drawCentredString(page_w / 2, page_h - 180, project_info.name)

    c.setFillColorRGB(0.42, 0.38, 0.35)
    c.setFont(FONT_NAME, 11)
    c.drawCentredString(page_w / 2, page_h - 220, project_info.subtitle)

    # 장식 구분선
    c.setStrokeColorRGB(0.76, 0.61, 0.38)
    c.setLineWidth(1)
    c.line(page_w / 2 - 40, page_h - 250, page_w / 2 + 40, page_h - 250)

    # 지은이
    c.setFillColorRGB(0.35, 0.32, 0.3)
    c.setFont(FONT_NAME, 11)
    c.drawCentredString(page_w / 2, page_h - 280, f"지은이  {project_info.author}")

    # 표지 하단
    c.setFillColorRGB(0.5, 0.45, 0.4)
    c.setFont(FONT_NAME, 9.5)
    c.drawCentredString(page_w / 2, 80, "StoryBook Studio")
    c.showPage()

    # ----------------------------------------------------
    # 2. 서문 (시인의 말)
    # ----------------------------------------------------
    c.setFillColorRGB(0.99, 0.98, 0.96)
    c.rect(0, 0, page_w, page_h, fill=1, stroke=0)

    c.setFillColorRGB(0.2, 0.18, 0.17)
    c.setFont(FONT_BOLD_NAME, 16)
    c.drawString(45, page_h - 100, "시인의 말")

    c.setStrokeColorRGB(0.85, 0.8, 0.75)
    c.line(45, page_h - 115, page_w - 45, page_h - 115)

    c.setFont(FONT_NAME, 10)
    c.setFillColorRGB(0.25, 0.23, 0.22)
    intro_lines = [
        "가장 개인적인 기억이 가장 깊은 문학이자 예술이 된다.",
        "",
        "이 책은 화려한 허구나 지어낸 교훈을 담지 않았습니다.",
        "마음속 깊은 곳에 오래 고여 있던 찰나의 순간,",
        "차갑게 식어가던 툇마루의 새벽과 그 시절 들었던 말 한마디를",
        "온전한 나의 목소리와 빛깔로 빚어낸 삶의 기록입니다.",
        "",
        "책장을 넘길 때마다 그날의 서정적 온기가",
        "그리운 당신의 마음에 가만히 가닿기를 소망합니다.",
        "",
        "",
        f"― {project_info.author} 엮음"
    ]
    y = page_h - 160
    for line in intro_lines:
        c.drawString(45, y, line)
        y -= 20
    c.showPage()

    # ----------------------------------------------------
    # 3. 본문 조판
    # ----------------------------------------------------
    page_num = 3
    book_type = getattr(project_info, "book_type", "illustrated")

    for work in works:
        if book_type == "illustrated":
            # [서정 시화집 모드] 2페이지 1세트: 좌측 삽화 + 우측 시 본문
            # 1) 좌측 페이지 - 짝수면 전면 삽화 (인쇄 재단 및 제본 안전 여백 준수)
            c.setFillColorRGB(0.98, 0.97, 0.95)
            c.rect(0, 0, page_w, page_h, fill=1, stroke=0)

            safe_img_x = 36
            safe_img_w = page_w - (36 + 46)
            safe_img_y = 45
            safe_img_h = page_h - (45 + 45)

            img_drawn = False
            if work.image_file:
                candidates = [
                    images_dir / Path(work.image_file).name,
                    images_dir / work.image_file,
                    BASE_DIR / work.image_file,
                    BASE_DIR / "images" / Path(work.image_file).name
                ]
                for candidate in candidates:
                    if candidate.exists() and candidate.is_file():
                        try:
                            # 300 DPI 출판 규격 검사 및 필요시 자동 보정
                            try:
                                ensure_300dpi_image(candidate, candidate)
                            except Exception:
                                pass
                            with Image.open(candidate) as im:
                                orig_w, orig_h = im.size
                            
                            ratio = min(safe_img_w / orig_w, safe_img_h / orig_h)
                            target_w = orig_w * ratio
                            target_h = orig_h * ratio
                            x_pos = safe_img_x + (safe_img_w - target_w) / 2
                            y_pos = safe_img_y + (safe_img_h - target_h) / 2

                            c.drawImage(str(candidate), x_pos, y_pos, width=target_w, height=target_h)
                            img_drawn = True
                            break
                        except Exception as e:
                            print(f"Image draw error ({candidate}): {e}")

            if not img_drawn:
                c.setStrokeColorRGB(0.85, 0.82, 0.78)
                c.setLineWidth(1)
                c.roundRect(safe_img_x + 10, safe_img_y + 20, safe_img_w - 20, safe_img_h - 40, 8, stroke=1, fill=0)
                c.setFillColorRGB(0.6, 0.55, 0.5)
                c.setFont(FONT_NAME, 11)
                c.drawCentredString(safe_img_x + safe_img_w / 2, safe_img_y + safe_img_h / 2, f"[ {work.episode_no} 삽화 준비 중 ]")

            # 좌측 페이지 번호
            c.setFillColorRGB(0.6, 0.58, 0.55)
            c.setFont(FONT_NAME, 8)
            c.drawCentredString(page_w / 2, 20, str(page_num))
            c.showPage()
            page_num += 1

            # 2) 우측 페이지 - 홀수면 시 본문
            margin_left = 46
            margin_right = 36
        else:
            # [일반 시집 모드] 1페이지 1작품 단독 조판 (종이 낭비 없는 정통 시집 포맷)
            is_odd = (page_num % 2 != 0)
            margin_left = 46 if is_odd else 36
            margin_right = 36 if is_odd else 46

        # 시 본문 페이지 공통 렌더링
        c.setFillColorRGB(0.99, 0.98, 0.96)
        c.rect(0, 0, page_w, page_h, fill=1, stroke=0)

        top_y = page_h - 54

        # 1) 작품 제목 (인쇄용 본문에서 [제01화] 제외하여 세로 공간 확보)
        c.setFillColorRGB(0.18, 0.16, 0.15)
        c.setFont(FONT_BOLD_NAME, 16.5)
        c.drawString(margin_left, top_y, work.title)

        # 장식 구분선
        c.setStrokeColorRGB(0.86, 0.82, 0.78)
        c.setLineWidth(0.8)
        c.line(margin_left, top_y - 12, page_w - margin_right, top_y - 12)

        # 2) 시 본문 동적 폰트/행간 조판
        lines = [line.rstrip() for line in (work.poem_body or "").split("\n")]
        line_count = len(lines)

        if line_count > 24:
            poem_font_size = 8.5
            line_spacing = 14.5
        elif line_count > 17:
            poem_font_size = 9.2
            line_spacing = 16.5
        elif line_count > 12:
            poem_font_size = 10.0
            line_spacing = 19.0
        else:
            poem_font_size = 10.5
            line_spacing = 21.0

        c.setFillColorRGB(0.24, 0.22, 0.21)
        c.setFont(FONT_NAME, poem_font_size)

        curr_y = top_y - 36
        for line in lines:
            trimmed = line.rstrip()
            if not trimmed:
                curr_y -= line_spacing
                continue

            # 1) 오른쪽 치우침 / 정렬 (>> 표식)
            if trimmed.startswith(">>") or trimmed.startswith("》》"):
                actual_text = trimmed.lstrip(">》 ")
                c.drawRightString(page_w - margin_right - 4, curr_y, actual_text)
            else:
                # 2) 시적 들여쓰기 (앞 공백 개수별 정밀 오프셋 반영)
                leading_spaces = len(line) - len(line.lstrip(' '))
                indent_offset = leading_spaces * (poem_font_size * 0.45)
                c.drawString(margin_left + 4 + indent_offset, curr_y, line.lstrip(' '))

            curr_y -= line_spacing

        # 하단 기억의 중심 주석 (있는 경우)
        if work.memory_anchor:
            c.setStrokeColorRGB(0.9, 0.87, 0.83)
            c.setLineWidth(0.5)
            c.line(margin_left, 54, page_w - margin_right, 54)
            c.setFillColorRGB(0.55, 0.52, 0.48)
            c.setFont(FONT_NAME, 7.5)
            note = f"기억의 중심: {work.memory_anchor}"
            if len(note) > 48:
                note = note[:45] + "..."
            c.drawString(margin_left, 42, note)

        # 페이지 번호
        c.setFillColorRGB(0.6, 0.58, 0.55)
        c.setFont(FONT_NAME, 8)
        c.drawCentredString(page_w / 2, 20, str(page_num))
        c.showPage()
        page_num += 1


    # ----------------------------------------------------
    # 4. 판권지 (Colophon)
    # ----------------------------------------------------
    c.setFillColorRGB(0.99, 0.98, 0.96)
    c.rect(0, 0, page_w, page_h, fill=1, stroke=0)

    c.setFillColorRGB(0.2, 0.18, 0.17)
    c.setFont(FONT_BOLD_NAME, 14)
    c.drawString(50, page_h - 200, project_info.name)

    c.setFont(FONT_NAME, 9)
    c.setFillColorRGB(0.35, 0.32, 0.3)
    colophon_lines = [
        f"지은이 : {project_info.author}",
        "펴낸곳 : StoryBook Studio",
        "판  형 : A5 (148 × 210 mm)",
        "출  력 : 부크크(Bookk) POD 인쇄",
        "",
        "본 도서는 인공지능 창작 동반자와 함께",
        "실제 생애 기억을 토대로 빚어낸 순수 시화집입니다.",
        "저작권자의 허락 없이 무단 복제 및 전재를 금합니다."
    ]
    cy = page_h - 235
    for cline in colophon_lines:
        c.drawString(50, cy, cline)
        cy -= 18

    c.showPage()
    c.save()
    return output_path
