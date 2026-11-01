/**
 * StoryBook Studio - 모듈형 2-Layer 조판 편집 엔진 (dtp_editor_core.js v4.0)
 * 
 * 1. 완전 대칭형 좌/우 2쪽(스프레드) 컴포넌트 아키텍처
 * 2. 2-Layer 완벽 독립 분리: Layer 1 (그림 레이어), Layer 2 (글 레이어)
 * 3. 상단 [페이지 용도] x [글 유형] 실시간 연동
 * 4. 시화창작 탭 연동: 좌(전면삽화) + 우(시 시작) 기본 프리셋 및 자유 변경
 * 5. 빨간색 가이드 박스: 제목(상단 안전선 준수), 본문(하단 안전선 준수)
 * 6. 정밀 행 용량(Capacity) 기반 본문 흐름 및 자동 2쪽 증설/축소 (무한루프 원천 차단):
 *    - 본문 초과 시 하단 배지 표시 & 자동으로 2쪽 추가 (2면 ➔ 4면 ➔ 6면)
 *    - 본문 축소 시 자동으로 2쪽 삭제 (6면 ➔ 4면 ➔ 2면)
 * 7. Undo / Redo (실행 취소 / 다시 실행)
 * 8. 실시간 한지 가독성 패널 (투명도 슬라이더 기본 85% + 글자색 반전)
 * 9. 시어 줄바꿈 보호 (word-break: keep-all) & A5 실물 줌
 */

(function(window) {
  'use strict';

  function hideElem(el) {
    if (!el) return;
    el.classList.add('is-hidden');
    el.style.display = 'none';
  }

  function showElem(el, displayType) {
    if (!el) return;
    el.classList.remove('is-hidden');
    el.style.display = displayType || 'block';
  }

  class DtpEditorCore {
    constructor() {
      this.currentWorkIndex = 0;
      this.currentSpreadPart = 1; // 1 = 1·2면, 2 = 3·4면, 3 = 5·6면
      this.showGuides = true;
      this.realScale = false;
      this.undoStack = [];
      this.redoStack = [];
      this.maxUndoSteps = 25;

      this.defaultConfig = {
        page_count: 2,
        font_size_pt: 12,
        line_height_ratio: 1.5,
        text_align: "left",
        backdrop_opacity: 0.85,
        text_color_mode: "dark",
        pages: [
          { page_num: 1, usage: "image", role: "none", image_file: "" },
          { page_num: 2, usage: "text", role: "start", image_file: "" }
        ]
      };
    }

    init() {
      console.log("[DTP Core v4.0] 모듈형 2-Layer 조판 편집 엔진 가동");
      this.bindShortcuts();
      this.bindToolbarEvents();

      // 탭 전환 감지: 조판 탭 진입 시 자동 렌더링
      document.querySelectorAll(".nav-tab-btn").forEach(btn => {
        btn.addEventListener("click", () => {
          const target = btn.getAttribute("data-target") || btn.id;
          if (target === "panelBook" || target === "tabBtnBook") {
            setTimeout(() => this.renderSpread(this.currentWorkIndex, this.currentSpreadPart || 1), 50);
          }
        });
      });

      // 초기 로드 시 자동 렌더링
      setTimeout(() => {
        if (this.getWorksList().length > 0) {
          this.renderSpread(this.currentWorkIndex, 1);
        } else {
          this.ensureStatusLoaded().then(ok => {
            if (ok) this.renderSpread(this.currentWorkIndex, 1);
          });
        }
      }, 150);
    }

    bindShortcuts() {
      document.addEventListener("keydown", (e) => {
        const panel = document.getElementById("panelBook");
        if (!panel || !panel.classList.contains("active")) return;

        if ((e.ctrlKey || e.metaKey) && (e.key === 'z' || e.key === 'Z')) {
          e.preventDefault();
          if (e.shiftKey) this.redo();
          else this.undo();
        } else if ((e.ctrlKey || e.metaKey) && (e.key === 'y' || e.key === 'Y')) {
          e.preventDefault();
          this.redo();
        }
      });
    }

    bindToolbarEvents() {
      const btnGuide = document.getElementById("btnToggleLayoutGuides");
      if (btnGuide) {
        btnGuide.onclick = () => this.toggleGuides();
      }
      this.bindPageDropzones();
    }

    bindPageDropzones() {
      ['left', 'right'].forEach(side => {
        const capSide = (side === 'left') ? 'Left' : 'Right';
        const pageEl = document.getElementById(`dtpPage${capSide}`);
        if (!pageEl) return;

        ['dragenter', 'dragover'].forEach(evt => {
          pageEl.addEventListener(evt, (e) => {
            e.preventDefault();
            e.stopPropagation();
            pageEl.style.outline = "2px dashed #C85A17";
          });
        });

        ['dragleave', 'dragend'].forEach(evt => {
          pageEl.addEventListener(evt, (e) => {
            e.preventDefault();
            e.stopPropagation();
            pageEl.style.outline = "";
          });
        });

        pageEl.addEventListener('drop', (e) => {
          e.preventDefault();
          e.stopPropagation();
          pageEl.style.outline = "";
          const files = e.dataTransfer?.files;
          if (files && files.length > 0 && files[0].type.startsWith("image/")) {
            const pageIdx = (this.currentSpreadPart - 1) * 2 + (side === 'left' ? 0 : 1);
            const pageNum = pageIdx + 1;
            window.currentSpreadPart = this.currentSpreadPart;
            if (typeof currentSpreadPart !== 'undefined') currentSpreadPart = this.currentSpreadPart;
            if (typeof currentViewerTargetSlot !== 'undefined') {
              currentViewerTargetSlot = (pageNum >= 3) ? "part2" : "main";
            }
            if (typeof uploadViewerImage === 'function') {
              uploadViewerImage(files[0]);
            }
          }
        });
      });
    }

    refreshImages() {
      this._imgCacheBust = Date.now();
      ['Left', 'Right'].forEach(capSide => {
        const imgElem = document.getElementById(`dtpImg${capSide}`);
        if (imgElem) imgElem.removeAttribute("data-clean-path");
      });
      this.renderSpread(this.currentWorkIndex, this.currentSpreadPart, false);
    }

    getWorksList() {
      if (typeof currentStatus !== 'undefined' && currentStatus && Array.isArray(currentStatus.works)) {
        window.currentStatus = currentStatus;
        return currentStatus.works;
      }
      if (window.currentStatus && Array.isArray(window.currentStatus.works)) {
        return window.currentStatus.works;
      }
      return [];
    }

    getCurrentWork() {
      const works = this.getWorksList();
      if (works.length === 0) return null;
      return works[this.currentWorkIndex] || works[0] || null;
    }

    async ensureStatusLoaded() {
      if (this.getWorksList().length > 0) return true;
      try {
        const res = await fetch("/api/status");
        if (res.ok) {
          const data = await res.json();
          window.currentStatus = data;
          if (typeof currentStatus !== 'undefined') {
            currentStatus = data;
          }
          return Array.isArray(data.works) && data.works.length > 0;
        }
      } catch (e) {
        console.error("[DTP Core] /api/status 직접 로드 실패:", e);
      }
      return false;
    }

    /**
     * 작품 layout_config 정규화 (pages 배열 단일화 & 구 slots/page_roles 완벽 호환)
     */
    getNormalizedConfig(work) {
      if (!work) return JSON.parse(JSON.stringify(this.defaultConfig));

      let cfg = work.layout_config;
      if (!cfg || typeof cfg !== 'object') {
        cfg = {};
      }

      let count = cfg.page_count || (work.layout_mode === 'multi_page' ? 4 : 2);
      if (count % 2 !== 0) count = Math.ceil(count / 2) * 2;
      count = Math.max(2, Math.min(6, count));

      let pages = Array.isArray(cfg.pages) ? [...cfg.pages] : [];

      const hasImage = Boolean(work.image_file && String(work.image_file).trim());
      const defaultSlots = hasImage ? ["image", "text"] : ["blank", "text"];
      const legacySlots = Array.isArray(cfg.slots) && cfg.slots.length >= 2 ? cfg.slots : defaultSlots;
      const legacyRoles = Array.isArray(cfg.page_roles) && cfg.page_roles.length >= 2 ? cfg.page_roles : ["none", "start"];

      for (let i = 0; i < 6; i++) {
        if (!pages[i]) {
          const slotType = (i < legacySlots.length) ? legacySlots[i] : "text";
          let usage = "text";
          if (slotType === "image") usage = "image";
          else if (slotType === "image_text") usage = "image_text";
          else if (slotType === "blank") usage = "blank";

          const roleType = (i < legacyRoles.length)
            ? legacyRoles[i]
            : (i === 0 ? "none" : (i === 1 ? "start" : "continue"));

          let imgFile = "";
          if (i === 0) imgFile = work.image_file || "";
          else if (i === 2) imgFile = work.image_file_2 || "";

          pages[i] = {
            page_num: i + 1,
            usage: usage,
            role: roleType,
            image_file: imgFile,
            custom_text: ""
          };
        } else {
          pages[i].page_num = i + 1;
          if (i === 0 && !pages[i].image_file && work.image_file) {
            pages[i].image_file = work.image_file;
          }
        }
      }

      const normalized = {
        page_count: count,
        font_size_pt: parseFloat(cfg.font_size_pt) || 12,
        line_height_ratio: parseFloat(cfg.line_height_ratio) || 1.5,
        text_align: cfg.text_align || "left",
        backdrop_opacity: cfg.backdrop_opacity !== undefined ? parseFloat(cfg.backdrop_opacity) : 0.85,
        text_color_mode: cfg.text_color_mode || "dark",
        pages: pages.slice(0, count),
        _all_pages_pool: pages,
        slots: pages.slice(0, count).map(p => p.usage),
        page_roles: pages.slice(0, count).map(p => p.role),
        image_settings: cfg.image_settings || {}
      };

      work.layout_config = normalized;
      return normalized;
    }

    /**
     * 🌟 정밀 페이지 행 용량(Capacity) 계산 및 순차 텍스트 흐름(Flow) 배정
     * - 앞 페이지부터 인쇄안전선 내부 용량만큼 먼저 채우고, 넘치는 줄만 다음 페이지로 이관합니다.
     * - 페이지 수(page_count)에 의해 앞 페이지의 줄 수가 흔들리지 않으므로 무한루프가 원천 차단됩니다.
     */
    calculateTextFlowAndPages(work, cfg) {
      const fullText = (work.poem_body || work.body || work.content || "").replace(/\r\n/g, "\n").trim();
      const rawLines = fullText ? fullText.split("\n") : [];

      const pt = parseFloat(cfg.font_size_pt) || 12;
      const lh = parseFloat(cfg.line_height_ratio) || 1.5;

      // 12pt 기준 15.2px, 줄높이 1.85 -> 1줄당 약 28.12px
      const fontPx = (pt / 12.0) * 15.2;
      const linePx = fontPx * lh;

      // 상단 제목+지은이 상자가 있는 페이지(start)의 본문 가용 높이: 약 435px (12pt 기준 15줄 안착)
      // 본문만 이어지는 페이지(continue)의 본문 가용 높이: 약 545px (12pt 기준 19줄 안착)
      const maxVisualLinesStart = Math.max(4, Math.floor(480 / linePx));
      const maxVisualLinesCont = Math.max(5, Math.floor(480 / linePx));

      // 한 줄당 한글 글자 수 (페이지별 좌우 여백 차감 반영)
      const getVisualLineCost = (lineStr, pageObj) => {
        const trimmed = (lineStr || "").trim();
        if (!trimmed) return 1;
        const leftOff = (pageObj && pageObj.left_offset) ? parseInt(pageObj.left_offset, 10) : 0;
        const rightOff = (pageObj && pageObj.right_offset) ? parseInt(pageObj.right_offset, 10) : 0;
        const effWidth = Math.max(120, 365 - leftOff - rightOff);
        const chars = Math.max(8, Math.floor(effWidth / (fontPx * 0.95)));
        return Math.max(1, Math.ceil(trimmed.length / chars));
      };

      // 최대 6페이지 풀 준비
      const pool = cfg._all_pages_pool || cfg.pages;
      while (pool.length < 6) {
        pool.push({
          page_num: pool.length + 1,
          usage: "text",
          role: "continue",
          image_file: "",
          custom_text: ""
        });
      }

      const textFlowMap = {};
      const overflowFlags = {}; // 각 페이지 하단에 '본문 초과 ➔ 다음 면 이어짐' 배지 표시 여부
      let cursor = 0;

      for (let idx = 0; idx < 6; idx++) {
        const p = pool[idx];
        const acceptsPoemFlow = (p.usage === "text" || p.usage === "image_text") &&
                                (p.role === "start" || p.role === "continue");

        if (!acceptsPoemFlow) {
          textFlowMap[idx] = [];
          overflowFlags[idx] = false;
          continue;
        }

        // 이어지는 페이지 시작 부분의 불필요한 빈 줄(연 구분 공백) 제거
        if (idx > 0 && p.role === "continue") {
          while (cursor < rawLines.length && rawLines[cursor].trim() === "") {
            cursor++;
          }
        }

        if (cursor >= rawLines.length) {
          textFlowMap[idx] = [];
          overflowFlags[idx] = false;
          continue;
        }

        const topOffset = p.top_offset ? parseInt(p.top_offset, 10) : 0;
        // 안전선 전체 522px - 패딩(28px) - 상단오프셋 = 최대 안전 본문 가용 높이
        const maxSafeHeight = Math.max(100, 522 - topOffset);
        const availableHeight = Math.max(100, maxSafeHeight - 28);
        const maxSafeLines = Math.max(3, Math.floor(availableHeight / linePx));
        const customLines = p.max_lines ? parseInt(p.max_lines, 10) : 0;
        const budget = (customLines > 0) ? Math.min(maxSafeLines, customLines) : maxSafeLines;
        let usedVisual = 0;
        const assigned = [];

        while (cursor < rawLines.length) {
          const line = rawLines[cursor];
          const cost = getVisualLineCost(line, p);
          if (usedVisual + cost > budget && assigned.length > 0) {
            break;
          }
          assigned.push(line);
          usedVisual += cost;
          cursor++;
        }

        // 페이지 맨 끝의 빈 줄 정리
        while (assigned.length > 0 && assigned[assigned.length - 1].trim() === "") {
          assigned.pop();
        }

        textFlowMap[idx] = assigned;

        // 남은 유효 텍스트가 더 있는지 확인
        let hasMoreNonEmpty = false;
        for (let k = cursor; k < rawLines.length; k++) {
          if (rawLines[k].trim() !== "") {
            hasMoreNonEmpty = true;
            break;
          }
        }
        overflowFlags[idx] = hasMoreNonEmpty;
      }

      // 만약 6면을 다 채웠는데도 남은 줄이 있다면 6면(idx=5)에 나머지 추가
      if (cursor < rawLines.length) {
        const lastIdx = 5;
        textFlowMap[lastIdx] = (textFlowMap[lastIdx] || []).concat(rawLines.slice(cursor));
        overflowFlags[lastIdx] = true;
      }

      // 필요한 총 페이지 수(2, 4, 6) 자동 산출
      let requiredPages = 2;
      const hasContentOn56 = (textFlowMap[4] && textFlowMap[4].length > 0) ||
                             (textFlowMap[5] && textFlowMap[5].length > 0) ||
                             (pool[4]?.role === 'independent' && pool[4]?.custom_text) ||
                             (pool[5]?.role === 'independent' && pool[5]?.custom_text);
      const hasContentOn34 = (textFlowMap[2] && textFlowMap[2].length > 0) ||
                             (textFlowMap[3] && textFlowMap[3].length > 0) ||
                             (pool[2]?.role === 'independent' && pool[2]?.custom_text) ||
                             (pool[3]?.role === 'independent' && pool[3]?.custom_text);

      if (hasContentOn56) {
        requiredPages = 6;
      } else if (hasContentOn34) {
        requiredPages = 4;
      } else {
        requiredPages = 2;
      }

      return {
        textFlowMap,
        overflowFlags,
        requiredPages,
        pool
      };
    }

    /**
     * 🌟 2쪽 대칭 스프레드 메인 렌더러
     */
    renderSpread(workIndex, spreadPart = null, notifyAutoPageChange = false) {
      const works = this.getWorksList();
      if (works.length === 0) {
        this.ensureStatusLoaded().then(loaded => {
          if (loaded) this.renderSpread(workIndex, spreadPart, notifyAutoPageChange);
        });
        return;
      }

      const prevWorkIndex = this.currentWorkIndex;
      if (workIndex !== undefined && workIndex !== null && !isNaN(workIndex)) {
        this.currentWorkIndex = Math.max(0, Math.min(works.length - 1, parseInt(workIndex, 10)));
        window.currentWorkIndex = this.currentWorkIndex;
        if (typeof currentWorkIndex !== 'undefined') {
          currentWorkIndex = this.currentWorkIndex;
        }
      }

      // 작품이 바뀌었을 때는 기본 1부로, 같은 작품 내에서는 현재 파트 유지
      if (spreadPart === null || spreadPart === undefined) {
        if (this.currentWorkIndex !== prevWorkIndex) {
          spreadPart = 1;
        } else {
          spreadPart = this.currentSpreadPart || 1;
        }
      }

      const work = this.getCurrentWork();
      if (!work) return;

      const cfg = this.getNormalizedConfig(work);
      const prevPageCount = cfg.page_count;

      // 1) 정밀 텍스트 분할 및 필요 면수(2/4/6) 자동 판정
      const flowResult = this.calculateTextFlowAndPages(work, cfg);
      const { textFlowMap, overflowFlags, requiredPages, pool } = flowResult;

      // 2) 본문 초과 시 2쪽 자동 추가 (2 ➔ 4 ➔ 6) / 본문 축소 시 2쪽 자동 삭제 (6 ➔ 4 ➔ 2)
      if (cfg.page_count !== requiredPages) {
        cfg.page_count = requiredPages;
        cfg.pages = pool.slice(0, requiredPages);
        cfg.slots = cfg.pages.map(p => p.usage);
        cfg.page_roles = cfg.pages.map(p => p.role);

        if (notifyAutoPageChange && window.showToast) {
          if (requiredPages > prevPageCount) {
            window.showToast(`⚠️ 본문 초과 감지: ${requiredPages - 1}·${requiredPages}면(본문 이어짐)이 자동 추가되었습니다. (총 ${requiredPages}쪽)`, "info");
          } else {
            window.showToast(`✅ 본문 안착: 불필요한 여분 2쪽이 자동 삭제되었습니다. (총 ${requiredPages}쪽)`, "info");
          }
        }
        this.saveLayoutConfigToServer(work.episode_no, cfg);
      }

      // 스프레드 파트 범위 검증 (1: 1·2면, 2: 3·4면, 3: 5·6면)
      const maxParts = Math.max(1, Math.ceil(cfg.page_count / 2));
      if (spreadPart > maxParts) spreadPart = maxParts;
      if (spreadPart < 1) spreadPart = 1;
      this.currentSpreadPart = spreadPart;
      window.currentSpreadPart = spreadPart;

      // 3) 상단 툴바 UI 동기화
      this.syncToolbarUI(work, cfg, maxParts, overflowFlags);

      // 4) 좌측 페이지 (Slot A) & 우측 페이지 (Slot B) 렌더링
      const leftPageIdx = (this.currentSpreadPart - 1) * 2;
      const rightPageIdx = leftPageIdx + 1;

      this.renderSinglePage("left", leftPageIdx, cfg, work, textFlowMap, overflowFlags);
      this.renderSinglePage("right", rightPageIdx, cfg, work, textFlowMap, overflowFlags);

      // 5) 가이드선 가시성 반영
      this.applyGuidesVisibility();
    }

    /**
     * 상단 툴바 UI 동기화
     */
    syncToolbarUI(work, cfg, maxParts, overflowFlags) {
      // 1) 작품 선택 드롭다운 채우기 및 값 동기화
      const selectWork = document.getElementById("selectWorkDropdown");
      if (selectWork) {
        const works = this.getWorksList();
        if (selectWork.options.length !== works.length) {
          selectWork.innerHTML = "";
          works.forEach((w, idx) => {
            const opt = document.createElement("option");
            opt.value = idx;
            const chapLabel = w.chapter ? `[${w.chapter}] ` : "";
            opt.textContent = `${chapLabel}[${w.episode_no}] ${w.title}`;
            selectWork.appendChild(opt);
          });
        }
        selectWork.value = this.currentWorkIndex;
      }

      // 2) 안전선 상태 배지 동기화
      const statusBadge = document.getElementById("layoutStatusBadge");
      const statusText = document.getElementById("layoutStatusText");
      if (statusBadge && statusText) {
        if (cfg.page_count > 2) {
          statusBadge.className = "layout-badge badge-ok";
          statusText.textContent = `✅ ${cfg.page_count}쪽 분할 안착 (${maxParts}부 구성)`;
        } else {
          statusBadge.className = "layout-badge badge-ok";
          statusText.textContent = "✅ 인쇄안전선 안착";
        }
      }

      // 3) 총 면수 배지 동기화
      const lblTotalPages = document.getElementById("lblTotalPagesBadge");
      if (lblTotalPages) {
        const curStart = (this.currentSpreadPart - 1) * 2 + 1;
        lblTotalPages.textContent = `📄 ${cfg.page_count}쪽 조판 (${curStart}·${curStart + 1}면 / 총 ${cfg.page_count}면)`;
      }

      // 4) 스프레드 이동 네비게이션 (1부: 1·2면, 2부: 3·4면, 3부: 5·6면)
      const partNav = document.getElementById("spreadPartNavGroup");
      if (partNav) {
        if (maxParts > 1) {
          showElem(partNav, "inline-flex");
          let navHtml = "";
          for (let p = 1; p <= maxParts; p++) {
            const isCur = (p === this.currentSpreadPart);
            const pStart = (p - 1) * 2 + 1;
            const pEnd = pStart + 1;
            navHtml += `<button type="button" class="btn-micro ${isCur ? 'active-part' : ''}" onclick="dtpEditor.switchSpreadPart(${p})" style="font-weight:700; padding:3px 9px; border-radius:4px; cursor:pointer; ${isCur ? 'background:#8C3B14; color:#fff; border:1px solid #8C3B14;' : 'background:#fff; color:#553412; border:1px solid #D5C2B0;'}">${p}부 (${pStart}·${pEnd}면)</button>`;
          }
          partNav.innerHTML = navHtml;
        } else {
          hideElem(partNav);
        }
      }

      // 5) 폰트 크기 pt 셀렉터 동기화
      const selectPt = document.getElementById("selectTypographyFontSizePt");
      if (selectPt) {
        const ptStr = String(cfg.font_size_pt || 12);
        const exists = Array.from(selectPt.options).some(o => o.value === ptStr);
        if (!exists) {
          const opt = document.createElement("option");
          opt.value = ptStr;
          opt.textContent = `${ptStr}pt`;
          selectWork && selectPt.insertBefore(opt, selectPt.lastElementChild);
        }
        selectPt.value = ptStr;
      }

      // 6) 한지 투명도 슬라이더 동기화
      const slider = document.getElementById("inputDtpHanjiOpacity");
      if (slider) {
        slider.value = Math.round((cfg.backdrop_opacity ?? 0.85) * 100);
      }
      const valLabel = document.getElementById("lblDtpHanjiOpacityVal");
      if (valLabel) {
        valLabel.textContent = `${Math.round((cfg.backdrop_opacity ?? 0.85) * 100)}%`;
      }

      // 7) 하단 책장 넘기기 인디케이터
      const turnIndicator = document.getElementById("pageTurnIndicator");
      if (turnIndicator) {
        const curStart = (this.currentSpreadPart - 1) * 2 + 1;
        const partLabel = maxParts > 1 ? ` (${this.currentSpreadPart}/${maxParts}부)` : "";
        turnIndicator.textContent = `${work.episode_no || ''} 「${work.title || ''}」 — ${curStart}·${curStart + 1}면${partLabel}`;
      }
    }

    /**
     * 단일 페이지 대칭 렌더링 (side: "left" | "right")
     */
    /**
     * 상/하단 리사이즈 핸들 드래그 연동 (본문 행수 실시간 조절)
     */
    attachResizeHandles(boxBody, side, pageIdx, cfg, work) {
      let topHandle = boxBody.querySelector(".dtp-resize-handle.handle-top");
      if (!topHandle) {
        topHandle = document.createElement("div");
        topHandle.className = "dtp-resize-handle handle-top";
        topHandle.innerHTML = '<div class="handle-bar-pill"></div><span class="handle-label">▲ 본문 시작선 ↕</span>';
        boxBody.appendChild(topHandle);
      }

      let bottomHandle = boxBody.querySelector(".dtp-resize-handle.handle-bottom");
      if (!bottomHandle) {
        bottomHandle = document.createElement("div");
        bottomHandle.className = "dtp-resize-handle handle-bottom";
        bottomHandle.innerHTML = '<div class="handle-bar-pill"></div><span class="handle-label">▼ 본문 종료선 ↕ (행수 조절)</span>';
        boxBody.appendChild(bottomHandle);
      }

      let leftHandle = boxBody.querySelector(".dtp-resize-handle.handle-left");
      if (!leftHandle) {
        leftHandle = document.createElement("div");
        leftHandle.className = "dtp-resize-handle handle-left";
        leftHandle.innerHTML = '<div class="handle-bar-pill"></div><span class="handle-label">◀ 좌측 여백 ↔</span>';
        boxBody.appendChild(leftHandle);
      }

      let rightHandle = boxBody.querySelector(".dtp-resize-handle.handle-right");
      if (!rightHandle) {
        rightHandle = document.createElement("div");
        rightHandle.className = "dtp-resize-handle handle-right";
        rightHandle.innerHTML = '<div class="handle-bar-pill"></div><span class="handle-label">우측 여백 ↔ ▶</span>';
        boxBody.appendChild(rightHandle);
      }

      const self = this;
      const pageData = cfg.pages[pageIdx] || (cfg._all_pages_pool && cfg._all_pages_pool[pageIdx]);
      if (!pageData) return;

      const pt = parseFloat(cfg.font_size_pt) || 12;
      const lh = parseFloat(cfg.line_height_ratio) || 1.5;
      const fontPx = (pt / 12.0) * 15.2;
      const linePx = fontPx * lh;

      // 1) 상단 핸들 드래그: 본문 시작선 위치(top_offset) 조절
      topHandle.onmousedown = function(e) {
        e.preventDefault();
        e.stopPropagation();

        const startY = e.clientY;
        const initialOffset = parseInt(pageData.top_offset, 10) || 0;
        let currOffset = initialOffset;

        boxBody.classList.add("is-resizing");
        document.body.style.cursor = "ns-resize";

        const label = topHandle.querySelector(".handle-label");
        if (label) {
          label.textContent = `▲ 본문 시작선 내림: +${initialOffset}px`;
          label.style.display = "block";
        }

        function onMouseMove(ev) {
          const deltaY = ev.clientY - startY;
          currOffset = Math.max(0, Math.min(240, Math.round(initialOffset + deltaY)));
          boxBody.style.setProperty("margin-top", `${currOffset}px`, "important");

          if (label) {
            label.textContent = `▲ 본문 시작선 내림: +${currOffset}px`;
          }
        }

        function onMouseUp(ev) {
          window.removeEventListener("mousemove", onMouseMove, true);
          window.removeEventListener("mouseup", onMouseUp, true);
          boxBody.classList.remove("is-resizing");
          document.body.style.cursor = "";

          if (label) {
            label.textContent = "▲ 본문 시작선 ↕";
            label.style.display = "";
          }

          if (currOffset !== initialOffset) {
            self.pushUndoState();
            pageData.top_offset = currOffset;
            if (work.layout_config && Array.isArray(work.layout_config.pages) && work.layout_config.pages[pageIdx]) {
              work.layout_config.pages[pageIdx].top_offset = currOffset;
            }
            self.renderSpread(self.currentWorkIndex, self.currentSpreadPart, true);
            self.saveLayoutConfigToServer(work.episode_no, cfg);
            if (window.showToast) {
              window.showToast(`📏 ${pageIdx + 1}면 본문 시작선이 ${currOffset}px로 조절되었습니다.`, "info");
            }
          }
        }

        window.addEventListener("mousemove", onMouseMove, true);
        window.addEventListener("mouseup", onMouseUp, true);
      };

      // 2) 하단 핸들 드래그: 본문 종료선 위치 및 수용 행수(max_lines) 조절 (하단 안전선 칼같이 절대 준수)
      bottomHandle.onmousedown = function(e) {
        e.preventDefault();
        e.stopPropagation();

        const startY = e.clientY;
        const startHeight = boxBody.offsetHeight;
        
        // 인쇄안전선(safe-boundary) 바닥 절대 좌표와 본문 상단 좌표 측정
        const safeBoundary = boxBody.closest(".dtp-safe-boundary") || boxBody.parentElement;
        const boundaryRect = safeBoundary.getBoundingClientRect();
        const boxRect = boxBody.getBoundingClientRect();
        
        // 본문 상자가 하단 안전선을 단 1px도 뚫고 내려갈 수 없도록 상한선 계산
        const maxAllowedHeight = Math.max(80, Math.floor(boundaryRect.bottom - boxRect.top));
        const maxSafeLines = Math.max(3, Math.floor((maxAllowedHeight - 28) / linePx));
        
        const currentBudget = pageData.max_lines || maxSafeLines;
        let newLines = currentBudget;
        let currHeight = startHeight;

        boxBody.classList.add("is-resizing");
        document.body.style.cursor = "ns-resize";

        const label = bottomHandle.querySelector(".handle-label");
        if (label) {
          label.textContent = `▼ 본문 수용 목표: ${currentBudget}행 (안전선 한도)`;
          label.style.display = "block";
        }

        function onMouseMove(ev) {
          const deltaY = ev.clientY - startY;
          // 하단 안전선 바닥에 닿으면 더 이상 늘어나지 않도록 maxAllowedHeight로 엄격히 제한!
          currHeight = Math.max(80, Math.min(maxAllowedHeight, Math.round(startHeight + deltaY)));
          const deltaLines = Math.round((currHeight - startHeight) / linePx);
          newLines = Math.max(3, Math.min(maxSafeLines, currentBudget + deltaLines));
          
          boxBody.style.setProperty("height", `${currHeight}px`, "important");
          boxBody.style.setProperty("flex", "none", "important");

          if (label) {
            const isAtMax = (currHeight >= maxAllowedHeight);
            const maxHint = isAtMax ? " [안전선 한계 도달]" : "";
            label.textContent = `▼ 본문 수용 목표: ${newLines}행${maxHint}`;
          }
        }

        function onMouseUp(ev) {
          window.removeEventListener("mousemove", onMouseMove, true);
          window.removeEventListener("mouseup", onMouseUp, true);
          boxBody.classList.remove("is-resizing");
          document.body.style.cursor = "";

          if (label) {
            label.textContent = "▼ 본문 종료선 ↕ (행수 조절)";
            label.style.display = "";
          }

          // 만약 안전선 바닥 한계까지 끌어올렸다면 max_lines를 null로 복원하여 기본 flex 안착
          const targetLines = (currHeight >= maxAllowedHeight - 4) ? null : newLines;

          if (targetLines !== (pageData.max_lines || null)) {
            self.pushUndoState();
            pageData.max_lines = targetLines;
            if (work.layout_config && Array.isArray(work.layout_config.pages) && work.layout_config.pages[pageIdx]) {
              work.layout_config.pages[pageIdx].max_lines = targetLines;
            }
            self.renderSpread(self.currentWorkIndex, self.currentSpreadPart, true);
            self.saveLayoutConfigToServer(work.episode_no, cfg);
            if (window.showToast) {
              const msg = targetLines ? `📏 ${pageIdx + 1}면 본문 수용 용량이 ${targetLines}행으로 조절되었습니다.` : `✅ ${pageIdx + 1}면 본문이 하단 안전선에 꼭 맞게 안착되었습니다.`;
              window.showToast(msg, "info");
            }
          }
        }

        window.addEventListener("mousemove", onMouseMove, true);
        window.addEventListener("mouseup", onMouseUp, true);
      };

      // 3) 좌측 핸들 드래그: 본문 좌측 여백(left_offset) 조절 (우측 경계 고정 & 좌측 폭 리사이즈)
      leftHandle.onmousedown = function(e) {
        e.preventDefault();
        e.stopPropagation();

        const startX = e.clientX;
        const initialLeft = parseInt(pageData.left_offset, 10) || 0;
        const currentRight = parseInt(pageData.right_offset, 10) || 0;
        let currLeft = initialLeft;

        const safeBoundary = boxBody.closest(".dtp-safe-boundary") || boxBody.parentElement;
        const boundaryW = safeBoundary ? safeBoundary.clientWidth : 380;
        const maxLeft = Math.max(0, Math.floor(boundaryW * 0.60 - currentRight));

        boxBody.classList.add("is-resizing");
        document.body.style.cursor = "ew-resize";

        const label = leftHandle.querySelector(".handle-label");
        if (label) {
          label.textContent = `◀ 좌측 여백: +${initialLeft}px`;
          label.style.display = "block";
        }

        function onMouseMove(ev) {
          const deltaX = ev.clientX - startX;
          currLeft = Math.max(0, Math.min(maxLeft, Math.round(initialLeft + deltaX)));
          boxBody.style.setProperty("margin-left", `${currLeft}px`, "important");
          boxBody.style.setProperty("width", `calc(100% - ${currLeft + currentRight}px)`, "important");

          if (label) {
            label.textContent = `◀ 좌측 여백: +${currLeft}px`;
          }
        }

        function onMouseUp() {
          window.removeEventListener("mousemove", onMouseMove, true);
          window.removeEventListener("mouseup", onMouseUp, true);
          boxBody.classList.remove("is-resizing");
          document.body.style.cursor = "";

          if (label) {
            label.textContent = "◀ 좌측 여백 ↔";
            label.style.display = "";
          }

          if (currLeft !== initialLeft) {
            self.pushUndoState();
            pageData.left_offset = currLeft;
            if (work.layout_config && Array.isArray(work.layout_config.pages) && work.layout_config.pages[pageIdx]) {
              work.layout_config.pages[pageIdx].left_offset = currLeft;
            }
            self.renderSpread(self.currentWorkIndex, self.currentSpreadPart, true);
            self.saveLayoutConfigToServer(work.episode_no, cfg);
            if (window.showToast) {
              window.showToast(`📏 ${pageIdx + 1}면 본문 좌측 여백이 ${currLeft}px로 조절되었습니다.`, "info");
            }
          }
        }

        window.addEventListener("mousemove", onMouseMove, true);
        window.addEventListener("mouseup", onMouseUp, true);
      };

      // 4) 우측 핸들 드래그: 본문 우측 여백(right_offset) 조절 (좌측 경계 고정 & 우측 폭 리사이즈)
      rightHandle.onmousedown = function(e) {
        e.preventDefault();
        e.stopPropagation();

        const startX = e.clientX;
        const currentLeft = parseInt(pageData.left_offset, 10) || 0;
        const initialRight = parseInt(pageData.right_offset, 10) || 0;
        let currRight = initialRight;

        const safeBoundary = boxBody.closest(".dtp-safe-boundary") || boxBody.parentElement;
        const boundaryW = safeBoundary ? safeBoundary.clientWidth : 380;
        const maxRight = Math.max(0, Math.floor(boundaryW * 0.60 - currentLeft));

        boxBody.classList.add("is-resizing");
        document.body.style.cursor = "ew-resize";

        const label = rightHandle.querySelector(".handle-label");
        if (label) {
          label.textContent = `우측 여백: +${initialRight}px ▶`;
          label.style.display = "block";
        }

        function onMouseMove(ev) {
          const deltaX = ev.clientX - startX;
          // 마우스를 왼쪽으로 밀면 우측 여백이 늘어남 (-deltaX)
          currRight = Math.max(0, Math.min(maxRight, Math.round(initialRight - deltaX)));
          boxBody.style.setProperty("margin-right", `${currRight}px`, "important");
          boxBody.style.setProperty("width", `calc(100% - ${currentLeft + currRight}px)`, "important");

          if (label) {
            label.textContent = `우측 여백: +${currRight}px ▶`;
          }
        }

        function onMouseUp() {
          window.removeEventListener("mousemove", onMouseMove, true);
          window.removeEventListener("mouseup", onMouseUp, true);
          boxBody.classList.remove("is-resizing");
          document.body.style.cursor = "";

          if (label) {
            label.textContent = "우측 여백 ↔ ▶";
            label.style.display = "";
          }

          if (currRight !== initialRight) {
            self.pushUndoState();
            pageData.right_offset = currRight;
            if (work.layout_config && Array.isArray(work.layout_config.pages) && work.layout_config.pages[pageIdx]) {
              work.layout_config.pages[pageIdx].right_offset = currRight;
            }
            self.renderSpread(self.currentWorkIndex, self.currentSpreadPart, true);
            self.saveLayoutConfigToServer(work.episode_no, cfg);
            if (window.showToast) {
              window.showToast(`📏 ${pageIdx + 1}면 본문 우측 여백이 ${currRight}px로 조절되었습니다.`, "info");
            }
          }
        }

        window.addEventListener("mousemove", onMouseMove, true);
        window.addEventListener("mouseup", onMouseUp, true);
      };
    }

    renderSinglePage(side, pageIdx, cfg, work, textFlowMap, overflowFlags) {
      const pageData = cfg.pages[pageIdx] || { usage: "text", role: "continue", image_file: "" };
      const pageNum = pageIdx + 1;
      const capSide = (side === 'left') ? 'Left' : 'Right';

      // 1) 면 번호 표시
      const lblNum = document.getElementById(`lblPage${capSide}Num`);
      if (lblNum) lblNum.textContent = `${pageNum}면(${side === 'left' ? '좌' : '우'})`;

      const lblFolio = document.getElementById(`lblBookFolio${capSide}`);
      if (lblFolio) lblFolio.textContent = `${pageNum}`;

      // 2) 드롭다운 셀렉터 동기화
      const selUsage = document.getElementById(`selectPageUsage${capSide}`);
      if (selUsage) selUsage.value = pageData.usage;

      const selRole = document.getElementById(`selectPageRole${capSide}`);
      if (selRole) {
        selRole.value = pageData.role;
        if (pageData.usage === 'image' || pageData.usage === 'blank') {
          selRole.disabled = true;
          selRole.style.opacity = '0.5';
        } else {
          selRole.disabled = false;
          selRole.style.opacity = '1.0';
        }
      }

      // 3) Layer 1: 그림 레이어 렌더링
      this.renderImageLayer(side, pageData, work, pageNum);

      // 4) Layer 2: 글 레이어 렌더링
      this.renderTextLayer(side, pageData, work, cfg, pageIdx, textFlowMap);

      // 5) 하단 초과/이어짐 배지 표시
      const overflowBadge = document.getElementById(`dtpOverflow${capSide}`);
      if (overflowBadge) {
        if (overflowFlags && overflowFlags[pageIdx]) {
          const nextPageNum = pageNum + 1;
          const nextPart = Math.ceil(nextPageNum / 2);
          overflowBadge.innerHTML = `⚠️ 본문 초과 ➔ ${nextPageNum}면으로 자동 이어짐 <span style="text-decoration:underline; margin-left:4px; cursor:pointer;">[${nextPart}부 보기]</span>`;
          overflowBadge.style.pointerEvents = "auto";
          overflowBadge.style.cursor = "pointer";
          overflowBadge.onclick = () => this.switchSpreadPart(nextPart);
          showElem(overflowBadge, "block");
        } else {
          hideElem(overflowBadge);
        }
      }
    }

    /**
     * Layer 1 (그림 레이어) 렌더링
     */
        /**
     * 그림 분할 레이아웃 변경 (single, split_vertical, split_horizontal, main_detail)
     */
    onImageLayoutChange(side, layout) {
      const work = this.getCurrentWork();
      if (!work) return;
      const cfg = this.getNormalizedConfig(work);
      const pageIdx = (this.currentSpreadPart - 1) * 2 + (side === 'left' ? 0 : 1);
      const pageData = cfg.pages[pageIdx];
      if (!pageData) return;

      this.pushUndoState();
      pageData.image_layout = layout;
      if (work.layout_config && Array.isArray(work.layout_config.pages) && work.layout_config.pages[pageIdx]) {
        work.layout_config.pages[pageIdx].image_layout = layout;
      }
      this.renderSpread(this.currentWorkIndex, this.currentSpreadPart, true);
      this.saveLayoutConfigToServer(work.episode_no, cfg);
      if (window.showToast) {
        const layoutNames = {
          single: "1장 전체",
          split_vertical: "상·하 2단 분할",
          split_horizontal: "좌·우 2단 분할",
          main_detail: "메인+소품 분할"
        };
        window.showToast(`🖼️ ${pageIdx + 1}면 그림 배치가 [${layoutNames[layout] || layout}]로 변경되었습니다.`, "info");
      }
    }

    /**
     * 분할 프레임별 개별 이미지 교체
     */
    openSlotImageFrameManager(side, frameIndex) {
      window.activeImageTargetSide = side;
      window.activeImageTargetFrame = frameIndex;
      if (typeof openSlotImageManager === 'function') {
        openSlotImageManager(side);
      }
    }

    renderImageLayer(side, pageData, work, pageNum) {
      const capSide = (side === 'left') ? 'Left' : 'Right';
      const layerImage = document.getElementById(`dtpLayerImage${capSide}`);
      const imgElem = document.getElementById(`dtpImg${capSide}`);
      const placeholder = document.getElementById(`dtpPlaceholder${capSide}`);
      const blankElem = document.getElementById(`dtpBlank${capSide}`);
      const btnArt = document.getElementById(`btnArt${capSide}`);
      const selLayout = document.getElementById(`selectImgLayout${capSide}`);

      if (!layerImage) return;

      // 1) 툴바 버튼 및 분할 드롭다운 표시 제어
      const hasImageMode = (pageData.usage === 'image' || pageData.usage === 'image_text');
      if (btnArt) {
        if (hasImageMode) showElem(btnArt, 'inline-flex');
        else hideElem(btnArt);
      }
      if (selLayout) {
        if (hasImageMode) {
          hideElem(selLayout);
          selLayout.value = pageData.image_layout || 'single';
        } else {
          hideElem(selLayout);
        }
      }

      // 본문 전용일 때 그림 레이어 완전 숨김
      if (pageData.usage === 'text') {
        hideElem(layerImage);
        hideElem(imgElem);
        hideElem(placeholder);
        hideElem(blankElem);
        layerImage.querySelectorAll('.dtp-image-frame').forEach(el => el.remove());
        return;
      }

      showElem(layerImage, 'flex');

      if (hasImageMode) {
        hideElem(blankElem);

        const layout = pageData.image_layout || 'single';
        // 기존 동적 프레임 청소
        layerImage.querySelectorAll('.dtp-image-frame').forEach(el => el.remove());
        layerImage.className = 'dtp-layer-image';

        let imgFile1 = pageData.image_file;
        if (!imgFile1) {
          if (pageNum === 1) imgFile1 = work.image_file;
          else if (pageNum === 3) imgFile1 = work.image_file_2 || work.image_file;
        }

        let imgFile2 = pageData.image_file_b || work.image_file_2 || work.image_file || imgFile1;

        if (layout === 'single') {
          // [기본] 1장 전체 그림
          if (imgFile1) {
            const baseCleanPath = "/" + String(imgFile1).replace(/^(\.\/|\/)+/, '');
            const cleanPath = this._imgCacheBust ? `${baseCleanPath}?t=${this._imgCacheBust}` : baseCleanPath;
            if (imgElem) {
              if (imgElem.getAttribute("data-clean-path") !== cleanPath) {
                imgElem.setAttribute("data-clean-path", cleanPath);
                imgElem.src = cleanPath;
              }
              showElem(imgElem, 'block');
            }
            hideElem(placeholder);
          } else {
            hideElem(imgElem);
            showElem(placeholder, 'flex');
          }
        } else {
          // [2단 분할 레이아웃: split_vertical, split_horizontal, main_detail]
          hideElem(imgElem);
          hideElem(placeholder);
          layerImage.classList.add(`layout-${layout}`);

          const cleanPath1 = imgFile1 ? ("/" + String(imgFile1).replace(/^(\.\/|\/)+/, '')) : "";
          const cleanPath2 = imgFile2 ? ("/" + String(imgFile2).replace(/^(\.\/|\/)+/, '')) : "";

          // 1번 프레임
          const frame1 = document.createElement("div");
          frame1.className = `dtp-image-frame ${layout === 'main_detail' ? 'frame-main' : ''}`;
          frame1.innerHTML = `
            <span class="frame-tag">${layout === 'main_detail' ? '메인 삽화' : '1번 그림'}</span>
            ${cleanPath1 ? `<img src="${cleanPath1}" alt="1번 삽화">` : '<div style="color:#A89F91; font-size:0.78rem;">그림을 등록하세요</div>'}
            <button type="button" class="btn-frame-change" onclick="dtpEditor.openSlotImageFrameManager('${side}', 1)">🎨 1번 그림 변경</button>
          `;

          // 2번 프레임
          const frame2 = document.createElement("div");
          frame2.className = `dtp-image-frame ${layout === 'main_detail' ? 'frame-detail' : ''}`;
          frame2.innerHTML = `
            <span class="frame-tag">${layout === 'main_detail' ? '보조 소품 컷' : '2번 그림'}</span>
            ${cleanPath2 ? `<img src="${cleanPath2}" alt="2번 삽화">` : '<div style="color:#A89F91; font-size:0.78rem;">그림을 등록하세요</div>'}
            <button type="button" class="btn-frame-change" onclick="dtpEditor.openSlotImageFrameManager('${side}', 2)">🎨 2번 그림 변경</button>
          `;

          layerImage.appendChild(frame1);
          layerImage.appendChild(frame2);
        }
      } else if (pageData.usage === 'blank') {
        layerImage.className = 'dtp-layer-image';
        layerImage.querySelectorAll('.dtp-image-frame').forEach(el => el.remove());
        hideElem(imgElem);
        hideElem(placeholder);
        showElem(blankElem, 'flex');
      }
    }

    renderTextLayer(side, pageData, work, cfg, pageIdx, textFlowMap) {
      const capSide = (side === 'left') ? 'Left' : 'Right';
      const layerText = document.getElementById(`dtpLayerText${capSide}`);
      const boxTitle = document.getElementById(`dtpBoxTitle${capSide}`);
      const boxBody = document.getElementById(`dtpBoxBody${capSide}`);
      const titleElem = document.getElementById(`dtpTitle${capSide}`);
      const authorElem = document.getElementById(`dtpAuthor${capSide}`);
      const bodyElem = document.getElementById(`dtpBody${capSide}`);
      const hanjiPanel = document.getElementById(`dtpHanji${capSide}`);

      if (!layerText) return;

      // 글이 없는 모드 (전면 그림, 문학적 여백, 글 없음)
      if (pageData.usage === 'image' || pageData.usage === 'blank' || pageData.role === 'none') {
        hideElem(layerText);
        hideElem(boxTitle);
        hideElem(boxBody);
        hideElem(hanjiPanel);
        return;
      }

      showElem(layerText, 'block');

      // 한지 가독성 패널 연동 ([그림+글] 모드일 때만 활성화)
      if (hanjiPanel) {
        if (pageData.usage === 'image_text') {
          showElem(hanjiPanel, 'block');
          const op = cfg.backdrop_opacity !== undefined ? cfg.backdrop_opacity : 0.85;
          hanjiPanel.style.backgroundColor = `rgba(254, 252, 248, ${op})`;
        } else {
          hideElem(hanjiPanel);
        }
      }

      // 글자색 모드 적용
      const isLightText = (cfg.text_color_mode === 'light' && pageData.usage === 'image_text');
      layerText.classList.toggle('text-color-light', isLightText);

      // 1) [제목+지은이 상자] - 상단 안전선 준수 (role이 'start'일 때 실재, 'continue'일 때 64px 투명 플레이스홀더로 완벽 정렬)
      if (pageData.role === 'start') {
        boxTitle.classList.remove('dtp-title-placeholder');
        showElem(boxTitle, 'block');
        if (titleElem) {
          titleElem.innerText = work.title || '무제';
          titleElem.onblur = () => {
            const newTitle = titleElem.innerText.trim();
            if (newTitle && newTitle !== work.title) {
              this.pushUndoState();
              work.title = newTitle;
              this.syncToolbarUI(work, cfg, Math.ceil(cfg.page_count / 2), {});
              this.saveLayoutConfigToServer(work.episode_no, cfg);
            }
          };
        }
        if (authorElem) {
          const works = this.getWorksList();
          const distinctWorkAuthors = new Set(works.map(w => (w.author || '').trim()).filter(Boolean));
          const isCollabBook = (window.currentStatus?.project?.author_type === 'collab') || (distinctWorkAuthors.size > 1);
          const workAuthor = (work.author || '').trim();

          if (isCollabBook && workAuthor) {
            authorElem.innerText = workAuthor;
            showElem(authorElem, 'block');
          } else {
            authorElem.innerText = workAuthor;
            hideElem(authorElem);
          }
        }
      } else if (pageData.role === 'continue') {
        // 시 이어짐 면: 제목 공간(64px)을 그대로 유지하는 투명 플레이스홀더로 본문 시작선 완벽 통일!
        boxTitle.classList.add('dtp-title-placeholder');
        showElem(boxTitle, 'block');
        if (titleElem) titleElem.innerText = '';
        if (authorElem) hideElem(authorElem);
      } else {
        boxTitle.classList.remove('dtp-title-placeholder');
        hideElem(boxTitle);
      }

      // 2) [본문 상자] - 상단/하단 핸들 및 높이 조절 지원
      if (boxBody && bodyElem) {
        showElem(boxBody, 'flex');

        // 상단 가이드 및 여백: 시 이어짐(continue)일 때 상단 여백 보정
        if (pageData.role === 'continue') {
          boxBody.classList.add('dtp-role-continue');
        } else {
          boxBody.classList.remove('dtp-role-continue');
        }

        // 상단 오프셋 적용 (상단 시작선) - !important로 확실히 보장
        const topOffset = pageData.top_offset || 0;
        if (topOffset > 0) {
          boxBody.style.setProperty("margin-top", `${topOffset}px`, "important");
        } else {
          boxBody.style.removeProperty("margin-top");
        }

        // 좌/우 오프셋 및 실제 가변 폭(width) 동기화 (진짜 리사이즈 보장)
        const leftOffset = parseInt(pageData.left_offset, 10) || 0;
        const rightOffset = parseInt(pageData.right_offset, 10) || 0;

        if (leftOffset > 0) {
          boxBody.style.setProperty("margin-left", `${leftOffset}px`, "important");
        } else {
          boxBody.style.removeProperty("margin-left");
        }

        if (rightOffset > 0) {
          boxBody.style.setProperty("margin-right", `${rightOffset}px`, "important");
        } else {
          boxBody.style.removeProperty("margin-right");
        }

        if (leftOffset > 0 || rightOffset > 0) {
          boxBody.style.setProperty("width", `calc(100% - ${leftOffset + rightOffset}px)`, "important");
        } else {
          boxBody.style.setProperty("width", "100%", "important");
        }

        // 하단 커스텀 높이 적용 (하단 안전선 절대 준수) - !important로 확실히 보장
        if (pageData.max_lines) {
          const pt = parseFloat(cfg.font_size_pt) || 12;
          const lh = parseFloat(cfg.line_height_ratio) || 1.5;
          const fontPx = (pt / 12.0) * 15.2;
          const linePx = fontPx * lh;
          
          // 부모 안전선 바닥 경계 계산
          const safeBoundary = boxBody.closest(".dtp-safe-boundary") || boxBody.parentElement;
          const boundaryH = safeBoundary ? safeBoundary.clientHeight : 520;
          const titleBox = safeBoundary ? safeBoundary.querySelector(".dtp-box-title") : null;
          const titleH = (titleBox && titleBox.offsetHeight) ? titleBox.offsetHeight : 64;
          const maxAllowedH = Math.max(80, boundaryH - titleH - 12 - topOffset);
          
          const customH = Math.min(maxAllowedH, Math.max(80, Math.round(pageData.max_lines * linePx + 28)));
          boxBody.style.setProperty("height", `${customH}px`, "important");
          boxBody.style.setProperty("flex", "none", "important");
        } else {
          boxBody.style.removeProperty("height");
          boxBody.style.setProperty("flex", "1 1 auto", "important");
        }

        // 핸들 이벤트 주입
        this.attachResizeHandles(boxBody, side, pageIdx, cfg, work);

        const pt = cfg.font_size_pt || 12;
        const remSize = (pt / 12.0) * 0.95;
        bodyElem.style.fontSize = `${remSize.toFixed(2)}rem`;
        bodyElem.style.lineHeight = `${cfg.line_height_ratio || 1.5}`;
        bodyElem.style.textAlign = cfg.text_align || 'left';

        if (pageData.role === 'independent') {
          const customTxt = pageData.custom_text || "독립 자유글을 이곳에 입력하세요.";
          bodyElem.innerHTML = customTxt.split("\n").map(line => `<p class="poem-line">${line || '&nbsp;'}</p>`).join('');
          bodyElem.onblur = () => {
            pageData.custom_text = bodyElem.innerText;
            this.saveLayoutConfigToServer(work.episode_no, cfg);
          };
        } else {
          const lines = textFlowMap[pageIdx] || [];
          if (lines.length > 0) {
            bodyElem.innerHTML = lines.map(line => {
              const trimmed = (line || "").replace(/[\u00a0\xa0]+/g, "").trimEnd();
              return `<p class="poem-line${!trimmed.trim() ? ' empty-line' : ''}">${trimmed.trim() || '<br>'}</p>`;
            }).join('');
          } else if (pageData.role === 'continue' && pageIdx > 0) {
            bodyElem.innerHTML = `<p class="poem-placeholder" style="color:#B5A898; font-style:italic; font-size:0.84rem;">(앞 면에서 본문 글이 마무리되었습니다 — 여백 면)</p>`;
          } else {
            bodyElem.innerHTML = `<p class="poem-placeholder" style="color:#A89F91; font-style:italic;">본문 글이 여기에 배치됩니다.</p>`;
          }
          bodyElem.onblur = () => {
            this.onBodyEdited(pageIdx, bodyElem, textFlowMap);
          };
        }
      }
    }

    /**
     * 본문 직접 편집 완료(blur) 시 전체 시 본문 병합 및 재계산
     */
    onBodyEdited(editedPageIdx, bodyElemOrText, textFlowMap) {
      const work = this.getCurrentWork();
      if (!work) return;

      const cfg = this.getNormalizedConfig(work);
      const updatedChunks = [];
      for (let i = 0; i < 6; i++) {
        if (i === editedPageIdx) {
          let editedLines = [];
          // DOM 요소인 경우 각 .poem-line의 텍스트를 정확히 1줄씩 추출 (브라우저 innerText의 <p>\n\n 중복 버그 원천 방지)
          if (bodyElemOrText && typeof bodyElemOrText === 'object' && bodyElemOrText.querySelectorAll) {
            const pElems = Array.from(bodyElemOrText.querySelectorAll(".poem-line"));
            if (pElems.length > 0) {
              editedLines = pElems.map(p => {
                if (p.classList.contains("empty-line")) return "";
                const text = p.textContent.replace(/[\u00a0\xa0]+/g, "").trimEnd();
                return text;
              });
            }
          }
          if (editedLines.length === 0 && typeof bodyElemOrText === 'string') {
            editedLines = bodyElemOrText
              .replace(/\r\n/g, "\n")
              .replace(/[\u00a0\xa0]+/g, "")
              .split("\n")
              .map(l => l.trimEnd());
          }

          if (editedLines.length > 0 && editedLines[0] !== "본문 글이 여기에 배치됩니다.") {
            updatedChunks.push(editedLines.join("\n"));
          }
        } else if (textFlowMap[i] && textFlowMap[i].length > 0) {
          updatedChunks.push(textFlowMap[i].join("\n"));
        }
      }

      let mergedPoem = updatedChunks.join("\n").trim();
      // 3개 이상의 연속 빈 줄은 연 구분(빈 줄 1개, \n\n)으로 깔끔하게 정돈
      mergedPoem = mergedPoem.replace(/\n{3,}/g, "\n\n");

      if (mergedPoem !== (work.poem_body || "").trim()) {
        this.pushUndoState();
        work.poem_body = mergedPoem;
        this.renderSpread(this.currentWorkIndex, this.currentSpreadPart, true);
        this.saveLayoutConfigToServer(work.episode_no, work.layout_config || cfg);
      }
    }

    /**
     * 작품 넘기기 (상단 ◀ 이전 / 다음 ▶ 버튼)
     */
    navigateWork(delta) {
      const works = this.getWorksList();
      if (works.length === 0) return;
      let next = this.currentWorkIndex + delta;
      if (next < 0) {
        if (window.showToast) window.showToast("시화집의 첫 번째 작품입니다.", "info");
        return;
      }
      if (next >= works.length) {
        if (window.showToast) window.showToast("시화집의 마지막 작품입니다.", "info");
        return;
      }
      this.currentWorkIndex = next;
      window.currentWorkIndex = next;
      if (typeof currentWorkIndex !== 'undefined') {
        currentWorkIndex = next;
      }
      this.renderSpread(next, 1, false);
    }

    /**
     * 페이지 넘기기 (하단 ◀ 이전 페이지 / 다음 페이지 ▶ 버튼)
     */
    navigatePage(delta) {
      const work = this.getCurrentWork();
      if (!work) return;
      const cfg = this.getNormalizedConfig(work);
      const totalParts = Math.max(1, Math.ceil(cfg.page_count / 2));
      const curPart = this.currentSpreadPart || 1;

      if (delta > 0) {
        // [다음 페이지]
        if (curPart < totalParts) {
          // 현재 작품 내 다음 면(스프레드)으로 이동
          this.switchSpreadPart(curPart + 1);
        } else {
          // 마지막 면에서 다음을 누르면 다음 작품의 1면으로
          const works = this.getWorksList();
          if (this.currentWorkIndex + 1 < works.length) {
            this.currentWorkIndex += 1;
            window.currentWorkIndex = this.currentWorkIndex;
            this.renderSpread(this.currentWorkIndex, 1, false);
          } else if (window.showToast) {
            window.showToast("시화집의 마지막 페이지입니다.", "info");
          }
        }
      } else {
        // [이전 페이지]
        if (curPart > 1) {
          // 2부(3·4면)나 3부(5·6면)에서는 무조건 앞 면(1·2면 등)으로 이동!
          this.switchSpreadPart(curPart - 1);
        } else {
          // 1부(1·2면)에서 이전을 누르면 이전 작품의 마지막 면으로 자연스럽게 이동!
          if (this.currentWorkIndex - 1 >= 0) {
            this.currentWorkIndex -= 1;
            window.currentWorkIndex = this.currentWorkIndex;
            const prevWork = this.getCurrentWork();
            const prevCfg = this.getNormalizedConfig(prevWork);
            const prevMaxParts = Math.max(1, Math.ceil(prevCfg.page_count / 2));
            this.renderSpread(this.currentWorkIndex, prevMaxParts, false);
          } else if (window.showToast) {
            window.showToast("시화집의 첫 번째 페이지입니다.", "info");
          }
        }
      }
    }

    /**
     * 페이지 용도 변경 (image, text, image_text, blank)
     */
    onPageUsageChange(side, newUsage) {
      const work = this.getCurrentWork();
      if (!work) return;
      this.pushUndoState();

      const cfg = this.getNormalizedConfig(work);
      const pageIdx = (this.currentSpreadPart - 1) * 2 + (side === 'left' ? 0 : 1);
      const page = cfg.pages[pageIdx];

      page.usage = newUsage;
      if (newUsage === 'image' || newUsage === 'blank') {
        page.role = 'none';
      } else if ((newUsage === 'text' || newUsage === 'image_text') && page.role === 'none') {
        // 기존에 start 페이지가 있는지 확인
        const hasStart = cfg.pages.some((p, i) => i !== pageIdx && p.role === 'start' && (p.usage === 'text' || p.usage === 'image_text'));
        page.role = hasStart ? 'continue' : 'start';
      }

      cfg.slots[pageIdx] = newUsage;
      cfg.page_roles[pageIdx] = page.role;

      this.renderSpread(this.currentWorkIndex, this.currentSpreadPart, true);
      this.saveLayoutConfigToServer(work.episode_no, cfg);
    }

    /**
     * 글 유형 변경 (start, continue, independent, none)
     */
    onPageRoleChange(side, newRole) {
      const work = this.getCurrentWork();
      if (!work) return;
      this.pushUndoState();

      const cfg = this.getNormalizedConfig(work);
      const pageIdx = (this.currentSpreadPart - 1) * 2 + (side === 'left' ? 0 : 1);
      const page = cfg.pages[pageIdx];

      if (newRole === 'start') {
        const pool = cfg._all_pages_pool || cfg.pages;
        pool.forEach((p, idx) => {
          if (idx !== pageIdx && p.role === 'start') {
            p.role = 'continue';
            if (cfg.page_roles[idx]) cfg.page_roles[idx] = 'continue';
          }
        });
      }
      page.role = newRole;
      if (newRole !== 'none' && (page.usage === 'image' || page.usage === 'blank')) {
        page.usage = (page.usage === 'image') ? 'image_text' : 'text';
        cfg.slots[pageIdx] = page.usage;
      }
      cfg.page_roles[pageIdx] = newRole;

      this.renderSpread(this.currentWorkIndex, this.currentSpreadPart, true);
      this.saveLayoutConfigToServer(work.episode_no, cfg);
    }

    /**
     * 폰트 크기(pt) 변경
     */
    setFontSizePt(val) {
      const work = this.getCurrentWork();
      if (!work) return;
      const cfg = this.getNormalizedConfig(work);

      let targetPt = 12;
      if (val === "custom") {
        const input = prompt("본문 글자 크기를 pt 단위로 입력하세요 (8 ~ 24):", String(cfg.font_size_pt || 12));
        if (!input || isNaN(parseFloat(input))) {
          this.syncToolbarUI(work, cfg, Math.ceil(cfg.page_count / 2), {});
          return;
        }
        targetPt = Math.max(8, Math.min(24, parseFloat(input)));
      } else {
        targetPt = Math.max(8, Math.min(24, parseFloat(val) || 12));
      }

      this.pushUndoState();
      cfg.font_size_pt = targetPt;
      this.renderSpread(this.currentWorkIndex, this.currentSpreadPart, true);
      this.saveLayoutConfigToServer(work.episode_no, cfg);
    }

    /**
     * 줄간격 조절
     */
    adjustLineHeight(delta) {
      const work = this.getCurrentWork();
      if (!work) return;
      this.pushUndoState();

      const cfg = this.getNormalizedConfig(work);
      const curLh = parseFloat(cfg.line_height_ratio) || 1.5;
      const nextLh = Math.max(1.3, Math.min(2.6, Math.round((curLh + delta * 0.1) * 100) / 100));
      cfg.line_height_ratio = nextLh;

      this.renderSpread(this.currentWorkIndex, this.currentSpreadPart, true);
      this.saveLayoutConfigToServer(work.episode_no, cfg);
      if (window.showToast) {
        window.showToast(`본문 줄간격: ${nextLh.toFixed(2)}배`, "info");
      }
    }

    /**
     * 글자 크기 & 줄간격 초기화
     */
    resetTypography() {
      const work = this.getCurrentWork();
      if (!work) return;
      this.pushUndoState();

      const cfg = this.getNormalizedConfig(work);
      cfg.font_size_pt = 12;
      cfg.line_height_ratio = 1.5;

      this.renderSpread(this.currentWorkIndex, 1, true);
      this.saveLayoutConfigToServer(work.episode_no, cfg);
      if (window.showToast) {
        window.showToast("본문 글자 크기(12pt)와 줄간격(1.85)을 기본값으로 초기화했습니다.", "info");
      }
    }

    /**
     * 스프레드 부(Part) 전환 (1부 = 1·2면, 2부 = 3·4면, 3부 = 5·6면)
     */
    switchSpreadPart(part) {
      this.renderSpread(this.currentWorkIndex, part, false);
    }

    /**
     * 한지 투명도 실시간 조절 (기본값 85%)
     */
    setHanjiOpacity(val) {
      const work = this.getCurrentWork();
      if (!work) return;
      const opacity = parseFloat(val) / 100.0;
      const cfg = this.getNormalizedConfig(work);
      cfg.backdrop_opacity = opacity;

      ['Left', 'Right'].forEach(side => {
        const panel = document.getElementById(`dtpHanji${side}`);
        if (panel) {
          panel.style.backgroundColor = `rgba(254, 252, 248, ${opacity})`;
        }
      });

      const lbl = document.getElementById("lblDtpHanjiOpacityVal");
      if (lbl) lbl.textContent = `${Math.round(opacity * 100)}%`;

      clearTimeout(this._saveDebounce);
      this._saveDebounce = setTimeout(() => {
        this.saveLayoutConfigToServer(work.episode_no, cfg);
      }, 500);
    }

    /**
     * 글자색 반전 토글 (어두운 먹색 <-> 순백색)
     */
    toggleTextColor() {
      const work = this.getCurrentWork();
      if (!work) return;
      this.pushUndoState();

      const cfg = this.getNormalizedConfig(work);
      cfg.text_color_mode = (cfg.text_color_mode === 'light') ? 'dark' : 'light';

      this.renderSpread(this.currentWorkIndex, this.currentSpreadPart, false);
      this.saveLayoutConfigToServer(work.episode_no, cfg);
      if (window.showToast) {
        window.showToast(cfg.text_color_mode === 'light' ? "글자색: 순백색 적용 (그림 위 글 모드)" : "글자색: 먹색 적용", "info");
      }
    }

    /**
     * 빨간색 가이드선 토글
     */
    toggleGuides() {
      this.showGuides = !this.showGuides;
      this.applyGuidesVisibility();
      const btn = document.getElementById("btnToggleLayoutGuides");
      if (btn) {
        btn.innerHTML = this.showGuides ? "<span>🟥 가이드선 켬</span>" : "<span>⬜ 가이드선 끔</span>";
        btn.style.background = this.showGuides ? "#FFF5F5" : "#FFF";
        btn.style.color = this.showGuides ? "#C53030" : "#6E5340";
      }
    }

    applyGuidesVisibility() {
      document.querySelectorAll(".dtp-guide-box").forEach(box => {
        box.classList.toggle("guides-hidden", !this.showGuides);
      });
    }

    /**
     * 1:1 A5 실물 크기 줌 토글
     */
    toggleRealScale() {
      this.realScale = !this.realScale;
      const spread = document.getElementById("bookSpreadContainer");
      if (spread) {
        spread.classList.toggle("real-scale-100", this.realScale);
      }
      const btn = document.getElementById("btnToggleRealScale");
      if (btn) {
        btn.innerHTML = this.realScale ? "<span>🔍 화면 맞춤</span>" : "<span>🔍 실물 100%</span>";
      }
    }

    /**
     * Undo / Redo 스택
     */
    pushUndoState() {
      const work = this.getCurrentWork();
      if (!work) return;
      const cleanCfg = this.getCleanConfigForSave(work.layout_config || {});
      this.undoStack.push(cleanCfg);
      if (this.undoStack.length > this.maxUndoSteps) {
        this.undoStack.shift();
      }
      this.redoStack = [];
      this.updateUndoRedoButtons();
    }

    undo() {
      if (this.undoStack.length === 0) return;
      const work = this.getCurrentWork();
      if (!work) return;

      const currentState = this.getCleanConfigForSave(work.layout_config || {});
      this.redoStack.push(currentState);

      const prevState = this.undoStack.pop();
      work.layout_config = prevState;
      this.renderSpread(this.currentWorkIndex, this.currentSpreadPart, false);
      this.saveLayoutConfigToServer(work.episode_no, prevState);
      this.updateUndoRedoButtons();
      if (window.showToast) window.showToast("이전 조판 상태로 되돌렸습니다.", "info");
    }

    redo() {
      if (this.redoStack.length === 0) return;
      const work = this.getCurrentWork();
      if (!work) return;

      const currentState = this.getCleanConfigForSave(work.layout_config || {});
      this.undoStack.push(currentState);

      const nextState = this.redoStack.pop();
      work.layout_config = nextState;
      this.renderSpread(this.currentWorkIndex, this.currentSpreadPart, false);
      this.saveLayoutConfigToServer(work.episode_no, nextState);
      this.updateUndoRedoButtons();
      if (window.showToast) window.showToast("되돌린 조판을 다시 실행했습니다.", "info");
    }

    updateUndoRedoButtons() {
      const btnUndo = document.getElementById("btnDtpUndo");
      const btnRedo = document.getElementById("btnDtpRedo");
      if (btnUndo) btnUndo.disabled = (this.undoStack.length === 0);
      if (btnRedo) btnRedo.disabled = (this.redoStack.length === 0);
    }

    getCleanConfigForSave(cfg) {
      const copy = JSON.parse(JSON.stringify(cfg || {}));
      delete copy._all_pages_pool;
      return copy;
    }

    /**
     * 백엔드 API 서버(/api/save_work_layout_config)에 비동기 저장
     */
    async saveLayoutConfigToServer(episodeNo, layoutConfig) {
      if (!episodeNo) return false;
      const payloadCfg = this.getCleanConfigForSave(layoutConfig);
      const curWork = this.getCurrentWork();
      const bodyPayload = {
        episode_no: episodeNo,
        layout_config: payloadCfg
      };
      if (curWork && curWork.episode_no === episodeNo) {
        if (curWork.title) bodyPayload.title = curWork.title;
        if (typeof curWork.poem_body === 'string') bodyPayload.poem_body = curWork.poem_body;
      }
      try {
        const resp = await fetch("/api/save_work_layout_config", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(bodyPayload)
        });
        if (!resp.ok) {
          console.error("[DTP Core] 조판 설정 저장 실패:", resp.statusText);
          return false;
        }
        return true;
      } catch (err) {
        console.error("[DTP Core] 저장 통신 오류:", err);
        return false;
      }
    }

    /**
     * [조판 완료] 버튼 클릭 시 현재 작품 설정 영구 저장
     */
    async finishAndSaveLayout() {
      const work = this.getCurrentWork();
      if (!work) return;
      const cfg = this.getNormalizedConfig(work);
      const ok = await this.saveLayoutConfigToServer(work.episode_no, cfg);
      if (ok && window.showToast) {
        window.showToast(`✅ [${work.episode_no}] 「${work.title}」 (${cfg.page_count}쪽) 조판 설정이 완료·저장되었습니다!`, "success");
      }
    }
  }

  // 전역 인스턴스 등록
  const coreInstance = new DtpEditorCore();
  window.dtpEditor = coreInstance;
  window.DtpEditorCore = DtpEditorCore;

  // 기존 레거시 함수 전면 브리지
  window.navigateWork = function(delta) {
    window.dtpEditor.navigateWork(delta);
  };
  window.navigatePage = function(delta) {
    window.dtpEditor.navigatePage(delta);
  };
  window.renderBookSpread = function(index) {
    window.dtpEditor.renderSpread(index, window.currentSpreadPart || 1, false);
  };
  window.onSelectWorkChange = function(val) {
    window.dtpEditor.renderSpread(parseInt(val, 10), 1, false);
  };
  window.onTypographyFontSizeSelectChange = function(val) {
    window.dtpEditor.setFontSizePt(val);
  };
  window.adjustCustomTypography = function(type, delta) {
    if (type === 'line') {
      window.dtpEditor.adjustLineHeight(delta);
    } else if (type === 'font') {
      const w = window.dtpEditor.getCurrentWork();
      const curPt = w?.layout_config?.font_size_pt || 12;
      window.dtpEditor.setFontSizePt(curPt + delta);
    }
  };
  window.resetCustomTypography = function() {
    window.dtpEditor.resetTypography();
  };
  window.finishAndSaveCurrentLayout = function() {
    window.dtpEditor.finishAndSaveLayout();
  };

  // DOMContentLoaded 시 자동 초기화
  if (document.readyState === 'loading') {
    document.addEventListener("DOMContentLoaded", () => window.dtpEditor.init());
  } else {
    window.dtpEditor.init();
  }

})(window);

var dtpEditor = window.dtpEditor;
