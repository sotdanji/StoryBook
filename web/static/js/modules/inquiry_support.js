/**
 * web/static/js/modules/inquiry_support.js
 * StoryBook Studio - 1:1 비밀 소통방 & AI 안실장 실시간 출판 코칭 모듈
 */

let currentActiveInquiry = null;

export function initInquirySupport() {
  window.openInquiryModal = openInquiryModal;
  window.closeInquiryModal = closeInquiryModal;
  window.switchInquiryTab = switchInquiryTab;
  window.handleInquirySubmit = handleInquirySubmit;
  window.loadMyInquiries = loadMyInquiries;
  window.handleInquiryResolveAction = handleInquiryResolveAction;
  window.handleInquiryEscalateAction = handleInquiryEscalateAction;
  window.toggleInquiryFollowupBox = toggleInquiryFollowupBox;
  window.cancelInquiryFollowup = cancelInquiryFollowup;
  window.submitInquiryFollowup = submitInquiryFollowup;
  window.resetInquiryFormToNew = resetInquiryFormToNew;

  // URL 파라미터로 상담 모달 자동 오픈 또는 갤러리 공유 요청 시
  try {
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get("open_inquiry") === "true") {
      setTimeout(() => {
        openInquiryModal();
        const shareGalleryUrl = urlParams.get("share_gallery");
        const shareProjName = urlParams.get("share_proj") || "나의 시집";
        if (shareGalleryUrl) {
          const titleInput = document.getElementById("inquiryTitle");
          const contentInput = document.getElementById("inquiryContent");
          const catSelect = document.getElementById("inquiryCategory");
          if (catSelect) catSelect.value = "coaching";
          if (titleInput) titleInput.value = `[내 갤러리 구경 오세요] ${shareProjName} 시화 갤러리를 나눕니다`;
          if (contentInput) {
            contentInput.value = `안녕하세요! 제가 빚어낸 시화집 '${shareProjName}' 갤러리를 소통방에 공유합니다.\n낭송과 노래도 들어보시고, 시어의 결이나 조판 여백에 대해 따뜻한 소감과 조언 부탁드립니다.\n\n🔗 갤러리 주소: ${shareGalleryUrl}`;
          }
        }
      }, 500);
    }
  } catch (e) { }
}

export function openInquiryModal() {
  const modal = document.getElementById("inquiryModal");
  if (!modal) return;

  // 현재 사용자 정보 자동 채우기 (로그인 시)
  const user = window.currentUser || null;
  const nameInput = document.getElementById("inquiryAuthorName");
  const emailInput = document.getElementById("inquiryAuthorEmail");

  if (nameInput && !nameInput.value) {
    nameInput.value = user?.display_name || user?.name || "";
  }
  if (emailInput && !emailInput.value) {
    emailInput.value = user?.email || "";
  }

  // 기본 탭: 새로운 상담 폼
  switchInquiryTab("new");

  modal.style.display = "flex";
}

export function closeInquiryModal() {
  const modal = document.getElementById("inquiryModal");
  if (modal) {
    modal.style.display = "none";
  }
}

export function switchInquiryTab(tab) {
  const btnNew = document.getElementById("tabBtnNewInquiry");
  const btnMy = document.getElementById("tabBtnMyInquiries");
  const paneForm = document.getElementById("inquiryFormPane");
  const paneAiResult = document.getElementById("inquiryAiResultPane");
  const paneList = document.getElementById("inquiryMyListPane");

  if (!btnNew || !btnMy || !paneForm || !paneList) return;

  if (tab === "new") {
    btnNew.style.background = "#FCFAF6";
    btnNew.style.color = "#8B4513";
    btnNew.style.borderBottom = "2px solid #8B4513";
    btnNew.style.fontWeight = "700";

    btnMy.style.background = "none";
    btnMy.style.color = "#7A695A";
    btnMy.style.borderBottom = "2px solid transparent";
    btnMy.style.fontWeight = "600";

    // 직전 상담 결과가 있으면 결과를, 없으면 작성 폼을 표시
    if (currentActiveInquiry && currentActiveInquiry.ai_reply) {
      if (paneAiResult) paneAiResult.style.display = "block";
      paneForm.style.display = "none";
    } else {
      if (paneAiResult) paneAiResult.style.display = "none";
      paneForm.style.display = "block";
    }
    paneList.style.display = "none";
  } else {
    btnMy.style.background = "#FCFAF6";
    btnMy.style.color = "#8B4513";
    btnMy.style.borderBottom = "2px solid #8B4513";
    btnMy.style.fontWeight = "700";

    btnNew.style.background = "none";
    btnNew.style.color = "#7A695A";
    btnNew.style.borderBottom = "2px solid transparent";
    btnNew.style.fontWeight = "600";

    paneForm.style.display = "none";
    if (paneAiResult) paneAiResult.style.display = "none";
    paneList.style.display = "block";

    loadMyInquiries();
  }
}

export function resetInquiryFormToNew() {
  currentActiveInquiry = null;
  const paneForm = document.getElementById("inquiryFormPane");
  const paneAiResult = document.getElementById("inquiryAiResultPane");
  if (paneAiResult) paneAiResult.style.display = "none";
  if (paneForm) paneForm.style.display = "block";

  const form = document.getElementById("formSubmitInquiry");
  if (form) form.reset();

  // 사용자 정보 재입력
  const user = window.currentUser || null;
  const nameInput = document.getElementById("inquiryAuthorName");
  const emailInput = document.getElementById("inquiryAuthorEmail");
  if (nameInput && user) nameInput.value = user.display_name || user.name || "";
  if (emailInput && user) emailInput.value = user.email || "";
}

export async function handleInquirySubmit(event) {
  if (event) event.preventDefault();

  const category = document.getElementById("inquiryCategory")?.value || "coaching";
  const authorName = document.getElementById("inquiryAuthorName")?.value || "";
  const authorEmail = document.getElementById("inquiryAuthorEmail")?.value || "";
  const title = document.getElementById("inquiryTitle")?.value || "";
  const content = document.getElementById("inquiryContent")?.value || "";

  const attachRadio = document.querySelector('input[name="attachOption"]:checked');
  const attachType = attachRadio ? attachRadio.value : "full_zip";

  if (!title.trim() || !content.trim()) {
    if (window.Swal) {
      Swal.fire({ icon: "warning", title: "입력 확인", text: "상담 제목과 내용을 입력해주세요." });
    } else {
      alert("상담 제목과 내용을 입력해주세요.");
    }
    return;
  }

  const btnSubmit = document.getElementById("btnSubmitInquiry");
  const originalHtml = btnSubmit ? btnSubmit.innerHTML : "";
  if (btnSubmit) {
    btnSubmit.disabled = true;
    btnSubmit.innerHTML = "<span>🤖 AI 안실장이 시집을 진단하고 처방 중...</span>";
  }

  try {
    const formData = new FormData();
    formData.append("category", category);
    formData.append("author_name", authorName);
    formData.append("author_email", authorEmail);
    formData.append("title", title);
    formData.append("content", content);
    formData.append("attach_type", attachType);

    const res = await fetch("/api/inquiries/submit", {
      method: "POST",
      body: formData
    });

    const data = await res.json();
    if (res.ok && data.success) {
      currentActiveInquiry = {
        inquiry_id: data.inquiry_id,
        category: category,
        title: title,
        content: content,
        ai_reply: data.ai_reply || "AI 안실장의 코칭 준비 중입니다.",
        coach_name: data.coach_name || "AI 안실장",
        answered_at: "방금 전"
      };

      // AI 안실장 즉시 처방 카드 렌더링
      renderAiCoachingResult(currentActiveInquiry);

    } else {
      throw new Error(data.detail || "접수에 실패했습니다.");
    }
  } catch (err) {
    console.error("Inquiry submit error:", err);
    if (window.Swal) {
      Swal.fire({ icon: "error", title: "접수 오류", text: err.message });
    } else {
      alert("오류: " + err.message);
    }
  } finally {
    if (btnSubmit) {
      btnSubmit.disabled = false;
      btnSubmit.innerHTML = originalHtml;
    }
  }
}

function renderAiCoachingResult(inq) {
  const paneForm = document.getElementById("inquiryFormPane");
  const paneResult = document.getElementById("inquiryAiResultPane");
  if (!paneResult) return;

  const titleEl = document.getElementById("aiResultTitle");
  const badgeCatEl = document.getElementById("aiResultCategoryBadge");
  const badgeIdEl = document.getElementById("aiResultIdBadge");
  const timeEl = document.getElementById("aiResultAnsweredAt");
  const contentEl = document.getElementById("aiResultContent");

  if (titleEl) titleEl.textContent = inq.title;
  if (badgeIdEl) badgeIdEl.textContent = inq.inquiry_id;
  if (timeEl) timeEl.textContent = inq.answered_at || "방금 전";

  const categoryLabels = {
    coaching: "🎨 시화집 편집 및 조판 코칭",
    bug: "🐞 버그 및 기술 오류",
    feature: "💡 기능 제안",
    publishing: "📖 독립출판 상담",
    general: "☕ 일반 문의"
  };
  if (badgeCatEl) badgeCatEl.textContent = categoryLabels[inq.category] || "🎨 출판 코칭";

  if (contentEl) {
    contentEl.textContent = inq.ai_reply;
  }

  // 후속 질문 폼 닫기
  cancelInquiryFollowup();

  // 화면 전환
  if (paneForm) paneForm.style.display = "none";
  paneResult.style.display = "block";

  // 스크롤 상단으로
  const modalBody = paneResult.closest(".modal-body");
  if (modalBody) modalBody.scrollTop = 0;
}

export function toggleInquiryFollowupBox() {
  const box = document.getElementById("inquiryFollowupBox");
  if (!box) return;
  const isHidden = box.style.display === "none" || !box.style.display;
  box.style.display = isHidden ? "block" : "none";
  if (isHidden) {
    const input = document.getElementById("inputInquiryFollowup");
    if (input) input.focus();
  }
}

export function cancelInquiryFollowup() {
  const box = document.getElementById("inquiryFollowupBox");
  const input = document.getElementById("inputInquiryFollowup");
  if (box) box.style.display = "none";
  if (input) input.value = "";
}

export async function submitInquiryFollowup() {
  if (!currentActiveInquiry || !currentActiveInquiry.inquiry_id) {
    alert("상담 정보를 찾을 수 없습니다.");
    return;
  }

  const input = document.getElementById("inputInquiryFollowup");
  const question = input ? input.value.trim() : "";
  if (!question) {
    alert("추가로 궁금하신 내용을 적어주세요.");
    return;
  }

  const btnSubmit = document.getElementById("btnSubmitFollowup");
  const originalHtml = btnSubmit ? btnSubmit.innerHTML : "";
  if (btnSubmit) {
    btnSubmit.disabled = true;
    btnSubmit.innerHTML = "<span>⏳ 안실장 생각 중...</span>";
  }

  try {
    const res = await fetch("/api/inquiries/ask_followup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        inquiry_id: currentActiveInquiry.inquiry_id,
        followup_content: question
      })
    });

    const data = await res.json();
    if (res.ok && data.success) {
      const contentEl = document.getElementById("aiResultContent");
      if (contentEl) {
        if (data.combined_reply) {
          contentEl.textContent = data.combined_reply;
        } else {
          contentEl.textContent += `\n\n───────────────────\n[💬 작가님의 추가 질문]\n${question}\n\n[🤖 AI 안실장의 추가 답변]\n${data.ai_reply || ""}`;
        }
      }
      currentActiveInquiry.ai_reply = contentEl ? contentEl.textContent : "";
      cancelInquiryFollowup();

      if (window.Swal) {
        Swal.fire({
          icon: "success",
          title: "추가 답변 완료",
          text: "AI 안실장의 추가 조언이 반영되었습니다.",
          timer: 1500,
          showConfirmButton: false
        });
      }
    } else {
      throw new Error(data.detail || "추가 답변 생성에 실패했습니다.");
    }
  } catch (err) {
    console.error("Followup error:", err);
    alert("오류: " + err.message);
  } finally {
    if (btnSubmit) {
      btnSubmit.disabled = false;
      btnSubmit.innerHTML = originalHtml;
    }
  }
}

export async function handleInquiryResolveAction(inquiryId = null) {
  const targetId = inquiryId || currentActiveInquiry?.inquiry_id;
  if (!targetId) {
    alert("상담 정보를 찾을 수 없습니다.");
    return;
  }

  try {
    const res = await fetch("/api/inquiries/resolve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        inquiry_id: targetId,
        satisfaction: 5
      })
    });

    const data = await res.json();
    if (res.ok && data.success) {
      if (window.Swal) {
        await Swal.fire({
          icon: "success",
          title: "🌸 시원하게 해결되었습니다!",
          html: `<div style="line-height: 1.6; color: #4A3E33;">
                  궁금증이 해결되어 정말 기쁩니다!<br>
                  AI 안실장이 언제나 작가님의 아름다운 시화집 완성을 응원하겠습니다.
                 </div>`,
          confirmButtonColor: "#2E7D32"
        });
      } else {
        alert("궁금증이 해결되어 기쁩니다! 언제든 편히 찾아주세요.");
      }

      currentActiveInquiry = null;
      closeInquiryModal();
      loadMyInquiries();
    } else {
      throw new Error(data.detail || "처리에 실패했습니다.");
    }
  } catch (err) {
    console.error("Resolve error:", err);
    alert("오류: " + err.message);
  }
}

export async function handleInquiryEscalateAction(inquiryId = null) {
  const targetId = inquiryId || currentActiveInquiry?.inquiry_id;
  if (!targetId) {
    alert("상담 정보를 찾을 수 없습니다.");
    return;
  }

  let proceed = true;
  if (window.Swal) {
    const result = await Swal.fire({
      icon: "question",
      title: "대표님께 직접 검토를 요청할까요?",
      html: `<div style="text-align: left; font-size: 0.9rem; line-height: 1.6; color: #4A3E33;">
              AI 안실장의 답변으로 부족하시거나, 조판 및 인쇄용 정밀 검토가 필요하신가요?<br><br>
              <strong>[확인]</strong>을 누르시면 작업 중인 시집 데이터와 함께 <strong>대표님(인간 작가)의 관리자 검토 대기열</strong>로 안전하게 전달됩니다.
             </div>`,
      showCancelButton: true,
      confirmButtonText: "네, 대표님께 요청합니다",
      cancelButtonText: "취소",
      confirmButtonColor: "#8B4513"
    });
    proceed = result.isConfirmed;
  } else {
    proceed = confirm("대표님께 직접 검토를 요청하시겠습니까?");
  }

  if (!proceed) return;

  try {
    const res = await fetch("/api/inquiries/escalate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        inquiry_id: targetId
      })
    });

    const data = await res.json();
    if (res.ok && data.success) {
      if (window.Swal) {
        await Swal.fire({
          icon: "success",
          title: "대표님 직접 검토 접수 완료",
          html: `<div style="line-height: 1.6; color: #4A3E33;">
                  대표님께 시집 데이터와 함께 안전하게 전달되었습니다.<br>
                  정성껏 확인 후 이메일 및 [내 문의 내역] 탭을 통해 피드백을 드리겠습니다.
                 </div>`,
          confirmButtonColor: "#8B4513"
        });
      } else {
        alert(data.message);
      }

      currentActiveInquiry = null;
      switchInquiryTab("my");
    } else {
      throw new Error(data.detail || "검토 요청 처리에 실패했습니다.");
    }
  } catch (err) {
    console.error("Escalate error:", err);
    alert("오류: " + err.message);
  }
}

export async function loadMyInquiries() {
  const container = document.getElementById("myInquiriesContainer");
  if (!container) return;

  container.innerHTML = `<div style="text-align: center; padding: 24px; color: #8C827A; font-size: 0.88rem;">내 문의 내역을 불러오는 중...</div>`;

  try {
    const res = await fetch("/api/inquiries/my");
    const data = await res.json();

    if (!res.ok) throw new Error(data.detail || "불러오기 실패");

    const items = data.inquiries || [];
    if (items.length === 0) {
      container.innerHTML = `
        <div style="text-align: center; padding: 36px 16px; background: #FAF7F2; border-radius: 10px; border: 1px dashed #D9C8B5;">
          <span style="font-size: 2rem;">📭</span>
          <p style="margin: 8px 0 4px; font-weight: 700; color: #5C4B3E; font-size: 0.95rem;">접수된 상담 내역이 없습니다.</p>
          <p style="margin: 0; font-size: 0.82rem; color: #8C7D70;">시화집 창작이나 조판 중 궁금한 점이 있으시면 언제든 1:1 상담을 요청하세요.</p>
        </div>
      `;
      return;
    }

    container.innerHTML = items.map(item => {
      let statusBadge = "";
      if (item.status === "resolved") {
        statusBadge = `<span style="background: #E8F5E9; color: #2E7D32; border: 1px solid #A5D6A7; font-size: 0.76rem; font-weight: 700; padding: 2px 8px; border-radius: 12px;">✅ 해결 완료</span>`;
      } else if (item.status === "escalated") {
        statusBadge = `<span style="background: #FFF8E1; color: #B78103; border: 1px solid #FFE082; font-size: 0.76rem; font-weight: 700; padding: 2px 8px; border-radius: 12px;">👤 대표님 검토 대기</span>`;
      } else if (item.status === "answered") {
        statusBadge = `<span style="background: #E3F2FD; color: #1565C0; border: 1px solid #90CAF9; font-size: 0.76rem; font-weight: 700; padding: 2px 8px; border-radius: 12px;">💬 작가 답변 완료</span>`;
      } else if (item.ai_reply) {
        statusBadge = `<span style="background: #F3E5F5; color: #7B1FA2; border: 1px solid #CE93D8; font-size: 0.76rem; font-weight: 700; padding: 2px 8px; border-radius: 12px;">🤖 안실장 처방 완료</span>`;
      } else {
        statusBadge = `<span style="background: #FFF3E0; color: #E65100; border: 1px solid #FFCC80; font-size: 0.76rem; font-weight: 700; padding: 2px 8px; border-radius: 12px;">⏳ 접수됨</span>`;
      }

      const attachBadge = item.attachment_filename
        ? `<span style="font-size: 0.76rem; color: #6D5B4D; background: #EFEBE4; padding: 2px 6px; border-radius: 4px;">📎 ${escapeHtml(item.attachment_filename)}</span>`
        : "";

      // AI 안실장 답변 카드
      const aiReplyBox = item.ai_reply
        ? `
          <div style="margin-top: 10px; background: #FAF6F0; border: 1px solid #E5D7C5; border-radius: 8px; padding: 10px 12px;">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px;">
              <strong style="color: #6D4C41; font-size: 0.82rem;">🤖 AI 안실장의 즉시 처방</strong>
              <span style="font-size: 0.72rem; color: #9E8E80;">${escapeHtml(item.ai_answered_at || "")}</span>
            </div>
            <div style="font-size: 0.84rem; color: #3E3024; line-height: 1.6; white-space: pre-wrap;">${escapeHtml(item.ai_reply)}</div>
          </div>
        `
        : "";

      // 대표님 직접 답변 카드
      const humanReplyBox = item.reply_content
        ? `
          <div style="margin-top: 10px; background: #F1F8F1; border: 1.5px solid #C8E6C9; border-radius: 8px; padding: 12px 14px;">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px;">
              <strong style="color: #2E7D32; font-size: 0.84rem;">👤 대표님(작가)의 직접 피드백</strong>
              <span style="font-size: 0.74rem; color: #66BB6A;">${escapeHtml(item.answered_at || "")}</span>
            </div>
            <div style="font-size: 0.86rem; color: #1B5E20; line-height: 1.6; white-space: pre-wrap;">${escapeHtml(item.reply_content)}</div>
          </div>
        `
        : "";

      // 하단 액션 버튼 (미해결 시)
      let actionButtons = "";
      if (item.status !== "resolved") {
        actionButtons = `
          <div style="margin-top: 10px; padding-top: 8px; border-top: 1px dashed #EDE0D4; display: flex; justify-content: flex-end; gap: 8px;">
            ${item.status !== "escalated" ? `
              <button type="button" onclick="handleInquiryEscalateAction('${item.id}')" style="padding: 5px 10px; font-size: 0.78rem; background: #FFF8E7; color: #8A5A00; border: 1px solid #FFD54F; border-radius: 6px; cursor: pointer;">
                👤 대표님 직접 검토 요청
              </button>
            ` : ""}
            <button type="button" onclick="handleInquiryResolveAction('${item.id}')" style="padding: 5px 12px; font-size: 0.78rem; background: #2E7D32; color: #FFF; border: none; border-radius: 6px; cursor: pointer;">
              ✨ 해결 완료 처리
            </button>
          </div>
        `;
      }

      return `
        <div style="background: #FFFFFF; border: 1px solid #E5D7C5; border-radius: 10px; padding: 14px 16px; box-shadow: 0 2px 5px rgba(0,0,0,0.03);">
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px;">
            <div style="display: flex; align-items: center; gap: 8px;">
              ${statusBadge}
              <span style="font-size: 0.8rem; color: #8C7D70; font-weight: 600;">${escapeHtml(item.category_label || "")}</span>
            </div>
            <span style="font-size: 0.76rem; color: #9E9185;">${escapeHtml(item.created_at || "")}</span>
          </div>

          <h4 style="margin: 6px 0; font-size: 0.95rem; font-weight: 700; color: #33261C;">${escapeHtml(item.title)}</h4>
          <p style="margin: 0; font-size: 0.86rem; color: #55473C; line-height: 1.55; white-space: pre-wrap;">${escapeHtml(item.content)}</p>

          <div style="margin-top: 8px; display: flex; align-items: center; justify-content: space-between;">
            ${attachBadge}
          </div>

          ${aiReplyBox}
          ${humanReplyBox}
          ${actionButtons}
        </div>
      `;
    }).join("");

  } catch (err) {
    container.innerHTML = `<div style="text-align: center; padding: 24px; color: #C0392B; font-size: 0.88rem;">불러오기 오류: ${escapeHtml(err.message)}</div>`;
  }
}

function escapeHtml(text) {
  if (!text) return "";
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
