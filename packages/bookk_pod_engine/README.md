# 📕 `bookk_pod_engine` (POD 자가출판 & 300 DPI 인쇄 조판 엔진)

부크크(Bookk) 등 POD(Print-On-Demand) 독립출판을 위한 **판형·책등(Spine) 자동 계산, 300 DPI LANCZOS 업스케일링, A5/사륙판 내지·표지 PDF 생성**을 담당하는 독립 모듈입니다.

## 🚀 다른 프로젝트에서 바로 사용하기

```python
from packages.bookk_pod_engine import (
    calculate_spine_and_cover,
    inspect_images_directory,
    ensure_300dpi_image,
    BookkPDFBuilder,
)

# 1. 페이지 수와 용지에 따른 책등 두께(mm) 및 표지 전체 픽셀 규격 계산
spec = calculate_spine_and_cover(pages=100, paper_type="백색 모조지 100g", format_key="a5")
print(spec["spine_thickness_mm"], spec["cover_canvas_px"])

# 2. 저해상도 이미지를 300 DPI 출판 인쇄 규격(1748x2480px)으로 자동 보정
ensure_300dpi_image("input.jpg")

# 3. 300 DPI 부크크 인쇄용 내지/표지 PDF 빌드
builder = BookkPDFBuilder(format_key="a5", paper_type="white_100g")
builder.build_interior_pdf("output_interior.pdf")
```
