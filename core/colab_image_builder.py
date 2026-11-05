# -*- coding: utf-8 -*-
"""
core/colab_image_builder.py
Google Colab SDXL-Lightning 원클릭 고화질 삽화 생성 노트북 모듈
- 다른 프로젝트(시집, 동화책, 소설, 갤러리 등)에서도 재사용 가능한 모듈화된 엔진
- 1단계: GPU 점검 (T4 15~16GB VRAM)
- 2단계: 필수 라이브러리 초고속 설치 (diffusers, transformers, accelerate)
- 3단계: [동적 조립 모듈] 작품별 에피소드, 제목, 화풍, 서정 프롬프트 A/B, 해상도 설정
- 4단계: SDXL-Lightning 기반 4스텝 초고속 2가지 시안(A안, B안) 추론 및 렌더링
- 5단계: 결과 미리보기 및 원클릭 자동 2종 다운로드
"""
import re
import json
from pathlib import Path
from typing import Dict, Any, Optional

# 모든 화풍 공통 여백 및 담백한 종이 질감
COMMON_WHITE_PAPER_MARGIN = "peaceful empty space, soft natural lighting, textured white paper"

COMMON_NEGATIVE_PROMPT = (
    "text, typography, letters, words, hangul, korean characters, chinese characters, "
    "poem text, title, signature, stamp, red seal, artist seal, watermark, logo, "
    "picture frame, border lines, rectangular crop, 3d render, cgi, digital vector, "
    "photo montage, harsh lines, oversaturated colors, ugly, deformed, blurry"
)

DEFAULT_STYLE_PRESETS = {
    "watercolor": {
        "name": "맑은 수채화 (Transparent Watercolor)",
        "prompt_suffix": f"delicate Korean lyric watercolor painting, soft translucent washes, {COMMON_WHITE_PAPER_MARGIN}",
        "negative_prompt": COMMON_NEGATIVE_PROMPT
    },
    "ink_wash": {
        "name": "수묵 담채화 (Korean Ink Wash)",
        "prompt_suffix": f"traditional Korean sumuk ink and wash painting, expressive brushwork on hanji, {COMMON_WHITE_PAPER_MARGIN}",
        "negative_prompt": COMMON_NEGATIVE_PROMPT
    },
    "oil_painting": {
        "name": "서정 유화 (Lyric Oil Painting)",
        "prompt_suffix": f"warm lyric impressionist oil painting, soft gentle brushstrokes, {COMMON_WHITE_PAPER_MARGIN}",
        "negative_prompt": COMMON_NEGATIVE_PROMPT
    },
    "fairytale": {
        "name": "동화풍 파스텔 (Pastel Fairytale)",
        "prompt_suffix": f"heartwarming storybook illustration, soft colored pencil and pastel texture, {COMMON_WHITE_PAPER_MARGIN}",
        "negative_prompt": COMMON_NEGATIVE_PROMPT
    }
}

def build_sdxl_image_notebook_dict(
    episode_no: str = "제01화",
    title: str = "새벽 대청",
    base_prompt: str = "고향집 토방마루와 새벽 안개",
    style_key: str = "watercolor",
    custom_style_prompt: Optional[str] = None,
    book_title: str = "시화집",
    width: int = 768,
    height: int = 1024,
    num_steps: int = 4
) -> Dict[str, Any]:
    """
    작품 정보(에피소드, 제목, 프롬프트, 화풍 스타일)를 전달받아
    완전하게 조립된 Google Colab (.ipynb) 딕셔너리를 생성합니다.
    다른 프로젝트에서도 style_key, prompt, width/height를 유연하게 지정하여 호출 가능합니다.
    """
    clean_ep = re.sub(r'[^0-9]', '', episode_no).zfill(2) if episode_no else "01"
    clean_title = re.sub(r'[\s\\/*?:"<>|]', '_', title) if title else "삽화"
    
    file_a = f"{clean_ep}_{clean_title}_시안A.jpg"
    file_b = f"{clean_ep}_{clean_title}_시안B.jpg"

    preset = DEFAULT_STYLE_PRESETS.get(style_key, DEFAULT_STYLE_PRESETS["watercolor"])
    style_suffix = custom_style_prompt.strip() if custom_style_prompt else preset["prompt_suffix"]
    neg_prompt = preset["negative_prompt"]

    cleaned_base = base_prompt.strip() if base_prompt else "한국의 정겨운 옛 고향 정경"
    # A안: 담담한 서정적 여백과 은유 구도
    full_prompt_a = f"{cleaned_base}, tranquil poetic negative space, minimalist composition, {style_suffix}"
    # B안: 따스한 정경 디테일과 온기 있는 구도
    full_prompt_b = f"{cleaned_base}, warm nostalgic ambiance, intimate poetic harmony, rich atmospheric details, {style_suffix}"

    cells = [
        # 셀 1: 마크다운 개요
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                f"# 🎨 [{episode_no}] {title} — Colab SDXL 원클릭 서정 삽화 생성기\n",
                "\n",
                f"- **작품집/프로젝트**: 『{book_title}』\n",
                f"- **작품 정보**: [{episode_no}] 「{title}」\n",
                f"- **생성 규격**: 출판용 고해상도 ({width}x{height}, 300 DPI 대응) 2종 (시안 A, 시안 B)\n",
                "- **환경**: Google Colab 무료 T4 GPU (15GB VRAM)\n",
                "\n",
                "> 💡 **[초간단 원클릭 실행 안내]**\n",
                "> 상단 메뉴에서 **[런타임] → [모두 실행]**을 누르면 자동으로 패키지 설치부터 초고속 AI 렌더링, 그리고 브라우저로 **`" + file_a + "`, `" + file_b + "` 2가지 시안 자동 다운로드**까지 한 번에 완료됩니다.\n",
                "> 다운로드된 그림 중 마음에 드는 시안을 스토리북 스튜디오나 뷰어에 등록하시면 됩니다."
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
                "# [2단계] 초고속 렌더링 라이브러리 설치 (diffusers, transformers, accelerate, torchao)\n",
                "!pip install -q --upgrade diffusers transformers accelerate safetensors torchao\n",
                "print(\"✅ 필수 패키지 설치 완료!\")"
            ]
        },
        # 셀 4: 3단계 [모듈화된 프롬프트 설정 영역]
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# @title [3단계] 삽화 메타데이터 및 프롬프트 설정 (동적 조립 모듈)\n",
                "# @markdown 스토리북 스튜디오에서 생성된 작품 정보가 사전에 설정되어 있습니다.\n",
                "# @markdown 필요시 다른 프로젝트에 맞게 값을 변경하고 3~5단계를 다시 실행할 수 있습니다.\n",
                "import os\n",
                "\n",
                f"EPISODE_NO = \"{episode_no}\"  # @param {{type:\"string\"}}\n",
                f"WORK_TITLE = \"{title}\"  # @param {{type:\"string\"}}\n",
                f"FILE_A = \"{file_a}\"  # @param {{type:\"string\"}}\n",
                f"FILE_B = \"{file_b}\"  # @param {{type:\"string\"}}\n",
                f"IMAGE_WIDTH = {width}  # @param {{type:\"integer\"}}\n",
                f"IMAGE_HEIGHT = {height}  # @param {{type:\"integer\"}}\n",
                f"STEPS = {num_steps}  # @param {{type:\"integer\"}}\n",
                "\n",
                "# 1안 (서정적 여백 중심)\n",
                f"PROMPT_A = \"\"\"{full_prompt_a}\"\"\"\n",
                "\n",
                "# 2안 (따스한 정경 디테일 중심)\n",
                f"PROMPT_B = \"\"\"{full_prompt_b}\"\"\"\n",
                "\n",
                f"NEGATIVE_PROMPT = \"\"\"{neg_prompt}\"\"\"\n",
                "\n",
                "print(f\"✅ 3단계: [{EPISODE_NO}] {WORK_TITLE} 삽화 프롬프트 준비 완료!\")\n",
                "print(f\" - 시안 A: {FILE_A}\")\n",
                "print(f\" - 시안 B: {FILE_B}\")"
            ]
        },
        # 셀 5: 4단계 SDXL-Lightning 2가지 시안 초고속 생성
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# [4단계] SDXL-Lightning 파이프라인 로드 및 2가지 시안 렌더링 (생성 대기 필요)\n",
                "import torch\n",
                "from diffusers import StableDiffusionXLPipeline, UNet2DConditionModel, EulerDiscreteScheduler\n",
                "from huggingface_hub import hf_hub_download\n",
                "from safetensors.torch import load_file\n",
                "\n",
                "base_model = \"stabilityai/stable-diffusion-xl-base-1.0\"\n",
                "repo_lightning = \"ByteDance/SDXL-Lightning\"\n",
                "ckpt = f\"sdxl_lightning_{STEPS}step_unet.safetensors\"\n",
                "\n",
                "print(\"🎨 초고속 SDXL Lightning 엔진을 로드합니다...\")\n",
                "# 4스텝 고속 UNet 로드\n",
                "unet = UNet2DConditionModel.from_config(base_model, subfolder=\"unet\").to(\"cuda\", torch.float16)\n",
                "unet.load_state_dict(load_file(hf_hub_download(repo_lightning, ckpt), device=\"cuda\"))\n",
                "\n",
                "# 파이프라인 조립\n",
                "pipe = StableDiffusionXLPipeline.from_pretrained(\n",
                "    base_model,\n",
                "    unet=unet,\n",
                "    torch_dtype=torch.float16,\n",
                "    variant=\"fp16\"\n",
                ").to(\"cuda\")\n",
                "\n",
                "# Lightning 권장 스케줄러 설정\n",
                "pipe.scheduler = EulerDiscreteScheduler.from_config(pipe.scheduler.config, timestep_spacing=\"trailing\")\n",
                "\n",
                "os.makedirs(\"/content/output\", exist_ok=True)\n",
                "\n",
                "print(f\"\\n🖼️ [시안 A: 서정적 여백 중심] 렌더링 중...\")\n",
                "gen_a = torch.Generator(\"cuda\").manual_seed(42)\n",
                "img_a = pipe(\n",
                "    prompt=PROMPT_A,\n",
                "    negative_prompt=NEGATIVE_PROMPT,\n",
                "    num_inference_steps=STEPS,\n",
                "    guidance_scale=0.0,\n",
                "    width=IMAGE_WIDTH,\n",
                "    height=IMAGE_HEIGHT,\n",
                "    generator=gen_a\n",
                ").images[0]\n",
                "path_a = os.path.join(\"/content\", FILE_A)\n",
                "img_a.save(path_a, quality=95)\n",
                "print(f\"✓ 시안 A 저장 완료: {path_a}\")\n",
                "\n",
                "print(f\"\\n🖼️ [시안 B: 따스한 정경 디테일] 렌더링 중...\")\n",
                "gen_b = torch.Generator(\"cuda\").manual_seed(1004)\n",
                "img_b = pipe(\n",
                "    prompt=PROMPT_B,\n",
                "    negative_prompt=NEGATIVE_PROMPT,\n",
                "    num_inference_steps=STEPS,\n",
                "    guidance_scale=0.0,\n",
                "    width=IMAGE_WIDTH,\n",
                "    height=IMAGE_HEIGHT,\n",
                "    generator=gen_b\n",
                ").images[0]\n",
                "path_b = os.path.join(\"/content\", FILE_B)\n",
                "img_b.save(path_b, quality=95)\n",
                "print(f\"✓ 시안 B 저장 완료: {path_b}\")\n",
                "print(\"\\n🎉 2가지 삽화 시안 생성이 모두 성공적으로 완료되었습니다!\")"
            ]
        },
        # 셀 6: 5단계 미리보기 및 원클릭 자동 2종 다운로드
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# [5단계] 2가지 시안 나란히 미리보기 및 컴퓨터로 자동 다운로드\n",
                "import os\n",
                "from IPython.display import Image, display\n",
                "from google.colab import files\n",
                "\n",
                "path_a = os.path.join(\"/content\", FILE_A)\n",
                "path_b = os.path.join(\"/content\", FILE_B)\n",
                "\n",
                "print(\"=\" * 65)\n",
                "print(f\"🎨 [{EPISODE_NO}] {WORK_TITLE} — 2가지 삽화 시안 미리보기\")\n",
                "print(\"=\" * 65)\n",
                "\n",
                "if os.path.exists(path_a):\n",
                "    print(f\"\\n[시안 A: 서정적 여백 중심] ({FILE_A})\")\n",
                "    display(Image(path_a, width=380))\n",
                "\n",
                "if os.path.exists(path_b):\n",
                "    print(f\"\\n[시안 B: 따스한 정경 디테일] ({FILE_B})\")\n",
                "    display(Image(path_b, width=380))\n",
                "\n",
                "print(\"\\n📥 대표님 PC의 [다운로드] 폴더로 2가지 삽화 시안 자동 다운로드를 시작합니다...\")\n",
                "if os.path.exists(path_a):\n",
                "    files.download(path_a)\n",
                "if os.path.exists(path_b):\n",
                "    files.download(path_b)\n",
                "\n",
                "print(f\"💡 다운로드된 그림 중 마음에 드는 파일을 스토리북 스튜디오의 [그림 파일 교체] 또는 드롭존에 등록하세요!\")"
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

def save_sdxl_image_notebook_file(
    file_path: Path,
    episode_no: str = "제01화",
    title: str = "새벽 대청",
    base_prompt: str = "고향집 토방마루와 새벽 안개",
    style_key: str = "watercolor",
    custom_style_prompt: Optional[str] = None,
    book_title: str = "시화집",
    width: int = 768,
    height: int = 1024,
    num_steps: int = 4
) -> Path:
    """
    지정된 경로에 Colab 삽화 생성 노트북(.ipynb)을 UTF-8 JSON으로 저장합니다.
    다른 프로젝트에서도 독립 스크립트로 호출하여 파일 생성이 가능합니다.
    """
    data = build_sdxl_image_notebook_dict(
        episode_no=episode_no,
        title=title,
        base_prompt=base_prompt,
        style_key=style_key,
        custom_style_prompt=custom_style_prompt,
        book_title=book_title,
        width=width,
        height=height,
        num_steps=num_steps
    )
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return file_path
