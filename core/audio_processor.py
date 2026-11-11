"""
StoryBook Studio - 안실장 오디오 프로세서 (Audio Processor)
1. 외부 녹음기(Web Audio Recorder 등)나 다운로더에서 유입되는 음원의 앞뒤 무음 구간 자동 트리밍
2. Suno 자동 연속 재생으로 인한 '다음 곡 침범 구간(Next-Song Bleed)' 자동 감지 및 싹둑 잘라내기
3. 수동 미세 구간 자르기(Manual Trim) 및 표준 고음질 320kbps MP3 자동 변환/최적화
"""

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List


def get_audio_duration(file_path: Path) -> Optional[float]:
    """ffprobe를 사용하여 오디오 파일의 재생 시간(초)을 측정합니다."""
    ffprobe_bin = shutil.which("ffprobe")
    if not ffprobe_bin or not file_path.exists():
        return None
    try:
        cmd = [
            ffprobe_bin, "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(file_path)
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
        if res.returncode == 0 and res.stdout.strip():
            return float(res.stdout.strip())
    except Exception:
        pass
    return None


def format_seconds(seconds: Optional[float]) -> str:
    """초 단위를 MM:SS 포맷 문자열로 변환합니다."""
    if seconds is None or seconds < 0:
        return "00:00"
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"


def parse_time_to_seconds(time_str: str) -> Optional[float]:
    """MM:SS 또는 초 단위 문자열을 float 초로 파싱합니다."""
    time_str = str(time_str).strip()
    if not time_str:
        return None
    try:
        if ":" in time_str:
            parts = time_str.split(":")
            if len(parts) == 2:
                return float(parts[0]) * 60 + float(parts[1])
            elif len(parts) == 3:
                return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
        return float(time_str)
    except Exception:
        return None


def detect_next_song_bleed(file_path: Path, dur: float) -> Optional[Dict[str, float]]:
    """
    Suno 등에서 노래가 끝나고 침묵 후 '다음 곡'이 잠깐 재생된 침범 구간(Next-song bleed)을 감지합니다.
    규칙:
    - 곡 마지막 30초 이내에 0.6초 이상의 무음 간격(Silence Gap)이 발생하고,
    - 그 무음 간격 이후 남은 끝부분 소리(다음곡 시작)가 12초 이하로 짧게 들어간 경우
    """
    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin or dur < 20.0:
        return None

    try:
        cmd = [
            ffmpeg_bin, "-i", str(file_path),
            "-af", "silencedetect=noise=-32dB:d=0.35",
            "-f", "null", "-"
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
        stderr_text = proc.stderr.decode("utf-8", errors="replace")

        silences: List[Tuple[float, float, float]] = []
        curr_start = None

        for line in stderr_text.splitlines():
            m_start = re.search(r"silence_start:\s*([0-9.]+)", line)
            if m_start:
                curr_start = float(m_start.group(1))
            m_end = re.search(r"silence_end:\s*([0-9.]+)\s*\|\s*silence_duration:\s*([0-9.]+)", line)
            if m_end and curr_start is not None:
                end = float(m_end.group(1))
                duration = float(m_end.group(2))
                silences.append((curr_start, end, duration))
                curr_start = None

        # 마지막 무음 구간부터 검사 (뒤에서부터)
        for s_start, s_end, s_dur in reversed(silences):
            tail = dur - s_end
            if s_start > (dur - 30.0) and s_dur >= 0.6 and 0.1 <= tail <= 12.0:
                cut_point = round(s_start + 0.3, 2)
                return {
                    "cut_point": cut_point,
                    "song_end": round(s_start, 2),
                    "silence_duration": round(s_dur, 2),
                    "next_song_bleed": round(tail, 2)
                }
    except Exception as e:
        print(f"[AudioProcessor] Bleed detection error: {e}")

    return None


def _sync_audio_to_r2(audio_path: Path) -> None:
    """처리된 오디오 파일을 Cloudflare R2 단일 마스터 스토리지로 자동 동기화"""
    try:
        from core.r2_storage import r2_storage, PROJECTS_DIR
        if r2_storage.is_r2_configured and audio_path.exists():
            resolved_audio = audio_path.resolve()
            resolved_proj = PROJECTS_DIR.resolve()
            if str(resolved_audio).startswith(str(resolved_proj)):
                rel_key = resolved_audio.relative_to(resolved_proj).as_posix()
                r2_storage.upload_bytes(
                    audio_path.read_bytes(),
                    rel_key,
                    local_cache_path=audio_path
                )
    except Exception as r2_err:
        print(f"[AudioProcessor R2 동기화 건너뜀]: {r2_err}")


def clean_and_optimize_audio(input_path: Path, output_path: Path) -> Dict[str, Any]:
    """
    오디오 파일을 종합 검사하여:
    1. 다음 곡 자동 재생 침범 구간(Next-song bleed) 자동 절단
    2. 앞뒤 무음 자동 제거
    3. 클릭 잡음 방지 미세 페이드인/아웃 적용
    4. 고음질 320kbps MP3로 최적화 저장
    """
    result: Dict[str, Any] = {
        "success": True,
        "trimmed": False,
        "bleed_cut": False,
        "orig_duration": None,
        "orig_duration_str": "",
        "final_duration": None,
        "final_duration_str": "",
        "trimmed_seconds": 0.0,
        "message": ""
    }

    if not input_path.exists() or input_path.stat().st_size == 0:
        result["success"] = False
        result["message"] = "오디오 파일이 비어 있거나 존재하지 않습니다."
        return result

    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        shutil.copy2(input_path, output_path)
        _sync_audio_to_r2(output_path)
        result["message"] = "FFmpeg 미설치로 원본 파일 그대로 안전하게 보관되었습니다."
        return result

    # 1. 원본 재생 시간 측정
    orig_dur = get_audio_duration(input_path)
    result["orig_duration"] = orig_dur
    result["orig_duration_str"] = format_seconds(orig_dur)

    # 2. 다음 곡 침범 구간(Next-song bleed) 감지
    bleed_info = None
    if orig_dur and orig_dur >= 20.0:
        bleed_info = detect_next_song_bleed(input_path, orig_dur)

    # 3. 임시 파일 준비
    temp_target = output_path.with_name(f"temp_proc_{output_path.name}")
    if temp_target.exists():
        temp_target.unlink()

    # 4. 필터 체인 구성
    filters = []
    
    # 만약 다음 곡 침범이 감지되었다면 해당 지점까지만 자르고 페이드아웃
    bleed_msg = ""
    if bleed_info:
        cut_pt = bleed_info["cut_point"]
        fade_st = max(0.0, cut_pt - 1.2)
        filters.append(f"atrim=0:{cut_pt}")
        filters.append(f"afade=t=out:st={fade_st}:d=1.2")
        result["bleed_cut"] = True
        bleed_msg = f"다음 곡 침범 구간({bleed_info['next_song_bleed']}초)을 감지하여 잘라내고, "

    # 앞뒤 무음 제거 필터 (silenceremove)
    filters.append("silenceremove=start_periods=1:start_duration=0.2:start_threshold=-45dB")
    filters.append("areverse")
    filters.append("silenceremove=start_periods=1:start_duration=0.2:start_threshold=-45dB")
    filters.append("areverse")
    filters.append("afade=t=in:ss=0:d=0.06")

    filter_chain = ",".join(filters)

    cmd = [
        ffmpeg_bin, "-y",
        "-i", str(input_path),
        "-af", filter_chain,
        "-codec:a", "libmp3lame",
        "-b:a", "320k",
        str(temp_target)
    ]

    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=45)
        if proc.returncode == 0 and temp_target.exists() and temp_target.stat().st_size > 1024:
            if output_path.exists():
                output_path.unlink()
            temp_target.rename(output_path)

            final_dur = get_audio_duration(output_path)
            result["final_duration"] = final_dur
            result["final_duration_str"] = format_seconds(final_dur)

            if orig_dur is not None and final_dur is not None:
                trimmed_diff = max(0.0, round(orig_dur - final_dur, 1))
                result["trimmed_seconds"] = trimmed_diff
                if trimmed_diff >= 0.3:
                    result["trimmed"] = True
                    result["message"] = (
                        f"✨ {bleed_msg}앞뒤 무음 구간을 포함하여 총 {trimmed_diff:.1f}초를 깔끔하게 다듬었습니다! "
                        f"({result['orig_duration_str']} ➔ {result['final_duration_str']})"
                    )
                else:
                    result["message"] = (
                        f"무음 없이 정갈한 음원입니다. 표준 고음질(320k) MP3로 등록되었습니다. ({result['final_duration_str']})"
                    )
            else:
                result["message"] = "음원을 고음질(320k) MP3로 최적화하여 등록했습니다."
            _sync_audio_to_r2(output_path)
            return result
    except Exception as e:
        print(f"[AudioProcessor] Processing warning: {e}")

    # 실패 시 원래 파일 복사
    if temp_target.exists():
        temp_target.unlink()
    shutil.copy2(input_path, output_path)
    _sync_audio_to_r2(output_path)
    result["message"] = "오디오 원본 포맷으로 안전하게 보존되었습니다."
    return result


def trim_audio_manually(file_path: Path, start_sec: float = 0.0, end_sec: Optional[float] = None) -> Dict[str, Any]:
    """
    사용자가 지정한 구간(start_sec ~ end_sec)으로 오디오를 정밀하게 수동 자르기합니다.
    부드러운 페이드인(0.05초) 및 페이드아웃(0.8초) 적용.
    """
    result: Dict[str, Any] = {
        "success": False,
        "message": "",
        "new_duration": 0.0,
        "new_duration_str": ""
    }

    if not file_path.exists():
        result["message"] = "음원 파일이 존재하지 않습니다."
        return result

    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        result["message"] = "FFmpeg 미설치로 자르기를 실행할 수 없습니다."
        return result

    total_dur = get_audio_duration(file_path) or 0.0
    start_sec = max(0.0, float(start_sec))
    if end_sec is None or end_sec <= 0.0 or end_sec > total_dur:
        end_sec = total_dur

    if start_sec >= end_sec:
        result["message"] = "시작 시간이 끝 시간보다 크거나 같을 수 없습니다."
        return result

    cut_dur = end_sec - start_sec
    temp_target = file_path.with_name(f"temp_manual_trim_{file_path.name}")
    if temp_target.exists():
        temp_target.unlink()

    # 페이드아웃 시작 지점
    fadeout_start = max(0.0, cut_dur - 0.8)
    filter_chain = f"afade=t=in:ss=0:d=0.06,afade=t=out:st={fadeout_start}:d=0.8"

    cmd = [
        ffmpeg_bin, "-y",
        "-ss", f"{start_sec:.3f}",
        "-t", f"{cut_dur:.3f}",
        "-i", str(file_path),
        "-af", filter_chain,
        "-codec:a", "libmp3lame",
        "-b:a", "320k",
        str(temp_target)
    ]

    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
        if proc.returncode == 0 and temp_target.exists() and temp_target.stat().st_size > 1024:
            file_path.unlink()
            temp_target.rename(file_path)
            new_dur = get_audio_duration(file_path)
            result["success"] = True
            result["new_duration"] = new_dur
            result["new_duration_str"] = format_seconds(new_dur)
            result["message"] = f"구간 자르기 완료: {format_seconds(start_sec)} ~ {format_seconds(end_sec)} (총 길이: {result['new_duration_str']})"
            return result
        else:
            stderr_err = proc.stderr.decode("utf-8", errors="replace")
            result["message"] = f"자르기 실패: {stderr_err[:120]}"
    except Exception as e:
        result["message"] = f"자르기 오류: {e}"

    if temp_target.exists():
        temp_target.unlink()
    return result
