import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Any, Dict
from core.config import MANUSCRIPT_FILE, TARGET_POEMS_COUNT

@dataclass
class PoemWork:
    episode_no: str          # 예: "제01화" 또는 "01"
    title: str               # 예: "새벽 대청"
    status: str              # 예: "완성 (승인 완료)"
    memory_anchor: str       # 예: "동지섣달 새벽, 대청마루에서..."
    image_file: str          # 예: "media/P-0001/illustration.jpg"
    art_direction: str       # 예: "호롱불 아래 어머니의 뒷모습 (한국적 서정 수채화)"
    poem_body: str           # 시 본문 전체 텍스트
    audio_file: str = ""     # 통합/하위호환 음원
    recite_file: str = ""    # 시인의 육성/TTS 낭송 음원
    music_file: str = ""     # 서정 노래/작곡 음원
    lyrics: str = ""         # 노랫말/가사 전체 텍스트
    chapter: str = ""        # 큰 주제별 묶음(부/챕터). 예: "제1부 흙과 솜꽃"
    author: str = ""         # 개별 시인/필자
    layout_mode: str = "compact"  # "compact" | "multi_page"
    part2_mode: str = "motif_symbol"  # "motif_symbol" | "image" | "pure_blank" | "poem_text"
    image_file_2: str = ""        # 4P 모드 2부 좌측면 삽화 경로
    layout_config: Optional[dict] = None  # 신규 2P/4P 매트릭스 슬롯 조판 설정
    piece_id: str = ""       # [신규] 고유 불변 ID (예: "P-0001")
    video_file: str = ""     # [신규] 16:9 비디오 상대 경로
    video_preview: str = ""  # [신규] 비디오 썸네일 경로
    voice_user_file: str = "" # [신규] 시인 육성 녹음
    voice_tts_file: str = ""  # [신규] AI TTS 낭송
    voice_suno_file: str = "" # [신규] SUNO 성우 낭송
    voice_bgm_file: str = ""  # [신규] BGM 결합 낭송

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

    def _get_project_id(self) -> str:
        return self.file_path.parent.name

    def load_works(self) -> List[PoemWork]:
        """
        [100% Turso DB 마스터 일원화]
        로컬 작품집_원고.md 파일 의존성을 완전히 제거하고,
        Turso DB(또는 마스터 DB)의 pieces 및 toc 테이블에서 직접 작품 목록을 로드합니다.
        """
        proj_id = self._get_project_id()

        try:
            from core.db_manager import db_manager
            # ⚡ 1. 단일 JOIN 쿼리로 TOC와 모든 Pieces를 0.05초 만에 초고속 로드 (N+1 쿼리 완전 제거)
            toc_pieces = db_manager.get_toc_with_pieces(proj_id)
            if toc_pieces:
                works = []
                for item in toc_pieces:
                    p = item["piece"]
                    recite_f = p.voice_tts_file or p.voice_user_file or p.voice_bgm_file
                    music_f = p.music_file
                    audio_f = music_f or recite_f

                    works.append(PoemWork(
                        episode_no=item["display_label"],
                        title=p.title,
                        status=p.status,
                        memory_anchor=p.memory_anchor,
                        image_file=p.image_file,
                        art_direction=p.art_direction,
                        poem_body=p.poem_body,
                        audio_file=audio_f,
                        recite_file=recite_f,
                        music_file=music_f,
                        lyrics=p.lyrics,
                        chapter=item["chapter"] or p.chapter_topic,
                        author=p.author,
                        layout_mode=p.layout_mode,
                        part2_mode=p.part2_mode,
                        image_file_2=p.image_file_2,
                        layout_config=p.layout_config,
                        piece_id=p.piece_id,
                        video_file=p.video_file_16x9,
                        video_preview=p.video_preview,
                        voice_user_file=p.voice_user_file,
                        voice_tts_file=p.voice_tts_file,
                        voice_suno_file=p.voice_suno_file,
                        voice_bgm_file=p.voice_bgm_file
                    ))
                return works

            # 폴백: TOC가 아직 없는 경우 pieces 목록에서 로드
            pieces = db_manager.list_pieces(proj_id)
            if pieces:
                works = []
                for idx, p in enumerate(pieces, start=1):
                    recite_f = p.voice_tts_file or p.voice_user_file or p.voice_bgm_file
                    music_f = p.music_file
                    audio_f = music_f or recite_f
                    works.append(PoemWork(
                        episode_no=f"제{idx:02d}화",
                        title=p.title,
                        status=p.status,
                        memory_anchor=p.memory_anchor,
                        image_file=p.image_file,
                        art_direction=p.art_direction,
                        poem_body=p.poem_body,
                        audio_file=audio_f,
                        recite_file=recite_f,
                        music_file=music_f,
                        lyrics=p.lyrics,
                        chapter=p.chapter_topic,
                        author=p.author,
                        layout_mode=p.layout_mode,
                        part2_mode=p.part2_mode,
                        image_file_2=p.image_file_2,
                        layout_config=p.layout_config,
                        piece_id=p.piece_id,
                        video_file=p.video_file_16x9,
                        video_preview=p.video_preview,
                        voice_user_file=p.voice_user_file,
                        voice_tts_file=p.voice_tts_file,
                        voice_suno_file=p.voice_suno_file,
                        voice_bgm_file=p.voice_bgm_file
                    ))
                return works
        except Exception:
            pass

        return []

    @staticmethod
    def parse_markdown_text(content: str) -> List[PoemWork]:
        """백업 ZIP 업로드(Import) 시 마크다운 원고 텍스트를 파싱하여 PoemWork 리스트로 반환"""
        works = []
        sections = re.split(r'\n(?=##\s*\[(?:제)?\d+화?\])', content)
        
        for section in sections:
            if not section.strip().startswith("##"):
                continue

            header_match = re.search(r'##\s*\[(?:제)?(\d+)화?\]\s*(.+)', section)
            if not header_match:
                continue

            ep_num = header_match.group(1).zfill(2)
            episode_no = f"제{ep_num}화"
            title = header_match.group(2).strip()

            pid_match = re.search(r'<!--\s*piece_id:\s*([A-Za-z0-9_-]+)\s*-->', section)
            piece_id = pid_match.group(1).strip() if pid_match else ""

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

            art_dir_match = re.search(r'-\s*\*\*그림 방향\*\*:[ \t]*([^\r\n]+)', section)
            art_direction = art_dir_match.group(1).strip() if art_dir_match else ""

            body_match = re.search(r'###\s*\[시\s*본문\]\s*\n(.*?)(?=\n###|\n##|\n---|\Z)', section, re.DOTALL)
            poem_body = body_match.group(1).strip() if body_match else ""

            lyrics_match = re.search(r'###\s*\[노랫말.*?\]\s*\n(.*?)(?=\n###|\n##|\n---|\Z)', section, re.DOTALL)
            lyrics = lyrics_match.group(1).strip() if lyrics_match else ""

            layout_mode_match = re.search(r'-\s*\*\*조판 모드\*\*:[ \t]*([^\r\n]+)', section)
            layout_mode = layout_mode_match.group(1).strip() if layout_mode_match else "compact"

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
                layout_config=layout_config,
                piece_id=piece_id
            ))

        return works

    def get_completed_count(self) -> int:
        """완성된 작품 개수 카운트"""
        works = self.load_works()
        return sum(1 for w in works if "완성" in w.status)

    def get_work_by_episode(self, episode_no: str) -> Optional[PoemWork]:
        """회차 번호(예: '제01화', '01화', '01', 1) 또는 piece_id(예: 'P-0001')로 특정 작품 객체 반환"""
        works = self.load_works()
        ep_str = str(episode_no).strip()
        # 1. piece_id 직접 조회
        for w in works:
            if getattr(w, "piece_id", "") and w.piece_id == ep_str:
                return w
        # 2. 회차 번호 조회
        clean_num = re.sub(r'[^0-9]', '', ep_str).zfill(2) if re.search(r'\d+', ep_str) else ""
        for w in works:
            w_clean = re.sub(r'[^0-9]', '', str(w.episode_no)).zfill(2) if re.search(r'\d+', str(w.episode_no)) else ""
            if w.episode_no == ep_str or (clean_num and clean_num == w_clean):
                return w
        return None

    def get_work(self, episode_no: str) -> Optional[PoemWork]:
        return self.get_work_by_episode(episode_no)

    def get_next_episode_number(self) -> int:
        """다음 신규 에피소드 회차 번호 계산"""
        works = self.load_works()
        if not works:
            return 1
        nums = [int(re.search(r'\d+', w.episode_no).group(0)) for w in works if re.search(r'\d+', w.episode_no)]
        return max(nums) + 1 if nums else 1

    def update_work_layout(
        self,
        episode_no: str,
        layout_mode: str,
        part2_mode: Optional[str] = None,
        image_file_2: Optional[str] = None
    ) -> bool:
        """특정 작품의 출판 조판 모드 ('compact' 또는 'multi_page') 및 4P 좌측면 연출 설정을 Turso DB에 갱신"""
        proj_id = self._get_project_id()
        work = self.get_work(episode_no)
        if not work:
            return False

        piece_id = getattr(work, "piece_id", "")
        if piece_id:
            try:
                from core.db_manager import db_manager
                p = db_manager.get_piece(proj_id, piece_id)
                if p:
                    p.layout_mode = layout_mode
                    if part2_mode is not None:
                        p.part2_mode = part2_mode
                    if image_file_2 is not None:
                        p.image_file_2 = image_file_2
                    db_manager.save_piece(p)
                    return True
            except Exception:
                pass
        return False

    def update_work_layout_config(
        self,
        episode_no: str,
        layout_config: dict,
        title: Optional[str] = None,
        poem_body: Optional[str] = None,
        status: Optional[str] = None
    ) -> bool:
        """조판 설정을 Turso DB 마스터에 영구 동기화 (로컬 중복 파일 쓰기 제거)"""
        proj_id = self._get_project_id()

        work = self.get_work(episode_no)
        if not work:
            return False

        piece_id = getattr(work, "piece_id", "")

        if piece_id:
            try:
                from core.db_manager import db_manager
                p = db_manager.get_piece(proj_id, piece_id)
                if p:
                    p.layout_config = layout_config
                    p.page_count = layout_config.get("page_count", p.page_count)
                    if p.page_count >= 4:
                        p.layout_mode = "multi_page"
                    if title is not None and title.strip():
                        p.title = title.strip()
                    if poem_body is not None:
                        p.poem_body = poem_body
                    if status is not None and status.strip():
                        p.status = status.strip()
                    db_manager.save_piece(p)
                    return True
            except Exception:
                pass
        return False

    def save_work(self, work: PoemWork) -> bool:
        """
        작품 저장 (100% Turso DB 마스터 일원화):
        1. piece_id가 없으면 DB 시퀀스 채번기(allocate_piece_id)를 호출하여 P-XXXX 자동 부여
        2. Turso DB(또는 로컬 SQLite)에 PieceData 영구 저장
        3. 목차(TOC)에 등록되어 있지 않으면 목차 맨 끝에 추가
        (평상시 로컬 작품집_원고.md 중복 파일 쓰기 제거 -> 온디맨드 ZIP 다운로드 시 즉석 생성)
        """
        proj_id = self._get_project_id()
        from core.db_manager import db_manager, PieceData

        # 1. piece_id 채번
        if not getattr(work, "piece_id", ""):
            old = self.get_work(work.episode_no)
            if old and getattr(old, "piece_id", ""):
                work.piece_id = old.piece_id
            else:
                work.piece_id = db_manager.allocate_piece_id(proj_id)

        # 2. PieceData 변환 및 DB 저장
        pdata = PieceData(
            piece_id=work.piece_id,
            project_id=proj_id,
            title=work.title,
            author=work.author or "임종훈",
            poem_body=work.poem_body,
            chapter_topic=work.chapter,
            memory_anchor=work.memory_anchor,
            art_direction=work.art_direction,
            status=work.status,
            image_file=work.image_file,
            image_file_2=work.image_file_2,
            recite_primary_type="user" if getattr(work, "voice_user_file", "") else "ai_tts",
            voice_user_file=getattr(work, "voice_user_file", ""),
            voice_tts_file=getattr(work, "voice_tts_file", "") or work.recite_file or work.audio_file,
            voice_suno_file=getattr(work, "voice_suno_file", ""),
            voice_bgm_file=getattr(work, "voice_bgm_file", ""),
            music_file=work.music_file,
            lyrics=work.lyrics,
            video_file_16x9=getattr(work, "video_file", ""),
            video_preview=getattr(work, "video_preview", ""),
            layout_mode=work.layout_mode,
            page_count=getattr(work, "layout_config", {}).get("page_count", 2) if getattr(work, "layout_config", None) else 2,
            part2_mode=work.part2_mode,
            layout_config=work.layout_config or {}
        )
        db_manager.save_piece(pdata)

        # 3. 목차 등록 확인
        toc = db_manager.get_toc(proj_id)
        if not any(item.piece_id == work.piece_id for item in toc):
            new_toc = [{"piece_id": item.piece_id, "chapter": item.chapter} for item in toc]
            new_toc.append({"piece_id": work.piece_id, "chapter": work.chapter})
            db_manager.set_toc(proj_id, new_toc)

        return True

    def delete_work(self, episode_no_or_piece_id: str) -> bool:
        """작품 삭제 (영구 결번 처리, 목차에서 제거 및 R2 고아 미디어 정리)"""
        proj_id = self._get_project_id()
        work = self.get_work(episode_no_or_piece_id)
        if not work:
            return False
        piece_id = getattr(work, "piece_id", "")
        if piece_id:
            from core.db_manager import db_manager
            db_manager.delete_piece(proj_id, piece_id)
        # R2 고아 미디어 파일(삽화, 음원) 정리
        try:
            from core.r2_storage import r2_storage
            for media_f in (work.image_file, getattr(work, "image_file_2", ""), getattr(work, "recite_file", ""), getattr(work, "music_file", "")):
                if media_f and not media_f.startswith("http"):
                    r2_storage.delete_file(f"{proj_id}/{media_f.lstrip('./')}")
        except Exception:
            pass
        return True

    def reorder_works(self, items: Any, auto_renumber: bool = True) -> List[PoemWork]:
        """목차 순서 재정렬 및 각 시의 부(챕터) 일괄 갱신 (100% Turso DB 일원화)"""
        proj_id = self._get_project_id()
        from core.db_manager import db_manager
        
        toc_items = []
        if isinstance(items, list):
            for it in items:
                if isinstance(it, str):
                    toc_items.append({
                        "piece_id": it,
                        "chapter": ""
                    })
                elif isinstance(it, dict):
                    ep = it.get("piece_id") or it.get("episode_no", "")
                    w = self.get_work(ep)
                    ch = it.get("chapter", "")
                    if w:
                        if ch is not None:
                            w.chapter = ch
                        pid = getattr(w, "piece_id", "") or ep
                        toc_items.append({
                            "piece_id": pid,
                            "chapter": ch or getattr(w, "chapter", "")
                        })
        
        if toc_items:
            db_manager.set_toc(proj_id, toc_items)

        return self.load_works()

    def render_markdown_text(self, works: Optional[List[PoemWork]] = None) -> str:
        """
        [온디맨드 원고 생성기]
        백업 ZIP 다운로드 등 사용자가 파일을 요청할 때만 Turso DB 데이터로 `작품집_원고.md` 전문을 즉석 조립합니다.
        """
        if works is None:
            works = self.load_works()
        completed_count = sum(1 for w in works if "완성" in w.status)
        target_cnt = TARGET_POEMS_COUNT
        book_title = "시화집 작품집"
        meta_quote_block = []

        proj_id = self._get_project_id()
        try:
            from core.db_manager import db_manager
            pdata = db_manager.get_project_meta(proj_id)
            if pdata:
                book_title = pdata.get("name", book_title)
                target_cnt = pdata.get("target_count", target_cnt)
                author_label = "지은이" if pdata.get("author_type", "single") == "single" else "엮은이"
                meta_quote_block = [
                    f"> **{author_label}**: {pdata.get('author', '')}  ",
                    f"> **부제**: {pdata.get('subtitle', '')}  ",
                    f"> **기획**: {pdata.get('description', '')}  ",
                    ""
                ]
        except Exception:
            pass

        lines = [
            f"# {book_title} 원고 (진행 현황: {completed_count} / {target_cnt}편 완료)",
            "",
            *meta_quote_block,
            "---",
            ""
        ]

        for w in works:
            lines.append(f"## [{w.episode_no}] {w.title}")
            if getattr(w, "piece_id", ""):
                lines.append(f"<!-- piece_id: {w.piece_id} -->")
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
            if getattr(w, 'audio_file', '') and w.audio_file != getattr(w, 'recite_file', '') and w.audio_file != getattr(w, 'music_file', ''):
                lines.append(f"- **음원 파일**: `{w.audio_file}`")
            if getattr(w, 'art_direction', ''):
                lines.append(f"- **그림 방향**: {w.art_direction}")
            lines.append("")
            lines.append("### [시 본문]")
            lines.append("")
            lines.append(w.poem_body)
            lines.append("")
            if getattr(w, 'lyrics', ''):
                lines.append("### [노랫말 / 작곡 가사]")
                lines.append("")
                lines.append(w.lyrics)
                lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    def _write_works_to_file(self, works: List[PoemWork], target_path: Optional[Path] = None) -> None:
        """온디맨드 내보내기 시 지정된 경로에 마크다운 원고 파일 기록"""
        out_path = target_path or self.file_path
        try:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(self.render_markdown_text(works), encoding="utf-8")
        except Exception:
            pass
