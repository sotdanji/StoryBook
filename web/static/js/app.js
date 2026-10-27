// StoryBook Studio Frontend Application Logic (Multi-Project Edition)
window.name = "StoryBookStudio";

let currentStatus = null;
let currentDrafts = null;
let currentWorkIndex = 0;
let projectList = [];
let currentEditingEpisode = null; // 현재 편집 중인 회차 (null이면 신규 작성)

// ============================================================================
// ⏳ [신규] 글로벌 비지/생성 대기 상태 관리자 (모래시계 & 원형 회전 스피너 커서)
// ============================================================================
let globalBusyCount = 0;
let busyIndicatorElem = null;
let lastMouseX = -100;
let lastMouseY = -100;
let busyDebounceTimer = null;

function initBusyCursorIndicator() {
  if (busyIndicatorElem) return;
  busyIndicatorElem = document.createElement("div");
  busyIndicatorElem.id = "appBusyCursorIndicator";
  busyIndicatorElem.innerHTML = `
    <span class="cursor-hourglass-icon">⏳</span>
    <span class="cursor-spinner-ring"></span>
    <span id="appBusyCursorLabel" style="font-size: 11px; letter-spacing: -0.3px;">처리 중...</span>
  `;
  document.body.appendChild(busyIndicatorElem);

  // 마우스 위치 실시간 추적 (커서 오른쪽 아래에 부드럽게 위치)
  window.addEventListener("mousemove", (e) => {
    lastMouseX = e.clientX;
    lastMouseY = e.clientY;
    if (busyIndicatorElem) {
      busyIndicatorElem.style.left = `${lastMouseX}px`;
      busyIndicatorElem.style.top = `${lastMouseY}px`;
    }
  }, { passive: true });
}

function setAppBusy(busy, label = "생성 및 처리 중...") {
  if (!busyIndicatorElem && document.body) {
    initBusyCursorIndicator();
  }

  if (busy) {
    globalBusyCount++;
    if (globalBusyCount === 1) {
      // 40ms 이상 소요되는 요청 시 표시 (불필요한 미세 깜빡임 방지)
      if (busyDebounceTimer) clearTimeout(busyDebounceTimer);
      busyDebounceTimer = setTimeout(() => {
        if (globalBusyCount > 0) {
          document.documentElement.classList.add("is-app-busy");
          document.body.classList.add("is-app-busy");
          if (busyIndicatorElem) {
            const labelElem = document.getElementById("appBusyCursorLabel");
            if (labelElem && label) labelElem.textContent = label;
            busyIndicatorElem.classList.add("visible");
          }
        }
      }, 40);
    }
  } else {
    globalBusyCount = Math.max(0, globalBusyCount - 1);
    if (globalBusyCount === 0) {
      if (busyDebounceTimer) {
        clearTimeout(busyDebounceTimer);
        busyDebounceTimer = null;
      }
      document.documentElement.classList.remove("is-app-busy");
      document.body.classList.remove("is-app-busy");
      if (busyIndicatorElem) {
        busyIndicatorElem.classList.remove("visible");
      }
    }
  }
}
window.setAppBusy = setAppBusy;

// 🌐 전역 fetch 인터셉터: 앱 내의 모든 API 요청(시 생성, 다듬기, 삽화 생성, 노래 생성, 저장 등)에
// 자동으로 모래시계 / 원형 회전 커서 적용
(function wrapGlobalFetchForBusyCursor() {
  const originalFetch = window.fetch;
  window.fetch = async function (...args) {
    const url = typeof args[0] === "string" ? args[0] : (args[0] && args[0].url ? args[0].url : "");
    
    // 상황별 라벨 자동 부여
    let busyLabel = "처리 중...";
    if (url.includes("generate_poem") || url.includes("generate_episodes")) busyLabel = "시 생성 중...";
    else if (url.includes("refine_poem")) busyLabel = "시 다듬는 중...";
    else if (url.includes("generate_illustration") || url.includes("regenerate_illustration")) busyLabel = "삽화 그리는 중...";
    else if (url.includes("generate_music") || url.includes("music")) busyLabel = "노래 작곡 중...";
    else if (url.includes("save_work") || url.includes("save")) busyLabel = "저장 중...";
    else if (url.includes("export") || url.includes("pdf")) busyLabel = "전자책 출판 중...";

    setAppBusy(true, busyLabel);
    try {
      return await originalFetch.apply(this, args);
    } finally {
      setAppBusy(false);
    }
  };
})();

// DOM 준비 완료 시 인디케이터 초기화
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initBusyCursorIndicator);
} else {
  initBusyCursorIndicator();
}

// ✨ 사용자 친화적인 감성 플로팅 토스트 메시지
function showToast(message, type = "success") {
  let toastContainer = document.getElementById("appToastContainer");
  if (!toastContainer) {
    toastContainer = document.createElement("div");
    toastContainer.id = "appToastContainer";
    toastContainer.style.position = "fixed";
    toastContainer.style.top = "24px";
    toastContainer.style.right = "24px";
    toastContainer.style.zIndex = "99999";
    toastContainer.style.display = "flex";
    toastContainer.style.flexDirection = "column";
    toastContainer.style.gap = "8px";
    toastContainer.style.pointerEvents = "none";
    document.body.appendChild(toastContainer);
  }

  const toast = document.createElement("div");
  toast.style.padding = "12px 20px";
  toast.style.borderRadius = "8px";
  toast.style.fontSize = "14.5px";
  toast.style.fontWeight = "600";
  toast.style.color = "#ffffff";
  toast.style.boxShadow = "0 8px 24px rgba(0,0,0,0.2)";
  toast.style.opacity = "0";
  toast.style.transform = "translateY(-10px)";
  toast.style.transition = "all 0.3s cubic-bezier(0.16, 1, 0.3, 1)";
  toast.style.pointerEvents = "auto";
  toast.style.maxWidth = "420px";
  toast.style.lineHeight = "1.5";

  if (type === "success") {
    toast.style.background = "linear-gradient(135deg, #2d6a4f 0%, #1b4332 100%)";
    toast.style.border = "1px solid #40916c";
  } else if (type === "error") {
    toast.style.background = "linear-gradient(135deg, #b91c1c 0%, #991b1b 100%)";
    toast.style.border = "1px solid #ef4444";
  } else {
    toast.style.background = "linear-gradient(135deg, #854d0e 0%, #713f12 100%)";
    toast.style.border = "1px solid #ca8a04";
  }

  toast.innerHTML = message;
  toastContainer.appendChild(toast);

  requestAnimationFrame(() => {
    toast.style.opacity = "1";
    toast.style.transform = "translateY(0)";
  });

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(-10px)";
    setTimeout(() => toast.remove(), 300);
  }, 3200);
}

// ✨ 새 작품(새 화) 작성 모드로 폼 초기화
function startNewPoem(skipConfirm = false) {
  if (!skipConfirm) {
    if (!confirm("새로운 작품을 작성하시겠습니까?\n작성 중인 내용이 정리되고 다음 회차(신규 화)로 준비됩니다.")) {
      return;
    }
  }
  currentEditingEpisode = null;
  document.getElementById("inputCoreMemory").value = "";
  document.getElementById("inputSensoryDetails").value = "";
  document.getElementById("inputSpokenWords").value = "";
  document.getElementById("inputFinalTitle").value = "";
  if (document.getElementById("inputFinalAuthor")) document.getElementById("inputFinalAuthor").value = "";
  document.getElementById("inputFinalPoem").value = "";
  
  const previewArea = document.getElementById("studioImagePreviewArea");
  if (previewArea) previewArea.style.display = "none";
  const genStatus = document.getElementById("studioGenStatus");
  if (genStatus) genStatus.style.display = "none";
  const upStatus = document.getElementById("studioUploadStatus");
  if (upStatus) upStatus.style.display = "none";
  const guideInput = document.getElementById("inputArtCustomGuide");
  if (guideInput) guideInput.value = "";

  if (typeof removeAudioFile === 'function') removeAudioFile();
  const lyricsInput = document.getElementById("musicLyricsInput");
  if (lyricsInput) lyricsInput.value = "";

  if (currentStatus && currentStatus.next_episode) {
    document.getElementById("inputEpisode").value = currentStatus.next_episode;
  }

  // 드롭다운 및 배지 업데이트
  const selBox = document.getElementById("selectWorkToEdit");
  if (selBox) selBox.value = "new";
  const epBadge = document.getElementById("labelCurrentEditingEpBadge");
  if (epBadge) epBadge.textContent = "[신규 작품 집필]";
  const btnDel = document.getElementById("btnDeleteCurrentWork");
  if (btnDel) btnDel.style.display = "none";
}

// 📖 기존 저장된 시 편집창 불러오기 드롭다운 갱신
function updateWorkToEditDropdown() {
  const selBox = document.getElementById("selectWorkToEdit");
  if (!selBox) return;

  selBox.innerHTML = "";

  const works = (currentStatus && currentStatus.works) ? currentStatus.works : [];

  // 옵션 1: 신규 작품 집필
  const optNew = document.createElement("option");
  optNew.value = "new";
  const nextEp = (currentStatus && currentStatus.next_episode) ? currentStatus.next_episode : "신규";
  optNew.textContent = `✨ [새 작품 집필] (다음 ${nextEp} 작성)`;
  selBox.appendChild(optNew);

  // 옵션 2~N: 기존 저장된 회차별 시
  works.forEach(w => {
    const opt = document.createElement("option");
    opt.value = w.episode_no;
    const chapTag = w.chapter ? `[${w.chapter}] ` : '';
    opt.textContent = `📖 ${chapTag}[${w.episode_no}] ${w.title}`;
    selBox.appendChild(opt);
  });

  // 현재 편집 중인 회차가 있으면 드롭다운 및 배지 동기화
  const epBadge = document.getElementById("labelCurrentEditingEpBadge");
  const btnDel = document.getElementById("btnDeleteCurrentWork");

  if (currentEditingEpisode) {
    const exists = works.some(w => w.episode_no === currentEditingEpisode);
    if (exists) {
      selBox.value = currentEditingEpisode;
      if (epBadge) epBadge.textContent = `[${currentEditingEpisode} 편집 중]`;
      if (btnDel) btnDel.style.display = "inline-flex";
    } else {
      selBox.value = "new";
      if (epBadge) epBadge.textContent = "[신규 작품 집필]";
      if (btnDel) btnDel.style.display = "none";
    }
  } else {
    selBox.value = "new";
    if (epBadge) epBadge.textContent = "[신규 작품 집필]";
    if (btnDel) btnDel.style.display = "none";
  }
}

// 📖 회차 선택 드롭다운 변경 시 해당 시를 편집창으로 로드
function onSelectWorkToEditChange(val) {
  if (!val || val === "new") {
    startNewPoem(true);
  } else {
    loadWorkIntoEditor(val);
  }
}

// 📖 지정된 회차의 시를 편집창(제목/본문/기억/삽화/노래)으로 로드
function loadWorkIntoEditor(episodeNo) {
  const works = (currentStatus && currentStatus.works) ? currentStatus.works : [];
  const work = works.find(w => w.episode_no === episodeNo);
  if (!work) return;

  currentEditingEpisode = work.episode_no;
  document.getElementById("inputEpisode").value = work.episode_no;

  // 제목 및 시 본문
  const inputTitle = document.getElementById("inputFinalTitle");
  if (inputTitle) inputTitle.value = work.title || "";
  const inputAuthor = document.getElementById("inputFinalAuthor");
  if (inputAuthor) inputAuthor.value = work.author || "";
  const inputPoem = document.getElementById("inputFinalPoem");
  if (inputPoem) {
    inputPoem.value = work.poem_body || "";
    inputPoem.dispatchEvent(new Event("input", { bubbles: true }));
  }

  // 기억 정보 로드 (비정상 메타데이터 태그 방어 필터링)
  let cleanMemory = work.memory_anchor || "";
  if (cleanMemory.startsWith("- **") || cleanMemory.includes("images/")) {
    cleanMemory = "";
  }
  const memInput = document.getElementById("inputCoreMemory");
  if (memInput) memInput.value = cleanMemory;
  const factLock = document.getElementById("factLockText");
  if (factLock) {
    factLock.textContent = cleanMemory 
      ? `기억의 중심: ${cleanMemory}` 
      : `[${work.episode_no}] 「${work.title}」 원고를 편집창으로 불러왔습니다.`;
  }

  const guideInput = document.getElementById("inputArtCustomGuide");
  if (guideInput) guideInput.value = "";

  const promptDisplay = document.getElementById("imagePromptDisplay");
  if (promptDisplay) {
    promptDisplay.value = "";
    promptDisplay.placeholder = `[${work.episode_no} 「${work.title}」] 삽화 프롬프트를 빚는 중이거나 단 1장 생성을 누르면 AI가 본문을 분석하여 자동 생성합니다...`;
  }

  // 배지 및 드롭다운 동기화, 삭제 버튼 노출
  const epBadge = document.getElementById("labelCurrentEditingEpBadge");
  if (epBadge) epBadge.textContent = `[${work.episode_no} 편집 중]`;
  const btnDel = document.getElementById("btnDeleteCurrentWork");
  if (btnDel) btnDel.style.display = "inline-flex";

  const selBox = document.getElementById("selectWorkToEdit");
  if (selBox) selBox.value = work.episode_no;

  // 우측 스튜디오 이미지(삽화) 미리보기 로드
  const previewArea = document.getElementById("studioImagePreviewArea");
  const previewImg = document.getElementById("studioPreviewImg");
  const previewFilename = document.getElementById("studioPreviewFilename");
  if (work.image_file) {
    const cleanImgPath = "/" + work.image_file.replace(/^(\.\/|\/)/, '');
    if (previewArea) previewArea.style.display = "flex";
    const tag = document.getElementById("studioPreviewTag");
    if (previewImg) {
      previewImg.onerror = () => {
        previewImg.style.display = "none";
        const fallback = previewImg.nextElementSibling;
        if (fallback) fallback.style.display = "flex";
        if (tag) {
          tag.textContent = "⏳ 삽화 파일 없음 (생성 또는 사진 등록 필요)";
          tag.style.color = "#c05621";
        }
      };
      previewImg.onload = () => {
        previewImg.style.display = "block";
        const fallback = previewImg.nextElementSibling;
        if (fallback) fallback.style.display = "none";
        if (tag) {
          tag.textContent = "✓ 삽화 적용 완료";
          tag.style.color = "var(--accent-green)";
        }
      };
      previewImg.src = `${cleanImgPath}?t=${Date.now()}`;
    }
    if (previewFilename) previewFilename.textContent = work.image_file.split('/').pop();
  } else {
    if (previewArea) previewArea.style.display = "none";
    if (previewImg) previewImg.src = "";
  }

  // 노래 가사 및 오디오 음원 로드
  const lyricsInput = document.getElementById("musicLyricsInput");
  if (lyricsInput) lyricsInput.value = work.lyrics || "";

  const proj = (currentStatus && currentStatus.project) ? currentStatus.project : null;
  const safeName = (proj && proj.name) ? proj.name.replace(/\s+/g, '_') : "노을빛_기억";

  // 1) 시인의 육성 낭송 음원 로드
  let rawRecite = work.recite_file || "";
  let rawMusic = work.music_file || "";
  // 하위 호환: 기존 audio_file만 있는 경우
  if (!rawRecite && !rawMusic && work.audio_file) {
    if (work.audio_file.includes("낭송") || work.audio_file.endsWith(".webm")) {
      rawRecite = work.audio_file;
    } else {
      rawMusic = work.audio_file;
    }
  }

  currentReciteFile = rawRecite;
  currentMusicFile = rawMusic;
  currentAudioFile = rawMusic || rawRecite || "";

  const recitePreviewArea = document.getElementById("studioRecitePreviewArea");
  const recitePlayer = document.getElementById("studioRecitePlayer");
  const reciteNameElem = document.getElementById("studioPreviewReciteFilename");

  if (rawRecite) {
    const reciteUrl = (rawRecite.startsWith("http") || rawRecite.startsWith("/"))
      ? rawRecite
      : `/projects/${safeName}/${rawRecite.replace(/^\.?\//, '')}`;
    if (reciteNameElem) reciteNameElem.textContent = rawRecite.split("/").pop();
    if (recitePlayer) {
      recitePlayer.src = reciteUrl;
      recitePlayer.load();
    }
    if (recitePreviewArea) recitePreviewArea.style.display = "block";
  } else {
    if (typeof removeReciteFile === 'function') removeReciteFile();
  }

  // 2) 서정 노래 음원 로드
  const audioPreviewArea = document.getElementById("studioAudioPreviewArea");
  const audioPlayer = document.getElementById("studioAudioPlayer");
  const audioNameElem = document.getElementById("studioPreviewAudioFilename");

  if (rawMusic) {
    const musicUrl = (rawMusic.startsWith("http") || rawMusic.startsWith("/"))
      ? rawMusic
      : `/projects/${safeName}/${rawMusic.replace(/^\.?\//, '')}`;
    if (audioNameElem) audioNameElem.textContent = rawMusic.split("/").pop();
    if (audioPlayer) {
      audioPlayer.src = musicUrl;
      audioPlayer.load();
    }
    if (audioPreviewArea) audioPreviewArea.style.display = "block";
  } else {
    if (typeof removeAudioFile === 'function') removeAudioFile();
  }

  // 시각적 강조 피드백
  if (inputTitle) {
    inputTitle.style.transition = "background-color 0.3s ease";
    inputTitle.style.backgroundColor = "#FFF9F0";
    setTimeout(() => { inputTitle.style.backgroundColor = ""; }, 400);
  }
}

// 📖 편집 대상 이전/다음 회차 이동 네비게이션
function navigateEditWork(delta) {
  const works = (currentStatus && currentStatus.works) ? currentStatus.works : [];
  if (works.length === 0) {
    alert("편집할 수 있는 기존 작품이 아직 없습니다.");
    return;
  }

  let curIdx = -1;
  if (currentEditingEpisode) {
    curIdx = works.findIndex(w => w.episode_no === currentEditingEpisode);
  }

  let nextIdx;
  if (curIdx === -1) {
    // 신규 작성 상태에서 이전(◀)을 누르면 마지막 작품으로, 다음(▶)을 누르면 첫 작품으로
    nextIdx = (delta < 0) ? (works.length - 1) : 0;
  } else {
    nextIdx = curIdx + delta;
    if (nextIdx < 0) {
      alert("첫 번째 작품입니다.");
      return;
    }
    if (nextIdx >= works.length) {
      // 마지막 작품 다음이면 신규 작품 모드로 안내
      if (confirm("마지막 작품입니다. 신규 작품 작성 모드로 전환하시겠습니까?")) {
        startNewPoem(true);
      }
      return;
    }
  }

  loadWorkIntoEditor(works[nextIdx].episode_no);
}

// 🗑️ 현재 편집 중인 시 원고에서 삭제 - 확인 전용 커스텀 모달 열기
function openDeleteConfirmModal(event) {
  if (event) {
    event.preventDefault();
    event.stopPropagation();
  }

  if (!currentEditingEpisode) {
    alert("현재 삭제할 기존 작품이 선택되어 있지 않습니다.\n(새 작품 집필 중에는 삭제할 수 없습니다.)");
    return;
  }

  const title = document.getElementById("inputFinalTitle").value.trim() || "무제";
  const titleElem = document.getElementById("deleteConfirmMsgTitle");
  if (titleElem) {
    titleElem.textContent = `[${currentEditingEpisode}] 「${title}」`;
  }

  const modal = document.getElementById("deleteConfirmModal");
  if (modal) {
    modal.style.display = "flex";
  }
}

// 🗑️ 삭제 확인 모달 닫기
function closeDeleteConfirmModal() {
  const modal = document.getElementById("deleteConfirmModal");
  if (modal) {
    modal.style.display = "none";
  }
}

// 🗑️ 삭제 실행 (모달의 [정말로 삭제하기] 버튼 클릭 시)
async function executeDeleteCurrentWork() {
  if (!currentEditingEpisode) {
    closeDeleteConfirmModal();
    return;
  }

  const title = document.getElementById("inputFinalTitle").value.trim() || "무제";
  const targetEp = currentEditingEpisode;
  const btn = document.getElementById("btnExecuteDeleteWork");
  const origHtml = btn ? btn.innerHTML : "";
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = "<span>⏳ 삭제 처리 중...</span>";
  }

  try {
    const res = await fetch("/api/delete_work", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ episode_no: targetEp })
    });
    const data = await res.json();
    if (res.ok && data.success) {
      closeDeleteConfirmModal();
      alert(`🗑️ [${targetEp}] 「${title}」 작품이 원고에서 성공적으로 삭제되었습니다.`);
      startNewPoem(true);
      await loadProjects();
      await loadStatus();
    } else {
      alert("삭제 실패: " + (data.detail || data.error || "오류가 발생했습니다."));
    }
  } catch (err) {
    alert("삭제 중 네트워크 오류 발생: " + err);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = origHtml;
    }
  }
}

// 기존 deleteCurrentWork도 openDeleteConfirmModal을 호출하도록 유지
function deleteCurrentWork(event) {
  openDeleteConfirmModal(event);
}

document.addEventListener("DOMContentLoaded", () => {
  bindEvents();
  initCustomTooltips();
  initSidebar();
  initTabs();
  loadProjects();
  loadStatus();
  calculateSpecs();
  initDropzones();
  selectDraft("A");
});

// 0. 사이드바 및 모바일 반응형 제어
function initSidebar() {
  const toggleBtn = document.getElementById("btnSidebarToggle");
  const closeBtn = document.getElementById("btnSidebarClose");
  const backdrop = document.getElementById("sidebarBackdrop");
  const sidebar = document.getElementById("appSidebar");

  if (toggleBtn) {
    toggleBtn.addEventListener("click", () => {
      if (sidebar) sidebar.classList.add("open");
      if (backdrop) backdrop.classList.add("active");
    });
  }

  if (closeBtn) {
    closeBtn.addEventListener("click", closeSidebarMobile);
  }

  if (backdrop) {
    backdrop.addEventListener("click", closeSidebarMobile);
  }
}

function closeSidebarMobile() {
  const sidebar = document.getElementById("appSidebar");
  const backdrop = document.getElementById("sidebarBackdrop");
  if (sidebar) sidebar.classList.remove("open");
  if (backdrop) backdrop.classList.remove("active");
}

// 독자용 시화 갤러리 단일 윈도우 인스턴스 (중복 생성 방지)
let readerGalleryWindow = null;

// 독자용 시화 갤러리 열기 (단일 창 유지 및 포커스)
function openReaderGallery() {
  const proj = (currentStatus && currentStatus.project) ? currentStatus.project : null;
  let targetUrl = "/projects/노을빛_기억/시화집_갤러리.html";
  
  if (proj && proj.name) {
    const safeName = proj.name.replace(/\s+/g, '_');
    targetUrl = `/projects/${safeName}/시화집_갤러리.html`;
  }

  const windowName = "StoryBookReaderGallery";

  // 1. 이미 열린 창이 존재하고 닫히지 않은 경우: 해당 창으로 포커스 이동 및 URL 갱신
  if (readerGalleryWindow && !readerGalleryWindow.closed) {
    try {
      if (readerGalleryWindow.location && readerGalleryWindow.location.pathname !== targetUrl) {
        readerGalleryWindow.location.href = targetUrl;
      }
      readerGalleryWindow.focus();
      return;
    } catch (e) {
      // 크로스 도메인이거나 접근 제한 시 window.open 재사용 진행
    }
  }

  // 2. 창이 없거나 닫힌 경우: 고유 윈도우 이름으로 열기 (브라우저 수준 중복 방지)
  readerGalleryWindow = window.open(targetUrl, windowName);
  if (readerGalleryWindow) {
    readerGalleryWindow.focus();
  }
}

// 시 본문 글자 크기 실시간 조절 (시니어 눈 편안 배려)
let currentPoemFontSize = 1.25; // rem
function adjustPoemFontSize(delta) {
  const textarea = document.getElementById("inputFinalPoem");
  if (!textarea) return;
  currentPoemFontSize = Math.max(0.95, Math.min(2.2, currentPoemFontSize + delta * 0.12));
  textarea.style.setProperty("font-size", `${currentPoemFontSize.toFixed(2)}rem`, "important");
  if (typeof showToast === 'function') {
    showToast(`시 본문 글자 크기: ${(currentPoemFontSize * 16).toFixed(0)}px`, "info");
  }
}

// 1. 탭 전환 초기화
function initTabs() {
  const tabs = document.querySelectorAll(".nav-tab-btn");
  const panels = document.querySelectorAll(".tab-content");

  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      tabs.forEach(t => t.classList.remove("active"));
      panels.forEach(p => p.classList.remove("active"));

      tab.classList.add("active");
      const targetId = tab.getAttribute("data-target");
      const targetPanel = document.getElementById(targetId);
      if (targetPanel) {
        targetPanel.classList.add("active");
        if (targetId === "panelStudio") {
          setTimeout(alignPoemEditorWithAudioDropzone, 50);
        }
      }

      // 모바일 환경에서는 탭 선택 후 사이드바 자동 닫기
      if (window.innerWidth <= 900) {
        closeSidebarMobile();
      }
    });
  });
}

// 2. 시집 프로젝트 목록 로드 및 드롭다운 연동
async function loadProjects() {
  try {
    const res = await fetch("/api/projects");
    const data = await res.json();
    projectList = data.projects || [];
    const active = data.active_project;

    const select = document.getElementById("selectProjectDropdown");
    select.innerHTML = "";

    projectList.forEach(proj => {
      const opt = document.createElement("option");
      opt.value = proj.id;
      // 캡처3 요청: 시집 제목만 표시 (뒤의 [시화집] (9/35편) 등 삭제)
      opt.textContent = proj.name;
      if (proj.is_active || (active && proj.id === active.id)) {
        opt.selected = true;
      }
      select.appendChild(opt);
    });

    if (active) {
      const exportProj = document.getElementById("exportProjectName");
      if (exportProj) exportProj.textContent = active.name;
    }
  } catch (err) {
    console.error("프로젝트 목록 로드 실패:", err);
  }
}

// 3. 시집 전환 이벤트 처리
async function onProjectSelectChange(projectId) {
  if (!projectId) return;

  try {
    const res = await fetch("/api/projects/select", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project_id: projectId })
    });
    const data = await res.json();

    if (data.success) {
      currentWorkIndex = 0;
      await loadProjects();
      await loadStatus();
      await loadImagesInspection();
    }
  } catch (err) {
    alert("시집 전환 중 오류가 발생했습니다: " + err);
  }
}

// 도서 형태 라디오 선택 UI 인터랙션
function onBookTypeOptionChange(input, modalType) {
  const isNew = modalType === 'new';
  const prefix = isNew ? 'optNewType' : 'optEditType';
  const optIllustrated = document.getElementById(`${prefix}Illustrated`);
  const optStandard = document.getElementById(`${prefix}Standard`);

  if (input.value === 'illustrated') {
    if (optIllustrated) optIllustrated.classList.add('selected');
    if (optStandard) optStandard.classList.remove('selected');
  } else {
    if (optStandard) optStandard.classList.add('selected');
    if (optIllustrated) optIllustrated.classList.remove('selected');
  }
}

// 저자 구성 (시집 성격: 개인 vs 공동/가족) 라디오 선택 UI 인터랙션
function onAuthorTypeOptionChange(input, modalType) {
  const isNew = modalType === 'new';
  const prefix = isNew ? 'optNewAuthor' : 'optEditAuthor';
  const optSingle = document.getElementById(`${prefix}Single`);
  const optCollab = document.getElementById(`${prefix}Collab`);
  const lblAuthor = document.getElementById(isNew ? 'lblNewProjAuthor' : 'lblEditProjAuthor');
  const inputAuthor = document.getElementById(isNew ? 'inputNewProjAuthor' : 'inputEditProjAuthor');

  if (input.value === 'single') {
    if (optSingle) optSingle.classList.add('selected');
    if (optCollab) optCollab.classList.remove('selected');
    if (lblAuthor) lblAuthor.textContent = "시인 / 지은이";
    if (inputAuthor) inputAuthor.placeholder = "예: 홍길동 시인";
  } else {
    if (optCollab) optCollab.classList.add('selected');
    if (optSingle) optSingle.classList.remove('selected');
    if (lblAuthor) lblAuthor.textContent = "대표 엮은이 / 모임 명칭 (가족·공동)";
    if (inputAuthor) inputAuthor.placeholder = "예: 온가족 엮음, 홍길동 엮음, 32회 문우회";
  }
}

// 4. 새 시집 생성 모달 제어
function openNewProjectModal() {
  const modal = document.getElementById("newProjectModal");
  modal.style.display = "flex";
  
  // 기본값: 서정 시화집 선택
  const radio = document.querySelector('input[name="newProjBookType"][value="illustrated"]');
  if (radio) {
    radio.checked = true;
    onBookTypeOptionChange(radio, 'new');
  }

  // 기본값: 개인 시집 선택
  const authRadio = document.querySelector('input[name="newProjAuthorType"][value="single"]');
  if (authRadio) {
    authRadio.checked = true;
    onAuthorTypeOptionChange(authRadio, 'new');
  }

  document.getElementById("inputNewProjName").focus();
}

function closeNewProjectModal() {
  const modal = document.getElementById("newProjectModal");
  modal.style.display = "none";
  document.getElementById("formNewProject").reset();
}

// 4-1. 시집 정보 수정 모달 제어
async function openEditProjectModal() {
  if (!currentStatus || !currentStatus.project) {
    await loadStatus();
  }
  if (!currentStatus || !currentStatus.project) {
    alert("시집 정보를 불러오는 중입니다. 잠시 후 다시 시도해주세요.");
    return;
  }
  const proj = currentStatus.project;

  const idElem = document.getElementById("inputEditProjId");
  if (idElem) idElem.value = proj.id;
  const nameElem = document.getElementById("inputEditProjName");
  if (nameElem) nameElem.value = proj.name || "";
  const subElem = document.getElementById("inputEditProjSubtitle");
  if (subElem) subElem.value = proj.subtitle || "";
  const authElem = document.getElementById("inputEditProjAuthor");
  if (authElem) authElem.value = proj.author || "";
  const targetElem = document.getElementById("inputEditProjTarget");
  if (targetElem) targetElem.value = proj.target_count || 35;
  const descElem = document.getElementById("inputEditProjDesc");
  if (descElem) descElem.value = proj.description || "";

  // 도서 형태 반영
  const currentType = proj.book_type || "illustrated";
  const radio = document.querySelector(`input[name="editProjBookType"][value="${currentType}"]`);
  if (radio) {
    radio.checked = true;
    onBookTypeOptionChange(radio, 'edit');
  }

  // 시집 성격(저자 구성) 반영
  const currentAuthorType = proj.author_type || "single";
  const authRadio = document.querySelector(`input[name="editProjAuthorType"][value="${currentAuthorType}"]`);
  if (authRadio) {
    authRadio.checked = true;
    onAuthorTypeOptionChange(authRadio, 'edit');
  }

  const delBtn = document.getElementById("btnDeleteCurrentProject");
  if (delBtn) {
    if (projectList && projectList.length <= 1) {
      delBtn.style.display = "none";
    } else {
      delBtn.style.display = "inline-block";
    }
  }

  const modal = document.getElementById("editProjectModal");
  if (modal) {
    modal.style.display = "flex";
  }
  if (nameElem) nameElem.focus();
}

function closeEditProjectModal() {
  const modal = document.getElementById("editProjectModal");
  modal.style.display = "none";
}

function onModalOverlayClick(e) {
  if (e.target && e.target.id === "newProjectModal") {
    closeNewProjectModal();
  }
  if (e.target && e.target.id === "editProjectModal") {
    closeEditProjectModal();
  }
}

async function onCreateNewProject(event) {
  event.preventDefault();

  const name = document.getElementById("inputNewProjName").value.trim();
  const subtitle = document.getElementById("inputNewProjSubtitle").value.trim();
  const author = document.getElementById("inputNewProjAuthor").value.trim();
  const target = parseInt(document.getElementById("inputNewProjTarget").value, 10) || 35;
  const desc = document.getElementById("inputNewProjDesc").value.trim();
  const bookTypeElem = document.querySelector('input[name="newProjBookType"]:checked');
  const bookType = bookTypeElem ? bookTypeElem.value : "illustrated";
  const authorTypeElem = document.querySelector('input[name="newProjAuthorType"]:checked');
  const authorType = authorTypeElem ? authorTypeElem.value : "single";

  if (!name) {
    alert("시집 제목을 입력해주세요.");
    return;
  }

  const btn = document.getElementById("btnSubmitNewProject");
  const origText = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = "<span>⏳ 새로운 시집을 준비하는 중...</span>";

  try {
    const res = await fetch("/api/projects/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: name,
        subtitle: subtitle,
        author: author,
        target_count: target,
        description: desc,
        book_type: bookType,
        author_type: authorType
      })
    });

    const data = await res.json();
    if (data.success) {
      alert(`🎉 새로운 시집 「${name}」 프로젝트가 시작되었습니다!`);
      closeNewProjectModal();
      currentWorkIndex = 0;
      await loadProjects();
      await loadStatus();
      await loadImagesInspection();
    } else {
      alert("시집 생성 실패: " + (data.detail || "오류가 발생했습니다."));
    }
  } catch (err) {
    alert("시집 생성 중 오류 발생: " + err);
  } finally {
    btn.disabled = false;
    btn.innerHTML = origText;
  }
}

async function onUpdateProject(event) {
  event.preventDefault();
  const pid = document.getElementById("inputEditProjId").value;
  const name = document.getElementById("inputEditProjName").value.trim();
  const subtitle = document.getElementById("inputEditProjSubtitle").value.trim();
  const author = document.getElementById("inputEditProjAuthor").value.trim();
  const target = parseInt(document.getElementById("inputEditProjTarget").value, 10) || 35;
  const desc = document.getElementById("inputEditProjDesc").value.trim();
  const bookTypeElem = document.querySelector('input[name="editProjBookType"]:checked');
  const bookType = bookTypeElem ? bookTypeElem.value : "illustrated";
  const authorTypeElem = document.querySelector('input[name="editProjAuthorType"]:checked');
  const authorType = authorTypeElem ? authorTypeElem.value : "single";

  if (!name) {
    alert("시집 제목을 입력해주세요.");
    return;
  }

  const btn = document.getElementById("btnSubmitEditProject");
  btn.disabled = true;

  try {
    const res = await fetch("/api/projects/update", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        project_id: pid,
        name: name,
        subtitle: subtitle,
        author: author,
        target_count: target,
        description: desc,
        book_type: bookType,
        author_type: authorType
      })
    });
    const data = await res.json();
    if (data.success) {
      alert("✅ 시집 정보가 성공적으로 변경되었습니다.");
      closeEditProjectModal();
      await loadProjects();
      await loadStatus();
    } else {
      alert("수정 실패: " + (data.detail || "오류가 발생했습니다."));
    }
  } catch (err) {
    alert("수정 중 오류 발생: " + err);
  } finally {
    btn.disabled = false;
  }
}

async function onDeleteCurrentProject() {
  const pid = document.getElementById("inputEditProjId").value;
  const name = document.getElementById("inputEditProjName").value;

  if (projectList && projectList.length <= 1) {
    alert("서재에 최소 1권의 시집 프로젝트는 보관되어야 하므로 삭제할 수 없습니다.");
    return;
  }

  if (!confirm(`⚠️ 정말로 시집 「${name}」 프로젝트를 삭제하시겠습니까?\n작성된 원고, CSV, 삽화 데이터가 모두 영구 삭제됩니다.`)) {
    return;
  }

  try {
    const res = await fetch("/api/projects/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project_id: pid })
    });
    const data = await res.json();
    if (data.success) {
      alert(`🗑️ 시집 「${name}」이 삭제되었습니다. 기본 시집으로 이동합니다.`);
      closeEditProjectModal();
      currentWorkIndex = 0;
      await loadProjects();
      await loadStatus();
    } else {
      alert("삭제 실패: " + (data.detail || "오류"));
    }
  } catch (err) {
    alert("삭제 중 오류 발생: " + err);
  }
}


// 5. 전체 상태 및 작품 목록 로드
async function loadStatus() {
  try {
    const res = await fetch("/api/status");
    currentStatus = await res.json();

    const proj = currentStatus.project || {};

    // 헤더 및 사이드바 배지 업데이트
    document.getElementById("badgeCompletedCount").textContent = currentStatus.completed_count;
    document.getElementById("badgeTargetCount").textContent = currentStatus.target_count;
    document.getElementById("exportCompletedCount").textContent = currentStatus.completed_count;
    
    // 현재 편집 중인 회차가 있으면 유지, 없으면 다음 회차 표시
    if (currentEditingEpisode) {
      document.getElementById("inputEpisode").value = currentEditingEpisode;
    } else {
      document.getElementById("inputEpisode").value = currentStatus.next_episode;
    }

    // 사이드바 프로그레스 위젯 및 모바일 배지 업데이트
    const progFill = document.getElementById("sidebarProgressFill");
    if (progFill) progFill.style.width = `${currentStatus.progress_percent}%`;
    const progPercent = document.getElementById("sidebarProgressPercent");
    if (progPercent) progPercent.textContent = `${currentStatus.progress_percent}%`;

    const mobComp = document.getElementById("mobileCompletedCount");
    if (mobComp) mobComp.textContent = currentStatus.completed_count;
    const mobTarget = document.getElementById("mobileTargetCount");
    if (mobTarget) mobTarget.textContent = currentStatus.target_count;

    // 캡처4 요청: 현재 시집 한 줄 인라인 배너 (시집 제목, 저자)
    const bTitle = document.getElementById("bannerBookTitle");
    if (bTitle) bTitle.textContent = proj.name || "시집 제목";
    const bAuthor = document.getElementById("bannerBookAuthor");
    if (bAuthor) bAuthor.textContent = proj.author ? `${proj.author} 지음` : "시인 지음";

    // 프롬프트 가이드 라벨 업데이트
    const labelPromptTitle = document.getElementById("labelPromptGuideTitle");
    const labelPromptDpi = document.getElementById("labelPromptDpiSubtitle");
    if (labelPromptTitle) {
      if (proj.book_type === "standard") {
        labelPromptTitle.textContent = "🎨 (선택) 삽화 프롬프트";
        if (labelPromptDpi) labelPromptDpi.textContent = "일반 시집에서는 생략 가능";
      } else {
        labelPromptTitle.textContent = "🎨 삽화 생성 가이드 프롬프트";
        if (labelPromptDpi) labelPromptDpi.textContent = "(출판 표준 300 DPI)";
      }
    }

    // 가상 시화집 북 뷰어 드롭다운 채우기
    const select = document.getElementById("selectWorkDropdown");
    select.innerHTML = "";

    if (currentStatus.works && currentStatus.works.length > 0) {
      currentStatus.works.forEach((w, idx) => {
        const opt = document.createElement("option");
        opt.value = idx;
        const chapLabel = w.chapter ? `[${w.chapter}] ` : "";
        opt.textContent = `${chapLabel}[${w.episode_no}] ${w.title}`;
        select.appendChild(opt);
      });

      if (currentWorkIndex >= currentStatus.works.length) {
        currentWorkIndex = currentStatus.works.length - 1;
      }
      renderBookSpread(currentWorkIndex);
    } else {
      const opt = document.createElement("option");
      opt.textContent = "작성된 작품이 없습니다";
      select.appendChild(opt);
      renderEmptyBookSpread();
    }

    // ZIP 백업 다운로드 링크 업데이트
    const zipUrl = `/api/projects/export_zip?project_id=${proj.id || ''}`;
    const btnBannerZip = document.getElementById("btnBannerExportZip");
    if (btnBannerZip) btnBannerZip.href = zipUrl;
    const btnCardZip = document.getElementById("btnExportZipCard");
    if (btnCardZip) btnCardZip.href = zipUrl;

    loadImagesInspection();
    updateWorkToEditDropdown();
  } catch (err) {
    console.error("상태 로드 실패:", err);
  }
}


let isSavingWork = false; // 저장 중복 클릭 및 동시 실행 방지 플래그

// 6. 이벤트 바인딩
function bindEvents() {
  const btnGemini = document.getElementById("btnOpenGeminiKeyModal");
  if (btnGemini) {
    btnGemini.onclick = openGeminiKeyModal;
  }
}

let isGeneratingDrafts = false; // 중복 클릭 및 동시 실행 방지 플래그

// 7. 시안 생성 요청
async function onGenerateDrafts(seed = null) {
  if (isGeneratingDrafts) return; // 이미 진행 중이면 중복 실행 방지
  isGeneratingDrafts = true;

  // 신규 시안 생성이므로 새 회차 작성 모드로 리셋
  currentEditingEpisode = null;
  if (currentStatus && currentStatus.next_episode) {
    document.getElementById("inputEpisode").value = currentStatus.next_episode;
  }

  const coreMemory = (document.getElementById("inputCoreMemory")?.value || "").trim();
  const sensoryDetails = (document.getElementById("inputSensoryDetails")?.value || "").trim();
  const spokenWords = (document.getElementById("inputSpokenWords")?.value || "").trim();
  const deepAnswer = (document.getElementById("inputDeepAnswer")?.value || "").trim();

  if (!coreMemory && !sensoryDetails && !spokenWords) {
    alert("기억의 실마리를 위해 1, 2, 3번 중 어느 한 항목이라도 편하게 입력해주세요.");
    document.getElementById("inputCoreMemory")?.focus();
    isGeneratingDrafts = false;
    return;
  }

  const btn = document.getElementById("btnGenerateDrafts");
  const originalText = btn ? btn.innerHTML : "<span>✨ 2가지 시안 빚어내기</span>";
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = "<span>⏳ 두 가지 시안을 빚어내는 중...</span>";
  }

  try {
    const res = await fetch("/api/generate_drafts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        core_memory: coreMemory,
        sensory_details: sensoryDetails,
        spoken_words: spokenWords,
        deep_interview_answer: deepAnswer,
        style_seed: seed || Math.floor(Math.random() * 100000)
      })
    });

    const data = await res.json();
    if (!res.ok || !data || !data.draft_a || !data.draft_b) {
      let errMsg = "";
      if (data && data.detail) {
        if (typeof data.detail === "string") {
          errMsg = data.detail;
        } else if (Array.isArray(data.detail)) {
          errMsg = data.detail.map(d => (d.msg ? `${d.loc ? d.loc.join('.') + ': ' : ''}${d.msg}` : JSON.stringify(d))).join(", ");
        } else {
          errMsg = JSON.stringify(data.detail);
        }
      } else {
        errMsg = `서버 응답 오류 (상태코드: ${res.status})`;
      }
      throw new Error(errMsg);
    }

    currentDrafts = data;

    // Fact Lock 카드 업데이트
    const parts = [];
    if (coreMemory) parts.push(`기억의 중심: ${coreMemory}`);
    if (sensoryDetails) parts.push(`사물/행동: ${sensoryDetails}`);
    if (spokenWords) parts.push(`실제 말: "${spokenWords}"`);
    const lockSummary = parts.length > 0 ? parts.join(" | ") : "기억의 한 조각";
    const factLockEl = document.getElementById("factLockText");
    if (factLockEl) factLockEl.textContent = lockSummary;

    // 모달 시안 데이터 바인딩
    const mTitleA = document.getElementById("modalDraftTitleA");
    const mBodyA = document.getElementById("modalDraftBodyA");
    const mTitleB = document.getElementById("modalDraftTitleB");
    const mBodyB = document.getElementById("modalDraftBodyB");
    if (mTitleA && data.draft_a) mTitleA.textContent = data.draft_a.title;
    if (mBodyA && data.draft_a) mBodyA.textContent = data.draft_a.body;
    if (mTitleB && data.draft_b) mTitleB.textContent = data.draft_b.title;
    if (mBodyB && data.draft_b) mBodyB.textContent = data.draft_b.body;

    // 2가지 시안 팝업창 오픈 및 기본 A안 반영
    try {
      selectDraft("A");
    } catch (e) {
      console.warn("기본 시안 A 선택 중 경미한 이슈:", e);
    }
    openPoemDraftsModal();

    // 삽화 프롬프트 안내
    const promptDisplay = document.getElementById("imagePromptDisplay");
    if (promptDisplay && data.image_prompt) {
      if (promptDisplay.value !== undefined) {
        promptDisplay.value = data.image_prompt;
      } else {
        promptDisplay.textContent = data.image_prompt;
      }
    }

  } catch (err) {
    console.error("시안 생성 오류:", err);
    const msg = (err && err.message) ? err.message : String(err);
    alert("시안 생성 중 안내: " + msg);
  } finally {
    isGeneratingDrafts = false;
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = originalText;
    }
  }
}

// 7-0. 2가지 시안 모달 열기/닫기/선택
function openPoemDraftsModal() {
  if (currentDrafts) {
    const mTitleA = document.getElementById("modalDraftTitleA");
    const mBodyA = document.getElementById("modalDraftBodyA");
    const mTitleB = document.getElementById("modalDraftTitleB");
    const mBodyB = document.getElementById("modalDraftBodyB");
    if (mTitleA && currentDrafts.draft_a) mTitleA.textContent = currentDrafts.draft_a.title;
    if (mBodyA && currentDrafts.draft_a) mBodyA.textContent = currentDrafts.draft_a.body;
    if (mTitleB && currentDrafts.draft_b) mTitleB.textContent = currentDrafts.draft_b.title;
    if (mBodyB && currentDrafts.draft_b) mBodyB.textContent = currentDrafts.draft_b.body;
  }
  const modal = document.getElementById("poemDraftsModal");
  if (modal) modal.style.display = "flex";
}

function closePoemDraftsModal() {
  const modal = document.getElementById("poemDraftsModal");
  if (modal) modal.style.display = "none";
}

function chooseDraftFromModal(type) {
  selectDraft(type);
  closePoemDraftsModal();

  const inputPoem = document.getElementById("inputFinalPoem");
  if (inputPoem) {
    inputPoem.style.transition = "background-color 0.3s ease";
    inputPoem.style.backgroundColor = "#FDF8F0";
    setTimeout(() => { inputPoem.style.backgroundColor = ""; }, 400);
    inputPoem.scrollIntoView({ behavior: "smooth", block: "center" });
    inputPoem.focus();
  }
}

// 7-1. 다른 느낌으로 다시 빚기 (다시 창작)
async function reDraftDifferentStyle() {
  const btnTop = document.getElementById("btnModalRedraftTop");
  const btnBottom = document.getElementById("btnModalRedraftBottom");
  const mBodyA = document.getElementById("modalDraftBodyA");
  const mBodyB = document.getElementById("modalDraftBodyB");

  const origTopHtml = btnTop ? btnTop.innerHTML : "<span>🔄 다시 짓기</span>";
  const origBottomHtml = btnBottom ? btnBottom.innerHTML : "<span>🔄 다시 짓기</span>";

  if (btnTop) {
    btnTop.disabled = true;
    btnTop.innerHTML = "<span>⏳ 다시 짓는 중...</span>";
  }
  if (btnBottom) {
    btnBottom.disabled = true;
    btnBottom.innerHTML = "<span>⏳ 다시 짓는 중...</span>";
  }

  if (mBodyA) mBodyA.style.opacity = "0.45";
  if (mBodyB) mBodyB.style.opacity = "0.45";

  try {
    const newSeed = Math.floor(Math.random() * 900000) + 100000;
    await onGenerateDrafts(newSeed);
  } finally {
    if (btnTop) {
      btnTop.disabled = false;
      btnTop.innerHTML = origTopHtml;
    }
    if (btnBottom) {
      btnBottom.disabled = false;
      btnBottom.innerHTML = origBottomHtml;
    }
    if (mBodyA) mBodyA.style.opacity = "1";
    if (mBodyB) mBodyB.style.opacity = "1";
  }
}

let previousPoemBody = null;

// 7-2. 원클릭 시 퇴고 다듬기 (더 담담하게, 3행 압축, 운율 정돈)
async function refineCurrentPoem(mode) {
  const inputPoem = document.getElementById("inputFinalPoem");
  const currentBody = inputPoem.value.trim();
  if (!currentBody) {
    alert("먼저 시안을 선택하거나 시 본문을 입력해주세요.");
    return;
  }

  const title = document.getElementById("inputFinalTitle") ? document.getElementById("inputFinalTitle").value.trim() : "";
  previousPoemBody = currentBody;
  const btnUndo = document.getElementById("btnUndoPoemRefine");

  try {
    const res = await fetch("/api/refine_poem", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: title,
        poem_body: currentBody,
        mode: mode
      })
    });
    const data = await res.json();
    if (data.success && data.refined_body) {
      inputPoem.value = data.refined_body;
      if (btnUndo) btnUndo.style.display = "inline-flex";

      const modeNames = {
        "subdued": "🌿 담담하게 절제된 어조로 다듬었습니다.",
        "shorten": "🍂 3행의 묵직한 압축시로 정제했습니다.",
        "rhythm": "🎵 연 구성을 보존하고 낭송 호흡과 운율에 맞게 정돈했습니다."
      };
      showToast(modeNames[mode] || "시를 아름답게 다듬었습니다.", "success");

      // 가벼운 시각적 피드백
      inputPoem.style.transition = "background-color 0.3s ease";
      inputPoem.style.backgroundColor = "#FDF8F0";
      setTimeout(() => { inputPoem.style.backgroundColor = ""; }, 400);
    }
  } catch (err) {
    alert("시 다듬기 중 오류가 발생했습니다: " + err);
  }
}

// 7-2-1. [신규] 사용자 맞춤 설명 및 자유 수정 요청 다듬기 (대화창 연동)
async function onCustomRefinePoem() {
  const inputPoem = document.getElementById("inputFinalPoem");
  const currentBody = inputPoem.value.trim();
  if (!currentBody) {
    alert("먼저 시안을 선택하거나 시 본문을 입력해주세요.");
    return;
  }

  const inputGuide = document.getElementById("inputCustomPoemGuide");
  const instruction = inputGuide ? inputGuide.value.trim() : "";
  if (!instruction) {
    alert("원하시는 수정 방향이나 설명을 입력해주세요.\n(예: 2연에 고무신을 잃어버린 슬픔을 더 강조해줘, 마지막 연을 노을빛 풍경으로 바꿔줘)");
    if (inputGuide) inputGuide.focus();
    return;
  }

  const title = document.getElementById("inputFinalTitle") ? document.getElementById("inputFinalTitle").value.trim() : "";
  const btn = document.getElementById("btnCustomRefinePoem");
  const origBtnContent = btn ? btn.innerHTML : "";

  if (btn) {
    btn.disabled = true;
    btn.style.opacity = "0.7";
    btn.innerHTML = `<span style="font-size: 0.85rem; line-height: 1;">⏳</span>`;
  }

  previousPoemBody = currentBody;
  const btnUndo = document.getElementById("btnUndoPoemRefine");

  try {
    const res = await fetch("/api/refine_poem", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: title,
        poem_body: currentBody,
        mode: "custom",
        instruction: instruction
      })
    });
    const data = await res.json();
    if (data.success && data.refined_body) {
      inputPoem.value = data.refined_body;
      if (btnUndo) btnUndo.style.display = "inline-flex";

      showToast(`💬 [${instruction}] 요청이 반영되어 시가 다듬어졌습니다!`, "success");
      if (inputGuide) inputGuide.value = ""; // 입력창 초기화

      // 시각적 강조 피드백
      inputPoem.style.transition = "background-color 0.4s ease";
      inputPoem.style.backgroundColor = "#FDF4EC";
      setTimeout(() => { inputPoem.style.backgroundColor = ""; }, 500);
    } else {
      alert("시 수정 중 오류가 발생했습니다: " + (data.error || "응답 실패"));
    }
  } catch (err) {
    alert("시 다듬기 중 오류가 발생했습니다: " + err.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.style.opacity = "1";
      btn.innerHTML = origBtnContent;
    }
  }
}

// 7-2-2. [신규] 수정 전 시 본문 되돌리기
function undoPoemRefine() {
  if (!previousPoemBody) return;
  const inputPoem = document.getElementById("inputFinalPoem");
  const current = inputPoem.value;
  inputPoem.value = previousPoemBody;
  previousPoemBody = current; // 한 번 더 누르면 다시 토글

  showToast("↩️ 수정 직전의 시 본문으로 복원되었습니다.", "info");
  inputPoem.style.transition = "background-color 0.3s ease";
  inputPoem.style.backgroundColor = "#EEF2FF";
  setTimeout(() => { inputPoem.style.backgroundColor = ""; }, 400);
}

// 7-3. 외부 무료 AI(ChatGPT, Claude, 뤼튼 등)용 전문 서정시 프롬프트 복사
async function copyExternalMegaPrompt() {
  const coreMemory = document.getElementById("inputCoreMemory").value.trim();
  const sensoryDetails = document.getElementById("inputSensoryDetails").value.trim();
  const spokenWords = document.getElementById("inputSpokenWords").value.trim();

  if (!coreMemory) {
    alert("기억의 중심을 최소 1개 이상 입력해주세요.");
    document.getElementById("inputCoreMemory").focus();
    return;
  }

  try {
    const res = await fetch("/api/smart_prompt", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        core_memory: coreMemory,
        sensory_details: sensoryDetails,
        spoken_words: spokenWords
      })
    });
    const data = await res.json();
    if (data.success && data.prompt) {
      await navigator.clipboard.writeText(data.prompt);
      alert("📋 [무료 AI용 전문 서정시 프롬프트]가 클립보드에 복사되었습니다!\n\nChatGPT, Claude, 뤼튼 등의 무료 채팅창에 그대로 [Ctrl+V] 붙여넣기 하시면 최고의 서정시 2편을 얻으실 수 있습니다.");
    }
  } catch (err) {
    alert("프롬프트 생성 중 오류가 발생했습니다: " + err);
  }
}

// 8. 시안 선택 (A or B)
function selectDraft(type) {
  const cardModalA = document.getElementById("cardModalDraftA");
  const cardModalB = document.getElementById("cardModalDraftB");
  const inputTitle = document.getElementById("inputFinalTitle");
  const inputPoem = document.getElementById("inputFinalPoem");

  // currentDrafts 객체가 없는 경우 모달 화면에 표시된 내용으로부터 자동 구성
  if (!currentDrafts) {
    const titleA = document.getElementById("modalDraftTitleA") ? document.getElementById("modalDraftTitleA").textContent.trim() : "새벽 대청";
    const bodyA = document.getElementById("modalDraftBodyA") ? document.getElementById("modalDraftBodyA").innerText.trim() : "";
    const titleB = document.getElementById("modalDraftTitleB") ? document.getElementById("modalDraftTitleB").textContent.trim() : "어머니의 물레";
    const bodyB = document.getElementById("modalDraftBodyB") ? document.getElementById("modalDraftBodyB").innerText.trim() : "";
    currentDrafts = {
      draft_a: { title: titleA, body: bodyA },
      draft_b: { title: titleB, body: bodyB }
    };
  }

  if (type === "A") {
    if (cardModalA) {
      cardModalA.style.borderColor = "#643E19";
      cardModalA.style.background = "#FDFBF7";
    }
    if (cardModalB) {
      cardModalB.style.borderColor = "#EBDCCB";
      cardModalB.style.background = "#FFFDF9";
    }
    if (inputTitle) inputTitle.value = currentDrafts.draft_a.title || "";
    if (inputPoem) {
      inputPoem.value = currentDrafts.draft_a.body || "";
      inputPoem.dispatchEvent(new Event("input", { bubbles: true }));
    }
  } else {
    if (cardModalB) {
      cardModalB.style.borderColor = "#8B4513";
      cardModalB.style.background = "#FDFBF7";
    }
    if (cardModalA) {
      cardModalA.style.borderColor = "#EBDCCB";
      cardModalA.style.background = "#FFFDF9";
    }
    if (inputTitle) inputTitle.value = currentDrafts.draft_b.title || "";
    if (inputPoem) {
      inputPoem.value = currentDrafts.draft_b.body || "";
      inputPoem.dispatchEvent(new Event("input", { bubbles: true }));
    }
  }

  // 1그룹에서 시안을 선택했으므로 2그룹을 '신규 회차 작성 모드'로 확실히 전환
  currentEditingEpisode = null;
  const selBox = document.getElementById("selectWorkToEdit");
  if (selBox) selBox.value = "new";

  const nextEp = (currentStatus && currentStatus.next_episode) ? currentStatus.next_episode : "신규 화";
  const epInput = document.getElementById("inputEpisode");
  if (epInput && currentStatus && currentStatus.next_episode) {
    epInput.value = currentStatus.next_episode;
  }

  const epBadge = document.getElementById("labelCurrentEditingEpBadge");
  if (epBadge) {
    epBadge.textContent = `[${nextEp} 신규 집필 중]`;
    epBadge.style.color = "#2E6B34";
    epBadge.style.background = "#EFF8EE";
    epBadge.style.borderColor = "#BCE3B9";
  }
  const btnDelete = document.getElementById("btnDeleteCurrentWork");
  if (btnDelete) btnDelete.style.display = "none";
}

let currentArtStyle = "watercolor"; // "watercolor" | "ink_wash" | "pastel" | "oil_painting"
let currentArtStyleDial = "literal"; // "literal" (정경 묘사형, 기본값) | "atmospheric" (여백 암시형)

// 화풍별 명칭 및 기본 예시 프롬프트 맵
const artStyleMeta = {
  watercolor: {
    name: "서정 수채화",
    color: "#2C5282",
    prompts: {
      atmospheric: "Korean minimalist lyric watercolor painting, subtle atmospheric impression, soft slanted sunlight, delicate watery bleed, soft vignette fading into pure white paper, peaceful poetic negative space, 300 dpi",
      literal: "Korean lyric watercolor illustration, detailed traditional scene, delicate wet-on-wet washes, warm nostalgic lighting, soft vignette fading into pure paper margin, 300 dpi"
    }
  },
  ink_wash: {
    name: "먹빛 수묵담채",
    color: "#2D3748",
    prompts: {
      atmospheric: "Traditional Korean ink wash painting, deep atmospheric impression, subtle faint pigment wash, rough mulberry hanji paper texture, soft vignette fading into paper, 300 dpi",
      literal: "Traditional Korean sumuk ink and wash painting, rich evocative scene, expressive ink brush lines, gentle earthy natural pigments, rustic hanji paper, soft vignette fading into paper, 300 dpi"
    }
  },
  pastel: {
    name: "파스텔 동화",
    color: "#975A16",
    prompts: {
      atmospheric: "Whimsical nostalgic storybook illustration, soft dreamy pastel textures, tender poetic impression, cozy ambient light, soft vignette fading into pure paper margin, 300 dpi",
      literal: "Heartwarming storybook illustration, rich textured colored pencil and soft chalk pastel, warm golden glow, sweet nostalgic childhood fairy tale style, soft vignette fading into paper, 300 dpi"
    }
  },
  sketch: {
    name: "만화/스케치",
    color: "#4A5568",
    prompts: {
      atmospheric: "Atmospheric manga sketch art, delicate pencil and ink linework, minimalist warm watercolor wash, airy poetic space, soft vignette fading into pure paper margin, 300 dpi",
      literal: "Delicate lyrical manga sketch illustration, detailed pen and ink drawing with gentle warm watercolor wash, cozy slice-of-life aesthetic, soft vignette fading into paper, 300 dpi"
    }
  },
  oil_painting: {
    name: "서정 유화",
    color: "#744210",
    prompts: {
      atmospheric: "Impressionist lyric oil painting, subtle atmospheric impression, expressive palette knife strokes, poetic spacious composition, soft vignette fading into canvas edge, 300 dpi",
      literal: "Rich lyrical oil painting, detailed textured scene, expressive impasto brushstrokes, glowing golden hour light, soft vignette fading into canvas edge, 300 dpi"
    }
  }
};

// 🎨 삽화 화풍 라디오 변경 이벤트 핸들러
function onArtStyleRadioChange() {
  const selected = document.querySelector('input[name="artStyleRadio"]:checked');
  if (selected) {
    currentArtStyle = selected.value;
  }

  const meta = artStyleMeta[currentArtStyle] || artStyleMeta.watercolor;
  const labelSummary = document.getElementById("labelArtStyleSummary");
  if (labelSummary) {
    labelSummary.textContent = `[현재: ${meta.name}]`;
    labelSummary.style.color = meta.color;
  }

  // 본문이 이미 작성되어 있다면 자동으로 새 화풍에 맞춰 프롬프트 즉시 재작성
  const poemBody = document.getElementById("inputFinalPoem")?.value?.trim();
  if (poemBody) {
    onGenerateImagePrompt(false);
  } else {
    // 본문이 아직 없을 경우 대표 예시 프롬프트를 해당 화풍으로 업데이트
    const display = document.getElementById("imagePromptDisplay");
    if (display) {
      const mode = currentArtStyleDial === "atmospheric" ? "atmospheric" : "literal";
      display.value = meta.prompts[mode] || meta.prompts.literal;
      // 시각적 피드백 효과
      display.style.backgroundColor = "#FAF7F2";
      setTimeout(() => {
        display.style.backgroundColor = "#FFFFFF";
      }, 350);
    }
  }
}

// 🎛️ 삽화 감성 다이얼 토글 (정경 묘사형 vs 여백 암시형)
function setArtStyleDial(mode) {
  currentArtStyleDial = mode;
  const btnAtm = document.getElementById("btnDialAtmospheric");
  const btnLit = document.getElementById("btnDialLiteral");
  const labelSummary = document.getElementById("labelArtDialSummary");

  if (btnAtm && btnLit) {
    if (mode === "literal") {
      btnLit.classList.add("active");
      btnAtm.classList.remove("active");
      if (labelSummary) {
        labelSummary.textContent = "[현재: 정경 묘사형 (溫情)]";
        labelSummary.style.color = "#2E5C38";
      }
    } else {
      btnAtm.classList.add("active");
      btnLit.classList.remove("active");
      if (labelSummary) {
        labelSummary.textContent = "[현재: 여백 암시형 (餘白)]";
        labelSummary.style.color = "#8B4513";
      }
    }
  }

  // 본문이 이미 작성되어 있다면 자동으로 새 감성 다이얼에 맞춰 프롬프트 재작성
  const poemBody = document.getElementById("inputFinalPoem")?.value?.trim();
  if (poemBody) {
    onGenerateImagePrompt(false);
  } else {
    const meta = artStyleMeta[currentArtStyle] || artStyleMeta.watercolor;
    const display = document.getElementById("imagePromptDisplay");
    if (display) {
      const dialMode = mode === "atmospheric" ? "atmospheric" : "literal";
      display.value = meta.prompts[dialMode] || meta.prompts.literal;
    }
  }
}

// 💡 삽화 연출 퀵 보정 칩 클릭 핸들러
function addArtGuideChip(text) {
  const guideInput = document.getElementById("inputArtCustomGuide");
  if (!guideInput) return;
  const current = guideInput.value.trim();
  if (!current) {
    guideInput.value = text;
  } else if (!current.includes(text)) {
    guideInput.value = `${current}, ${text}`;
  }
  guideInput.focus();
}

// 8. 다듬어진 시로 삽화 프롬프트 작성 (선택된 화풍, 감성 다이얼, 사용자 연출 지시 연동)
async function onGenerateImagePrompt(alertIfEmpty = true) {
  const title = document.getElementById("inputFinalTitle").value.trim();
  const poemBody = document.getElementById("inputFinalPoem").value.trim();
  const coreMemory = document.getElementById("inputCoreMemory").value.trim();
  const sensoryDetails = document.getElementById("inputSensoryDetails").value.trim();
  const customGuide = document.getElementById("inputArtCustomGuide")?.value?.trim() || "";

  if (!poemBody) {
    if (alertIfEmpty) {
      alert("시 본문을 먼저 작성하거나 다듬어주세요.");
      document.getElementById("inputFinalPoem").focus();
    }
    return;
  }

  const btn = document.getElementById("btnCreateImagePrompt");
  const origText = btn ? btn.innerHTML : "";
  const meta = artStyleMeta[currentArtStyle] || artStyleMeta.watercolor;
  const dialLabel = currentArtStyleDial === "atmospheric" ? "여백 암시형" : "정경 묘사형";

  if (btn) {
    btn.disabled = true;
    const guideTag = customGuide ? ` · 연출보정 반영` : "";
    btn.innerHTML = `<span>⏳ [${meta.name} · ${dialLabel}${guideTag}] 삽화 프롬프트 빚는 중...</span>`;
  }

  try {
    const res = await fetch("/api/generate_image_prompt", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: title || "무제",
        poem_body: poemBody,
        core_memory: coreMemory,
        sensory_details: sensoryDetails,
        style_mode: currentArtStyleDial,
        art_style: currentArtStyle,
        custom_guide: customGuide
      })
    });
    if (!res.ok) {
      const errText = await res.text();
      throw new Error(`서버 응답 오류 (${res.status}): ${errText}`);
    }
    const data = await res.json();
    if (data.success && data.prompt) {
      if (data.english_prompt) {
        latestEnglishPrompt = data.english_prompt;
      }
      if (data.korean_instruction) {
        latestKoreanInstruction = data.korean_instruction;
      }
      const display = document.getElementById("imagePromptDisplay");
      if (display) {
        display.value = data.prompt;
        // 시각적 피드백 효과 (화풍별 맞춤 하이라이트)
        const highlightColors = {
          watercolor: "#EBF8FF",
          ink_wash: "#EDF2F7",
          pastel: "#FEFCBF",
          sketch: "#F0F4F8",
          oil_painting: "#FEEBC8"
        };
        display.style.backgroundColor = highlightColors[currentArtStyle] || "#F5F3FF";
        display.style.borderColor = "var(--accent-primary)";
        setTimeout(() => {
          display.style.backgroundColor = "#FFFFFF";
          display.style.borderColor = "#DFD8CB";
        }, 600);
      }
    }
  } catch (err) {
    if (alertIfEmpty) alert("프롬프트 생성 중 오류가 발생했습니다: " + err);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = origText;
    }
  }
}

let latestKoreanInstruction = "";
let latestEnglishPrompt = "";

// 📋 클립보드 안전 복사 헬퍼 (모든 브라우저 환경 및 비보안 HTTP 호환)
async function safeCopyToClipboard(text) {
  if (!text) return false;
  // 1차 시도: 최신 navigator.clipboard API
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch (err) {
    console.warn("navigator.clipboard 실패, 폴백 시도:", err);
  }
  // 2차 시도: execCommand('copy') 호환성 폴백
  try {
    const textArea = document.createElement("textarea");
    textArea.value = text;
    textArea.style.position = "fixed";
    textArea.style.left = "-9999px";
    textArea.style.top = "-9999px";
    textArea.setAttribute("readonly", "");
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    const successful = document.execCommand("copy");
    document.body.removeChild(textArea);
    return successful;
  } catch (err) {
    console.error("클립보드 복사 최종 실패:", err);
    return false;
  }
}

// 9. 영문 마스터 프롬프트 복사
async function copyPrompt() {
  let targetText = latestEnglishPrompt;

  // 아직 영문 프롬프트가 준비되지 않았다면 즉시 생성 시도
  if (!targetText) {
    await onGenerateImagePrompt(false);
    targetText = latestEnglishPrompt;
  }

  // 그래도 비어있다면 화면 입력창 내용 활용
  if (!targetText) {
    const elem = document.getElementById("imagePromptDisplay");
    targetText = elem ? (elem.value || elem.textContent || "") : "";
  }

  if (!targetText) {
    alert("복사할 프롬프트가 없습니다. 먼저 [시 본문으로 삽화 프롬프트 작성]을 눌러주세요.");
    return;
  }

  const success = await safeCopyToClipboard(targetText);
  if (success) {
    showToast("📋 [영문 삽화 마스터 프롬프트]가 클립보드에 복사되었습니다!<br>Midjourney, Stable Diffusion, 외부 AI에 붙여넣으세요.", "success");
  } else {
    alert("클립보드 복사에 실패했습니다. 브라우저 권한을 확인해주세요.");
  }
}

// 9-2. 흰색 종이 10% 여백 및 화풍 규칙이 완비된 전문 한글 지시문 복사
async function copyKoreanArtInstruction() {
  let targetText = latestKoreanInstruction;
  if (!targetText) {
    await onGenerateImagePrompt(false);
    targetText = latestKoreanInstruction;
  }

  if (!targetText) {
    showToast("⚠️ 먼저 좌측에서 시를 선택하거나 [시 본문으로 삽화 프롬프트 작성]을 눌러주세요.", "error");
    return;
  }

  const success = await safeCopyToClipboard(targetText);
  if (success) {
    showToast("📋 [순백 10% 여백 & 화풍 규격 한글 전문 지시문]이 복사되었습니다!<br>ChatGPT, Gemini, Claude에 그대로 붙여넣으세요.", "success");
  } else {
    alert("클립보드 복사에 실패했습니다.");
  }
}

// 10. 원고 최종 저장 (시 본문 우선 저장 또는 전체 최종 저장)
async function onSaveWork() {
  if (isSavingWork) return;
  const inputTitleEl = document.getElementById("inputFinalTitle");
  const inputPoemEl = document.getElementById("inputFinalPoem");
  const title = inputTitleEl ? inputTitleEl.value.trim() : "";
  const poem = inputPoemEl ? inputPoemEl.value.trim() : "";
  const memory = document.getElementById("inputCoreMemory") ? document.getElementById("inputCoreMemory").value.trim() : "";
  let ep = currentEditingEpisode || (document.getElementById("inputEpisode") ? document.getElementById("inputEpisode").value : "제01화");

  if (!title) {
    showToast("⚠️ 시 제목을 입력해주세요.", "error");
    if (inputTitleEl) {
      inputTitleEl.focus();
      inputTitleEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    return;
  }

  if (!poem) {
    showToast("⚠️ 시 본문을 입력해주세요.", "error");
    if (inputPoemEl) {
      inputPoemEl.focus();
      inputPoemEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    return;
  }

  // 1. 이미 등록/저장된 시인지 확인 및 수정 여부 확인창 제어
  const works = (currentStatus && currentStatus.works) ? currentStatus.works : [];
  const existingByEp = works.find(w => w.episode_no === ep);
  const existingByTitle = works.find(w => w.title.trim() === title);

  let isUpdate = false;
  let targetEp = ep;
  let origWork = null;

  if (currentEditingEpisode) {
    // Case 1: 회차 선택 또는 이전 저장을 통해 현재 특정 회차를 편집 중인 경우
    isUpdate = true;
    targetEp = currentEditingEpisode;
    origWork = works.find(w => w.episode_no === targetEp);

    // 다른 회차에 같은 제목이 있는지 중복 체크
    const dupOtherWork = works.find(w => w.title.trim() === title && w.episode_no !== targetEp);
    if (dupOtherWork) {
      showToast(`⚠️ 다른 회차([${dupOtherWork.episode_no}])에 이미 같은 제목(「${title}」)의 시가 존재합니다.`, "error");
      return;
    }

    const origTitle = origWork ? origWork.title : "";
    let confirmMsg = "";
    if (origTitle && origTitle !== title) {
      confirmMsg = `📝 [${targetEp}] 원고의 제목과 본문 수정을 반영하시겠습니까?\n\n- 기존 제목: 「${origTitle}」\n- 새 제목: 「${title}」\n\n[확인]을 누르시면 변경된 제목과 본문으로 [${targetEp}] 원고가 갱신됩니다.`;
    } else {
      confirmMsg = `📝 [${targetEp}] 「${title}」 원고를 수정한 내용으로 덮어쓰시겠습니까?\n\n- [확인]: 기존 [${targetEp}] 원고에 수정본으로 저장\n- [취소]: 저장 취소`;
    }
    if (!confirm(confirmMsg)) return;

  } else if (existingByEp) {
    // Case 2: 신규 작성 모드이지만 입력된 회차 번호가 이미 기존 원고에 존재하는 경우
    isUpdate = true;
    targetEp = existingByEp.episode_no;
    origWork = existingByEp;
    const ok = confirm(`📝 [${targetEp}] 원고가 이미 존재합니다.\n\n해당 회차의 원고를 현재 내용(「${title}」)으로 수정(덮어쓰기)하시겠습니까?\n\n- [확인]: [${targetEp}] 원고를 수정하여 덮어쓰기\n- [취소]: 저장 취소`);
    if (!ok) return;

  } else if (existingByTitle) {
    // Case 3: 신규 작성 모드인데 동일한 제목의 시가 다른 회차에 이미 등록되어 있는 경우
    showToast(`⚠️ 이미 [${existingByTitle.episode_no}]에 같은 제목(「${title}」)의 시가 등록되어 있습니다.`, "error");
    return;

  } else {
    // Case 4: 완전히 새로운 시를 처음 저장하는 경우
    isUpdate = false;
    targetEp = ep;
  }

  const cleanTitle = title.replace(/[\s\\/*?:"<>|]/g, '');
  
  // 이미지 파일 결정: 기존 작품에 이미 삽화가 있다면 보존하고, 신규 제안이 있을 때만 갱신
  let imageFile = "";
  if (currentDrafts && currentDrafts.suggested_image_file) {
    imageFile = currentDrafts.suggested_image_file;
  } else if (origWork && origWork.image_file) {
    imageFile = origWork.image_file;
  } else {
    imageFile = `images/${targetEp.replace(/[^0-9]/g, '')}_${cleanTitle}.jpg`;
  }

  // 음원 파일 결정: 낭송 음원과 노래 음원을 독립적으로 유지
  const reciteFile = currentReciteFile || (origWork ? (origWork.recite_file || "") : "") || "";
  const musicFile = currentMusicFile || (origWork ? (origWork.music_file || "") : "") || "";
  const audioFile = musicFile || reciteFile || currentAudioFile || (origWork ? origWork.audio_file : "") || "";

  const dialLabel = currentArtStyleDial === "atmospheric" ? "여백의 미" : "정경 묘사";
  const artStyleLabels = {
    watercolor: "한국 정통 서정 수채화",
    ink_wash: "전통 먹빛 수묵담채화",
    pastel: "포근한 파스텔 동화풍",
    sketch: "정감 있는 만화·스케치풍",
    oil_painting: "서정적 유화·유채화"
  };
  const artDirection = `${artStyleLabels[currentArtStyle] || "한국 정통 서정 수채화"} (${dialLabel}, 300 DPI)`;
  const lyricsInput = document.getElementById("musicLyricsInput");
  const lyricsText = lyricsInput ? lyricsInput.value.trim() : (origWork ? origWork.lyrics : "");
  const inputAuthor = document.getElementById("inputFinalAuthor");
  const authorText = inputAuthor ? inputAuthor.value.trim() : (origWork ? (origWork.author || "") : "");

  const btn = document.getElementById("btnSaveWork");
  const btnLeft = document.getElementById("btnSaveWorkLeft");
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span>⏳ 저장 중...</span>';
  }
  if (btnLeft) {
    btnLeft.disabled = true;
    btnLeft.innerHTML = '<span>⏳ 저장 중...</span>';
  }

  isSavingWork = true;
  try {
    const res = await fetch("/api/save_work", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        episode_no: targetEp,
        title: title,
        status: "완성 (승인 완료)",
        memory_anchor: memory,
        image_file: imageFile,
        art_direction: artDirection,
        poem_body: poem,
        author: authorText || "",
        recite_file: reciteFile,
        music_file: musicFile,
        audio_file: audioFile,
        lyrics: lyricsText || ""
      })
    });

    if (!res.ok) {
      throw new Error(`서버 응답 오류 (HTTP ${res.status})`);
    }

    const data = await res.json();
    
    // 처음 저장 vs 수정본 재저장 안내 토스트
    const successMsg = isUpdate 
      ? `✅ [${targetEp}] 「${title}」 수정본이 성공적으로 원고에 저장되었습니다!`
      : `🎉 [${targetEp}] 「${title}」 새 원고가 성공적으로 등록되었습니다!`;
    showToast(successMsg, "success");

    // 현재 작업 중인 회차를 기억하여, 이후 재저장 시 같은 화로 유지 (다음 화로 무단 복제 방지)
    currentEditingEpisode = targetEp;
    if (document.getElementById("inputEpisode")) {
      document.getElementById("inputEpisode").value = targetEp;
    }

    await loadProjects();
    await loadStatus();

    // loadStatus() 갱신 후에도 현재 편집 회차 유지
    if (currentEditingEpisode && document.getElementById("inputEpisode")) {
      document.getElementById("inputEpisode").value = currentEditingEpisode;
    }

    // 시니어 작가님을 위한 창작 ➔ 조판 원클릭 징검다리 안내창
    if (typeof Swal !== "undefined") {
      Swal.fire({
        title: "🌸 작품이 안전하게 저장되었습니다!",
        html: `
          <div style="font-size: 0.96rem; color: #4B382A; line-height: 1.7; padding: 6px; text-align: left;">
            <p style="margin-bottom: 8px;"><strong>[${targetEp}] 「${escapeHtml(title)}」</strong> 작품이 공식 원고에 안전하게 수록되었습니다.</p>
            <div style="background: #FFF9F2; border: 1px solid #EBD5C2; border-left: 4px solid #C85A17; padding: 10px 14px; border-radius: 6px; font-size: 0.88rem; color: #7C4A1E;">
              📖 <em>방금 다듬으신 시와 그림이 <strong>실물 책장에서 어떻게 펼쳐지는지</strong> 조판실로 가서 바로 확인해 보시겠습니까?</em>
            </div>
          </div>
        `,
        icon: "success",
        showCancelButton: true,
        confirmButtonText: "📖 내 책장으로 가서 조판 보기",
        cancelButtonText: "계속 여기서 시 쓰기",
        confirmButtonColor: "#C85A17",
        cancelButtonColor: "#8A6D56",
        reverseButtons: true
      }).then((result) => {
        if (result.isConfirmed) {
          if (currentStatus && currentStatus.works) {
            const wIdx = currentStatus.works.findIndex(w => w.episode_no === targetEp);
            if (wIdx >= 0) currentWorkIndex = wIdx;
          }
          const bookTabBtn = document.getElementById("tabBtnBook");
          if (bookTabBtn) {
            bookTabBtn.click();
          } else {
            const bookTab = document.querySelector('[data-target="panelBook"]');
            if (bookTab) bookTab.click();
          }
          renderBookSpread(currentWorkIndex);
        }
      });
    }

  } catch (err) {
    console.error("저장 중 오류:", err);
    showToast("❌ 저장 중 오류 발생: " + err.message, "error");
  } finally {
    isSavingWork = false;
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '<span>💾 시 · 그림 · 노래 전체 최종 저장하기</span>';
    }
    if (btnLeft) {
      btnLeft.disabled = false;
      btnLeft.innerHTML = '<span>📝 시 본문 우선 저장하기</span>';
    }
  }
}

// 11. 시화집 조판 편집 (출판 조판실 렌더링 & 넘침 감지)
let currentSpreadPart = 1; // 1: 전반부 (p.2-3), 2: 후반부 (p.4-5)
let customFontDelta = 0;   // 폰트 크기 미세 조율
let customLineDelta = 0;   // 줄간격 미세 조율

// =========================================================
// [조판 설정] 슬롯 매트릭스 지능형 N분할 & 레이아웃 헬퍼
// =========================================================
function splitPoemByChunks(rawLines, count) {
  if (count <= 1 || rawLines.length <= 6) {
    return [rawLines];
  }
  const total = rawLines.length;

  if (count === 2) {
    const mid = Math.floor(total / 2);
    let splitIdx = mid;
    for (let offset = 0; offset < Math.max(mid, total - mid); offset++) {
      if (mid - offset > 4 && rawLines[mid - offset].trim() === "") {
        splitIdx = mid - offset;
        break;
      }
      if (mid + offset < total - 4 && rawLines[mid + offset].trim() === "") {
        splitIdx = mid + offset;
        break;
      }
    }
    const c1 = rawLines.slice(0, splitIdx);
    let c2 = rawLines.slice(splitIdx);
    if (c2.length > 0 && c2[0].trim() === "") c2 = c2.slice(1);
    return [c1, c2];
  }

  if (count === 3) {
    const oneThird = Math.floor(total / 3);
    const twoThird = Math.floor((total * 2) / 3);

    let split1 = oneThird;
    for (let offset = 0; offset < Math.max(oneThird, total - oneThird); offset++) {
      if (oneThird - offset >= 3 && rawLines[oneThird - offset].trim() === "") {
        split1 = oneThird - offset;
        break;
      }
      if (oneThird + offset < twoThird && rawLines[oneThird + offset].trim() === "") {
        split1 = oneThird + offset;
        break;
      }
    }

    let split2 = twoThird;
    for (let offset = 0; offset < Math.max(total - twoThird, twoThird - split1); offset++) {
      if (twoThird - offset > split1 + 3 && rawLines[twoThird - offset].trim() === "") {
        split2 = twoThird - offset;
        break;
      }
      if (twoThird + offset < total - 3 && rawLines[twoThird + offset].trim() === "") {
        split2 = twoThird + offset;
        break;
      }
    }

    const c1 = rawLines.slice(0, split1);
    let c2 = rawLines.slice(split1, split2);
    let c3 = rawLines.slice(split2);
    if (c2.length > 0 && c2[0].trim() === "") c2 = c2.slice(1);
    if (c3.length > 0 && c3[0].trim() === "") c3 = c3.slice(1);
    return [c1, c2, c3];
  }

  if (count === 4) {
    const q1 = Math.floor(total / 4);
    const q2 = Math.floor(total / 2);
    const q3 = Math.floor((total * 3) / 4);

    let s1 = q1, s2 = q2, s3 = q3;
    for (let off = 0; off < 8; off++) {
      if (q1 - off >= 2 && rawLines[q1 - off].trim() === "") { s1 = q1 - off; break; }
      if (q1 + off < q2 && rawLines[q1 + off].trim() === "") { s1 = q1 + off; break; }
    }
    for (let off = 0; off < 8; off++) {
      if (q2 - off > s1 + 2 && rawLines[q2 - off].trim() === "") { s2 = q2 - off; break; }
      if (q2 + off < q3 && rawLines[q2 + off].trim() === "") { s2 = q2 + off; break; }
    }
    for (let off = 0; off < 8; off++) {
      if (q3 - off > s2 + 2 && rawLines[q3 - off].trim() === "") { s3 = q3 - off; break; }
      if (q3 + off < total - 2 && rawLines[q3 + off].trim() === "") { s3 = q3 + off; break; }
    }

    const c1 = rawLines.slice(0, s1);
    let c2 = rawLines.slice(s1, s2);
    let c3 = rawLines.slice(s2, s3);
    let c4 = rawLines.slice(s3);
    if (c2.length > 0 && c2[0].trim() === "") c2 = c2.slice(1);
    if (c3.length > 0 && c3[0].trim() === "") c3 = c3.slice(1);
    if (c4.length > 0 && c4[0].trim() === "") c4 = c4.slice(1);
    return [c1, c2, c3, c4];
  }

  return [rawLines];
}

function getNormalizedLayoutConfig(work) {
  if (work && work.layout_config && Array.isArray(work.layout_config.slots)) {
    const cfg = JSON.parse(JSON.stringify(work.layout_config));
    while (cfg.slots.length < 4) {
      cfg.slots.push((cfg.slots.length % 2 === 0) ? "image" : "text");
    }
    if (!cfg.image_settings) cfg.image_settings = {};
    if (!cfg.image_settings.page_1) {
      cfg.image_settings.page_1 = { mode: "image", file: work?.image_file || "" };
    }
    return cfg;
  }
  const rawSlots = (work && work.layout_config && work.layout_config.slots) ? work.layout_config.slots : null;
  const rawBodyLines = (work?.poem_body || "").split("\n").filter(l => l.trim().length > 0).length;

  let slots;
  if (rawSlots && rawSlots.length >= 2) {
    // 기존에 저장된 슬롯 구성이 있으면 그대로 유지 (짝수 개 보장)
    slots = [...rawSlots];
    if (slots.length % 2 !== 0) slots.push("blank");
  } else {
    // 본문 줄 수가 22줄을 초과하는 긴 시는 자동으로 4면(2펼침)으로 안착 (3면 본문, 4면 공백 또는 본문)
    if (rawBodyLines > 22) {
      slots = (rawBodyLines > 35) ? ["image", "text", "text", "text"] : ["image", "text", "text", "blank"];
    } else {
      slots = ["image", "text"];
    }
  }

  const p2Mode = (work && work.part2_mode) || "motif_symbol";
  const imageSettings = {
    page_1: { mode: "image", file: work?.image_file || "" }
  };
  if (slots.length >= 4) {
    imageSettings.page_3 = { 
      mode: p2Mode, 
      file: work?.image_file_2 || "", 
      motif_text: "여백 속에 머무는 시의 숨결" 
    };
  }

  return {
    page_count: slots.length,
    slots: slots,
    image_settings: imageSettings
  };
}

function formatPoemLinesHtml(lines) {
  return lines.map(ln => {
    const trimmed = ln.trim();
    if (!trimmed) {
      return '<div class="poem-line poem-line-empty" style="height: 1.1em;"></div>';
    }
    if (trimmed.startsWith(">>") || trimmed.startsWith("》》")) {
      const actualText = trimmed.replace(/^[>》\s]+/, '');
      return `<div class="poem-line" style="text-align: right; white-space: pre-wrap;">${escapeHtml(actualText)}</div>`;
    }
    return `<div class="poem-line" style="white-space: pre-wrap;">${escapeHtml(ln)}</div>`;
  }).join("");
}

// 캔바형 상하 혼합 슬롯 렌더링 헬퍼 (상단 그림형 / 하단 그림형)
function renderMixedSlotHtml(type, imgFile, title, lines, isFirst, isLast, fontSizeRem, lineSpacing) {
  const cleanImg = imgFile ? "/" + imgFile.replace(/^(\.\/|\/)/, '') : "";
  const fadeClass = (type === "image_top") ? "fade-bottom" : "fade-top";
  const textPosClass = (type === "image_top") ? "text-bottom" : "text-top";

  const imgTag = cleanImg 
    ? `<div class="slot-mixed-image ${fadeClass}"><img src="${cleanImg}?t=${Date.now()}" alt="시화 삽화"></div>`
    : `<div class="slot-mixed-image ${fadeClass}"><span style="font-size: 2rem;">🎨</span><span style="font-size: 0.8rem; color: #8A6D56; margin-left: 6px;">삽화 준비 중</span></div>`;

  const headerHtml = isFirst
    ? `<div class="poem-header-area"><h2 class="poem-header-title">${escapeHtml(title)}</h2></div>`
    : `<div style="font-size: 0.78rem; color: #9A7B66; font-style: italic; margin-bottom: 6px;">(이어서 계속)</div>`;

  const bodyContent = formatPoemLinesHtml(lines);
  const nextGuide = (!isLast) ? `<div style="margin-top: 8px; text-align: right; font-size: 0.75rem; color: #9A7B66; font-style: italic;">(다음 면에 계속 ➔)</div>` : "";

  const textTag = `
    <div class="slot-mixed-text ${textPosClass}">
      ${headerHtml}
      <div class="poem-display-body" style="font-size: ${fontSizeRem.toFixed(2)}rem; line-height: ${lineSpacing.toFixed(2)}; overflow: hidden !important;">
        ${bodyContent}
        ${nextGuide}
      </div>
    </div>
  `;

  if (type === "image_top") {
    return `<div class="slot-mixed-wrapper">${imgTag}${textTag}</div>`;
  } else {
    return `<div class="slot-mixed-wrapper">${textTag}${imgTag}</div>`;
  }
}


// =========================================================
// 📖 실물 펼침면 렌더링 엔진 (슬롯 매트릭스 & 1P/2P/4P 지원)
// =========================================================
function renderBookSpread(index) {
  if (!currentStatus || !currentStatus.works || currentStatus.works.length === 0) {
    return;
  }
  if (index < 0 || index >= currentStatus.works.length) return;

  currentWorkIndex = index;
  const work = currentStatus.works[index];
  const cfg = getNormalizedLayoutConfig(work);
  const pageCount = cfg.page_count || 2;

  document.getElementById("selectWorkDropdown").value = index;

  // 조판실 미니 낭송/노래 플레이어 버튼 상태 동기화
  updateViewerAudioButtons(work);

  // 1) 양면 펼침 기본 유지
  const spreadContainer = document.querySelector(".book-spread");
  if (spreadContainer) {
    spreadContainer.classList.remove("single-page-mode");
  }

  const totalSpreads = Math.max(1, Math.ceil(pageCount / 2));
  if (currentSpreadPart > totalSpreads) currentSpreadPart = totalSpreads;
  if (currentSpreadPart < 1) currentSpreadPart = 1;

  // 상단 총 면수 배지 & 삭제 버튼 상태 동기화
  const lblTotalPages = document.getElementById("lblTotalPagesBadge");
  if (lblTotalPages) {
    lblTotalPages.textContent = `📖 총 ${pageCount}면 (${totalSpreads}펼침)`;
  }
  const btnRemoveSpread = document.getElementById("btnRemoveSpread");
  if (btnRemoveSpread) {
    btnRemoveSpread.style.display = (pageCount > 2) ? "inline-flex" : "none";
  }

  // 조판 모드 버튼 상태 동기화
  const btnOpenLayoutConfig = document.getElementById("btnOpenLayoutConfig");
  if (btnOpenLayoutConfig) {
    btnOpenLayoutConfig.innerHTML = `<span>⚙ 조판 설정 (${pageCount}P)</span>`;
  }
  const rawLines = (work.poem_body || "").split("\n");

  // 2) 글(시 본문) 슬롯 매핑 & N분할 계산 (순수 본문 및 상하 혼합 슬롯 포함)
  const textSlotMap = {}; // slotIndex -> chunkIndex
  let textSlotCount = 0;
  for (let i = 0; i < pageCount; i++) {
    const s = cfg.slots[i];
    if (s === "text" || s === "image_top" || s === "image_bottom") {
      textSlotMap[i] = textSlotCount;
      textSlotCount++;
    }
  }

  const poemChunks = splitPoemByChunks(rawLines, Math.max(1, textSlotCount));

  // 3) 스마트 폰트 크기 및 행간 산출
  let maxChunkLines = 0;
  poemChunks.forEach(chk => { if (chk.length > maxChunkLines) maxChunkLines = chk.length; });
  let baseFontSize = 1.0;
  let baseLineHeight = 1.9;

  if (textSlotCount === 1) {
    if (maxChunkLines > 25) { baseFontSize = 0.80; baseLineHeight = 1.45; }
    else if (maxChunkLines > 18) { baseFontSize = 0.86; baseLineHeight = 1.60; }
    else if (maxChunkLines > 13) { baseFontSize = 0.92; baseLineHeight = 1.75; }
    else { baseFontSize = 1.0; baseLineHeight = 1.95; }
  } else {
    baseFontSize = (maxChunkLines > 20) ? 0.86 : 0.94;
    baseLineHeight = (maxChunkLines > 20) ? 1.65 : 1.82;
  }

  // 시니어 큰 활자본까지 시원시원하게 지원 (최대 2.80rem / 약 33.6pt 대폭 확장)
  const finalFontSize = Math.max(0.55, Math.min(2.80, baseFontSize + (customFontDelta * 0.05)));
  const finalLineHeight = Math.max(1.10, Math.min(3.20, baseLineHeight + (customLineDelta * 0.08)));

  // 4) 현재 펼침면에 대응하는 좌/우 슬롯 인덱스 계산
  const leftSlotIdx = (currentSpreadPart - 1) * 2;
  const rightSlotIdx = leftSlotIdx + 1;

  const leftType = cfg.slots[leftSlotIdx] || "image";
  const rightType = cfg.slots[rightSlotIdx] || "text";

  // 인라인 셀렉터 및 면 번호 라벨 동기화
  const selLeft = document.getElementById("selectPageTemplateLeft");
  if (selLeft) selLeft.value = leftType;
  const selRight = document.getElementById("selectPageTemplateRight");
  if (selRight) selRight.value = rightType;
  const toolsRight = document.getElementById("pageInlineToolsRight");
  if (toolsRight) toolsRight.style.display = (rightType === "image" || rightType === "image_top" || rightType === "image_bottom") ? "inline-flex" : "none";
  const toolsLeft = document.getElementById("pageInlineToolsLeft");
  if (toolsLeft) toolsLeft.style.display = (leftType === "image" || leftType === "image_top" || leftType === "image_bottom") ? "inline-flex" : "none";

  const lblLeft = document.getElementById("lblPageLeftNum");
  if (lblLeft) lblLeft.textContent = `${leftSlotIdx + 1}면(좌)`;
  const lblRight = document.getElementById("lblPageRightNum");
  if (lblRight) lblRight.textContent = `${rightSlotIdx + 1}면(우)`;

  // 5) 좌측 페이지 렌더링
  const imgElem = document.getElementById("viewerImage");
  const placeholder = document.getElementById("viewerImagePlaceholder");
  const mixedHolderLeft = document.getElementById("viewerMixedHolderLeft");
  const part2Holder = document.getElementById("viewerPart2LeftHolder");
  const poemArea = document.getElementById("viewerPart2PoemArea");
  const poemBodyPart2 = document.getElementById("viewerPart2PoemBody");

  const leftImgSetting = (cfg.image_settings && cfg.image_settings[`page_${leftSlotIdx + 1}`]) || {};
  const leftImgFile = leftImgSetting.file || (leftSlotIdx === 0 ? work.image_file : work.image_file_2);

  if (leftType === "image_top" || leftType === "image_bottom") {
    // 5-A) 상하 혼합 슬롯
    if (imgElem) imgElem.style.display = "none";
    if (placeholder) placeholder.style.display = "none";
    if (part2Holder) part2Holder.style.display = "none";
    if (mixedHolderLeft) {
      mixedHolderLeft.style.display = "flex";
      const cIdx = textSlotMap[leftSlotIdx] ?? 0;
      const chunkLines = poemChunks[cIdx] || [];
      const isFirst = (cIdx === 0);
      const isLast = (cIdx === textSlotCount - 1);
      mixedHolderLeft.innerHTML = renderMixedSlotHtml(leftType, leftImgFile, work.title, chunkLines, isFirst, isLast, finalFontSize, finalLineHeight);
    }
  } else if (leftType === "blank") {
    // 5-B) 문학적 여백 (1쪽 엽서 모드 또는 좌측 여백)
    if (imgElem) imgElem.style.display = "none";
    if (placeholder) placeholder.style.display = "none";
    if (mixedHolderLeft) mixedHolderLeft.style.display = "none";
    if (part2Holder) {
      part2Holder.style.display = "flex";
      const chipBtn = part2Holder.querySelector(".btn-part2-setting-chip");
      if (chipBtn) chipBtn.style.display = (leftSlotIdx === 2) ? "inline-flex" : "none";
      const imgElem2 = document.getElementById("viewerImage2");
      const symbolArea = document.getElementById("viewerPart2SymbolArea");
      const blankArea = document.getElementById("viewerPart2BlankArea");
      if (imgElem2) imgElem2.style.display = "none";
      if (poemArea) poemArea.style.display = "none";
      if (blankArea) blankArea.style.display = "none";
      if (symbolArea) {
        symbolArea.style.display = "flex";
        const motifText = symbolArea.querySelector(".part2-text");
        const motifSub = symbolArea.querySelector(".part2-subtext");
        if (motifText) motifText.textContent = "여백 속에 머무는 시의 숨결";
        if (motifSub) motifSub.textContent = (pageCount === 1) ? "엽서형 단독 조판 (마주보는 여백)" : "여백의 미학";
      }
    }
  } else if (leftType === "text") {
    // 5-C) 순수 시 본문
    if (imgElem) imgElem.style.display = "none";
    if (placeholder) placeholder.style.display = "none";
    if (mixedHolderLeft) mixedHolderLeft.style.display = "none";
    if (part2Holder) {
      part2Holder.style.display = "flex";
      const chipBtn = part2Holder.querySelector(".btn-part2-setting-chip");
      if (chipBtn) chipBtn.style.display = (leftSlotIdx === 2) ? "inline-flex" : "none";
      const imgElem2 = document.getElementById("viewerImage2");
      const symbolArea = document.getElementById("viewerPart2SymbolArea");
      const blankArea = document.getElementById("viewerPart2BlankArea");
      if (imgElem2) imgElem2.style.display = "none";
      if (symbolArea) symbolArea.style.display = "none";
      if (blankArea) blankArea.style.display = "none";
      if (poemArea) {
        poemArea.style.display = "flex";
        const chunkIdx = textSlotMap[leftSlotIdx] ?? 0;
        const lines = poemChunks[chunkIdx] || [];
        if (poemBodyPart2) {
          poemBodyPart2.innerHTML = formatPoemLinesHtml(lines);
          poemBodyPart2.style.fontSize = `${finalFontSize.toFixed(2)}rem`;
          poemBodyPart2.style.lineHeight = `${finalLineHeight.toFixed(2)}`;
        }
        const guideTop = poemArea.querySelector(".part2-poem-guide");
        if (guideTop) {
          guideTop.textContent = (chunkIdx > 0) ? `(${leftSlotIdx}면에 이어짐 ➔ ${leftSlotIdx + 1}면 본문)` : `(${leftSlotIdx + 1}면 본문)`;
        }
      }
    }
  } else {
    // 5-D) 전면 그림 (100%)
    if (mixedHolderLeft) mixedHolderLeft.style.display = "none";
    if (currentSpreadPart === 1 && leftSlotIdx === 0) {
      if (part2Holder) part2Holder.style.display = "none";
      if (leftImgFile) {
        const cleanImgPath = "/" + leftImgFile.replace(/^(\.\/|\/)/, '');
        imgElem.src = `${cleanImgPath}?t=${Date.now()}`;
        imgElem.style.display = "block";
        placeholder.style.display = "none";
        imgElem.onerror = () => {
          imgElem.style.display = "none";
          placeholder.style.display = "flex";
          placeholder.innerHTML = `<span style="font-size: 2.5rem;">🎨</span><span>삽화 이미지를 준비 중입니다.</span>`;
        };
      } else {
        imgElem.style.display = "none";
        placeholder.style.display = "flex";
        placeholder.innerHTML = `<span style="font-size: 2.5rem;">🎨</span><span>${leftSlotIdx + 1}면 삽화 준비 중</span>`;
      }
    } else {
      if (imgElem) imgElem.style.display = "none";
      if (placeholder) placeholder.style.display = "none";
      if (part2Holder) {
        part2Holder.style.display = "flex";
        const chipBtn = part2Holder.querySelector(".btn-part2-setting-chip");
        if (chipBtn) chipBtn.style.display = (leftSlotIdx === 2) ? "inline-flex" : "none";
        if (poemArea) poemArea.style.display = "none";
        const imgMode = leftImgSetting.mode || "image";
        const imgElem2 = document.getElementById("viewerImage2");
        const symbolArea = document.getElementById("viewerPart2SymbolArea");
        const blankArea = document.getElementById("viewerPart2BlankArea");

        if (imgMode === "image" && leftImgFile) {
          if (symbolArea) symbolArea.style.display = "none";
          if (blankArea) blankArea.style.display = "none";
          if (imgElem2) {
            const cleanImg2 = "/" + leftImgFile.replace(/^(\.\/|\/)/, '');
            imgElem2.src = `${cleanImg2}?t=${Date.now()}`;
            imgElem2.style.display = "block";
          }
        } else if (imgMode === "pure_blank") {
          if (imgElem2) imgElem2.style.display = "none";
          if (symbolArea) symbolArea.style.display = "none";
          if (blankArea) blankArea.style.display = "flex";
        } else {
          if (imgElem2) imgElem2.style.display = "none";
          if (blankArea) blankArea.style.display = "none";
          if (symbolArea) symbolArea.style.display = "flex";
        }
      }
    }
  }

  // 6) 우측 페이지 렌더링
  const rightPoemHolder = document.getElementById("viewerRightPoemHolder");
  const rightVisualHolder = document.getElementById("viewerRightVisualHolder");
  const mixedHolderRight = document.getElementById("viewerMixedHolderRight");

  const rightImgSetting = (cfg.image_settings && cfg.image_settings[`page_${rightSlotIdx + 1}`]) || {};
  const rightImgFile = rightImgSetting.file || work.image_file;

  if (rightType === "image_top" || rightType === "image_bottom") {
    // 6-A) 우측면 상하 혼합 슬롯 (엽서형)
    if (rightPoemHolder) rightPoemHolder.style.display = "none";
    if (rightVisualHolder) rightVisualHolder.style.display = "none";
    if (mixedHolderRight) {
      mixedHolderRight.style.display = "flex";
      const cIdx = textSlotMap[rightSlotIdx] ?? 0;
      const chunkLines = poemChunks[cIdx] || [];
      const isFirst = (cIdx === 0);
      const isLast = (cIdx === textSlotCount - 1);
      mixedHolderRight.innerHTML = renderMixedSlotHtml(rightType, rightImgFile, work.title, chunkLines, isFirst, isLast, finalFontSize, finalLineHeight);
    }
  } else if (rightType === "blank") {
    // 6-B) 우측면 문학적 여백 (1쪽 엽서 모드 마주보는 여백 등)
    if (mixedHolderRight) mixedHolderRight.style.display = "none";
    if (rightPoemHolder) rightPoemHolder.style.display = "none";
    if (rightVisualHolder) {
      rightVisualHolder.style.display = "flex";
      const rImg = document.getElementById("viewerRightImage");
      const rSymbol = document.getElementById("viewerRightSymbolArea");
      const rBlank = document.getElementById("viewerRightBlankArea");
      if (rImg) rImg.style.display = "none";
      if (rBlank) rBlank.style.display = "none";
      if (rSymbol) {
        rSymbol.style.display = "flex";
        const mText = document.getElementById("viewerRightMotifText");
        if (mText) mText.textContent = (pageCount === 1) ? "엽서형 단독 조판 (마주보는 여백)" : "여백 속에 머무는 시의 숨결";
      }
    }
  } else if (rightType === "text") {
    // 6-C) 우측면 순수 시 본문
    if (mixedHolderRight) mixedHolderRight.style.display = "none";
    if (rightVisualHolder) rightVisualHolder.style.display = "none";
    if (rightPoemHolder) rightPoemHolder.style.display = "flex";

    const chunkIdx = textSlotMap[rightSlotIdx] ?? 0;
    const lines = poemChunks[chunkIdx] || [];
    const isFirstTextSlot = (chunkIdx === 0);
    const isLastTextSlot = (chunkIdx === textSlotCount - 1);

    const headerArea = document.querySelector(".poem-header-area");
    if (headerArea) {
      headerArea.style.display = "block";
      headerArea.style.visibility = isFirstTextSlot ? "visible" : "hidden";
    }

    const titleElem = document.getElementById("viewerTitle");
    if (titleElem) titleElem.textContent = isFirstTextSlot ? work.title : `${work.title} Ⅱ`;

    const bodyElem = document.getElementById("viewerBody");
    if (bodyElem) {
      bodyElem.innerHTML = formatPoemLinesHtml(lines);
      bodyElem.style.fontSize = `${finalFontSize.toFixed(2)}rem`;
      bodyElem.style.lineHeight = `${finalLineHeight.toFixed(2)}`;
      bodyElem.style.overflow = "hidden";
      bodyElem.style.scrollbarWidth = "none";
    }
  } else {
    // 6-D) 우측면 전면 그림
    if (mixedHolderRight) mixedHolderRight.style.display = "none";
    if (rightPoemHolder) rightPoemHolder.style.display = "none";
    if (rightVisualHolder) {
      rightVisualHolder.style.display = "flex";
      const rImg = document.getElementById("viewerRightImage");
      const rSymbol = document.getElementById("viewerRightSymbolArea");
      const rBlank = document.getElementById("viewerRightBlankArea");

      if (rightImgFile) {
        if (rSymbol) rSymbol.style.display = "none";
        if (rBlank) rBlank.style.display = "none";
        if (rImg) {
          const cleanImg = "/" + rightImgFile.replace(/^(\.\/|\/)/, '');
          rImg.src = `${cleanImg}?t=${Date.now()}`;
          rImg.style.display = "block";
        }
      } else {
        if (rImg) rImg.style.display = "none";
        if (rBlank) rBlank.style.display = "none";
        if (rSymbol) rSymbol.style.display = "flex";
      }
    }
  }

  // 이전/다음 버튼 활성/비활성 제어
  document.getElementById("btnPrevWork").disabled = (index <= 0);
  document.getElementById("btnNextWork").disabled = (index >= currentStatus.works.length - 1);

  // 풍선도움말에 현재 세팅된 본문 글자 크기 및 줄간격 실시간 갱신
  updateTypographyTooltips(finalFontSize, finalLineHeight);

  // 책장 하단 양쪽 앞/뒤 페이지 이동 버튼 상태 및 인디케이터 갱신
  updatePageTurnButtons();

  // 실시간 종이 인쇄 영역 넘침(Overflow) 검사
  setTimeout(checkPageOverflow, 60);
}

// 실시간 본문 넘침 검사 및 상태 배지 갱신 (몇 줄 넘쳤는지 정밀 계산하여 상단 배지 & 하단 안전선에 동시 표시)
function checkPageOverflow() {
  const bodyElem = document.getElementById("viewerBody");
  const container = document.getElementById("poemBodyContainer");
  const badge = document.getElementById("layoutStatusBadge");
  const statusText = document.getElementById("layoutStatusText");
  const safetyLine = document.getElementById("printSafetyLine");

  if (!bodyElem || !container || !badge || !statusText) return;

  const maxSafeY = container.clientHeight - 28;
  const isOverflow = bodyElem.scrollHeight > maxSafeY;

  if (isOverflow) {
    // 1) 안전선 아래로 넘친 행(줄) 수 정밀 카운트
    const lineDivs = bodyElem.querySelectorAll(".poem-line");
    let overflowLines = 0;
    lineDivs.forEach(div => {
      if (div.offsetTop + (div.offsetHeight * 0.4) > maxSafeY) {
        overflowLines++;
      }
    });

    // 폴백 계산 (div 높이 미측정 시 스크롤 높이 기반 계산)
    if (overflowLines === 0) {
      const overflowPx = bodyElem.scrollHeight - maxSafeY;
      const computedLineH = parseFloat(window.getComputedStyle(bodyElem).lineHeight) || 22;
      overflowLines = Math.max(1, Math.ceil(overflowPx / computedLineH));
    }

    badge.className = "layout-badge badge-overflow";
    statusText.textContent = `⚠️ 본문 ${overflowLines}줄 넘침 (조판 조율 필요)`;
    bodyElem.classList.add("is-overflowing");
    const autoFitBtn = document.getElementById("btnSmartAutoFit");
    if (autoFitBtn) autoFitBtn.style.display = "inline-flex";

    if (safetyLine) {
      safetyLine.classList.add("line-warning");
      safetyLine.innerHTML = `<span>⚠️ 인쇄 안전선 (아래로 ${overflowLines}줄 초과 — 조판 조율 필요)</span>`;
      safetyLine.title = `현재 페이지 아래로 약 ${overflowLines}줄이 넘쳐 있습니다. [✨ 글자 크기 맞춤] 또는 [➕ 2쪽 추가]로 쾌적하게 조율해주세요.`;
    }
  } else {
    badge.className = "layout-badge badge-ok";
    const cfg = getNormalizedLayoutConfig(currentStatus?.works?.[currentWorkIndex]);
    const pCount = cfg.page_count || 2;
    statusText.textContent = (pCount > 2) ? `✅ ${pCount}면 연속 분절 안착` : "✅ 1페이지 안착 (조판 완벽)";
    bodyElem.classList.remove("is-overflowing");
    const autoFitBtn = document.getElementById("btnSmartAutoFit");
    if (autoFitBtn) autoFitBtn.style.display = "none";

    if (safetyLine) {
      safetyLine.classList.remove("line-warning");
      safetyLine.innerHTML = `<span>--- 인쇄 안전선 (Safe Printable Area) ---</span>`;
      safetyLine.title = "실제 종이 인쇄 안전 한계선: 글자가 이 선 아래로 내려가지 않아 안전하게 인쇄됩니다.";
    }
  }
}

// -------------------------------------------------------------
// ✨ 글자 크기 스마트 자동 맞춤 (현재 면에 쏙 들어가도록 폰트 미세 축소)
// -------------------------------------------------------------
function autoFitTextToCurrentSpread() {
  customFontDelta = Math.max(-8, customFontDelta - 2);
  renderBookSpread(currentWorkIndex);
  showToast("✨ 글자 크기를 조율하여 현재 면에 맞추었습니다.", "success");
}

// -------------------------------------------------------------
// ➕ 다음 펼침면(2쪽) 동적 추가 (긴 시 수용 및 연작 삽화 확장)
// -------------------------------------------------------------
async function addSpreadToCurrentWork() {
  if (!currentStatus || !currentStatus.works || !currentStatus.works[currentWorkIndex]) return;
  const work = currentStatus.works[currentWorkIndex];
  const cfg = getNormalizedLayoutConfig(work);

  const rawLines = (work.poem_body || "").split("\n").filter(l => l.trim().length > 0);
  const lineCount = rawLines.length;

  // 새로 추가되는 2면(한 펼침):
  // 좌측면(새 홀수면)은 기본적으로 본문(text)으로 하여 나머지 시를 분배,
  // 우측면(새 짝수면)은 본문이 길지 않으면 공백(blank), 장시면 본문(text)으로 분배!
  const leftNewSlot = "text";
  const rightNewSlot = (lineCount > 35) ? "text" : "blank";

  cfg.slots.push(leftNewSlot);
  cfg.slots.push(rightNewSlot);
  cfg.page_count = cfg.slots.length;
  work.layout_config = cfg;
  work.layout_mode = (cfg.page_count >= 4) ? "multi_page" : "compact";

  currentSpreadPart = Math.ceil(cfg.page_count / 2);

  await saveWorkLayoutConfigToServer(work.episode_no, cfg);
  renderBookSpread(currentWorkIndex);
  showToast(`📖 다음 펼침면이 추가되어 본문이 자연스럽게 분배되었습니다.`, "success");
}

// -------------------------------------------------------------
// ➖ 여분의 마지막 펼침면(2쪽) 삭제 (원문 100% 안전 보존 안심 확인창 연동)
// -------------------------------------------------------------
async function removeLastSpreadFromCurrentWork() {
  if (!currentStatus || !currentStatus.works || !currentStatus.works[currentWorkIndex]) return;
  const work = currentStatus.works[currentWorkIndex];
  const cfg = getNormalizedLayoutConfig(work);

  if (cfg.slots.length <= 2) {
    showToast("기본 2면(1펼침)은 책의 최소 단위이므로 더 이상 줄일 수 없습니다.", "warning");
    return;
  }

  const targetCount = cfg.slots.length - 2;

  // 시니어 작가님을 위한 크고 다정한 안심 확인창
  if (typeof Swal !== "undefined") {
    const result = await Swal.fire({
      title: "📖 마지막 2면을 줄이시겠습니까?",
      html: `
        <div style="font-size: 0.95rem; color: #4B382A; text-align: left; line-height: 1.7; padding: 4px;">
          <div style="background: #F0FDF4; border: 1.5px solid #BBF7D0; border-left: 4px solid #16A34A; padding: 10px 14px; border-radius: 6px; margin-bottom: 12px;">
            <strong style="color: #15803D; font-size: 0.96rem;">🔒 원고 본문 100% 안전 보존</strong><br>
            작가님이 정성껏 쓰신 <strong>시 원문(텍스트)은 글자 하나도 지워지지 않고 원고에 온전히 보존</strong>됩니다.
          </div>
          <p style="margin-bottom: 8px;">
            현재 <strong>총 ${cfg.page_count}면</strong>에서 마지막 2면을 접어 <strong>총 ${targetCount}면</strong>으로 정리합니다.
          </p>
          <div style="background: #FFFBEB; border: 1px dashed #F59E0B; padding: 8px 12px; border-radius: 6px; font-size: 0.85rem; color: #92400E;">
            💡 <em>안내: 면수가 줄어들어 본문이 넘치더라도, 언제든 상단의 <strong>[➕ 2쪽 추가]</strong>나 <strong>[✨ 글자 크기 맞춤]</strong>을 누르시면 다시 여유롭게 펼치실 수 있습니다.</em>
          </div>
        </div>
      `,
      icon: "question",
      showCancelButton: true,
      confirmButtonText: "네, 2쪽 줄이기",
      cancelButtonText: "그대로 두기",
      confirmButtonColor: "#C85A17",
      cancelButtonColor: "#8A6D56",
      reverseButtons: true
    });

    if (!result.isConfirmed) return;
  }

  cfg.slots.pop();
  cfg.slots.pop();
  cfg.page_count = cfg.slots.length;
  work.layout_config = cfg;
  work.layout_mode = (cfg.page_count >= 4) ? "multi_page" : "compact";

  const totalSpreads = Math.max(1, Math.ceil(cfg.page_count / 2));
  if (currentSpreadPart > totalSpreads) currentSpreadPart = totalSpreads;

  await saveWorkLayoutConfigToServer(work.episode_no, cfg);
  renderBookSpread(currentWorkIndex);
  showToast(`마지막 2면이 정리되어 총 ${cfg.page_count}면이 되었습니다. (시 본문은 안전하게 보존됩니다)`, "info");
}


// 조판 모드 전환 ('compact' 1페이지 압축 vs 'multi_page' 2페이지 연속 조판)
async function onToggleLayoutMode(newMode) {
  if (!currentStatus || !currentStatus.works || !currentStatus.works[currentWorkIndex]) return;
  const work = currentStatus.works[currentWorkIndex];
  work.layout_mode = newMode;
  currentSpreadPart = 1;

  // 백엔드에 조판 설정 영구 저장
  try {
    await fetch("/api/save_work_layout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        episode_no: work.episode_no,
        layout_mode: newMode,
        part2_mode: work.part2_mode || "motif_symbol",
        image_file_2: work.image_file_2 || ""
      })
    });
  } catch (err) {
    console.error("조판 모드 저장 실패:", err);
  }

  renderBookSpread(currentWorkIndex);

  // 2페이지 연속 조판(4P)을 선택했을 때, 4페이지 좌측면 연출을 결정하는 모달 팝업 자동 오픈!
  if (newMode === "multi_page") {
    openLayoutConfigModal();
  }
}

// =========================================================
// ⚙ 통합 조판 설정 (2P/4P 매트릭스 슬롯 시스템) 모달 컨트롤러
// =========================================================
let currentLayoutModalState = null;

function openLayoutConfigModal() {
  if (!currentStatus || !currentStatus.works || !currentStatus.works[currentWorkIndex]) return;
  const work = currentStatus.works[currentWorkIndex];
  const modal = document.getElementById("modalLayoutConfig");
  if (!modal) return;

  const baseCfg = getNormalizedLayoutConfig(work);
  // 깊은 복제
  currentLayoutModalState = JSON.parse(JSON.stringify(baseCfg));
  if (!currentLayoutModalState.image_settings) {
    currentLayoutModalState.image_settings = {};
  }
  if (!currentLayoutModalState.image_settings.page_1) {
    currentLayoutModalState.image_settings.page_1 = { mode: "image", file: work.image_file || "" };
  }
  if (!currentLayoutModalState.image_settings.page_3) {
    currentLayoutModalState.image_settings.page_3 = { mode: work.part2_mode || "motif_symbol", file: work.image_file_2 || "", motif_text: "여백 속에 머무는 시의 숨결" };
  }

  // 1) 편집 형식 라디오 체크
  const radiosCount = document.querySelectorAll('input[name="cfg_page_count"]');
  radiosCount.forEach(r => {
    r.checked = (parseInt(r.value) === currentLayoutModalState.page_count);
  });

  // 2) 매트릭스 라디오 체크
  for (let p = 1; p <= 4; p++) {
    const slotType = currentLayoutModalState.slots[p - 1] || ((p % 2 === 1) ? "image" : "text");
    const r = document.querySelector(`input[name="slot_type_${p}"][value="${slotType}"]`);
    if (r) r.checked = true;
  }

  updateLayoutMatrixVisibility();
  updateLayoutConfigSummaryText();
  renderImageSlotConfigsUI();

  modal.style.display = "flex";
}

function closeLayoutConfigModal() {
  const modal = document.getElementById("modalLayoutConfig");
  if (modal) modal.style.display = "none";
}

function onLayoutPageCountChange(count) {
  if (!currentLayoutModalState) return;
  count = parseInt(count);
  currentLayoutModalState.page_count = count;
  updateLayoutMatrixVisibility();
  updateLayoutConfigSummaryText();
  renderImageSlotConfigsUI();
}

function onLayoutSlotTypeChange(pageNumber, type) {
  if (!currentLayoutModalState) return;
  currentLayoutModalState.slots[pageNumber - 1] = type;
  updateLayoutConfigSummaryText();
  renderImageSlotConfigsUI();
}

function updateLayoutMatrixVisibility() {
  if (!currentLayoutModalState) return;
  const count = currentLayoutModalState.page_count;
  const is1P = (count === 1);
  const is4P = (count === 4);

  document.querySelectorAll(".col-2p-cell").forEach(el => {
    el.style.display = is1P ? "none" : "";
  });
  document.querySelectorAll(".col-4p-cell").forEach(el => {
    el.style.display = is4P ? "" : "none";
  });
}

function updateLayoutConfigSummaryText() {
  if (!currentLayoutModalState) return;
  const count = currentLayoutModalState.page_count;
  const slots = currentLayoutModalState.slots.slice(0, count);
  const hintElem = document.getElementById("layoutConfigSummaryHint");
  if (!hintElem) return;

  const desc = slots.map((s, idx) => {
    let name = "글";
    if (s === "image") name = "전면그림";
    else if (s === "image_top") name = "상단그림";
    else if (s === "image_bottom") name = "하단그림";
    else if (s === "blank") name = "여백";
    return `[${idx + 1}면: ${name}]`;
  }).join(" ➔ ");

  let note = "";
  if (count === 1) {
    note = "💌 1쪽 엽서형 조판 (양면 펼침: 엽서 + 마주보는 여백)";
  } else if (count === 2) {
    if (slots[0] === "image" && slots[1] === "text") note = "정통 1세트 시화집 (좌측 그림 + 우측 본문)";
    else if (slots[0] === "image_top" && slots[1] === "image_bottom") note = "긴 시 유기적 시작과 여운 조판 (첫머리+마무리)";
    else note = "자유 맞춤 2면 조판";
  } else {
    note = "4페이지 대서사/연작 시화집 조판";
  }
  hintElem.textContent = `ℹ 현재 구성: ${desc} — ${note}`;
}

// -------------------------------------------------------------
// 캔바형 원터치 프리셋 적용 (1쪽 엽서 / 2쪽 마주보기 / 4쪽 대서사)
// -------------------------------------------------------------
async function applyLayoutPreset(presetCount) {
  if (!currentStatus || !currentStatus.works || !currentStatus.works[currentWorkIndex]) return;
  const work = currentStatus.works[currentWorkIndex];

  let newSlots = ["image", "text", "image", "text"];
  let newMode = "compact";

  if (presetCount === 1) {
    newMode = "single_page";
    newSlots = ["image_top", "blank", "image", "text"];
  } else if (presetCount === 2) {
    newMode = "compact";
    newSlots = ["image", "text", "image", "text"];
  } else if (presetCount === 4) {
    newMode = "multi_page";
    newSlots = ["image", "text", "image", "text"];
  }

  const newConfig = {
    page_count: presetCount,
    slots: newSlots,
    image_settings: {
      page_1: { mode: "image", file: work.image_file || "" },
      page_3: { mode: work.part2_mode || "motif_symbol", file: work.image_file_2 || "", motif_text: "여백 속에 머무는 시의 숨결" }
    }
  };

  work.layout_config = newConfig;
  work.layout_mode = newMode;
  currentSpreadPart = 1;

  await saveWorkLayoutConfigToServer(work.episode_no, newConfig);
  renderBookSpread(currentWorkIndex);

  if (presetCount === 4) {
    showToast("📚 4쪽 대서사로 확장되었습니다! 본문 하단 또는 책장 아래의 [2부: 3-4면] 단추를 누르시면 3·4면(뒷부분)이 열립니다.", "info");
  } else if (presetCount === 1) {
    showToast("💌 1쪽 엽서형 조판으로 변경되었습니다.", "info");
  } else {
    showToast("📖 정통 2쪽 마주보기 조판으로 변경되었습니다.", "info");
  }
}

// -------------------------------------------------------------
// 책장 위 인라인 템플릿 실시간 변경 (좌측/우측 드롭다운 변경 시)
// -------------------------------------------------------------
async function onInlineTemplateChange(side, templateValue) {
  if (!currentStatus || !currentStatus.works || !currentStatus.works[currentWorkIndex]) return;
  const work = currentStatus.works[currentWorkIndex];
  const cfg = getNormalizedLayoutConfig(work);

  const leftSlotIdx = (currentSpreadPart - 1) * 2;
  const rightSlotIdx = leftSlotIdx + 1;
  const slotIdx = (side === "left") ? leftSlotIdx : rightSlotIdx;

  cfg.slots[slotIdx] = templateValue;

  // 사용자가 좌측면을 그림/상단그림형/여백 등으로 변경했을 때,
  // 만약 우측면이 공백(blank) 상태라면 시 본문이 우측면으로 자연스럽게 밀려나서 수용되도록 text로 자동 전환!
  if (side === "left" && templateValue !== "text") {
    if (cfg.slots[rightSlotIdx] === "blank") {
      cfg.slots[rightSlotIdx] = "text";
    }
  }

  cfg.page_count = cfg.slots.length;
  work.layout_mode = (cfg.page_count >= 4) ? "multi_page" : "compact";
  work.layout_config = cfg;

  const savedPart = currentSpreadPart;
  await saveWorkLayoutConfigToServer(work.episode_no, cfg);
  currentSpreadPart = savedPart;
  renderBookSpread(currentWorkIndex);
}

// -------------------------------------------------------------
// 캔바형 통합 삽화 관리 모달 (AI 새 삽화 생성 & 내 파일 업로드 완전 통합)
// -------------------------------------------------------------
async function openSlotImageManager(side) {
  if (!currentStatus || !currentStatus.works || !currentStatus.works[currentWorkIndex]) return;
  const work = currentStatus.works[currentWorkIndex];
  
  const slotIdx = (side === "left") 
    ? (currentSpreadPart - 1) * 2 
    : (currentSpreadPart - 1) * 2 + 1;

  const pageNum = slotIdx + 1;
  const pageLabel = `${pageNum}면 (${side === 'left' ? '좌측' : '우측'})`;
  currentViewerTargetSlot = (pageNum >= 3) ? "part2" : "main";

  if (typeof Swal !== "undefined") {
    await Swal.fire({
      title: `🎨 [${pageLabel}] 삽화 관리 & 교체`,
      html: `
        <div style="font-size: 0.92rem; color: #5C3818; margin-bottom: 1.25rem; line-height: 1.6;">
          현재 작품: <strong>「${escapeHtml(work.title)}」</strong><br>
          이 페이지에 들어갈 삽화를 어떻게 구성하시겠습니까?
        </div>
        <div style="display: flex; flex-direction: column; gap: 10px;">
          <button type="button" id="swalBtnGenAi" class="swal2-confirm swal2-styled" style="background: #C85A17; margin: 0; padding: 12px 16px; font-size: 0.95rem; font-weight: 700; border-radius: 8px; display: flex; align-items: center; justify-content: center; gap: 8px; box-shadow: 0 2px 6px rgba(200,90,23,0.25);">
            <span>⚡ AI 새 삽화 자동 생성 (시안 2종 추천)</span>
          </button>
          <button type="button" id="swalBtnUploadFile" class="swal2-confirm swal2-styled" style="background: #2563EB; margin: 0; padding: 12px 16px; font-size: 0.95rem; font-weight: 700; border-radius: 8px; display: flex; align-items: center; justify-content: center; gap: 8px; box-shadow: 0 2px 6px rgba(37,99,235,0.25);">
            <span>📁 내 컴퓨터에서 사진/그림 올리기</span>
          </button>
        </div>
      `,
      showConfirmButton: false,
      showCancelButton: true,
      cancelButtonText: "취소",
      cancelButtonColor: "#8A6D56",
      didOpen: () => {
        const genBtn = document.getElementById("swalBtnGenAi");
        const uploadBtn = document.getElementById("swalBtnUploadFile");

        if (genBtn) {
          genBtn.addEventListener("click", () => {
            Swal.close();
            if (pageNum >= 3) {
              executeGenPart2Image();
            } else {
              onViewerGenerateFreeImage();
            }
          });
        }

        if (uploadBtn) {
          uploadBtn.addEventListener("click", () => {
            Swal.close();
            triggerViewerFileInput();
          });
        }
      }
    });
  } else {
    const choice = prompt(`[${pageLabel}] 삽화 변경 방식을 선택하세요:\n1: AI 새 삽화 자동 생성\n2: 내 컴퓨터 파일 올리기\n취소: ESC`);
    if (choice === "1") {
      if (pageNum >= 3) executeGenPart2Image();
      else onViewerGenerateFreeImage();
    } else if (choice === "2") {
      triggerViewerFileInput();
    }
  }
}

// 하위 호환성 유지용 별칭
function triggerInlineAiImage(side) {
  openSlotImageManager(side);
}

// 백엔드 영구 저장 공통 헬퍼
async function saveWorkLayoutConfigToServer(episodeNo, layoutConfig) {
  try {
    await fetch("/api/save_work_layout_config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        episode_no: episodeNo,
        layout_config: layoutConfig
      })
    });
  } catch (err) {
    console.error("조판 설정 영구 저장 실패:", err);
  }
}

function renderImageSlotConfigsUI() {
  if (!currentLayoutModalState) return;
  const container = document.getElementById("containerImageSlotConfigs");
  if (!container) return;

  const count = currentLayoutModalState.page_count;
  const imagePages = [];
  for (let i = 0; i < count; i++) {
    if (currentLayoutModalState.slots[i] === "image") {
      imagePages.push(i + 1);
    }
  }

  if (imagePages.length === 0) {
    container.innerHTML = `
      <div style="padding: 12px; background: #F8FAFC; border: 1px dashed #CBD5E1; border-radius: 8px; font-size: 0.85rem; color: #64748B; text-align: center;">
        ✍️ 모든 페이지가 '글'로 지정되었습니다. (그림 없이 시 본문만 조판됩니다)
      </div>
    `;
    return;
  }

  const work = currentStatus.works[currentWorkIndex];
  container.innerHTML = imagePages.map(pageNum => {
    const pageKey = `page_${pageNum}`;
    const setting = currentLayoutModalState.image_settings[pageKey] || {
      mode: (pageNum === 1) ? "image" : (work.part2_mode || "motif_symbol"),
      file: (pageNum === 1) ? (work.image_file || "") : (work.image_file_2 || ""),
      motif_text: "여백 속에 머무는 시의 숨결"
    };
    currentLayoutModalState.image_settings[pageKey] = setting;

    const isImage = (setting.mode === "image");
    const isMotif = (setting.mode === "motif_symbol");
    const isBlank = (setting.mode === "pure_blank");

    return `
      <div class="slot-image-card" style="background: #FFFDF9; border: 1px solid #E5D5C5; border-radius: 8px; padding: 12px 14px;">
        <div style="font-weight: 700; font-size: 0.88rem; color: #5C3818; margin-bottom: 8px; display: flex; align-items: center; justify-content: space-between;">
          <span>🎨 [${pageNum}면] 그림 상세 연출</span>
          <span style="font-size: 0.76rem; color: var(--text-muted); font-weight: normal;">(좌/우 펼침 위치: ${pageNum % 2 === 1 ? '좌측면' : '우측면'})</span>
        </div>
        <div style="display: flex; gap: 14px; flex-wrap: wrap; font-size: 0.82rem;">
          <label style="display: flex; align-items: center; gap: 6px; cursor: pointer;">
            <input type="radio" name="img_mode_p${pageNum}" value="image" ${isImage ? 'checked' : ''} onchange="onSlotImageModeChange(${pageNum}, 'image')">
            <span>🖼️ 삽화 이미지 사용</span>
          </label>
          <label style="display: flex; align-items: center; gap: 6px; cursor: pointer;">
            <input type="radio" name="img_mode_p${pageNum}" value="motif_symbol" ${isMotif ? 'checked' : ''} onchange="onSlotImageModeChange(${pageNum}, 'motif_symbol')">
            <span>❦ 문학적 여백 심볼</span>
          </label>
          <label style="display: flex; align-items: center; gap: 6px; cursor: pointer;">
            <input type="radio" name="img_mode_p${pageNum}" value="pure_blank" ${isBlank ? 'checked' : ''} onchange="onSlotImageModeChange(${pageNum}, 'pure_blank')">
            <span>🤍 완전한 순백 여백</span>
          </label>
        </div>
        ${(pageNum >= 3) ? `
          <div style="margin-top: 8px; display: flex; gap: 8px; align-items: center;">
            <button type="button" class="btn-micro" onclick="executeGenPart2Image()" style="background: #2563EB; color: white; border: none; padding: 4px 10px; font-weight: 600;">
              <span>⚡ ${pageNum}면 연작 삽화 무료 자동 생성</span>
            </button>
            <span style="font-size: 0.78rem; color: var(--text-muted);">
              ${setting.file ? `(현재 파일: ${setting.file.split('/').pop()})` : '(등록된 이미지 없음)'}
            </span>
          </div>
        ` : `
          <div style="margin-top: 6px; font-size: 0.78rem; color: var(--text-muted);">
            ${setting.file ? `등록 파일: ${setting.file.split('/').pop()}` : '소장 그림 또는 AI로 생성된 기본 삽화가 표시됩니다.'}
          </div>
        `}
      </div>
    `;
  }).join("");
}

function onSlotImageModeChange(pageNum, mode) {
  if (!currentLayoutModalState) return;
  const pageKey = `page_${pageNum}`;
  if (!currentLayoutModalState.image_settings[pageKey]) {
    currentLayoutModalState.image_settings[pageKey] = {};
  }
  currentLayoutModalState.image_settings[pageKey].mode = mode;
}

async function applyLayoutConfigSettings() {
  if (!currentStatus || !currentStatus.works || !currentStatus.works[currentWorkIndex]) return;
  const work = currentStatus.works[currentWorkIndex];
  if (!currentLayoutModalState) return;

  if (!Array.isArray(currentLayoutModalState.slots)) {
    currentLayoutModalState.slots = ["image", "text", "image", "text"];
  }
  while (currentLayoutModalState.slots.length < 4) {
    currentLayoutModalState.slots.push((currentLayoutModalState.slots.length % 2 === 0) ? "image" : "text");
  }

  try {
    const res = await fetch("/api/save_work_layout_config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        episode_no: work.episode_no,
        layout_config: currentLayoutModalState
      })
    });
    const data = await res.json();
    if (data.success) {
      work.layout_config = currentLayoutModalState;
      work.layout_mode = (currentLayoutModalState.page_count === 4) ? "multi_page" : "compact";
      currentSpreadPart = 1;
      showToast("✅ 조판 설정이 성공적으로 반영 및 저장되었습니다.");
    }
  } catch (err) {
    console.error("조판 설정 저장 오류:", err);
    showToast(`❌ 조판 설정 저장 실패: ${err.message}`, "error");
  }

  closeLayoutConfigModal();
  renderBookSpread(currentWorkIndex);
}

// =========================================================
// 4P 연속 조판 2부 좌측 페이지(4면) 연출 모달 컨트롤러 (호환 유지)
// =========================================================
let currentP4SelectedMode = "motif_symbol";

function openMultiPageLeftModal() {
  openLayoutConfigModal();
}

function closeMultiPageLeftModal() {
  closeLayoutConfigModal();
}

function onP4OptionChange(mode) {
  currentP4SelectedMode = mode;

  // 모든 카드의 active 클래스 갱신
  document.getElementById("cardOptImageGen")?.classList.toggle("active", mode === "image");
  document.getElementById("cardOptUpload")?.classList.toggle("active", mode === "image_upload");
  document.getElementById("cardOptMotif")?.classList.toggle("active", mode === "motif_symbol");
  document.getElementById("cardOptBlank")?.classList.toggle("active", mode === "pure_blank");
  document.getElementById("cardOptPoemText")?.classList.toggle("active", mode === "poem_text");

  // 서브 액션 row 표시 제어
  const rowGen = document.getElementById("p4ImageGenActionRow");
  if (rowGen) rowGen.style.display = (mode === "image") ? "flex" : "none";

  const rowUpload = document.getElementById("p4UploadActionRow");
  if (rowUpload) rowUpload.style.display = (mode === "image_upload") ? "flex" : "none";

  const rowMotif = document.getElementById("p4MotifActionRow");
  if (rowMotif) rowMotif.style.display = (mode === "motif_symbol") ? "flex" : "none";
}

// 2부 연작 삽화 AI 자동 생성 실행 (시 후반부 정경 분석 연작 프롬프트 연동 & 미리보기 모달 팝업)
async function executeGenPart2Image() {
  if (!currentStatus || !currentStatus.works || !currentStatus.works[currentWorkIndex]) return;
  const work = currentStatus.works[currentWorkIndex];
  const btn = document.getElementById("btnGenPart2Image");
  const statusElem = document.getElementById("p4ImageGenStatus");

  if (btn) btn.disabled = true;
  if (statusElem) statusElem.textContent = "⏳ 시 후반부 정경 분석 및 연작 수채화 생성 중... (약 3초)";

  try {
    const res = await fetch("/api/generate_part2_image", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        episode_no: work.episode_no,
        prompt: "" // 백엔드에서 시 후반부(Part 2) 본문을 정밀 분석한 전용 연작 프롬프트로 자동 조립
      })
    });
    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.detail || data.error || "생성 실패");
    }

    if (statusElem) statusElem.textContent = `✓ 연작 삽화 생성 완료! 미리보기 창에서 확인하세요.`;

    // 4P 설정 모달 닫기
    closeMultiPageLeftModal();

    // 2부 연작 전용 미리보기 모달 열기
    openImagePreviewConfirmModal({
      episode_no: work.episode_no,
      title: work.title,
      filename: data.filename,
      image_url: data.image_url,
      target_slot: "part2"
    });

  } catch (err) {
    if (statusElem) statusElem.textContent = `❌ 생성 실패: ${err.message}`;
    showToast(`❌ 2부 연작 삽화 생성 실패: ${err.message}`, "error");
  } finally {
    if (btn) btn.disabled = false;
  }
}

// 내 컴퓨터에서 2부 삽화 파일 업로드 선택 시
async function onMultiPageFileSelected(event) {
  const file = event.target.files && event.target.files[0];
  if (!file) return;

  if (!currentStatus || !currentStatus.works || !currentStatus.works[currentWorkIndex]) return;
  const work = currentStatus.works[currentWorkIndex];
  const statusElem = document.getElementById("p4UploadStatus");
  if (statusElem) statusElem.textContent = "⏳ 파일 업로드 및 300DPI 보정 중...";

  const formData = new FormData();
  formData.append("file", file);
  formData.append("episode_no", work.episode_no);
  formData.append("target_slot", "part2");

  try {
    const res = await fetch("/api/upload_image", {
      method: "POST",
      body: formData
    });
    const data = await res.json();
    if (data.success) {
      work.image_file_2 = `./images/${data.filename}`;
      work.part2_mode = "image";
      currentP4SelectedMode = "image";
      if (statusElem) statusElem.textContent = `✅ 등록 완료! (${data.filename})`;
      showToast(data.message || "2부 삽화가 등록되었습니다.");
      renderBookSpread(currentWorkIndex);
    } else {
      if (statusElem) statusElem.textContent = `❌ 등록 실패: ${data.detail || '오류'}`;
    }
  } catch (err) {
    if (statusElem) statusElem.textContent = `❌ 오류: ${err.message}`;
  }
}

// 모달에서 [이 설정으로 조판 확정] 클릭 시 저장
async function applyMultiPageLeftSettings() {
  if (!currentStatus || !currentStatus.works || !currentStatus.works[currentWorkIndex]) return;
  const work = currentStatus.works[currentWorkIndex];

  let finalMode = currentP4SelectedMode;
  if (finalMode === "image_upload") finalMode = "image";

  work.part2_mode = finalMode;

  try {
    const res = await fetch("/api/save_work_layout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        episode_no: work.episode_no,
        layout_mode: work.layout_mode || "multi_page",
        part2_mode: finalMode,
        image_file_2: work.image_file_2 || ""
      })
    });
    const data = await res.json();
    if (data.success) {
      showToast("4페이지 좌측면 연출 설정이 저장되었습니다.");
    }
  } catch (err) {
    console.error("4P 설정 저장 오류:", err);
  }

  closeMultiPageLeftModal();
  renderBookSpread(currentWorkIndex);
}

// 2페이지 연속 조판 시 1부(전반부) / 2부(후반부) 펼침면 전환
function switchSpreadPart(part) {
  currentSpreadPart = part;
  renderBookSpread(currentWorkIndex);
}

// -------------------------------------------------------------
// [책장 하단 양쪽] 앞/뒤 페이지(펼침면) 연속 이동 엔진
// - 내부: 현재 시의 펼침면(1부 ➔ 2부 ➔ 3부...) 순차 이동
// - 경계선: 앞 시(작품) 또는 다음 시(작품)로 연속 이동
// -------------------------------------------------------------
function navigatePage(delta) {
  if (!currentStatus || !currentStatus.works || currentStatus.works.length === 0) return;
  const work = currentStatus.works[currentWorkIndex];
  const cfg = getNormalizedLayoutConfig(work);
  const pageCount = cfg.page_count || 2;
  const totalSpreads = Math.max(1, Math.ceil(pageCount / 2));

  if (delta === 1) {
    // [다음 페이지 ▶] 클릭
    if (currentSpreadPart < totalSpreads) {
      // 1) 현재 시의 다음 펼침면으로 책장 넘김!
      currentSpreadPart++;
      renderBookSpread(currentWorkIndex);
    } else {
      // 2) 현재 시의 마지막 펼침면이면 -> 다음 작품(시)으로 이동!
      if (currentWorkIndex < currentStatus.works.length - 1) {
        currentWorkIndex++;
        currentSpreadPart = 1; // 다음 시의 첫 면부터 시작
        renderBookSpread(currentWorkIndex);
      } else {
        showToast("시화집의 마지막 페이지입니다.", "info");
      }
    }
  } else if (delta === -1) {
    // [◀ 이전 페이지] 클릭
    if (currentSpreadPart > 1) {
      // 1) 현재 시의 이전 펼침면으로 책장 넘김!
      currentSpreadPart--;
      renderBookSpread(currentWorkIndex);
    } else {
      // 2) 현재 시의 첫 펼침면이면 -> 이전 작품(시)으로 이동!
      if (currentWorkIndex > 0) {
        currentWorkIndex--;
        const prevWork = currentStatus.works[currentWorkIndex];
        const prevCfg = getNormalizedLayoutConfig(prevWork);
        const prevPageCount = prevCfg.page_count || 2;
        const prevTotalSpreads = Math.max(1, Math.ceil(prevPageCount / 2));
        // 이전 작품의 마지막 펼침면으로 펼침!
        currentSpreadPart = prevTotalSpreads;
        renderBookSpread(currentWorkIndex);
      } else {
        showToast("시화집의 첫 페이지입니다.", "info");
      }
    }
  }
}

// 책장 하단 양쪽 페이지 이동 화살표 버튼 상태 및 쪽수 인디케이터 갱신
function updatePageTurnButtons() {
  const btnPrev = document.getElementById("btnPageTurnPrev");
  const btnNext = document.getElementById("btnPageTurnNext");
  const indicator = document.getElementById("pageTurnIndicator");

  if (!currentStatus || !currentStatus.works || currentStatus.works.length === 0) return;
  const work = currentStatus.works[currentWorkIndex];
  const cfg = getNormalizedLayoutConfig(work);
  const pageCount = cfg.page_count || 2;
  const totalSpreads = Math.max(1, Math.ceil(pageCount / 2));

  const isFirstPage = (currentWorkIndex === 0 && currentSpreadPart === 1);
  const isLastWork = (currentWorkIndex === currentStatus.works.length - 1);
  const isLastSpread = (currentSpreadPart === totalSpreads);
  const isFinalPage = isLastWork && isLastSpread;

  const leftSlotNum = (currentSpreadPart - 1) * 2 + 1;
  const rightSlotNum = leftSlotNum + 1;

  if (btnPrev) {
    btnPrev.disabled = isFirstPage;
    if (isFirstPage) {
      btnPrev.title = "시화집의 첫 페이지입니다.";
    } else if (currentSpreadPart > 1) {
      btnPrev.title = `[이전 면] 「${work.title}」 앞 펼침면으로 책장을 넘깁니다.`;
    } else if (currentWorkIndex > 0) {
      const prevTitle = currentStatus.works[currentWorkIndex - 1]?.title || '이전 시';
      btnPrev.title = `[이전 시] 이전 작품 「${prevTitle}」의 마지막 면으로 책장을 넘깁니다.`;
    }
  }

  if (btnNext) {
    btnNext.disabled = isFinalPage;
    if (isFinalPage) {
      btnNext.title = "시화집의 마지막 페이지입니다.";
    } else if (currentSpreadPart < totalSpreads) {
      btnNext.title = `[다음 면] 「${work.title}」 다음 펼침면으로 책장을 넘깁니다.`;
    } else if (currentWorkIndex < currentStatus.works.length - 1) {
      const nextTitle = currentStatus.works[currentWorkIndex + 1]?.title || '다음 시';
      btnNext.title = `[다음 시] 다음 작품 「${nextTitle}」의 첫 면으로 책장을 넘깁니다.`;
    }
  }

  if (indicator) {
    const epLabel = work.episode_no || `제${String(currentWorkIndex + 1).padStart(2, '0')}화`;
    if (totalSpreads > 1) {
      indicator.innerHTML = `<strong>${epLabel} 「${escapeHtml(work.title)}」</strong> <span style="color: #C85A17; margin-left: 6px;">[${leftSlotNum}·${rightSlotNum}면 / 총 ${pageCount}면 (${currentSpreadPart}/${totalSpreads}부)]</span>`;
    } else {
      indicator.innerHTML = `<strong>${epLabel} 「${escapeHtml(work.title)}」</strong> <span style="color: #8A6D56; margin-left: 6px;">[${leftSlotNum}·${rightSlotNum}면 펼침]</span>`;
    }
  }
}

// -------------------------------------------------------------
// 🎧 조판실 실시간 미니 감상 플레이어 (내 목소리 낭송 / 서정 노래)
// -------------------------------------------------------------
let currentViewerAudioType = null;

function updateViewerAudioButtons(work) {
  const btnRecite = document.getElementById("btnViewerPlayRecite");
  const btnSong = document.getElementById("btnViewerPlaySong");
  const audioEl = document.getElementById("viewerAudioElement");

  // 이전 재생 정지
  if (audioEl && !audioEl.paused) {
    audioEl.pause();
    currentViewerAudioType = null;
  }

  const hasRecite = !!(work && (work.recite_file || (work.audio_file && work.audio_file.includes("낭송"))));
  const hasSong = !!(work && (work.music_file || (work.audio_file && !work.audio_file.includes("낭송"))));

  if (btnRecite) {
    btnRecite.style.display = hasRecite ? "inline-flex" : "none";
    const lbl = document.getElementById("lblViewerPlayRecite");
    if (lbl) lbl.textContent = "🎧 낭송 듣기";
  }

  if (btnSong) {
    btnSong.style.display = hasSong ? "inline-flex" : "none";
    const lbl = document.getElementById("lblViewerPlaySong");
    if (lbl) lbl.textContent = "🎵 노래 듣기";
  }
}

function toggleViewerAudio(type) {
  if (!currentStatus || !currentStatus.works || !currentStatus.works[currentWorkIndex]) return;
  const work = currentStatus.works[currentWorkIndex];
  const audioEl = document.getElementById("viewerAudioElement");
  if (!audioEl) return;

  const lblRecite = document.getElementById("lblViewerPlayRecite");
  const lblSong = document.getElementById("lblViewerPlaySong");

  // 현재 같은 오디오가 재생 중이면 일시정지
  if (currentViewerAudioType === type && !audioEl.paused) {
    audioEl.pause();
    currentViewerAudioType = null;
    if (lblRecite) lblRecite.textContent = "🎧 낭송 듣기";
    if (lblSong) lblSong.textContent = "🎵 노래 듣기";
    showToast("음원 재생을 일시정지했습니다.", "info");
    return;
  }

  let fileUrl = "";
  if (type === "recite") {
    fileUrl = work.recite_file || work.audio_file;
  } else if (type === "song") {
    fileUrl = work.music_file || work.audio_file;
  }

  if (!fileUrl) {
    showToast("등록된 음원이 없습니다.", "warning");
    return;
  }

  const cleanUrl = "/" + fileUrl.replace(/^(\.\/|\/)/, '');
  audioEl.src = `${cleanUrl}?t=${Date.now()}`;
  audioEl.play().then(() => {
    currentViewerAudioType = type;
    if (lblRecite) lblRecite.textContent = (type === "recite") ? "⏸ 낭송 정지" : "🎧 낭송 듣기";
    if (lblSong) lblSong.textContent = (type === "song") ? "⏸ 노래 정지" : "🎵 노래 듣기";
    const title = (type === "recite") ? `「${work.title}」 시낭송` : `「${work.title}」 노래`;
    showToast(`▶ ${title}을(를) 책장과 함께 감상합니다.`, "info");
  }).catch(err => {
    console.warn("오디오 재생 오류:", err);
    showToast("음원 파일을 불러오지 못했습니다.", "error");
  });
}

function onViewerAudioEnded() {
  currentViewerAudioType = null;
  const lblRecite = document.getElementById("lblViewerPlayRecite");
  const lblSong = document.getElementById("lblViewerPlaySong");
  if (lblRecite) lblRecite.textContent = "🎧 낭송 듣기";
  if (lblSong) lblSong.textContent = "🎵 노래 듣기";
}

// -------------------------------------------------------------
// 📚 PDF 출판 파일 다운로드 친절 안내 (시니어 완주 가이드)
// -------------------------------------------------------------
function onDownloadPdfGuide(type) {
  setTimeout(() => {
    if (typeof Swal === "undefined") return;

    const isBookk = (type === "bookk");
    const bookTitle = currentStatus?.project?.title || "시화집";
    const fileName = isBookk ? `${bookTitle}_부크크_인쇄용_A5.pdf` : `${bookTitle}_열람용_A5.pdf`;

    Swal.fire({
      title: "🌸 시집 PDF 파일이 다운로드되었습니다!",
      html: `
        <div style="font-size: 0.95rem; color: #4B382A; text-align: left; line-height: 1.7; padding: 4px;">
          <div style="background: #F0FDF4; border: 1.5px solid #BBF7D0; border-left: 4px solid #16A34A; padding: 12px 14px; border-radius: 6px; margin-bottom: 12px;">
            <strong style="color: #15803D; font-size: 1.0rem;">📂 다운로드 완료 위치</strong><br>
            컴퓨터의 <strong>[다운로드] 폴더</strong>에 <br>
            <span style="color: #166534; font-weight: 700;">${fileName}</span> 파일로 저장되었습니다.
          </div>
          
          ${isBookk ? `
            <div style="background: #FFF9F2; border: 1px solid #EBD5C2; padding: 12px 14px; border-radius: 6px; font-size: 0.9rem; color: #7C4A1E; line-height: 1.6;">
              <strong>📖 독립출판 안내 (부크크 BOOKK)</strong><br>
              1. <strong>부크크(bookk.co.kr)</strong>에 로그인하신 뒤 [책 만들기]를 클릭하세요.<br>
              2. 규격은 <strong>국판 (A5, 148×210 mm)</strong>을 선택하세요.<br>
              3. 방금 다운로드된 이 PDF 파일을 본문 파일로 업로드하시면 <strong>소장용 실물 종이책</strong>으로 인쇄됩니다!
            </div>
          ` : `
            <div style="background: #FFF9F2; border: 1px solid #EBD5C2; padding: 10px 14px; border-radius: 6px; font-size: 0.88rem; color: #7C4A1E;">
              📱 이 전자책 PDF는 스마트폰, 태블릿, PC에서 가족·지인들에게 카카오톡이나 이메일로 선물하시기 가장 좋습니다.
            </div>
          `}
        </div>
      `,
      icon: "success",
      confirmButtonText: "확인했습니다 🌸",
      confirmButtonColor: "#C85A17"
    });
  }, 1200);
}


// 글자 크기 및 줄간격 미세 조율 (확장된 조절 범위 및 실시간 풍선도움말 연동)
function adjustCustomTypography(type, delta) {
  if (type === 'font') {
    // 글자 크기: -8단계부터 +25단계까지 시원하게 대폭 확장 (최대 2.80rem / 약 34pt 지원)
    customFontDelta = Math.max(-8, Math.min(25, customFontDelta + delta));
  } else if (type === 'line') {
    // 줄간격: -8단계부터 +15단계까지 확장
    customLineDelta = Math.max(-8, Math.min(15, customLineDelta + delta));
  }
  renderBookSpread(currentWorkIndex);

  // 시니어 작업자를 위한 실시간 토스트 알림
  const bodyElem = document.getElementById("viewerBody");
  const currentSize = bodyElem ? bodyElem.style.fontSize : "";
  const pxVal = currentSize ? (parseFloat(currentSize) * 16).toFixed(1) + "px" : "";
  if (type === 'font') {
    const stepStr = (customFontDelta === 0) ? "기본 크기" : `${customFontDelta > 0 ? '+' : ''}${customFontDelta}단계`;
    showToast(`시 본문 글자 크기: ${currentSize} (${pxVal}, ${stepStr})`, "info");
  } else if (type === 'line') {
    const stepStr = (customLineDelta === 0) ? "기본 간격" : `${customLineDelta > 0 ? '+' : ''}${customLineDelta}단계`;
    showToast(`시 본문 줄간격 조율 (${stepStr})`, "info");
  }
}

// 미세 조율 초기화
function resetCustomTypography() {
  customFontDelta = 0;
  customLineDelta = 0;
  renderBookSpread(currentWorkIndex);
  showToast("본문 글자 크기와 줄간격을 기본 규격으로 복원했습니다.", "info");
}

// 조판 미세 조율기 풍선도움말 실시간 동기화
function updateTypographyTooltips(finalFontSize, finalLineHeight) {
  const pxVal = (finalFontSize * 16).toFixed(1);
  const ptVal = (finalFontSize * 12).toFixed(1);
  const fontStepStr = (customFontDelta === 0) ? "기본" : `${customFontDelta > 0 ? '+' : ''}${customFontDelta}단계`;
  const lineStepStr = (customLineDelta === 0) ? "기본" : `${customLineDelta > 0 ? '+' : ''}${customLineDelta}단계`;

  const btnFontMinus = document.getElementById("btnTypographyFontMinus");
  const btnFontPlus = document.getElementById("btnTypographyFontPlus");
  const btnLineMinus = document.getElementById("btnTypographyLineMinus");
  const btnLinePlus = document.getElementById("btnTypographyLinePlus");
  const btnReset = document.getElementById("btnTypographyReset");
  const container = document.getElementById("layoutMicroAdjust");

  const fontDesc = `현재 본문 글자: ${pxVal}px (${finalFontSize.toFixed(2)}rem / ${ptVal}pt, ${fontStepStr})`;
  const lineDesc = `현재 줄간격: ${finalLineHeight.toFixed(2)}배 (${lineStepStr})`;

  const setTooltipText = (el, titleText) => {
    if (!el) return;
    el.setAttribute("title", titleText);
    el.setAttribute("data-tooltip", titleText);
  };

  setTooltipText(btnFontMinus, `[글자 크기 축소] ${fontDesc}. 클릭 시 1단계 축소합니다.`);
  setTooltipText(btnFontPlus, `[글자 크기 확대] ${fontDesc}. 클릭 시 1단계 확대합니다. (최대 25단계 지원)`);
  setTooltipText(btnLineMinus, `[줄간격 축소] ${lineDesc}. 클릭 시 1단계 좁힙니다.`);
  setTooltipText(btnLinePlus, `[줄간격 확대] ${lineDesc}. 클릭 시 1단계 넓힙니다.`);
  setTooltipText(btnReset, `[조판 초기화] ${fontDesc} / ${lineDesc}를 기본 조판값으로 되돌립니다.`);
  setTooltipText(container, `[조판 글자·줄간격] ${fontDesc} | ${lineDesc}`);

  // 현재 커스텀 툴팁이 활성화되어 떠 있다면 내용 즉시 갱신
  const tooltip = document.getElementById("appCustomTooltip");
  if (tooltip && tooltip.classList.contains("visible")) {
    const activeHover = document.querySelector(".btn-micro:hover, .layout-micro-adjust:hover");
    if (activeHover && activeHover.hasAttribute("data-tooltip")) {
      const text = activeHover.getAttribute("data-tooltip");
      const badgeMatch = text.match(/^(\[[^\]]+\])\s*([\s\S]*)$/);
      if (badgeMatch) {
        tooltip.innerHTML = `<span class="tooltip-header-badge">${badgeMatch[1]}</span><span class="tooltip-desc">${badgeMatch[2]}</span>`;
      } else {
        tooltip.innerHTML = `<span class="tooltip-desc">${text}</span>`;
      }
    }
  }
}


function renderEmptyBookSpread() {
  const isStandard = (currentStatus.project && currentStatus.project.book_type === "standard");
  const spreadContainer = document.querySelector(".book-spread");
  if (spreadContainer) {
    if (isStandard) spreadContainer.classList.add("standard-mode");
    else spreadContainer.classList.remove("standard-mode");
  }

  document.getElementById("viewerEpisode").textContent = "준비 중";
  document.getElementById("viewerTitle").textContent = "첫 번째 작품을 창작해보세요";
  document.getElementById("viewerBody").textContent = "좌측 [✍️ 시화 창작] 탭에서 기억을 들려주시면 아름다운 시가 이곳에 엮입니다.";
  document.getElementById("viewerImage").style.display = "none";
  const placeholder = document.getElementById("viewerImagePlaceholder");
  placeholder.style.display = "flex";
  if (isStandard) {
    placeholder.innerHTML = `<span style="font-size: 2.2rem; margin-bottom: 6px;">📖</span><span style="font-weight: 600; color: #49637c;">일반 시집 (텍스트 조판)</span>`;
  } else {
    placeholder.innerHTML = `<span style="font-size: 2.5rem;">🎨</span><span>삽화 이미지를 준비 중입니다.</span>`;
  }
  document.getElementById("btnPrevWork").disabled = true;
  document.getElementById("btnNextWork").disabled = true;
}

function navigateWork(delta) {
  renderBookSpread(currentWorkIndex + delta);
}

function onSelectWorkChange(val) {
  renderBookSpread(parseInt(val, 10));
}

// 12. 부크크 책등 계산기 실시간 연동
async function calculateSpecs() {
  const pages = document.getElementById("inputPages").value || 80;
  try {
    const res = await fetch(`/api/book_spec?pages=${pages}`);
    const data = await res.json();

    document.getElementById("specSpine").textContent = `${data.spine_thickness_mm} mm`;
    document.getElementById("specCoverSize").textContent = `${data.cover_canvas_width_mm} × ${data.cover_canvas_height_mm} mm`;
  } catch (err) {
    console.error("규격 계산 실패:", err);
  }
}

// 13. 이미지 규격 검사 리스트 로드
async function loadImagesInspection() {
  const container = document.getElementById("imagesInspectionContainer");
  try {
    const res = await fetch("/api/images");
    const list = await res.json();

    if (list.length === 0) {
      container.innerHTML = `<p style="color: var(--text-muted); font-size: 0.9rem;">현재 시집에 등록된 이미지가 없습니다.</p>`;
      return;
    }

    let html = `<div style="display: flex; flex-direction: column; gap: 8px;">`;
    list.forEach(item => {
      const isOk = item.is_ready;
      const statusColor = isOk ? "var(--accent-green)" : "#C84B31";
      html += `
        <div style="background: #FCFAF7; padding: 10px 14px; border-radius: 6px; border: 1px solid var(--border-subtle); display: flex; justify-content: space-between; align-items: center; font-size: 0.9rem;">
          <div>
            <strong>${item.filename}</strong>
            <span style="color: var(--text-muted); font-size: 0.82rem; margin-left: 8px;">${item.resolution} | ${item.dpi}</span>
          </div>
          <span style="color: ${statusColor}; font-weight: 600;">${item.status}</span>
        </div>
      `;
    });
    html += `</div>`;
    container.innerHTML = html;
  } catch (err) {
    container.innerHTML = `<p style="color: red;">검사 실패: ${err}</p>`;
  }
}

// =========================================================
// 14. 2원화 감성 삽화 관리: 무료 원클릭 자동 생성 & 드래그 앤 드롭 업로드
// =========================================================

// 14-1. 드래그 앤 드롭 이벤트 초기화
function initDropzones() {
  // 1) 스튜디오 드롭존
  const studioDropzone = document.getElementById("studioDropzone");
  if (studioDropzone) {
    ['dragenter', 'dragover'].forEach(eventName => {
      studioDropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        studioDropzone.classList.add('drag-over');
      }, false);
    });

    ['dragleave', 'dragend'].forEach(eventName => {
      studioDropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        studioDropzone.classList.remove('drag-over');
      }, false);
    });

    studioDropzone.addEventListener('drop', (e) => {
      e.preventDefault();
      e.stopPropagation();
      studioDropzone.classList.remove('drag-over');
      const dt = e.dataTransfer;
      const files = dt.files;
      if (files && files.length > 0) {
        uploadStudioImage(files[0]);
      }
    }, false);
  }

  // 2) 가상 북 뷰어 좌측 페이지 드롭존
  const viewerDropzone = document.getElementById("viewerDropzone");
  const viewerDropOverlay = document.getElementById("viewerDropOverlay");

  if (viewerDropzone && viewerDropOverlay) {
    ['dragenter', 'dragover'].forEach(eventName => {
      viewerDropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        viewerDropOverlay.style.display = 'flex';
      }, false);
    });

    viewerDropOverlay.addEventListener('dragleave', (e) => {
      e.preventDefault();
      e.stopPropagation();
      viewerDropOverlay.style.display = 'none';
    }, false);

    viewerDropOverlay.addEventListener('drop', (e) => {
      e.preventDefault();
      e.stopPropagation();
      viewerDropOverlay.style.display = 'none';
      const dt = e.dataTransfer;
      const files = dt.files;
      if (files && files.length > 0) {
        currentViewerTargetSlot = (currentSpreadPart === 2) ? "part2" : "main";
        uploadViewerImage(files[0]);
      }
    }, false);
  }

  // 3) 스튜디오 오디오 음원 드롭존
  const audioDropzone = document.getElementById("studioAudioDropzone");
  if (audioDropzone) {
    ['dragenter', 'dragover'].forEach(eventName => {
      audioDropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        audioDropzone.classList.add('drag-over');
      }, false);
    });

    ['dragleave', 'dragend'].forEach(eventName => {
      audioDropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        audioDropzone.classList.remove('drag-over');
      }, false);
    });

    audioDropzone.addEventListener('drop', (e) => {
      e.preventDefault();
      e.stopPropagation();
      audioDropzone.classList.remove('drag-over');
      const dt = e.dataTransfer;
      const files = dt.files;
      if (files && files.length > 0) {
        uploadStudioAudio(files[0]);
      }
    }, false);
  }
}

// 14-2. 스튜디오: 파일 선택창 트리거 & 체인지
function triggerStudioFileInput() {
  const input = document.getElementById("studioFileInput");
  if (input) input.click();
}

function onStudioFileSelected(event) {
  const file = event.target.files && event.target.files[0];
  if (file) {
    uploadStudioImage(file);
  }
}

// 14-3. 스튜디오: 방법 2 (나노바나나/Gemini 이미지 업로드 실행)
async function uploadStudioImage(file) {
  if (!file.type.startsWith("image/")) {
    alert("이미지 파일(JPG, PNG, WebP 등)만 업로드할 수 있습니다.");
    return;
  }

  const ep = document.getElementById("inputEpisode").value || "제01화";
  const statusBox = document.getElementById("studioUploadStatus");
  statusBox.className = "upload-status-text loading";
  statusBox.style.display = "block";
  statusBox.innerHTML = `<span>⏳ [${ep}] 그림 파일 업로드 및 적용 중...</span>`;

  const formData = new FormData();
  formData.append("file", file);
  formData.append("episode_no", ep);

  try {
    const res = await fetch("/api/upload_image", {
      method: "POST",
      body: formData
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.detail || "업로드 실패");
    }

    statusBox.className = "upload-status-text success";
    statusBox.innerHTML = `<span>✓ ${data.message}</span>`;

    // 미리보기 바 갱신
    const previewArea = document.getElementById("studioImagePreviewArea");
    const previewImg = document.getElementById("studioPreviewImg");
    const previewFilename = document.getElementById("studioPreviewFilename");
    if (previewArea && previewImg && previewFilename) {
      previewArea.style.display = "flex";
      previewImg.src = data.image_url;
      previewFilename.textContent = data.filename;
    }

    await loadStatus();
    await loadImagesInspection();

  } catch (err) {
    statusBox.className = "upload-status-text error";
    statusBox.innerHTML = `<span>⚠️ 오류: ${err.message}</span>`;
  }
}

let currentCandidateData = null;

let currentPreviewCandidate = null; // { episode_no, title, filename, image_url }

// 14-4. 스튜디오: 방법 1 (무료 API 단일 삽화 생성 후 미리보기 모달 팝업)
async function onStudioGenerateFreeImage() {
  const ep = document.getElementById("inputEpisode").value || "제01화";
  const title = document.getElementById("inputFinalTitle").value || "";
  const memory = document.getElementById("inputCoreMemory").value || "";
  const promptElem = document.getElementById("imagePromptDisplay");
  const prompt = promptElem ? (promptElem.value || promptElem.textContent || "").trim() : "";

  const btn = document.getElementById("btnStudioGenerateFree");
  const statusBox = document.getElementById("studioGenStatus");
  const originalText = btn.innerHTML;
  const meta = artStyleMeta[currentArtStyle] || artStyleMeta.watercolor;

  btn.disabled = true;
  btn.innerHTML = `<span>⏳ ${meta.name} 삽화 그리는 중... (약 3초)</span>`;
  if (statusBox) {
    statusBox.className = "gen-status-text loading";
    statusBox.style.display = "block";
    statusBox.innerHTML = `<span>🎨 무료 한도 절약을 위해 단 1장의 최적 ${meta.name} 삽화를 그리는 중입니다...</span>`;
  }

  try {
    const res = await fetch("/api/generate_image_candidates", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        episode_no: ep,
        title: title,
        memory_anchor: memory,
        prompt: prompt,
        art_style: currentArtStyle
      })
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.detail || "삽화 생성 실패");
    }

    if (data.used_prompt && promptElem) {
      promptElem.value = data.used_prompt;
    }

    if (statusBox) {
      statusBox.className = "gen-status-text success";
      statusBox.innerHTML = `<span>✓ 삽화가 생성되었습니다. 미리보기 창에서 확인하세요.</span>`;
    }

    // 미리보기 모달 팝업 열기 (사용자가 [삽입]을 선택할 때만 본문에 반영)
    openImagePreviewConfirmModal({
      episode_no: ep,
      title: title,
      filename: data.filename,
      image_url: data.image_url
    });

  } catch (err) {
    if (statusBox) {
      statusBox.className = "gen-status-text error";
      statusBox.innerHTML = `<span>⚠️ 생성 실패: ${err.message}</span>`;
    }
    showToast(`⚠️ 삽화 생성 실패: ${err.message}`, "error");
  } finally {
    btn.disabled = false;
    btn.innerHTML = originalText;
  }
}

// 🎨 생성된 삽화 미리보기 모달 열기 (1부 본 삽화 vs 2부 연작 삽화 공통 지원)
function openImagePreviewConfirmModal(item) {
  currentPreviewCandidate = item;
  const modal = document.getElementById("imagePreviewConfirmModal");
  if (!modal) return;

  const isPart2 = (item.target_slot === "part2");

  const titleEl = document.getElementById("labelPreviewModalTitle");
  if (titleEl) {
    titleEl.textContent = isPart2
      ? `[${item.episode_no}] 「${item.title || '새벽 대청'}」 2부 연작 삽화(4면) 미리보기`
      : `[${item.episode_no}] 「${item.title || '새벽 대청'}」 1부 본 삽화(2면) 미리보기`;
  }

  const descEl = modal.querySelector(".modal-desc");
  if (descEl) {
    descEl.innerHTML = isPart2
      ? `시의 후반부 정경을 바탕으로 그린 <strong>2부 연작 수채화</strong>입니다. 마음에 드시면 <strong>[2부 연작 삽화로 삽입]</strong>을 누르세요.`
      : `새로 생성된 그림을 확인하세요. 마음에 드시면 <strong>[삽화로 삽입]</strong>을 누르고, 마음에 들지 않으면 <strong>[다시 생성]</strong> 또는 <strong>[취소]</strong>를 누르세요.`;
  }

  const imgEl = document.getElementById("imgPreviewConfirm");
  if (imgEl) {
    imgEl.src = item.image_url;
  }

  const overlay = document.getElementById("imgPreviewLoadingOverlay");
  if (overlay) overlay.style.display = "none";

  const btnInsert = document.getElementById("btnConfirmInsertImage");
  if (btnInsert) {
    btnInsert.disabled = false;
    btnInsert.innerHTML = isPart2
      ? `<span>✨ 2부 연작 삽화(4면)로 삽입</span>`
      : `<span>✨ 본 삽화(2면)로 삽입</span>`;
  }

  modal.style.display = "flex";
}

// 모달 닫기 (취소: 기존 그림 유지)
function closeImagePreviewConfirmModal() {
  const modal = document.getElementById("imagePreviewConfirmModal");
  if (modal) modal.style.display = "none";
  currentPreviewCandidate = null;
  clearArtReferenceImage();
}

// [✨ 삽화로 삽입] 클릭 시: 원고에 공식 반영 (1부 vs 2부 슬롯 자동 판별)
async function onConfirmInsertImage() {
  if (!currentPreviewCandidate) return;

  const btn = document.getElementById("btnConfirmInsertImage");
  const origText = btn ? btn.innerHTML : "";
  const isPart2 = (currentPreviewCandidate.target_slot === "part2");

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<span>⏳ ${isPart2 ? '2부 연작 삽화' : '본 삽화'} 반영 중...</span>`;
  }

  try {
    const res = await fetch("/api/select_image_candidate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        episode_no: currentPreviewCandidate.episode_no,
        candidate_filename: currentPreviewCandidate.filename,
        candidate_name: isPart2 ? "2부 연작 시안" : "생성 시안",
        target_slot: currentPreviewCandidate.target_slot || "part1"
      })
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.detail || "삽화 반영 실패");
    }

    const slotLabel = isPart2 ? "2부 연작 삽화(4면)" : "1부 본 삽화(2면)";
    showToast(`✅ [${currentPreviewCandidate.episode_no}] ${slotLabel}가 성공적으로 본문에 삽입되었습니다!`, "success");
    closeImagePreviewConfirmModal();

    // 상태 동기화 & 조판 화면 갱신 (4쪽 3-4면 위치 유지)
    const savedPart = isPart2 ? 2 : (currentSpreadPart || 1);
    await loadStatus();
    await loadImagesInspection();

    if (currentStatus && currentStatus.works && typeof currentWorkIndex !== 'undefined') {
      const curWork = currentStatus.works[currentWorkIndex];
      if (curWork) {
        if (isPart2) {
          curWork.image_file_2 = `./images/${data.filename}`;
          curWork.part2_mode = "image";
          curWork.layout_mode = "multi_page";
          if (!curWork.layout_config) {
            curWork.layout_config = {
              page_count: 4,
              slots: ["image", "text", "image", "text"],
              image_settings: {
                page_1: { mode: "image", file: curWork.image_file || "" },
                page_3: { mode: "image", file: `./images/${data.filename}` }
              }
            };
          } else {
            curWork.layout_config.page_count = 4;
            if (curWork.layout_config.slots && curWork.layout_config.slots.length >= 3) {
              curWork.layout_config.slots[2] = "image";
            }
            if (!curWork.layout_config.image_settings) curWork.layout_config.image_settings = {};
            curWork.layout_config.image_settings.page_3 = { mode: "image", file: `./images/${data.filename}` };
          }
        } else {
          curWork.image_file = `./images/${data.filename}`;
        }
      }
    }

    // 스튜디오 미리보기 바 갱신 (1부인 경우)
    if (!isPart2) {
      const previewArea = document.getElementById("studioImagePreviewArea");
      const previewImg = document.getElementById("studioPreviewImg");
      const previewFilename = document.getElementById("studioPreviewFilename");
      if (previewArea && previewImg && previewFilename) {
        previewArea.style.display = "flex";
        previewImg.src = data.image_url;
        previewFilename.textContent = data.filename;
      }
    }

    currentSpreadPart = savedPart;
    if (typeof renderBookSpread === 'function' && typeof currentWorkIndex !== 'undefined') {
      renderBookSpread(currentWorkIndex);
    }

  } catch (err) {
    alert("삽화 반영 중 오류: " + err.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = origText;
    }
  }
}

// ========================================================
// 📷 [신규] 삽화 참조 사진 / 그림 첨부 및 비전 분석 처리
// ========================================================
let currentArtReferenceBase64 = null;

function handleArtReferenceBlob(blob, filename = "참조사진.jpg") {
  if (!blob || !blob.type.startsWith("image/")) {
    alert("이미지 파일만 첨부할 수 있습니다.");
    return;
  }
  const reader = new FileReader();
  reader.onload = function(e) {
    currentArtReferenceBase64 = e.target.result;
    const box = document.getElementById("artReferencePreviewBox");
    const thumb = document.getElementById("imgArtReferenceThumb");
    const nameEl = document.getElementById("artReferenceFileName");
    const optBox = document.getElementById("artReferenceOptionsBox");

    if (thumb) thumb.src = currentArtReferenceBase64;
    if (nameEl) nameEl.textContent = filename;
    if (box) box.style.display = "flex";
    if (optBox) optBox.style.display = "flex";

    showToast("📷 참조 사진이 첨부되었습니다! [🔄 다시 생성]을 누르면 사진 구도를 반영합니다.", "info");
  };
  reader.readAsDataURL(blob);
}

function handleArtReferenceFileSelected(input) {
  if (input && input.files && input.files[0]) {
    const file = input.files[0];
    handleArtReferenceBlob(file, file.name);
  }
}

function clearArtReferenceImage() {
  currentArtReferenceBase64 = null;
  const fileInput = document.getElementById("inputArtReferenceFile");
  if (fileInput) fileInput.value = "";
  const box = document.getElementById("artReferencePreviewBox");
  if (box) box.style.display = "none";
  const optBox = document.getElementById("artReferenceOptionsBox");
  if (optBox) optBox.style.display = "none";
  const thumb = document.getElementById("imgArtReferenceThumb");
  if (thumb) thumb.src = "";
  const radioVision = document.getElementById("radioRefAiVision");
  if (radioVision) radioVision.checked = true;
}

// 드래그 앤 드롭 지원
document.addEventListener("DOMContentLoaded", function() {
  const dropZone = document.getElementById("artReferenceDropZone");
  if (!dropZone) return;

  dropZone.addEventListener("dragover", function(e) {
    e.preventDefault();
    dropZone.style.borderColor = "#643E19";
    dropZone.style.background = "#F7EFE9";
  });
  dropZone.addEventListener("dragleave", function(e) {
    e.preventDefault();
    dropZone.style.borderColor = "#C8B9A6";
    dropZone.style.background = "#FFFFFF";
  });
  dropZone.addEventListener("drop", function(e) {
    e.preventDefault();
    dropZone.style.borderColor = "#C8B9A6";
    dropZone.style.background = "#FFFFFF";
    if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      handleArtReferenceBlob(file, file.name);
    }
  });
});

// 클립보드 이미지 붙여넣기 (Ctrl+V) 지원: 미리보기 모달이 열려 있을 때 이미지 붙여넣기 시 즉시 참조 사진으로 장착!
window.addEventListener("paste", function(e) {
  const modal = document.getElementById("imagePreviewConfirmModal");
  if (!modal || modal.style.display === "none") return;

  if (e.clipboardData && e.clipboardData.items) {
    for (let i = 0; i < e.clipboardData.items.length; i++) {
      const item = e.clipboardData.items[i];
      if (item.type.indexOf("image") !== -1) {
        const blob = item.getAsFile();
        if (blob) {
          handleArtReferenceBlob(blob, `클립보드_캡처_${new Date().toLocaleTimeString().replace(/:/g, '')}.jpg`);
          e.preventDefault();
          break;
        }
      }
    }
  }
});

// [🔄 다시 생성] 클릭 시: 모달 내부에서 즉시 새로운 시드로 재생성 (참조 사진/직접 사용 옵션 완벽 지원)
async function onRegeneratePreviewImage() {
  if (!currentPreviewCandidate) return;

  const ep = currentPreviewCandidate.episode_no;
  const title = currentPreviewCandidate.title;
  const isPart2 = (currentPreviewCandidate.target_slot === "part2");
  const memory = document.getElementById("inputCoreMemory") ? document.getElementById("inputCoreMemory").value : "";
  const promptElem = document.getElementById("imagePromptDisplay");
  const prompt = promptElem ? (promptElem.value || promptElem.textContent || "").trim() : "";
  const customGuide = document.getElementById("inputArtCustomGuide") ? document.getElementById("inputArtCustomGuide").value.trim() : "";

  // [신규] 참조 사진 및 직접 사용 여부 판별
  const radioDirect = document.getElementById("radioRefDirectPhoto");
  const isDirectUsePhoto = Boolean(radioDirect && radioDirect.checked && currentArtReferenceBase64);

  // [신규: 방법 1] 현재 그림 유지하며 부분 수정 (Image-to-Image) 체크 상태
  const chkUseBase = document.getElementById("chkUseCurrentImageAsBase");
  const useCurrentAsBase = chkUseBase ? chkUseBase.checked : true;

  const overlay = document.getElementById("imgPreviewLoadingOverlay");
  const btnRegen = document.getElementById("btnRegeneratePreviewImage");
  const btnInsert = document.getElementById("btnConfirmInsertImage");

  if (overlay) {
    const spinnerText = overlay.querySelector("span");
    if (spinnerText) {
      if (isDirectUsePhoto) {
        spinnerText.textContent = "소장 사진을 300 DPI 출판용 순백 여백으로 보정 중...";
      } else if (currentArtReferenceBase64) {
        spinnerText.textContent = "참조 사진의 구도를 비전 분석하여 수채화 그리는 중...";
      } else if (useCurrentAsBase && customGuide) {
        spinnerText.textContent = `현재 그림의 구도를 유지하며 [${customGuide}] 부분 수정 중... (약 3초)`;
      } else {
        spinnerText.textContent = "새로운 감성 삽화 그리는 중... (약 3초)";
      }
    }
    overlay.style.display = "flex";
  }
  if (btnRegen) btnRegen.disabled = true;
  if (btnInsert) btnInsert.disabled = true;

  try {
    const endpoint = isPart2 ? "/api/generate_part2_image" : "/api/generate_image_candidates";
    const bodyPayload = isPart2
      ? {
          episode_no: ep,
          prompt: "",
          custom_guide: customGuide,
          art_style: currentArtStyle,
          reference_image: currentArtReferenceBase64,
          direct_use_photo: isDirectUsePhoto,
          base_image_filename: currentPreviewCandidate.filename,
          use_current_as_base: useCurrentAsBase
        }
      : {
          episode_no: ep,
          title: title,
          memory_anchor: memory,
          prompt: prompt,
          custom_guide: customGuide,
          art_style: currentArtStyle,
          reference_image: currentArtReferenceBase64,
          direct_use_photo: isDirectUsePhoto,
          base_image_filename: currentPreviewCandidate.filename,
          use_current_as_base: useCurrentAsBase
        };

    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(bodyPayload)
    });

    let data;
    try {
      data = await res.json();
    } catch (parseErr) {
      const errText = await res.text().catch(() => "");
      throw new Error(errText || `서버 응답 오류 (상태 코드: ${res.status})`);
    }

    if (!res.ok || !data.success) {
      throw new Error(data.detail || data.error || "재생성 실패");
    }

    currentPreviewCandidate.filename = data.filename;
    currentPreviewCandidate.image_url = data.image_url;

    const imgEl = document.getElementById("imgPreviewConfirm");
    if (imgEl) {
      imgEl.src = data.image_url;
    }

    if (data.used_prompt && promptElem) {
      promptElem.value = data.used_prompt;
    }

    let toastMsg = "🎨 새로운 삽화가 다시 생성되었습니다!";
    if (isDirectUsePhoto) {
      toastMsg = "📷 소장 사진이 300 DPI 순백 여백 규격으로 보정되어 시안에 등록되었습니다!";
    } else if (currentArtReferenceBase64) {
      toastMsg = "🎨 첨부하신 사진의 실제 구도와 피사체를 분석하여 새 수채화 삽화를 그렸습니다!";
    } else if (useCurrentAsBase && customGuide) {
      toastMsg = `🎨 기존 구도를 유지하며 [${customGuide}] 연출이 반영되었습니다!`;
    } else if (customGuide) {
      toastMsg = `🎨 [${customGuide}] 연출이 반영된 새 삽화가 생성되었습니다!`;
    }
    showToast(toastMsg, "success");

  } catch (err) {
    alert("삽화 재생성 실패: " + err.message);
  } finally {
    if (overlay) overlay.style.display = "none";
    if (btnRegen) btnRegen.disabled = false;
    if (btnInsert) btnInsert.disabled = false;
  }
}

// 🎨 삽화 2안 모달 열기
function openImageCandidatesModal(data) {
  currentCandidateData = data;
  const modal = document.getElementById("imageCandidatesModal");
  if (!modal) return;

  const titleEl = document.getElementById("labelCandModalTitle");
  if (titleEl) {
    titleEl.textContent = `[${data.episode_no}] 삽화 시안 선택 (2가지 시안 중 마음에 드는 그림 선택)`;
  }

  const imgA = document.getElementById("candImgA");
  const imgB = document.getElementById("candImgB");
  if (imgA && data.candidate_a) imgA.src = data.candidate_a.image_url;
  if (imgB && data.candidate_b) imgB.src = data.candidate_b.image_url;

  // 선택 버튼 리셋
  const btnA = document.getElementById("btnSelectCandA");
  const btnB = document.getElementById("btnSelectCandB");
  if (btnA) {
    btnA.disabled = false;
    btnA.innerHTML = "<span>✨ [1안] 이 그림으로 최종 반영하기</span>";
  }
  if (btnB) {
    btnB.disabled = false;
    btnB.innerHTML = "<span>✨ [2안] 이 그림으로 최종 반영하기</span>";
  }

  modal.style.display = "flex";
}

// 닫기
function closeImageCandidatesModal() {
  const modal = document.getElementById("imageCandidatesModal");
  if (modal) modal.style.display = "none";
}

// 1안 또는 2안 선택 확정
async function onSelectCandidate(candId) {
  if (!currentCandidateData) return;
  const cand = candId === 'A' ? currentCandidateData.candidate_a : currentCandidateData.candidate_b;
  if (!cand) return;

  const targetBtn = candId === 'A' 
    ? document.getElementById("btnSelectCandA") 
    : document.getElementById("btnSelectCandB");
  const origBtnText = targetBtn ? targetBtn.innerHTML : "";

  if (targetBtn) {
    targetBtn.disabled = true;
    targetBtn.innerHTML = `<span>⏳ [${candId === 'A' ? '1안' : '2안'}] 삽화 확정 반영 중...</span>`;
  }

  try {
    const res = await fetch("/api/select_image_candidate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        episode_no: currentCandidateData.episode_no,
        candidate_filename: cand.filename,
        candidate_name: candId === 'A' ? "1안" : "2안"
      })
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.detail || "선택 반영 실패");
    }

    showToast(`✅ [${candId === 'A' ? '1안' : '2안'}] 그림이 최종 삽화로 성공적으로 채택되었습니다!`, "success");

    // 모달 닫기
    closeImageCandidatesModal();

    // 스튜디오 미리보기 바 갱신
    const previewArea = document.getElementById("studioImagePreviewArea");
    const previewImg = document.getElementById("studioPreviewImg");
    const previewFilename = document.getElementById("studioPreviewFilename");
    if (previewArea && previewImg && previewFilename) {
      previewArea.style.display = "flex";
      previewImg.src = data.image_url;
      previewFilename.textContent = data.filename;
    }

    // 상태 동기화 & 뷰어 갱신
    await loadStatus();
    await loadImagesInspection();
    if (typeof renderBookSpread === 'function' && typeof currentWorkIndex !== 'undefined') {
      renderBookSpread(currentWorkIndex);
    }

  } catch (err) {
    alert("시안 반영 중 오류가 발생했습니다: " + err.message);
  } finally {
    if (targetBtn) {
      targetBtn.disabled = false;
      targetBtn.innerHTML = origBtnText;
    }
  }
}

// 모달 안에서 새 2안 다시 생성
async function onRegenerateCandidates() {
  closeImageCandidatesModal();
  await onStudioGenerateFreeImage();
}

// 14-5. 뷰어: 파일 선택창 트리거 & 체인지
function triggerViewerFileInput() {
  const input = document.getElementById("viewerFileInput");
  if (input) input.click();
}

function onViewerFileSelected(event) {
  const file = event.target.files && event.target.files[0];
  if (file) {
    uploadViewerImage(file);
  }
}

// 14-6. 뷰어: 현재 보고 있는 페이지에 이미지 업로드 및 실시간 교체
async function uploadViewerImage(file) {
  if (!file.type.startsWith("image/")) {
    alert("이미지 파일만 업로드할 수 있습니다.");
    return;
  }

  if (!currentStatus || !currentStatus.works || currentStatus.works.length === 0) {
    alert("작품이 존재하지 않습니다.");
    return;
  }

  const work = currentStatus.works[currentWorkIndex];
  if (!work) return;

  const loadingOverlay = document.getElementById("viewerLoadingOverlay");
  const loadingText = document.getElementById("viewerLoadingText");
  if (loadingOverlay && loadingText) {
    loadingText.textContent = `[${work.episode_no}] 그림 파일 업로드 및 교체 중...`;
    loadingOverlay.style.display = "flex";
  }

  const slotIdx = (currentSpreadPart === 1) ? 0 : 2;
  const targetSlot = currentViewerTargetSlot || ((slotIdx === 2) ? "part2" : "main");

  const formData = new FormData();
  formData.append("file", file);
  formData.append("episode_no", work.episode_no);
  formData.append("target_slot", targetSlot);

  try {
    const res = await fetch("/api/upload_image", {
      method: "POST",
      body: formData
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.detail || "업로드 실패");
    }

    currentViewerTargetSlot = null;
    const savedSpreadPart = (targetSlot === "part2") ? 2 : currentSpreadPart;
    await loadStatus();
    currentSpreadPart = savedSpreadPart;
    renderBookSpread(currentWorkIndex);

  } catch (err) {
    alert("이미지 등록 실패: " + err.message);
  } finally {
    if (loadingOverlay) loadingOverlay.style.display = "none";
  }
}

// 14-7. 뷰어: 현재 보고 있는 페이지의 2가지 삽화 시안 동시 생성 & 모달 선택
async function onViewerGenerateFreeImage() {
  if (!currentStatus || !currentStatus.works || currentStatus.works.length === 0) {
    alert("작품이 존재하지 않습니다.");
    return;
  }

  const work = currentStatus.works[currentWorkIndex];
  if (!work) return;

  const loadingOverlay = document.getElementById("viewerLoadingOverlay");
  const loadingText = document.getElementById("viewerLoadingText");
  if (loadingOverlay && loadingText) {
    loadingText.textContent = `[${work.episode_no}] 「${work.title}」 2가지 삽화 시안 빚어내는 중... (약 7~10초)`;
    loadingOverlay.style.display = "flex";
  }

  try {
    const res = await fetch("/api/generate_image_candidates", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        episode_no: work.episode_no,
        title: work.title,
        memory_anchor: work.memory_anchor || "",
        prompt: "",
        art_style: currentArtStyle
      })
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.detail || "시안 생성 실패");
    }

    openImageCandidatesModal(data);

  } catch (err) {
    alert("삽화 시안 생성 실패: " + err.message);
  } finally {
    if (loadingOverlay) loadingOverlay.style.display = "none";
  }
}

// =========================================================
// 15. 완성 원고 통째 일괄 불러오기 (Bulk Import)
// =========================================================

let parsedBulkItems = [];

function openBulkImportModal() {
  const modal = document.getElementById("bulkImportModal");
  if (modal) modal.style.display = "flex";
  document.getElementById("bulkTextInput").focus();
}

function closeBulkImportModal() {
  const modal = document.getElementById("bulkImportModal");
  if (modal) modal.style.display = "none";
  document.getElementById("formBulkImport").reset();
  document.getElementById("bulkPreviewSection").style.display = "none";
  document.getElementById("bulkPreviewList").innerHTML = "";
  const submitBtn = document.getElementById("btnSubmitBulkImport");
  submitBtn.disabled = true;
  submitBtn.style.opacity = "0.5";
  parsedBulkItems = [];
}

function triggerBulkFileInput() {
  const input = document.getElementById("bulkFileInput");
  if (input) input.click();
}

function onBulkFileSelected(event) {
  const file = event.target.files && event.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = (e) => {
    const text = e.target.result;
    document.getElementById("bulkTextInput").value = text;
    analyzeBulkText();
  };
  reader.readAsText(file, "UTF-8");
}

function onBulkTextInputChange() {
  const text = document.getElementById("bulkTextInput").value.trim();
  const submitBtn = document.getElementById("btnSubmitBulkImport");
  if (!text) {
    submitBtn.disabled = true;
    submitBtn.style.opacity = "0.5";
  }
}

async function analyzeBulkText() {
  const text = document.getElementById("bulkTextInput").value.trim();
  if (!text) {
    alert("분석할 원고 텍스트를 입력하거나 텍스트 파일을 선택해주세요.");
    document.getElementById("bulkTextInput").focus();
    return;
  }

  const btn = document.getElementById("btnAnalyzeBulk");
  const origText = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = `<span>⏳ 원고 분석 중...</span>`;

  try {
    const res = await fetch("/api/preview_bulk_manuscript", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ raw_text: text })
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.detail || "원고 분석 실패");
    }

    parsedBulkItems = data.items || [];
    renderBulkPreview(parsedBulkItems);

    const submitBtn = document.getElementById("btnSubmitBulkImport");
    if (parsedBulkItems.length > 0) {
      submitBtn.disabled = false;
      submitBtn.style.opacity = "1";
    } else {
      submitBtn.disabled = true;
      submitBtn.style.opacity = "0.5";
      alert("감지된 시가 없습니다. 빈 줄(2개 이상) 또는 번호(1., 2.)로 시를 구분해주세요.");
    }

  } catch (err) {
    alert("원고 분석 오류: " + err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = origText;
  }
}

function renderBulkPreview(items) {
  const section = document.getElementById("bulkPreviewSection");
  const countBadge = document.getElementById("bulkPreviewCountBadge");
  const list = document.getElementById("bulkPreviewList");

  countBadge.textContent = `총 ${items.length}편 감지됨`;
  list.innerHTML = "";

  items.forEach(item => {
    const div = document.createElement("div");
    div.className = "bulk-preview-item";
    div.innerHTML = `
      <span class="item-ep">${item.episode_no}</span>
      <span class="item-title">${item.title}</span>
      <span class="item-snippet">${item.memory_anchor || item.poem_body.substring(0, 30)}...</span>
    `;
    list.appendChild(div);
  });

  section.style.display = "block";
}

async function onSubmitBulkImport(event) {
  event.preventDefault();
  const text = document.getElementById("bulkTextInput").value.trim();
  if (!text) {
    alert("원고 내용이 없습니다.");
    return;
  }

  const mode = document.querySelector('input[name="bulkImportMode"]:checked')?.value || "overwrite";
  const autoPrompts = document.getElementById("chkAutoPrompts")?.checked ?? true;

  const btn = document.getElementById("btnSubmitBulkImport");
  btn.disabled = true;
  btn.innerHTML = `<span>⏳ 원고 일괄 저장 및 조판 중...</span>`;

  try {
    const res = await fetch("/api/import_bulk_manuscript", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        raw_text: text,
        mode: mode,
        auto_prompts: autoPrompts
      })
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.detail || "등록 실패");
    }

    closeBulkImportModal();
    await loadProjects();
    await loadStatus();

    // 뷰어 탭으로 자동 이동
    const bookTab = document.querySelector('[data-target="panelBook"]');
    if (bookTab) bookTab.click();

    // 스마트 일괄 생성 제안 팝업
    const isIllustrated = (!currentStatus.project || currentStatus.project.book_type === "illustrated");
    if (isIllustrated) {
      setTimeout(() => {
        const wantBatchGen = confirm(
          `🎉 [${data.imported_count}편]의 시 원고가 성공적으로 등록되었습니다!\n\n` +
          `지금 바로 전편(총 ${data.count}편)에 어울리는 한국형 서정 수채화 삽화를 일괄 자동 생성하시겠습니까?\n` +
          `(키 없이 100% 무료 FLUX 엔진으로 순차 자동 생성됩니다)`
        );
        if (wantBatchGen) {
          openBatchGenModal();
          startBatchGen();
        }
      }, 300);
    } else {
      alert(`🎉 [${data.imported_count}편]의 시 원고가 성공적으로 등록되었습니다! 뷰어에서 확인하세요.`);
    }

  } catch (err) {
    alert("일괄 등록 오류: " + err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<span>🚀 이 원고로 전체 등록하기</span>`;
  }
}

// =========================================================
// 16. 전편 서정 수채화 삽화 일괄 자동 생성 (Batch Image Generation)
// =========================================================

let isBatchGenRunning = false;
let batchCancelRequested = false;

function openBatchGenModal() {
  const modal = document.getElementById("batchGenModal");
  if (modal) modal.style.display = "flex";

  const works = (currentStatus && currentStatus.works) ? currentStatus.works : [];
  const total = works.length;

  document.getElementById("batchProgressBar").style.width = "0%";
  document.getElementById("batchProgressPercentText").textContent = "0%";
  document.getElementById("batchProgressCountText").textContent = `0 / ${total}편 완료`;
  document.getElementById("batchProgressCurrentTitle").textContent = "시작 버튼을 누르면 자동 생성이 시작됩니다.";
  document.getElementById("batchThumbnailGrid").innerHTML = "";

  const startBtn = document.getElementById("btnStartBatchGen");
  startBtn.disabled = false;
  startBtn.innerHTML = `<span>🎨 전편 삽화 일괄 생성 시작 (${total}편)</span>`;
}

function closeBatchGenModal() {
  if (isBatchGenRunning) {
    const confirmStop = confirm("현재 삽화 생성이 진행 중입니다. 정말 중단하시겠습니까?");
    if (!confirmStop) return;
    batchCancelRequested = true;
  }
  const modal = document.getElementById("batchGenModal");
  if (modal) modal.style.display = "none";
}

function onBatchGenOverlayClick(event) {
  if (!isBatchGenRunning) {
    closeBatchGenModal();
  }
}

function cancelBatchGen() {
  if (isBatchGenRunning) {
    batchCancelRequested = true;
    document.getElementById("batchProgressCurrentTitle").textContent = "중단 요청 중... 잠시만 기다려주세요.";
  } else {
    closeBatchGenModal();
  }
}

async function startBatchGen() {
  if (!currentStatus || !currentStatus.works || currentStatus.works.length === 0) {
    alert("등록된 시 작품이 없습니다. 먼저 원고를 등록해주세요.");
    return;
  }

  const works = currentStatus.works;
  const total = works.length;
  const startBtn = document.getElementById("btnStartBatchGen");
  const cancelBtn = document.getElementById("btnCancelBatchGen");
  const progressBar = document.getElementById("batchProgressBar");
  const percentText = document.getElementById("batchProgressPercentText");
  const countText = document.getElementById("batchProgressCountText");
  const currentTitle = document.getElementById("batchProgressCurrentTitle");
  const grid = document.getElementById("batchThumbnailGrid");

  isBatchGenRunning = true;
  batchCancelRequested = false;
  startBtn.disabled = true;
  cancelBtn.textContent = "작업 중단";

  let successCount = 0;

  for (let i = 0; i < total; i++) {
    if (batchCancelRequested) {
      currentTitle.textContent = "사용자에 의해 일괄 생성이 중단되었습니다.";
      break;
    }

    const work = works[i];
    const progressPercent = Math.round((i / total) * 100);

    progressBar.style.width = `${progressPercent}%`;
    percentText.textContent = `${progressPercent}%`;
    countText.textContent = `${i} / ${total}편 완료`;
    currentTitle.textContent = `[${work.episode_no}] 「${work.title}」 수채화 빚어내는 중...`;

    try {
      const res = await fetch("/api/generate_image_free", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          episode_no: work.episode_no,
          title: work.title,
          memory_anchor: work.memory_anchor || "",
          prompt: work.image_prompt || "",
          art_style: currentArtStyle
        })
      });

      const data = await res.json();
      if (res.ok && data.success) {
        successCount++;
        // 썸네일 그리드에 카드 추가
        const card = document.createElement("div");
        card.className = "batch-thumb-card";
        card.innerHTML = `
          <img src="${data.image_url}" alt="${work.title}" class="batch-thumb-img">
          <span class="batch-thumb-title">[${work.episode_no}] ${work.title}</span>
        `;
        grid.prepend(card);
      }
    } catch (err) {
      console.warn(`[${work.episode_no}] 생성 건너뜀:`, err);
    }
  }

  isBatchGenRunning = false;
  startBtn.disabled = false;
  cancelBtn.textContent = "닫기";

  if (!batchCancelRequested) {
    progressBar.style.width = "100%";
    percentText.textContent = "100%";
    countText.textContent = `${total} / ${total}편 완료`;
    currentTitle.textContent = `🎉 전편(${successCount}편)의 수채화 삽화가 모두 완성되었습니다!`;
  }

  // 상태 리로드 및 뷰어 갱신
  await loadStatus();
  renderBookSpread(currentWorkIndex);
}

// =========================================================
// 17. 300 DPI 출판 규격 전체 일괄 자동 보정 실행
// =========================================================
async function onEnhanceAllImages300Dpi() {
  const btn = document.getElementById("btnEnhance300Dpi");
  const origText = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = `<span>⏳ 300 DPI 보정 중...</span>`;

  try {
    const res = await fetch("/api/images/enhance_300dpi", { method: "POST" });
    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.detail || "보정 실패");
    }

    alert(`🎉 ${data.message}`);
    await loadImagesInspection();
    await loadStatus();
  } catch (err) {
    alert("300 DPI 보정 오류: " + err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = origText;
  }
}

// =========================================================
// 18. 서정 노래 / 음원 제작 (선택 옵션) 로직
// =========================================================
let currentAudioFile = "";
let currentReciteFile = "";
let currentMusicFile = "";
let currentLyrics = "";
let currentMusicGenre = "minyo";
let currentMusicData = null;

function toggleMusicOption(enabled) {
  const panel = document.getElementById("musicContentPanel");
  if (!panel) return;
  panel.style.display = enabled ? "block" : "none";
}

function onMusicGenreChange() {
  const selected = document.querySelector('input[name="musicGenre"]:checked');
  if (selected) {
    currentMusicGenre = selected.value;
  }

  const genreNames = {
    minyo: "서정 민요조",
    folk: "어쿠스틱 포크",
    gagok: "서정 예술 가곡",
    dongyo: "서정 동요/동심"
  };
  const gName = genreNames[currentMusicGenre] || "서정 음악";

  // 이미 노랫말 또는 시 본문이 있다면 새 장르 스킬 블록으로 자동 재편곡
  const poem = document.getElementById("inputFinalPoem")?.value?.trim();
  const lyricsInput = document.getElementById("musicLyricsInput");
  if (poem || (lyricsInput && lyricsInput.value.trim())) {
    showToast(`🎵 [${gName}] 장르 스킬 블록으로 전환합니다. 이전 추임새를 정리하고 재편곡합니다.`, "info");
    onGenerateLyrics(true);
  }
}

function highlightFreeMusicButton() {
  const freeBtn = document.getElementById("btnSelectTrebloAI") || document.getElementById("btnSelectFreeMusicAI");
  if (!freeBtn) return;
  freeBtn.scrollIntoView({ behavior: "smooth", block: "center" });
  freeBtn.style.transition = "all 0.3s ease";
  freeBtn.style.boxShadow = "0 0 0 4px #2E7D32, 0 4px 14px rgba(46, 125, 50, 0.45)";
  freeBtn.style.transform = "scale(1.02)";
  setTimeout(() => {
    freeBtn.style.boxShadow = "";
    freeBtn.style.transform = "";
  }, 2500);
}

async function onGenerateLyrics(showAlert = true) {
  const title = document.getElementById("inputFinalTitle").value.trim() || "무제";
  const poem = document.getElementById("inputFinalPoem").value.trim();
  const existingLyrics = document.getElementById("musicLyricsInput")?.value?.trim() || "";
  const sourceText = poem || existingLyrics;

  if (!sourceText) {
    if (showAlert) {
      alert("먼저 시 본문을 작성하거나 다듬어주세요.");
      document.getElementById("inputFinalPoem").focus();
    }
    return;
  }

  const btn = document.getElementById("btnGenerateLyrics");
  const origText = btn ? btn.innerHTML : "";
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = "<span>⏳ 모듈러 스킬 블록으로 노랫말 운율화 중...</span>";
  }

  try {
    const res = await fetch("/api/generate_lyrics", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: title,
        poem_body: sourceText,
        genre: currentMusicGenre
      })
    });
    const resData = await res.json();
    const payload = resData.data || (resData.lyrics ? resData : null);
    if (resData.success && payload) {
      currentMusicData = payload;
      currentLyrics = payload.lyrics || resData.lyrics;
      const lyricsInput = document.getElementById("musicLyricsInput");
      if (lyricsInput) {
        lyricsInput.value = currentLyrics;
        lyricsInput.style.backgroundColor = "#FFF9F0";
        setTimeout(() => { lyricsInput.style.backgroundColor = "#FFFFFF"; }, 400);
      }

      // 🎼 노랫말 정서 & 맞춤 악기 변주 배지 업데이트
      const moodTheme = payload.mood_theme || resData.mood_theme || "";
      const inst = payload.instruments || resData.instruments || "";
      const varBadge = document.getElementById("badgeMusicVariation");
      if (varBadge && moodTheme) {
        const leadInst = inst ? inst.split(',')[0].trim() : "";
        varBadge.textContent = `🎼 ${moodTheme}` + (leadInst ? ` (${leadInst} 등)` : "");
        varBadge.style.display = "inline-block";
        varBadge.title = `[노랫말 맞춤 악기 편성]\n${inst}\n템포: ${payload.bpm || resData.bpm || '72 BPM'}`;
      }

      if (showAlert) {
        const genreName = payload.genre_name || resData.genre_name || "서정 음악";
        setTimeout(() => {
          let extraMsg = "";
          if (moodTheme || inst) {
            extraMsg = `\n[노랫말 맞춤 악기 & 정서 변주]\n• 감성 테마: ${moodTheme || '서정'}\n• 추천 악기: ${inst || '어쿠스틱 편성'}\n`;
          }
          alert(
            `🎵 [${genreName}] 노랫말과 맞춤 악기 편곡이 완료되었습니다!${extraMsg}\n` +
            `노랫말을 확인하신 후, 아래의 [🎵 1. Suno AI] / [🎼 2. Udio AI] / [🚀 3. YuE2 AI] 중 원하시는 도구를 선택하여 세상에 하나뿐인 노래를 만들어 보세요.`
          );
        }, 150);
      }
    } else {
      if (showAlert) alert("노랫말 생성 실패: " + (resData.error || "알 수 없는 오류"));
    }
  } catch (err) {
    if (showAlert) alert("노랫말 생성 중 오류가 발생했습니다: " + err);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = origText;
    }
  }
}

async function copyLyricsText() {
  const lyricsInput = document.getElementById("musicLyricsInput");
  const text = lyricsInput ? lyricsInput.value.trim() : "";
  if (!text) {
    alert("복사할 노랫말이 없습니다. 먼저 '노랫말 운율화하기'를 실행해주세요.");
    return;
  }
  const success = await safeCopyToClipboard(text);
  if (success) {
    showToast("📜 노래 가사(Verse/Chorus)가 클립보드에 복사되었습니다!", "success");
  } else {
    alert("클립보드 복사에 실패했습니다.");
  }
}

// 3대 음악 AI 탭 선택 상태 갱신 헬퍼
function updateMusicTabSelection(selected) {
  const b1 = document.getElementById("btnSelectSunoAI");
  const b2 = document.getElementById("btnSelectUdioAI");
  const b3 = document.getElementById("btnSelectYue2AI");
  
  [b1, b2, b3].forEach(b => {
    if (!b) return;
    b.classList.remove("active-music-btn");
    b.style.background = "#ffffff";
    b.style.color = "#643e19";
    b.style.borderColor = "#c9a98b";
    b.style.fontWeight = "normal";
  });

  let targetBtn = null;
  if (selected === "suno") targetBtn = b1;
  else if (selected === "udio") targetBtn = b2;
  else if (selected === "yue2") targetBtn = b3;

  if (targetBtn) {
    targetBtn.classList.add("active-music-btn");
    targetBtn.style.background = "#643e19";
    targetBtn.style.color = "#ffffff";
    targetBtn.style.borderColor = "#643e19";
    targetBtn.style.fontWeight = "bold";
  }
}

// 1번 탭: Suno AI 작곡 가이드
function openSunoAIGuide() {
  updateMusicTabSelection("suno");
  const modal = document.getElementById("sunoMusicModal");
  if (modal) modal.style.display = "flex";
}

function closeSunoMusicModal() {
  const modal = document.getElementById("sunoMusicModal");
  if (modal) modal.style.display = "none";
}

// 2번 탭: Udio AI 서정 예술 작곡 가이드
function openUdioAIGuide() {
  updateMusicTabSelection("udio");
  const modal = document.getElementById("udioMusicModal");
  if (modal) modal.style.display = "flex";
}

function closeUdioMusicModal() {
  const modal = document.getElementById("udioMusicModal");
  if (modal) modal.style.display = "none";
}

// 3번 탭: YuE2 고성능 웹 스튜디오 가이드
function openYue2AIGuide() {
  updateMusicTabSelection("yue2");
  const modal = document.getElementById("colabYuE2Modal");
  if (modal) modal.style.display = "flex";
}

function closeColabYuE2Modal() {
  const modal = document.getElementById("colabYuE2Modal");
  if (modal) modal.style.display = "none";
}

// 하위 호환성 별칭
function openTrebloAIGuide() { openUdioAIGuide(); }
function openFreeMusicAIGuide() { openUdioAIGuide(); }
function closeFreeMusicModal() { closeUdioMusicModal(); }
function openColabYuE2Guide() { openYue2AIGuide(); }

function getMusicGenrePrompt(genre) {
  const g = genre || currentMusicGenre || "minyo";
  if (currentMusicData && currentMusicData.music_prompt && currentMusicData.genre === g) {
    return currentMusicData.music_prompt;
  }
  const promptMap = {
    minyo: "Korean traditional lyrical folk song, acoustic gayageum and bamboo daegeum flute, subtle haegum, emotional warm vocal, sorrowful yet uplifting Korean minyo style, traditional janggu percussion, warm acoustic sound, 75 bpm",
    folk: "Korean warm acoustic folk song, delicate nylon acoustic guitar fingerpicking, soft upright piano, intimate emotional vocals, warm 1970s 1980s nostalgic storytelling, peaceful lyrical atmosphere, 78 bpm, warm analog sound",
    gagok: "Korean classical art song, elegant gagok style, expressive concert grand piano, warm cello counter-melody, graceful lyrical classical vocal, poetic and dramatic resonance, majestic and tender emotion, 72 bpm",
    dongyo: "Korean lyrical children song, nostalgic dongyo, pure innocent vocal, bright glockenspiel bells, gentle acoustic piano, soft acoustic guitar, warm heartwarming childhood melody, peaceful and tender, 82 bpm",
    ballad: "Korean emotional acoustic ballad, delicate piano melody, tender string quartet, heartfelt warm vocal, nostalgic and cinematic soundscape, 70 bpm"
  };
  return promptMap[g] || promptMap.minyo;
}

async function copyFullMusicPrompt(silent = false) {
  const lyricsInput = document.getElementById("musicLyricsInput");
  const lyrics = lyricsInput ? lyricsInput.value.trim() : "";
  const title = document.getElementById("inputFinalTitle").value.trim() || "무제";
  
  const genrePrompt = getMusicGenrePrompt(currentMusicGenre);
  const fullPrompt = `[Title]\n${title}\n\n[Style / Tags]\n${genrePrompt}\n\n[Lyrics]\n${lyrics || "(시 본문을 노랫말로 운율화해주세요)"}`;

  const success = await safeCopyToClipboard(fullPrompt);
  if (success) {
    if (!silent) {
      showToast("✨ <b>[전체 내용(제목·스타일·가사)]</b>이 복사되었습니다!<br>음악 사이트의 <b>Lyrics(가사)</b> 칸에 <b>Ctrl + V</b>로 통째로 붙여넣으시면 AI가 알아서 작곡합니다.", "success");
    }
  } else {
    if (!silent) alert("클립보드 복사에 실패했습니다.");
  }
  return success;
}

// [시니어/초보자 배려 1] 노래 가사만 따로 복사
async function copyLyricsOnly(btn) {
  const lyricsInput = document.getElementById("musicLyricsInput");
  const lyrics = lyricsInput ? lyricsInput.value.trim() : "";
  if (!lyrics) {
    showToast("⚠️ 먼저 [노랫말 운율화하기]를 실행하여 가사를 생성해주세요.", "error");
    return;
  }
  const success = await safeCopyToClipboard(lyrics);
  if (success) {
    const firstLine = lyrics.split("\n").filter(l => l.trim()).slice(0, 2).join(" / ");
    showToast(`📋 <b>[2. 노래 가사]</b> 복사 완료!<br><span style="font-size:0.78rem;color:#f3d9b8;">"${firstLine.substring(0, 45)}..."</span><br>음악 사이트의 <b>Lyrics(가사)</b> 칸에 <b>Ctrl + V</b>로 붙여넣으세요.`, "success");
    if (btn) {
      const orig = btn.innerHTML;
      btn.innerHTML = "<span>✓ 가사 복사 완료!</span>";
      btn.style.borderColor = "#3a7352";
      btn.style.color = "#3a7352";
      setTimeout(() => {
        btn.innerHTML = orig;
        btn.style.borderColor = "";
        btn.style.color = "";
      }, 1800);
    }
  }
}

// [시니어/초보자 배려 2] 음악 스타일(장르) 태그만 따로 복사
async function copyStyleOnly(btn) {
  const genrePrompt = getMusicGenrePrompt(currentMusicGenre);
  const success = await safeCopyToClipboard(genrePrompt);
  if (success) {
    const preview = genrePrompt.length > 50 ? genrePrompt.substring(0, 50) + "..." : genrePrompt;
    showToast(`🎵 <b>[1. 음악 스타일 태그]</b> 복사 완료!<br><span style="font-size:0.78rem;color:#f3d9b8;">"${preview}"</span><br>음악 사이트의 <b>Song description (또는 Style)</b> 칸에 <b>Ctrl + V</b>로 붙여넣으세요.`, "success");
    if (btn) {
      const orig = btn.innerHTML;
      btn.innerHTML = "<span>✓ 스타일 태그 복사 완료!</span>";
      btn.style.borderColor = "#3a7352";
      btn.style.color = "#3a7352";
      setTimeout(() => {
        btn.innerHTML = orig;
        btn.style.borderColor = "";
        btn.style.color = "";
      }, 1800);
    }
  }
}

// [시니어/초보자 배려 3] 곡 제목만 따로 복사
async function copyTitleOnly(btn) {
  const title = document.getElementById("inputFinalTitle").value.trim() || "서정시 노래";
  const success = await safeCopyToClipboard(title);
  if (success) {
    showToast(`📝 곡 제목(<b>「${title}」</b>)이 복사되었습니다!<br>음악 사이트의 <b>Title(제목)</b> 칸에 <b>Ctrl + V</b>로 붙여넣으세요.`, "success");
    if (btn) {
      const orig = btn.innerHTML;
      btn.innerHTML = "<span>✓ 제목 복사 완료!</span>";
      btn.style.borderColor = "#3a7352";
      btn.style.color = "#3a7352";
      setTimeout(() => {
        btn.innerHTML = orig;
        btn.style.borderColor = "";
        btn.style.color = "";
      }, 1800);
    }
  }
}

// [가이드 탭 전환] Suno vs Udio
function switchMusicAITab(platform) {
  const sunoTab = document.getElementById("tabMusicSuno");
  const udioTab = document.getElementById("tabMusicUdio");
  const sunoContent = document.getElementById("guideContentSuno");
  const udioContent = document.getElementById("guideContentUdio");

  if (platform === "suno") {
    if (sunoTab) {
      sunoTab.style.background = "#643e19";
      sunoTab.style.color = "#ffffff";
      sunoTab.style.borderColor = "#643e19";
      sunoTab.style.fontWeight = "bold";
    }
    if (udioTab) {
      udioTab.style.background = "#fbf9f4";
      udioTab.style.color = "#665f57";
      udioTab.style.borderColor = "#ebdccb";
      udioTab.style.fontWeight = "normal";
    }
    if (sunoContent) sunoContent.style.display = "block";
    if (udioContent) udioContent.style.display = "none";
  } else {
    if (udioTab) {
      udioTab.style.background = "#643e19";
      udioTab.style.color = "#ffffff";
      udioTab.style.borderColor = "#643e19";
      udioTab.style.fontWeight = "bold";
    }
    if (sunoTab) {
      sunoTab.style.background = "#fbf9f4";
      sunoTab.style.color = "#665f57";
      sunoTab.style.borderColor = "#ebdccb";
      sunoTab.style.fontWeight = "normal";
    }
    if (udioContent) udioContent.style.display = "block";
    if (sunoContent) sunoContent.style.display = "none";
  }
}

// 1번 탭: Suno AI 음악 플랫폼 단일 윈도우 인스턴스 (중복 생성 방지)
let sunoMusicPlatformWindow = null;

async function openSunoPlatform() {
  const url = "https://suno.com";
  const windowName = "SunoAIMusicPlatformWindow";

  // 1. 이미 열린 Suno 창이 존재하고 닫히지 않은 경우: 해당 창으로 포커스 이동 (새 탭 중복 생성 방지)
  if (sunoMusicPlatformWindow && !sunoMusicPlatformWindow.closed) {
    try {
      sunoMusicPlatformWindow.focus();
      showToast("🚀 이미 열려 있는 Suno 창으로 이동했습니다!<br><b>Ctrl + V</b>로 가사를 붙여넣으세요.", "info");
      return;
    } catch (e) {
      // 크로스 도메인 보안 예외 방어
    }
  }

  // 2. 창이 없거나 닫힌 경우: 고유 윈도우 이름으로 열기 (브라우저 수준 중복 방지)
  sunoMusicPlatformWindow = window.open(url, windowName);
  if (sunoMusicPlatformWindow) {
    sunoMusicPlatformWindow.focus();
    showToast("🚀 Suno AI 사이트가 새 창으로 열렸습니다!<br>화면 좌측 <b>Create</b> ➜ <b>Custom</b> 켠 후 <b>Ctrl + V</b>로 붙여넣으세요.", "success");
  }
}

// 2번 탭: Udio AI 음악 플랫폼 단일 윈도우 인스턴스 (중복 생성 방지)
let udioMusicPlatformWindow = null;

async function openUdioPlatform() {
  const url = "https://www.udio.com";
  const windowName = "UdioAIMusicPlatformWindow";

  // 1. 이미 열린 Udio 창이 존재하고 닫히지 않은 경우: 해당 창으로 포커스 이동 (새 탭 중복 생성 방지)
  if (udioMusicPlatformWindow && !udioMusicPlatformWindow.closed) {
    try {
      udioMusicPlatformWindow.focus();
      showToast("🚀 이미 열려 있는 Udio 창으로 이동했습니다!<br><b>[Custom]</b> 켠 후 스타일과 가사를 붙여넣으세요.", "info");
      return;
    } catch (e) {
      // 크로스 도메인 보안 예외 방어
    }
  }

  // 2. 창이 없거나 닫힌 경우: 고유 윈도우 이름으로 열기 (브라우저 수준 중복 방지)
  udioMusicPlatformWindow = window.open(url, windowName);
  if (udioMusicPlatformWindow) {
    udioMusicPlatformWindow.focus();
    showToast("🚀 Udio AI 사이트가 새 창으로 열렸습니다!<br>상단 <b>[Custom]</b>을 켠 뒤 스타일과 가사를 붙여넣으세요.", "success");
  }
}

// 3번 탭: YuE2 공식 웹 스튜디오 단일 윈도우 인스턴스 (중복 생성 방지)
let yue2MusicPlatformWindow = null;

async function openYue2Platform() {
  const url = "https://yue.noizai.net/";
  const windowName = "Yue2AIMusicPlatformWindow";

  // 1. 이미 열린 YuE2 창이 존재하고 닫히지 않은 경우: 해당 창으로 포커스 이동 (새 탭 중복 생성 방지)
  if (yue2MusicPlatformWindow && !yue2MusicPlatformWindow.closed) {
    try {
      yue2MusicPlatformWindow.focus();
      showToast("🚀 이미 열려 있는 YuE2 스튜디오 창으로 이동했습니다!<br><b>Ctrl + V</b>로 가사와 스타일을 붙여넣으세요.", "info");
      return;
    } catch (e) {
      // 크로스 도메인 보안 예외 방어
    }
  }

  // 2. 창이 없거나 닫힌 경우: 고유 윈도우 이름으로 열기 (브라우저 수준 중복 방지)
  yue2MusicPlatformWindow = window.open(url, windowName);
  if (yue2MusicPlatformWindow) {
    yue2MusicPlatformWindow.focus();
    showToast("🚀 YuE2 공식 스튜디오가 새 창으로 열렸습니다!<br><b>Ctrl + V</b>로 가사와 스타일을 붙여넣으세요.", "success");
  }
}

// 하위 호환성 별칭
async function openTrebloPlatform() { return openUdioPlatform(); }
async function openMusicPlatform(url, platformName) {
  if (url && url.includes("udio")) return openUdioPlatform();
  return openSunoPlatform();
}

// Suno 곡 링크 붙여넣기로 1초 만에 무료 다운로드 및 스튜디오 등록 (Out of Downloads 결제 우회)
async function importFromSunoLink() {
  const linkInput = document.getElementById("inputSunoLink");
  const rawUrl = linkInput ? linkInput.value.trim() : "";
  if (!rawUrl) {
    alert("Suno 사이트 화면의 [Copy Link] 버튼을 눌러 복사한 링크를 붙여넣어 주세요.");
    if (linkInput) linkInput.focus();
    return;
  }

  const ep = document.getElementById("inputEpisode").value || "제01화";
  const btn = document.getElementById("btnImportSuno");
  const origBtnText = btn ? btn.innerHTML : "📥 무료 가져오기";

  const statusBox = document.getElementById("studioAudioUploadStatus");
  if (statusBox) {
    statusBox.className = "upload-status-text loading";
    statusBox.style.display = "block";
    statusBox.innerHTML = `<span>⏳ [${ep}] Suno CDN에서 무료 음원(MP3) 다운로드 및 등록 중...</span>`;
  }
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = "⏳ 가져오는 중...";
  }

  try {
    const res = await fetch("/api/import_suno_url", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url: rawUrl,
        episode_no: ep
      })
    });
    const data = await res.json();

    if (data.success) {
      currentMusicFile = data.music_file;
      currentAudioFile = data.music_file;

      const previewArea = document.getElementById("studioAudioPreviewArea");
      const player = document.getElementById("studioAudioPlayer");
      const nameElem = document.getElementById("studioPreviewAudioFilename");

      if (nameElem) nameElem.textContent = data.filename;
      if (player) {
        player.src = `${data.web_url}?t=${Date.now()}`;
        player.load();
      }
      if (previewArea) previewArea.style.display = "block";

      if (statusBox) {
        statusBox.className = "upload-status-text success";
        statusBox.innerHTML = `<span>✓ [${ep}] Suno 음원이 100% 무료로 성공적으로 등록되었습니다! (${Math.round((data.size || 0)/1024)} KB)</span>`;
      }
      if (linkInput) linkInput.value = "";
      showToast(`🎉 [${ep}] Suno 음원이 결제 없이 100% 무료로 등록되었습니다!`, "success");
      await loadStatus();
    } else {
      if (statusBox) {
        statusBox.className = "upload-status-text error";
        statusBox.innerHTML = `<span>✕ 실패: ${data.error || "음원을 가져오지 못했습니다."}</span>`;
      }
      alert(`음원 가져오기 실패:\n${data.error || "알 수 없는 오류가 발생했습니다."}`);
    }
  } catch (err) {
    if (statusBox) {
      statusBox.className = "upload-status-text error";
      statusBox.innerHTML = `<span>✕ 네트워크 오류가 발생했습니다: ${err}</span>`;
    }
    alert("서버 연결 실패: " + err);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = origBtnText;
    }
  }
}

// Suno 공유 링크로 7회 다운로드 제한 없이 즉시 음원 가져오기
async function onImportSunoShare() {
  const input = document.getElementById("inputSunoShareUrl") || document.getElementById("inputSunoLink");
  const rawUrl = input ? input.value.trim() : "";
  if (!rawUrl) {
    alert("Suno 사이트에서 곡 화면의 [Share] ➜ [Copy Link]를 눌러 복사한 링크를 붙여넣어 주세요.\n(예: https://suno.com/song/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)");
    if (input) input.focus();
    return;
  }

  const ep = document.getElementById("inputEpisode")?.value || "제01화";
  const btn = document.getElementById("btnImportSunoShare") || document.getElementById("btnImportSuno");
  const origText = btn ? btn.innerHTML : "📥 음원 가져오기";
  const statusBox = document.getElementById("studioAudioUploadStatus");

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<span>⏳ CDN 음원 가져오는 중...</span>`;
  }
  if (statusBox) {
    statusBox.className = "upload-status-text loading";
    statusBox.style.display = "block";
    statusBox.innerHTML = `<span>⏳ [${ep}] Suno 스트리밍 CDN에서 7회 다운로드 제한 없이 고음질 MP3를 내려받는 중입니다...</span>`;
  }

  try {
    const res = await fetch("/api/import_suno_share", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        share_url: rawUrl,
        episode_no: ep
      })
    });
    const data = await res.json();

    if (res.ok && data.success) {
      currentMusicFile = data.rel_path || data.filename;
      currentAudioFile = currentMusicFile;

      // 스튜디오 오디오 플레이어 배너 갱신
      const previewArea = document.getElementById("studioAudioPreviewArea");
      const player = document.getElementById("studioAudioPlayer");
      const nameElem = document.getElementById("studioPreviewAudioFilename");

      if (nameElem) nameElem.textContent = data.filename;
      if (player && data.music_url) {
        player.src = data.music_url;
        player.load();
      }
      if (previewArea) previewArea.style.display = "block";

      if (statusBox) {
        statusBox.className = "upload-status-text success";
        statusBox.innerHTML = `<span>✓ [${ep}] Suno 음원이 7회 다운로드 제한 없이 성공적으로 등록되었습니다! (${data.filename})</span>`;
      }
      if (input) input.value = "";
      showToast(`🎉 [${ep}] Suno 노래 음원이 7회 제한 없이 성공적으로 시집에 등록되었습니다!`, "success");
      await loadStatus();
    } else {
      const errMsg = data.detail || data.error || "음원을 가져오지 못했습니다.";
      if (statusBox) {
        statusBox.className = "upload-status-text error";
        statusBox.innerHTML = `<span>✕ 실패: ${errMsg}</span>`;
      }
      alert(`Suno 음원 가져오기 실패:\n${errMsg}`);
    }
  } catch (err) {
    if (statusBox) {
      statusBox.className = "upload-status-text error";
      statusBox.innerHTML = `<span>✕ 서버 통신 오류: ${err}</span>`;
    }
    alert("서버 연결 실패: " + err);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = origText;
    }
  }
}

function triggerStudioAudioFileInput() {
  const input = document.getElementById("studioAudioFileInput");
  if (input) input.click();
}

function onStudioAudioFileSelected(event) {
  const file = event.target.files && event.target.files[0];
  if (file) {
    uploadStudioAudio(file);
  }
}

async function uploadStudioAudio(file) {
  const ep = document.getElementById("inputEpisode").value || "제01화";
  const statusBox = document.getElementById("studioAudioUploadStatus");
  if (statusBox) {
    statusBox.className = "upload-status-text loading";
    statusBox.style.display = "block";
    statusBox.innerHTML = `<span>⏳ [${ep}] 노래 음원 분석 및 앞뒤 무음 자동 다듬기 진행 중...</span>`;
  }

  const formData = new FormData();
  formData.append("audio_file", file);
  formData.append("episode_no", ep);

  // 📜 현재 입력된 노랫말(Suno 가사)도 함께 원고에 자동 저장
  const lyricsInput = document.getElementById("musicLyricsInput");
  if (lyricsInput && lyricsInput.value.trim()) {
    formData.append("lyrics", lyricsInput.value.trim());
  }

  try {
    const res = await fetch("/api/upload_audio", {
      method: "POST",
      body: formData
    });
    const data = await res.json();
    if (data.success) {
      currentMusicFile = data.music_file || data.audio_file;
      currentAudioFile = currentMusicFile;
      if (statusBox) {
        statusBox.className = "upload-status-text success";
        let msg = `<span>✨ [안실장 최적화] `;
        if (data.trimmed && data.trimmed_seconds > 0) {
          msg += `앞뒤 무음 <strong>${data.trimmed_seconds}초</strong>를 깔끔하게 잘라내고 고음질(320k) MP3로 등록 완료! (${data.orig_duration} ➔ ${data.final_duration})`;
        } else {
          msg += `${data.trim_message || '표준 고음질(320k) MP3로 안전하게 등록되었습니다.'}`;
        }
        msg += `<br><small style="color: #643e19;">💡 노래와 실제 가사가 다를 경우 위의 [📜 완성된 노래 가사] 칸에 Suno 가사를 붙여넣고 [원고 저장]을 누르시면 갤러리에도 즉시 일치됩니다.</small></span>`;
        statusBox.innerHTML = msg;
      }
      // 미리듣기 오디오 플레이어 노출
      const previewArea = document.getElementById("studioAudioPreviewArea");
      const player = document.getElementById("studioAudioPlayer");
      const nameElem = document.getElementById("studioPreviewAudioFilename");
      if (nameElem) {
        let tag = data.filename;
        if (data.trimmed && data.trimmed_seconds > 0) {
          tag += ` (무음 ${data.trimmed_seconds}초 자동 정리)`;
        }
        nameElem.textContent = tag;
      }
      if (player) {
        player.src = data.web_url;
        player.load();
      }
      if (previewArea) previewArea.style.display = "block";

      const toastMsg = data.trimmed
        ? `✨ [안실장] 앞뒤 무음 ${data.trimmed_seconds}초를 깔끔하게 다듬어 고음질 MP3로 등록했습니다!`
        : `✓ [${ep}] 노래 음원이 고음질 MP3로 성공적으로 등록되었습니다!`;
      if (typeof showToast === 'function') showToast(toastMsg, "success");
      if (typeof loadStatus === 'function') await loadStatus();
    } else {
      if (statusBox) {
        statusBox.className = "upload-status-text error";
        statusBox.innerHTML = `<span>❌ 업로드 실패: ${data.error || '오류'}</span>`;
      }
      alert(`음원 등록 실패: ${data.error || '알 수 없는 오류'}`);
    }
  } catch (err) {
    if (statusBox) {
      statusBox.className = "upload-status-text error";
      statusBox.innerHTML = `<span>❌ 네트워크 오류: ${err}</span>`;
    }
    alert(`음원 업로드 중 네트워크 오류가 발생했습니다: ${err}`);
  }
}

function removeAudioFile() {
  currentMusicFile = "";
  currentAudioFile = currentReciteFile || "";
  const previewArea = document.getElementById("studioAudioPreviewArea");
  if (previewArea) previewArea.style.display = "none";
  const player = document.getElementById("studioAudioPlayer");
  if (player) {
    player.pause();
    player.src = "";
  }
  const statusBox = document.getElementById("studioAudioUploadStatus");
  if (statusBox) statusBox.style.display = "none";
  const trimBox = document.getElementById("audioTrimBox");
  if (trimBox) trimBox.style.display = "none";
}

function toggleAudioTrimBox() {
  const box = document.getElementById("audioTrimBox");
  if (!box) return;
  const isHidden = box.style.display === "none";
  box.style.display = isHidden ? "block" : "none";
  if (isHidden) {
    const player = document.getElementById("studioAudioPlayer");
    const endInput = document.getElementById("inputTrimEnd");
    if (player && player.duration && endInput && !endInput.value) {
      endInput.value = formatAudioSeconds(player.duration);
    }
  }
}

function formatAudioSeconds(sec) {
  if (isNaN(sec) || sec < 0) return "00:00";
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

function setTrimStartFromCurrent() {
  const player = document.getElementById("studioAudioPlayer");
  const input = document.getElementById("inputTrimStart");
  if (player && input) {
    input.value = formatAudioSeconds(player.currentTime);
    if (typeof showToast === 'function') showToast(`시작 시간 설정: ${input.value}`, "info");
  }
}

function setTrimEndFromCurrent() {
  const player = document.getElementById("studioAudioPlayer");
  const input = document.getElementById("inputTrimEnd");
  if (player && input) {
    input.value = formatAudioSeconds(player.currentTime);
    if (typeof showToast === 'function') showToast(`끝 시간 설정: ${input.value} (다음 곡 직전 위치)`, "info");
  }
}

async function onApplyAudioTrim() {
  const ep = document.getElementById("inputEpisode")?.value || "제01화";
  const startVal = document.getElementById("inputTrimStart")?.value.trim() || "00:00";
  const endVal = document.getElementById("inputTrimEnd")?.value.trim() || "";

  if (!endVal) {
    alert("끝 시간을 입력하거나, 노래를 들으시다가 다음 곡이 나오기 직전에 [끝: 현재위치] 버튼을 눌러주세요.");
    return;
  }

  const btn = document.getElementById("btnApplyTrim");
  const origBtnText = btn ? btn.innerHTML : "✂️ 자르기 적용";
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = "⏳ 자르는 중...";
  }

  try {
    const res = await fetch("/api/trim_audio", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        episode_no: ep,
        start_time: startVal,
        end_time: endVal
      })
    });
    const data = await res.json();
    if (data.success) {
      const player = document.getElementById("studioAudioPlayer");
      if (player) {
        player.pause();
        player.src = `${data.web_url}&cachebust=${Date.now()}`;
        player.load();
      }
      const nameElem = document.getElementById("studioPreviewAudioFilename");
      if (nameElem) {
        nameElem.textContent = `${data.filename} (${data.new_duration_str})`;
      }
      const statusBox = document.getElementById("studioAudioUploadStatus");
      if (statusBox) {
        statusBox.className = "upload-status-text success";
        statusBox.style.display = "block";
        statusBox.innerHTML = `<span>✨ [안실장 미세 다듬기] ${data.message}</span>`;
      }
      if (typeof showToast === 'function') {
        showToast(`✨ [${ep}] ${data.message}`, "success");
      }
      const box = document.getElementById("audioTrimBox");
      if (box) box.style.display = "none";
      if (typeof loadStatus === 'function') await loadStatus();
    } else {
      alert(`자르기 실패: ${data.error || '오류가 발생했습니다.'}`);
    }
  } catch (err) {
    alert(`네트워크 오류: ${err}`);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = origBtnText;
    }
  }
}

function removeReciteFile() {
  currentReciteFile = "";
  currentAudioFile = currentMusicFile || "";
  const previewArea = document.getElementById("studioRecitePreviewArea");
  if (previewArea) previewArea.style.display = "none";
  const player = document.getElementById("studioRecitePlayer");
  if (player) {
    player.pause();
    player.src = "";
  }
}

// =========================================================
// 19. Colab YuE2 맞춤형 노트북 동적 다운로드 및 [3단계] 코드 복사
// =========================================================
async function downloadModularNotebook() {
  const ep = document.getElementById("inputEpisode").value || "제01화";
  const title = document.getElementById("inputFinalTitle").value.trim() || "무제";
  const lyricsInput = document.getElementById("musicLyricsInput");
  const lyrics = lyricsInput ? lyricsInput.value.trim() : "";

  const genrePrompt = getMusicGenrePrompt(currentMusicGenre);

  try {
    const res = await fetch("/api/export_colab_notebook", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        episode_no: ep,
        title: title,
        genre_prompt: genrePrompt,
        lyrics: lyrics
      })
    });
    const data = await res.json();
    if (data.success && data.notebook) {
      const blob = new Blob([JSON.stringify(data.notebook, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = data.filename || "노래음원_YuE2_원클릭.ipynb";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      alert(`🎉 [${ep}] 「${title}」 맞춤형 Colab 노트북이 다운로드되었습니다!\n\n파일명: ${data.filename}\n\nGoogle Colab에서 업로드하여 [런타임 모두 실행]을 누르시면 곧바로 작곡이 시작됩니다.`);
    } else {
      alert("노트북 생성 실패: " + (data.error || "오류"));
    }
  } catch (err) {
    alert("노트북 다운로드 중 오류 발생: " + err);
  }
}

function copyStep3Code() {
  const ep = document.getElementById("inputEpisode").value || "제01화";
  const title = document.getElementById("inputFinalTitle").value.trim() || "무제";
  const cleanEp = ep.replace(/[^0-9]/g, '').padStart(2, '0') || "01";
  const cleanTitle = title.replace(/[\s\\/*?:"<>|]/g, '_') || "노래";
  const outFilename = `${cleanEp}_${cleanTitle}.mp3`;
  const lyricsInput = document.getElementById("musicLyricsInput");
  const lyrics = lyricsInput ? lyricsInput.value.trim() : "";

  const genrePrompt = getMusicGenrePrompt(currentMusicGenre);

  const step3Code = `# @title [3단계] 노랫말 및 사운드 프롬프트 구성 (스토리북 스튜디오 연동)
import os

SONG_EPISODE = "${ep}"
SONG_TITLE = "${title}"
TARGET_FILENAME = "${outFilename}"

GENRE_PROMPT = """${genrePrompt}"""

LYRICS_CONTENT = """${lyrics}"""

os.makedirs("/content/input", exist_ok=True)
with open("/content/input/genre.txt", "w", encoding="utf-8") as f:
    f.write(GENRE_PROMPT.strip())
with open("/content/input/lyrics.txt", "w", encoding="utf-8") as f:
    f.write(LYRICS_CONTENT.strip())

print(f"✅ 3단계: [{SONG_EPISODE}] {SONG_TITLE} 가사 및 프롬프트 준비 완료! (/content/input/)")`;

  navigator.clipboard.writeText(step3Code).then(() => {
    alert("📋 [3단계 파이썬 코드]가 클립보드에 복사되었습니다!\n\n노래음원_YuE2_원클릭.ipynb의 [3단계] 셀에 그대로 [Ctrl+V] 붙여넣기 하시면 됩니다.");
  });
}

// =========================================================
// 19-2. Colab SDXL 맞춤형 삽화 노트북 동적 다운로드 및 [3단계] 코드 복사
// =========================================================
let colabImageTargetEpisode = null;
let colabImageTargetTitle = null;

function onOpenGoogleFlowLink(e) {
  const promptElem = document.getElementById("imagePromptDisplay");
  let promptStr = promptElem ? (promptElem.value || promptElem.textContent || "").trim() : "";
  if (!promptStr) {
    const title = document.getElementById("inputFinalTitle")?.value?.trim() || "무제";
    promptStr = `Korean lyric watercolor illustration, ${title}, soft warm lighting, poetic negative space, delicate ink wash, 300 dpi, masterpiece`;
  }

  // 프롬프트 클립보드 자동 복사
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(promptStr);
  }

  // 차단 없는 토스트 안내
  showToast("📋 현재 시의 300 DPI 프롬프트가 복사되었습니다! 새 창 Flow 입력창에 [Ctrl+V] 하세요.", "success");
}

function openGoogleFlowGuide() {
  onOpenGoogleFlowLink();
  window.open("https://flow.google.com/", "_blank");
}

function openColabImageGuide() {
  colabImageTargetEpisode = null;
  colabImageTargetTitle = null;
  const modal = document.getElementById("colabImageModal");
  if (modal) modal.style.display = "flex";
}

function openColabImageGuideFromViewer() {
  const select = document.getElementById("selectWorkDropdown");
  const selectedEp = select ? select.value : "";
  const work = (typeof currentBookWorks !== "undefined" && Array.isArray(currentBookWorks))
    ? currentBookWorks.find(w => w.episode_no === selectedEp)
    : null;
  if (work) {
    colabImageTargetEpisode = work.episode_no;
    colabImageTargetTitle = work.title;
  }
  const modal = document.getElementById("colabImageModal");
  if (modal) modal.style.display = "flex";
}

function closeColabImageModal() {
  const modal = document.getElementById("colabImageModal");
  if (modal) modal.style.display = "none";
}

async function downloadModularImageNotebook() {
  let ep = colabImageTargetEpisode || document.getElementById("inputEpisode")?.value || "제01화";
  let title = colabImageTargetTitle || document.getElementById("inputFinalTitle")?.value?.trim() || "무제";
  
  // 프롬프트 취득
  let promptStr = "";
  const promptElem = document.getElementById("imagePromptDisplay");
  if (promptElem) {
    promptStr = (promptElem.value || promptElem.textContent || "").trim();
  }
  if (!promptStr) {
    const memory = document.getElementById("inputCoreMemory")?.value || "";
    promptStr = memory ? `${title}, ${memory}` : `${title}의 정경`;
  }

  const artStyle = typeof currentArtStyle !== "undefined" ? currentArtStyle : "watercolor";

  try {
    const res = await fetch("/api/export_colab_image_notebook", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        episode_no: ep,
        title: title,
        prompt: promptStr,
        art_style: artStyle,
        width: 768,
        height: 1024
      })
    });
    const data = await res.json();
    if (data.success && data.notebook) {
      const blob = new Blob([JSON.stringify(data.notebook, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = data.filename || "삽화_Colab_원클릭.ipynb";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      alert(`🎉 [${ep}] 「${title}」 맞춤형 Colab 삽화 노트북이 다운로드되었습니다!\n\n파일명: ${data.filename}\n\nGoogle Colab에서 업로드하여 [런타임 모두 실행]을 누르시면 T4 GPU에서 5초 만에 2가지 시안이 완성됩니다.`);
    } else {
      alert("노트북 생성 실패: " + (data.error || "오류"));
    }
  } catch (err) {
    alert("노트북 다운로드 중 오류 발생: " + err);
  }
}

function copyStep3ImageCode() {
  let ep = colabImageTargetEpisode || document.getElementById("inputEpisode")?.value || "제01화";
  let title = colabImageTargetTitle || document.getElementById("inputFinalTitle")?.value?.trim() || "무제";
  const cleanEp = ep.replace(/[^0-9]/g, '').padStart(2, '0') || "01";
  const cleanTitle = title.replace(/[\s\\/*?:"<>|]/g, '_') || "삽화";
  const fileA = `${cleanEp}_${cleanTitle}_시안A.jpg`;
  const fileB = `${cleanEp}_${cleanTitle}_시안B.jpg`;

  let promptStr = "";
  const promptElem = document.getElementById("imagePromptDisplay");
  if (promptElem) {
    promptStr = (promptElem.value || promptElem.textContent || "").trim();
  }
  if (!promptStr) {
    promptStr = `${title}의 정경`;
  }

  const step3Code = `# @title [3단계] 삽화 메타데이터 및 프롬프트 설정 (동적 조립 모듈)
EPISODE_NO = "${ep}"
WORK_TITLE = "${title}"
FILE_A = "${fileA}"
FILE_B = "${fileB}"
IMAGE_WIDTH = 768
IMAGE_HEIGHT = 1024
STEPS = 4

PROMPT_A = """${promptStr}, tranquil poetic negative space, minimalist composition, korean lyric watercolor painting, delicate brush strokes, soft watercolor wash, poetic negative space, gentle morning light, nostalgic mood, masterpiece, highly detailed, 300 dpi illustration"""
PROMPT_B = """${promptStr}, warm nostalgic ambiance, intimate poetic harmony, rich atmospheric details, korean lyric watercolor painting, delicate brush strokes, soft watercolor wash, poetic negative space, gentle morning light, nostalgic mood, masterpiece, highly detailed, 300 dpi illustration"""
NEGATIVE_PROMPT = """ugly, deformed, disfigured, poor anatomy, bad hands, blurry, low quality, oversaturated, text, watermark, signature, modern electronics, photo frame"""

print(f"✅ 3단계: [{EPISODE_NO}] {WORK_TITLE} 삽화 프롬프트 준비 완료!")`;

  navigator.clipboard.writeText(step3Code).then(() => {
    alert("📋 [3단계 파이썬 코드]가 클립보드에 복사되었습니다!\n\nColab 삽화 노트북의 [3단계] 셀에 그대로 [Ctrl+V] 붙여넣기 하시면 됩니다.");
  });
}

// =========================================================
// 19. 고품질 스마트 커스텀 풍선 도움말 (Smart Custom Tooltip)
// - 너비: 가로로 길어지지 않게 약 절반(max-width 270px)으로 압축
// - 폰트: 15px(0.95rem)로 시원하고 또렷하게 확대
// - [제목] 배지와 설명 단락 분리 및 스마트 화면 경계 보정
// =========================================================
function initCustomTooltips() {
  let tooltip = document.getElementById("appCustomTooltip");
  if (!tooltip) {
    tooltip = document.createElement("div");
    tooltip.id = "appCustomTooltip";
    tooltip.className = "app-custom-tooltip";
    document.body.appendChild(tooltip);
  }

  let activeTarget = null;

  function findTooltipTarget(el) {
    while (el && el !== document.body && el !== document.documentElement) {
      if (el.getAttribute && (el.hasAttribute("title") || el.hasAttribute("data-tooltip"))) {
        return el;
      }
      el = el.parentElement;
    }
    return null;
  }

  function escapeTooltipHtml(str) {
    if (!str) return '';
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function showTooltip(target, clientX, clientY) {
    if (target.hasAttribute("title")) {
      const titleText = target.getAttribute("title").trim();
      if (titleText) {
        target.setAttribute("data-tooltip", titleText);
      }
      target.removeAttribute("title");
    }

    const text = target.getAttribute("data-tooltip");
    if (!text) {
      hideTooltip();
      return;
    }

    activeTarget = target;

    // [제목] 헤더 배지와 본문 설명 분리 렌더링
    const badgeMatch = text.match(/^(\[[^\]]+\])\s*([\s\S]*)$/);
    if (badgeMatch) {
      const badge = badgeMatch[1];
      const desc = badgeMatch[2];
      tooltip.innerHTML = `<span class="tooltip-header-badge">${escapeTooltipHtml(badge)}</span><span class="tooltip-desc">${escapeTooltipHtml(desc)}</span>`;
    } else {
      tooltip.innerHTML = `<span class="tooltip-desc">${escapeTooltipHtml(text)}</span>`;
    }

    tooltip.classList.add("visible");
    updateTooltipPos(clientX, clientY);
  }

  function hideTooltip() {
    activeTarget = null;
    if (tooltip) {
      tooltip.classList.remove("visible");
    }
  }

  function updateTooltipPos(clientX, clientY) {
    if (!tooltip) return;
    const padding = 14;
    let left = clientX + 16;
    let top = clientY + 18;

    const rect = tooltip.getBoundingClientRect();
    const tooltipWidth = rect.width || 240;
    const tooltipHeight = rect.height || 80;

    // 화면 오른쪽 경계 벗어남 방지
    if (left + tooltipWidth > window.innerWidth - padding) {
      left = clientX - tooltipWidth - 14;
    }
    if (left < padding) {
      left = padding;
    }

    // 화면 아래쪽 경계 벗어남 방지
    if (top + tooltipHeight > window.innerHeight - padding) {
      top = clientY - tooltipHeight - 14;
    }
    if (top < padding) {
      top = padding;
    }

    tooltip.style.left = `${left}px`;
    tooltip.style.top = `${top}px`;
  }

  // mousemove 기반 스마트 감지: 마우스 위치에 따라 대상 요소 자동 인식 및 툴팁 표시
  document.addEventListener("mousemove", (e) => {
    const target = findTooltipTarget(e.target);
    if (!target) {
      if (activeTarget) {
        hideTooltip();
      }
      return;
    }

    if (target !== activeTarget) {
      showTooltip(target, e.clientX, e.clientY);
    } else {
      updateTooltipPos(e.clientX, e.clientY);
    }
  });

  window.addEventListener("scroll", hideTooltip, { passive: true });
}

// ========================================================
// 🎙️ 음성 인터뷰 (Web Speech API STT) & 시 낭송 (TTS)
// ========================================================
let currentRecognition = null;
let activeTargetId = null;
let activeBtnId = null;

function toggleVoiceDictation(targetInputId, btnId) {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    alert("현재 브라우저는 음성 인식(STT) 기능을 지원하지 않습니다.\nGoogle Chrome 또는 Microsoft Edge 브라우저를 이용해 주시기 바랍니다.");
    return;
  }

  const btn = document.getElementById(btnId);
  const target = document.getElementById(targetInputId);
  if (!target) return;

  // 이미 실행 중이고 동일한 버튼을 누른 경우 -> 중지
  if (currentRecognition && activeBtnId === btnId) {
    currentRecognition.stop();
    return;
  }

  // 다른 버튼이 실행 중이었던 경우 -> 기존 인식 중지
  if (currentRecognition) {
    currentRecognition.stop();
  }

  try {
    const recognition = new SpeechRecognition();
    recognition.lang = 'ko-KR';
    recognition.continuous = true;
    recognition.interimResults = true;

    currentRecognition = recognition;
    activeTargetId = targetInputId;
    activeBtnId = btnId;

    let baseText = target.value;
    let finalChunk = '';

    if (btn) {
      btn.classList.add('mic-recording');
      btn.innerHTML = `<span class="mic-icon recording-pulse">🔴</span> <span class="mic-label">듣고 있어요... (중지)</span>`;
    }

    recognition.onresult = (event) => {
      let interimChunk = '';
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          finalChunk += event.results[i][0].transcript + ' ';
        } else {
          interimChunk += event.results[i][0].transcript;
        }
      }

      const spoken = (finalChunk + interimChunk).trim();
      if (baseText) {
        const needsSpace = !(baseText.endsWith('\n') || baseText.endsWith(' '));
        target.value = baseText + (needsSpace ? ' ' : '') + spoken;
      } else {
        target.value = spoken;
      }
      target.dispatchEvent(new Event('input'));
    };

    recognition.onerror = (event) => {
      console.warn("음성 인식 이벤트:", event.error);
      if (event.error === 'not-allowed') {
        alert("마이크 사용 권한이 허용되지 않았습니다.\n브라우저 주소창 좌측의 자물쇠/사이트 설정 아이콘을 눌러 마이크 권한을 '허용'해 주세요.");
      }
    };

    recognition.onend = () => {
      if (btn) {
        btn.classList.remove('mic-recording');
        if (targetInputId === 'inputFinalPoem') {
          btn.innerHTML = `<span class="mic-icon">🎙️</span> <span class="mic-label">음성 구술</span>`;
        } else {
          btn.innerHTML = `<span class="mic-icon">🎙️</span> <span class="mic-label">말로 구술하기</span>`;
        }
      }
      currentRecognition = null;
      activeTargetId = null;
      activeBtnId = null;
    };

    recognition.start();

  } catch (err) {
    console.error("음성 인식 시작 실패:", err);
    alert("마이크를 시작할 수 없습니다: " + err.message);
  }
}

// 🎧 시 낭송 듣기 (Google Gemini TTS & Microsoft Edge-TTS 지능형 하이브리드 연동)
let currentGeminiReciteAudio = null;
let currentTtsEngine = 'gemini'; // 'gemini' | 'edge'
let isGeminiCreditExpired = false;

// 1. Google Gemini 전용 AI 서정 성우 목록
const GEMINI_VOICES = [
  { value: "Aoede", text: "🌸 여성 서정 (맑고 따뜻함)" },
  { value: "Charon", text: "🍃 남성 중저음 (깊은 울림)" },
  { value: "Kore", text: "🍵 여성 차분 (온화한 호흡)" },
  { value: "Puck", text: "🌾 남성 담백 (진솔한 청년)" },
  { value: "Fenrir", text: "🕊️ 원로 중후 (세월의 깊이)" }
];

// 2. Microsoft Edge-TTS 전용 고품질 신경망(Neural) 성우 목록 (100% 무료 무제한)
const EDGE_VOICES = [
  { value: "ko-KR-SunHiNeural", text: "🌸 선희 (맑은 서정 여성)" },
  { value: "ko-KR-InJoonNeural", text: "🍃 인준 (중후한 남성 중저음)" },
  { value: "ko-KR-HyunsuMultilingualNeural", text: "🌾 현수 (부드러운 청년 감성)" },
  { value: "ko-KR-BongJinNeural", text: "🕊️ 봉진 (차분하고 성숙한 남성)" }
];

// 성우 드롭다운 옵션 동적 교체
function updateVoiceSelectOptions(engine) {
  const select = document.getElementById("selectVoiceActor");
  if (!select) return;
  const currentVal = select.value;
  select.innerHTML = "";
  const list = (engine === "edge") ? EDGE_VOICES : GEMINI_VOICES;
  list.forEach(v => {
    const opt = document.createElement("option");
    opt.value = v.value;
    opt.textContent = v.text;
    select.appendChild(opt);
  });

  // 이전 선택 성우의 성별/톤에 맞춰 자연스러운 자동 매칭
  if (engine === "edge") {
    if (["Charon", "Fenrir"].includes(currentVal)) select.value = "ko-KR-InJoonNeural";
    else if (currentVal === "Puck") select.value = "ko-KR-HyunsuMultilingualNeural";
    else select.value = "ko-KR-SunHiNeural";
  } else {
    if (currentVal.includes("InJoon") || currentVal.includes("BongJin")) select.value = "Charon";
    else if (currentVal.includes("Hyunsu")) select.value = "Puck";
    else select.value = "Aoede";
  }
}

// TTS 엔진 상태 반영 및 UI 교체
function setTtsEngine(engine, isCreditExpired = false) {
  currentTtsEngine = engine;
  isGeminiCreditExpired = isCreditExpired;

  const badge = document.getElementById("badgeTtsEngine");
  const container = document.getElementById("ttsVoiceContainer");
  const btnCheck = document.getElementById("btnCheckGoogleCredit");

  updateVoiceSelectOptions(engine);

  if (engine === "edge") {
    if (badge) {
      badge.textContent = "⚡ Edge-TTS";
      badge.style.background = "#059669";
      badge.title = "[Edge-TTS 모드] 100% 무료 무제한 고품질 신경망 성우로 낭송합니다. (클릭하여 전환)";
    }
    if (container) {
      container.style.borderColor = "#10B981";
      container.style.background = "#ECFDF5";
    }
    if (btnCheck) {
      btnCheck.style.display = "inline-block";
    }
  } else {
    if (badge) {
      badge.textContent = "🌐 Google TTS";
      badge.style.background = "#E11D48";
      badge.title = "[Google Gemini TTS 모드] 고품질 AI 서정 성우로 낭송합니다. (클릭하여 전환)";
    }
    if (container) {
      container.style.borderColor = "#F43F5E";
      container.style.background = "#FFF1F2";
    }
    if (btnCheck) {
      btnCheck.style.display = "none";
    }
  }
}

// 사용자가 배지를 클릭했을 때 수동 전환 토글
async function toggleTtsEngineManual() {
  if (currentTtsEngine === "gemini") {
    setTtsEngine("edge", isGeminiCreditExpired);
    showToast("⚡ Microsoft Edge-TTS(무료 고음질 신경망) 성우 모드로 전환되었습니다.", "info");
  } else {
    if (isGeminiCreditExpired) {
      checkGoogleCreditRecovery();
    } else {
      setTtsEngine("gemini", false);
      showToast("🌐 Google Gemini TTS 성우 모드로 전환되었습니다.", "info");
    }
  }
}

// 📢 TTS 알림 전용 안전 모달 (절대로 저절로 닫히지 않으며 사용자가 확인할 때까지 유지)
function showTtsNoticeModal(options) {
  const { title, html, icon = 'info', confirmText = '확인', confirmColor = '#059669' } = options;

  if (window.Swal) {
    Swal.fire({
      icon: icon,
      title: title,
      html: html,
      allowOutsideClick: false,
      allowEscapeKey: false,
      showConfirmButton: true,
      confirmButtonText: confirmText,
      confirmButtonColor: confirmColor
    });
    return;
  }

  // SweetAlert2 라이브러리 부재 시 자체 DOM 팝업 모달
  let modalOverlay = document.getElementById("ttsCustomNoticeModal");
  if (!modalOverlay) {
    modalOverlay = document.createElement("div");
    modalOverlay.id = "ttsCustomNoticeModal";
    modalOverlay.style.position = "fixed";
    modalOverlay.style.inset = "0";
    modalOverlay.style.background = "rgba(0, 0, 0, 0.6)";
    modalOverlay.style.backdropFilter = "blur(3px)";
    modalOverlay.style.zIndex = "999999";
    modalOverlay.style.display = "flex";
    modalOverlay.style.alignItems = "center";
    modalOverlay.style.justifyContent = "center";
    modalOverlay.style.padding = "20px";
    document.body.appendChild(modalOverlay);
  }

  modalOverlay.innerHTML = `
    <div style="background: #FFFFFF; border-radius: 12px; width: 100%; max-width: 490px; box-shadow: 0 20px 45px rgba(0,0,0,0.3); overflow: hidden; border: 1.5px solid #E5E7EB;">
      <div style="padding: 18px 22px; border-bottom: 1px solid #E5E7EB; display: flex; align-items: center; justify-content: space-between; background: #FAF5FF;">
        <h3 style="margin: 0; font-size: 1.05rem; font-weight: 700; color: #1F2937;">${title}</h3>
        <button type="button" onclick="closeTtsNoticeModal()" style="border: none; background: transparent; font-size: 1.25rem; line-height: 1; cursor: pointer; color: #6B7280; padding: 2px 6px;">✕</button>
      </div>
      <div style="padding: 22px 24px; max-height: 60vh; overflow-y: auto;">
        ${html}
      </div>
      <div style="padding: 14px 22px; background: #F9FAFB; border-top: 1px solid #E5E7EB; text-align: right;">
        <button type="button" onclick="closeTtsNoticeModal()" style="background: ${confirmColor}; color: #FFFFFF; border: none; border-radius: 6px; padding: 9px 22px; font-size: 0.92rem; font-weight: 700; cursor: pointer; box-shadow: 0 2px 6px rgba(0,0,0,0.15);">${confirmText}</button>
      </div>
    </div>
  `;
  modalOverlay.style.display = "flex";
}

function closeTtsNoticeModal() {
  const modal = document.getElementById("ttsCustomNoticeModal");
  if (modal) modal.style.display = "none";
}

// Google 크레딧 재충전 확인 및 Google TTS 복구
async function checkGoogleCreditRecovery(e) {
  if (e) {
    e.preventDefault();
    e.stopPropagation();
  }

  const btnCheck = document.getElementById("btnCheckGoogleCredit");
  if (btnCheck) {
    btnCheck.disabled = true;
    btnCheck.textContent = "⏳ 확인 중...";
  }

  try {
    const res = await fetch("/api/tts/check_google", { method: "POST" });
    const data = await res.json();
    if (data.success) {
      setTtsEngine("gemini", false);
      showTtsNoticeModal({
        icon: "success",
        title: "🎉 Google TTS 복원 완료!",
        html: `<p style="font-size: 0.95rem; color: #166534; line-height: 1.6; margin: 0;">Google API 크레딧 충전 및 연결이 정상 확인되었습니다.<br><strong style="color: #BE123C;">Google Gemini TTS</strong> 성우 목록으로 자동 복원되었습니다.</p>`,
        confirmColor: "#166534"
      });
    } else {
      showTtsNoticeModal({
        icon: "warning",
        title: "⚠️ 아직 Google 크레딧이 충전되지 않음",
        html: `
          <div style="text-align: left; font-size: 0.9rem; line-height: 1.6; color: #374151;">
            <p style="margin: 0 0 8px 0;">Google Cloud API 크레딧이 아직 충전되지 않았거나 결제 활성화가 진행 중입니다.</p>
            <div style="background: #FFFBEB; border: 1px solid #FCD34D; padding: 10px 12px; border-radius: 6px; font-size: 0.83rem; color: #92400E; word-break: break-all; margin: 10px 0;">
              <strong>Google 응답:</strong> ${data.message || '402 Payment Required'}
            </div>
            <p style="margin: 10px 0 0 0; color: #047857; font-weight: 600;">
              💡 크레딧 충전 전까지 <strong>Edge-TTS(무료 고품질 신경망)</strong> 엔진이 계속 안전하게 유지됩니다.
            </p>
          </div>
        `,
        confirmColor: "#059669"
      });
    }
  } catch (err) {
    console.error("Google TTS 확인 실패:", err);
    showToast("서버 통신 오류로 Google TTS 상태 확인 실패", "error");
  } finally {
    if (btnCheck) {
      btnCheck.disabled = false;
      btnCheck.textContent = "🔄 크레딧 재충전 확인";
    }
  }
}

// 페이지 로드 시 초기 TTS 상태 점검
async function checkInitialTtsStatus() {
  try {
    const res = await fetch("/api/tts/status");
    const data = await res.json();
    if (data && data.gemini_credit_expired) {
      setTtsEngine("edge", true);
    } else if (data && data.engine) {
      setTtsEngine(data.engine, false);
    }
  } catch (err) {
    console.warn("TTS 상태 조회 실패:", err);
  }
}

async function toggleSpeakPoem() {
  const btn = document.getElementById("btnSpeakPoem");
  const poemText = document.getElementById("inputFinalPoem") ? document.getElementById("inputFinalPoem").value.trim() : "";
  const title = document.getElementById("inputFinalTitle") ? document.getElementById("inputFinalTitle").value.trim() : "무제";
  const ep = document.getElementById("inputEpisode") ? document.getElementById("inputEpisode").value.trim() : "제01화";

  const voiceSelect = document.getElementById("selectVoiceActor");
  const selectedVoice = voiceSelect ? voiceSelect.value : (currentTtsEngine === 'edge' ? "ko-KR-SunHiNeural" : "Aoede");
  const voiceNameText = voiceSelect && voiceSelect.selectedOptions[0] ? voiceSelect.selectedOptions[0].text : "AI 성우";

  // 1. 이미 재생 중인 경우 즉시 중지
  if (currentGeminiReciteAudio && !currentGeminiReciteAudio.paused) {
    currentGeminiReciteAudio.pause();
    currentGeminiReciteAudio.currentTime = 0;
    if (btn) btn.innerHTML = `🎧 시 낭송 듣기`;
    return;
  }
  if (window.speechSynthesis && window.speechSynthesis.speaking) {
    window.speechSynthesis.cancel();
    if (btn) btn.innerHTML = `🎧 시 낭송 듣기`;
    return;
  }

  if (!poemText) {
    alert("낭송할 시 본문이 비어 있습니다. 먼저 시를 다듬어 주세요.");
    return;
  }

  // 스튜디오 내 기존 육성 낭송 및 노래 플레이어 즉시 중지 (중복 재생 방지)
  const studioRecitePlayer = document.getElementById("studioRecitePlayer");
  const studioAudioPlayer = document.getElementById("studioAudioPlayer");
  if (studioRecitePlayer && !studioRecitePlayer.paused) studioRecitePlayer.pause();
  if (studioAudioPlayer && !studioAudioPlayer.paused) studioAudioPlayer.pause();

  // 2. TTS 호출 시도
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<span>⏳ ${voiceNameText.split(' ')[1] || '성우'} 낭송 빚는 중...</span>`;
  }

  try {
    const res = await fetch("/api/speak_poem", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: title,
        poem_body: poemText,
        episode_no: ep,
        voice: selectedVoice,
        engine: currentTtsEngine
      })
    });

    const data = await res.json();

    // 📢 Google 크레딧 만료 감지 시 알림 공지 및 Edge-TTS 모드 자동 전환
    if (data.gemini_credit_expired && (!isGeminiCreditExpired || data.just_switched)) {
      setTtsEngine("edge", true);
      showTtsNoticeModal({
        icon: 'warning',
        title: '📢 Google API 크레딧 만료 알림',
        html: `
          <div style="text-align: left; font-size: 0.92rem; line-height: 1.6; color: #374151;">
            <p style="margin-bottom: 8px; font-weight: 700; color: #BE123C;">Google Cloud API 크레딧이 만료(소진)되었습니다.</p>
            <p>시 낭송 감상이 끊기지 않도록 <strong>Microsoft Edge-TTS(고품질 신경망 성우)</strong>로 자동 전환되었습니다.</p>
            <ul style="padding-left: 20px; margin: 10px 0; color: #047857; font-weight: 600;">
              <li>성우 선택란이 Edge-TTS 신경망 성우(선희, 인준, 현수, 봉진)로 교체되었습니다.</li>
              <li>100% 무료·무제한으로 고음질 낭송이 생성되어 재생 및 보존됩니다.</li>
            </ul>
            <div style="background: #F3F4F6; padding: 10px; border-radius: 6px; font-size: 0.84rem; color: #4B5563;">
              💡 <strong>재충전 공지:</strong> Google Cloud 콘솔 결제 후, 성우 상자의 <strong>[🔄 크레딧 재충전 확인]</strong> 버튼을 누르시면 즉시 원래의 Google TTS로 복구됩니다.
            </div>
          </div>
        `,
        confirmText: '확인 및 계속 감상',
        confirmColor: '#059669'
      });
    }

    if (res.ok && data.success && (data.data_uri || data.audio_url)) {
      currentGeminiReciteAudio = new Audio(data.data_uri || data.audio_url);
      
      currentGeminiReciteAudio.onplay = () => {
        if (btn) {
          btn.disabled = false;
          btn.innerHTML = `⏹️ 낭송 중지`;
        }
      };

      currentGeminiReciteAudio.onended = () => {
        if (btn) btn.innerHTML = `🎧 시 낭송 듣기`;
      };

      currentGeminiReciteAudio.onerror = () => {
        if (btn) btn.innerHTML = `🎧 시 낭송 듣기`;
      };

      await currentGeminiReciteAudio.play();
      showToast(`✨ [${data.provider_name || voiceNameText}] 고음질 서정 낭송이 재생됩니다. (음원으로 보존됨)`, "success");

      // 🎙️ 본문 상단 [시 낭송 등록됨] 전용 오디오 플레이어 배너 즉시 연동 및 표시
      currentReciteFile = data.rel_path || `music/${data.filename}`;
      const recitePlayer = document.getElementById("studioRecitePlayer");
      const recitePreviewArea = document.getElementById("studioRecitePreviewArea");
      const reciteFilename = document.getElementById("studioPreviewReciteFilename");
      if (recitePlayer && data.audio_url) {
        recitePlayer.src = data.audio_url;
        if (reciteFilename) reciteFilename.textContent = data.filename;
        if (recitePreviewArea) recitePreviewArea.style.display = "block";
      }

      // 현재 status 내 works 캐시에도 낭송 파일 동기화
      if (currentStatus && currentStatus.works) {
        const curWork = currentStatus.works.find(w => w.episode_no === ep);
        if (curWork) {
          curWork.recite_file = currentReciteFile;
        }
      }

      // 우측 하단 음악 플레이어에도 보조 연동
      const audioPlayer = document.getElementById("studioAudioPlayer");
      const audioPreviewArea = document.getElementById("studioAudioPreviewArea");
      const audioFilename = document.getElementById("studioPreviewAudioFilename");
      if (audioPlayer && data.audio_url) {
        audioPlayer.src = data.audio_url;
        if (audioFilename) audioFilename.textContent = data.filename;
        if (audioPreviewArea) audioPreviewArea.style.display = "block";
      }
      return;
    } else {
      const errMsg = (data && (data.detail || data.error)) ? String(data.detail || data.error) : "TTS 서비스 호출 실패";
      console.warn("[TTS 실패]:", errMsg);
      showToast(`⚠️ 시 낭송 생성 실패: ${errMsg}`, "error", 6000);
    }
  } catch (err) {
    console.warn("TTS 호출 네트워크 예외 발생:", err);
    showToast("⚠️ <b>시 낭송 연결 실패:</b> 서버 네트워크 연결을 확인해주세요.", "error", 6000);
  } finally {
    if (btn) btn.disabled = false;
  }


  // 3. 폴백: 로컬 Web Speech API 브라우저 TTS
  if ('speechSynthesis' in window) {
    const fallbackText = (title && title !== "무제") ? `${title}.\n\n${poemText}` : poemText;
    const utterance = new SpeechSynthesisUtterance(fallbackText);
    utterance.lang = 'ko-KR';
    
    // 성우 성별/연령대에 맞춘 피치 및 속도 조절
    const isMale = ["Charon", "Puck", "Fenrir"].includes(selectedVoice);
    if (selectedVoice === "Fenrir") {
      utterance.pitch = 0.78;
      utterance.rate = 0.80;
    } else if (selectedVoice === "Charon") {
      utterance.pitch = 0.82;
      utterance.rate = 0.86;
    } else if (selectedVoice === "Puck") {
      utterance.pitch = 0.94;
      utterance.rate = 0.90;
    } else if (selectedVoice === "Kore") {
      utterance.pitch = 0.98;
      utterance.rate = 0.86;
    } else {
      utterance.pitch = 1.05; // Aoede 기본 여성
      utterance.rate = 0.88;
    }

    const voices = window.speechSynthesis.getVoices();
    const koVoices = voices.filter(v => v.lang.startsWith('ko'));
    if (koVoices.length > 0) {
      if (isMale) {
        const maleVoice = koVoices.find(v => v.name.includes("Male") || v.name.includes("남성") || v.name.includes("InJoon") || v.name.includes("MinHo"));
        utterance.voice = maleVoice || koVoices[0];
      } else {
        const femaleVoice = koVoices.find(v => v.name.includes("Female") || v.name.includes("여성") || v.name.includes("SunHi") || v.name.includes("HeaMi"));
        utterance.voice = femaleVoice || koVoices[0];
      }
    }

    utterance.onstart = () => { if (btn) btn.innerHTML = `⏹️ 낭송 중지`; };
    utterance.onend = () => { if (btn) btn.innerHTML = `🎧 시 낭송 듣기`; };
    utterance.onerror = () => { if (btn) btn.innerHTML = `🎧 시 낭송 듣기`; };

    window.speechSynthesis.speak(utterance);
  } else {
    alert("음성을 재생할 수 없습니다.");
  }
}

// ========================================================
// 21. 시집 목차 & 순서 편집기 (TOC & Order Editor)
// ========================================================
let tocEditItems = [];
let tocChapters = [
  "제1부: 흙과 솜꽃",
  "제2부: 밤을 잣는 손",
  "제3부: 바람과 불의 길",
  "제4부: 덜커덩, 세월을 짜다",
  "제5부: 살을 덮는 온기"
];

// 목차 편집 모달 열기
function openTocEditorModal() {
  const works = (currentStatus && currentStatus.works) ? currentStatus.works : [];
  if (works.length === 0) {
    alert("현재 등록된 시 작품이 없습니다.\n먼저 시를 작성해 주세요.");
    return;
  }

  // 챕터 목록 수집 (기존 프리셋 + 저장된 챕터 병합)
  const existingChapters = new Set(tocChapters);
  works.forEach(w => {
    if (w.chapter && w.chapter.trim()) {
      existingChapters.add(w.chapter.trim());
    }
  });
  tocChapters = Array.from(existingChapters);

  // 편집용 복사본 생성
  tocEditItems = works.map((w, idx) => ({
    episode_no: w.episode_no,
    title: w.title,
    chapter: w.chapter || ""
  }));

  renderTocEditorList();

  const modal = document.getElementById("tocEditorModal");
  if (modal) modal.style.display = "flex";
}

// 목차 편집 모달 닫기
function closeTocEditorModal() {
  const modal = document.getElementById("tocEditorModal");
  if (modal) modal.style.display = "none";
}

// 목차 리스트 UI 렌더링
function renderTocEditorList() {
  const container = document.getElementById("tocItemsListContainer");
  const countSummary = document.getElementById("tocItemCountSummary");
  if (!container) return;

  if (countSummary) {
    countSummary.textContent = `총 ${tocEditItems.length}편 수록 중`;
  }

  container.innerHTML = "";

  tocEditItems.forEach((item, idx) => {
    const card = document.createElement("div");
    card.style.cssText = `
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      padding: 9px 12px;
      background: #FFFFFF;
      border: 1px solid #EBD5C2;
      border-radius: 6px;
      transition: all 0.2s ease;
    `;

    // 좌측: 순번 + 회차 배지 + 시 제목
    const leftDiv = document.createElement("div");
    leftDiv.style.cssText = "display: flex; align-items: center; gap: 8px; flex: 1; min-width: 0;";
    leftDiv.innerHTML = `
      <span style="font-size: 0.76rem; font-weight: 700; color: #8B5A2B; background: #FFF4E8; padding: 2px 7px; border-radius: 12px; border: 1px solid #EBD0B5; min-width: 32px; text-align: center;">#${idx + 1}</span>
      <span style="font-size: 0.8rem; color: #665F57; font-weight: 600;">[${item.episode_no}]</span>
      <span style="font-size: 0.92rem; font-weight: 700; color: #2C2520; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${escapeHtml(item.title)}</span>
    `;

    // 중앙: 부/챕터 선택 셀렉트박스
    const midDiv = document.createElement("div");
    midDiv.style.cssText = "display: flex; align-items: center; gap: 6px;";
    
    const select = document.createElement("select");
    select.className = "form-input";
    select.style.cssText = "padding: 4px 8px; font-size: 0.82rem; height: 32px; width: 185px; color: #643E19; font-weight: 600; background: #FFFDF9; border-color: #EBD5C2;";
    
    const defOpt = document.createElement("option");
    defOpt.value = "";
    defOpt.textContent = "— 부(주제) 미지정 —";
    select.appendChild(defOpt);

    tocChapters.forEach(chap => {
      const opt = document.createElement("option");
      opt.value = chap;
      opt.textContent = `📁 ${chap}`;
      if (item.chapter === chap) {
        opt.selected = true;
      }
      select.appendChild(opt);
    });

    select.onchange = (e) => {
      tocEditItems[idx].chapter = e.target.value;
    };
    midDiv.appendChild(select);

    // 우측: 순서 이동 버튼 (위/아래)
    const rightDiv = document.createElement("div");
    rightDiv.style.cssText = "display: flex; gap: 4px;";

    const btnUp = document.createElement("button");
    btnUp.type = "button";
    btnUp.className = "btn-copy";
    btnUp.style.cssText = "padding: 3px 8px; font-size: 0.78rem;";
    btnUp.textContent = "▲ 위로";
    btnUp.disabled = (idx === 0);
    btnUp.title = "[위로 이동] 이 작품을 한 칸 위로 순서를 올립니다.";
    btnUp.onclick = () => moveTocItem(idx, -1);

    const btnDown = document.createElement("button");
    btnDown.type = "button";
    btnDown.className = "btn-copy";
    btnDown.style.cssText = "padding: 3px 8px; font-size: 0.78rem;";
    btnDown.textContent = "▼ 아래로";
    btnDown.disabled = (idx === tocEditItems.length - 1);
    btnDown.title = "[아래로 이동] 이 작품을 한 칸 아래로 순서를 내립니다.";
    btnDown.onclick = () => moveTocItem(idx, 1);

    rightDiv.appendChild(btnUp);
    rightDiv.appendChild(btnDown);

    card.appendChild(leftDiv);
    card.appendChild(midDiv);
    card.appendChild(rightDiv);
    container.appendChild(card);
  });
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// 순서 이동 (스왑)
function moveTocItem(index, delta) {
  const targetIndex = index + delta;
  if (targetIndex < 0 || targetIndex >= tocEditItems.length) return;

  const temp = tocEditItems[index];
  tocEditItems[index] = tocEditItems[targetIndex];
  tocEditItems[targetIndex] = temp;

  renderTocEditorList();
}

// 새 부(챕터) 추가
function addNewTocChapter() {
  const name = prompt("새로운 부/챕터 이름을 입력해주세요.\n(예: 제6부: 달빛 머문 뜨락 또는 특별부: 못다 한 이야기)");
  if (name && name.trim()) {
    const trimmed = name.trim();
    if (!tocChapters.includes(trimmed)) {
      tocChapters.push(trimmed);
      renderTocEditorList();
      alert(`📁 새로운 부 「${trimmed}」이(가) 목록에 추가되었습니다.\n각 시의 소속 부 드롭다운에서 선택할 수 있습니다.`);
    } else {
      alert("이미 동일한 부/챕터가 존재합니다.");
    }
  }
}

// 5부작 연작 프리셋 원클릭 적용
function applyDefaultChaptersPreset() {
  const default5 = [
    "제1부: 흙과 솜꽃",
    "제2부: 밤을 잣는 손",
    "제3부: 바람과 불의 길",
    "제4부: 덜커덩, 세월을 짜다",
    "제5부: 살을 덮는 온기"
  ];

  default5.forEach(c => {
    if (!tocChapters.includes(c)) tocChapters.push(c);
  });

  const total = tocEditItems.length;
  if (total === 0) return;

  const ok = confirm(
    "🌸 「목화와 어머니」 5부작 연작 체계 프리셋을 불러옵니다.\n\n" +
    "현재 등록된 시들(총 " + total + "편)을 5개 부로 순서에 맞추어 균등하게 자동 배분하시겠습니까?\n\n" +
    "- [확인]: 5개 부로 자동 분배\n" +
    "- [취소]: 부/챕터 목록만 추가하고 개별 수동 선택"
  );

  if (ok) {
    const perChapter = Math.ceil(total / 5);
    tocEditItems.forEach((item, idx) => {
      const chapIdx = Math.min(Math.floor(idx / perChapter), 4);
      item.chapter = default5[chapIdx];
    });
  }

  renderTocEditorList();
}

// 목차 및 순서 백엔드 최종 저장
async function saveTocAndOrder() {
  if (tocEditItems.length === 0) return;

  const btn = document.getElementById("btnSaveTocOrder");
  const origHtml = btn ? btn.innerHTML : "";
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = "<span>⏳ 목차와 순서 정리 중...</span>";
  }

  const chkRenumber = document.getElementById("chkAutoRenumberToc");
  const autoRenumber = chkRenumber ? chkRenumber.checked : true;

  try {
    const res = await fetch("/api/reorder_works", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        items: tocEditItems.map(it => ({
          episode_no: it.episode_no,
          chapter: it.chapter || ""
        })),
        auto_renumber: autoRenumber
      })
    });

    const data = await res.json();
    if (res.ok && data.success) {
      closeTocEditorModal();
      alert(`🎉 ${data.message}\n\n가상 북 뷰어와 출판 원고에 새로운 목차와 순서가 반영되었습니다.`);
      currentEditingEpisode = null;
      await loadProjects();
      await loadStatus();
    } else {
      alert("목차 저장 실패: " + (data.detail || data.error || "오류가 발생했습니다."));
    }
  } catch (err) {
    alert("목차 저장 중 네트워크 오류 발생: " + err);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = origHtml;
    }
  }
}


// ============================================================
// 15. 시인의 집필실: 퇴고 판본(Revision) 이력 & 나란히 비교(Diff)
// ============================================================
let currentWorkRevisions = [];
let selectedRevision = null;

async function openRevisionsModal() {
  const epSelect = document.getElementById("selectWorkToEdit");
  let epNo = epSelect ? epSelect.value : "";
  if (!epNo) {
    const epInput = document.getElementById("inputEpisode");
    epNo = epInput ? epInput.value : "제01화";
  }

  const modal = document.getElementById("revisionsModal");
  if (modal) modal.style.display = "flex";

  const listContainer = document.getElementById("revsListContainer");
  const diffContainer = document.getElementById("revsDiffContentContainer");
  const countBadge = document.getElementById("revsCountBadge");
  const btnRestore = document.getElementById("btnRestoreRevision");
  if (btnRestore) btnRestore.disabled = true;

  if (listContainer) listContainer.innerHTML = "<div style='color: var(--text-muted); padding: 10px; font-size: 0.8rem;'>판본 목록을 불러오는 중...</div>";
  if (diffContainer) diffContainer.innerHTML = "<div style='color: var(--text-muted); text-align: center; padding: 40px;'>좌측에서 비교할 판본을 선택해 주세요.</div>";

  try {
    const res = await fetch(`/api/revisions/${encodeURIComponent(epNo)}`);
    const data = await res.json();
    if (res.ok && data.success) {
      currentWorkRevisions = data.revisions || [];
      if (countBadge) countBadge.textContent = `${currentWorkRevisions.length}개`;
      renderRevisionsList();

      if (currentWorkRevisions.length > 0) {
        selectRevisionItem(currentWorkRevisions.length - 1);
      } else {
        if (listContainer) listContainer.innerHTML = "<div style='color: var(--text-muted); padding: 14px 6px; font-size: 0.82rem;'>아직 저장된 판본이 없습니다.<br>원고를 저장하면 자동으로 초고가 보관됩니다.</div>";
        if (diffContainer) diffContainer.innerHTML = "<div style='color: var(--text-muted); text-align: center; padding: 40px;'>저장된 이전 판본이 없습니다.</div>";
      }
    }
  } catch (err) {
    if (listContainer) listContainer.innerHTML = `<div style='color: #c84b31; padding: 10px; font-size: 0.8rem;'>오류: ${err.message}</div>`;
  }
}

function closeRevisionsModal() {
  const modal = document.getElementById("revisionsModal");
  if (modal) modal.style.display = "none";
}

function renderRevisionsList() {
  const listContainer = document.getElementById("revsListContainer");
  if (!listContainer) return;
  listContainer.innerHTML = "";

  currentWorkRevisions.slice().reverse().forEach((rev, idx) => {
    const realIndex = currentWorkRevisions.length - 1 - idx;
    const isSelected = selectedRevision && selectedRevision.rev_id === rev.rev_id;

    const item = document.createElement("div");
    item.style.padding = "8px 10px";
    item.style.borderRadius = "6px";
    item.style.border = isSelected ? "1px solid #643e19" : "1px solid var(--border-subtle)";
    item.style.background = isSelected ? "#FDF5ED" : "#FFFFFF";
    item.style.cursor = "pointer";
    item.style.transition = "all 0.15s ease";

    item.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2px;">
        <span style="font-weight: 700; font-size: 0.85rem; color: #2C2520;">${rev.version_name}</span>
        <span style="font-size: 0.72rem; color: #8C827A;">${rev.line_count || 0}행</span>
      </div>
      <div style="font-size: 0.74rem; color: var(--text-muted); margin-bottom: 2px;">${rev.title || '무제'}</div>
      <div style="font-size: 0.68rem; color: #A69D95;">${rev.timestamp || ''}</div>
    `;

    item.onclick = () => selectRevisionItem(realIndex);
    listContainer.appendChild(item);
  });
}

async function selectRevisionItem(index) {
  selectedRevision = currentWorkRevisions[index];
  renderRevisionsList();

  const titleEl = document.getElementById("revSelectedTitle");
  if (titleEl && selectedRevision) {
    titleEl.textContent = `${selectedRevision.version_name} (${selectedRevision.timestamp})`;
  }

  const btnRestore = document.getElementById("btnRestoreRevision");
  if (btnRestore) btnRestore.disabled = !selectedRevision;

  const currentPoem = (document.getElementById("inputFinalPoem")?.value || "").trim();
  const pastPoem = (selectedRevision?.poem_body || "").trim();

  const diffContainer = document.getElementById("revsDiffContentContainer");
  if (diffContainer) diffContainer.innerHTML = "<div style='color: var(--text-muted); text-align: center; padding: 30px;'>판본 차이점을 분석하는 중...</div>";

  try {
    const res = await fetch("/api/compare_revisions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        body_a: pastPoem,
        body_b: currentPoem,
        name_a: selectedRevision ? selectedRevision.version_name : "이전 판본",
        name_b: "현재 편집창 본문"
      })
    });
    const data = await res.json();
    if (res.ok && data.success) {
      renderDiffView(data.diff);
    }
  } catch (err) {
    if (diffContainer) diffContainer.innerHTML = `<div style='color: #c84b31;'>비교 실패: ${err.message}</div>`;
  }
}

function renderDiffView(diffData) {
  const container = document.getElementById("revsDiffContentContainer");
  if (!container) return;

  if (!diffData || !diffData.diff_blocks) {
    container.innerHTML = "<div>비교 데이터가 없습니다.</div>";
    return;
  }

  let html = "<div style='display: flex; flex-direction: column; gap: 4px;'>";

  diffData.diff_blocks.forEach(block => {
    if (block.tag === "equal") {
      block.lines_b.forEach(line => {
        html += `<div style="padding: 2px 6px; color: #4A4036;">${escapeHtml(line) || '&nbsp;'}</div>`;
      });
    } else if (block.tag === "replace") {
      block.lines_a.forEach(line => {
        html += `<div style="padding: 2px 6px; background: #FFF0F0; color: #A83232; text-decoration: line-through; border-left: 3px solid #D9534F;">${escapeHtml(line) || '&nbsp;'} <span style="font-size: 0.72rem; color: #888;">(이전 판본)</span></div>`;
      });
      block.lines_b.forEach(line => {
        html += `<div style="padding: 2px 6px; background: #F0FFF0; color: #2E7D32; font-weight: 500; border-left: 3px solid #5CB85C;">${escapeHtml(line) || '&nbsp;'} <span style="font-size: 0.72rem; color: #2E7D32;">(현재 수정본)</span></div>`;
      });
    } else if (block.tag === "delete") {
      block.lines_a.forEach(line => {
        html += `<div style="padding: 2px 6px; background: #FFF0F0; color: #A83232; text-decoration: line-through; border-left: 3px solid #D9534F;">${escapeHtml(line) || '&nbsp;'} <span style="font-size: 0.72rem; color: #888;">(현재에서 삭제됨)</span></div>`;
      });
    } else if (block.tag === "insert") {
      block.lines_b.forEach(line => {
        html += `<div style="padding: 2px 6px; background: #F0FFF0; color: #2E7D32; font-weight: 500; border-left: 3px solid #5CB85C;">${escapeHtml(line) || '&nbsp;'} <span style="font-size: 0.72rem; color: #2E7D32;">(새로 추가됨)</span></div>`;
      });
    }
  });

  html += "</div>";
  container.innerHTML = html;
}

function restoreSelectedRevision() {
  if (!selectedRevision) return;

  const confirmMsg = `정말로 [${selectedRevision.version_name}] 판본으로 현재 편집창의 제목과 본문을 되돌리시겠습니까?\n\n(현재 편집 중인 내용은 복원 직전 판본으로 자동 스냅샷 보관됩니다.)`;
  if (!confirm(confirmMsg)) return;

  const titleInput = document.getElementById("inputFinalTitle");
  const poemInput = document.getElementById("inputFinalPoem");

  if (titleInput && selectedRevision.title) titleInput.value = selectedRevision.title;
  if (poemInput && selectedRevision.poem_body) poemInput.value = selectedRevision.poem_body;

  closeRevisionsModal();
  alert(`✨ [${selectedRevision.version_name}] 판본으로 성공적으로 복원되었습니다!\n\n편집창에서 내용을 확인하신 후 [시 본문 우선 저장하기]를 눌러주세요.`);
}


// ============================================================
// 16. 시인의 영혼: 내 목소리 육성 낭송 녹음실 (Voice Studio)
// ============================================================
let voiceMediaRecorder = null;
let voiceAudioChunks = [];
let voiceRecordedBlob = null;
let voiceRecTimerInterval = null;
let voiceRecSeconds = 0;

function openVoiceRecModal() {
  const epSelect = document.getElementById("selectWorkToEdit");
  let epNo = epSelect ? epSelect.value : "";
  if (!epNo) {
    const epInput = document.getElementById("inputEpisode");
    epNo = epInput ? epInput.value : "제01화";
  }
  const title = document.getElementById("inputFinalTitle")?.value || "무제";

  const badge = document.getElementById("voiceRecTargetBadge");
  if (badge) badge.textContent = `[${epNo}] ${title}`;

  resetVoiceRecState();

  const modal = document.getElementById("voiceRecModal");
  if (modal) modal.style.display = "flex";
}

function closeVoiceRecModal() {
  if (voiceMediaRecorder && voiceMediaRecorder.state === "recording") {
    voiceMediaRecorder.stop();
  }
  resetVoiceRecState();
  const modal = document.getElementById("voiceRecModal");
  if (modal) modal.style.display = "none";
}

function resetVoiceRecState() {
  if (voiceRecTimerInterval) {
    clearInterval(voiceRecTimerInterval);
    voiceRecTimerInterval = null;
  }
  voiceRecSeconds = 0;
  voiceAudioChunks = [];
  voiceRecordedBlob = null;

  const timerEl = document.getElementById("voiceRecTimerDisplay");
  if (timerEl) timerEl.textContent = "00:00";

  const statusEl = document.getElementById("voiceRecStatusText");
  if (statusEl) statusEl.textContent = "'낭송 녹음 시작' 버튼을 누른 뒤 시를 낭독해 주세요.";

  const indicator = document.getElementById("voiceRecPulsingIndicator");
  if (indicator) {
    indicator.style.background = "#FFFFFF";
    indicator.style.borderColor = "#EBD5C2";
    indicator.style.boxShadow = "none";
  }

  const btnStart = document.getElementById("btnVoiceRecStart");
  const btnStop = document.getElementById("btnVoiceRecStop");
  const btnSave = document.getElementById("btnVoiceRecSave");
  const previewArea = document.getElementById("voiceRecPreviewArea");

  if (btnStart) btnStart.disabled = false;
  if (btnStop) btnStop.disabled = true;
  if (btnSave) btnSave.disabled = true;
  if (previewArea) previewArea.style.display = "none";

  const audioPlayer = document.getElementById("voiceRecAudioPlayer");
  if (audioPlayer) {
    audioPlayer.pause();
    audioPlayer.src = "";
  }
}

async function startVoiceRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    voiceAudioChunks = [];
    voiceRecordedBlob = null;

    voiceMediaRecorder = new MediaRecorder(stream);
    voiceMediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) voiceAudioChunks.push(e.data);
    };

    voiceMediaRecorder.onstop = () => {
      voiceRecordedBlob = new Blob(voiceAudioChunks, { type: "audio/webm" });
      const audioUrl = URL.createObjectURL(voiceRecordedBlob);
      const audioPlayer = document.getElementById("voiceRecAudioPlayer");
      if (audioPlayer) audioPlayer.src = audioUrl;

      const previewArea = document.getElementById("voiceRecPreviewArea");
      if (previewArea) previewArea.style.display = "block";

      const btnSave = document.getElementById("btnVoiceRecSave");
      if (btnSave) btnSave.disabled = false;

      stream.getTracks().forEach(track => track.stop());
    };

    voiceMediaRecorder.start();

    const btnStart = document.getElementById("btnVoiceRecStart");
    const btnStop = document.getElementById("btnVoiceRecStop");
    if (btnStart) btnStart.disabled = true;
    if (btnStop) btnStop.disabled = false;

    const statusEl = document.getElementById("voiceRecStatusText");
    if (statusEl) statusEl.textContent = "🔴 녹음 중... 시인의 따뜻한 육성으로 시를 낭독해 주세요.";

    const indicator = document.getElementById("voiceRecPulsingIndicator");
    if (indicator) {
      indicator.style.background = "#FFF0EE";
      indicator.style.borderColor = "#C84B31";
      indicator.style.boxShadow = "0 0 16px rgba(200, 75, 49, 0.4)";
    }

    voiceRecSeconds = 0;
    voiceRecTimerInterval = setInterval(() => {
      voiceRecSeconds++;
      const mins = String(Math.floor(voiceRecSeconds / 60)).padStart(2, '0');
      const secs = String(voiceRecSeconds % 60).padStart(2, '0');
      const timerEl = document.getElementById("voiceRecTimerDisplay");
      if (timerEl) timerEl.textContent = `${mins}:${secs}`;
    }, 1000);

  } catch (err) {
    alert("마이크 접근 권한이 필요합니다: " + err.message);
  }
}

function stopVoiceRecording() {
  if (voiceMediaRecorder && voiceMediaRecorder.state === "recording") {
    voiceMediaRecorder.stop();
  }
  if (voiceRecTimerInterval) {
    clearInterval(voiceRecTimerInterval);
    voiceRecTimerInterval = null;
  }

  const btnStart = document.getElementById("btnVoiceRecStart");
  const btnStop = document.getElementById("btnVoiceRecStop");
  if (btnStart) btnStart.disabled = false;
  if (btnStop) btnStop.disabled = true;

  const statusEl = document.getElementById("voiceRecStatusText");
  if (statusEl) statusEl.textContent = "✓ 낭송 녹음이 완료되었습니다. 아래에서 들어보실 수 있습니다.";

  const indicator = document.getElementById("voiceRecPulsingIndicator");
  if (indicator) {
    indicator.style.background = "#EEF4EB";
    indicator.style.borderColor = "#436940";
    indicator.style.boxShadow = "none";
  }
}

async function saveVoiceRecordingToWork() {
  if (!voiceRecordedBlob) {
    alert("녹음된 음원 데이터가 없습니다.");
    return;
  }

  const epSelect = document.getElementById("selectWorkToEdit");
  let epNo = epSelect ? epSelect.value : "";
  if (!epNo) {
    const epInput = document.getElementById("inputEpisode");
    epNo = epInput ? epInput.value : "제01화";
  }
  const title = document.getElementById("inputFinalTitle")?.value || "무제";

  const btnSave = document.getElementById("btnVoiceRecSave");
  const origText = btnSave ? btnSave.innerHTML : "";
  if (btnSave) {
    btnSave.disabled = true;
    btnSave.innerHTML = "<span>⏳ 시집에 육성 보관 중...</span>";
  }

  const formData = new FormData();
  formData.append("episode_no", epNo);
  formData.append("title", title);
  formData.append("audio_file", voiceRecordedBlob, `${epNo}_낭송.webm`);

  try {
    const res = await fetch("/api/save_voice_recording", {
      method: "POST",
      body: formData
    });
    const data = await res.json();
    if (res.ok && data.success) {
      alert(`🎉 ${data.message}\n\n가상 북 뷰어와 스튜디오에 시인의 육성이 공식 낭송 음원으로 등록되었습니다.`);
      closeVoiceRecModal();

      currentReciteFile = data.audio_file;
      currentAudioFile = currentMusicFile || currentReciteFile;

      const recitePreviewArea = document.getElementById("studioRecitePreviewArea");
      const reciteFilenameEl = document.getElementById("studioPreviewReciteFilename");
      const recitePlayer = document.getElementById("studioRecitePlayer");

      if (reciteFilenameEl) reciteFilenameEl.textContent = data.filename || data.audio_file.split("/").pop();
      if (recitePlayer) {
        const proj = (currentStatus && currentStatus.project) ? currentStatus.project : null;
        const safeName = (proj && proj.name) ? proj.name.replace(/\s+/g, '_') : "노을빛_기억";
        recitePlayer.src = `/projects/${safeName}/${data.audio_file.replace(/^\.?\//, '')}`;
        recitePlayer.load();
      }
      if (recitePreviewArea) recitePreviewArea.style.display = "block";

      await loadStatus();
    } else {
      alert("육성 저장 실패: " + (data.detail || data.error || "오류가 발생했습니다."));
    }
  } catch (err) {
    alert("육성 업로드 네트워크 오류: " + err);
  } finally {
    if (btnSave) {
      btnSave.disabled = false;
      btnSave.innerHTML = origText;
    }
  }
}


// (17번 섹션의 중복 정의 함수는 19번 섹션 구현으로 통합되어 제거됨)


// ============================================================
// 18. 시인의 집필실: 시어(詩語) 감각 사전 & 방언/토속어
// ============================================================
let thesaurusSelectedWordRange = null;

async function openThesaurusModal() {
  const textarea = document.getElementById("inputFinalPoem");
  let queryWord = "";

  if (textarea && textarea.selectionStart !== textarea.selectionEnd) {
    queryWord = textarea.value.substring(textarea.selectionStart, textarea.selectionEnd).trim();
    thesaurusSelectedWordRange = {
      start: textarea.selectionStart,
      end: textarea.selectionEnd
    };
  } else {
    thesaurusSelectedWordRange = null;
  }

  const modal = document.getElementById("thesaurusModal");
  if (modal) modal.style.display = "flex";

  const searchInput = document.getElementById("thesaurusSearchInput");
  if (searchInput) {
    searchInput.value = queryWord || "어머니";
  }

  await loadThesaurusThemes();
  await searchThesaurusWord(queryWord || "어머니");
}

function closeThesaurusModal() {
  const modal = document.getElementById("thesaurusModal");
  if (modal) modal.style.display = "none";
}

async function loadThesaurusThemes() {
  const container = document.getElementById("thesaurusTagsContainer");
  if (!container) return;

  try {
    const res = await fetch("/api/thesaurus/all");
    const data = await res.json();
    if (res.ok && data.success) {
      container.innerHTML = "";
      data.categories.forEach(item => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "btn-copy";
        btn.style.padding = "4px 10px";
        btn.style.fontSize = "0.78rem";
        btn.style.color = "#4A3B80";
        btn.style.borderColor = "#DCD6F7";
        btn.style.background = "#F9F8FF";
        btn.innerHTML = `<strong>#${item.key}</strong> <span style="color: #8C827A; font-size: 0.72rem;">(${item.category_preview})</span>`;
        btn.onclick = () => {
          const searchInput = document.getElementById("thesaurusSearchInput");
          if (searchInput) searchInput.value = item.key;
          searchThesaurusWord(item.key);
        };
        container.appendChild(btn);
      });
    }
  } catch (err) {
    console.error("Thesaurus themes load error:", err);
  }
}

async function searchThesaurusWord(customQuery = null) {
  const searchInput = document.getElementById("thesaurusSearchInput");
  const word = (customQuery !== null ? customQuery : (searchInput ? searchInput.value : "")).trim();
  const resultArea = document.getElementById("thesaurusResultArea");
  if (!resultArea) return;

  if (!word) {
    resultArea.innerHTML = "<div style='color: var(--text-muted); padding: 20px; text-align: center;'>검색할 시어를 입력해 주세요.</div>";
    return;
  }

  resultArea.innerHTML = "<div style='color: var(--text-muted); padding: 20px; text-align: center;'>시어의 결을 탐색하는 중...</div>";

  try {
    const res = await fetch(`/api/thesaurus/lookup?word=${encodeURIComponent(word)}`);
    const data = await res.json();

    if (res.ok && data.success && data.found) {
      renderThesaurusResult(data.matched_key, data.data);
    } else {
      resultArea.innerHTML = `
        <div style="background: #FFF9F5; border: 1px dashed #EBD0B5; border-radius: 8px; padding: 20px; text-align: center;">
          <div style="font-weight: 700; color: #643E19; margin-bottom: 6px;">'${escapeHtml(word)}'에 대한 직관 사전 결과가 없습니다.</div>
          <p style="font-size: 0.82rem; color: var(--text-muted); margin-bottom: 12px;">아래의 정통 서정 시어 테마(#어머니, #목화, #비, #바람, #새벽, #그리움 등)를 클릭해 보세요.</p>
        </div>
      `;
    }
  } catch (err) {
    resultArea.innerHTML = `<div style='color: #c84b31;'>검색 오류: ${err.message}</div>`;
  }
}

function renderThesaurusResult(key, dbItem) {
  const resultArea = document.getElementById("thesaurusResultArea");
  if (!resultArea || !dbItem) return;

  let html = `
    <div style="background: #FDFBFF; border: 1px solid #E8E2F7; border-radius: 8px; padding: 14px 16px;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; border-bottom: 1px solid #EFEAFD; padding-bottom: 8px;">
        <span style="font-size: 1.05rem; font-weight: 700; color: #4A3B80; font-family: var(--font-serif);">
          『${escapeHtml(key)}』의 정서적 온도와 시어 팔레트
        </span>
        <span style="font-size: 0.74rem; color: #7B719B;">클릭 시 본문에 즉시 적용</span>
      </div>
      <div style="display: flex; flex-direction: column; gap: 12px;">
  `;

  for (const [catName, words] of Object.entries(dbItem.categories || {})) {
    html += `
      <div>
        <div style="font-size: 0.82rem; font-weight: 700; color: #5B4E8C; margin-bottom: 6px; display: flex; align-items: center; gap: 4px;">
          <span>🔹</span> <span>${escapeHtml(catName)}</span>
        </div>
        <div style="display: flex; flex-wrap: wrap; gap: 6px;">
    `;

    words.forEach(w => {
      const cleanWord = w.split('(')[0].trim();
      html += `
        <button type="button" class="btn-copy" onclick="applyThesaurusWord('${escapeHtml(cleanWord)}')" style="padding: 5px 12px; font-size: 0.84rem; background: #FFFFFF; border-color: #D6CEF0; color: #2C2520; transition: all 0.15s;" title="[클릭] 이 시어로 본문 교체하기">
          <strong>${escapeHtml(cleanWord)}</strong>
          ${w.includes('(') ? `<span style="font-size: 0.7rem; color: #8C827A;">(${escapeHtml(w.split('(')[1])}</span>` : ''}
        </button>
      `;
    });

    html += `
        </div>
      </div>
    `;
  }

  html += `
      </div>
    </div>
  `;

  resultArea.innerHTML = html;
}

function applyThesaurusWord(newWord) {
  const textarea = document.getElementById("inputFinalPoem");
  if (!textarea) return;

  const targetRange = thesaurusSelectedWordRange || activePaletteRange;
  if (targetRange && targetRange.start !== targetRange.end) {
    const value = textarea.value;
    textarea.value = value.substring(0, targetRange.start) + newWord + value.substring(targetRange.end);
    textarea.selectionStart = targetRange.start;
    textarea.selectionEnd = targetRange.start + newWord.length;
  } else {
    const pos = textarea.selectionStart || textarea.value.length;
    textarea.value = textarea.value.substring(0, pos) + " " + newWord + textarea.value.substring(pos);
    textarea.selectionStart = textarea.selectionEnd = pos + newWord.length + 1;
  }

  closeThesaurusModal();
  closePoeticPalette();
  textarea.focus();
  textarea.dispatchEvent(new Event("input", { bubbles: true }));

  try {
    navigator.clipboard.writeText(newWord);
  } catch (_) {}

  showCustomFloatingAlert(`✨ 시어 『${newWord}』가 본문에 아름답게 적용되었습니다!`);
}

// ============================================================
// 19. 시인의 집필실: [기둥 3] 공간의 시학 (행간·들여쓰기 타이포그래피 바)
// ============================================================

// 19-1. 들여쓰기 (선택된 행들 또는 현재 행의 시작에 공백 n칸 삽입)
function formatPoemIndent(spaces = 2) {
  const textarea = document.getElementById("inputFinalPoem");
  if (!textarea) return;

  const indentStr = " ".repeat(spaces);
  const start = textarea.selectionStart;
  const end = textarea.selectionEnd;
  const val = textarea.value;

  const lineStart = val.lastIndexOf("\n", start - 1) + 1;
  let lineEnd = val.indexOf("\n", end);
  if (lineEnd === -1) lineEnd = val.length;

  const targetText = val.substring(lineStart, lineEnd);
  const lines = targetText.split("\n");
  const indentedLines = lines.map(line => indentStr + line);
  const newText = indentedLines.join("\n");

  textarea.value = val.substring(0, lineStart) + newText + val.substring(lineEnd);
  
  textarea.selectionStart = start + spaces;
  textarea.selectionEnd = end + (spaces * lines.length);
  textarea.focus();
  textarea.dispatchEvent(new Event("input", { bubbles: true }));
}

// 19-2. 내어쓰기 (선택된 행들 또는 현재 행의 앞 공백 최대 n칸 삭제)
function formatPoemOutdent(spaces = 2) {
  const textarea = document.getElementById("inputFinalPoem");
  if (!textarea) return;

  const start = textarea.selectionStart;
  const end = textarea.selectionEnd;
  const val = textarea.value;

  const lineStart = val.lastIndexOf("\n", start - 1) + 1;
  let lineEnd = val.indexOf("\n", end);
  if (lineEnd === -1) lineEnd = val.length;

  const targetText = val.substring(lineStart, lineEnd);
  const lines = targetText.split("\n");
  let totalRemoved = 0;
  let firstLineRemoved = 0;

  const outdentedLines = lines.map((line, idx) => {
    let removed = 0;
    while (removed < spaces && line.startsWith(" ")) {
      line = line.substring(1);
      removed++;
    }
    if (idx === 0) firstLineRemoved = removed;
    totalRemoved += removed;
    return line;
  });

  const newText = outdentedLines.join("\n");
  textarea.value = val.substring(0, lineStart) + newText + val.substring(lineEnd);

  textarea.selectionStart = Math.max(lineStart, start - firstLineRemoved);
  textarea.selectionEnd = Math.max(lineStart, end - totalRemoved);
  textarea.focus();
  textarea.dispatchEvent(new Event("input", { bubbles: true }));
}

// 19-3. 깊은 여백 (연과 연 사이 깊은 침묵: 빈 줄 2칸 삽입)
function insertPoemDeepSpace() {
  const textarea = document.getElementById("inputFinalPoem");
  if (!textarea) return;

  const start = textarea.selectionStart;
  const end = textarea.selectionEnd;
  const val = textarea.value;

  const deepSpace = "\n\n";
  textarea.value = val.substring(0, start) + deepSpace + val.substring(end);
  textarea.selectionStart = textarea.selectionEnd = start + deepSpace.length;
  textarea.focus();
  textarea.dispatchEvent(new Event("input", { bubbles: true }));
}

// 19-4. 오른쪽 치우침 (>> 표식 토글)
function formatPoemAlignRight() {
  const textarea = document.getElementById("inputFinalPoem");
  if (!textarea) return;

  const start = textarea.selectionStart;
  const end = textarea.selectionEnd;
  const val = textarea.value;

  const lineStart = val.lastIndexOf("\n", start - 1) + 1;
  let lineEnd = val.indexOf("\n", end);
  if (lineEnd === -1) lineEnd = val.length;

  const targetText = val.substring(lineStart, lineEnd);
  const lines = targetText.split("\n");

  const toggledLines = lines.map(line => {
    const trimmed = line.trim();
    if (trimmed.startsWith(">>") || trimmed.startsWith("》》")) {
      return line.replace(/^(\s*)(>>\s*|》》\s*)/, '$1');
    } else {
      return ">> " + line.trim();
    }
  });

  const newText = toggledLines.join("\n");
  textarea.value = val.substring(0, lineStart) + newText + val.substring(lineEnd);
  textarea.selectionStart = lineStart;
  textarea.selectionEnd = lineStart + newText.length;
  textarea.focus();
  textarea.dispatchEvent(new Event("input", { bubbles: true }));
}

// 19-5. 에디터 Tab / Shift+Tab 단축키 등록
function setupPoemEditorKeybindings() {
  const textarea = document.getElementById("inputFinalPoem");
  if (!textarea) return;

  textarea.addEventListener("keydown", function(e) {
    if (e.key === "Tab") {
      e.preventDefault();
      if (e.shiftKey) {
        formatPoemOutdent(2);
      } else {
        formatPoemIndent(2);
      }
    }
  });
}

// ============================================================
// 20. 시인의 집필실: [기둥 1] 인라인 미니 플로팅 시어 팔레트
// ============================================================
let activePaletteWord = "";
let activePaletteRange = null;

function setupPoeticFloatingPalette() {
  const textarea = document.getElementById("inputFinalPoem");
  if (!textarea) return;

  const handleSelection = () => {
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    if (start === end) return;

    const selectedText = textarea.value.substring(start, end).trim();
    // 2자 이상 15자 이하의 단어 선택 시 미니 플로팅 팔레트 트리거
    if (selectedText.length >= 2 && selectedText.length <= 15) {
      activePaletteWord = selectedText;
      activePaletteRange = { start, end };
      thesaurusSelectedWordRange = { start, end };
      openPoeticFloatingPalette(selectedText);
    }
  };

  textarea.addEventListener("mouseup", () => {
    setTimeout(handleSelection, 20);
  });

  textarea.addEventListener("keyup", (e) => {
    if (e.shiftKey && ["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(e.key)) {
      handleSelection();
    }
  });

  // ESC 누르면 닫기
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      closePoeticPalette();
    }
  });

  // 팔레트 바깥 클릭 시 닫기
  document.addEventListener("mousedown", (e) => {
    const palette = document.getElementById("poeticFloatingPalette");
    if (!palette || palette.style.display === "none") return;
    if (!palette.contains(e.target) && e.target !== textarea) {
      closePoeticPalette();
    }
  });
}

async function openPoeticFloatingPalette(word) {
  const palette = document.getElementById("poeticFloatingPalette");
  const textarea = document.getElementById("inputFinalPoem");
  if (!palette || !textarea) return;

  const titleElem = document.getElementById("floatingWordTitle");
  if (titleElem) titleElem.textContent = `『${escapeHtml(word)}』의 시어 결`;

  const chipsContainer = document.getElementById("floatingChipsContainer");
  if (chipsContainer) {
    chipsContainer.innerHTML = '<div class="palette-loading" style="font-size: 0.8rem; color: #8C827A; padding: 6px;">시어의 결을 벼리는 중...</div>';
  }

  // 팔레트 위치 지정 (textarea 상단 또는 커서 주변 안전 위치)
  const rect = textarea.getBoundingClientRect();
  palette.style.display = "block";
  palette.style.position = "absolute";

  const topPos = window.scrollY + rect.top + 36;
  const leftPos = Math.min(window.scrollX + rect.left + 24, window.innerWidth - 340);
  palette.style.top = `${topPos}px`;
  palette.style.left = `${Math.max(10, leftPos)}px`;

  // 1차: 사전 검색
  try {
    const res = await fetch(`/api/thesaurus/lookup?word=${encodeURIComponent(word)}`);
    const data = await res.json();

    if (res.ok && data.success && data.found && data.data) {
      renderPaletteChipsFromDb(data.data);
    } else {
      // 사전에 없을 때 실시간 AI 감각 추천 자동 호출
      await requestAiPoeticPalette(word);
    }
  } catch (err) {
    if (chipsContainer) {
      chipsContainer.innerHTML = `<div style="font-size: 0.78rem; color: #8C827A; padding: 4px;">사전 대기 중. <a href="#" onclick="requestAiPoeticPalette(); return false;" style="color: #4A3B80; font-weight: 700;">[AI 추천받기]</a></div>`;
    }
  }
}

function renderPaletteChipsFromDb(dbItem) {
  const chipsContainer = document.getElementById("floatingChipsContainer");
  if (!chipsContainer || !dbItem) return;

  chipsContainer.innerHTML = "";
  const categories = dbItem.categories || {};
  let count = 0;

  for (const [catName, words] of Object.entries(categories)) {
    for (const w of words) {
      if (count >= 8) break;
      const cleanWord = w.split("(")[0].trim();
      const desc = w.includes("(") ? w.split("(")[1].replace(")", "") : catName;

      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "poetic-chip-btn";
      btn.title = `[클릭] '${cleanWord}'(으)로 본문 교체하기`;
      btn.innerHTML = `<strong>${escapeHtml(cleanWord)}</strong> <span class="poetic-chip-desc">(${escapeHtml(desc)})</span>`;
      btn.onclick = () => replaceSelectedWord(cleanWord);
      chipsContainer.appendChild(btn);
      count++;
    }
    if (count >= 8) break;
  }
}

async function requestAiPoeticPalette(customWord = null) {
  const word = customWord || activePaletteWord;
  if (!word) return;

  const chipsContainer = document.getElementById("floatingChipsContainer");
  if (chipsContainer) {
    chipsContainer.innerHTML = '<div class="palette-loading" style="font-size: 0.8rem; color: #5B4E8C; padding: 6px;">💫 AI가 서정적 시어의 결을 빚는 중...</div>';
  }

  const textarea = document.getElementById("inputFinalPoem");
  const poemContext = textarea ? textarea.value.substring(0, 300) : "";

  try {
    const res = await fetch(`/api/thesaurus/suggest?word=${encodeURIComponent(word)}&context=${encodeURIComponent(poemContext)}`);
    const data = await res.json();

    if (res.ok && data.success && data.suggestions && data.suggestions.length > 0) {
      chipsContainer.innerHTML = "";
      data.suggestions.forEach(item => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "poetic-chip-btn";
        btn.title = `[클릭] '${item.word}'(으)로 본문 교체하기`;
        btn.innerHTML = `<strong>${escapeHtml(item.word)}</strong> <span class="poetic-chip-desc">(${escapeHtml(item.desc || item.category)})</span>`;
        btn.onclick = () => replaceSelectedWord(item.word);
        chipsContainer.appendChild(btn);
      });
    } else {
      if (chipsContainer) {
        chipsContainer.innerHTML = '<div style="font-size: 0.78rem; color: #8C827A; padding: 6px;">추천된 시어가 없습니다. 감각 사전을 열어보세요.</div>';
      }
    }
  } catch (err) {
    if (chipsContainer) {
      chipsContainer.innerHTML = `<div style="font-size: 0.78rem; color: #C84B31; padding: 6px;">추천 오류: ${err.message}</div>`;
    }
  }
}

function replaceSelectedWord(newWord) {
  const textarea = document.getElementById("inputFinalPoem");
  if (!textarea) return;

  const targetRange = activePaletteRange || thesaurusSelectedWordRange;
  if (targetRange && targetRange.start !== targetRange.end) {
    const val = textarea.value;
    textarea.value = val.substring(0, targetRange.start) + newWord + val.substring(targetRange.end);
    textarea.selectionStart = targetRange.start;
    textarea.selectionEnd = targetRange.start + newWord.length;
  } else {
    const pos = textarea.selectionStart || textarea.value.length;
    const val = textarea.value;
    textarea.value = val.substring(0, pos) + newWord + val.substring(pos);
    textarea.selectionStart = textarea.selectionEnd = pos + newWord.length;
  }

  textarea.focus();
  textarea.dispatchEvent(new Event("input", { bubbles: true }));
  closePoeticPalette();

  showCustomFloatingAlert(`✨ 시어 『${newWord}』가 본문에 아름답게 교체되었습니다!`);
}

function closePoeticPalette() {
  const palette = document.getElementById("poeticFloatingPalette");
  if (palette) palette.style.display = "none";
}

function expandToThesaurusModal() {
  closePoeticPalette();
  openThesaurusModal();
}

function showCustomFloatingAlert(msg) {
  const alertBox = document.createElement("div");
  alertBox.style.position = "fixed";
  alertBox.style.bottom = "24px";
  alertBox.style.right = "24px";
  alertBox.style.zIndex = "9999";
  alertBox.style.background = "#4A3B80";
  alertBox.style.color = "#FFFFFF";
  alertBox.style.padding = "10px 18px";
  alertBox.style.borderRadius = "8px";
  alertBox.style.boxShadow = "0 6px 18px rgba(74, 59, 128, 0.35)";
  alertBox.style.fontSize = "0.88rem";
  alertBox.style.fontFamily = "var(--font-serif)";
  alertBox.textContent = msg;
  document.body.appendChild(alertBox);

  setTimeout(() => {
    alertBox.style.opacity = "0";
    alertBox.style.transition = "opacity 0.4s ease";
    setTimeout(() => alertBox.remove(), 400);
  }, 2200);
}

// 초기화 바인딩
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => {
    bindEvents();
    setupPoemEditorKeybindings();
    setupPoeticFloatingPalette();
    setTimeout(alignPoemEditorWithAudioDropzone, 200);
    checkGeminiKeyStatus();
  });
} else {
  bindEvents();
  setupPoemEditorKeybindings();
  setupPoeticFloatingPalette();
  setTimeout(alignPoemEditorWithAudioDropzone, 200);
  checkGeminiKeyStatus();
}

// =========================================================
// 20. 시 본문 입력창 하단 선과 우측 음원 드롭존 하단 선 수평 정렬
// =========================================================
function alignPoemEditorWithAudioDropzone() {
  const poemEditor = document.getElementById("inputFinalPoem");
  if (!poemEditor) return;
  // CSS Flexbox가 전체 세로 공간을 100% 채우도록 인라인 height 제거
  poemEditor.style.removeProperty("height");
}

// =========================================================
// 21. Google Gemini API 키 및 최신 AI 모델 관리 & 상태 확인
// =========================================================
async function checkGeminiKeyStatus() {
  const btn = document.getElementById("btnOpenGeminiKeyModal");
  const statusText = document.getElementById("geminiKeyCurrentStatusText");
  const modelSelect = document.getElementById("selectGeminiModel");
  try {
    const [keyRes, modelRes] = await Promise.all([
      fetch("/api/settings/gemini_key"),
      fetch("/api/settings/gemini_model")
    ]);
    const keyData = await keyRes.json();
    const modelData = await modelRes.json();

    const currentModel = (modelData && modelData.current_model) ? modelData.current_model : "gemini-3.8-flash";

    if (modelSelect) {
      modelSelect.value = currentModel;
      modelSelect.onchange = async () => {
        const chosen = modelSelect.value;
        try {
          const res = await fetch("/api/settings/gemini_model", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ model_name: chosen })
          });
          const d = await res.json();
          if (d.success) {
            showTemporaryToast(`🤖 AI 모델이 [${chosen}]로 변경되었습니다!`);
            await checkGeminiKeyStatus();
          }
        } catch (e) {
          console.error("모델 변경 실패:", e);
        }
      };
    }

    if (keyData.configured) {
      if (btn) {
        btn.innerHTML = `<span style="color:#16A34A; font-weight:700;">🔑 AI 키 연결됨 (${currentModel} 활성)</span>`;
        btn.style.borderColor = "#86EFAC";
        btn.style.background = "#F0FDF4";
        btn.title = `Google Gemini 키가 연동되어 있습니다 (${keyData.masked_key}). 현재 ${currentModel} 모델로 시를 빚습니다.`;
      }
      if (statusText) {
        statusText.innerHTML = `<span style="color:#16A34A; font-weight:700;">✓ 현재 키 연동됨: ${keyData.masked_key} (${currentModel})</span>`;
      }
    } else {
      if (btn) {
        btn.innerHTML = '<span>🔑 무료 AI 키 설정 (100% 무료)</span>';
        btn.style.borderColor = "#B8977E";
        btn.style.background = "#FFFDF9";
        btn.title = "Google AI Studio에서 30초 만에 100% 무료 키를 발급받아 등록하면, 상투적이지 않은 고품격 서정시를 빚어냅니다.";
      }
      if (statusText) {
        statusText.innerHTML = '<span style="color:#DC2626;">✕ 등록된 API 키가 없습니다 (기본 룰베이스 엔진 작동 중)</span>';
      }
    }
    if (btn) {
      btn.onclick = openGeminiKeyModal;
    }
  } catch (err) {
    console.warn("Gemini 키 상태 확인 실패:", err);
  }
}

function openGeminiKeyModal() {
  const modal = document.getElementById("modalGeminiKey");
  if (modal) {
    modal.style.display = "flex";
    const msg = document.getElementById("geminiKeyValidationMsg");
    if (msg) msg.style.display = "none";
    const input = document.getElementById("inputGeminiApiKey");
    if (input) {
      input.value = "";
      input.focus();
    }
    checkGeminiKeyStatus();
  }
}

// 전역 window 객체 노출 (인라인 onclick 안전 보장)
window.openGeminiKeyModal = openGeminiKeyModal;
window.closeGeminiKeyModal = closeGeminiKeyModal;
window.saveGeminiApiKey = saveGeminiApiKey;
window.checkGeminiKeyStatus = checkGeminiKeyStatus;

function closeGeminiKeyModal() {
  const modal = document.getElementById("modalGeminiKey");
  if (modal) modal.style.display = "none";
}

async function saveGeminiApiKey() {
  const input = document.getElementById("inputGeminiApiKey");
  const msg = document.getElementById("geminiKeyValidationMsg");
  const saveBtn = document.getElementById("btnSaveGeminiKey");
  const modelSelect = document.getElementById("selectGeminiModel");
  const apiKey = (input ? input.value : "").trim();
  const selectedModel = modelSelect ? modelSelect.value : "gemini-3.8-flash";

  // 모델 먼저 저장
  if (selectedModel) {
    await fetch("/api/settings/gemini_model", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model_name: selectedModel })
    });
  }

  if (!apiKey) {
    // 키 입력 없이 모델만 바꾼 경우
    showTemporaryToast(`🤖 AI 모델이 [${selectedModel}]로 저장되었습니다!`);
    await checkGeminiKeyStatus();
    closeGeminiKeyModal();
    return;
  }

  if (saveBtn) {
    saveBtn.disabled = true;
    saveBtn.innerHTML = "<span>⏳ 검증 및 저장 중...</span>";
  }

  try {
    const res = await fetch("/api/settings/gemini_key", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ api_key: apiKey })
    });
    const data = await res.json();
    if (data.success) {
      if (msg) {
        msg.style.display = "block";
        msg.style.color = "#16A34A";
        msg.textContent = `✓ Gemini 키 및 [${selectedModel}] 모델이 성공적으로 활성화되었습니다!`;
      }
      showTemporaryToast(`✨ [${selectedModel}] 모델이 활성화되었습니다. 깊이 있는 현대시를 빚어냅니다!`);
      await checkGeminiKeyStatus();
      setTimeout(() => {
        closeGeminiKeyModal();
      }, 1200);
    } else {
      if (msg) {
        msg.style.display = "block";
        msg.style.color = "#DC2626";
        msg.textContent = `⚠️ 오류: ${data.detail || "검증 실패"}`;
      }
    }
  } catch (err) {
    if (msg) {
      msg.style.display = "block";
      msg.style.color = "#DC2626";
      msg.textContent = `⚠️ 통신 실패: ${err.message}`;
    }
  } finally {
    if (saveBtn) {
      saveBtn.disabled = false;
      saveBtn.innerHTML = "<span>💾 저장 및 즉시 활성화</span>";
    }
  }
}

// =========================================================
// 22. AI 심층 인터뷰 (영감 꼬리질문 & 감각 발굴)
// =========================================================
async function onStartDeepInterview() {
  const coreMemory = (document.getElementById("inputCoreMemory")?.value || "").trim();
  const sensoryDetails = (document.getElementById("inputSensoryDetails")?.value || "").trim();
  const spokenWords = (document.getElementById("inputSpokenWords")?.value || "").trim();

  if (!coreMemory && !sensoryDetails && !spokenWords) {
    alert("인터뷰 1, 2, 3번 질문 중 적어도 한 가지를 간단히 적어주셔야 맞춤형 심층 꼬리 질문을 던져드릴 수 있습니다.");
    document.getElementById("inputCoreMemory")?.focus();
    return;
  }

  const btn = document.getElementById("btnStartDeepInterview");
  const panel = document.getElementById("deepInterviewPanel");
  const origBtnHtml = btn ? btn.innerHTML : "";

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = "<span>⏳ 영감 분석 & 꼬리 질문 생성 중...</span>";
  }

  try {
    const res = await fetch("/api/interview/deep_questions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        core_memory: coreMemory,
        sensory_details: sensoryDetails,
        spoken_words: spokenWords
      })
    });
    const data = await res.json();
    if (!res.ok || !data.questions) {
      throw new Error(data.detail || "심층 질문 생성에 실패했습니다.");
    }

    // 1. 공감 요약 박스 업데이트
    const summaryBox = document.getElementById("deepInterviewSummaryBox");
    if (summaryBox) {
      summaryBox.innerHTML = `<strong>🕊️ AI 시인의 마음 읽기:</strong><br>${data.summary || "선생님께서 들려주신 기억의 편린을 소중히 음미하고 있습니다."}`;
    }

    // 2. 꼬리 질문 3개 리스트 렌더링
    const qList = document.getElementById("deepInterviewQuestionsList");
    if (qList) {
      qList.innerHTML = "";
      data.questions.forEach((q, idx) => {
        const item = document.createElement("div");
        item.style.cssText = "background: #FFFFFF; border: 1px solid #EBD0B5; border-radius: 6px; padding: 8px 12px; cursor: pointer; transition: all 0.2s ease; display: flex; align-items: flex-start; gap: 8px;";
        item.onmouseenter = () => { item.style.borderColor = "#8B5A2B"; item.style.background = "#FFF9F2"; };
        item.onmouseleave = () => { item.style.borderColor = "#EBD0B5"; item.style.background = "#FFFFFF"; };
        item.onclick = () => selectDeepQuestion(q);

        item.innerHTML = `
          <span style="background: #8B5A2B; color: #FFF; font-size: 0.72rem; font-weight: 700; border-radius: 50%; width: 18px; height: 18px; display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0; margin-top: 2px;">${idx + 1}</span>
          <div style="flex: 1;">
            <div style="font-size: 0.83rem; color: #3E2723; font-weight: 600; line-height: 1.45;">${q}</div>
            <div style="font-size: 0.72rem; color: #8D6E63; margin-top: 2px;">👉 이 질문을 선택하고 아래에 한 줄로 답하기</div>
          </div>
        `;
        qList.appendChild(item);
      });
    }

    // 3. 패널 열기 및 부드러운 스크롤
    if (panel) {
      panel.style.display = "block";
      panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }

    // 4. 입력창 포커스
    const inputDeep = document.getElementById("inputDeepAnswer");
    if (inputDeep) {
      inputDeep.focus();
    }
  } catch (err) {
    alert("심층 인터뷰 생성 중 오류가 발생했습니다: " + err.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = origBtnHtml;
    }
  }
}

function selectDeepQuestion(qText) {
  const input = document.getElementById("inputDeepAnswer");
  if (input) {
    input.placeholder = `[선택한 질문] "${qText}" → 짧게 한 줄 덧붙여주세요`;
    input.focus();
  }
}

function closeDeepInterviewPanel() {
  const panel = document.getElementById("deepInterviewPanel");
  if (panel) panel.style.display = "none";
}

async function onGenerateDraftsWithDeepAnswer() {
  const inputDeep = document.getElementById("inputDeepAnswer");
  const deepVal = inputDeep ? inputDeep.value.trim() : "";
  if (!deepVal) {
    if (!confirm("심층 질문에 대한 답변이 비어있습니다. 기존 입력 내용만으로 시안을 생성할까요?")) {
      if (inputDeep) inputDeep.focus();
      return;
    }
  }
  await onGenerateDrafts();
}

// =============================================================
// 📖 시집 본문 외 출판 완결 편집실 (Front & Back Matter) 연동
// =============================================================

async function loadBookExtras() {
  try {
    const res = await fetch("/api/book_extras");
    if (!res.ok) return;
    const data = await res.json();
    if (!data.success) return;

    const extras = data.extras || {};

    const prologueInput = document.getElementById("bookPrologueInput");
    if (prologueInput && !prologueInput.value) {
      prologueInput.value = extras.prologue || "";
    }

    const epilogueInput = document.getElementById("bookEpilogueInput");
    if (epilogueInput && !epilogueInput.value) {
      epilogueInput.value = extras.epilogue || "";
    }

    const blurbInput = document.getElementById("bookBlurbInput");
    if (blurbInput && !blurbInput.value) {
      blurbInput.value = extras.back_cover_blurb || "";
    }

    const pubInput = document.getElementById("bookPublisherInput");
    if (pubInput && extras.publisher) {
      pubInput.value = extras.publisher;
    }

    const dateInput = document.getElementById("bookPublishedDateInput");
    if (dateInput && extras.published_date) {
      dateInput.value = extras.published_date;
    }

    const priceInput = document.getElementById("bookPriceInput");
    if (priceInput && extras.price) {
      priceInput.value = extras.price;
    }

    const isbnInput = document.getElementById("bookIsbnInput");
    if (isbnInput && extras.isbn) {
      isbnInput.value = extras.isbn;
    }

    // 앞표지 삽화 목록 채우기
    const coverSelect = document.getElementById("bookCoverImageSelect");
    if (coverSelect && data.available_images) {
      const currentSelected = extras.cover_image || "";
      coverSelect.innerHTML = `<option value="">(삽화 없음 - 타이포그래피 표지)</option>`;
      data.available_images.forEach(img => {
        const isSel = (img === currentSelected || `images/${img}` === currentSelected) ? "selected" : "";
        coverSelect.innerHTML += `<option value="images/${img}" ${isSel}>${img}</option>`;
      });
    }
  } catch (err) {
    console.error("Error loading book extras:", err);
  }
}

async function saveBookExtras() {
  const btn = document.getElementById("btnSaveBookExtras");
  const origText = btn ? btn.innerHTML : "";

  try {
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = `<span>⏳ 저장 중...</span>`;
    }

    const payload = {
      prologue: document.getElementById("bookPrologueInput")?.value || "",
      epilogue: document.getElementById("bookEpilogueInput")?.value || "",
      back_cover_blurb: document.getElementById("bookBlurbInput")?.value || "",
      cover_image: document.getElementById("bookCoverImageSelect")?.value || "",
      publisher: document.getElementById("bookPublisherInput")?.value || "부크크 (Bookk) 자가출판",
      published_date: document.getElementById("bookPublishedDateInput")?.value || "",
      price: document.getElementById("bookPriceInput")?.value || "13,000원",
      isbn: document.getElementById("bookIsbnInput")?.value || ""
    };

    const res = await fetch("/api/book_extras/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.detail || data.message || "저장 실패");
    }

    alert("✨ 시인의 말, 맺음말, 뒷표지 카피, 판권 정보가 시집 출판 메타데이터에 안전하게 저장되었습니다!\n\n이제 [부크크 내지/표지 완제본 PDF]나 [Canva 출판 CSV]를 내려받으시면 완벽히 반영됩니다.");
  } catch (err) {
    alert("출판 구성 요소 저장 중 오류가 발생했습니다: " + err.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = origText;
    }
  }
}

async function generateBookExtra(target, btnId, inputId) {
  const btn = document.getElementById(btnId);
  const input = document.getElementById(inputId);
  const origHtml = btn ? btn.innerHTML : "";

  try {
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = `<span>✨ 감성 집필 중...</span>`;
    }

    const res = await fetch("/api/book_extras/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target })
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.detail || "AI 생성 실패");
    }

    if (input) {
      input.value = data.generated_text;
      input.style.backgroundColor = "#FFFDF0";
      setTimeout(() => {
        input.style.backgroundColor = "#FFFFFF";
      }, 1000);
      input.focus();
    }
  } catch (err) {
    alert("AI 문구 생성 중 오류가 발생했습니다: " + err.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = origHtml;
    }
  }
}

// 이벤트 리스너 등록
document.addEventListener("DOMContentLoaded", () => {
  // 출판 데이터 탭 진입 시 로드
  const tabBtnExport = document.getElementById("tabBtnExport");
  if (tabBtnExport) {
    tabBtnExport.addEventListener("click", () => {
      loadBookExtras();
    });
  }

  // 출판 저장 버튼
  const btnSave = document.getElementById("btnSaveBookExtras");
  if (btnSave) {
    btnSave.addEventListener("click", saveBookExtras);
  }

  // AI 생성 버튼들
  const btnPrologue = document.getElementById("btnGenPrologue");
  if (btnPrologue) {
    btnPrologue.addEventListener("click", () => generateBookExtra("prologue", "btnGenPrologue", "bookPrologueInput"));
  }

  const btnEpilogue = document.getElementById("btnGenEpilogue");
  if (btnEpilogue) {
    btnEpilogue.addEventListener("click", () => generateBookExtra("epilogue", "btnGenEpilogue", "bookEpilogueInput"));
  }

  const btnBlurb = document.getElementById("btnGenBlurb");
  if (btnBlurb) {
    btnBlurb.addEventListener("click", () => generateBookExtra("back_cover_blurb", "btnGenBlurb", "bookBlurbInput"));
  }

  // 초기 1회 로드
  setTimeout(loadBookExtras, 800);
  initAudioMutualExclusion();
  checkInitialTtsStatus();
});

// 🎧 오디오 중복 재생 방지 (낭송, 노래, TTS 상호 배타적 제어)
function initAudioMutualExclusion() {
  const recitePlayer = document.getElementById("studioRecitePlayer");
  const musicPlayer = document.getElementById("studioAudioPlayer");

  if (recitePlayer) {
    recitePlayer.addEventListener("play", () => {
      // 낭송이 시작되면 노래 및 TTS 즉시 중단
      if (musicPlayer && !musicPlayer.paused) {
        musicPlayer.pause();
      }
      if (currentGeminiReciteAudio && !currentGeminiReciteAudio.paused) {
        currentGeminiReciteAudio.pause();
        const btn = document.getElementById("btnSpeakPoem");
        if (btn) btn.innerHTML = "🎧 시 낭송 듣기";
      }
      if (window.speechSynthesis && window.speechSynthesis.speaking) {
        window.speechSynthesis.cancel();
      }
    });
  }

  if (musicPlayer) {
    musicPlayer.addEventListener("play", () => {
      // 노래가 시작되면 낭송 및 TTS 즉시 중단
      if (recitePlayer && !recitePlayer.paused) {
        recitePlayer.pause();
      }
      if (currentGeminiReciteAudio && !currentGeminiReciteAudio.paused) {
        currentGeminiReciteAudio.pause();
        const btn = document.getElementById("btnSpeakPoem");
        if (btn) btn.innerHTML = "🎧 시 낭송 듣기";
      }
      if (window.speechSynthesis && window.speechSynthesis.speaking) {
        window.speechSynthesis.cancel();
      }
    });
  }
}





