import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
from core.config import MANUSCRIPT_FILE, TARGET_POEMS_COUNT

@dataclass
class PoemWork:
    episode_no: str          # 예: "제01화" 또는 "01"
    title: str               # 예: "새벽 대청"
    status: str              # 예: "완성 (승인 완료)"
    memory_anchor: str       # 예: "동지섣달 새벽, 대청마루에서..."
    image_file: str          # 예: "images/01_새벽대청.jpg"
    art_direction: str       # 예: "호롱불 아래 어머니의 뒷모습 (한국적 서정 수채화)"
    poem_body: str           # 시 본문 전체 텍스트
    audio_file: str = ""     # 통합/하위호환 음원 (예: "music/01_새벽대청.mp3")
    recite_file: str = ""    # 시인의 육성 낭송 음원 (예: "images/01_낭송.webm")
    music_file: str = ""     # 서정 노래/작곡 음원 (예: "music/01_음원.mp3")
    lyrics: str = ""         # 노랫말/가사 전체 텍스트
    chapter: str = ""        # 큰 주제별 묶음(부/챕터). 예: "제1부 흙과 솜꽃"
    author: str = ""         # 개별 시인/필자 (예: "어머니 김영희", "윤동주", 비워둘 시 대표 저자)
    layout_mode: str = "compact"  # 출판 조판 모드: "compact" (1페이지 쏙 맞춤) | "multi_page" (2페이지 연속 조판)
    part2_mode: str = "motif_symbol"  # 4P 모드 2부 좌측면: "motif_symbol" | "image" | "pure_blank" | "poem_text"
    image_file_2: str = ""        # 4P 모드 2부 좌측면 삽화 경로 (예: "images/01_새벽대청_후반.jpg")
    layout_config: Optional[dict] = None  # 신규 2P/4P 매트릭스 슬롯 조판 설정

class ManuscriptManager:
    def __init__(self, file_path: Optional[Path] = None):
        if file_path is None:
            try:
                from core.project_manager import project_manager
                self.file_path = project_manager.get_project_dir() / "작품집_원고.md"
            except Exception:
                from core.config import BASE_DIR
                self.file_path = BASE_DIR / "작품집_원고.md"
        else:
            self.file_path = file_path

    def load_works(self) -> List[PoemWork]:
        """원고 마크다운 파일을 파싱하여 PoemWork 객체 리스트로 반환"""
        if not self.file_path.exists():
            return []

        content = self.file_path.read_text(encoding="utf-8")
        works = []

        # 각 화(Episode) 블록 분리: ## [제XX화] 또는 ## [XX화] 패턴
        sections = re.split(r'\n(?=##\s*\[(?:제)?\d+화?\])', content)
        
        for section in sections:
            if not section.strip().startswith("##"):
                continue

            # 헤더 파싱: ## [제01화] 새벽 대청
            header_match = re.search(r'##\s*\[(?:제)?(\d+)화?\]\s*(.+)', section)
            if not header_match:
                continue

            ep_num = header_match.group(1).zfill(2)
            episode_no = f"제{ep_num}화"
            title = header_match.group(2).strip()

            # 메타데이터 추출 (개행을 건너뛰지 않도록 [ \t] 사용)
            status_match = re.search(r'-\s*\*\*상태\*\*:[ \t]*([^\r\n]+)', section)
            status = status_match.group(1).strip().replace("**", "") if status_match else "작성 중"

            chapter_match = re.search(r'-\s*\*\*부/주제\*\*:[ \t]*([^\r\n]+)', section)
            chapter = chapter_match.group(1).strip() if chapter_match else ""

            author_match = re.search(r'-\s*\*\*시인\*\*:[ \t]*([^\r\n]+)', section)
            author = author_match.group(1).strip() if author_match else ""

            memory_match = re.search(r'-\s*\*\*기억의 중심\*\*:[ \t]*([^\r\n]+)', section)
            memory_anchor = memory_match.group(1).strip() if memory_match else ""

            image_match = re.search(r'-\s*\*\*삽화 파일\*\*:[ \t]*`?([^`\r\n]+)`?', section)
            image_file = image_match.group(1).strip() if image_match else ""

            recite_match = re.search(r'-\s*\*\*낭송 음원\*\*:[ \t]*`?([^`\r\n]+)`?', section)
            recite_file = recite_match.group(1).strip() if recite_match else ""

            music_match = re.search(r'-\s*\*\*노래 음원\*\*:[ \t]*`?([^`\r\n]+)`?', section)
            music_file = music_match.group(1).strip() if music_match else ""

            audio_match = re.search(r'-\s*\*\*음원 파일\*\*:[ \t]*`?([^`\r\n]+)`?', section)
            audio_file = audio_match.group(1).strip() if audio_match else ""

            # 디스크 파일시스템 자동 감지: 낭송/노래 파일이 디스크에 존재하면 자동 연결
            proj_music_dir = self.file_path.parent / "music"
            if not recite_file and proj_music_dir.exists():
                for cand in [f"{ep_num}_낭송.wav", f"{ep_num}_낭송.webm", f"{int(ep_num)}_낭송.wav"]:
                    if (proj_music_dir / cand).exists():
                        recite_file = f"music/{cand}"
                        break
            if not music_file and proj_music_dir.exists():
                for cand in [f"{ep_num}_음원.mp3", f"{ep_num}_음원.m4a", f"{ep_num}_음원.wav", f"{int(ep_num)}_음원.mp3"]:
                    if (proj_music_dir / cand).exists():
                        music_file = f"music/{cand}"
                        break

            # 하위 호환 매핑: 기존 데이터에 audio_file만 있는 경우 자동 분기
            if audio_file:
                if ("낭송" in audio_file or audio_file.endswith(".webm")) and not recite_file:
                    recite_file = audio_file
                elif not music_file and not recite_file:
                    music_file = audio_file
            if not audio_file:
                audio_file = music_file or recite_file

            art_match = re.search(r'-\s*\*\*그림 방향\*\*:[ \t]*([^\r\n]+)', section)
            art_direction = art_match.group(1).strip() if art_match else ""

            # 방어 로직: 빈 줄 후 다음 행(- **삽화 파일** 등)이 잘못 매칭된 경우 원천 정제
            if memory_anchor.startswith("- **") or memory_anchor.startswith("###"):
                memory_anchor = ""
            if art_direction.startswith("- **") or art_direction.startswith("###"):
                art_direction = ""

            # 노랫말 추출: ### [노랫말] 이후 내용
            lyrics = ""
            lyrics_split = re.split(r'###\s*\[노랫말\]', section)
            if len(lyrics_split) > 1:
                lyrics = lyrics_split[1].split("\n---")[0].strip()

            # 시 본문 추출: ### [시 본문] 이후 내용 (노랫말 섹션이 있으면 그 전까지)
            poem_split = re.split(r'###\s*\[시 본문\]', section)
            if len(poem_split) > 1:
                body_candidate = poem_split[1]
                if "### [노랫말]" in body_candidate:
                    poem_body = body_candidate.split("### [노랫말]")[0].strip()
                else:
                    poem_body = body_candidate.split("\n---")[0].strip()
            else:
                poem_body = ""

            layout_match = re.search(r'-\s*\*\*조판 모드\*\*:[ \t]*([^\r\n]+)', section)
            layout_mode = layout_match.group(1).strip() if layout_match else "compact"

            part2_mode_match = re.search(r'-\s*\*\*2부 조판 방식\*\*:[ \t]*([^\r\n]+)', section)
            part2_mode = part2_mode_match.group(1).strip() if part2_mode_match else "motif_symbol"

            image_file_2_match = re.search(r'-\s*\*\*2부 삽화 파일\*\*:[ \t]*`?([^`\r\n]+)`?', section)
            image_file_2 = image_file_2_match.group(1).strip() if image_file_2_match else ""

            layout_config = None
            layout_cfg_match = re.search(r'-\s*\*\*조판 설정\*\*:[ \t]*`?({[^\r\n]+})`?', section)
            if layout_cfg_match:
                try:
                    import json
                    layout_config = json.loads(layout_cfg_match.group(1))
                except Exception:
                    layout_config = None

            works.append(PoemWork(
                episode_no=episode_no,
                title=title,
                status=status,
                memory_anchor=memory_anchor,
                image_file=image_file,
                art_direction=art_direction,
                poem_body=poem_body,
                audio_file=audio_file,
                recite_file=recite_file,
                music_file=music_file,
                lyrics=lyrics,
                chapter=chapter,
                author=author,
                layout_mode=layout_mode,
                part2_mode=part2_mode,
                image_file_2=image_file_2,
                layout_config=layout_config
            ))

        return works

    def get_completed_count(self) -> int:
        """완성된 작품 개수 카운트"""
        works = self.load_works()
        return sum(1 for w in works if "완성" in w.status)

    def get_work_by_episode(self, episode_no: str) -> Optional[PoemWork]:
        """회차 번호(예: '제01화', '01화', '01', 1)로 특정 작품 객체 반환"""
        clean_num = re.sub(r'[^0-9]', '', str(episode_no)).zfill(2) if re.search(r'\d+', str(episode_no)) else ""
        works = self.load_works()
        for w in works:
            w_clean = re.sub(r'[^0-9]', '', str(w.episode_no)).zfill(2) if re.search(r'\d+', str(w.episode_no)) else ""
            if w.episode_no == episode_no or (clean_num and clean_num == w_clean):
                return w
        return None

    def _write_works_to_file(self, works: List[PoemWork]) -> None:
        """작품 리스트를 받아 마크다운 파일로 영구 저장"""
        completed_count = sum(1 for w in works if "완성" in w.status)

        lines = [
            f"# 시화집 작품집 원고 (진행 현황: {completed_count} / {TARGET_POEMS_COUNT}편 완료)",
            "",
            "---",
            ""
        ]

        for w in works:
            lines.append(f"## [{w.episode_no}] {w.title}")
            lines.append(f"- **상태**: **{w.status}**")
            if getattr(w, 'chapter', ''):
                lines.append(f"- **부/주제**: {w.chapter}")
            if getattr(w, 'author', ''):
                lines.append(f"- **시인**: {w.author}")
            if getattr(w, 'layout_mode', '') and w.layout_mode != "compact":
                lines.append(f"- **조판 모드**: {w.layout_mode}")
            if getattr(w, 'part2_mode', '') and w.part2_mode != "motif_symbol":
                lines.append(f"- **2부 조판 방식**: {w.part2_mode}")
            if getattr(w, 'image_file_2', ''):
                lines.append(f"- **2부 삽화 파일**: `{w.image_file_2}`")
            if getattr(w, 'layout_config', None):
                import json
                lines.append(f"- **조판 설정**: `{json.dumps(w.layout_config, ensure_ascii=False)}`")
            lines.append(f"- **기억의 중심**: {w.memory_anchor}")
            lines.append(f"- **삽화 파일**: `{w.image_file}`")
            if getattr(w, 'recite_file', ''):
                lines.append(f"- **낭송 음원**: `{w.recite_file}`")
            if getattr(w, 'music_file', ''):
                lines.append(f"- **노래 음원**: `{w.music_file}`")
            if getattr(w, 'audio_file', '') and not getattr(w, 'recite_file', '') and not getattr(w, 'music_file', ''):
                lines.append(f"- **음원 파일**: `{w.audio_file}`")
            lines.append(f"- **그림 방향**: {w.art_direction}")
            lines.append("")
            lines.append("### [시 본문]")
            lines.append("")
            lines.append(w.poem_body)
            if getattr(w, 'lyrics', ''):
                lines.append("")
                lines.append("### [노랫말]")
                lines.append("")
                lines.append(w.lyrics)
            lines.append("")
            lines.append("---")
            lines.append("")

        self.file_path.write_text("\n".join(lines), encoding="utf-8")

    def save_work(self, work: PoemWork) -> None:
        """새 작품을 추가하거나 기존 작품을 수정하여 마크다운 파일 갱신"""
        works = self.load_works()
        existing_index = next((i for i, w in enumerate(works) if w.episode_no == work.episode_no), None)

        if existing_index is not None:
            # 기존 챕터 정보가 있고 새 입력에 없으면 기존 챕터 유지
            if not getattr(work, 'chapter', '') and getattr(works[existing_index], 'chapter', ''):
                work.chapter = works[existing_index].chapter
            works[existing_index] = work
        else:
            works.append(work)

        # 에피소드 번호 기준 정렬
        def _get_ep_num(w):
            m = re.search(r'\d+', w.episode_no)
            return int(m.group(0)) if m else 0

        works.sort(key=_get_ep_num)
        self._write_works_to_file(works)

    def get_next_episode_number(self) -> int:
        """다음 작성할 에피소드 번호 반환"""
        works = self.load_works()
        if not works:
            return 1
        nums = [int(re.search(r'\d+', w.episode_no).group(0)) for w in works if re.search(r'\d+', w.episode_no)]
        return max(nums) + 1 if nums else 1

    def delete_work(self, episode_no: str) -> bool:
        """지정된 에피소드 번호의 작품을 원고에서 삭제하고 마크다운 파일 갱신"""
        works = self.load_works()
        original_len = len(works)
        works = [w for w in works if w.episode_no != episode_no]
        if len(works) == original_len:
            return False

        def _get_ep_num(w):
            m = re.search(r'\d+', w.episode_no)
            return int(m.group(0)) if m else 0

        works.sort(key=_get_ep_num)
        self._write_works_to_file(works)
        return True

    def reorder_works(self, reordered_items: List[dict], auto_renumber: bool = True) -> List[PoemWork]:
        """
        목차 및 순서 편집 결과를 반영하여 전체 작품 순서를 재정렬하고 필요시 회차 번호를 자동 재부여.
        reordered_items: [{'episode_no': '제01화', 'chapter': '제1부: 흙과 솜꽃'}, ...]
        """
        works = self.load_works()
        work_map = {w.episode_no: w for w in works}

        new_works = []
        for item in reordered_items:
            orig_ep = item.get("episode_no")
            if orig_ep in work_map:
                w = work_map[orig_ep]
                w.chapter = item.get("chapter", "").strip()
                new_works.append(w)

        # 목록에 누락된 기존 작품이 있다면 뒤에 덧붙임
        for w in works:
            if w not in new_works:
                new_works.append(w)

        # 회차 번호 자동 재부여 (제01화, 제02화...)
        if auto_renumber:
            for idx, w in enumerate(new_works, 1):
                w.episode_no = f"제{str(idx).zfill(2)}화"

        self._write_works_to_file(new_works)
        return new_works

    def update_work_layout(
        self,
        episode_no: str,
        layout_mode: str,
        part2_mode: Optional[str] = None,
        image_file_2: Optional[str] = None
    ) -> bool:
        """특정 작품의 출판 조판 모드 ('compact' 또는 'multi_page') 및 4P 좌측면 연출 설정 갱신"""
        works = self.load_works()
        found = False
        for w in works:
            if w.episode_no == episode_no:
                w.layout_mode = layout_mode
                if part2_mode is not None:
                    w.part2_mode = part2_mode
                if image_file_2 is not None:
                    w.image_file_2 = image_file_2
                found = True
                break
        if found:
            self._write_works_to_file(works)
        return found

    def update_work_layout_config(self, episode_no: str, layout_config: dict) -> bool:
        """2P/4P 매트릭스 슬롯 조판 설정을 갱신하고 기존 layout_mode/part2_mode도 호환 동기화"""
        works = self.load_works()
        found = False
        target_num = re.sub(r'[^0-9]', '', str(episode_no)).zfill(2)

        for w in works:
            w_num = re.sub(r'[^0-9]', '', str(w.episode_no)).zfill(2)
            if w.episode_no == episode_no or (target_num and w_num == target_num):
                w.layout_config = layout_config
                page_count = layout_config.get("page_count", 2)
                if page_count == 4:
                    w.layout_mode = "multi_page"
                elif page_count == 1:
                    w.layout_mode = "single_page"
                else:
                    w.layout_mode = "compact"
                
                # 4P 모드일 때 3면/4면 기반 part2_mode 유추
                slots = layout_config.get("slots", [])
                if page_count == 4 and len(slots) >= 4:
                    slot3 = slots[2] if isinstance(slots[2], dict) else {"type": slots[2]}
                    if slot3.get("type") == "text":
                        w.part2_mode = "poem_text"
                    else:
                        img_cfg = layout_config.get("image_settings", {}).get("page_3", {})
                        mode = img_cfg.get("mode", "motif_symbol")
                        w.part2_mode = mode
                        if mode == "image" and img_cfg.get("file"):
                            w.image_file_2 = img_cfg.get("file")
                found = True
                break
        if found:
            self._write_works_to_file(works)
        return found


