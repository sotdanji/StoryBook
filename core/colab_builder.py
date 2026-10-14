# -*- coding: utf-8 -*-
"""
core/colab_builder.py
Google Colab YuE2 원클릭 작곡 노트북 생성 및 조립 모듈
- 1단계: GPU 점검 (T4 16GB)
- 2단계: 패키지 및 엔진 설치
- 3단계: [동적 조립 모듈] 작품별 제목, 장르 태그, 노랫말 설정
- 4단계: YuE 음원 추론 및 렌더링
- 5단계: 미리듣기 및 원클릭 자동 다운로드
"""
import re
import json
from pathlib import Path
from typing import Dict, Any, Optional

DEFAULT_GENRE_PROMPT = (
    "Korean Traditional Folk Ballad, Mournful Elegy, Han, Gugak Crossover, "
    "Haegeum, Daegum solo, Gayageum, Janggu, Deep Korean Buk, Soft Strings, Low Piano, "
    "Slow 68 BPM, Joongmori rhythm, sorrowful traditional female vocal, heartbreaking"
)

def build_yue2_notebook_dict(
    episode_no: str = "제01화",
    title: str = "새벽 대청",
    genre_prompt: str = DEFAULT_GENRE_PROMPT,
    lyrics: str = "",
    book_title: str = "시화집"
) -> Dict[str, Any]:
    """
    작품 정보(에피소드, 제목, 장르, 가사)를 전달받아
    완전하게 조립된 Google Colab (.ipynb) 딕셔너리를 생성합니다.
    """
    clean_ep = re.sub(r'[^0-9]', '', episode_no).zfill(2) if episode_no else "01"
    clean_title = re.sub(r'[\s\\/*?:"<>|]', '_', title) if title else "노래"
    out_filename = f"{clean_ep}_{clean_title}.mp3"

    if not lyrics.strip():
        lyrics = f"""[Verse 1]
{title} 그 길목에
바람이 분다

[Chorus]
흘러가는 세월 속에
남겨진 우리들의 이야기

[Outro]
영원히 기억되리"""

    # 이스케이프 처리된 가사 문자열
    lyrics_escaped = lyrics.replace('\\', '\\\\').replace('"', '\\"').replace('\r\n', '\n')

    cells = [
        # 셀 1: 마크다운 개요
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                f"# 🎵 [{episode_no}] {title} — YuE 원클릭 음원 생성기 (Colab T4 최적화판)\n",
                "\n",
                f"- **시집**: 『{book_title}』\n",
                f"- **작품**: [{episode_no}] 「{title}」\n",
                f"- **출력 파일**: `{out_filename}`\n",
                "- **환경**: Google Colab 무료 T4 GPU (15GB VRAM)\n",
                "\n",
                "> 💡 **[초간단 원클릭 실행 안내]**\n",
                "> 상단 메뉴에서 **[런타임] → [모두 실행]**을 누르면 자동으로 패키지 설치부터 모델 로드, 음원 생성, 그리고 브라우저로 **`" + out_filename + "` 자동 다운로드**까지 완벽하게 진행됩니다."
            ]
        },
        # 셀 2: 1단계 GPU 점검
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# [1단계] GPU 하드웨어 가속기 점검 (Google Colab T4 16GB VRAM)\n",
                "!nvidia-smi\n",
                "\n",
                "import torch\n",
                "print(f\"CUDA 사용 가능 여부: {torch.cuda.is_available()}\")\n",
                "if torch.cuda.is_available():\n",
                "    print(f\"연결된 GPU: {torch.cuda.get_device_name(0)}\")\n",
                "    print(f\"VRAM 총량: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.2f} GB\")\n",
                "else:\n",
                "    raise SystemError(\"GPU가 감지되지 않았습니다. [런타임] -> [런타임 유형 변경]에서 T4 GPU를 선택해 주세요!\")"
            ]
        },
        # 셀 3: 2단계 패키지 설치
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# [2단계] YuE 및 오디오 신디사이징 필수 종속성 패키지 설치\n",
                "!pip install -q --upgrade pip\n",
                "!pip install -q torch torchaudio transformers accelerate soundfile librosa pydub einops omegaconf sentencepiece bitsandbytes\n",
                "\n",
                "# YuE 리포지토리 클론 및 로컬 패키지 설치\n",
                "%cd /content\n",
                "!rm -rf /content/YuE\n",
                "!git clone https://github.com/multimodal-art-projection/YuE.git /content/YuE\n",
                "%cd /content/YuE\n",
                "!pip install -q -e . || true\n",
                "\n",
                "print(\"✅ 필수 패키지 및 YuE 엔진 설치 완료!\")"
            ]
        },
        # 셀 4: 3단계 [모듈화된 프롬프트 및 가사 구성 영역]
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# @title [3단계] 노랫말 및 사운드 프롬프트 구성 (동적 조립 모듈)\n",
                "# @markdown 스토리북 스튜디오에서 생성된 노랫말과 장르 프롬프트가 자동으로 설정되어 있습니다.\n",
                "# @markdown 다른 곡으로 변경하려면 아래 값을 수정하신 후 3~5단계를 다시 실행하세요.\n",
                "import os\n",
                "\n",
                f"SONG_EPISODE = \"{episode_no}\"  # @param {{type:\"string\"}}\n",
                f"SONG_TITLE = \"{title}\"  # @param {{type:\"string\"}}\n",
                f"TARGET_FILENAME = \"{out_filename}\"  # @param {{type:\"string\"}}\n",
                "\n",
                "# 음악 사운드 스타일 태그\n",
                f"GENRE_PROMPT = \"{genre_prompt}\"\n",
                "\n",
                "# 완성된 노래 가사\n",
                f"LYRICS_CONTENT = \"\"\"{lyrics}\"\"\"\n",
                "\n",
                "# 추론용 파일 저장\n",
                "os.makedirs(\"/content/input\", exist_ok=True)\n",
                "with open(\"/content/input/genre.txt\", \"w\", encoding=\"utf-8\") as f:\n",
                "    f.write(GENRE_PROMPT.strip())\n",
                "with open(\"/content/input/lyrics.txt\", \"w\", encoding=\"utf-8\") as f:\n",
                "    f.write(LYRICS_CONTENT.strip())\n",
                "\n",
                f"print(f\"✅ 3단계: [{{SONG_EPISODE}}] {{SONG_TITLE}} 가사 및 프롬프트 준비 완료! (/content/input/)\")"
            ]
        },
        # 셀 5: 4단계 YuE 오디오 추론 및 렌더링
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# [4단계] YuE 오디오 추론 및 완곡 음원 렌더링 (실시간 로그 출력)\n",
                "import os\n",
                "import glob\n",
                "import shutil\n",
                "\n",
                "os.makedirs(\"/content/output\", exist_ok=True)\n",
                "print(f\"🎵 YuE 모델 로드 및 음원 추론을 시작합니다: [{SONG_EPISODE}] {SONG_TITLE}...\")\n",
                "\n",
                "# inference 디렉토리로 이동 후 추론 실행\n",
                "%cd /content/YuE/inference\n",
                "!python infer.py \\\n",
                "  --stage1_model m-a-p/YuE-s1-7B-anneal-en-cot \\\n",
                "  --stage2_model m-a-p/YuE-s2-1B-general \\\n",
                "  --genre_txt /content/input/genre.txt \\\n",
                "  --lyrics_txt /content/input/lyrics.txt \\\n",
                "  --run_n_segments 2 \\\n",
                "  --stage2_batch_size 4 \\\n",
                "  --output_dir /content/output \\\n",
                "  --cuda_idx 0 \\\n",
                "  --max_new_tokens 3000\n",
                "\n",
                "# 생성된 음원 탐색 및 최종 파일 통일\n",
                "audio_candidates = glob.glob(\"/content/output/**/*.mp3\", recursive=True) + glob.glob(\"/content/output/**/*.wav\", recursive=True)\n",
                "final_audio = os.path.join(\"/content\", TARGET_FILENAME)\n",
                "\n",
                "if audio_candidates:\n",
                "    src = audio_candidates[0]\n",
                "    if src.endswith(\".mp3\"):\n",
                "        shutil.copy(src, final_audio)\n",
                "    else:\n",
                "        !ffmpeg -y -i \"{src}\" \"{final_audio}\"\n",
                "    print(f\"🎉 최종 음원 준비 완료: {final_audio}\")\n",
                "else:\n",
                "    print(\"⚠️ output 디렉토리에 생성된 오디오 파일이 없습니다. 위 에러 로그를 확인해 주세요.\")"
            ]
        },
        # 셀 6: 5단계 미리듣기 및 자동 다운로드
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# [5단계] 완성된 테마곡 미리듣기 및 원클릭 자동 다운로드\n",
                "import os\n",
                "from IPython.display import Audio, display\n",
                "from google.colab import files\n",
                "\n",
                "TARGET_AUDIO = os.path.join(\"/content\", TARGET_FILENAME)\n",
                "\n",
                "if os.path.exists(TARGET_AUDIO):\n",
                "    print(\"=\" * 65)\n",
                "    print(f\"🎶 [{SONG_EPISODE}] {SONG_TITLE} 테마곡 재생\")\n",
                "    print(\"=\" * 65)\n",
                "    display(Audio(TARGET_AUDIO, autoplay=True))\n",
                "    \n",
                "    print(f\"\\n📥 대표님 PC의 [다운로드] 폴더로 음원({TARGET_FILENAME}) 자동 다운로드를 시작합니다...\")\n",
                "    files.download(TARGET_AUDIO)\n",
                "    print(f\"💡 다운로드받은 '{TARGET_FILENAME}' 파일을 스토리북 스튜디오의 [음원 등록]에 등록하세요!\")\n",
                "else:\n",
                "    print(\"⚠️ 음원 파일이 아직 생성되지 않았습니다. 4단계 셀의 출력을 확인해 주세요.\")"
            ]
        }
    ]

    return {
        "cells": cells,
        "metadata": {
            "accelerator": "GPU",
            "colab": {
                "gpuType": "T4",
                "provenance": []
            },
            "kernelspec": {
                "display_name": "Python 3",
                "name": "python3"
            },
            "language_info": {
                "name": "python"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 0
    }

def save_yue2_notebook_file(
    file_path: Path,
    episode_no: str = "제01화",
    title: str = "새벽 대청",
    genre_prompt: str = DEFAULT_GENRE_PROMPT,
    lyrics: str = "",
    book_title: str = "시화집"
) -> Path:
    """노트북 파일(.ipynb)을 지정된 경로에 UTF-8로 저장합니다."""
    data = build_yue2_notebook_dict(
        episode_no=episode_no,
        title=title,
        genre_prompt=genre_prompt,
        lyrics=lyrics,
        book_title=book_title
    )
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return file_path
