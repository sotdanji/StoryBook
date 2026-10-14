import re
from typing import Dict, Any, Optional
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.markdown import Markdown

from core.config import get_gemini_api_key, DEFAULT_ART_STYLE
from core.manuscript import ManuscriptManager, PoemWork

console = Console()

class InterviewEngine:
    def __init__(self):
        self.manager = ManuscriptManager()
        self.api_key = get_gemini_api_key()

    def _generate_with_gemini(self, system_instruction: str, prompt: str) -> Optional[str]:
        """Google Gemini API를 호출하여 시안 또는 프롬프트를 생성"""
        if not self.api_key:
            return None
        try:
            client = genai.Client(api_key=self.api_key)
            active_model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
            response = client.models.generate_content(
                model=active_model,
                contents=prompt,
                config={
                    "system_instruction": system_instruction,
                    "temperature": 0.7,
                }
            )
            return response.text
        except Exception as e:
            console.print(f"[dim yellow]API 호출 안내: {e}[/dim yellow]")
            return None

    def run_creation_session(self) -> None:
        """11단계 표준 창작 인터뷰 세션 실행"""
        next_num = self.manager.get_next_episode_number()
        ep_str = f"제{str(next_num).zfill(2)}화"

        console.print()
        console.print(Panel(
            f"[bold cyan]🌸 {ep_str} 기억 기반 시화 창작 동반자 인터뷰 🌸[/bold cyan]\n\n"
            "완성된 글이 없어도 괜찮습니다. 단어 하나, 짧은 기억 조각에서 시작됩니다.\n"
            "당신의 소중한 순간을 온전한 당신의 언어로 빚어드리겠습니다.",
            border_style="cyan"
        ))

        # Step 2: 기억의 실마리 (단일 장면)
        console.print("\n[bold yellow][Step 1/6] 기억의 실마리 찾기[/bold yellow]")
        console.print("[dim]거창한 일대기 대신, 마음에 오래 고여 있는 '단 하나의 작은 순간'을 들려주세요.[/dim]")
        core_memory = Prompt.ask("👉 그 기억의 중심이 되는 시간, 장소, 혹은 인물은 무엇인가요?")

        # Step 3: 세부 감각 인터뷰
        console.print("\n[bold yellow][Step 2/6] 감각적 디테일 발견[/bold yellow]")
        actions_and_things = Prompt.ask("👉 그 순간 가장 또렷이 보이는 사물이나 행동, 풍경은 어떤 모습인가요?")
        spoken_words = Prompt.ask("👉 그때 들었던 말, 혹은 마음속으로 읊조렸던 말이 있다면 한 줄로 들려주세요 (없으면 엔터)")

        # 수집된 팩트 정리
        fact_summary = f"장소/시간/인물: {core_memory} | 행동/사물: {actions_and_things}"
        if spoken_words.strip():
            fact_summary += f" | 실제 말: \"{spoken_words}\""

        console.print("\n[bold green]🔒 사실 확인 (Fact Lock)[/bold green]")
        console.print(Panel(fact_summary, title="잠긴 사실들 (추측이나 왜곡 금지)", border_style="green"))

        # Step 4: 시안 생성
        console.print("\n[bold yellow][Step 3/6] 소재 구조화 및 시(詩) 창작[/bold yellow]")
        console.print("[dim]사실을 훼손하지 않고, 두 가지 시적 호흡의 시안(A/B)을 구성합니다...[/dim]\n")

        system_prompt = (
            "당신은 사용자의 실제 기억을 시로 빚어내는 창작 동반자입니다.\n"
            "규칙 1: 사용자가 말한 사실(장소, 사물, 행동, 말)만 사용하고 절대 없는 인물이나 사건을 날조하지 마세요.\n"
            "규칙 2: 상투적인 교훈이나 억지 감동(\"희망을 얻었다\", \"성장했다\")은 배제하세요.\n"
            "규칙 3: A안은 담담하고 절제된 장면 중심, B안은 깊은 여운과 은유 중심의 서로 다른 2개 시안을 제시하세요.\n"
            "각 시안은 제목과 본문으로 구성하고, 한국어 시의 행과 연을 자연스럽게 살려주세요."
        )

        user_content = (
            f"기억의 중심: {core_memory}\n"
            f"구체적 사물과 행동: {actions_and_things}\n"
            f"실제 한 말/들은 말: {spoken_words if spoken_words else '없음'}\n"
            "위 사실만을 바탕으로 A안과 B안 2가지 시를 작성해주세요."
        )

        generated_text = self._generate_with_gemini(system_prompt, user_content)

        if generated_text:
            console.print(Panel(Markdown(generated_text), title="AI 제안 시안 (A/B)", border_style="magenta"))
        else:
            console.print("[dim italic]API 키가 설정되지 않아 프롬프트 템플릿을 안내합니다.[/dim italic]")
            console.print(Panel(user_content, title="외부 AI(ChatGPT/Claude)에 전달할 프롬프트", border_style="magenta"))

        # 시 확정 입력
        console.print("\n[bold cyan]📝 최종 시 원고 확정[/bold cyan]")
        poem_title = Prompt.ask("👉 채택하실 시의 최종 제목을 입력해 주세요")
        console.print("👉 시 본문을 입력해 주세요. (입력 완료 시 빈 줄에서 'END' 입력 후 엔터):")
        poem_lines = []
        while True:
            line = input()
            if line.strip() == "END":
                break
            poem_lines.append(line)
        poem_body = "\n".join(poem_lines).strip()

        # Step 6~8: 그림 방향 결정
        console.print("\n[bold yellow][Step 4/6] 시각 앵커 및 그림 방향 카드[/bold yellow]")
        console.print(f"[dim]화풍: {DEFAULT_ART_STYLE} (전권 통일 규격)[/dim]")
        
        card_a_desc = f"{core_memory}에서 포착한 사물과 빛의 조화"
        card_b_desc = f"{actions_and_things}에 집중한 서정적 여백의 구도"
        
        console.print(f"  [1] 카드 A: {card_a_desc}")
        console.print(f"  [2] 카드 B: {card_b_desc}")
        console.print("  [3] 직접 지정")
        choice = Prompt.ask("👉 어느 방향 카드를 선택하시겠습니까?", choices=["1", "2", "3"], default="1")

        if choice == "1":
            selected_direction = f"{card_a_desc} ({DEFAULT_ART_STYLE})"
        elif choice == "2":
            selected_direction = f"{card_b_desc} ({DEFAULT_ART_STYLE})"
        else:
            selected_direction = Prompt.ask("👉 원하시는 그림 방향을 입력해주세요")

        # Step 9: 이미지 파일명 지정 및 프롬프트 안내
        clean_title = re.sub(r'[\s\\/*?:"<>|]', '', poem_title)
        image_filename = f"{str(next_num).zfill(2)}_{clean_title}.jpg"
        image_path = f"images/{image_filename}"

        img_prompt = (
            f"Delicate Korean lyric watercolor illustration of {core_memory}, {actions_and_things}, "
            f"warm natural lighting, soft translucent washes, peaceful empty space, textured white paper"
        )

        console.print("\n[bold yellow][Step 5/6] 삽화 프롬프트 및 파일 안내[/bold yellow]")
        console.print(Panel(
            f"[bold green]권장 이미지 파일 경로:[/bold green] `{image_path}`\n\n"
            f"[bold cyan]이미지 생성 AI 프롬프트 (Midjourney/DALL-E/Imagen):[/bold cyan]\n"
            f"[italic]{img_prompt}[/italic]",
            title="삽화 제작 가이드",
            border_style="yellow"
        ))

        # Step 11: 최종 검증 및 저장
        console.print("\n[bold yellow][Step 6/6] 최종 검증 및 아카이빙[/bold yellow]")
        console.print("  ✅ 사실 날조 없는 순수 기억 반영 여부")
        console.print("  ✅ 사용자의 고유한 목소리 보존 여부")
        console.print("  ✅ 억지 교훈 배제 여부")
        
        if Confirm.ask(f"\n👉 [{ep_str}] 「{poem_title}」을(를) 작품집 원고에 최종 등록하시겠습니까?"):
            work = PoemWork(
                episode_no=ep_str,
                title=poem_title,
                status="완성 (승인 완료)",
                memory_anchor=core_memory,
                image_file=image_path,
                art_direction=selected_direction,
                poem_body=poem_body
            )
            self.manager.save_work(work)
            console.print(f"\n[bold green]🎉 축하합니다! [{ep_str}] 「{poem_title}」이(가) '작품집_원고.md'에 성공적으로 저장되었습니다![/bold green]\n")
        else:
            console.print("[dim yellow]등록이 취소되었습니다.[/dim yellow]")
