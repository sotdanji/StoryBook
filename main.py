import sys
import os

# Windows 콘솔 환경에서 한글 출력 깨짐 방지
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt

from core.config import TARGET_POEMS_COUNT
from core.manuscript import ManuscriptManager
from core.csv_builder import build_canva_csv
from core.book_spec import calculate_spine_and_cover, inspect_images
from core.interview import InterviewEngine
from core.bookk_pdf_builder import build_pdf_book

console = Console()

def export_pdf_cli():
    console.print("\n[bold cyan]📕 완제 시화집 전자책(PDF) 생성 중...[/bold cyan]")
    try:
        path = build_pdf_book()
        console.print(f"[bold green]✔ 성공:[/bold green] 완제본 시화집 PDF 파일이 생성되었습니다.")
        console.print(f"👉 파일 위치: [bold yellow]{path}[/bold yellow]")
        console.print(f"👉 파일 크기: {round(path.stat().st_size / 1024 / 1024, 2)} MB\n")
    except Exception as e:
        console.print(f"[bold red]오류 발생: {e}[/bold red]\n")

def print_banner():
    console.print(Panel.fit(
        "[bold magenta]📖 StoryBook Studio: 기억 기반 시화집 독립출판 툴킷[/bold magenta]\n"
        "[dim cyan]“가장 개인적인 기억이 가장 깊은 문학이자 예술이 된다.”[/dim cyan]\n"
        "[dim]부크크(Bookk) POD 출판 & Canva 대량 조판 자동화 파이프라인[/dim]",
        border_style="magenta"
    ))

def show_manuscript_status():
    manager = ManuscriptManager()
    works = manager.load_works()
    completed = manager.get_completed_count()

    console.print(f"\n[bold green]📊 전체 진행률: {completed} / {TARGET_POEMS_COUNT}편 완료 ({round(completed/TARGET_POEMS_COUNT*100, 1)}%)[/bold green]\n")

    if not works:
        console.print("[dim yellow]등록된 작품이 아직 없습니다.[/dim yellow]")
        return

    table = Table(title="[시화집 작품집 원고 목록]", border_style="cyan")
    table.add_column("회차", justify="center", style="bold yellow")
    table.add_column("제목", style="bold white")
    table.add_column("기억의 중심", style="dim")
    table.add_column("삽화 파일", style="cyan")
    table.add_column("상태", justify="center")

    for w in works:
        status_color = "green" if "완성" in w.status else "yellow"
        table.add_row(
            w.episode_no,
            w.title,
            w.memory_anchor[:30] + "..." if len(w.memory_anchor) > 30 else w.memory_anchor,
            w.image_file,
            f"[{status_color}]{w.status}[/{status_color}]"
        )

    console.print(table)

def export_csv():
    console.print("\n[bold cyan]📑 Canva 대량 제작용 CSV 데이터 내보내기[/bold cyan]")
    try:
        count, path = build_canva_csv()
        console.print(f"[bold green]✔ 성공:[/bold green] 총 [bold]{count}편[/bold]의 원고가 추출되었습니다.")
        console.print(f"👉 생성 파일: [bold yellow]{path}[/bold yellow]")
        console.print("[dim]Canva 템플릿의 '앱 > 대량 제작(Bulk Create)' 메뉴에서 위 CSV를 업로드하세요.[/dim]\n")
    except Exception as e:
        console.print(f"[bold red]오류 발생: {e}[/bold red]")

def check_book_specs():
    console.print("\n[bold cyan]📐 부크크 책등(세네카) 및 표지 펼침면 규격 계산기[/bold cyan]")
    pages_input = Prompt.ask("👉 전체 도서 페이지 수를 입력하세요 (권장: 80)", default="80")
    try:
        pages = int(pages_input)
    except ValueError:
        pages = 80

    spec = calculate_spine_and_cover(pages)

    table = Table(title=f"[A5 판형 {pages}p 기준 계산 결과]", border_style="green")
    table.add_column("항목", style="bold white")
    table.add_column("계산 수치 및 규격", style="bold yellow")

    table.add_row("도서 판형", "A5 (148 x 210 mm)")
    table.add_row("내지 용지", "백색모조 100g (장당 0.06mm)")
    table.add_row("책등(세네카) 두께", f"{spec['spine_thickness_mm']} mm")
    table.add_row("표지 펼침면 캔버스 크기", f"{spec['cover_canvas_width_mm']} x {spec['cover_canvas_height_mm']} mm (도련 3mm 포함)")
    table.add_row("안쪽 제본 안전 여백", f"{spec['inner_safe_margin_mm']} mm 이상 (필수)")
    table.add_row("바코드 영역", f"{spec['barcode_box']} (뒤표지 비워둘 곳)")

    console.print(table)

def inspect_image_specs():
    console.print("\n[bold cyan]🔍 삽화 인쇄 해상도(300 DPI) 일괄 검사[/bold cyan]")
    results = inspect_images()

    if not results:
        console.print("[dim yellow]검사할 이미지가 images/ 폴더에 없습니다.[/dim yellow]")
        return

    table = Table(title="[삽화 파일 규격 검사 결과]", border_style="yellow")
    table.add_column("파일명", style="bold white")
    table.add_column("픽셀 해상도", justify="center")
    table.add_column("DPI 메타데이터", justify="center")
    table.add_column("인쇄 적합성", justify="center")

    for r in results:
        status_color = "green" if r["is_ready"] else "red"
        table.add_row(
            r["filename"],
            r["resolution"],
            r["dpi"],
            f"[{status_color}]{r['status']}[/{status_color}]"
        )

    console.print(table)

def main():
    engine = InterviewEngine()

    while True:
        console.print()
        print_banner()
        console.print("\n[bold white]메뉴를 선택해 주세요:[/bold white]")
        console.print("  [1] ✍️  새로운 시화 창작 시작 (11단계 인터뷰)")
        console.print("  [2] 📚  작품집 원고 현황 및 목록 보기")
        console.print("  [3] 📑  Canva 대량 조판용 CSV 내보내기")
        console.print("  [4] 📕  완제 시화집 전자책(PDF) 즉시 생성")
        console.print("  [5] 📐  부크크 출판 규격 및 책등(세네카) 계산기")
        console.print("  [6] 🔍  삽화 인쇄 해상도(300 DPI) 일괄 검사")
        console.print("  [0] 🚪  종료")

        choice = Prompt.ask("\n👉 선택", choices=["1", "2", "3", "4", "5", "6", "0"], default="2")

        if choice == "1":
            engine.run_creation_session()
        elif choice == "2":
            show_manuscript_status()
        elif choice == "3":
            export_csv()
        elif choice == "4":
            export_pdf_cli()
        elif choice == "5":
            check_book_specs()
        elif choice == "6":
            inspect_image_specs()
        elif choice == "0":
            console.print("\n[dim cyan]StoryBook 툴킷을 종료합니다. 따뜻한 창작 여정을 응원합니다![/dim cyan]\n")
            sys.exit(0)

if __name__ == "__main__":
    main()
