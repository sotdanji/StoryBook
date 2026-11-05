# -*- coding: utf-8 -*-
import json
import os
import re
from dataclasses import asdict
from pathlib import Path
from typing import Optional, Dict, Any

from core.project_manager import project_manager


def build_project_gallery_payload(project_id: Optional[str] = None, relative_paths: bool = False) -> Dict[str, Any]:
    """
    지정된 프로젝트의 최신 원고(works), DTP 조판 설정(layout_config), 음원/영상,
    책 전체 구조(book_structure)를 추출하여 갤러리 렌더링용 데이터 딕셔너리를 반환합니다.
    - relative_paths=False: 웹 서버 API(/api/gallery_data)용 절대 경로 (/projects/{safe_name}/...)
    - relative_paths=True: 오프라인 시화집_갤러리.html 내장 폴백용 상대 경로 (images/..., music/...)
    """
    pid = project_id or project_manager.get_active_project_id()
    info = project_manager.get_project_info(pid)
    mgr = project_manager.get_manuscript_manager(pid)
    works = mgr.load_works()

    safe_name = info.name.replace(" ", "_")
    proj_dir = project_manager.get_project_dir(pid)
    music_dir = proj_dir / "music"
    videos_dir = proj_dir / "videos"

    def _fmt_path(rel_p: str) -> str:
        if not rel_p:
            return ""
        clean = str(rel_p).replace("./", "").lstrip("/")
        if clean.startswith(f"projects/{safe_name}/"):
            clean = clean[len(f"projects/{safe_name}/"):]
        if relative_paths:
            return clean
        return f"/projects/{safe_name}/{clean}"

    episodes = []
    for w in works:
        img_file = (w.image_file or "").replace("./", "").lstrip("/")
        if img_file and not img_file.startswith("images/") and not img_file.startswith("projects/"):
            img_file = f"images/{img_file}"
        img_path = _fmt_path(img_file)

        img_file_2 = (getattr(w, "image_file_2", "") or "").replace("./", "").lstrip("/")
        if img_file_2 and not img_file_2.startswith("images/") and not img_file_2.startswith("projects/"):
            img_file_2 = f"images/{img_file_2}"
        img_path_2 = _fmt_path(img_file_2)

        recite_f = getattr(w, "recite_file", "") or ""
        music_f = getattr(w, "music_file", "") or ""
        if not recite_f and not music_f:
            old_a = getattr(w, "audio_file", "") or ""
            if "낭송" in old_a or old_a.endswith(".webm"):
                recite_f = old_a
            else:
                music_f = old_a

        ep_digits = re.sub(r"[^0-9]", "", w.episode_no or "").zfill(2)

        # 1) 육성 시 낭송
        voice_f = ""
        if music_dir.exists() and ep_digits:
            for ext in ["wav", "webm", "mp3", "m4a"]:
                cand = music_dir / f"{ep_digits}_육성.{ext}"
                if cand.exists():
                    voice_f = f"music/{cand.name}"
                    break
        if not voice_f and recite_f and ("육성" in recite_f or recite_f.endswith(".webm")):
            voice_f = recite_f

        # 2) AI 시 낭송
        ai_recite_f = ""
        if music_dir.exists() and ep_digits:
            for ext in ["wav", "mp3", "m4a"]:
                for tag in ["낭송", "AI낭송"]:
                    cand = music_dir / f"{ep_digits}_{tag}.{ext}"
                    if cand.exists():
                        ai_recite_f = f"music/{cand.name}"
                        break
                if ai_recite_f:
                    break
        if not ai_recite_f and recite_f and "육성" not in recite_f and "음악" not in recite_f:
            ai_recite_f = recite_f

        # 3) 음악 시 낭송
        music_recite_f = ""
        if music_dir.exists() and ep_digits:
            for ext in ["mp3", "m4a", "wav"]:
                for tag in ["음악낭송", "음악시낭송"]:
                    cand = music_dir / f"{ep_digits}_{tag}.{ext}"
                    if cand.exists():
                        music_recite_f = f"music/{cand.name}"
                        break
                if music_recite_f:
                    break
        if not music_recite_f and recite_f and "음악" in recite_f:
            music_recite_f = recite_f

        # 4) 노래 듣기
        song_f = ""
        if music_dir.exists() and ep_digits:
            for ext in ["mp3", "m4a", "wav"]:
                for tag in ["노래", "음원", "music"]:
                    cand = music_dir / f"{ep_digits}_{tag}.{ext}"
                    if cand.exists():
                        song_f = f"music/{cand.name}"
                        break
                if song_f:
                    break
        if not song_f and music_f:
            song_f = music_f

        recite_f = voice_f or ai_recite_f or music_recite_f
        music_f = song_f

        recite_path = _fmt_path(recite_f)
        music_path = _fmt_path(music_f)
        voice_path = _fmt_path(voice_f)
        ai_recite_path = _fmt_path(ai_recite_f)
        music_recite_path = _fmt_path(music_recite_f)
        song_path = _fmt_path(song_f)

        poem_video_path = ""
        song_video_path = ""
        if videos_dir.exists() and ep_digits:
            matched_song_v = list(videos_dir.glob(f"*{ep_digits}*music*.mp4")) or list(videos_dir.glob(f"{ep_digits}_*노래*.mp4")) or list(videos_dir.glob(f"{ep_digits}_*리릭*.mp4"))
            if matched_song_v:
                latest_song = max(matched_song_v, key=os.path.getmtime)
                song_video_path = f"videos/{latest_song.name}" if relative_paths else f"/api/poem_video/stream/{safe_name}/{latest_song.name}"
            matched_poem_v = list(videos_dir.glob(f"*{ep_digits}*recite*.mp4")) or list(videos_dir.glob(f"{ep_digits}_*낭송*.mp4")) or [v for v in videos_dir.glob(f"{ep_digits}_*.mp4") if "리릭" not in v.name and "music" not in v.name]
            if matched_poem_v:
                latest_poem = max(matched_poem_v, key=os.path.getmtime)
                poem_video_path = f"videos/{latest_poem.name}" if relative_paths else f"/api/poem_video/stream/{safe_name}/{latest_poem.name}"

        has_video = bool(poem_video_path or song_video_path)
        default_video = song_video_path or poem_video_path

        episodes.append({
            "ep": w.episode_no,
            "episode_no": w.episode_no,
            "title": w.title,
            "status": getattr(w, "status", "완성"),
            "image": img_path,
            "image_file": img_path,
            "image2": img_path_2,
            "image_file_2": img_path_2,
            "memory": w.memory_anchor,
            "body": w.poem_body,
            "poem_body": w.poem_body,
            "hasRecite": bool(recite_f),
            "recite": recite_path,
            "hasVoice": bool(voice_f),
            "voice": voice_path,
            "hasAiRecite": bool(ai_recite_f),
            "aiRecite": ai_recite_path,
            "hasMusicRecite": bool(music_recite_f),
            "musicRecite": music_recite_path,
            "hasSong": bool(song_f),
            "song": song_path,
            "hasMusic": bool(music_f),
            "music": music_path,
            "hasAudio": bool(voice_f or ai_recite_f or music_recite_f or song_f),
            "audio": music_path or recite_path,
            "lyrics": getattr(w, "lyrics", "") or "",
            "hasVideo": has_video,
            "video": default_video,
            "hasPoemVideo": bool(poem_video_path),
            "poemVideo": poem_video_path,
            "hasSongVideo": bool(song_video_path),
            "songVideo": song_video_path,
            "layout_mode": getattr(w, "layout_mode", "compact") or "compact",
            "part2_mode": getattr(w, "part2_mode", "motif_symbol") or "motif_symbol",
            "layout_config": getattr(w, "layout_config", None),
            "chapter": getattr(w, "chapter", "") or "",
            "author": getattr(w, "author", "") or info.author
        })

    book_structure = project_manager.get_book_structure(pid)

    return {
        "success": True,
        "project": asdict(info),
        "projects": project_manager.list_projects(),
        "episodes": episodes,
        "book_structure": book_structure
    }


def sync_project_gallery_html(project_id: Optional[str] = None) -> bool:
    """
    프로젝트 폴더의 시화집_갤러리.html 내장 데이터(EPISODES, BOOK_STRUCTURE, PROJECT_INFO)를
    최신 원고 및 DTP 조판 설정(layout_config)과 100% 자동 동기화합니다.
    (오프라인 file:/// 열람 시에도 DTP 조판 편집기 화면과 완벽히 동일하게 표시)
    """
    try:
        pid = project_id or project_manager.get_active_project_id()
        proj_dir = project_manager.get_project_dir(pid)
        gallery_file = proj_dir / "시화집_갤러리.html"
        if not gallery_file.exists():
            # 기준 템플릿(노을빛_기억)에서 복사
            base_gallery = project_manager.projects_dir / "노을빛_기억" / "시화집_갤러리.html"
            if base_gallery.exists() and base_gallery != gallery_file:
                gallery_file.write_text(base_gallery.read_text(encoding="utf-8"), encoding="utf-8")
            else:
                return False

        payload = build_project_gallery_payload(pid, relative_paths=True)
        episodes_json = json.dumps(payload["episodes"], ensure_ascii=False, indent=2)
        struct_json = json.dumps(payload["book_structure"], ensure_ascii=False, indent=2)
        proj_json = json.dumps(payload["project"], ensure_ascii=False, indent=2)

        html_text = gallery_file.read_text(encoding="utf-8")

        marker_start = "// [AUTO-SYNC-GALLERY-DATA-START]"
        marker_end = "// [AUTO-SYNC-GALLERY-DATA-END]"

        new_data_block = (
            f"{marker_start}\n"
            f"    const PROJECT_INFO = {proj_json};\n"
            f"    const BOOK_STRUCTURE = {struct_json};\n"
            f"    const EPISODES = {episodes_json};\n"
            f"    {marker_end}"
        )

        if marker_start in html_text and marker_end in html_text:
            pattern = re.compile(
                re.escape(marker_start) + r".*?" + re.escape(marker_end),
                re.DOTALL
            )
            updated_html = pattern.sub(lambda _: new_data_block, html_text, count=1)
            gallery_file.write_text(updated_html, encoding="utf-8")
            return True
        return False
    except Exception as e:
        print(f"[Gallery Sync Warning] {e}")
        return False

