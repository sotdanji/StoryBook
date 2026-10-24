import csv
import shutil
from pathlib import Path
from typing import Tuple, Optional
from core.config import BASE_DIR
from core.manuscript import ManuscriptManager
from core.project_manager import project_manager

def build_canva_csv(
    output_file: Optional[Path] = None,
    manuscript_manager: Optional[ManuscriptManager] = None
) -> Tuple[int, Path]:
    """
    작품집 원고에서 완성된 작품들을 읽어 Canva 대량 제작용 CSV 파일을 생성합니다.
    BOM(utf-8-sig) 인코딩을 적용하여 엑셀 및 Canva 업로드 시 한글 깨짐을 방지합니다.
    """
    if manuscript_manager is None:
        manuscript_manager = project_manager.get_active_manuscript_manager()

    if output_file is None:
        output_file = project_manager.get_active_csv_path()

    works = manuscript_manager.load_works()

    # 내용이 있는 유효한 작품 추출
    valid_works = [w for w in works if w.poem_body.strip()]

    headers = ["Episode_No", "Title", "Poem_Body", "Memory_Anchor", "Image_File"]

    with open(output_file, mode="w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()

        for w in valid_works:
            img_filename = Path(w.image_file).name if w.image_file else ""
            
            writer.writerow({
                "Episode_No": w.episode_no,
                "Title": w.title,
                "Poem_Body": w.poem_body,
                "Memory_Anchor": w.memory_anchor,
                "Image_File": img_filename
            })

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
