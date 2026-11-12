// ============================================================================
// [Module] project_shelf.js - 시집 서재/프로젝트 관리, 전권 구조 트리, 일괄 가져오기, 목차 편집기
// ============================================================================
// 2. 시집 프로젝트 목록 로드 및 드롭다운 연동
async function loadProjects() {
  const select = document.getElementById("selectProjectDropdown");
  if (!select) return;

  try {
    const res = await fetch("/api/projects");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    projectList = data.projects || [];
    const active = data.active_project;

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

      // 집필 시집 상단 배너 즉시 동기화
      const bannerTitle = document.getElementById("bannerBookTitle");
      if (bannerTitle && active.name) bannerTitle.textContent = active.name;
      const bannerAuthor = document.getElementById("bannerBookAuthor");
      if (bannerAuthor) bannerAuthor.textContent = active.author ? `${active.author} 지음` : "시인 지음";
    }
  } catch (err) {
    console.warn("서버 API 부재: 웹 독립 실행 모드로 자동 폴백합니다.", err);
    // [웹 독립 실행 모드] 기본 시집 자동 주입
    projectList = [
      { id: "sunset_memory", name: "노을빛 기억 (시범 시집)", is_active: true }
    ];
    select.innerHTML = "";
    const opt = document.createElement("option");
    opt.value = "sunset_memory";
    opt.textContent = "노을빛 기억 (시범 시집)";
    opt.selected = true;
    select.appendChild(opt);

    const bannerTitle = document.getElementById("bannerBookTitle");
    if (bannerTitle) bannerTitle.textContent = "노을빛 기억";
    const bannerAuthor = document.getElementById("bannerBookAuthor");
    if (bannerAuthor) bannerAuthor.textContent = "임종훈 시인 지음";
  }
}

// 3. 시집 전환 이벤트 처리
async function onProjectSelectChange(projectId) {
  if (!projectId) return;

  try {
    // 클라이언트 브라우저 쿠키 및 저장소 즉시 갱신
    document.cookie = `sb_active_project=${encodeURIComponent(projectId)}; path=/; max-age=2592000; SameSite=Lax`;
    try { localStorage.setItem("sb_active_project", projectId); } catch (e) { }

    const res = await fetch("/api/projects/select", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project_id: projectId })
    });
    const data = await res.json();

    if (res.ok && data.success) {
      // 시집 전환 시 전체 상태, 책 구성표, 조판 화면이 깨끗하게 동기화되도록 즉시 새로고침
      window.location.reload();
    } else {
      alert("시집 전환 실패: " + (data.detail || data.error || "알 수 없는 오류"));
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
    let res = await fetch("/api/status");
    if (!res.ok) {
      console.warn("웹 정적 클라이언트 모드: /studio/data/default_status.json에서 작품을 로드합니다.");
      res = await fetch("/studio/data/default_status.json");
    }
    currentStatus = await res.json();
    window.currentStatus = currentStatus;

    // 창작실 제목 목록 드롭다운 최우선 즉시 갱신 (지연 방지)
    updateWorkToEditDropdown();

    const proj = currentStatus.project || {};

    // 1. 현재 시집 한 줄 인라인 배너 최우선 동기화
    const bTitle = document.getElementById("bannerBookTitle");
    if (bTitle && proj.name) bTitle.textContent = proj.name;
    const bAuthor = document.getElementById("bannerBookAuthor");
    if (bAuthor) bAuthor.textContent = proj.author ? `${proj.author} 지음` : "시인 지음";

    // 2. 헤더 및 사이드바 배지 업데이트 (요소 부재 시 안전 가드)
    const badgeComp = document.getElementById("badgeCompletedCount");
    if (badgeComp) badgeComp.textContent = currentStatus.completed_count;
    const badgeTarget = document.getElementById("badgeTargetCount");
    if (badgeTarget) badgeTarget.textContent = currentStatus.target_count;
    const exportComp = document.getElementById("exportCompletedCount");
    if (exportComp) exportComp.textContent = currentStatus.completed_count;
    
    // 현재 편집 중인 회차가 있으면 유지, 없으면 다음 회차 표시
    const inputEp = document.getElementById("inputEpisode");
    if (inputEp) {
      if (currentEditingEpisode) {
        inputEp.value = currentEditingEpisode;
      } else {
        inputEp.value = currentStatus.next_episode || "01";
      }
    }

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
      if (window.dtpEditor) window.dtpEditor.renderSpread(currentWorkIndex, 1, false, { isInitialLoad: true }); else renderBookSpread(currentWorkIndex);
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
    if (typeof refreshBookStructure === 'function') {
      await refreshBookStructure();
    }
  } catch (err) {
    console.error("상태 로드 실패:", err);
  }
}

// ========================================================
// 📚 [Full Book Architecture] 책 전체 구성표 트리 위젯 로직
// ========================================================
let bookStructureData = null;
let currentSelectedBookSectionId = null;

async function refreshBookStructure() {
  try {
    const res = await fetch("/api/book/structure");
    const json = await res.json();
    if (!json.success || !json.data) {
      console.warn("책 구조 응답 실패:", json);
      return;
    }

    bookStructureData = json.data;
    window.bookStructureData = bookStructureData;

    // 1. 총 페이지 및 완성도 뱃지 업데이트 (안전한 fallback)
    const badgePages = document.getElementById("badgeTotalBookPages");
    const stats = bookStructureData.stats || {};
    const totalP = stats.total_pages || bookStructureData.total_pages || 0;
    const compRate = stats.completion_rate !== undefined ? stats.completion_rate : 0;
    const compCnt = stats.completed_sections !== undefined ? stats.completed_sections : (stats.completed || 0);
    const totCnt = stats.total_sections || (bookStructureData.sections ? bookStructureData.sections.length : 0);

    if (badgePages) {
      badgePages.textContent = "총 " + totalP + "쪽";
      badgePages.title = "완성도: " + compRate + "% (" + compCnt + "/" + totCnt + " 섹션)";
    }

    // 2. 트리 렌더링
    renderBookStructureTree(bookStructureData);
  } catch (err) {
    console.error("책 전체 구성표 로드 예외:", err);
  }
}

function renderBookStructureTree(data) {
  const container = document.getElementById("bookStructureTree");
  if (!container) return;

  if (!data || !data.sections || data.sections.length === 0) {
    container.innerHTML = '<div style="font-size: 0.74rem; color: #A08C7D; padding: 8px; text-align: center;">등록된 섹션이 없습니다.</div>';
    return;
  }

  // 그룹별 분할 (front_matter, body_matter, back_matter)
  const bodyCount = data.sections.filter(function(s) { return s.group === 'body_matter'; }).length;
  const groups = {
    front_matter: { label: "앞부속 (표지·서문·목차)", icon: "📖", items: [] },
    body_matter: { label: "본문 시화 (" + bodyCount + "편)", icon: "📜", items: [] },
    back_matter: { label: "뒷부속 (맺음말·판권지)", icon: "🔖", items: [] }
  };

  data.sections.forEach(function(sec) {
    if (groups[sec.group]) {
      groups[sec.group].items.push(sec);
    }
  });

  let html = '';
  Object.keys(groups).forEach(function(grpKey) {
    const grp = groups[grpKey];
    if (grp.items.length === 0) return;

    const firstItem = grp.items[0];
    const lastItem = grp.items[grp.items.length - 1];

    const firstPage = firstItem.start_page !== undefined ? firstItem.start_page : (firstItem.page_start !== undefined ? firstItem.page_start : 0);
    const lastPage = lastItem.end_page !== undefined ? lastItem.end_page : (lastItem.start_page !== undefined ? lastItem.start_page : (lastItem.page_start || 0));
    const pageRange = "p." + firstPage + "~" + lastPage;

    html += '<div class="book-tree-group" id="treeGroup_' + grpKey + '">';
    html += '  <div class="book-tree-group-header" onclick="toggleBookTreeGroup(\'' + grpKey + '\')">';
    html += '    <div class="group-title-left">';
    html += '      <span class="group-chevron">▾</span>';
    html += '      <span>' + grp.icon + ' ' + grp.label + '</span>';
    html += '    </div>';
    html += '    <span class="group-page-range">' + pageRange + '</span>';
    html += '  </div>';
    html += '  <div class="book-tree-group-items">';

    grp.items.forEach(function(sec) {
      const sPage = sec.start_page !== undefined ? sec.start_page : (sec.page_start !== undefined ? sec.page_start : 0);
      const ePage = sec.end_page !== undefined ? sec.end_page : (sec.page_count && sec.page_count > 1 ? (sPage + sec.page_count - 1) : sPage);
      const pageStr = (ePage > sPage) ? ("p." + sPage + "~" + ePage) : ("p." + sPage);
      
      const isActive = currentSelectedBookSectionId === sec.id ? ' active' : '';
      const safeTitle = (sec.title || '').replace(/"/g, '&quot;');
      const epAttr = sec.episode_no ? (' data-episode="' + sec.episode_no + '"') : '';

      const stIcon = sec.status_icon || (sec.status === 'completed' ? '🟢' : (sec.status === 'in_progress' ? '🟠' : '⚪'));
      const stLabel = sec.status_label || (sec.status === 'completed' ? '완성' : (sec.status === 'in_progress' ? '작성 중' : '미작성'));

      html += '    <div class="book-tree-item' + isActive + '" id="treeItem_' + sec.id + '"' +
              ' data-section-id="' + sec.id + '" data-category="' + (sec.category || sec.section_type || '') + '"' + epAttr +
              ' onclick="onBookTreeItemClick(\'' + sec.id + '\')"' +
              ' title="' + safeTitle + ' (' + stLabel + ', ' + pageStr + ')">';
      html += '      <div class="item-left">';
      html += '        <span class="item-page">' + pageStr + '</span>';
      html += '        <span class="item-title">' + safeTitle + '</span>';
      html += '      </div>';
      html += '      <span class="item-status" title="' + stLabel + '">' + stIcon + '</span>';
      html += '    </div>';
    });

    html += '  </div>';
    html += '</div>';
  });

  container.innerHTML = html;
}

function toggleBookTreeGroup(grpKey) {
  const grpEl = document.getElementById("treeGroup_" + grpKey);
  if (grpEl) {
    grpEl.classList.toggle("collapsed");
  }
}

function switchToTab(targetId) {
  const tabs = document.querySelectorAll(".nav-tab-btn");
  const panels = document.querySelectorAll(".tab-content");

  tabs.forEach(tab => {
    const t = tab.getAttribute("data-target") || tab.id;
    if (t === targetId || (targetId === 'panelBook' && (t === 'panelBook' || tab.id === 'tabBtnBook'))) {
      tab.classList.add("active");
    } else {
      tab.classList.remove("active");
    }
  });

  panels.forEach(p => {
    if (p.id === targetId) {
      p.classList.add("active");
    } else {
      p.classList.remove("active");
    }
  });
}

function updateBookTreeActiveItem(sectionId) {
  if (!sectionId) return;
  document.querySelectorAll('.book-tree-item').forEach(function(el) { el.classList.remove('active'); });
  const targetEl = document.getElementById("treeItem_" + sectionId);
  if (targetEl) targetEl.classList.add('active');
}
window.updateBookTreeActiveItem = updateBookTreeActiveItem;
window.refreshBookStructure = refreshBookStructure;

async function onBookTreeItemClick(sectionId) {
  if (!bookStructureData || !bookStructureData.sections) return;
  const sec = bookStructureData.sections.find(function(s) { return s.id === sectionId; });
  if (!sec) return;

  currentSelectedBookSectionId = sectionId;

  // 트리 UI 활성화 갱신
  updateBookTreeActiveItem(sectionId);

  const activeTab = document.querySelector('.tab-content.active');
  const tabId = activeTab ? activeTab.id : '';

  // 1) 본문 시화인 경우: 시화창작 탭이든 조판편집 탭이든 구성표·집필실·조판편집기 3자 100% 동시 연동!
  if ((sec.category === 'poem' || sec.group === 'body_matter') && sec.episode_no) {
    const epNo = sec.episode_no;
    window._hasUserSelectedWork = true;

    // (A) 집필실(회차 선택 드롭다운, 시 제목, 본문 등) 즉시 동기화
    if (typeof loadWorkIntoEditor === 'function') {
      loadWorkIntoEditor(epNo, { fromDtpOrTree: true });
    }

    // (B) 조판 편집기(현재 작품 인덱스 및 펼침면) 즉시 동기화
    if (window.dtpEditor && typeof window.dtpEditor.loadSection === 'function') {
      window.dtpEditor.loadSection(sec, { skipStudioSync: true });
    } else if (currentStatus && currentStatus.works) {
      const foundIdx = currentStatus.works.findIndex(function(w) { return w.episode_no === epNo; });
      if (foundIdx !== -1) {
        currentWorkIndex = foundIdx;
        window.currentWorkIndex = foundIdx;
        if (typeof renderBookSpread === 'function') renderBookSpread(foundIdx);
      }
    }

    // 시화창작 탭이 아닐 때 다른 부가 탭(영상 등)에 있었다면 조판편집 탭으로 전환
    if (tabId !== 'panelStudio' && tabId !== 'panelBook') {
      switchToTab('panelBook');
    }
  } else {
    // 2) 부속물 (앞표지, 속표지, 서문, 목차, 맺음말, 판권지, 뒤표지)인 경우:
    // 무조건 조판 편집기(panelBook)로 즉각 화면 전환하여 실물 조판 펼침면을 렌더링!
    switchToTab('panelBook');
    if (window.dtpEditor && typeof window.dtpEditor.loadSection === 'function') {
      window.dtpEditor.loadSection(sec);
    }
  }
}

let isSavingWork = false; // 저장 중복 클릭 및 동시 실행 방지 플래그

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
  let promptMsg = "➕ 새로운 부/챕터 이름을 입력해주세요.\n";
  if (tocChapters.length > 0) {
    promptMsg += "\n[현재 등록된 부/챕터 목록]\n" + tocChapters.map((c, i) => `${i + 1}. ${c}`).join("\n") + "\n";
  }
  const nextNo = tocChapters.length + 1;
  promptMsg += `\n(예: 제${nextNo}부: 달빛 머문 뜨락 또는 특별부: 못다 한 이야기)`;

  const name = prompt(promptMsg);
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

// 부(챕터) 이름 바꾸기
function renameTocChapter() {
  if (tocChapters.length === 0) {
    alert("이름을 변경할 부/챕터가 목록에 없습니다.\n먼저 [➕ 새 부(챕터) 추가]를 해주세요.");
    return;
  }

  const listStr = tocChapters.map((c, i) => `${i + 1}. ${c}`).join("\n");
  const choice = prompt(
    "✏️ 이름을 변경할 부(챕터)의 번호를 선택해주세요:\n\n" + listStr
  );
  if (!choice) return;

  const idx = parseInt(choice.trim(), 10) - 1;
  if (isNaN(idx) || idx < 0 || idx >= tocChapters.length) {
    alert("올바른 번호를 입력해주세요.");
    return;
  }

  const oldName = tocChapters[idx];
  const newName = prompt(`「${oldName}」의 새로운 부/챕터 이름을 입력해주세요:`, oldName);
  if (!newName || !newName.trim()) return;

  const trimmedNew = newName.trim();
  if (trimmedNew === oldName) return;

  if (tocChapters.includes(trimmedNew)) {
    alert("이미 동일한 이름의 부/챕터가 존재합니다.");
    return;
  }

  // 1) 챕터 목록 갱신
  tocChapters[idx] = trimmedNew;

  // 2) 편집 목록에서 해당 부에 속했던 시들의 챕터 일괄 변경
  let updatedCount = 0;
  tocEditItems.forEach(item => {
    if (item.chapter === oldName) {
      item.chapter = trimmedNew;
      updatedCount++;
    }
  });

  renderTocEditorList();
  alert(`✏️ 「${oldName}」 부가 「${trimmedNew}」(으)로 변경되었습니다.\n(소속된 시 ${updatedCount}편의 소속 부가 함께 갱신되었습니다.)\n\n하단의 [💾 목차 및 순서 저장하기]를 눌러 최종 반영하세요.`);
}

// 부(챕터) 삭제
function deleteTocChapter() {
  if (tocChapters.length === 0) {
    alert("삭제할 부/챕터가 목록에 없습니다.");
    return;
  }

  const listStr = tocChapters.map((c, i) => `${i + 1}. ${c}`).join("\n");
  const choice = prompt(
    "🗑️ 삭제할 부(챕터)의 번호를 입력해주세요:\n\n" + listStr + "\n\n(참고: 삭제 시 해당 부에 속했던 시들은 '소속 부 없음(미분류)' 상태로 안전하게 전환됩니다.)"
  );
  if (!choice) return;

  const idx = parseInt(choice.trim(), 10) - 1;
  if (isNaN(idx) || idx < 0 || idx >= tocChapters.length) {
    alert("올바른 번호를 입력해주세요.");
    return;
  }

  const targetChapter = tocChapters[idx];
  const ok = confirm(`정말 「${targetChapter}」 부(챕터)를 삭제하시겠습니까?\n이 부에 속한 시들은 소속 부가 해제(미분류)됩니다.`);
  if (!ok) return;

  tocChapters.splice(idx, 1);

  let clearedCount = 0;
  tocEditItems.forEach(item => {
    if (item.chapter === targetChapter) {
      item.chapter = "";
      clearedCount++;
    }
  });

  renderTocEditorList();
  alert(`🗑️ 「${targetChapter}」 부가 삭제되었습니다.\n(해당 부에 속했던 시 ${clearedCount}편의 소속이 해제되었습니다.)\n\n하단의 [💾 목차 및 순서 저장하기]를 눌러 최종 반영하세요.`);
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
      if (typeof refreshBookStructure === 'function') {
        await refreshBookStructure();
      }
      if (window.dtpEditor && typeof window.dtpEditor.ensureStatusLoaded === 'function') {
        await window.dtpEditor.ensureStatusLoaded(true);
      }
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

// 전역 window 바인딩 (인라인 HTML onclick 이벤트 안전 보장)
window.openEditProjectModal = openEditProjectModal;
window.closeEditProjectModal = closeEditProjectModal;
window.onCreateNewProject = onCreateNewProject;
window.onUpdateProject = onUpdateProject;
window.onDeleteCurrentProject = onDeleteCurrentProject;
window.openTocEditorModal = openTocEditorModal;
window.closeTocEditorModal = closeTocEditorModal;
window.submitTocEditor = submitTocEditor;
window.onModalOverlayClick = onModalOverlayClick;



