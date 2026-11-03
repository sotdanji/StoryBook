import json
import re
import shutil
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from core.config import BASE_DIR, TARGET_POEMS_COUNT
from core.manuscript import ManuscriptManager

PROJECTS_DIR = BASE_DIR / "projects"
ACTIVE_PROJECT_FILE = BASE_DIR / ".active_project"

@dataclass
class ProjectInfo:
    id: str                  # 영문/숫자 고유 식별자 (폴더명)
    name: str                # 시집 제목 (예: "기억이 머무는 자리")
    subtitle: str            # 시집 부제 (예: "삶의 궤적을 빚어낸 서정 시화집")
    author: str              # 시인/지은이 (예: "기억의 작가")
    target_count: int        # 목표 시 편수 (기본 35)
    description: str         # 시집 기획 의도 및 설명
    book_type: str = "illustrated" # "illustrated" (서정 시화집) | "standard" (일반 시집)
    author_type: str = "single"    # "single" (개인 시집) | "collab" (공동/가족 시집)
    owner_id: str = ""       # 회원 계정 고유 ID (Supabase Auth UID)
    owner_email: str = ""    # 회원 이메일 (소유자 확인용)
    prologue: str = ""       # 시인의 말 / 서문 (Prologue)
    epilogue: str = ""       # 맺음말 / 에필로그 (Epilogue)
    back_cover_blurb: str = "" # 책 뒷표지 감성 소개/추천 카피 (Blurb)
    cover_image: str = ""    # 앞표지 대표 삽화 파일 (예: images/01_새벽대청.jpg)
    publisher: str = "부크크 (Bookk) 자가출판" # 펴낸곳
    published_date: str = "" # 발행일 (예: 2026년 10월)
    price: str = "13,000원"  # 정가
    isbn: str = ""           # ISBN (선택 사항)
    created_at: str = ""
    updated_at: str = ""


class ProjectManager:
    def __init__(self, projects_dir: Path = PROJECTS_DIR):
        self.projects_dir = projects_dir
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_default_project()

    def _ensure_default_project(self):
        """프로젝트 폴더가 비어있을 경우에만 기본 템플릿 프로젝트 생성"""
        existing_dirs = [p for p in self.projects_dir.iterdir() if p.is_dir()]
        
        # 이미 프로젝트가 하나라도 있으면 새로 만들지 않음
        if existing_dirs:
            if not ACTIVE_PROJECT_FILE.exists() or not (self.projects_dir / ACTIVE_PROJECT_FILE.read_text(encoding="utf-8").strip()).exists():
                self.set_active_project_id(existing_dirs[0].name)
            return

        # 프로젝트가 아예 없는 경우: 깨끗한 기본 템플릿 시집 생성
        default_dir = self.projects_dir / "노을빛_기억"
        default_dir.mkdir(parents=True, exist_ok=True)
        (default_dir / "images").mkdir(parents=True, exist_ok=True)

        meta_file = default_dir / "project.json"
        default_meta = ProjectInfo(
            id="노을빛_기억",
            name="노을빛 기억",
            subtitle="황혼과 유년의 서정 시화집",
            author="김서정 시인",
            target_count=35,
            description="고향 마을의 저녁 노을과 유년기 따스한 추억들",
            book_type="illustrated",
            created_at=datetime.now().strftime("%Y-%m-%d"),
            updated_at=datetime.now().strftime("%Y-%m-%d")
        )
        meta_file.write_text(json.dumps(asdict(default_meta), ensure_ascii=False, indent=2), encoding="utf-8")

        # 원고 초기화
        manuscript_file = default_dir / "작품집_원고.md"
        manuscript_file.write_text(
            f"# {default_meta.name} 원고 (진행 현황: 0 / {default_meta.target_count}편 완료)\n\n"
            f"> **지은이**: {default_meta.author}  \n"
            f"> **부제**: {default_meta.subtitle}  \n"
            f"> **기획**: {default_meta.description}  \n\n---\n",
            encoding="utf-8"
        )

        self.set_active_project_id("노을빛_기억")

    def get_active_project_id(self) -> str:
        if ACTIVE_PROJECT_FILE.exists():
            active_id = ACTIVE_PROJECT_FILE.read_text(encoding="utf-8").strip()
            if (self.projects_dir / active_id).exists():
                return active_id
        
        # 없으면 첫 번째 프로젝트 폴더 사용
        existing = [p.name for p in self.projects_dir.iterdir() if p.is_dir()]
        if existing:
            self.set_active_project_id(existing[0])
            return existing[0]
            
        self._ensure_default_project()
        return "노을빛_기억"

    def set_active_project_id(self, project_id: str):
        target_dir = self.projects_dir / project_id
        if not target_dir.exists():
            raise ValueError(f"존재하지 않는 시집 프로젝트입니다: {project_id}")
        ACTIVE_PROJECT_FILE.write_text(project_id, encoding="utf-8")

    def get_project_dir(self, project_id: Optional[str] = None) -> Path:
        pid = project_id or self.get_active_project_id()
        return self.projects_dir / pid

    def get_project_info(self, project_id: Optional[str] = None) -> ProjectInfo:
        pdir = self.get_project_dir(project_id)
        meta_file = pdir / "project.json"
        if meta_file.exists():
            data = json.loads(meta_file.read_text(encoding="utf-8"))
            return ProjectInfo(
                id=data.get("id", pdir.name),
                name=data.get("name", pdir.name),
                subtitle=data.get("subtitle", "서정 시화집"),
                author=data.get("author", "기억의 작가"),
                target_count=data.get("target_count", 35),
                description=data.get("description", ""),
                book_type=data.get("book_type", "illustrated"),
                author_type=data.get("author_type", "single"),
                owner_id=data.get("owner_id", ""),
                owner_email=data.get("owner_email", ""),
                prologue=data.get("prologue", ""),
                epilogue=data.get("epilogue", ""),
                back_cover_blurb=data.get("back_cover_blurb", ""),
                cover_image=data.get("cover_image", ""),
                publisher=data.get("publisher", "부크크 (Bookk) 자가출판"),
                published_date=data.get("published_date", datetime.now().strftime("%Y년 %m월")),
                price=data.get("price", "13,000원"),
                isbn=data.get("isbn", ""),
                created_at=data.get("created_at", datetime.now().strftime("%Y-%m-%d")),
                updated_at=data.get("updated_at", datetime.now().strftime("%Y-%m-%d"))
            )
        
        # 메타 파일이 없을 경우 기본값 생성
        pid = pdir.name
        return ProjectInfo(
            id=pid,
            name=pid,
            subtitle="서정 시화집",
            author="작가",
            target_count=35,
            description="",
            owner_id="",
            owner_email="",
            prologue="",
            epilogue="",
            back_cover_blurb="",
            cover_image="",
            publisher="부크크 (Bookk) 자가출판",
            published_date=datetime.now().strftime("%Y년 %m월"),
            price="13,000원",
            isbn="",
            created_at=datetime.now().strftime("%Y-%m-%d"),
            updated_at=datetime.now().strftime("%Y-%m-%d")
        )

    def claim_project(self, project_id: str, user_id: str, user_email: str) -> bool:
        """
        게스트나 미할당 상태의 시집 프로젝트를 로그인한 회원의 계정으로 안전하게 귀속합니다.
        """
        try:
            pdir = self.get_project_dir(project_id)
            meta_file = pdir / "project.json"
            if not meta_file.exists():
                return False

            info = self.get_project_info(project_id)
            # 이미 다른 사람이 소유한 프로젝트가 아니라면 현재 로그인 회원으로 귀속
            if not info.owner_id or info.owner_id == user_id:
                info.owner_id = user_id
                info.owner_email = user_email
                info.updated_at = datetime.now().strftime("%Y-%m-%d")
                meta_file.write_text(json.dumps(asdict(info), ensure_ascii=False, indent=2), encoding="utf-8")
                return True
            return False
        except Exception as e:
            print(f"Error claiming project {project_id}: {e}")
            return False

    def list_projects(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        프로젝트 목록 조회 (user_id가 지정된 경우 내 프로젝트 및 미할당 프로젝트만 필터링)
        """
        active_id = self.get_active_project_id()
        projects = []

        for pdir in self.projects_dir.iterdir():
            if not pdir.is_dir():
                continue
            info = self.get_project_info(pdir.name)

            # 사용자 분리: 다른 회원의 시집은 목록에서 보호(숨김)
            if user_id:
                if info.owner_id and info.owner_id != user_id:
                    # 기본 시집이거나 활성 시집, 또는 예시 계정 소유 시집인 경우 현재 로그인 사용자로 자동 귀속
                    if pdir.name == "노을빛_기억" or info.id == active_id or info.owner_id == "poet_kim_123":
                        self.claim_project(pdir.name, user_id, "")
                    else:
                        continue
            
            # 원고 진행 상태 계산
            manuscript_file = pdir / "작품집_원고.md"
            mgr = ManuscriptManager(file_path=manuscript_file)
            completed = mgr.get_completed_count()
            total_works = len(mgr.load_works())

            projects.append({
                "id": info.id,
                "name": info.name,
                "subtitle": info.subtitle,
                "author": info.author,
                "target_count": info.target_count,
                "description": info.description,
                "book_type": getattr(info, "book_type", "illustrated"),
                "owner_id": info.owner_id,
                "owner_email": info.owner_email,
                "is_mine": (info.owner_id == user_id) if user_id else True,
                "completed_count": completed,
                "total_works": total_works,
                "progress_percent": round((completed / max(1, info.target_count)) * 100, 1),
                "is_active": (info.id == active_id),
                "created_at": info.created_at,
                "updated_at": info.updated_at
            })

        # 활성 프로젝트 우선, 그다음 최신순 정렬
        projects.sort(key=lambda x: (not x["is_active"], x["created_at"]), reverse=False)
        return projects

    def create_project(
        self,
        name: str,
        subtitle: str,
        author: str,
        target_count: int = 35,
        description: str = "",
        book_type: str = "illustrated",
        author_type: str = "single",
        owner_id: str = "",
        owner_email: str = ""
    ) -> ProjectInfo:
        """새로운 시집 프로젝트를 생성하고 기본 구조 초기화"""
        # 폴더용 ID 생성 (한글/영문 안전 변환)
        safe_name = re.sub(r'[^a-zA-Z0-9가-힣]', '_', name).strip('_')
        base_id = safe_name.lower() if safe_name else "poem_book"
        
        project_id = base_id
        counter = 1
        while (self.projects_dir / project_id).exists():
            project_id = f"{base_id}_{counter}"
            counter += 1

        pdir = self.projects_dir / project_id
        pdir.mkdir(parents=True, exist_ok=True)
        (pdir / "images").mkdir(parents=True, exist_ok=True)

        info = ProjectInfo(
            id=project_id,
            name=name,
            subtitle=subtitle or ("삶의 궤적을 빚어낸 서정 시화집" if book_type == "illustrated" else "서정 시집"),
            author=author or ("기억의 작가" if author_type == "single" else "온가족 엮음"),
            target_count=target_count or 35,
            description=description,
            book_type=book_type or "illustrated",
            author_type=author_type or "single",
            owner_id=owner_id or "",
            owner_email=owner_email or "",
            created_at=datetime.now().strftime("%Y-%m-%d"),
            updated_at=datetime.now().strftime("%Y-%m-%d")
        )

        # metadata 저장
        (pdir / "project.json").write_text(json.dumps(asdict(info), ensure_ascii=False, indent=2), encoding="utf-8")

        # 템플릿 작품집_원고.md 생성
        author_label = "지은이" if info.author_type == "single" else "엮은이"
        template_md = f"""# {info.name} 원고 (진행 현황: 0 / {info.target_count}편 완료)

> **{author_label}**: {info.author}  
> **부제**: {info.subtitle}  
> **도서 형태**: {'서정 시화집' if info.book_type == 'illustrated' else '일반 시집'}  
> **시집 성격**: {'개인 시집' if info.author_type == 'single' else '공동·가족 시집 (앤솔로지)'}  
> **기획**: {info.description}  

---
"""
        (pdir / "작품집_원고.md").write_text(template_md, encoding="utf-8")

        # 기본 CSV 헤더 생성
        headers = "Episode_No,Title,Poem_Body,Memory_Anchor,Image_File\n"
        (pdir / "시화집_본문데이터.csv").write_text(headers, encoding="utf-8-sig")

        # 새 프로젝트를 활성 프로젝트로 설정
        self.set_active_project_id(project_id)
        return info

    def update_project_info(
        self,
        project_id: Optional[str],
        name: str,
        subtitle: str,
        author: str,
        target_count: int = 35,
        description: str = "",
        book_type: Optional[str] = None,
        author_type: Optional[str] = None
    ) -> ProjectInfo:
        """기존 시집 프로젝트의 메타데이터 수정 (제목 변경 시 폴더명도 안전하게 자동 리네이밍)"""
        pid = project_id or self.get_active_project_id()
        pdir = self.get_project_dir(pid)
        if not pdir.exists():
            raise ValueError(f"존재하지 않는 프로젝트입니다: {pid}")

        info = self.get_project_info(pid)
        cleaned_name = name.strip() or info.name
        info.name = cleaned_name
        info.subtitle = subtitle.strip() or info.subtitle
        info.author = author.strip() or info.author
        info.target_count = target_count or info.target_count
        info.description = description.strip()
        if book_type:
            info.book_type = book_type
        if author_type:
            info.author_type = author_type
        info.updated_at = datetime.now().strftime("%Y-%m-%d")

        # 폴더명 리네이밍 (새 제목 기반)
        was_active = (self.get_active_project_id() == pid)
        safe_id = re.sub(r'[^\w가-힣]+', '_', cleaned_name).strip('_')
        if safe_id and safe_id != pid:
            new_pdir = self.projects_dir / safe_id
            if not new_pdir.exists():
                try:
                    pdir.rename(new_pdir)
                    pdir = new_pdir
                    pid = safe_id
                    info.id = safe_id
                    if was_active:
                        self.set_active_project_id(safe_id)
                except Exception:
                    pass  # 파일 락 등으로 실패 시 기존 폴더 유지

        # project.json 저장
        (pdir / "project.json").write_text(json.dumps(asdict(info), ensure_ascii=False, indent=2), encoding="utf-8")


        # 작품집_원고.md 상단 메타데이터 동기화 (기존 시 본문은 보존)
        manuscript_file = pdir / "작품집_원고.md"
        if manuscript_file.exists():
            content = manuscript_file.read_text(encoding="utf-8")
            # 상단 제목 및 메타 라인 교체
            mgr = ManuscriptManager(file_path=manuscript_file)
            completed = mgr.get_completed_count()
            
            # 본문 분리 (첫 번째 --- 이후)
            parts = content.split("\n---\n", 1)
            body_content = parts[1] if len(parts) > 1 else ""
            
            new_header = f"""# {info.name} 원고 (진행 현황: {completed} / {info.target_count}편 완료)

> **지은이**: {info.author}  
> **부제**: {info.subtitle}  
> **기획**: {info.description}  
"""
            updated_md = new_header + "\n---\n" + body_content
            manuscript_file.write_text(updated_md, encoding="utf-8")
        return info

    def delete_project(self, project_id: str) -> bool:
        """시집 프로젝트 삭제 (서재에 최소 1권은 보존)"""
        existing = [p.name for p in self.projects_dir.iterdir() if p.is_dir()]
        if len(existing) <= 1:
            raise ValueError("서재에 최소 1권의 시집 프로젝트는 보관되어야 하므로 삭제할 수 없습니다.")

        target_dir = self.projects_dir / project_id
        if not target_dir.exists():
            raise ValueError(f"존재하지 않는 시집 프로젝트입니다: {project_id}")

        # 현재 활성 프로젝트를 삭제하는 경우 남아있는 다른 프로젝트로 자동 복귀
        if self.get_active_project_id() == project_id:
            remaining = [p for p in existing if p != project_id]
            self.set_active_project_id(remaining[0])

        shutil.rmtree(target_dir)
        return True

    def update_book_extras(self, project_id: Optional[str], extras: dict) -> ProjectInfo:
        """시인의 말, 에필로그, 뒷표지 카피, 판권지 정보 등 본문 외 출판 메타데이터 저장"""
        pid = project_id or self.get_active_project_id()
        pdir = self.get_project_dir(pid)
        if not pdir.exists():
            raise ValueError(f"존재하지 않는 프로젝트입니다: {pid}")

        info = self.get_project_info(pid)
        if "prologue" in extras:
            info.prologue = str(extras["prologue"]).strip()
        if "epilogue" in extras:
            info.epilogue = str(extras["epilogue"]).strip()
        if "back_cover_blurb" in extras:
            info.back_cover_blurb = str(extras["back_cover_blurb"]).strip()
        if "cover_image" in extras:
            info.cover_image = str(extras["cover_image"]).strip()
        if "publisher" in extras:
            info.publisher = str(extras["publisher"]).strip() or "부크크 (Bookk) 자가출판"
        if "published_date" in extras:
            info.published_date = str(extras["published_date"]).strip()
        if "price" in extras:
            info.price = str(extras["price"]).strip()
        if "isbn" in extras:
            info.isbn = str(extras["isbn"]).strip()

        info.updated_at = datetime.now().strftime("%Y-%m-%d")

        meta_file = pdir / "project.json"
        meta_file.write_text(json.dumps(asdict(info), ensure_ascii=False, indent=2), encoding="utf-8")
        return info

    def export_project_zip(self, project_id: Optional[str] = None) -> Path:
        """시집 전체 데이터(원고, CSV, PDF, 삽화)를 ZIP 압축 파일로 패키징"""
        import zipfile
        pdir = self.get_project_dir(project_id)
        info = self.get_project_info(project_id)

        export_dir = BASE_DIR / ".exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        zip_path = export_dir / f"{info.id}_backup.zip"

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file in pdir.rglob("*"):
                if file.is_file():
                    arcname = file.relative_to(pdir)
                    zf.write(file, arcname)

        return zip_path

    def get_active_project_info(self) -> ProjectInfo:
        return self.get_project_info()

    def get_manuscript_manager(self, project_id: Optional[str] = None) -> ManuscriptManager:
        pdir = self.get_project_dir(project_id)
        return ManuscriptManager(file_path=pdir / "작품집_원고.md")

    def get_active_manuscript_manager(self) -> ManuscriptManager:
        pdir = self.get_project_dir()
        return ManuscriptManager(file_path=pdir / "작품집_원고.md")

    def get_active_csv_path(self) -> Path:
        return self.get_project_dir() / "시화집_본문데이터.csv"

    def get_active_pdf_path(self) -> Path:
        return self.get_project_dir() / "시화집_완성본.pdf"

    def get_active_images_dir(self) -> Path:
        return self.get_project_dir() / "images"

# 전역 프로젝트 매니저 싱글톤 인스턴스
    def get_book_structure(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """
        [Full Book Architecture]
        책 전체의 시퀀스 구조(앞표지 -> 속표지 -> 서문 -> 목차 -> 부/시화 본문 -> 맺음말 -> 판권지 -> 뒤표지)와
        각 섹션별 페이지 번호, 완성 상태(상태 머신), 세부 데이터를 단일 모델로 반환합니다.
        """
        info = self.get_project_info(project_id)
        mgr = self.get_manuscript_manager(project_id)
        works = mgr.load_works()

        sections: List[Dict[str, Any]] = []
        current_page = 1

        # -------------------------------------------------------------
        # 1. Front Matter (책의 시작)
        # -------------------------------------------------------------
        # 1-1. 앞표지 (Cover - Page 0)
        has_cover_img = bool(getattr(info, "cover_image", "").strip())
        sections.append({
            "id": "cover",
            "section_type": "cover",
            "group": "front_matter",
            "title": "앞표지",
            "subtitle": info.subtitle or "",
            "author": info.author or "",
            "status": "completed" if has_cover_img else "in_progress",
            "page_start": 0,
            "page_count": 2,
            "episode_no": "",
            "chapter": "",
            "data": {
                "cover_image": info.cover_image or "",
                "title": info.name or "",
                "subtitle": info.subtitle or "",
                "author": info.author or ""
            }
        })

        # 1-2. 속표지 (도비라 - Page 1~2)
        sections.append({
            "id": "half_title",
            "section_type": "half_title",
            "group": "front_matter",
            "title": "속표지 (도비라)",
            "subtitle": info.subtitle or "",
            "author": info.author or "",
            "status": "completed",
            "page_start": 1,
            "page_count": 2,
            "episode_no": "",
            "chapter": "",
            "data": {
                "title": info.name or "",
                "subtitle": info.subtitle or "",
                "author": info.author or "",
                "publisher": getattr(info, "publisher", "부크크 (Bookk) 자가출판")
            }
        })
        current_page = 3

        # 1-3. 시인의 말 (서문 / Prologue - Page 3)
        prologue_text = (getattr(info, "prologue", "") or "").strip()
        has_prologue = bool(prologue_text)
        sections.append({
            "id": "prologue",
            "section_type": "prologue",
            "group": "front_matter",
            "title": "시인의 말 (서문)",
            "subtitle": "Prologue",
            "author": info.author or "",
            "status": "completed" if has_prologue else "empty",
            "page_start": current_page,
            "page_count": 1,
            "episode_no": "",
            "chapter": "",
            "data": {
                "content": prologue_text,
                "author": info.author or ""
            }
        })
        current_page += 1

        # 1-4. 차례 (시집 목차 - Page 4~5)
        sections.append({
            "id": "toc",
            "section_type": "toc",
            "group": "front_matter",
            "title": "차 례 (목차)",
            "subtitle": "Table of Contents",
            "author": "",
            "status": "completed",
            "page_start": current_page,
            "page_count": 2,
            "episode_no": "",
            "chapter": "",
            "data": {
                "works_count": len(works)
            }
        })
        current_page += 2

        # -------------------------------------------------------------
        # 2. Body Matter (부 간지 & 시화 본문)
        # -------------------------------------------------------------
        current_chapter = None
        part_idx = 1

        for w in works:
            ch = getattr(w, "chapter", "").strip()
            # 새로운 부(Chapter)가 등장하고 비어있지 않은 경우 부 간지(Part Divider) 자동 배치
            if ch and ch != current_chapter:
                current_chapter = ch
                sections.append({
                    "id": f"part_{part_idx}",
                    "section_type": "part_divider",
                    "group": "body_matter",
                    "title": ch,
                    "subtitle": f"제{part_idx}부",
                    "author": "",
                    "status": "completed",
                    "page_start": current_page,
                    "page_count": 2,
                    "episode_no": "",
                    "chapter": ch,
                    "data": {
                        "chapter_title": ch
                    }
                })
                current_page += 2
                part_idx += 1

            # 시화 작품 노드
            cfg = getattr(w, "layout_config", None)
            lines_cnt = len((getattr(w, "poem_body", "") or "").split("\n"))
            if cfg and isinstance(cfg, dict) and "slots" in cfg and cfg.get("slots"):
                page_span = cfg.get("page_count", 2)
            elif getattr(w, "layout_mode", "compact") == "multi_page" and lines_cnt > 16:
                page_span = 4
            else:
                page_span = 2

            w_status = "completed" if (getattr(w, "status", "") == "완성" or cfg) else "in_progress"
            sections.append({
                "id": f"poem_{w.episode_no}",
                "section_type": "poem",
                "group": "body_matter",
                "title": f"[{w.episode_no}] {w.title}",
                "subtitle": w.title,
                "author": getattr(w, "author", "") or info.author,
                "status": w_status,
                "page_start": current_page,
                "page_count": page_span,
                "episode_no": w.episode_no,
                "chapter": current_chapter or "",
                "data": {
                    "episode_no": w.episode_no,
                    "title": w.title,
                    "poem_body": getattr(w, "poem_body", ""),
                    "image_file": getattr(w, "image_file", ""),
                    "image_file_2": getattr(w, "image_file_2", ""),
                    "author": getattr(w, "author", "") or info.author,
                    "layout_config": cfg
                }
            })
            current_page += page_span

        # -------------------------------------------------------------
        # 3. Back Matter (책의 갈무리)
        # -------------------------------------------------------------
        # 3-1. 맺음말 (에필로그 / Epilogue)
        epilogue_text = (getattr(info, "epilogue", "") or "").strip()
        has_epilogue = bool(epilogue_text)
        sections.append({
            "id": "epilogue",
            "section_type": "epilogue",
            "group": "back_matter",
            "title": "맺음말 (에필로그)",
            "subtitle": "Epilogue",
            "author": info.author or "",
            "status": "completed" if has_epilogue else "empty",
            "page_start": current_page,
            "page_count": 1,
            "episode_no": "",
            "chapter": "",
            "data": {
                "content": epilogue_text,
                "author": info.author or ""
            }
        })
        current_page += 1

        # 3-2. 정식 출판 판권지 (Colophon)
        sections.append({
            "id": "colophon",
            "section_type": "colophon",
            "group": "back_matter",
            "title": "정식 출판 판권지",
            "subtitle": "Colophon",
            "author": info.author or "",
            "status": "completed",
            "page_start": current_page,
            "page_count": 1,
            "episode_no": "",
            "chapter": "",
            "data": {
                "publisher": getattr(info, "publisher", "부크크 (Bookk) 자가출판"),
                "published_date": getattr(info, "published_date", ""),
                "price": getattr(info, "price", "13,000원"),
                "isbn": getattr(info, "isbn", ""),
                "title": info.name or "",
                "author": info.author or ""
            }
        })
        current_page += 1

        # 3-3. 뒤표지 (Back Cover)
        blurb_text = (getattr(info, "back_cover_blurb", "") or "").strip()
        has_blurb = bool(blurb_text)
        sections.append({
            "id": "back_cover",
            "section_type": "back_cover",
            "group": "back_matter",
            "title": "뒤표지 (책 소개 & 바코드)",
            "subtitle": "Back Cover",
            "author": "",
            "status": "completed" if has_blurb else "empty",
            "page_start": current_page,
            "page_count": 1,
            "episode_no": "",
            "chapter": "",
            "data": {
                "blurb": blurb_text,
                "price": getattr(info, "price", "13,000원"),
                "isbn": getattr(info, "isbn", "")
            }
        })

        # 각 섹션 표준 필드 정규화 (프론트엔드 호환용 start_page, end_page, status_icon, group_label 등)
        for s in sections:
            p_start = s.get("page_start", 0)
            p_cnt = s.get("page_count", 1)
            s["start_page"] = p_start
            s["end_page"] = max(p_start, p_start + p_cnt - 1)
            s["category"] = s.get("section_type", "")
            
            st = s.get("status", "empty")
            if st == "completed":
                s["status_icon"] = "🟢"
                s["status_label"] = "완성"
            elif st == "in_progress":
                s["status_icon"] = "🟠"
                s["status_label"] = "작성 중"
            else:
                s["status_icon"] = "⚪"
                s["status_label"] = "미작성"

            grp = s.get("group", "")
            if grp == "front_matter":
                s["group_label"] = "앞부속 (표지·서문·목차)"
            elif grp == "body_matter":
                s["group_label"] = "본문 시화"
            else:
                s["group_label"] = "뒷부속 (맺음말·판권지)"

            s["can_dtp_edit"] = True

        # 상태 머신 통계
        completed_cnt = sum(1 for s in sections if s["status"] == "completed")
        empty_cnt = sum(1 for s in sections if s["status"] == "empty")
        in_prog_cnt = sum(1 for s in sections if s["status"] == "in_progress")

        return {
            "project_id": info.id,
            "project_name": info.name,
            "subtitle": info.subtitle,
            "author": info.author,
            "total_pages": current_page,
            "stats": {
                "total_sections": len(sections),
                "completed_sections": completed_cnt,
                "completed": completed_cnt,
                "in_progress": in_prog_cnt,
                "empty": empty_cnt,
                "total_pages": current_page,
                "completion_rate": round((completed_cnt / len(sections)) * 100, 1) if sections else 0
            },
            "sections": sections
        }

    def update_section_content(
        self,
        section_id: str,
        payload: Dict[str, Any],
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        특정 섹션의 콘텐츠(서문, 에필로그, 판권 정보, 표지 등)를 실시간 업데이트하고
        최신 책 구조를 반환합니다.
        """
        info = self.get_project_info(project_id)
        updated = False

        if section_id in ("prologue", "preface"):
            if "content" in payload: info.prologue = payload["content"]
            if "author" in payload and payload["author"]: info.author = payload["author"]
            updated = True
        elif section_id == "epilogue":
            if "content" in payload: info.epilogue = payload["content"]
            if "author" in payload and payload["author"]: info.author = payload["author"]
            updated = True
        elif section_id == "back_cover":
            if "blurb" in payload: info.back_cover_blurb = payload["blurb"]
            if "price" in payload: info.price = payload["price"]
            if "isbn" in payload: info.isbn = payload["isbn"]
            updated = True
        elif section_id == "colophon":
            if "title" in payload and payload["title"]: info.name = payload["title"]
            if "author" in payload and payload["author"]: info.author = payload["author"]
            if "publisher" in payload: info.publisher = payload["publisher"]
            if "published_date" in payload: info.published_date = payload["published_date"]
            if "price" in payload: info.price = payload["price"]
            if "isbn" in payload: info.isbn = payload["isbn"]
            updated = True
        elif section_id in ("cover", "half_title"):
            if "cover_image" in payload: info.cover_image = payload["cover_image"]
            if "title" in payload and payload["title"]: info.name = payload["title"]
            if "subtitle" in payload: info.subtitle = payload["subtitle"]
            if "author" in payload and payload["author"]: info.author = payload["author"]
            if "publisher" in payload and payload["publisher"]: info.publisher = payload["publisher"]
            updated = True

        if updated:
            self.update_project_info(info.id, asdict(info))

        return self.get_book_structure(project_id)

project_manager = ProjectManager()


