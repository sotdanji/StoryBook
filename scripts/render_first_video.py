# -*- coding: utf-8 -*-
import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.video_director_bridge import video_director_bridge
from core.project_manager import project_manager

project_name = "샘플_기억상자"
ep_num = 1
mgr = project_manager.get_manuscript_manager(project_name)
work = mgr.get_work_by_episode(str(ep_num))

title = work.title
lyrics_lines = [l.strip() for l in work.lyrics.splitlines() if l.strip() and not l.strip().startswith('[')]
image_path = str(BASE_DIR / "projects" / project_name / "images" / "01_밍밭에서.jpg")
audio_path = str(BASE_DIR / "projects" / project_name / "music" / "01_음원.mp3")

print(f"Starting song video render for {title}...")
print(f"Image: {image_path}")
print(f"Audio: {audio_path}")
print(f"Lyrics lines: {len(lyrics_lines)}")

res = video_director_bridge.render_song_video(
    project_name=project_name,
    episode_num=ep_num,
    title=title,
    lyrics_lines=lyrics_lines,
    image_path=image_path,
    audio_path=audio_path,
    aspect_ratio="16:9",
    spectrum_style="mirror",
    lyric_mode="focus2line",
    is_async=False
)

print("Render result:", res)

