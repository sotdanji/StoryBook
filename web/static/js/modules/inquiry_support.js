/**
 * web/static/js/modules/inquiry_support.js
 * StoryBook Studio - 1:1 비밀 상담 & 출판 편집 코칭 모달 제어 모듈
 */

export function initInquirySupport() {
  window.openInquiryModal = openInquiryModal;
  window.closeInquiryModal = closeInquiryModal;
  window.switchInquiryTab = switchInquiryTab;
  window.handleInquirySubmit = handleInquirySubmit;
  window.loadMyInquiries = loadMyInquiries;

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
  } catch (e) {}
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

    paneForm.style.display = "block";
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
    paneList.style.display = "block";

    loadMyInquiries();
  }
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
    btnSubmit.innerHTML = "<span>⏳ 시집 압축 및 접수 중...</span>";
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
      if (window.Swal) {
        await Swal.fire({
          icon: "success",
          title: "비밀 상담 접수 완료!",
          html: `<div style="text-align: left; font-size: 0.9rem; line-height: 1.6; color: #444;">
                  ${data.message}<br><br>
                  • <strong>접수 번호</strong>: <code style="color: #8B4513;">${data.inquiry_id}</code><br>
                  • 작가님이 검토 후 작성해주신 코칭 피드백은 <strong>이메일</strong> 및 상단의 <strong>[내 문의 내역 및 작가 답변]</strong> 탭에서 확인하실 수 있습니다.
                 </div>`,
          confirmButtonColor: "#8B4513"
        });
      } else {
        alert(data.message);
      }

      // 폼 초기화 후 내역 탭으로 전환
      document.getElementById("formSubmitInquiry")?.reset();
      switchInquiryTab("my");
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
      const isAnswered = item.status === "answered";
      const statusBadge = isAnswered 
        ? `<span style="background: #E8F5E9; color: #2E7D32; border: 1px solid #A5D6A7; font-size: 0.76rem; font-weight: 700; padding: 2px 8px; border-radius: 12px;">✅ 답변 완료</span>`
        : `<span style="background: #FFF3E0; color: #E65100; border: 1px solid #FFCC80; font-size: 0.76rem; font-weight: 700; padding: 2px 8px; border-radius: 12px;">⏳ 검토 중 (접수됨)</span>`;

      const attachBadge = item.attachment_filename
        ? `<span style="font-size: 0.76rem; color: #6D5B4D; background: #EFEBE4; padding: 2px 6px; border-radius: 4px;">📎 ${item.attachment_filename}</span>`
        : "";

      const replyBox = isAnswered && item.reply_content
        ? `
          <div style="margin-top: 12px; background: #F1F8F1; border: 1.5px solid #C8E6C9; border-radius: 8px; padding: 12px 14px;">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px;">
              <strong style="color: #2E7D32; font-size: 0.86rem;">💬 작가님의 코칭 답변 & 피드백</strong>
              <span style="font-size: 0.75rem; color: #66BB6A;">${item.answered_at || ""}</span>
            </div>
            <div style="font-size: 0.86rem; color: #2C3E50; line-height: 1.6; white-space: pre-wrap;">${escapeHtml(item.reply_content)}</div>
          </div>
        `
        : `
          <div style="margin-top: 10px; font-size: 0.8rem; color: #A68B75; font-style: italic;">
            작가님이 회원님의 시집과 사연을 확인하고 있습니다. 정성껏 검토 후 답변을 남겨드립니다.
          </div>
        `;

      return `
        <div style="background: #FFFFFF; border: 1px solid #E5D7C5; border-radius: 10px; padding: 14px 16px; box-shadow: 0 2px 5px rgba(0,0,0,0.03);">
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px;">
            <div style="display: flex; align-items: center; gap: 8px;">
              ${statusBadge}
              <span style="font-size: 0.8rem; color: #8C7D70; font-weight: 600;">${item.category_label || ""}</span>
            </div>
            <span style="font-size: 0.76rem; color: #9E9185;">${item.created_at || ""}</span>
          </div>

          <h4 style="margin: 6px 0; font-size: 0.95rem; font-weight: 700; color: #33261C;">${escapeHtml(item.title)}</h4>
          <p style="margin: 0; font-size: 0.86rem; color: #55473C; line-height: 1.55; white-space: pre-wrap;">${escapeHtml(item.content)}</p>

          <div style="margin-top: 8px; display: flex; align-items: center; justify-content: space-between;">
            ${attachBadge}
          </div>

          ${replyBox}
        </div>
      `;
    }).join("");

  } catch (err) {
    container.innerHTML = `<div style="text-align: center; padding: 24px; color: #C0392B; font-size: 0.88rem;">불러오기 오류: ${err.message}</div>`;
  }
}

function escapeHtml(text) {
  if (!text) return "";
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

