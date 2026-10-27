"""
StoryBook Video Manifest Builder (Remotion 연동 비디오 매니페스트 생성기)

시 텍스트, 고화질 삽화, 낭송/노래 음원을 결합하여
Remotion 비디오 엔진이 직접 렌더링할 수 있는 규격화된 manifest JSON을 생성합니다.
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Any


def get_audio_duration_seconds(audio_path: Path) -> float:
    """오디오 파일의 재생 길이(초)를 추정하거나 계산합니다."""
    if not audio_path.exists():
        return 30.0  # 기본값 30초

    try:
        # wave 모듈로 wav 길이 계산
        if audio_path.suffix.lower() == ".wav":
            import wave
            with wave.open(str(audio_path), 'rb') as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                if rate > 0:
                    return max(frames / float(rate), 5.0)
    except Exception:
        pass

    try:
        # 파일 크기 기반 일반적인 mp3/wav 재생 길이 어림(폴백)
        size_bytes = audio_path.stat().st_size
        if audio_path.suffix.lower() == ".wav":
            # 24kHz 16bit 모노 = 48000 bytes/sec
            return max(size_bytes / 48000.0, 10.0)
        elif audio_path.suffix.lower() == ".mp3":
            # 128kbps = 16000 bytes/sec
            return max(size_bytes / 16000.0, 15.0)
    except Exception:
        pass

    return 45.0


class VideoManifestBuilder:
    def __init__(self, project_dir: Path, fps: int = 30):
        self.project_dir = Path(project_dir)
        self.fps = fps

    def build_episode_manifest(
        self,
        episode_no: str,
        title: str,
        poem_body: str,
        image_path: str,
        audio_path: Optional[str] = None,
        mode: str = "recite",  # "recite" | "music" | "bgm"
        aspect_ratio: str = "16:9",  # "16:9" | "9:16"
        lyrics: Optional[str] = None,
        include_subtitles: bool = False,  # 자막 싱크 오류 및 화면 방해를 막기 위해 기본값 무자막
    ) -> Dict[str, Any]:
        """
        단일 회차의 비디오 렌더링 매니페스트(JSON 구조)를 생성합니다.
        가사 자막은 화면 몰입을 위해 기본적으로 완전히 배제되며,
        300DPI 삽화의 멀티 앵글 씬(원경, 클로즈업, 포커스, 페이드아웃) 궤적을 연산합니다.
        """
        # 해상도 설정
        if aspect_ratio == "9:16":
            width, height = 1080, 1920
        else:
            width, height = 1920, 1080

        # 절대 경로 정리
        abs_img = self.project_dir / image_path if not os.path.isabs(image_path) else Path(image_path)
        
        abs_audio = None
        duration_sec = 40.0
        if audio_path:
            abs_audio = self.project_dir / audio_path if not os.path.isabs(audio_path) else Path(audio_path)
            duration_sec = get_audio_duration_seconds(abs_audio)

        total_frames = int(duration_sec * self.fps)

        # 🎬 300 DPI 멀티 앵글 씬 분할 (4개 시네마틱 무빙 시퀀스)
        # 곡 전체를 4개의 감성 앵글 구간으로 자동 분할
        f_intro = int(total_frames * 0.18)       # 씬 1: 도입부 원경 슬로우 패닝
        f_verse = int(total_frames * 0.40)       # 씬 2: 전개부 핵심 피사체 클로즈업
        f_chorus = int(total_frames * 0.75)      # 씬 3: 절정부 감성 앵글 이동
        # 씬 4: 나머지 여운 페이드아웃

        scenes = [
            {
                "sceneId": "scene_intro",
                "name": "도입부 대청마루/풍경 원경 패닝",
                "startFrame": 0,
                "endFrame": f_intro,
                "camera": {
                    "startScale": 1.0,
                    "endScale": 1.06,
                    "panX": -2.0,
                    "panY": 1.0,
                },
                "transition": "crossfade"
            },
            {
                "sceneId": "scene_verse",
                "name": "전개부 핵심 피사체(인물/사물) 클로즈업",
                "startFrame": f_intro,
                "endFrame": f_verse,
                "camera": {
                    "startScale": 1.15,
                    "endScale": 1.25,
                    "panX": 2.5,
                    "panY": -1.5,
                },
                "transition": "crossfade"
            },
            {
                "sceneId": "scene_chorus",
                "name": "절정부 감성 피사체 딥 포커스",
                "startFrame": f_verse,
                "endFrame": f_chorus,
                "camera": {
                    "startScale": 1.20,
                    "endScale": 1.10,
                    "panX": -1.5,
                    "panY": 2.0,
                },
                "transition": "crossfade"
            },
            {
                "sceneId": "scene_outro",
                "name": "여운 물빛 번짐 원경 페이드아웃",
                "startFrame": f_chorus,
                "endFrame": total_frames,
                "camera": {
                    "startScale": 1.10,
                    "endScale": 1.0,
                    "panX": 0.0,
                    "panY": 0.0,
                },
                "transition": "fade_to_black"
            }
        ]

        manifest = {
            "version": "1.0",
            "meta": {
                "episodeNo": episode_no,
                "title": title,
                "mode": mode,
                "aspectRatio": aspect_ratio,
                "width": width,
                "height": height,
                "fps": self.fps,
                "durationInFrames": total_frames,
                "durationInSeconds": round(duration_sec, 2),
                "subtitlesEnabled": include_subtitles,
            },
            "assets": {
                "image": str(abs_img).replace("\\", "/"),
                "audio": str(abs_audio).replace("\\", "/") if abs_audio and abs_audio.exists() else None,
            },
            "visuals": {
                "style": "Korean Lyrical Watercolor / Ink & Wash",
                "vignette": True,
                "ambientParticles": True,
                "scenes": scenes,
            },
            "typography": {
                "fontFamily": "Nanum Myeongjo",
                "captions": []  # 무자막 원칙: 순수 그림과 음악에만 100% 집중
            }
        }
        return manifest

    def save_manifest(self, manifest: Dict[str, Any], output_filename: Optional[str] = None) -> Path:
        """생성된 매니페스트를 JSON 파일로 저장합니다."""
        videos_dir = self.project_dir / "videos"
        videos_dir.mkdir(parents=True, exist_ok=True)

        if not output_filename:
            ep_slug = re.sub(r'[^0-9a-zA-Z가-힣]', '_', manifest["meta"]["title"])
            mode = manifest["meta"]["mode"]
            output_filename = f"{manifest['meta']['episodeNo']}_{ep_slug}_{mode}_manifest.json"

        out_path = videos_dir / output_filename
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        return out_path

