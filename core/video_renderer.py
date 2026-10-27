"""
StoryBook Video Renderer Engine

FFmpeg 기반으로 300 DPI 수채화·수묵화 삽화와 노래/낭송 음원을 결합하여
고화질 MP4 시네마틱 비디오(16:9 / 9:16)를 로컬에서 직접 렌더링합니다.
가사 자막 및 인물 립싱크를 완전히 배제하고, 순수 4단계 서정적 앵글 씬 무빙으로 영상을 제작합니다.
메모리 누수 없는 스트리밍 켄 번스(Ken Burns) 필터와 오디오 무결성 자동 검증/폴백을 지원합니다.
"""

import json
import os
import re
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from core.video_manifest_builder import VideoManifestBuilder, get_audio_duration_seconds


class VideoRenderer:
    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir)
        self.videos_dir = self.project_dir / "videos"
        self.videos_dir.mkdir(parents=True, exist_ok=True)
        self.ffmpeg_cmd = shutil.which("ffmpeg") or "ffmpeg"
        self.ffprobe_cmd = shutil.which("ffprobe") or "ffprobe"

    def list_rendered_videos(self) -> List[Dict[str, Any]]:
        """프로젝트에 이미 렌더링된 비디오 목록을 반환합니다."""
        results = []
        if not self.videos_dir.exists():
            return results

        for f in sorted(self.videos_dir.glob("*.mp4"), key=lambda x: x.stat().st_mtime, reverse=True):
            stat = f.stat()
            name = f.stem
            aspect = "16:9" if "16x9" in name else ("9:16" if "9x16" in name else "16:9")
            mode = "music" if "music" in name else ("recite" if "recite" in name else "bgm")
            display_name = name.replace("_music", " [노래]").replace("_recite", " [낭송]").replace("_bgm", " [BGM]").replace("_16x9", " (16:9)").replace("_9x16", " (9:16)")
            results.append({
                "filename": f.name,
                "path": str(f).replace("\\", "/"),
                "web_url": f"/api/videos/download/{f.name}",
                "sizeMb": round(stat.st_size / (1024 * 1024), 2),
                "modifiedTime": stat.st_mtime,
                "aspect": aspect,
                "mode": mode,
                "displayName": display_name
            })
        return results

    def validate_audio_file(self, audio_path: Path) -> Tuple[bool, float, str]:
        """
        오디오 파일의 무결성을 ffprobe로 검사합니다.
        손상되었거나 헤더가 없는 파일(Invalid data found 등)을 사전 감지합니다.
        반환: (유효여부, 재생시간, 오류메시지)
        """
        if not audio_path.exists():
            return False, 0.0, "파일이 존재하지 않습니다."
        
        try:
            cmd = [
                self.ffprobe_cmd,
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(audio_path)
            ]
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=10
            )
            if res.returncode != 0 or not res.stdout.strip():
                err_msg = res.stderr.strip() or "디코딩 불가능한 오디오 형식"
                return False, 0.0, err_msg
            
            dur = float(res.stdout.strip())
            if dur <= 0.5:
                return False, dur, "재생 시간이 너무 짧음"
            return True, dur, ""
        except Exception as e:
            return False, 0.0, str(e)

    def resolve_safe_audio(self, episode_no: str, requested_audio: Optional[str]) -> Tuple[Optional[Path], float, str]:
        """
        요청된 오디오 경로를 검증하고, 손상된 경우 동일 회차의 대체 음원(낭송 WAV 등)으로 자동 폴백합니다.
        """
        ep_clean = re.sub(r'[^0-9]', '', episode_no).zfill(2)
        music_dir = self.project_dir / "music"
        
        # 1차 시도: 요청된 오디오 검증
        if requested_audio:
            cand = self.project_dir / requested_audio if not os.path.isabs(requested_audio) else Path(requested_audio)
            is_valid, dur, err = self.validate_audio_file(cand)
            if is_valid:
                return cand, dur, "정상 음원"
            else:
                print(f"[VideoRenderer] 요청 음원 손상 감지 ({cand.name}): {err} -> 대체 음원 탐색 중...")

        # 2차 시도: 동일 회차의 낭송 WAV 파일 탐색
        recite_cand = music_dir / f"{ep_clean}_낭송.wav"
        if recite_cand.exists():
            is_valid, dur, _ = self.validate_audio_file(recite_cand)
            if is_valid:
                print(f"[VideoRenderer] 대체 낭송 음원으로 안전 전환: {recite_cand.name}")
                return recite_cand, dur, "낭송 음원으로 자동 폴백"

        # 3차 시도: 동일 회차의 다른 mp3/wav 파일 탐색
        for cand in sorted(music_dir.glob(f"{ep_clean}_*")):
            if cand.suffix.lower() in [".mp3", ".wav", ".m4a"]:
                is_valid, dur, _ = self.validate_audio_file(cand)
                if is_valid:
                    print(f"[VideoRenderer] 대체 음원 발견: {cand.name}")
                    return cand, dur, f"{cand.name} 음원으로 폴백"

        return None, 40.0, "유효한 음원이 없어 무음 서정 영상으로 진행"

    def render_episode_video(
        self,
        episode_no: str,
        title: str,
        image_path: str,
        audio_path: Optional[str] = None,
        aspect_ratio: str = "16:9",
        mode: str = "music",  # "music" | "recite" | "bgm"
    ) -> Path:
        """
        단일 회차의 고화질 시네마틱 MP4 비디오를 렌더링합니다.
        메모리 누수 없는 스트리밍 켄 번스 필터와 오디오 무결성 자동 검증을 적용합니다.
        """
        abs_img = self.project_dir / image_path if not os.path.isabs(image_path) else Path(image_path)
        if not abs_img.exists():
            alt_img = self.project_dir / "images" / Path(image_path).name
            if alt_img.exists():
                abs_img = alt_img
            else:
                raise FileNotFoundError(f"삽화 이미지를 찾을 수 없습니다: {image_path}")

        # 오디오 무결성 검증 및 안전한 음원 결정
        safe_audio, duration_sec, audio_note = self.resolve_safe_audio(episode_no, audio_path)
        print(f"[VideoRenderer] 음원 상태: {audio_note} (길이: {duration_sec:.1f}초)")

        # 화면 해상도 설정
        if aspect_ratio == "9:16":
            width, height = 1080, 1920
        else:
            width, height = 1920, 1080

        # 파일명 생성
        clean_ep = re.sub(r'[^0-9a-zA-Z가-힣]', '', episode_no)
        clean_title = re.sub(r'[^0-9a-zA-Z가-힣]', '_', title)
        actual_mode = mode if safe_audio else "silent"
        output_filename = f"{clean_ep}_{clean_title}_{actual_mode}_{aspect_ratio.replace(':', 'x')}.mp4"
        output_path = self.videos_dir / output_filename

        fps = 30
        
        # 캔버스를 1.15배 스케일업 후, 시간(t)에 따라 부드러운 패닝/줌을 주는 메모리 안전 켄 번스 필터
        # zoompan의 내부 큐 메모리 누수(Cannot allocate memory OOM)를 완전히 해결함
        scale_w = int(width * 1.15)
        scale_h = int(height * 1.15)
        x_diff = scale_w - width
        y_diff = scale_h - height

        crop_expr_x = f"(iw-{width})/2 + {x_diff * 0.4:.1f}*sin(t*0.08)"
        crop_expr_y = f"(ih-{height})/2 + {y_diff * 0.4:.1f}*cos(t*0.06)"

        fade_out_st = max(duration_sec - 2.0, 1.0)

        vf_filters = [
            f"scale={scale_w}:{scale_h}:force_original_aspect_ratio=increase",
            f"crop={width}:{height}:'{crop_expr_x}':'{crop_expr_y}'",
            "vignette=PI/4",
            "fade=t=in:st=0:d=1.5",
            f"fade=t=out:st={fade_out_st:.2f}:d=2.0",
            "format=yuv420p"
        ]
        filter_complex = ",".join(vf_filters)

        cmd = [
            self.ffmpeg_cmd,
            "-y",  # 기존 파일 덮어쓰기
            "-loop", "1",
            "-framerate", str(fps),
            "-i", str(abs_img.resolve()),
        ]

        if safe_audio and safe_audio.exists():
            afade_out_st = max(duration_sec - 2.5, 1.0)
            cmd.extend([
                "-i", str(safe_audio.resolve()),
                "-t", str(duration_sec),
                "-vf", filter_complex,
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "21",
                "-c:a", "aac",
                "-b:a", "192k",
                "-af", f"afade=t=in:st=0:d=1.0,afade=t=out:st={afade_out_st:.2f}:d=2.5",
                "-shortest",
                str(output_path.resolve())
            ])
        else:
            # 오디오가 없거나 손상된 경우 무음 서정 영상
            cmd.extend([
                "-t", str(duration_sec),
                "-vf", filter_complex,
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "21",
                str(output_path.resolve())
            ])

        print(f"[VideoRenderer] 비디오 렌더링 시작: {output_path.name}")
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )
        if proc.returncode != 0:
            print(f"[VideoRenderer 에러] FFmpeg 실패:\n{proc.stderr}")
            raise RuntimeError(f"비디오 렌더링 실패: {proc.stderr[-400:]}")

        size_mb = round(output_path.stat().st_size / (1024 * 1024), 2)
        print(f"[VideoRenderer 완료] 성공적으로 비디오 생성됨: {output_path.name} ({size_mb} MB)")
        return output_path
