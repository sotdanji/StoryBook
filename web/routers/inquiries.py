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
from core.ai_coach import ai_coach

router = APIRouter()


class ReplyRequest(BaseModel):
    inquiry_id: str
    reply_content: str
    status: Optional[str] = "answered"


class EscalateRequest(BaseModel):
    inquiry_id: str


class ResolveRequest(BaseModel):
    inquiry_id: str
    satisfaction: Optional[int] = 5


class FollowupRequest(BaseModel):
    inquiry_id: str
    followup_content: str


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
    """사용자 1:1 문의 접수 및 즉시 AI 안실장 자동 출판 코칭 생성"""
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
        # 1. 1:1 문의 데이터 영구 보관 (Turso DB)
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

        # 2. 🤖 AI 안실장 실시간 맞춤 출판 코칭 생성 (Gemini 3.8 Flash + 매뉴얼 지식 + 시집 컨텍스트)
        advice = ai_coach.generate_coaching_advice(
            title=title,
            content=content,
            author_name=author_name,
            category=category,
            project_context=None
        )

        ai_reply = advice.get("reply", "")
        if ai_reply:
            inquiry_manager.save_ai_reply(
                inquiry_id=item.id,
                ai_reply=ai_reply,
                project_context=advice.get("project_context")
            )

        return {
            "success": True,
            "message": "AI 안실장의 실시간 맞춤 코칭 답변이 도착했습니다!",
            "inquiry_id": item.id,
            "ai_reply": ai_reply,
            "coach_name": advice.get("coach_name", "AI 안실장"),
            "status": "ai_answered",
            "can_escalate": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"문의 접수 실패: {str(e)}")


@router.post("/api/inquiries/escalate")
async def escalate_inquiry_to_human(req: EscalateRequest):
    """작가가 AI 안실장 답변 외에 사람 전문가(대표님) 직접 검토를 요청함"""
    updated = inquiry_manager.escalate_inquiry(req.inquiry_id)
    if not updated:
        raise HTTPException(status_code=404, detail="문의 내역을 찾을 수 없습니다.")
    return {
        "success": True,
        "message": "대표님께 직접 검토 요청이 안전하게 전달되었습니다. 확인 후 정성껏 안내해 드리겠습니다.",
        "status": "escalated"
    }


@router.post("/api/inquiries/resolve")
async def resolve_inquiry(req: ResolveRequest):
    """작가가 AI 안실장의 답변으로 문제가 잘 해결되었음을 표시함"""
    updated = inquiry_manager.resolve_inquiry(req.inquiry_id, req.satisfaction)
    if not updated:
        raise HTTPException(status_code=404, detail="문의 내역을 찾을 수 없습니다.")
    return {
        "success": True,
        "message": "도움이 되어 정말 기쁩니다! 언제든 편하게 질문해 주세요.",
        "status": "resolved"
    }


@router.post("/api/inquiries/ask_followup")
async def ask_followup(req: FollowupRequest):
    """AI 안실장과 연속 추가 문답 진행"""
    item = inquiry_manager.get_inquiry(req.inquiry_id)
    if not item:
        raise HTTPException(status_code=404, detail="문의 내역을 찾을 수 없습니다.")

    followup_prompt = f"""
[이전 질문]: {item.content}
[이전 AI 안실장 답변]: {item.ai_reply}
[작가님의 추가 질문]: {req.followup_content}
"""
    advice = ai_coach.generate_coaching_advice(
        title=f"추가 질문: {item.title}",
        content=followup_prompt,
        author_name=item.author_name,
        category=item.category,
        project_context=item.project_context
    )
    new_reply = advice.get("reply", "")

    # 대화 이어붙이기
    combined_reply = f"{item.ai_reply}\n\n---\n💬 **[추가 답변]**\n{new_reply}"
    inquiry_manager.save_ai_reply(item.id, combined_reply)

    return {
        "success": True,
        "inquiry_id": item.id,
        "ai_reply": new_reply,
        "combined_reply": combined_reply
    }


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

