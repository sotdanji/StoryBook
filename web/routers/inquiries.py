"""
web/routers/inquiries.py
StoryBook Studio - 1:1 비밀 문의 및 출판 코칭 상담 API 라우터
"""

import urllib.parse
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Form, File, UploadFile
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel

from core.auth_manager import auth_manager
from core.inquiry_manager import inquiry_manager

router = APIRouter()


class ReplyRequest(BaseModel):
    inquiry_id: str
    reply_content: str
    status: Optional[str] = "answered"


# -------------------------------------------------------------
# 사용자 API
# -------------------------------------------------------------
@router.post("/api/inquiries/submit")
async def submit_inquiry(
    category: str = Form(...),
    title: str = Form(...),
    content: str = Form(...),
    author_name: str = Form(...),
    author_email: str = Form(...),
    attach_type: str = Form("none"),
    custom_file: Optional[UploadFile] = File(None)
):
    """사용자 1:1 문의 및 출판 편집 도움 요청 접수"""
    if not title.strip() or not content.strip():
        raise HTTPException(status_code=400, detail="제목과 문의 내용을 모두 입력해주세요.")
    if not author_email.strip() or "@" not in author_email:
        raise HTTPException(status_code=400, detail="회신을 받으실 올바른 이메일 주소를 입력해주세요.")

    current_user = auth_manager.get_current_user()
    user_id = current_user.get("user_id", "") if current_user else ""

    file_bytes = None
    filename = None
    if custom_file and attach_type == "custom_file":
        file_bytes = await custom_file.read()
        filename = custom_file.filename

    try:
        item = inquiry_manager.create_inquiry(
            category=category,
            title=title,
            content=content,
            author_name=author_name,
            author_email=author_email,
            user_id=user_id,
            attach_type=attach_type,
            custom_file_bytes=file_bytes,
            custom_filename=filename
        )
        return {
            "success": True,
            "message": "상담 요청이 안전하게 접수되었습니다. 작가님이 검토 후 이메일 및 스튜디오로 회신드립니다.",
            "inquiry_id": item.id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"문의 접수 실패: {str(e)}")


@router.get("/api/inquiries/my")
async def get_my_inquiries():
    """현재 로그인 사용자의 상담 문의 내역 및 답변 조회"""
    current_user = auth_manager.get_current_user()
    user_id = current_user.get("user_id") if current_user else None
    email = current_user.get("email") if current_user else None

    # 미로그인 상태인 경우 빈 목록
    if not user_id and not email:
        return {"inquiries": []}

    items = inquiry_manager.list_inquiries(user_id=user_id, user_email=email)
    return {"inquiries": items}


# -------------------------------------------------------------
# 최고 관리자 전용 API
# -------------------------------------------------------------
@router.get("/api/admin/inquiries")
async def get_admin_inquiries():
    """관리자: 전체 1:1 문의 목록 조회"""
    if not auth_manager.is_current_user_admin():
        raise HTTPException(status_code=403, detail="최고 관리자 권한이 필요합니다.")
    items = inquiry_manager.list_inquiries()
    return {"inquiries": items}


@router.post("/api/admin/inquiries/reply")
async def reply_inquiry_endpoint(req: ReplyRequest):
    """관리자: 1:1 문의 답변 등록"""
    if not auth_manager.is_current_user_admin():
        raise HTTPException(status_code=403, detail="최고 관리자 권한이 필요합니다.")
    
    if not req.reply_content.strip():
        raise HTTPException(status_code=400, detail="답변 내용을 입력해주세요.")

    item = inquiry_manager.reply_inquiry(
        inquiry_id=req.inquiry_id,
        reply_content=req.reply_content,
        status=req.status or "answered"
    )
    if not item:
        raise HTTPException(status_code=404, detail="문의 내역을 찾을 수 없습니다.")

    return {"success": True, "message": "답변이 등록되었습니다."}


@router.get("/api/admin/inquiries/download/{inquiry_id}")
async def download_inquiry_attachment(inquiry_id: str):
    """관리자: 문의에 첨부된 시집 백업 ZIP 다운로드"""
    if not auth_manager.is_current_user_admin():
        raise HTTPException(status_code=403, detail="최고 관리자 권한이 필요합니다.")

    item = inquiry_manager.get_inquiry(inquiry_id)
    if not item or not item.attachment_path:
        raise HTTPException(status_code=404, detail="첨부 파일이 없습니다.")

    abs_path = inquiry_manager.get_attachment_abs_path(inquiry_id)
    if not abs_path or not abs_path.exists():
        raise HTTPException(status_code=404, detail="첨부 파일을 찾을 수 없습니다.")

    download_name = item.attachment_filename or abs_path.name
    safe_name = urllib.parse.quote(download_name)
    return FileResponse(
        path=str(abs_path),
        filename=download_name,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_name}"}
    )

