# -*- coding: utf-8 -*-
"""
build_colab_notebook.py
제03화 마지막 상여 - Google Colab 원클릭 YuE2 음원 생성 노트북 (.ipynb) 수정본
- T4 GPU 호환 패키지 (einops, omegaconf, bitsandbytes 등) 명시적 설치
- YuE 패키지 정식 설치 (pip install -e .)
- inference 디렉토리 진입 후 명확한 추론 명령 실행 및 실시간 로그 출력
"""
import json
import sys
from pathlib import Path

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
NOTEBOOK_PATH = BASE_DIR / "마지막상여_YuE2_원클릭.ipynb"

cells = [
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "# 🎵 [제03화] 마지막 상여 — YuE 국악 민요풍 원클릭 음원 생성기 (Colab T4 최적화판)\n",
            "\n",
            "- **작품**: 『노을빛 기억』 제03화 「마지막 상여」\n",
            "- **장르**: 애절한 국악 민요조 크로스오버 발라드 (해금, 대금, 가야금, 장구, 북, 68 BPM 진양조~중모리)\n",
            "- **환경**: Google Colab T4 GPU (15GB VRAM)\n",
            "\n",
            "> 💡 **[실행 안내]**\n",
            "> 상단 메뉴에서 **[런타임] → [모두 실행]**을 누르면 자동으로 패키지 설치부터 모델 다운로드, 음원 생성, 그리고 브라우저로 **`03_마지막상여.mp3` 자동 다운로드**까지 완벽하게 진행됩니다."
        ]
    },
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
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# [3단계] 제03화 마지막 상여 — 국악 민요풍 노랫말 및 사운드 프롬프트 구성\n",
            "import os\n",
            "\n",
            "GENRE_PROMPT = (\n",
            "    \"Korean Traditional Folk Ballad, Mournful Elegy, Han, Gugak Crossover, \"\n",
            "    \"Haegeum, Daegum solo, Gayageum, Janggu, Deep Korean Buk, Soft Strings, Low Piano, \"\n",
            "    \"Slow 68 BPM, Joongmori rhythm, sorrowful traditional female vocal, heartbreaking\"\n",
            ")\n",
            "\n",
            "LYRICS_CONTENT = \"\"\"[Genre: Korean Traditional Folk Ballad, Mournful Elegy, Han, Gugak Crossover]\n",
            "[Instruments: Haegeum, Daegum, Gayageum, Janggu, Deep Korean Buk, Soft Strings]\n",
            "[Tempo: Slow, 68 BPM, Joongmori rhythm]\n",
            "[Mood: Heartbreaking, Tearful, Sorrowful, Poetic]\n",
            "\n",
            "[Intro]\n",
            "(구슬픈 대금 독주로 시작되어 빗소리와 함께 해금의 처연한 선율이 얹어진다. 장구의 느린 북편 소리가 가슴을 먹먹하게 두드린다.)\n",
            "\n",
            "[Verse 1]\n",
            "목화는 어느덧 전설이 되고\n",
            "모시올 풀던 날 아득하여라\n",
            "겨울엔 살 덥히는 무명베를 짜고\n",
            "여름엔 숨통 틔울 올을 고르며\n",
            "사철 우리 어머니 쉴 날 없었네\n",
            "\n",
            "사대가 모여 사는 종갓집 맏며느리\n",
            "환갑이 지나도록 층층시하라\n",
            "서방님 손목 잡고 마실 문턱조차\n",
            "한 번을 나선 적이 없던 사람아\n",
            "\n",
            "[Verse 2]\n",
            "전란의 포화 속에 뼈나 찾을까\n",
            "점쟁이 말대로 살아는 왔으나\n",
            "마당에 쏟아내던 기침 소리엔\n",
            "아직도 화약 내음 묻어 있었지\n",
            "\n",
            "산신령님 조왕님 감사하여라\n",
            "두 손 모아 눈물로 빌고 빌어도\n",
            "칠순의 문턱에서 숨이 꺾이어\n",
            "애비 노릇 그만두고 눈을 감았네\n",
            "\n",
            "[Chorus]\n",
            "오뉴월 장대비는 억수로 퍼붓는데\n",
            "장롱 속 오십 년 묵은 모시 수의\n",
            "고이 접은 슬픔을 몸에 두르고\n",
            "먼 길 떠나는 임을 배웅하누나\n",
            "골목길 굽이돌아 꽃상여 나가니\n",
            "빗물에 상여꽃이 녹아내리네\n",
            "\n",
            "[Bridge]\n",
            "(장구와 북소리가 중중모리로 고조되며, 해금이 애간장을 끊듯 솟구친다)\n",
            "어허- 넘차 달구야\n",
            "어허- 넘차 달구야\n",
            "어른 노릇 그 삶이 그리 버거워\n",
            "자기 어머니 등진 지 석 달 만에\n",
            "홀로 이 빗속을 떠나가시오\n",
            "\n",
            "[Chorus]\n",
            "오뉴월 장대비는 억수로 퍼붓는데\n",
            "장롱 속 오십 년 묵은 모시 수의\n",
            "고이 접은 슬픔을 몸에 두르고\n",
            "먼 길 떠나는 임을 배웅하누나\n",
            "골목길 굽이돌아 꽃상여 나가니\n",
            "빗물에 상여꽃이 녹아내리네\n",
            "\n",
            "[Outro]\n",
            "베틀 소리 끊긴 지 반백 년 세월\n",
            "달구 소리만 구슬프게 골목을 도네\n",
            "녹아내린 꽃잎 따라 길을 떠나는\n",
            "우리 마을의, 아…… 마지막 상여여라.\n",
            "(대금의 여운과 빗소리가 천천히 잦아들며 페이드아웃)\"\"\"\n",
            "\n",
            "# 프롬프트 및 가사 파일 저장\n",
            "os.makedirs(\"/content/input\", exist_ok=True)\n",
            "with open(\"/content/input/genre.txt\", \"w\", encoding=\"utf-8\") as f:\n",
            "    f.write(GENRE_PROMPT)\n",
            "with open(\"/content/input/lyrics.txt\", \"w\", encoding=\"utf-8\") as f:\n",
            "    f.write(LYRICS_CONTENT)\n",
            "\n",
            "print(\"✅ 3단계: 국악 가사 및 프롬프트 파일 저장 완료! (/content/input/)\")"
        ]
    },
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
            "\n",
            "print(\"🎵 YuE 모델 로드 및 음원 추론을 시작합니다. (모델 가중치 다운로드에 수 분이 소요될 수 있습니다)...\")\n",
            "\n",
            "# inference 디렉토리로 이동 후 직접 실행\n",
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
            "final_audio = \"/content/03_마지막상여.mp3\"\n",
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
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# [5단계] 완성된 국악 테마곡 미리듣기 및 원클릭 자동 다운로드\n",
            "import os\n",
            "from IPython.display import Audio, display\n",
            "from google.colab import files\n",
            "\n",
            "TARGET_AUDIO = \"/content/03_마지막상여.mp3\"\n",
            "\n",
            "if os.path.exists(TARGET_AUDIO):\n",
            "    print(\"=\" * 65)\n",
            "    print(\"🎶 [제03화] 마지막 상여 - 국악 민요풍 테마곡 재생\")\n",
            "    print(\"=\" * 65)\n",
            "    display(Audio(TARGET_AUDIO, autoplay=True))\n",
            "    \n",
            "    print(\"\\n📥 대표님 PC의 [다운로드] 폴더로 음원 자동 다운로드를 시작합니다...\")\n",
            "    files.download(TARGET_AUDIO)\n",
            "    print(\"💡 다운로드받은 '03_마지막상여.mp3' 파일을 프로젝트의 'images/' 폴더에 넣으시면 시화 갤러리에서 즉시 재생됩니다!\")\n",
            "else:\n",
            "    print(\"⚠️ 음원 파일이 아직 생성되지 않았습니다. 4단계 셀의 출력을 확인해 주세요.\")"
        ]
    }
]

notebook_data = {
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

with open(NOTEBOOK_PATH, "w", encoding="utf-8") as f:
    json.dump(notebook_data, f, ensure_ascii=False, indent=2)

print(f"🎉 코랩 노트북 업데이트 완료: {NOTEBOOK_PATH}")
