# -*- coding: utf-8 -*-
"""
1) 글상자 상단선 리사이즈 고정(하단선 고정 & 상단선 리사이즈)
2) 그림틀 이동 바 모든 레이아웃 바인딩 및 가시성 완벽 보장
"""

def apply_fixes():
    # 1. dtp_editor_core.js 수정
    with open('web/static/js/dtp_editor_core.js', 'r', encoding='utf-8') as f:
        core = f.read()

    # (1) topHandle 리사이즈 로직: 하단선(fixedBottomY) 고정 및 상단선 리사이즈
    old_top_handle_logic = """        const startY = e.clientY;
        const initialOffset = parseInt(pageData.top_offset, 10) || 0;
        let currOffset = initialOffset;

        boxBody.classList.add("is-resizing");
        document.body.style.cursor = "ns-resize";

        const label = topHandle.querySelector(".handle-label");
        if (label) {
          label.textContent = `▲ 본문 시작선 내림: +${initialOffset}px`;
          label.style.display = "block";
        }

        const minBottomH = Math.max(34, Math.round(linePx + 16));
        const maxTopOffset = Math.max(0, 517 - minBottomH); // 하단 기준 1줄 남길 때까지 극단 허용 (~470px)

        function onMouseMove(ev) {
          const deltaY = ev.clientY - startY;
          currOffset = Math.max(0, Math.min(maxTopOffset, Math.round(initialOffset + deltaY)));
          boxBody.style.setProperty("margin-top", `${currOffset}px`, "important");

          if (label) {
            label.textContent = `▲ 본문 시작선 내림: +${currOffset}px`;
          }
          self.detectAndApplyLineOverlap(side);
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
        }"""

    new_top_handle_logic = """        const startY = e.clientY;
        const initialOffset = parseInt(pageData.top_offset, 10) || 0;
        const initialHeight = boxBody.offsetHeight;
        // 하단선 기준선 고정 (상단선만 내리면 높이가 줄어들며 하단선은 절대 이동하지 않음)
        const fixedBottomY = initialOffset + initialHeight;
        let currOffset = initialOffset;

        boxBody.classList.add("is-resizing");
        document.body.style.cursor = "ns-resize";

        const minBottomH = Math.max(34, Math.round(linePx + 16));
        const maxTopOffset = Math.max(0, fixedBottomY - minBottomH); // 하단 기준 1줄 남길 때까지 극단 허용

        const label = topHandle.querySelector(".handle-label");
        if (label) {
          label.textContent = `▲ 본문 시작선 내림: +${initialOffset}px`;
          label.style.display = "block";
        }

        function onMouseMove(ev) {
          const deltaY = ev.clientY - startY;
          currOffset = Math.max(0, Math.min(maxTopOffset, Math.round(initialOffset + deltaY)));
          // 하단선 고정: 높이 = fixedBottomY - currOffset
          const rawHeight = Math.max(minBottomH, fixedBottomY - currOffset);
          const candidateLines = Math.max(1, Math.floor((rawHeight - 16) / linePx));
          const newHeight = Math.max(minBottomH, Math.round(candidateLines * linePx + 18));

          boxBody.style.setProperty("margin-top", `${currOffset}px`, "important");
          boxBody.style.setProperty("height", `${newHeight}px`, "important");
          boxBody.style.setProperty("flex", "none", "important");

          if (label) {
            label.textContent = `▲ 시작선: +${currOffset}px (수용: ${candidateLines}행)`;
          }
          self.detectAndApplyLineOverlap(side);
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
            const rawHeight = Math.max(minBottomH, fixedBottomY - currOffset);
            const candidateLines = Math.max(1, Math.floor((rawHeight - 16) / linePx));
            pageData.max_lines = candidateLines;
            if (work.layout_config && Array.isArray(work.layout_config.pages) && work.layout_config.pages[pageIdx]) {
              work.layout_config.pages[pageIdx].top_offset = currOffset;
              work.layout_config.pages[pageIdx].max_lines = candidateLines;
            }
            self.renderSpread(self.currentWorkIndex, self.currentSpreadPart, true);
            self.saveLayoutConfigToServer(work.episode_no, cfg);
            if (window.showToast) {
              window.showToast(`📏 ${pageIdx + 1}면 본문 상단선이 조절되었습니다 (${candidateLines}행 수용).`, "info");
            }
          }
        }"""

    assert old_top_handle_logic in core, "old_top_handle_logic not found"
    core = core.replace(old_top_handle_logic, new_top_handle_logic, 1)

    # (2) attachFrameMoveHandle 호출 누락 보정 (중복 제거 & 분할 프레임 누락 추가)
    old_call_block = """          this.attachImagePanDrag(frame1, side, 1);
          this.attachFrame4WayResizeHandles(frame1, side, 1);
          this.attachFrameMoveHandle(frame1, side, 1);
          this.attachFrameMoveHandle(frame1, side, 1);
          layerImage.appendChild(frame1);
        } else {
          // [2단 분할 레이아웃: split_vertical, split_horizontal, main_detail]
          hideElem(imgElem);
          hideElem(placeholder);
          layerImage.classList.add(`layout-${layout}`);

          const cleanPath1 = imgFile1 ? ("/" + String(imgFile1).replace(/^(\.\/|\/)+/, '')) : "";
          const cleanPath2 = imgFile2 ? ("/" + String(imgFile2).replace(/^(\.\/|\/)+/, '')) : "";

          // 1번 프레임 생성 및 글상자 스타일 4변 여백 리사이즈 바인딩
          const frame1 = document.createElement("div");
          const isSel1 = (this.targetPageSlot === side && this.selectedSubFrame === 1);
          frame1.className = `dtp-image-frame ${layout === 'main_detail' ? 'frame-main' : ''} ${isSel1 ? 'is-selected' : ''}`;
          frame1.setAttribute("data-sub-frame", "1");

          const insets1 = pageData.frame_insets_1 || { top: 0, bottom: 0, left: 0, right: 0 };
          this.applyFrameInsetsStyle(frame1, insets1, layout, 1);
          frame1.innerHTML = `
            <div class="dtp-frame-crop">
              ${cleanPath1 ? `<img src="${cleanPath1}" alt="1번 삽화" draggable="false">` : '<div style="color:#A89F91; font-size:0.78rem;">그림을 등록하세요</div>'}
            </div>
            <span class="frame-tag">${layout === 'split_sandwich' ? '상단 그림' : '1번 그림'}</span>
            <button type="button" class="btn-frame-change" onclick="event.stopPropagation(); dtpEditor.openSlotImageFrameManager('${side}', 1)">🎨 1번 그림 변경</button>
          `;
          frame1.onclick = (e) => {
            e.stopPropagation();
            this.setTargetPageSlot(side);
            this.setSelectedSubFrame(1);
            this.switchToolboxTab('image');
          };
          const img1 = frame1.querySelector('img');
          if (img1) {
            const p1 = pageData.image_pan_1 || pageData.image_pan || {x:0, y:0};
            const s1 = pageData.image_scale_1 || 100;
            const f1 = pageData.image_filter_1 || pageData.image_filter || {vignette: 0, blur: 0, tone: 'none'};
            this.applyCustomImageStyle(img1, p1, s1, f1);
          }
          this.attachImagePanDrag(frame1, side, 1);
          this.attachFrame4WayResizeHandles(frame1, side, 1);

          // 2번 프레임 생성 및 글상자 스타일 4변 여백 리사이즈 바인딩
          const frame2 = document.createElement("div");
          const isSel2 = (this.targetPageSlot === side && this.selectedSubFrame === 2);
          frame2.className = `dtp-image-frame ${layout === 'main_detail' ? 'frame-detail' : ''} ${isSel2 ? 'is-selected' : ''}`;
          frame2.setAttribute("data-sub-frame", "2");

          const insets2 = pageData.frame_insets_2 || { top: 0, bottom: 0, left: 0, right: 0 };
          this.applyFrameInsetsStyle(frame2, insets2, layout, 2);
          frame2.innerHTML = `
            <div class="dtp-frame-crop">
              ${cleanPath2 ? `<img src="${cleanPath2}" alt="2번 삽화" draggable="false">` : '<div style="color:#A89F91; font-size:0.78rem;">그림을 등록하세요</div>'}
            </div>
            <span class="frame-tag">${layout === 'split_sandwich' ? '하단 그림' : '2번 그림'}</span>
            <button type="button" class="btn-frame-change" onclick="event.stopPropagation(); dtpEditor.openSlotImageFrameManager('${side}', 2)">🎨 2번 그림 변경</button>
          `;
          frame2.onclick = (e) => {
            e.stopPropagation();
            this.setTargetPageSlot(side);
            this.setSelectedSubFrame(2);
            this.switchToolboxTab('image');
          };
          const img2 = frame2.querySelector('img');
          if (img2) {
            const p2 = pageData.image_pan_2 || {x:0, y:0};
            const s2 = pageData.image_scale_2 || 100;
            const f2 = pageData.image_filter_2 || {vignette: 0, blur: 0, tone: 'none'};
            this.applyCustomImageStyle(img2, p2, s2, f2);
          }
          this.attachImagePanDrag(frame2, side, 2);
          this.attachFrame4WayResizeHandles(frame2, side, 2);
          this.attachFrameMoveHandle(frame2, side, 2);"""

    new_call_block = """          this.attachImagePanDrag(frame1, side, 1);
          this.attachFrame4WayResizeHandles(frame1, side, 1);
          this.attachFrameMoveHandle(frame1, side, 1);
          layerImage.appendChild(frame1);
        } else {
          // [2단 분할 레이아웃: split_vertical, split_horizontal, main_detail]
          hideElem(imgElem);
          hideElem(placeholder);
          layerImage.classList.add(`layout-${layout}`);

          const cleanPath1 = imgFile1 ? ("/" + String(imgFile1).replace(/^(\.\/|\/)+/, '')) : "";
          const cleanPath2 = imgFile2 ? ("/" + String(imgFile2).replace(/^(\.\/|\/)+/, '')) : "";

          // 1번 프레임 생성 및 글상자 스타일 4변 여백 리사이즈 바인딩
          const frame1 = document.createElement("div");
          const isSel1 = (this.targetPageSlot === side && this.selectedSubFrame === 1);
          frame1.className = `dtp-image-frame ${layout === 'main_detail' ? 'frame-main' : ''} ${isSel1 ? 'is-selected' : ''}`;
          frame1.setAttribute("data-sub-frame", "1");

          const insets1 = pageData.frame_insets_1 || { top: 0, bottom: 0, left: 0, right: 0 };
          this.applyFrameInsetsStyle(frame1, insets1, layout, 1);
          frame1.innerHTML = `
            <div class="dtp-frame-crop">
              ${cleanPath1 ? `<img src="${cleanPath1}" alt="1번 삽화" draggable="false">` : '<div style="color:#A89F91; font-size:0.78rem;">그림을 등록하세요</div>'}
            </div>
            <span class="frame-tag">${layout === 'split_sandwich' ? '상단 그림' : '1번 그림'}</span>
            <button type="button" class="btn-frame-change" onclick="event.stopPropagation(); dtpEditor.openSlotImageFrameManager('${side}', 1)">🎨 1번 그림 변경</button>
          `;
          frame1.onclick = (e) => {
            e.stopPropagation();
            this.setTargetPageSlot(side);
            this.setSelectedSubFrame(1);
            this.switchToolboxTab('image');
          };
          const img1 = frame1.querySelector('img');
          if (img1) {
            const p1 = pageData.image_pan_1 || pageData.image_pan || {x:0, y:0};
            const s1 = pageData.image_scale_1 || 100;
            const f1 = pageData.image_filter_1 || pageData.image_filter || {vignette: 0, blur: 0, tone: 'none'};
            this.applyCustomImageStyle(img1, p1, s1, f1);
          }
          this.attachImagePanDrag(frame1, side, 1);
          this.attachFrame4WayResizeHandles(frame1, side, 1);
          this.attachFrameMoveHandle(frame1, side, 1);

          // 2번 프레임 생성 및 글상자 스타일 4변 여백 리사이즈 바인딩
          const frame2 = document.createElement("div");
          const isSel2 = (this.targetPageSlot === side && this.selectedSubFrame === 2);
          frame2.className = `dtp-image-frame ${layout === 'main_detail' ? 'frame-detail' : ''} ${isSel2 ? 'is-selected' : ''}`;
          frame2.setAttribute("data-sub-frame", "2");

          const insets2 = pageData.frame_insets_2 || { top: 0, bottom: 0, left: 0, right: 0 };
          this.applyFrameInsetsStyle(frame2, insets2, layout, 2);
          frame2.innerHTML = `
            <div class="dtp-frame-crop">
              ${cleanPath2 ? `<img src="${cleanPath2}" alt="2번 삽화" draggable="false">` : '<div style="color:#A89F91; font-size:0.78rem;">그림을 등록하세요</div>'}
            </div>
            <span class="frame-tag">${layout === 'split_sandwich' ? '하단 그림' : '2번 그림'}</span>
            <button type="button" class="btn-frame-change" onclick="event.stopPropagation(); dtpEditor.openSlotImageFrameManager('${side}', 2)">🎨 2번 그림 변경</button>
          `;
          frame2.onclick = (e) => {
            e.stopPropagation();
            this.setTargetPageSlot(side);
            this.setSelectedSubFrame(2);
            this.switchToolboxTab('image');
          };
          const img2 = frame2.querySelector('img');
          if (img2) {
            const p2 = pageData.image_pan_2 || {x:0, y:0};
            const s2 = pageData.image_scale_2 || 100;
            const f2 = pageData.image_filter_2 || {vignette: 0, blur: 0, tone: 'none'};
            this.applyCustomImageStyle(img2, p2, s2, f2);
          }
          this.attachImagePanDrag(frame2, side, 2);
          this.attachFrame4WayResizeHandles(frame2, side, 2);
          this.attachFrameMoveHandle(frame2, side, 2);"""

    assert old_call_block in core, "old_call_block not found"
    core = core.replace(old_call_block, new_call_block, 1)

    with open('web/static/js/dtp_editor_core.js', 'w', encoding='utf-8') as f:
        f.write(core)
    print("✓ dtp_editor_core.js 패치 완료!")

    # 2. dtp_editor.css 스타일 강화 (가시성 및 z-index)
    with open('web/static/css/dtp_editor.css', 'r', encoding='utf-8') as f:
        css = f.read()

    css_fix = """
/* 그림틀 통째 위치 이동 핸들 바 (언제나 최상단 노출 보장) */
.dtp-frame-move-bar {
  position: absolute !important;
  top: 8px !important;
  left: 8px !important;
  z-index: 95 !important;
  display: inline-flex !important;
  align-items: center !important;
  gap: 5px !important;
  padding: 4px 10px !important;
  background: #1D4ED8 !important;
  color: #FFFFFF !important;
  font-size: 0.74rem !important;
  font-weight: 700 !important;
  border-radius: 4px !important;
  cursor: move !important;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.45) !important;
  user-select: none !important;
  pointer-events: auto !important;
  border: 1px solid rgba(255, 255, 255, 0.5) !important;
  visibility: visible !important;
  opacity: 1 !important;
  transition: transform 0.15s ease, background 0.15s ease !important;
}

.dtp-frame-move-bar:hover {
  background: #1E40AF !important;
  transform: scale(1.06) !important;
}

.dtp-frame-move-bar .move-icon {
  font-size: 0.85rem !important;
  line-height: 1 !important;
}

/* 선택된 그림틀은 텍스트 모드에서도 항상 위로 노출되고 이동 바와 핸들이 선명하게 표시됨 */
.book-spread .dtp-image-frame.is-selected {
  z-index: 40 !important;
  pointer-events: auto !important;
}
.book-spread .dtp-image-frame.is-selected .dtp-frame-move-bar {
  display: inline-flex !important;
  pointer-events: auto !important;
  z-index: 99 !important;
}
.book-spread .dtp-image-frame.is-selected .dtp-frame-handle {
  display: flex !important;
  pointer-events: auto !important;
  z-index: 85 !important;
}
"""
    # 기존 추가 블록 교체 또는 추가
    if '/* 그림틀 통째 위치 이동 핸들 바 */' in css:
        idx_c = css.find('/* 그림틀 통째 위치 이동 핸들 바 */')
        css = css[:idx_c] + css_fix.strip() + "\n"
    else:
        css += "\n" + css_fix.strip() + "\n"

    with open('web/static/css/dtp_editor.css', 'w', encoding='utf-8') as f:
        f.write(css)
    print("✓ dtp_editor.css 패치 완료!")

if __name__ == '__main__':
    apply_fixes()

