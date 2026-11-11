"""
scripts/sync_to_cloud.py
로컬 프로젝트(노을빛_기억 등)의 원고 데이터와 300 DPI 삽화/음원을
Turso 클라우드 DB 및 Cloudflare R2 단일 마스터 스토리지로 일괄 동기화하는 스크립트
실행 방법: python scripts/sync_to_cloud.py
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.config import get_cloud_infrastructure_status
from core.project_manager import project_manager
from core.db_manager import db_manager, PieceData
from core.r2_storage import r2_storage


def sync_all_projects():
    print("=" * 65)
    print("🚀 StoryBook Studio: 로컬 ➔ 클라우드(Turso + R2) 일괄 동기화 시작")
    print("=" * 65)

    infra = get_cloud_infrastructure_status()
    print(f"• DB 모드      : {'Turso Cloud (' + infra['turso_url_masked'] + ')' if db_manager.is_cloud_mode else 'Local SQLite (Fallback)'}")
    print(f"• 스토리지 모드 : {'Cloudflare R2 (' + infra['r2_public_url'] + ')' if r2_storage.is_r2_configured else 'Local Cache (Fallback)'}")
    print("-" * 65)

    projects = project_manager.list_projects()
    for proj in projects:
        pid = proj.id
        print(f"\n📂 프로젝트 동기화 중: [{proj.title}] (ID: {pid})")
        mgr = project_manager.get_manuscript_manager(pid)
        works = mgr.load_works()

        toc_entries = []
        for idx, w in enumerate(works, start=1):
            piece_id = f"P-{idx:04d}"
            piece = PieceData(
                piece_id=piece_id,
                project_id=pid,
                title=w.title,
                poem_body=w.poem_body or "",
                chapter_topic=getattr(w, "chapter", "") or "",
                memory_anchor=w.memory_anchor or "",
                status="approved" if w.status == "완성" else "draft",
                art_style=getattr(w, "art_style", "watercolor") or "watercolor",
                art_direction=w.art_direction or "",
                illustration_prompt=getattr(w, "image_prompt", "") or "",
                image_file=w.image_file or "",
                image_file_2=getattr(w, "image_file_2", "") or "",
                music_file=getattr(w, "music_file", "") or "",
                lyrics=getattr(w, "lyrics", "") or "",
                layout_mode=getattr(w, "layout_mode", "compact") or "compact",
                page_count=int(getattr(w, "page_count", 2) or 2),
                part2_mode=getattr(w, "part2_mode", "motif_symbol") or "motif_symbol",
                layout_config=getattr(w, "layout_config", {}) or {},
            )
            db_manager.save_piece(piece)
            toc_entries.append({
                "piece_id": piece_id,
                "chapter": piece.chapter_topic,
                "display_label": w.episode_no or f"제{idx:02d}화"
            })

        if toc_entries:
            db_manager.set_toc(pid, toc_entries)
            print(f"  ✅ 시 원고 {len(toc_entries)}편 DB(Turso/SQLite) 동기화 완료")

        # 이미지 파일 R2 업로드 동기화
        images_dir = project_manager.get_project_dir(pid) / "images"
        if images_dir.exists() and r2_storage.is_r2_configured:
            img_files = [f for f in images_dir.iterdir() if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")]
            for img_f in img_files:
                r2_storage.save_project_image(pid, img_f.name, img_f.read_bytes())
            print(f"  ✅ 삽화 이미지 {len(img_files)}장 Cloudflare R2 업로드 완료")

    print("\n" + "=" * 65)
    print("✨ 모든 프로젝트의 단일 플랫폼 동기화가 성공적으로 완료되었습니다!")
    print("=" * 65)


if __name__ == "__main__":
    sync_all_projects()

