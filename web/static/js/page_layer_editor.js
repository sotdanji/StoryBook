/**
 * StoryBook Studio - 2-Layer 유연 조판 시스템 (InDesign식 전문 DTP 프레임워크 v2.2)
 * 
 * 1. 글상자 아랫선이 인쇄 안전선 위(바닥 여백 80px)에 확실히 안착하도록 정밀 설계
 * 2. 상자 축소 시 빨간 점선 밑변과 핸들이 텍스트를 따라 실시간 위로 축소
 * 3. 넘침 발생 시:
 *    - "다음 3면으로 N줄 자동 넘김 (클릭 시 2부 열기)" 클릭 시 즉시 2페이지 자동 추가 및 2부(3·4면) 펼침!
 *    - 글상자 조절 완료 시 4페이지 자동 확장 연동
 * 4. 2부(3면에 넘친 내용 완벽 안착)
 */

window.showLayoutGuides = true;
window.pageBoxStates = window.pageBoxStates || {};
window.dtpOverflowLines = []; // 넘친 줄 글로벌 보관

/**
 * 조판 렌더링 직후 호출되는 DTP 가이드 & 핸들 오버레이 장착 함수
 */
function attachDtpGuidesAndHandles(work, cfg, rawLines, finalFontSize, finalLineHeight) {
    const leftPage = document.querySelector(".book-page-left");
    const rightPage = document.getElementById("bookPageRight");
    if (!leftPage || !rightPage) return;

    // 1) 불필요한 구버전/잔여 바닥 인쇄 안전선 정리 (글상자 안전 여백 가드로 완전 대체)
    clearLegacySafetyGuides(leftPage);
    clearLegacySafetyGuides(rightPage);

    // 2) 현재 1부(1·2면)인 경우와 2부(3·4면)인 경우 분기 처리
    const currentPart = window.currentSpreadPart || 1;

    // [요구사항 3] 전면그림/여백이 아니면 1·2면과 3·4면 모두 가이드선 및 핸들 완벽 부착!
    const leftSlotIdx = (currentPart - 1) * 2;
    const rightSlotIdx = leftSlotIdx + 1;
    const leftType = (cfg && cfg.slots) ? (cfg.slots[leftSlotIdx] || "image") : "image";
    const rightType = (cfg && cfg.slots) ? (cfg.slots[rightSlotIdx] || "text") : "text";

    // [핵심] 좌측면: 글이 있는 형태(text, image_text, image_top, image_bottom)이면 1·2·3부 모든 면에서 가이드선 완벽 부착!
    if (leftType !== "image" && leftType !== "blank") {
        if (leftType === "image_text") {
            setupLeftOverlayDtpBox(work, cfg, rawLines, finalFontSize, finalLineHeight);
        } else {
            // 순수 본문(text) 및 혼합형: 좌측 본문 상자(viewerPart2PoemArea)에 붉은 점선 및 상·하단 핸들 일원화 부착!
            setupLeftPageUnifiedTextDtp(work, cfg, rawLines, finalFontSize, finalLineHeight, leftSlotIdx);
        }
    } else {
        // 전면그림 또는 여백인 경우 좌측 오버레이 및 텍스트 상자 가이드선 숨김
        const overlayHolder = document.getElementById("viewerLeftOverlayTextHolder");
        if (overlayHolder) overlayHolder.style.display = "none";
        const poemArea = document.getElementById("viewerPart2PoemArea");
        if (poemArea) {
            poemArea.classList.remove("dtp-box-wrapper", "dtp-box-body");
            const tag = poemArea.querySelector(".dtp-part2-tag");
            if (tag) tag.remove();
            const th = poemArea.querySelector(".handle-top");
            if (th) th.remove();
            const bh = poemArea.querySelector(".handle-bottom");
            if (bh) bh.remove();
        }
    }

    // 우측면: 글이 있는 형태이면 가이드선 부착
    if (rightType !== "image" && rightType !== "blank") {
        setupRightPageDtpBoxes(work, cfg, rawLines, finalFontSize, finalLineHeight);
    }

    // 3) 가이드선 켬/끔 가시성 상태 동기화
    applyLayoutGuidesVisibility();
}

/**
 * 구버전 및 잔여 안전선 요소 정리
 */
function clearLegacySafetyGuides(pageEl) {
    if (!pageEl) return;
    const guides = pageEl.querySelectorAll(".print-safety-guide, .print-safety-line, #printSafetyLine");
    guides.forEach(g => g.remove());
}

/**
 * 2부(3·4면) 스프레드일 때 3면에 넘친 글이 온전히 들어가도록 주입
 */
function setupPart2SpreadDtp(work, cfg, rawLines, finalFontSize, finalLineHeight) {
    const poemBodyPart2 = document.getElementById("viewerPart2PoemBody");
    const poemArea = document.getElementById("viewerPart2PoemArea");

    if (poemBodyPart2 && window.dtpOverflowLines && window.dtpOverflowLines.length > 0) {
        if (typeof formatPoemLinesHtml === 'function') {
            poemBodyPart2.innerHTML = formatPoemLinesHtml(window.dtpOverflowLines);
        } else {
            poemBodyPart2.innerHTML = window.dtpOverflowLines.map(l => `<p class="poem-line">${l || '&nbsp;'}</p>`).join("");
        }
        poemBodyPart2.style.fontSize = `${(finalFontSize || 0.95).toFixed(2)}rem`;
        poemBodyPart2.style.lineHeight = `${(finalLineHeight || 1.85).toFixed(2)}`;
        poemBodyPart2.style.userSelect = "text";
        poemBodyPart2.style.cursor = "text";
    }

    // [요구사항 3] 3면(좌측 이어짐 본문)에도 DTP 붉은 점선 상자 및 상·하단 핸들 부착!
    if (poemArea) {
        poemArea.classList.add("dtp-box-wrapper", "dtp-box-body");

        let tag = poemArea.querySelector(".dtp-part2-tag");
        if (!tag) {
            tag = document.createElement("div");
            tag.className = "dtp-box-tag dtp-part2-tag";
            tag.innerHTML = `<span>3면 본문 상자 (상·하단 드래그 조절 가능)</span>`;
            poemArea.prepend(tag);
        }

        let topHandle = poemArea.querySelector(".dtp-resize-handle.handle-top");
        if (!topHandle) {
            topHandle = document.createElement("div");
            topHandle.className = "dtp-resize-handle handle-top";
            topHandle.title = "본문 시작선 ↕ (아래로 드래그하여 상단 위치 조절)";
            topHandle.innerHTML = `<div class="handle-bar-pill"></div><div class="handle-label">▲ 본문 시작선 (드래그 조절) ▼</div>`;
            poemArea.prepend(topHandle);
        }

        let bottomHandle = poemArea.querySelector(".dtp-resize-handle.handle-bottom");
        if (!bottomHandle) {
            bottomHandle = document.createElement("div");
            bottomHandle.className = "dtp-resize-handle handle-bottom";
            bottomHandle.title = "본문 종료선 ↕ (위아래 드래그하여 상자 크기 조절)";
            bottomHandle.innerHTML = `<div class="handle-bar-pill"></div><div class="handle-label">▲ 본문 종료선 (드래그 조절) ▼</div>`;
            poemArea.appendChild(bottomHandle);
        }

        const stateKey = `work_${window.currentWorkIndex || 0}_part2_left`;
        const savedState = window.pageBoxStates[stateKey] || {};

        if (savedState.marginTop !== undefined) {
            poemArea.style.marginTop = `${savedState.marginTop}px`;
        }
        if (savedState.height !== undefined) {
            poemArea.style.height = `${savedState.height}px`;
        }

        bindBoxResizeInteraction(poemArea, poemBodyPart2, topHandle, bottomHandle, stateKey, (newHeight) => {
            // 3면 높이 조절 콜백
        });
    }
}

// 좌측면이 순수 본문(text) 또는 상하혼합일 때 DTP 가이드선 부착
function setupLeftPageTextDtpBox(work, cfg, rawLines, finalFontSize, finalLineHeight, slotIdx) {
    const leftHolder = document.getElementById("viewerPart2LeftHolder") || document.getElementById("viewerMixedHolderLeft");
    const poemArea = document.getElementById("viewerPart2PoemArea");
    if (!poemArea) return;

    poemArea.classList.add("dtp-box-wrapper", "dtp-box-body");

    let tag = poemArea.querySelector(".dtp-part2-tag");
    if (!tag) {
        tag = document.createElement("div");
        tag.className = "dtp-box-tag dtp-part2-tag";
        tag.innerHTML = `<span>좌측 본문 상자 (상·하단 드래그 조절 가능)</span>`;
        poemArea.prepend(tag);
    }

    let topHandle = poemArea.querySelector(".dtp-resize-handle.handle-top");
    if (!topHandle) {
        topHandle = document.createElement("div");
        topHandle.className = "dtp-resize-handle handle-top";
        topHandle.title = "본문 시작선 ↕ (아래로 드래그하여 상단 위치 조절)";
        topHandle.innerHTML = `<div class="handle-bar-pill"></div><div class="handle-label">▲ 본문 시작선 (드래그 조절) ▼</div>`;
        poemArea.prepend(topHandle);
    }

    let bottomHandle = poemArea.querySelector(".dtp-resize-handle.handle-bottom");
    if (!bottomHandle) {
        bottomHandle = document.createElement("div");
        bottomHandle.className = "dtp-resize-handle handle-bottom";
        bottomHandle.title = "본문 종료선 ↕ (위아래 드래그하여 상자 크기 조절)";
        bottomHandle.innerHTML = `<div class="handle-bar-pill"></div><div class="handle-label">▲ 본문 종료선 (드래그 조절) ▼</div>`;
        poemArea.appendChild(bottomHandle);
    }

    const stateKey = `work_${window.currentWorkIndex || 0}_slot_${slotIdx}`;
    const savedState = window.pageBoxStates[stateKey] || {};

    if (savedState.marginTop !== undefined) {
        poemArea.style.marginTop = `${savedState.marginTop}px`;
    }
    if (savedState.height !== undefined) {
        poemArea.style.height = `${savedState.height}px`;
    }

    bindBoxResizeInteraction(poemArea, poemArea.querySelector(".poem-display-body"), topHandle, bottomHandle, stateKey, (newHeight) => {
        // 높이 조절 콜백
    });
}

/**
 * 좌측 페이지 [전면그림+글] 오버레이 상자 드래그 핸들 연결
 */
function setupLeftOverlayDtpBox(work, cfg, rawLines, finalFontSize, finalLineHeight) {
    const overlayHolder = document.getElementById("viewerLeftOverlayTextHolder");
    const overlayBox = document.getElementById("dtpOverlayBoxLeft");
    const overlayContent = document.getElementById("viewerLeftOverlayContent");
    const topHandle = document.getElementById("dtpOverlayTopHandleLeft");
    const bottomHandle = document.getElementById("dtpOverlayBottomHandleLeft");

    if (!overlayHolder || !overlayBox || !overlayContent) return;

    const leftSlotIdx = (window.currentSpreadPart ? (window.currentSpreadPart - 1) * 2 : 0);
    const leftType = (cfg && cfg.slots) ? (cfg.slots[leftSlotIdx] || "image") : "image";

    if (leftType !== "image_text") {
        overlayHolder.style.display = "none";
        overlayHolder.classList.add("is-hidden");
        overlayBox.style.display = "none";
        return;
    }

    overlayHolder.style.display = "flex";
    overlayHolder.classList.remove("is-hidden");
    overlayBox.style.display = "flex";

    const stateKey = `work_${window.currentWorkIndex || 0}_overlay_left`;
    const savedState = window.pageBoxStates[stateKey] || {};

    if (savedState.marginTop !== undefined) {
        overlayBox.style.marginTop = `${savedState.marginTop}px`;
    } else {
        overlayBox.style.marginTop = "24px";
    }
    if (savedState.height !== undefined) {
        overlayBox.style.height = `${savedState.height}px`;
    }

    if (topHandle && bottomHandle) {
        bindBoxResizeInteraction(overlayBox, overlayContent, topHandle, bottomHandle, stateKey, (newHeight) => {
            // 좌측 오버레이 높이 변경 시 처리
        });
    }
}

/**
 * 우측 페이지 제목 상자, 지은이 상자, 본문 상자 스타일링 및 드래그 핸들 연결
 */
function setupRightPageDtpBoxes(work, cfg, rawLines, finalFontSize, finalLineHeight) {
    const headerArea = document.querySelector(".poem-header-area");
    const titleElem = document.getElementById("viewerTitle");
    const rightHolder = document.getElementById("viewerRightPoemHolder");
    const bodyElem = document.getElementById("viewerBody");
    const poemBodyContainer = document.getElementById("poemBodyContainer");

    if (!rightHolder || !bodyElem) return;

    // A) 제목 상자 & 지은이 상자 (상단 고정 및 뭉개짐 방지)
    if (headerArea && titleElem) {
        headerArea.classList.add("dtp-box-wrapper", "dtp-box-title-author");
        
        let titleTag = headerArea.querySelector(".dtp-header-tag");
        if (!titleTag) {
            titleTag = document.createElement("div");
            titleTag.className = "dtp-box-tag dtp-header-tag";
            titleTag.innerHTML = `<span>제목·지은이 상자 (위치 고정)</span>`;
            headerArea.prepend(titleTag);
        }

        let authorElem = headerArea.querySelector(".dtp-author-display");
        if (!authorElem) {
            authorElem = document.createElement("div");
            authorElem.className = "dtp-author-display";
            headerArea.appendChild(authorElem);
        }
        const authorName = work.author || (window.currentStatus?.author) || (window.currentStatus?.project?.author) || "임종훈";
        const authorType = (window.currentStatus?.project?.author_type) || (window.currentStatus?.author_type) || "single";
        const isCollab = (authorType === "collab");

        if (!isCollab) {
            // [요구사항 1] 1인 시집: 본문에서는 지은이 생략
            authorElem.style.display = "none";
            if (titleTag) titleTag.innerHTML = `<span>제목 상자 (위치 고정)</span>`;
        } else {
            // 공동/가족 시집: 지은이 표기 및 우측정렬
            authorElem.style.display = "block";
            authorElem.style.textAlign = "right";
            authorElem.style.marginTop = "4px";
            authorElem.style.fontWeight = "600";
            authorElem.style.color = "#6E5340";
            authorElem.textContent = `${authorName} 지음`;
            if (titleTag) titleTag.innerHTML = `<span>제목·지은이 상자 (위치 고정)</span>`;
        }
    }

    // B) 본문 상자 (상·하단 드래그 조절)
    const targetBodyBox = poemBodyContainer || bodyElem.parentElement || bodyElem;
    targetBodyBox.classList.add("dtp-box-wrapper", "dtp-box-body");

    let bodyTag = targetBodyBox.querySelector(".dtp-body-tag");
    if (!bodyTag) {
        bodyTag = document.createElement("div");
        bodyTag.className = "dtp-box-tag dtp-body-tag";
        bodyTag.innerHTML = `<span>본문 상자 (상·하단 드래그 조절 가능)</span>`;
        targetBodyBox.prepend(bodyTag);
    }

    // 상단 리사이즈 핸들 (시작선)
    let topHandle = targetBodyBox.querySelector(".dtp-resize-handle.handle-top");
    if (!topHandle) {
        topHandle = document.createElement("div");
        topHandle.className = "dtp-resize-handle handle-top";
        topHandle.title = "본문 시작선 ↕ (아래로 드래그하여 상자 상단 위치 조절)";
        topHandle.innerHTML = `
            <div class="handle-bar-pill"></div>
            <div class="handle-label">▲ 본문 시작선 (드래그 조절) ▼</div>
        `;
        targetBodyBox.prepend(topHandle);
    }

    // 하단 리사이즈 핸들 (종료선)
    let bottomHandle = targetBodyBox.querySelector(".dtp-resize-handle.handle-bottom");
    if (!bottomHandle) {
        bottomHandle = document.createElement("div");
        bottomHandle.className = "dtp-resize-handle handle-bottom";
        bottomHandle.title = "본문 종료선 ↕ (위아래 드래그하여 상자 크기 조절: 줄이면 다음 페이지로 자동 넘김)";
        bottomHandle.innerHTML = `
            <div class="handle-bar-pill"></div>
            <div class="handle-label">▲ 본문 종료선 (드래그 조절) ▼</div>
        `;
        targetBodyBox.appendChild(bottomHandle);
    }

    // [핵심] 넘침 알림 칩을 상자 내부가 아닌 우측 페이지 하단 고정 슬롯(#dtpOverflowFixedSlot)에 안착!
    let fixedSlot = document.getElementById("dtpOverflowFixedSlot");
    if (!fixedSlot) {
        fixedSlot = document.createElement("div");
        fixedSlot.id = "dtpOverflowFixedSlot";
        fixedSlot.style.cssText = "position: absolute; bottom: 24px; left: 50%; transform: translateX(-50%); z-index: 100; pointer-events: auto; display: flex; justify-content: center; width: 90%;";
        const rPage = document.getElementById("bookPageRight");
        if (rPage) rPage.appendChild(fixedSlot);
    }

    let overflowChip = document.getElementById("dtpOverflowGlobalChip");
    if (!overflowChip) {
        overflowChip = document.createElement("div");
        overflowChip.id = "dtpOverflowGlobalChip";
        overflowChip.className = "dtp-overflow-badge";
        if (fixedSlot) fixedSlot.appendChild(overflowChip);
    } else if (fixedSlot && overflowChip.parentElement !== fixedSlot) {
        fixedSlot.appendChild(overflowChip);
    }

    // [핵심] "클릭 시 2부 열기" 클릭 핸들러: 없으면 자동 2페이지 추가 후 2부 즉시 펼침!
    overflowChip.onclick = async (e) => {
        e.preventDefault();
        e.stopPropagation();

        const curWork = window.currentStatus?.works?.[window.currentWorkIndex];
        const curCfg = (typeof window.getNormalizedLayoutConfig === 'function' && curWork) 
            ? window.getNormalizedLayoutConfig(curWork) 
            : (curWork?.layout_config || {});
        const pCount = curCfg.page_count || 2;

        if (pCount <= 2) {
            // 현재 2면뿐이면 -> 2페이지 자동 추가하고 2부(3·4면)로 이동!
            if (typeof window.addSpreadToCurrentWork === 'function') {
                await window.addSpreadToCurrentWork();
            }
        } else {
            // 이미 4면 이상이면 -> 즉시 2부(3·4면)로 이동하여 넘친 글 확인!
            window.currentSpreadPart = 2;
            if (typeof window.renderBookSpread === 'function') {
                window.renderBookSpread(window.currentWorkIndex);
            }
        }
    };

    // [핵심] 인쇄 안전선 위쪽에 확실히 위치하도록 하단 안전 여백 80px로 대폭 확보!
    const pageEl = document.getElementById("bookPageRight") || targetBodyBox.closest(".book-page-right");
    const pageH = (pageEl && pageEl.clientHeight > 200) ? pageEl.clientHeight : 610;
    
    let topRelative = 110;
    if (pageEl && targetBodyBox) {
        const pageRect = pageEl.getBoundingClientRect();
        const boxRect = targetBodyBox.getBoundingClientRect();
        if (boxRect.top > 0 && pageRect.top > 0) {
            topRelative = Math.max(70, Math.round(boxRect.top - pageRect.top));
        } else {
            topRelative = targetBodyBox.offsetTop || 110;
        }
    }

    // 하단 안전 여백: 책장 바닥에서 80px 위에 본문 박스 밑변이 위치하도록 상한선 설정!
    const maxSafeHeight = Math.max(90, Math.floor(pageH - topRelative - 80));

    // 저장된 상태 복원 적용 (기존에 너무 길게 저장된 높이는 maxSafeHeight로 즉시 축소)
    const stateKey = `work_${window.currentWorkIndex || 0}_body`;
    const savedState = window.pageBoxStates[stateKey] || {};

    if (savedState.marginTop !== undefined) {
        targetBodyBox.style.marginTop = `${savedState.marginTop}px`;
    }
    
    if (savedState.height !== undefined && savedState.height <= maxSafeHeight) {
        targetBodyBox.style.height = `${savedState.height}px`;
        targetBodyBox.style.maxHeight = `${savedState.height}px`;
    } else {
        // 기본 초기 높이: 하단 안전 여백(바닥에서 80px 위)에 딱 맞춤!
        targetBodyBox.style.height = `${maxSafeHeight}px`;
        targetBodyBox.style.maxHeight = `${maxSafeHeight}px`;
        window.pageBoxStates[stateKey] = window.pageBoxStates[stateKey] || {};
        window.pageBoxStates[stateKey].height = maxSafeHeight;
    }

    // [요구사항 2] 1부(1·2면)와 2부(3·4면 이상)의 본문 분기:
    // 2부 이상(currentSpreadPart >= 2)일 때, 우측면(4면, 6면)은 1연 첫행부터 시작하면 절대 안 됨!
    const curPart = window.currentSpreadPart || 1;

    if (curPart === 1) {
        // [1부: 2면(우)] 시의 시작! 2면 상자 크기에 맞춰 넘침 계산
        reflowTextIntoBodyAndNextPage(targetBodyBox, bodyElem, overflowChip, rawLines, finalFontSize, finalLineHeight, false);

        bindBoxResizeInteraction(targetBodyBox, bodyElem, topHandle, bottomHandle, stateKey, (newHeight) => {
            reflowTextIntoBodyAndNextPage(targetBodyBox, bodyElem, overflowChip, rawLines, finalFontSize, finalLineHeight, true);
        });
    } else {
        // [2부: 4면(우) 이상] 3면에서 넘친 추가 시구(window.dtpOverflowLinesPart2)가 있을 때만 4면에 주입!
        // 시가 3면에서 이미 끝났다면 4면은 깨끗한 빈 글상자로 유지!
        const linesForRightPage = window.dtpOverflowLinesPart2 || [];

        // 4면에서는 [다음 3면으로 자동 넘김] 칩을 무조건 숨김!
        if (overflowChip) overflowChip.style.display = "none";

        if (linesForRightPage.length > 0) {
            reflowTextIntoBodyAndNextPage(targetBodyBox, bodyElem, null, linesForRightPage, finalFontSize, finalLineHeight, false);
            bindBoxResizeInteraction(targetBodyBox, bodyElem, topHandle, bottomHandle, stateKey, (newHeight) => {
                reflowTextIntoBodyAndNextPage(targetBodyBox, bodyElem, null, linesForRightPage, finalFontSize, finalLineHeight, true);
            });
        } else {
            // 시가 이미 완료됨 -> 4면은 완전한 빈 본문 상자로 대기! (1연 복제 원천 차단)
            bodyElem.innerHTML = "<div class='poem-line poem-line-empty' style='height: 1.1em;'></div>";
            if (overflowChip) overflowChip.style.display = "none";

            bindBoxResizeInteraction(targetBodyBox, bodyElem, topHandle, bottomHandle, stateKey, (newHeight) => {
                // 빈 상자 높이 조절
            });
        }
    }
}

/**
 * 상자 크기에 맞춰 행을 분할하고 넘치는 행을 다음 페이지(3면)로 연쇄 이동시키는 실시간 Text Threading 엔진
 */
function reflowTextIntoBodyAndNextPage(boxEl, bodyElem, overflowChip, rawLines, fontSizeRem, lineHeightRatio, isInteractive) {
    if (!rawLines || rawLines.length === 0) return;

    // [요구사항 2-2] 상자 안쪽 가용 높이: 칩이 바깥 고정 슬롯으로 나갔으므로 순수 패딩(10px)만 제외하여 하단선 부근까지 꽉 채움!
    const boxHeight = boxEl.clientHeight || 360;
    const availableHeight = Math.max(60, boxHeight - 10);

    // 1행 기준 높이 (px) - pt 및 rem 크기 정확 반영
    const curWork = window.currentStatus?.works?.[window.currentWorkIndex];
    const curPt = curWork?.layout_config?.font_size_pt || 12;
    const baseFontSizePx = (fontSizeRem || (curPt / 12.0)) * 16;
    const rowHeightPx = baseFontSizePx * (lineHeightRatio || 1.85);

    // 현재 본문 상자에 들어갈 수 있는 최대 줄 수
    const capacity = Math.max(2, Math.floor(availableHeight / rowHeightPx));

    // 행 분할: 2면에 들어갈 줄과 넘치는 줄
    const displayedLines = rawLines.slice(0, capacity);
    const overflowLines = rawLines.slice(capacity);

    // 글로벌 변수에 넘친 줄 보관 (2부 펼침 시 3면에 자동 주입용)
    window.dtpOverflowLines = overflowLines;

    // 2면 본문 갱신
    if (typeof formatPoemLinesHtml === 'function') {
        bodyElem.innerHTML = formatPoemLinesHtml(displayedLines);
    } else {
        bodyElem.innerHTML = displayedLines.map(l => `<p class="poem-line">${l || '&nbsp;'}</p>`).join("");
    }

    // 넘친 줄들 처리
    if (overflowLines.length > 0) {
        // [핵심 2] 2쪽 추가가 자동으로 이미 실행되도록 백그라운드 보장!
        ensureWorkHasFourPagesSilently();

        // 하단 알림 배지 활성화 (하단선 따라 위로 밀리지 않는 고정 슬롯에서 명쾌하게 안내)
        if (overflowChip) {
            overflowChip.style.display = "inline-flex";
            overflowChip.innerHTML = `<span>📖 다음 3면으로 ${overflowLines.length}줄 자동 넘김 ➔ [3·4면 바로보기]</span>`;
            overflowChip.title = "현재 본문 상자 크기에 맞춰 넘친 시구가 3면으로 자동 넘겨졌습니다. 클릭하면 3·4면으로 즉시 책장을 넘깁니다.";
        }

        // 3면(좌측 2부 슬롯)의 본문 영역(#viewerPart2PoemBody)에도 실시간 주입
        const part2PoemBody = document.getElementById("viewerPart2PoemBody");
        if (part2PoemBody) {
            if (typeof formatPoemLinesHtml === 'function') {
                part2PoemBody.innerHTML = formatPoemLinesHtml(overflowLines);
            } else {
                part2PoemBody.innerHTML = overflowLines.map(l => `<p class="poem-line">${l || '&nbsp;'}</p>`).join("");
            }
        }
    } else {
        // 넘친 줄이 없으면 배지 숨김
        if (overflowChip) {
            overflowChip.style.display = "none";
        }
    }
}

/**
 * 붉은 점선 상자 자체의 크기(height) 및 상단 위치(marginTop)를 마우스로 직접 조절하는 인터랙션 엔진
 */
function bindBoxResizeInteraction(boxEl, contentElem, topHandle, bottomHandle, stateKey, onHeightChangeCallback) {
    // 1) 상단 핸들: 아래로 드래그하여 상자 전체의 상단 위치를 끌어내림
    topHandle.onmousedown = function (e) {
        e.preventDefault();
        e.stopPropagation();

        const startY = e.clientY;
        const startMarginTop = parseFloat(window.getComputedStyle(boxEl).marginTop) || 0;

        boxEl.classList.add("is-resizing");
        document.body.style.cursor = "ns-resize";

        const startHeight = boxEl.clientHeight || 360;
        const bottomFixedAnchor = startMarginTop + startHeight; // [요구사항 2-1] 아랫면 고정 앵커

        function onMouseMove(ev) {
            const deltaY = ev.clientY - startY;
            let newMarginTop = startMarginTop + deltaY;

            if (newMarginTop < 0) newMarginTop = 0;
            if (newMarginTop > bottomFixedAnchor - 70) newMarginTop = bottomFixedAnchor - 70;

            // 아랫면(bottom) 위치가 고정되도록 상자 높이를 마우스에 맞춰 정밀 연동!
            let newHeight = Math.max(70, bottomFixedAnchor - newMarginTop);

            boxEl.style.marginTop = `${Math.round(newMarginTop)}px`;
            boxEl.style.height = `${Math.round(newHeight)}px`;
            boxEl.style.maxHeight = `${Math.round(newHeight)}px`;

            window.pageBoxStates[stateKey] = window.pageBoxStates[stateKey] || {};
            window.pageBoxStates[stateKey].marginTop = Math.round(newMarginTop);
            window.pageBoxStates[stateKey].height = Math.round(newHeight);

            if (onHeightChangeCallback) onHeightChangeCallback(newHeight);
        }

        function onMouseUp() {
            window.removeEventListener("mousemove", onMouseMove);
            window.removeEventListener("mouseup", onMouseUp);
            boxEl.classList.remove("is-resizing");
            document.body.style.cursor = "";
            saveLayoutBoxStatesToStorage();
        }

        window.addEventListener("mousemove", onMouseMove);
        window.addEventListener("mouseup", onMouseUp);
    };

    // 2) 하단 핸들: 위아래로 드래그하여 상자 자체의 높이(height)를 줄이거나 늘림!
    bottomHandle.onmousedown = function (e) {
        e.preventDefault();
        e.stopPropagation();

        const startY = e.clientY;
        const startHeight = boxEl.clientHeight || 360;

        boxEl.classList.add("is-resizing");
        document.body.style.cursor = "ns-resize";

        const pageEl = document.getElementById("bookPageRight") || boxEl.closest(".book-page-right");
        const pageH = (pageEl && pageEl.clientHeight > 200) ? pageEl.clientHeight : 610;
        
        let topRelative = 110;
        if (pageEl && boxEl) {
            const pageRect = pageEl.getBoundingClientRect();
            const boxRect = boxEl.getBoundingClientRect();
            if (boxRect.top > 0 && pageRect.top > 0) {
                topRelative = Math.max(70, Math.round(boxRect.top - pageRect.top));
            } else {
                topRelative = boxEl.offsetTop || 110;
            }
        }
        
        // 바닥에서 80px 떨어진 곳까지만 최대 확장 허용!
        const maxSafeHeight = Math.max(90, Math.floor(pageH - topRelative - 80));

        function onMouseMove(ev) {
            const deltaY = ev.clientY - startY;
            let newHeight = startHeight + deltaY;

            if (newHeight < 90) newHeight = 90;
            if (newHeight > maxSafeHeight) newHeight = maxSafeHeight;

            // 빨간 점선 상자 자체의 높이를 실시간 직접 변경 (밑변이 마우스 따라 올라오고 내려감)
            boxEl.style.height = `${Math.round(newHeight)}px`;
            boxEl.style.maxHeight = `${Math.round(newHeight)}px`;

            window.pageBoxStates[stateKey] = window.pageBoxStates[stateKey] || {};
            window.pageBoxStates[stateKey].height = Math.round(newHeight);

            // 실시간 텍스트 넘김 분할 호출
            if (onHeightChangeCallback) onHeightChangeCallback(newHeight);
        }

        async function onMouseUp() {
            window.removeEventListener("mousemove", onMouseMove);
            window.removeEventListener("mouseup", onMouseUp);
            boxEl.classList.remove("is-resizing");
            document.body.style.cursor = "";
            saveLayoutBoxStatesToStorage();

            // [핵심] 상자를 줄여서 글이 넘쳤을 때 현재 2면뿐이라면 4면으로 자동 확장!
            await autoCheckAndExpandSpreadIfOverflow();
        }

        window.addEventListener("mousemove", onMouseMove);
        window.addEventListener("mouseup", onMouseUp);
    };
}

/**
 * 텍스트 넘침 시 4면 자동 확장 연계
 */
async function autoCheckAndExpandSpreadIfOverflow() {
    const overflowChip = document.querySelector(".dtp-overflow-badge");
    if (overflowChip && overflowChip.style.display !== "none") {
        const work = window.currentStatus?.works?.[window.currentWorkIndex];
        const cfg = (typeof window.getNormalizedLayoutConfig === 'function' && work) 
            ? window.getNormalizedLayoutConfig(work) 
            : (work?.layout_config || {});
        if (cfg && cfg.page_count <= 2) {
            if (typeof window.addSpreadToCurrentWork === 'function') {
                await window.addSpreadToCurrentWork();
                if (typeof showToast === 'function') {
                    showToast("📖 넘친 줄을 위해 다음 2페이지(3·4면)가 자동 추가되었습니다! [클릭 시 2부 열기]를 눌러보세요.", "success");
                }
            }
        }
    }
}

/**
 * 조판 가이드선 토글 (편집용 빨간 네모 보이기/숨기기)
 */
function toggleLayoutGuides(show) {
    window.showLayoutGuides = (show !== undefined) ? show : !window.showLayoutGuides;
    applyLayoutGuidesVisibility();
}

function applyLayoutGuidesVisibility() {
    const bookSpread = document.querySelector(".book-spread");
    if (!bookSpread) return;

    if (window.showLayoutGuides) {
        bookSpread.classList.remove("hide-dtp-guides");
    } else {
        bookSpread.classList.add("hide-dtp-guides");
    }

    const btn = document.getElementById("btnToggleLayoutGuides");
    if (btn) {
        btn.innerHTML = window.showLayoutGuides ? `<span>🟥 가이드선 켬</span>` : `<span>⬜ 가이드선 끔</span>`;
    }
}

function saveLayoutBoxStatesToStorage() {
    try {
        localStorage.setItem("storybook_page_box_states", JSON.stringify(window.pageBoxStates));
    } catch {}
}

function loadLayoutBoxStatesFromStorage() {
    try {
        const saved = localStorage.getItem("storybook_page_box_states");
        if (saved) {
            window.pageBoxStates = JSON.parse(saved);
        }
    } catch {}
}

loadLayoutBoxStatesFromStorage();


/**
 * [사용자 요구 2] 시 본문이 넘쳤을 때 별도 클릭 없이 자동으로 2쪽(총 4면)을 즉시 추가 확장
 */
async function ensureWorkHasFourPagesSilently() {
    const curWork = window.currentStatus?.works?.[window.currentWorkIndex];
    if (!curWork) return;
    const curCfg = (typeof window.getNormalizedLayoutConfig === 'function') 
        ? window.getNormalizedLayoutConfig(curWork) 
        : (curWork.layout_config || {});
    const pCount = curCfg.page_count || 2;

    if (pCount <= 2) {
        // [핵심 2] 본문 넘침 발생 시 클릭 없이도 즉시 영구적으로 4면 자동 확장!
        curCfg.page_count = 4;
        curCfg.slots = curCfg.slots || ["image", "text"];
        while (curCfg.slots.length < 4) {
            curCfg.slots.push("text"); // [원칙] 추가되는 모든 홀수/짝수면의 초기값은 무조건 "text" (순수 본문)!
        }
        curWork.layout_config = curCfg;
        curWork.layout_mode = "multi_page";

        // 툴바 페이지 배지 및 1부/2부 탭 강제 노출
        updateLayoutToolbarPageBadges(curCfg);

        // 백엔드에도 비동기 영구 저장
        if (typeof window.saveWorkLayoutConfigToServer === 'function') {
            window.saveWorkLayoutConfigToServer(curWork.episode_no, curCfg);
        }
    }
}

function updateLayoutToolbarPageBadges(cfg) {
    const pCount = cfg?.page_count || 2;
    const totalBadge = document.getElementById("lblTotalPagesBadge");
    const partNav = document.getElementById("spreadPartNavGroup");
    const btnPart1 = document.getElementById("btnGoSpreadPart1");
    const btnPart2 = document.getElementById("btnGoSpreadPart2");

    if (totalBadge) {
        if (pCount <= 2) {
            totalBadge.textContent = "📄 2쪽 조판 (1·2면)";
            totalBadge.style.color = "#553412";
            totalBadge.style.borderColor = "#D5C2B0";
        } else {
            totalBadge.textContent = "📑 4쪽 조판 (1·2면 + 3·4면)";
            totalBadge.style.color = "#1E40AF";
            totalBadge.style.borderColor = "#93C5FD";
            totalBadge.style.background = "#EFF6FF";
        }
    }

    if (partNav) {
        // [핵심] pageCount 가 4 이상이면 1부/2부 탭이 절대 사라지지 않고 항시 노출!
        partNav.style.display = (pCount > 2) ? "inline-flex" : "none";
        const currentPart = (typeof window.currentSpreadPart !== 'undefined') ? window.currentSpreadPart : 1;
        if (btnPart1) {
            btnPart1.style.background = (currentPart === 1) ? "#FFF" : "transparent";
            btnPart1.style.color = (currentPart === 1) ? "#7C3E1D" : "#8C6D58";
            btnPart1.style.border = (currentPart === 1) ? "1.5px solid #D5C2B0" : "1px solid transparent";
            btnPart1.style.boxShadow = (currentPart === 1) ? "0 1px 3px rgba(0,0,0,0.08)" : "none";
        }
        if (btnPart2) {
            btnPart2.style.background = (currentPart === 2) ? "#FFF" : "transparent";
            btnPart2.style.color = (currentPart === 2) ? "#7C3E1D" : "#8C6D58";
            btnPart2.style.border = (currentPart === 2) ? "1.5px solid #D5C2B0" : "1px solid transparent";
            btnPart2.style.boxShadow = (currentPart === 2) ? "0 1px 3px rgba(0,0,0,0.08)" : "none";
        }
    }
}

function switchSpreadPart(part) {
    const p = parseInt(part, 10) || 1;
    window.currentSpreadPart = p;
    if (typeof window.switchSpreadPart === 'function') {
        window.switchSpreadPart(p);
    } else if (typeof window.renderBookSpread === 'function') {
        window.renderBookSpread(window.currentWorkIndex);
    }
}


/**
 * [StoryBook 2-Layer DTP] 좌측면 순수 본문 상자 가이드선 & 상·하단 핸들 통합 엔진
 * (3면, 5면 등 홀수면 본문 상자에 붉은 점선 테두리와 드래그 핸들을 오차 없이 장착)
 */
function setupLeftPageUnifiedTextDtp(work, cfg, rawLines, finalFontSize, finalLineHeight, slotIdx) {
    const poemArea = document.getElementById("viewerPart2PoemArea");
    const poemBody = document.getElementById("viewerPart2PoemBody");
    const leftHolder = document.getElementById("viewerPart2LeftHolder");
    if (!poemArea || !poemBody) return;

    if (leftHolder) {
        leftHolder.style.display = "flex";
    }
    poemArea.style.display = "flex";

    // 붉은 점선 상자 클래스 부여
    poemArea.classList.add("dtp-box-wrapper", "dtp-box-body");

    // 상단 태그 라벨
    let tag = poemArea.querySelector(".dtp-part2-tag");
    if (!tag) {
        tag = document.createElement("div");
        tag.className = "dtp-box-tag dtp-part2-tag";
        tag.innerHTML = `<span>좌측 본문 상자 (${slotIdx + 1}면 드래그 조절)</span>`;
        poemArea.prepend(tag);
    } else {
        tag.innerHTML = `<span>좌측 본문 상자 (${slotIdx + 1}면 드래그 조절)</span>`;
    }

    // 상단 리사이즈 핸들 (시작선)
    let topHandle = poemArea.querySelector(".dtp-resize-handle.handle-top");
    if (!topHandle) {
        topHandle = document.createElement("div");
        topHandle.className = "dtp-resize-handle handle-top";
        topHandle.title = "본문 시작선 ↕ (아래로 드래그하여 상단 위치 조절)";
        topHandle.innerHTML = `<div class="handle-bar-pill"></div><div class="handle-label">▲ 본문 시작선 (드래그 조절) ▼</div>`;
        poemArea.prepend(topHandle);
    }

    // 하단 리사이즈 핸들 (종료선)
    let bottomHandle = poemArea.querySelector(".dtp-resize-handle.handle-bottom");
    if (!bottomHandle) {
        bottomHandle = document.createElement("div");
        bottomHandle.className = "dtp-resize-handle handle-bottom";
        bottomHandle.title = "본문 종료선 ↕ (위아래 드래그하여 상자 크기 조절)";
        bottomHandle.innerHTML = `<div class="handle-bar-pill"></div><div class="handle-label">▲ 본문 종료선 (드래그 조절) ▼</div>`;
        poemArea.appendChild(bottomHandle);
    }

    // 페이지 높이에 맞춘 안전 상한선 계산
    const leftPageEl = document.querySelector(".book-page-left");
    const pageH = (leftPageEl && leftPageEl.clientHeight > 200) ? leftPageEl.clientHeight : 610;
    const maxSafeHeight = Math.max(90, pageH - 120);

    const stateKey = `work_${window.currentWorkIndex || 0}_slot_${slotIdx}`;
    const savedState = window.pageBoxStates[stateKey] || {};

    if (savedState.marginTop !== undefined) {
        poemArea.style.marginTop = `${savedState.marginTop}px`;
    } else {
        poemArea.style.marginTop = "10px";
    }

    if (savedState.height !== undefined && savedState.height <= maxSafeHeight) {
        poemArea.style.height = `${savedState.height}px`;
        poemArea.style.maxHeight = `${savedState.height}px`;
    } else {
        poemArea.style.height = `${maxSafeHeight}px`;
        poemArea.style.maxHeight = `${maxSafeHeight}px`;
    }

    // 3면에서 넘치는 줄이 있는지 정밀 계산하여 4면(우)으로 연쇄 이동
    const overflowLinesFromPart1 = window.dtpOverflowLines || [];
    if (overflowLinesFromPart1.length > 0) {
        const boxH = poemArea.clientHeight || maxSafeHeight;
        const availH = Math.max(60, boxH - 10);
        const curWork = window.currentStatus?.works?.[window.currentWorkIndex];
        const curPt = curWork?.layout_config?.font_size_pt || 12;
        const basePx = (finalFontSize || (curPt / 12.0)) * 16;
        const rowH = basePx * (finalLineHeight || 1.85);
        const cap = Math.max(2, Math.floor(availH / rowH));

        const disp3 = overflowLinesFromPart1.slice(0, cap);
        const over3 = overflowLinesFromPart1.slice(cap);

        poemBody.innerHTML = (typeof formatPoemLinesHtml === 'function') 
            ? formatPoemLinesHtml(disp3) 
            : disp3.map(l => `<p class="poem-line">${l || '&nbsp;'}</p>`).join("");

        // 3면에서도 넘친 줄이 있다면 4면용 글로벌 변수에 보관
        window.dtpOverflowLinesPart2 = over3;
    } else {
        window.dtpOverflowLinesPart2 = [];
    }

    // 마우스 드래그 조절 인터랙션 연결 (상단 내릴 때 아랫면 고정 연동)
    bindBoxResizeInteraction(poemArea, poemBody, topHandle, bottomHandle, stateKey, (newHeight) => {
        // 좌측 본문 높이 조절 콜백
    });
}
