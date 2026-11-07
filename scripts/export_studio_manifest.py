import json
import sys
from pathlib import Path
from dataclasses import asdict

# StoryBook 경로 설정
sys.path.insert(0, str(Path("d:/AG/StoryBook")))

from core.project_manager import project_manager

def export_default_status():
    mgr = project_manager.get_active_manuscript_manager()
    info = project_manager.get_active_project_info()
    works = mgr.load_works()
    completed = mgr.get_completed_count()
    next_num = mgr.get_next_episode_number()

    works_data = []
    for w in works:
        img = w.image_file or ""
        # 갤러리에 배포된 웹 이미지 경로 매핑
        if img:
            img_name = Path(img).name
            web_img = f"/gallery/images/{img_name}"
        else:
            web_img = ""

        works_data.append({
            "episode_no": w.episode_no,
            "title": w.title,
            "status": w.status,
            "chapter": getattr(w, "chapter", ""),
            "author": getattr(w, "author", "") or "김서정",
            "memory_anchor": w.memory_anchor,
            "image_file": web_img,
            "image_file_2": getattr(w, "image_file_2", ""),
            "layout_mode": getattr(w, "layout_mode", "compact"),
            "part2_mode": getattr(w, "part2_mode", "motif_symbol"),
            "layout_config": getattr(w, "layout_config", None),
            "recite_file": getattr(w, "recite_file", ""),
            "music_file": getattr(w, "music_file", ""),
            "audio_file": getattr(w, "audio_file", "") or getattr(w, "music_file", "") or getattr(w, "recite_file", ""),
            "lyrics": getattr(w, "lyrics", ""),
            "art_direction": w.art_direction,
            "poem_body": w.poem_body
        })

    status_data = {
        "project": asdict(info),
        "target_count": info.target_count,
        "completed_count": completed,
        "progress_percent": round((completed / max(1, info.target_count)) * 100, 1),
        "next_episode": f"제{str(next_num).zfill(2)}화",
        "works": works_data
    }

    out_dir = Path("d:/AG/EduAI_Hub/public/studio/data")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "default_status.json"
    out_file.write_text(json.dumps(status_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ default_status.json 추출 완료: {len(works_data)}개 작품 수록 -> {out_file}")

if __name__ == "__main__":
    export_default_status()

