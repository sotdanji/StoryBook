# -*- coding: utf-8 -*-
"""
packages/lyric_video_maker
AI 오디오 무음 트리밍/마스터링, Whisper 가사 타임스탬프 싱크, Remotion/FFmpeg 리릭 비디오 제작 독립 패키지
"""
from pathlib import Path
from typing import Optional, Dict, Any
from core.audio_processor import (
    clean_and_optimize_audio,
    trim_audio_manually,
    parse_time_to_seconds,
    get_audio_duration,
    format_seconds,
)
from core.audio_sync_director import extract_vocal_sync, format_timestamp
from core.video_director_bridge import VideoDirectorBridge


class LyricVideoMaker:
    """타 프로젝트에서 오디오 마스터링, 자막 싱크, 리릭 비디오 렌더링을 단일 인터페이스로 호출하는 SDK 클래스"""

    def __init__(self, engine_dir: Optional[Path] = None):
        self.engine_dir = Path(engine_dir) if engine_dir else None
        self.bridge = VideoDirectorBridge()

    @staticmethod
    def master_audio(input_path: Path, output_path: Path, **kwargs) -> Dict[str, Any]:
        return clean_and_optimize_audio(Path(input_path), Path(output_path), **kwargs)

    @staticmethod
    def trim_audio(file_path: Path, start_sec: float = 0.0, end_sec: Optional[float] = None) -> Dict[str, Any]:
        return trim_audio_manually(Path(file_path), start_sec=start_sec, end_sec=end_sec)

    @staticmethod
    def get_duration(file_path: Path) -> float:
        return get_audio_duration(Path(file_path))

    @staticmethod
    def align_lyrics(audio_path: str, lyrics_text: str, output_srt_path: str) -> Dict[str, Any]:
        return extract_vocal_sync(audio_path=audio_path, poem_text=lyrics_text, output_srt_path=output_srt_path)


__all__ = [
    "LyricVideoMaker",
    "VideoDirectorBridge",
    "extract_vocal_sync",
    "format_timestamp",
    "clean_and_optimize_audio",
    "trim_audio_manually",
    "parse_time_to_seconds",
    "get_audio_duration",
    "format_seconds",
]
