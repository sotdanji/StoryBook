import csv
import shutil
from pathlib import Path
from typing import Tuple, Optional, List, Dict, Any
from core.config import BASE_DIR
from core.manuscript import ManuscriptManager
from core.project_manager import project_manager

def _split_poem_into_chunks(lines: List[str], count: int) -> List[List[str]]:
    """
    시 본문 행들을 연(Stanza) 구분을 존중하여 count개의 묶음으로 분할합니다.
    """
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
        while part1 and part1[-1].strip() == "":
            part1.pop()
        while part2 and part2[0].strip() == "":
            part2.pop(0)
        return [part1, part2]

    # 3개 이상 분할
    step = total // count
    res = []
    start = 0
    for i in range(count):
        if i == count - 1:
            res.append(lines[start:])
        else:
            end = start + step
            for off in range(step // 2):
                if end - off > start + 3 and lines[end - off].strip() == "":
                    end = end - off
                    break
                if end + off < total - 3 and lines[end + off].strip() == "":
                    end = end + off
                    break
            chunk = lines[start:end]
            while chunk and chunk[-1].strip() == "":
                chunk.pop()
            res.append(chunk)
            start = end
            while start < total and lines[start].strip() == "":
                start += 1
    return res


def build_canva_csv(
    output_file: Optional[Path] = None,
    manuscript_manager: Optional[ManuscriptManager] = None
) -> Tuple[int, Path]:
    """
    [Full Book Architecture & DTP 동기화]
    작품집 원고에서 완성된 작품들을 읽어 Canva 대량 제작용 CSV 파일을 생성합니다.
    - 기존 단일 템플릿 호환 필드 (Poem_Body, Image_File) 유지
    - DTP 조판 엔진과 100% 동기화된 페이지별 분할 필드 (Page_1_Text, Page_1_Image, Page_2_Text...) 완벽 지원
    - BOM(utf-8-sig) 인코딩으로 엑셀 및 Canva 한글 깨짐 방지
    """
    if manuscript_manager is None:
        manuscript_manager = project_manager.get_active_manuscript_manager()

    if output_file is None:
        output_file = project_manager.get_active_csv_path()

    works = manuscript_manager.load_works()

    # 내용이 있는 유효한 작품 추출
    valid_works = [w for w in works if w.poem_body.strip()]

    headers = [
        "Episode_No", "Title", "Chapter", "Page_Count",
        "Poem_Body", "Memory_Anchor", "Image_File",
        "Page_1_Usage", "Page_1_Text", "Page_1_Image",
        "Page_2_Usage", "Page_2_Text", "Page_2_Image",
        "Page_3_Usage", "Page_3_Text", "Page_3_Image",
        "Page_4_Usage", "Page_4_Text", "Page_4_Image",
    ]

    with open(output_file, mode="w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()

        for w in valid_works:
            img_filename = Path(w.image_file).name if w.image_file else ""
            lines = [l.rstrip() for l in (w.poem_body or "").split("\n")]

            # DTP 조판 설정 분석
            cfg = getattr(w, 'layout_config', {}) or {}
            pages_cfg = cfg.get("pages", [])
            page_count = cfg.get("page_count", 2)

            if not pages_cfg:
                # 기본 2쪽 (1면 이미지, 2면 텍스트)
                pages_cfg = [
                    {"page_num": 1, "usage": "image", "role": "none", "image_file": ""},
                    {"page_num": 2, "usage": "text", "role": "start", "image_file": ""}
                ]

            # 텍스트가 들어가는 페이지 개수 파악
            text_pages = [p for p in pages_cfg if p.get("usage") in ("text", "mixed", "image_text")]
            text_chunks = _split_poem_into_chunks(lines, max(1, len(text_pages)))

            page_data: Dict[str, str] = {}
            chunk_idx = 0

            for p_num in range(1, 5):
                usage_key = f"Page_{p_num}_Usage"
                text_key = f"Page_{p_num}_Text"
                img_key = f"Page_{p_num}_Image"

                if p_num <= len(pages_cfg):
                    p_info = pages_cfg[p_num - 1]
                    usage = p_info.get("usage", "text")
                    page_data[usage_key] = usage

                    # 텍스트 배치
                    if usage in ("text", "mixed", "image_text") and chunk_idx < len(text_chunks):
                        page_data[text_key] = "\n".join(text_chunks[chunk_idx])
                        chunk_idx += 1
                    else:
                        page_data[text_key] = ""

                    # 이미지 배치
                    if usage in ("image", "mixed", "image_text"):
                        override_img = p_info.get("image_file", "")
                        page_data[img_key] = Path(override_img).name if override_img else img_filename
                    else:
                        page_data[img_key] = ""
                else:
                    page_data[usage_key] = "none"
                    page_data[text_key] = ""
                    page_data[img_key] = ""

            row = {
                "Episode_No": w.episode_no,
                "Title": w.title,
                "Chapter": getattr(w, 'chapter', '') or '',
                "Page_Count": page_count,
                "Poem_Body": w.poem_body,
                "Memory_Anchor": w.memory_anchor,
                "Image_File": img_filename,
            }
            row.update(page_data)
            writer.writerow(row)

    return len(valid_works), output_file


def build_canva_publishing_metadata_csv(
    output_file: Optional[Path] = None,
    project_id: Optional[str] = None
) -> Path:
    """
    Canva 표지/서문/목차/에필로그/판권 템플릿에 데이터 바인딩할 수 있는
    시집 본문 외 출판 전용 메타데이터 CSV 파일을 생성합니다.
    """
    info = project_manager.get_project_info(project_id)
    if output_file is None:
        pdir = project_manager.get_project_dir(project_id)
        output_file = pdir / "시화집_출판구성데이터.csv"

    headers = [
        "Book_Title", "Book_Subtitle", "Book_Author",
        "Prologue", "Epilogue", "Back_Cover_Blurb", "Cover_Image",
        "Publisher", "Published_Date", "Price", "ISBN"
    ]

    with open(output_file, mode="w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerow({
            "Book_Title": info.name,
            "Book_Subtitle": info.subtitle,
            "Book_Author": info.author,
            "Prologue": info.prologue,
            "Epilogue": info.epilogue,
            "Back_Cover_Blurb": info.back_cover_blurb,
            "Cover_Image": Path(info.cover_image).name if info.cover_image else "",
            "Publisher": info.publisher,
            "Published_Date": info.published_date,
            "Price": info.price,
            "ISBN": info.isbn
        })

    return output_file
