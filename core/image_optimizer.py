import io
from pathlib import Path
from typing import Union, Tuple, Dict, Any, Optional
from PIL import Image, ImageDraw, ImageFilter

# A5 출판 규격 (148 x 210 mm) 300 DPI 환산 픽셀: 가로 1748 px, 세로 2480 px
A5_PRINT_WIDTH_300DPI = 1748
A5_PRINT_HEIGHT_300DPI = 2480

def apply_watercolor_edge_fade(image: Image.Image, margin_ratio: float = 0.12) -> Image.Image:
    """
    이미지 사방 가장자리를 순백색(#FFFFFF) 종이 배경으로 경계선 없이 완벽하게 스며들도록
    출판 표준 서정 비네팅(Smoothstep Vignette) 마스크를 적용합니다.
    - 외곽 4~5% 영역: 수학적으로 100% 완전한 순백색(#FFFFFF)으로 고정하여 사각 칼선/테두리 원천 제거
    - 외곽 4~14% 영역: 부드러운 에르미트 S-커브(Smoothstep)로 종이에 물감이 번지는 듯한 무경계 페이드아웃
    - 인공지능 워터마크(pollinations.ai 등) 및 직사각형 프레임 100% 완전 차단
    """
    img_rgb = image.convert("RGB")
    w, h = img_rgb.size

    try:
        import numpy as np

        # 2D 좌표 그리드 생성
        x = np.linspace(0.0, 1.0, w, dtype=np.float32)
        y = np.linspace(0.0, 1.0, h, dtype=np.float32)
        xx, yy = np.meshgrid(x, y)

        # 가장자리로부터의 정규화된 거리 계산 (0.0 ~ 0.5)
        dist_x = np.minimum(xx, 1.0 - xx)
        dist_y = np.minimum(yy, 1.0 - yy)

        # 마진 파라미터 (외곽 4%는 무조건 100% 순백, 14%까지 부드럽게 번짐)
        zero_margin = 0.04
        fade_margin = max(margin_ratio, 0.13)

        # 3차 에르미트 보간 S-커브 (부드러운 물감 번짐 연출)
        t_x = np.clip((dist_x - zero_margin) / (fade_margin - zero_margin), 0.0, 1.0)
        mask_x = t_x * t_x * (3.0 - 2.0 * t_x)

        t_y = np.clip((dist_y - zero_margin) / (fade_margin - zero_margin), 0.0, 1.0)
        mask_y = t_y * t_y * (3.0 - 2.0 * t_y)

        # 사방 및 네 모서리 자연스러운 타원형 감쇄 결합
        mask = mask_x * mask_y

        # 우하단 워터마크 영역 집중 제거 가드: 우측 및 하단 모서리 추가 소프트 페이드
        corner_dist = np.sqrt(np.square(1.0 - xx) + np.square(1.0 - yy))
        # 우하단 모서리 부근(워터마크 위치) 감쇄 보조
        br_fade = np.clip(corner_dist / 0.25, 0.0, 1.0)
        mask = mask * (br_fade * br_fade * (3.0 - 2.0 * br_fade))

        mask_u8 = (mask * 255.0).astype(np.uint8)
        mask_img = Image.fromarray(mask_u8, mode="L")

        # 부드러운 가우시안 블러를 미세하게 입혀 디지털 계단 현상 완벽 방지
        mask_img = mask_img.filter(ImageFilter.GaussianBlur(radius=max(2.0, min(w, h) * 0.005)))

        white_bg = Image.new("RGB", (w, h), (255, 255, 255))
        return Image.composite(img_rgb, white_bg, mask_img)

    except Exception:
        # Fallback: 순수 PIL 방식
        white_bg = Image.new("RGB", (w, h), (255, 255, 255))
        margin_x = int(w * 0.12)
        margin_y = int(h * 0.12)

        mask = Image.new("L", (w, h), 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle(
            [margin_x, margin_y, w - margin_x, h - margin_y],
            radius=int(min(margin_x, margin_y) * 1.8),
            fill=255
        )
        blur_radius = max(margin_x, margin_y) * 0.8
        mask = mask.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        return Image.composite(img_rgb, white_bg, mask)

def ensure_300dpi_image(
    image_input: Union[Path, str, bytes, Image.Image],
    output_path: Optional[Union[Path, str]] = None,
    target_width: int = A5_PRINT_WIDTH_300DPI,
    target_height: int = A5_PRINT_HEIGHT_300DPI,
    quality: int = 95,
    apply_edge_fade: bool = True
) -> Dict[str, Any]:
    """
    삽화 해상도 및 메타데이터를 검사하여 300 DPI 미만이거나 크기가 작을 경우,
    출판용 고품질 LANCZOS 알고리즘으로 업스케일 및 dpi=(300, 300)을 자동 주입하여 저장합니다.
    """
    # 1. Image 객체 로드
    opened_internally = False
    if isinstance(image_input, Image.Image):
        img = image_input
    elif isinstance(image_input, (bytes, bytearray)):
        img = Image.open(io.BytesIO(image_input))
        opened_internally = True
    elif isinstance(image_input, (str, Path)):
        img_path = Path(image_input)
        if not img_path.exists():
            raise FileNotFoundError(f"이미지 파일을 찾을 수 없습니다: {img_path}")
        img = Image.open(img_path)
        opened_internally = True
        if output_path is None:
            output_path = img_path
    else:
        raise ValueError("지원하지 않는 이미지 입력 형태입니다.")

    try:
        # RGBA 또는 P 모드(팔레트)일 경우 RGB로 안전 변환 (JPEG 저장 호환성)
        if img.mode in ("RGBA", "LA", "P"):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode in ("RGBA", "LA"):
                bg.paste(img, mask=img.split()[-1])
            else:
                bg.paste(img.convert("RGBA"))
            img_processed = bg
        elif img.mode != "RGB":
            img_processed = img.convert("RGB")
        else:
            img_processed = img.copy()

        orig_w, orig_h = img_processed.size
        orig_dpi = img.info.get("dpi", (72.0, 72.0))
        orig_dpi_val = round(orig_dpi[0]) if isinstance(orig_dpi, tuple) else 72

        # 300 DPI 충족 여부 검사
        needs_resolution_boost = (orig_w < 1500 or orig_h < 1500)
        needs_dpi_metadata = (orig_dpi_val < 300)
        was_enhanced = False

        final_img = img_processed

        # [A5 세로 판형 보장] 원본 비율을 유지하며 타겟 영역(1748 x 2480 px)을 가득 채우도록 스케일 계산 후 중앙 크롭
        scale = max(target_width / orig_w, target_height / orig_h)
        new_w = int(round(orig_w * scale))
        new_h = int(round(orig_h * scale))

        # 고품질 LANCZOS 안티앨리어싱 리샘플링
        resized_img = img_processed.resize((new_w, new_h), Image.Resampling.LANCZOS)
        was_enhanced = True

        # 가로로 긴 이미지가 들어와도 세로 판형에 맞게 중앙 서정 정물을 중심으로 깔끔하게 크롭
        left = max(0, (new_w - target_width) // 2)
        top = max(0, (new_h - target_height) // 2)
        final_img = resized_img.crop((left, top, left + target_width, top + target_height))

        out_w, out_h = final_img.size

        # 서정 수채화 가장자리 10~14% 순백 페더링 블러 마스크 적용 (직사각형 테두리 제거 & 워터마크 마스킹)
        if apply_edge_fade:
            try:
                final_img = apply_watercolor_edge_fade(final_img, margin_ratio=0.12)
            except Exception as fade_err:
                print(f"[가장자리 블러 마스킹 건너뜀]: {fade_err}")

        # 저장 대상 경로 결정
        if output_path is None:
            raise ValueError("저장할 output_path가 지정되지 않았습니다.")
        
        save_path = Path(output_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)

        # 300 DPI 메타데이터 및 고화질 압축률(95)로 저장
        final_img.save(
            save_path,
            format="JPEG",
            dpi=(300, 300),
            quality=quality,
            subsampling=0  # 색상 서브샘플링 없이 최고 화질 유지
        )

        return {
            "success": True,
            "path": str(save_path),
            "was_enhanced": was_enhanced,
            "original_resolution": f"{orig_w} x {orig_h} px",
            "original_dpi": f"{orig_dpi_val} DPI",
            "final_resolution": f"{out_w} x {out_h} px",
            "final_dpi": "300 DPI",
            "message": f"300 DPI 자동 보정 완료 ({orig_w}x{orig_h} @ {orig_dpi_val}DPI -> {out_w}x{out_h} @ 300DPI)"
            if was_enhanced else "이미 300 DPI 규격을 완벽히 충족합니다."
        }
    finally:
        if opened_internally:
            img.close()
