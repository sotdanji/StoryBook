"""
core/inquiry_manager.py
StoryBook Studio - 1:1 비밀 문의 및 출판 코칭 상담 관리자
- 사용자 문의(버그 제보, 조판 편집 도움 요청) 저장 및 조회
- 작업 중인 시집 백업 ZIP 자동 첨부 연계
- 최고 관리자의 답변 및 상태(접수/검토중/답변완료) 관리
"""

import json
import shutil
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from core.config import BASE_DIR
from core.project_manager import project_manager

INQUIRIES_DIR = BASE_DIR / "data" / "inquiries"
ATTACHMENTS_DIR = INQUIRIES_DIR / "attachments"


@dataclass
class InquiryItem:
    id: str                         # inquiry_20261105_104500_ab12
    category: str                   # "coaching" | "bug" | "feature" | "publishing" | "general"
    category_label: str             # "시화집 편집 및 조판 코칭"
    title: str                      # 제목
    content: str                    # 문의 내용
    author_name: str                # 신청자 성함/필명
    author_email: str               # 회신받을 이메일
    user_id: Optional[str] = ""     # 회원 UID (로그인 시)
    project_id: Optional[str] = ""  # 첨부된 시집 ID
    project_name: Optional[str] = ""# 시집 이름
    attachment_type: str = "none"   # "full_zip" | "csv" | "custom_file" | "none"
    attachment_path: str = ""       # 상대 저장 경로
    attachment_filename: str = ""   # 원본 파일명
    status: str = "pending"         # "pending" (접수 대기) | "reviewing" (검토 중) | "answered" (답변 완료)
    reply_content: str = ""         # 작가/관리자의 코칭 답변
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    answered_at: Optional[str] = "" # 답변 완료 일시


CATEGORY_MAP = {
    "coaching": "🎨 시화집 편집 및 조판 코칭",
    "bug": "🐞 버그 제보 및 기술 지원",
    "feature": "💡 새로운 기능 제안",
    "publishing": "📖 독립출판 및 종이책 상담",
    "general": "☕ 기타 문의 및 응원"
}


class InquiryManager:
    def __init__(self, base_dir: Path = INQUIRIES_DIR):
        self.inquiries_dir = base_dir
        self.attachments_dir = self.inquiries_dir / "attachments"
        self.inquiries_dir.mkdir(parents=True, exist_ok=True)
        self.attachments_dir.mkdir(parents=True, exist_ok=True)

    def _generate_id(self) -> str:
        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        import uuid
        short_uuid = uuid.uuid4().hex[:6]
        return f"inq_{now_str}_{short_uuid}"

    def create_inquiry(
        self,
        category: str,
        title: str,
        content: str,
        author_name: str,
        author_email: str,
        user_id: str = "",
        attach_type: str = "none",
        custom_file_bytes: Optional[bytes] = None,
        custom_filename: Optional[str] = None
    ) -> InquiryItem:
        """새로운 1:1 문의/코칭 요청 등록"""
        inquiry_id = self._generate_id()
        cat_label = CATEGORY_MAP.get(category, "일반 문의")

        active_id = project_manager.get_active_project_id()
        active_info = project_manager.get_active_project_info()
        pname = active_info.name if active_info else "알 수 없는 시집"

        attachment_path = ""
        attachment_filename = ""

        # 1. 시집 전체 백업 ZIP 자동 첨부
        if attach_type == "full_zip":
            try:
                zip_path = project_manager.export_project_zip(active_id)
                if zip_path.exists():
                    target_name = f"{inquiry_id}_{active_id}_전체백업.zip"
                    target_dest = self.attachments_dir / target_name
                    shutil.copy2(zip_path, target_dest)
                    attachment_path = str(target_dest.relative_to(self.inquiries_dir))
                    attachment_filename = f"{pname}_전체백업.zip"
            except Exception as e:
                print(f"Failed to auto-attach project zip: {e}")

        # 2. 본문데이터 CSV만 첨부
        elif attach_type == "csv":
            try:
                csv_path = project_manager.get_active_csv_path()
                if csv_path.exists():
                    target_name = f"{inquiry_id}_{active_id}_본문데이터.csv"
                    target_dest = self.attachments_dir / target_name
                    shutil.copy2(csv_path, target_dest)
                    attachment_path = str(target_dest.relative_to(self.inquiries_dir))
                    attachment_filename = f"{pname}_본문데이터.csv"
            except Exception as e:
                print(f"Failed to attach csv: {e}")

        # 3. 직접 업로드한 커스텀 파일
        elif attach_type == "custom_file" and custom_file_bytes and custom_filename:
            safe_fname = Path(custom_filename).name
            target_name = f"{inquiry_id}_{safe_fname}"
            target_dest = self.attachments_dir / target_name
            target_dest.write_bytes(custom_file_bytes)
            attachment_path = str(target_dest.relative_to(self.inquiries_dir))
            attachment_filename = safe_fname

        item = InquiryItem(
            id=inquiry_id,
            category=category,
            category_label=cat_label,
            title=title.strip(),
            content=content.strip(),
            author_name=author_name.strip() or "작가님",
            author_email=author_email.strip(),
            user_id=user_id or "",
            project_id=active_id,
            project_name=pname,
            attachment_type=attach_type,
            attachment_path=attachment_path,
            attachment_filename=attachment_filename,
            status="pending"
        )

        # JSON 저장
        item_file = self.inquiries_dir / f"{inquiry_id}.json"
        item_file.write_text(json.dumps(asdict(item), ensure_ascii=False, indent=2), encoding="utf-8")
        return item

    def get_inquiry(self, inquiry_id: str) -> Optional[InquiryItem]:
        item_file = self.inquiries_dir / f"{inquiry_id}.json"
        if not item_file.exists():
            return None
        try:
            data = json.loads(item_file.read_text(encoding="utf-8"))
            return InquiryItem(**data)
        except Exception:
            return None

    def list_inquiries(self, user_id: Optional[str] = None, user_email: Optional[str] = None) -> List[Dict[str, Any]]:
        """전체 또는 특정 사용자 문의 목록 반환 (최신순)"""
        items = []
        for f in self.inquiries_dir.glob("inq_*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                # 사용자 필터링 (user_id 또는 이메일 매칭)
                if user_id or user_email:
                    match_id = bool(user_id and data.get("user_id") == user_id)
                    match_email = bool(user_email and data.get("author_email") == user_email)
                    if not (match_id or match_email):
                        continue
                items.append(data)
            except Exception:
                continue

        # 최신 등록순 정렬
        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return items

    def reply_inquiry(self, inquiry_id: str, reply_content: str, status: str = "answered") -> Optional[InquiryItem]:
        """관리자 답변 등록 및 상태 갱신"""
        item_file = self.inquiries_dir / f"{inquiry_id}.json"
        if not item_file.exists():
            return None
        try:
            data = json.loads(item_file.read_text(encoding="utf-8"))
            data["reply_content"] = reply_content.strip()
            data["status"] = status
            data["answered_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            item_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            return InquiryItem(**data)
        except Exception:
            return None

    def get_attachment_abs_path(self, inquiry_id: str) -> Optional[Path]:
        """첨부 파일의 안전한 절대 경로 반환"""
        item = self.get_inquiry(inquiry_id)
        if not item or not item.attachment_path:
            return None
        target = (self.inquiries_dir / item.attachment_path).resolve()
        # inquiries_dir 하위 경로인지 검증
        try:
            target.relative_to(self.inquiries_dir.resolve())
            if target.exists() and target.is_file():
                return target
        except Exception:
            pass
        return None


inquiry_manager = InquiryManager()

