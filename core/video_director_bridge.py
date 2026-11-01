"""
StoryBook Studio - Video Director Bridge (파이썬-비디오 엔진 연동 브릿지 모듈)
StoryBook의 시 원고, 삽화, 음원(TTS/육성/Suno)을 결합하여
tools/poem_video_engine을 통해 고화질 슬림 MP4 비디오를 완전 자동 생성합니다.
"""

import os
import glob
import shutil
import subprocess
import json
import threading
from typing import Dict, Any, Optional, List
from pathlib import Path

from core.audio_sync_director import extract_vocal_sync

BASE_DIR = Path(__file__).resolve().parent.parent
ENGINE_DIR = BASE_DIR / "tools" / "poem_video_engine"


class VideoDirectorBridge:
    def __init__(self):
        self.engine_dir = ENGINE_DIR
        self.input_dir = self.engine_dir / "input"
        self.output_dir = self.engine_dir / "output"
        self._current_tasks: Dict[str, Dict[str, Any]] = {}

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """비디오 렌더링 작업 상태 조회"""
        return self._current_tasks.get(task_id, {"status": "not_found"})

    def clean_engine_temp(self):
        """임시 파일 0Byte 완전 청소 (Zero Residual Footprint)"""
        try:
            # 1. input 폴더 청소 (README.txt 제외)
            if self.input_dir.exists():
                for item in self.input_dir.iterdir():
                    if item.name != "README.txt" and item.is_file():
                        try:
                            item.unlink()
                        except Exception:
                            pass

            # 2. .musicstep/runs 캐시 청소
            runs_dir = self.engine_dir / ".musicstep" / "runs"
            if runs_dir.exists():
                shutil.rmtree(runs_dir, ignore_errors=True)

            # 3. .musicstep lock 파일 해제
            lock_file = self.engine_dir / ".musicstep" / "make-video.lock"
            if lock_file.exists():
                try:
                    lock_file.unlink()
                except Exception:
                    pass
        except Exception as e:
            print(f"[VideoDirectorBridge] 임시 파일 정리 오류: {e}")

    def render_poem_video(
        self,
        project_name: str,
        episode_num: int,
        title: str,
        poem_lines: List[str],
        image_path: str,
        audio_path: str,
        aspect_ratio: str = "16:9",
        spectrum_style: str = "bar",
        is_async: bool = False
    ) -> Dict[str, Any]:
        """
        시 낭송 영상 원클릭 렌더링 파이프라인 (16:9 와이드 및 9:16 세로형 쇼츠 지원)
        """
        task_id = f"{project_name}_ep{episode_num}_{int(os.times().system * 100)}"
        self._current_tasks[task_id] = {
            "status": "starting",
            "progress": 0,
            "project": project_name,
            "episode": episode_num,
            "title": title,
            "aspect_ratio": aspect_ratio,
            "spectrum_style": spectrum_style
        }

        if is_async:
            thread = threading.Thread(
                target=self._execute_render_pipeline,
                args=(task_id, project_name, episode_num, title, poem_lines, image_path, audio_path, aspect_ratio, spectrum_style),
                daemon=True
            )
            thread.start()
            return {"status": "started", "task_id": task_id}
        else:
            return self._execute_render_pipeline(
                task_id, project_name, episode_num, title, poem_lines, image_path, audio_path, aspect_ratio, spectrum_style
            )

    def render_song_video(
        self,
        project_name: str,
        episode_num: int,
        title: str,
        lyrics_lines: List[str],
        image_path: str,
        audio_path: str,
        custom_srt_path: Optional[str] = None,
        aspect_ratio: str = "16:9",
        spectrum_style: str = "mirror",
        lyric_mode: str = "focus2line",
        is_async: bool = False
    ) -> Dict[str, Any]:
        """
        서정 노래 뮤직비디오 원클릭 렌더링 파이프라인
        """
        task_id = f"{project_name}_song_ep{episode_num}_{int(os.times().system * 100)}"
        self._current_tasks[task_id] = {
            "status": "starting",
            "progress": 0,
            "project": project_name,
            "episode": episode_num,
            "title": title,
            "video_type": "song",
            "aspect_ratio": aspect_ratio,
            "spectrum_style": spectrum_style,
            "lyric_mode": lyric_mode
        }

        if is_async:
            thread = threading.Thread(
                target=self._execute_render_pipeline,
                args=(task_id, project_name, episode_num, title, lyrics_lines, image_path, audio_path, aspect_ratio, spectrum_style, "song", lyric_mode, custom_srt_path),
                daemon=True
            )
            thread.start()
            return {"status": "started", "task_id": task_id}
        else:
            return self._execute_render_pipeline(
                task_id, project_name, episode_num, title, lyrics_lines, image_path, audio_path, aspect_ratio, spectrum_style, "song", lyric_mode, custom_srt_path
            )

    def _execute_render_pipeline(
        self,
        task_id: str,
        project_name: str,
        episode_num: int,
        title: str,
        poem_lines: List[str],
        image_path: str,
        audio_path: str,
        aspect_ratio: str = "16:9",
        spectrum_style: str = "bar",
        video_type: str = "poem",
        lyric_mode: str = "rolling",
        custom_srt_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """내부 렌더링 파이프라인 실행 루틴 (시 낭송 및 서정 노래 공통 지원)"""
        try:
            self._current_tasks[task_id]["status"] = "preparing"
            self._current_tasks[task_id]["progress"] = 10

            # 1. 이전 임시 파일 청소
            self.clean_engine_temp()

            if not os.path.exists(image_path):
                raise FileNotFoundError(f"삽화 이미지를 찾을 수 없습니다: {image_path}")
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"음원 파일을 찾을 수 없습니다: {audio_path}")

            # 2. 안전한 파일명 정규화 (NFC)
            safe_title = "".join(c for c in title if c.isalnum() or c in (" ", "_", "-")).strip()
            if not safe_title:
                safe_title = f"ep{episode_num}"

            # 3. 자막 (.srt) 준비: 사용자 제공 SRT 또는 Whisper AI 싱크 추출
            srt_target = str(self.input_dir / f"{safe_title}.srt")
            if custom_srt_path and os.path.exists(custom_srt_path):
                self._current_tasks[task_id]["status"] = "applying_custom_srt"
                self._current_tasks[task_id]["progress"] = 25
                shutil.copyfile(custom_srt_path, srt_target)
                sync_res = {"duration": 0, "cues_count": len(poem_lines)}
            else:
                self._current_tasks[task_id]["status"] = "analyzing_audio_sync"
                self._current_tasks[task_id]["progress"] = 25
                sync_res = extract_vocal_sync(
                    audio_path=audio_path,
                    poem_lines=poem_lines,
                    output_srt_path=srt_target,
                    model_size="base"
                )

            # 4. 음원 및 이미지 input 복사
            audio_ext = os.path.splitext(audio_path)[1].lower()
            img_ext = os.path.splitext(image_path)[1].lower()
            
            engine_audio = self.input_dir / f"{safe_title}{audio_ext}"
            engine_img = self.input_dir / f"{safe_title}{img_ext}"

            shutil.copyfile(audio_path, engine_audio)
            shutil.copyfile(image_path, engine_img)

            # 5. Remotion 비디오 렌더러 실행
            self._current_tasks[task_id]["status"] = "rendering"
            self._current_tasks[task_id]["progress"] = 40

            cmd = [
                "node", "scripts/make-video.mjs",
                "--aspect-ratio", aspect_ratio,
                "--spectrum", spectrum_style,
                "--video-type", video_type,
                "--lyric-mode", lyric_mode
            ]
            proc = subprocess.Popen(
                cmd,
                cwd=str(self.engine_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="ignore",
                bufsize=1
            )

            stdout_lines = []
            if proc.stdout:
                for line in proc.stdout:
                    line_str = line.strip()
                    if line_str:
                        stdout_lines.append(line_str)
                        match = re.search(r'영상 만드는 중 ·\s*(\d+)%', line_str)
                        if match:
                            remotion_pct = int(match.group(1))
                            mapped_pct = min(88, 40 + int(remotion_pct * 0.48))
                            self._current_tasks[task_id]["progress"] = mapped_pct
                            self._current_tasks[task_id]["status"] = f"프레임 렌더링 중 ({remotion_pct}%)"

            proc.wait()
            if proc.returncode != 0:
                error_log = "\n".join(stdout_lines)
                raise RuntimeError(f"영상 렌더링 실패:\n{error_log}")

            # 6. 완성된 비디오 프로젝트 보관소로 이관
            self._current_tasks[task_id]["status"] = "saving"
            self._current_tasks[task_id]["progress"] = 90

            rendered_files = list(self.output_dir.glob("*_lyric-video.mp4"))
            if not rendered_files:
                raise FileNotFoundError("렌더링된 출력 비디오 파일을 찾을 수 없습니다.")

            latest_video = max(rendered_files, key=os.path.getmtime)

            project_videos_dir = BASE_DIR / "projects" / project_name / "videos"
            project_videos_dir.mkdir(parents=True, exist_ok=True)

            is_shorts = (aspect_ratio == "9:16")
            is_song = (video_type == "song")

            if is_song:
                prefix_label = "노래_쇼츠" if is_shorts else "노래_영상"
            else:
                prefix_label = "쇼츠_영상" if is_shorts else "시낭송_영상"

            final_video_name = f"{episode_num:02d}_{safe_title}_{prefix_label}.mp4"
            final_video_path = project_videos_dir / final_video_name
            shutil.copyfile(latest_video, final_video_path)

            # 7. 썸네일 프리뷰 복사
            preview_files = list((self.engine_dir / ".musicstep" / "runs").glob("*/preview.png"))
            final_preview_path = None
            if preview_files:
                latest_preview = max(preview_files, key=os.path.getmtime)
                if is_song:
                    preview_suffix = "song_shorts_preview.png" if is_shorts else "song_preview.png"
                else:
                    preview_suffix = "shorts_preview.png" if is_shorts else "preview.png"
                final_preview_name = f"{episode_num:02d}_{safe_title}_{preview_suffix}"
                final_preview_path = project_videos_dir / final_preview_name
                shutil.copyfile(latest_preview, final_preview_path)

            # 8. 최종 임시 파일 자동 클린업 (용량 최소화)
            self.clean_engine_temp()

            result = {
                "status": "complete",
                "progress": 100,
                "video_path": str(final_video_path),
                "video_name": final_video_name,
                "preview_path": str(final_preview_path) if final_preview_path else None,
                "duration": sync_res.get("duration", 0),
                "cues_count": sync_res.get("cues_count", len(poem_lines))
            }
            self._current_tasks[task_id].update(result)
            return result

        except Exception as e:
            err_msg = str(e)
            print(f"[VideoDirectorBridge] 렌더링 파이프라인 에러: {err_msg}")
            self.clean_engine_temp()
            err_res = {"status": "error", "message": err_msg}
            self._current_tasks[task_id].update(err_res)
            return err_res

    def merge_playlist_video(
        self,
        project_name: str,
        aspect_ratio: str = "16:9"
    ) -> Dict[str, Any]:
        """
        시화집 전편(EP01~EP10 등) 낭송 영상을 순서대로 무손실 초고속 결합하여
        하나의 롱폼 '시화집 낭송 플레이리스트 영상'으로 완성합니다.
        """
        try:
            project_videos_dir = BASE_DIR / "projects" / project_name / "videos"
            if not project_videos_dir.exists():
                raise FileNotFoundError(f"프로젝트 영상 폴더가 존재하지 않습니다: {project_videos_dir}")

            is_shorts = (aspect_ratio == "9:16")
            filter_pattern = "*_쇼츠_영상.mp4" if is_shorts else "*_시낭송_영상.mp4"

            # 1. 대상 비디오 파일 탐색 및 에피소드 번호순 정렬
            candidates = list(project_videos_dir.glob(filter_pattern))
            if not candidates:
                # 일반 mp4 fallback
                candidates = [
                    f for f in project_videos_dir.glob("*.mp4")
                    if not f.name.endswith("_플레이리스트.mp4") and not f.name.endswith("_전편_연속재생.mp4")
                ]

            if len(candidates) < 2:
                raise ValueError(f"플레이리스트 결합을 위해서는 최소 2개 이상의 완성된 영상이 필요합니다. (현재: {len(candidates)}개)")

            # 파일명 앞자리(01_, 02_ 등) 기준 정렬
            def sort_key(p: Path):
                digits = re.findall(r'^\d+', p.name)
                return int(digits[0]) if digits else 999

            sorted_videos = sorted(candidates, key=sort_key)

            # 2. FFmpeg concat 파일리스트 생성
            concat_list_file = project_videos_dir / "concat_playlist.txt"
            with open(concat_list_file, "w", encoding="utf-8") as f:
                for v in sorted_videos:
                    # Windows 경로 안전하게 포맷팅
                    safe_v_path = str(v.resolve()).replace("\\", "/")
                    f.write(f"file '{safe_v_path}'\n")

            # 3. FFmpeg 무손실 결합 실행 (-c copy)
            ratio_label = "쇼츠_모음집" if is_shorts else "전편_플레이리스트"
            output_filename = f"{project_name}_시화집_{ratio_label}.mp4"
            output_path = project_videos_dir / output_filename

            cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_list_file),
                "-c", "copy",
                str(output_path)
            ]

            proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")

            # concat 파일 삭제
            try:
                concat_list_file.unlink(missing_ok=True)
            except Exception:
                pass

            if proc.returncode != 0 or not output_path.exists():
                raise RuntimeError(f"영상 결합 실패:\n{proc.stderr}")

            size_mb = round(os.path.getsize(output_path) / (1024 * 1024), 2)

            return {
                "success": True,
                "output_filename": output_filename,
                "output_path": str(output_path),
                "count": len(sorted_videos),
                "size_mb": size_mb,
                "episodes": [v.name for v in sorted_videos]
            }

        except Exception as e:
            print(f"[VideoDirectorBridge] 플레이리스트 결합 에러: {e}")
            return {"success": False, "error": str(e)}


video_director_bridge = VideoDirectorBridge()

