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
