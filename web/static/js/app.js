// StoryBook Studio Frontend Application Logic (Multi-Project Edition)
window.name = "StoryBookStudio";

var currentStatus = null;
window.currentStatus = null;
let currentDrafts = null;
var currentWorkIndex = 0;
window.currentWorkIndex = 0;
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
  window._hasUserSelectedWork = false;
  if (typeof currentSelectedBookSectionId !== "undefined") currentSelectedBookSectionId = null;
  document.getElementById("inputCoreMemory").value = "";
  document.getElementById("inputSensoryDetails").value = "";
  document.getElementById("inputSpokenWords").value = "";
  document.getElementById("inputFinalTitle").value = "";
  if (document.getElementById("inputFinalAuthor")) document.getElementById("inputFinalAuthor").value = "";
  document.getElementById("inputFinalPoem").value = "";
  if (typeof syncPoemEditorWithDtpConfig === "function") syncPoemEditorWithDtpConfig(null);
  
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
  document.querySelectorAll('.book-tree-item').forEach(el => el.classList.remove('active'));
}

// 📖 기존 저장된 시 편집창 불러오기 드롭다운 갱신
function updateWorkToEditDropdown() {
  const selBox = document.getElementById("selectWorkToEdit");
  if (!selBox) return;

  selBox.innerHTML = "";

  let works = (currentStatus && currentStatus.works && currentStatus.works.length > 0) ? currentStatus.works : [];
  if (works.length === 0 && window.bookStructureData && Array.isArray(window.bookStructureData.sections)) {
    works = window.bookStructureData.sections
      .filter(s => s.group === 'body_matter' || s.category === 'poem')
      .map(s => ({
        episode_no: s.episode_no,
        title: (s.title || '').replace(/^\[.*?\]\s*/, ''),
        chapter: s.chapter || ""
      }));
  }

  // 옵션 1: 신규 작품 집필
  const optNew = document.createElement("option");
  optNew.value = "new";
  const nextEp = (currentStatus && currentStatus.next_episode) ? currentStatus.next_episode : "신규";
  optNew.textContent = `✨ [새 작품 집필] (다음 ${nextEp} 작성)`;
  selBox.appendChild(optNew);

  // 옵션 2~N: 기존 저장된 회차별 시
  works.forEach(w => {
    if (!w.episode_no) return;
    const opt = document.createElement("option");
    opt.value = w.episode_no;
    const chapTag = w.chapter ? `[${w.chapter}] ` : '';
    opt.textContent = `📖 ${chapTag}[${w.episode_no}] ${w.title || '무제'}`;
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
function loadWorkIntoEditor(episodeNo, options = {}) {
  window._hasUserSelectedWork = true;
  let works = (currentStatus && currentStatus.works) ? currentStatus.works : [];
  let workIdx = works.findIndex(w => w.episode_no === episodeNo);
  let work = workIdx >= 0 ? works[workIdx] : null;

  // fallback: currentStatus.works에 아직 없는 경우 bookStructureData 탐색
  if (!work && window.bookStructureData && Array.isArray(window.bookStructureData.sections)) {
    const sec = window.bookStructureData.sections.find(s => s.episode_no === episodeNo);
    if (sec) {
      work = {
        episode_no: sec.episode_no,
        title: (sec.title || '').replace(/^\[.*?\]\s*/, ''),
        author: sec.author || '',
        poem_body: (sec.data && sec.data.poem_body) || '',
        memory_anchor: (sec.data && sec.data.memory_anchor) || '',
        image_file: (sec.data && sec.data.image_file) || ''
      };
    }
  }
  if (!work) return;

  // 창작실 드롭다운이 아직 비어있다면 즉시 갱신
  const selBox = document.getElementById("selectWorkToEdit");
  if (selBox) {
    if (selBox.options.length <= 1) {
      updateWorkToEditDropdown();
    }
    selBox.value = work.episode_no;
  }

  currentEditingEpisode = work.episode_no;
  if (workIdx >= 0) {
    currentWorkIndex = workIdx;
    window.currentWorkIndex = workIdx;
  }
  // 좌측 '책 전체 구성표' 트리 활성 항목 동기화
  let treeSecId = `poem_${work.episode_no}`;
  if (window.bookStructureData && Array.isArray(window.bookStructureData.sections)) {
    const matchingSec = window.bookStructureData.sections.find(s => s.episode_no === work.episode_no);
    if (matchingSec) treeSecId = matchingSec.id;
  }
  if (typeof window.updateBookTreeActiveItem === 'function') {
    window.updateBookTreeActiveItem(treeSecId);
  }
  // 집필실에서 직접 선택한 경우 조판 편집기(DTP)도 동일 회차로 동기화
  if (!options.fromDtpOrTree && window.dtpEditor && workIdx >= 0) {
    window.dtpEditor.renderSpread(workIdx, 1, false, { skipStudioSync: true });
  }
  if (typeof updateSidebarVideoCard === 'function') {
    const cleanedEp = String(work.episode_no).replace(/[^0-9]/g, '');
    if (cleanedEp) updateSidebarVideoCard(parseInt(cleanedEp, 10));
  }
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
  if (typeof syncPoemEditorWithDtpConfig === "function") syncPoemEditorWithDtpConfig(work);

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

  // selBox is already declared above
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
  if (lyricsInput) {
    lyricsInput.value = work.lyrics || "";
    if (typeof updateStudioLyricsDisplay === 'function') updateStudioLyricsDisplay();
  }

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


document.addEventListener("DOMContentLoaded", () => {
  bindEvents();
  initCustomTooltips();
  initSidebar();
  initTabs();
  loadProjects();
  updateWorkToEditDropdown();
  loadStatus();
  if (typeof refreshBookStructure === 'function') {
    refreshBookStructure();
  }
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

// [글꼴·크기 단일화] 조판 편집기 '글 편집 도구상자' 속성을 집필실 본문창에 100% 동기화
let currentPoemFontSize = (13.0 / 12.0) * 0.95; // 기본 13pt (약 1.03rem)
function syncPoemEditorWithDtpConfig(work) {
  const cfg = (work && work.layout_config) ? work.layout_config : {};
  const selFont = document.getElementById("selectTbFontFamily");
  const selSize = document.getElementById("selectTbFontSize");
  const selAlign = document.getElementById("selectTbTextAlign");

  const fontFam = cfg.font_family || (selFont && selFont.value !== "custom" ? selFont.value : "'BookkMyungjo', '부크크 명조', 'Nanum Myeongjo', serif");
  const pt = parseFloat(cfg.font_size_pt) || (selSize && selSize.value !== "custom" ? parseFloat(selSize.value) : 13) || 13;
  const remSize = (pt / 12.0) * 0.95;
  const lineHeight = parseFloat(cfg.line_height_ratio) || 1.6;
  const textAlign = cfg.text_align || (selAlign ? selAlign.value : "left") || "left";

  currentPoemFontSize = remSize;

  const textarea = document.getElementById("inputFinalPoem");
  if (textarea) {
    textarea.style.setProperty("font-family", fontFam, "important");
    textarea.style.setProperty("font-size", `${remSize.toFixed(2)}rem`, "important");
    textarea.style.setProperty("line-height", `${lineHeight}`, "important");
    textarea.style.setProperty("text-align", textAlign, "important");
  }
  const inputTitle = document.getElementById("inputFinalTitle");
  if (inputTitle) inputTitle.style.setProperty("font-family", fontFam, "important");
  const inputAuthor = document.getElementById("inputFinalAuthor");
  if (inputAuthor) inputAuthor.style.setProperty("font-family", fontFam, "important");
}
window.syncPoemEditorWithDtpConfig = syncPoemEditorWithDtpConfig;

// 시 본문 집필 화면 확대/축소 전용 (A+ / A- : 조판 pt 설정은 변경하지 않고 집필창 화면만 확대/축소)
function adjustPoemFontSize(delta) {
  const textarea = document.getElementById("inputFinalPoem");
  if (!textarea) return;
  currentPoemFontSize = Math.max(0.75, Math.min(2.2, currentPoemFontSize + delta * 0.10));
  textarea.style.setProperty("font-size", `${currentPoemFontSize.toFixed(2)}rem`, "important");
  if (typeof showToast === 'function') {
    showToast(`집필 화면 표시 크기: ${(currentPoemFontSize * 16).toFixed(0)}px (조판 글자크기 설정은 유지됨)`, "info");
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
        } else if (targetId === "panelVideo") {
          if (typeof updateSidebarVideoCard === 'function') {
            updateSidebarVideoCard();
          }
        } else if (targetId === "panelBook") {
          renderBookSpread(currentWorkIndex);
        }
      }

      // 모바일 환경에서는 탭 선택 후 사이드바 자동 닫기
      if (window.innerWidth <= 900) {
        closeSidebarMobile();
      }
    });
  });
}



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
  window._hasUserSelectedWork = false;
  if (typeof currentSelectedBookSectionId !== "undefined") currentSelectedBookSectionId = null;
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
    btn.innerHTML = "<span>⏳ 두 가지 시안을 빚어내는 중... (생성 대기 필요)</span>";
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
  window._hasUserSelectedWork = false;
  if (typeof currentSelectedBookSectionId !== "undefined") currentSelectedBookSectionId = null;
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

// [StoryBook DTP Core v4.0] 양면 펼침면 렌더링은 dtp_editor_core.js에서 전담합니다.
function renderBookSpread(index) {
  if (window.dtpEditor && typeof window.dtpEditor.renderSpread === 'function') {
    return window.dtpEditor.renderSpread(index, window.currentSpreadPart || 1, false);
  }
}

// -------------------------------------------------------------
// 캔바형 통합 삽화 관리 모달 (AI 새 삽화 생성 & 내 파일 업로드 완전 통합)
// -------------------------------------------------------------
async function openSlotImageManager(side) {
  if (!currentStatus || !currentStatus.works || !currentStatus.works[currentWorkIndex]) return;
  const work = currentStatus.works[currentWorkIndex];
  const activePart = (window.dtpEditor && window.dtpEditor.currentSpreadPart) ? window.dtpEditor.currentSpreadPart : (window.currentSpreadPart || currentSpreadPart || 1);
  currentSpreadPart = activePart;
  window.currentSpreadPart = activePart;
  
  const slotIdx = (side === "left") 
    ? (activePart - 1) * 2 
    : (activePart - 1) * 2 + 1;

  const pageNum = slotIdx + 1;
  const frameNum = window.activeImageTargetFrame || 1;
  window.activeImageTargetPageNum = pageNum;
  window.activeImageTargetSide = side;
  window.activeImageTargetFrame = frameNum;

  const frameDesc = frameNum === 2 ? " 2번 그림" : "";
  const pageLabel = `${pageNum}면 (${side === 'left' ? '좌측' : '우측'})${frameDesc}`;
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
            <span>⚡ AI 새 삽화 자동 생성 (시안 1장 추천)</span>
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
              executeGenPart2Image(pageNum, frameNum);
            } else {
              onViewerGenerateFreeImage(pageNum, frameNum);
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
      if (pageNum >= 3) executeGenPart2Image(pageNum, frameNum);
      else onViewerGenerateFreeImage(pageNum, frameNum);
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

// 2부 연작 삽화 AI 자동 생성 실행 (시 후반부 정경 분석 연작 프롬프트 연동 & 미리보기 모달 팝업)
async function executeGenPart2Image(customPageNum, customFrameIdx) {
  if (!currentStatus || !currentStatus.works || !currentStatus.works[currentWorkIndex]) return;
  const work = currentStatus.works[currentWorkIndex];
  const btn = document.getElementById("btnGenPart2Image");
  const statusElem = document.getElementById("p4ImageGenStatus");

  if (btn) btn.disabled = true;
  if (statusElem) statusElem.textContent = "⏳ 시 후반부 정경 분석 및 연작 수채화 생성 중... (생성 대기 필요)";

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

    const targetPage = customPageNum || window.activeImageTargetPageNum || 4;
    const targetFrame = customFrameIdx || window.activeImageTargetFrame || 1;

    // 2부 연작 전용 미리보기 모달 열기
    openImagePreviewConfirmModal({
      episode_no: work.episode_no,
      title: work.title,
      filename: data.filename,
      image_url: data.image_url,
      page_label: `${targetPage}면 ${targetFrame === 2 ? '2번 ' : ''}연작 삽화`,
      page_num: targetPage,
      frame_idx: targetFrame,
      target_slot: "part2"
    });

  } catch (err) {
    if (statusElem) statusElem.textContent = `❌ 생성 실패: ${err.message}`;
    showToast(`❌ 2부 연작 삽화 생성 실패: ${err.message}`, "error");
  } finally {
    if (btn) btn.disabled = false;
  }
}


function openGlobalVideoModal(videoUrl, title = "시화집 영상 감상") {
  let modal = document.getElementById("storybookGlobalVideoModal");
  if (!modal) {
    modal = document.createElement("div");
    modal.id = "storybookGlobalVideoModal";
    modal.style.position = "fixed";
    modal.style.top = "0";
    modal.style.left = "0";
    modal.style.width = "100vw";
    modal.style.height = "100vh";
    modal.style.backgroundColor = "rgba(0, 0, 0, 0.88)";
    modal.style.display = "flex";
    modal.style.flexDirection = "column";
    modal.style.justifyContent = "center";
    modal.style.alignItems = "center";
    modal.style.zIndex = "999999";
    modal.style.backdropFilter = "blur(6px)";

    modal.innerHTML = `
      <div style="position: relative; width: 92%; max-width: 980px; background: #181412; border: 1.5px solid #4A3B32; border-radius: 14px; overflow: hidden; box-shadow: 0 14px 40px rgba(0,0,0,0.65);">
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px 18px; background: #261F1A; border-bottom: 1px solid #3D312A; color: #FFF;">
          <div style="display: flex; align-items: center; gap: 8px;">
            <span style="font-size: 1.2rem;">🎬</span>
            <span id="storybookGlobalVideoTitle" style="font-weight: 700; font-size: 1rem; color: #F5E8D3;">${escapeHtml(title)}</span>
          </div>
          <button onclick="closeGlobalVideoModal()" style="background: none; border: none; color: #D5C2B0; font-size: 1.6rem; cursor: pointer; padding: 0 4px; line-height: 1;">&times;</button>
        </div>
        <div style="position: relative; width: 100%; height: 0; padding-bottom: 56.25%; background: #000;">
          <video id="storybookGlobalVideoElement" controls autoplay style="position: absolute; top:0; left:0; width: 100%; height: 100%; outline: none;"></video>
        </div>
      </div>
    `;
    document.body.appendChild(modal);

    modal.addEventListener("click", (e) => {
      if (e.target === modal) closeGlobalVideoModal();
    });
  }

  const titleEl = document.getElementById("storybookGlobalVideoTitle");
  if (titleEl) titleEl.textContent = title;

  const videoEl = document.getElementById("storybookGlobalVideoElement");
  if (videoEl) {
    videoEl.src = videoUrl;
    videoEl.load();
    videoEl.play().catch(() => {});
  }
  modal.style.display = "flex";
}

function closeGlobalVideoModal() {
  const modal = document.getElementById("storybookGlobalVideoModal");
  if (modal) {
    const videoEl = document.getElementById("storybookGlobalVideoElement");
    if (videoEl) {
      videoEl.pause();
      videoEl.src = "";
    }
    modal.style.display = "none";
  }
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



function renderEmptyBookSpread() {
  const isStandard = Boolean(currentStatus && currentStatus.project && currentStatus.project.book_type === "standard");
  const spreadContainer = document.querySelector(".book-spread");
  if (spreadContainer) {
    if (isStandard) spreadContainer.classList.add("standard-mode");
    else spreadContainer.classList.remove("standard-mode");
  }

  const epEl = document.getElementById("viewerEpisode");
  if (epEl) epEl.textContent = "준비 중";
  const titleEl = document.getElementById("viewerTitle") || document.getElementById("dtpTitleRight");
  if (titleEl) titleEl.textContent = "첫 번째 작품을 창작해보세요";
  const bodyEl = document.getElementById("viewerBody") || document.getElementById("dtpBodyRight");
  if (bodyEl) bodyEl.textContent = "좌측 [✍️ 시화 창작] 탭에서 기억을 들려주시면 아름다운 시가 이곳에 엮입니다.";
  const imgEl = document.getElementById("viewerImage");
  if (imgEl) imgEl.style.display = "none";
  const placeholder = document.getElementById("viewerImagePlaceholder");
  if (placeholder) {
    placeholder.style.display = "flex";
    if (isStandard) {
      placeholder.innerHTML = `<span style="font-size: 2.2rem; margin-bottom: 6px;">📖</span><span style="font-weight: 600; color: #49637c;">일반 시집 (텍스트 조판)</span>`;
    } else {
      placeholder.innerHTML = `<span style="font-size: 2.5rem;">🎨</span><span>삽화 이미지를 준비 중입니다.</span>`;
    }
  }
  const btnPrev = document.getElementById("btnPrevWork");
  if (btnPrev) btnPrev.disabled = true;
  const btnNext = document.getElementById("btnNextWork");
  if (btnNext) btnNext.disabled = true;
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
      // [요구사항 1] 좌측 책장 드롭존 툴팁 차단
      if (el.id === "viewerDropzone" || el.classList?.contains("book-page-left")) {
        return null;
      }
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



// 🔄 시 제목 변경 시 [집필실 제목창 ⇄ 집필실 드롭다운 ⇄ 책 전체 구성표 ⇄ 조판 편집기] 4자 실시간 동기화
function syncWorkTitleEverywhere(episodeNo, newTitle, source = "") {
  if (!episodeNo || !newTitle) return;
  const cleanTitle = newTitle.trim();
  if (!cleanTitle) return;

  // 1) 전역 works 상태 갱신
  if (currentStatus && Array.isArray(currentStatus.works)) {
    const w = currentStatus.works.find(item => item.episode_no === episodeNo);
    if (w) w.title = cleanTitle;
  }

  // 2) 집필실 제목 입력창 & 회차 드롭다운 텍스트 갱신
  if (source !== "studioInput" && currentEditingEpisode === episodeNo) {
    const inputTitle = document.getElementById("inputFinalTitle");
    if (inputTitle && inputTitle.value.trim() !== cleanTitle) {
      inputTitle.value = cleanTitle;
    }
  }
  const selEdit = document.getElementById("selectWorkToEdit");
  if (selEdit) {
    const opt = Array.from(selEdit.options).find(o => o.value === episodeNo);
    if (opt) opt.textContent = `📖 [${episodeNo}] ${cleanTitle}`;
  }

  // 3) 좌측 '책 전체 구성표' 트리 항목 제목 갱신
  if (window.bookStructureData && Array.isArray(window.bookStructureData.sections)) {
    const sec = window.bookStructureData.sections.find(s => s.episode_no === episodeNo);
    if (sec) {
      sec.title = `[${episodeNo}] ${cleanTitle}`;
      const treeEl = document.getElementById("treeItem_" + sec.id);
      if (treeEl) {
        const titleSpan = treeEl.querySelector(".item-title");
        if (titleSpan) titleSpan.textContent = `[${episodeNo}] ${cleanTitle}`;
      }
    }
  }
  const fallbackTreeEl = document.getElementById("treeItem_poem_" + episodeNo);
  if (fallbackTreeEl) {
    const titleSpan = fallbackTreeEl.querySelector(".item-title");
    if (titleSpan) titleSpan.textContent = `[${episodeNo}] ${cleanTitle}`;
  }

  // 4) 조판 편집기 상단 드롭다운 및 현재 열린 조판 제목 상자 갱신
  const selDtp = document.getElementById("selectWorkDropdown");
  if (selDtp && currentStatus && Array.isArray(currentStatus.works)) {
    const wIdx = currentStatus.works.findIndex(item => item.episode_no === episodeNo);
    if (wIdx >= 0) {
      const optDtp = Array.from(selDtp.options).find(o => String(o.value) === String(wIdx));
      if (optDtp) {
        const wObj = currentStatus.works[wIdx];
        const chapLabel = wObj.chapter ? `[${wObj.chapter}] ` : "";
        optDtp.textContent = `${chapLabel}[${episodeNo}] ${cleanTitle}`;
      }
    }
  }
  if (source !== "dtpTitle" && window.dtpEditor) {
    const curW = window.dtpEditor.getCurrentWork();
    if (curW && curW.episode_no === episodeNo) {
      ["dtpTitleLeft", "dtpTitleRight"].forEach(id => {
        const el = document.getElementById(id);
        if (el && el.offsetParent !== null) el.innerText = cleanTitle;
      });
    }
  }
}
window.syncWorkTitleEverywhere = syncWorkTitleEverywhere;

document.addEventListener("DOMContentLoaded", () => {
  const inputTitleEl = document.getElementById("inputFinalTitle");
  if (inputTitleEl) {
    inputTitleEl.addEventListener("input", () => {
      if (currentEditingEpisode && inputTitleEl.value.trim()) {
        syncWorkTitleEverywhere(currentEditingEpisode, inputTitleEl.value.trim(), "studioInput");
      }
    });
  }
});
