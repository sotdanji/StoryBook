# -*- coding: utf-8 -*-
"""
그림틀 통째 이동(Move Entire Frame) 기능 추가 패치 스크립트
"""

def patch_frame_move():
    # 1. dtp_editor_core.js 수정
    with open('web/static/js/dtp_editor_core.js', 'r', encoding='utf-8') as f:
        core = f.read()

    # attachFrame4WayResizeHandles 호출 부근에 attachFrameMoveHandle 추가
    # 1) single frame1
    anchor1 = """          this.attachImagePanDrag(frame1, side, 1);
          this.attachFrame4WayResizeHandles(frame1, side, 1);"""
    rep1 = """          this.attachImagePanDrag(frame1, side, 1);
          this.attachFrame4WayResizeHandles(frame1, side, 1);
          this.attachFrameMoveHandle(frame1, side, 1);"""
    assert anchor1 in core, "anchor1 not found"
    core = core.replace(anchor1, rep1, 1)

    # 2) split frame1
    anchor2 = """          this.attachImagePanDrag(frame1, side, 1);
          this.attachFrame4WayResizeHandles(frame1, side, 1);"""
    rep2 = """          this.attachImagePanDrag(frame1, side, 1);
          this.attachFrame4WayResizeHandles(frame1, side, 1);
          this.attachFrameMoveHandle(frame1, side, 1);"""
    assert anchor2 in core, "anchor2 not found"
    core = core.replace(anchor2, rep2, 1)

    # 3) split frame2
    anchor3 = """          this.attachImagePanDrag(frame2, side, 2);
          this.attachFrame4WayResizeHandles(frame2, side, 2);"""
    rep3 = """          this.attachImagePanDrag(frame2, side, 2);
          this.attachFrame4WayResizeHandles(frame2, side, 2);
          this.attachFrameMoveHandle(frame2, side, 2);"""
    assert anchor3 in core, "anchor3 not found"
    core = core.replace(anchor3, rep3, 1)

    # attachFrameMoveHandle 및 moveSelectedFrame 메서드 본문 추가
    method_anchor = """    attachFrame4WayResizeHandles(frameEl, side, frameNum) {"""
    new_methods = """    /**
     * 그림틀(프레임) 통째 위치 이동 인터랙티브 드래그 핸들 바인딩
     */
    attachFrameMoveHandle(frameEl, side, frameNum) {
      let moveHandle = frameEl.querySelector('.dtp-frame-move-bar');
      if (!moveHandle) {
        moveHandle = document.createElement("div");
        moveHandle.className = "dtp-frame-move-bar";
        const tagText = (frameNum === 2) ? "✥ 2번 그림틀 이동" : (frameEl.parentElement && frameEl.parentElement.classList.contains('layout-split_vertical') ? "✥ 1번 그림틀 이동" : "✥ 그림틀 위치 이동");
        moveHandle.innerHTML = `<span class="move-icon">✥</span> <span class="move-text">${tagText}</span>`;
        moveHandle.title = "마우스로 누른 채 끌면 크기 변화 없이 원하는 위치로 그림틀이 통째로 이동합니다.";
        frameEl.appendChild(moveHandle);
      }

      moveHandle.onmousedown = (e) => {
        e.preventDefault();
        e.stopPropagation();

        const slot = side.toLowerCase();
        this.setTargetPageSlot(slot);
        this.setSelectedSubFrame(frameNum);

        frameEl.classList.add("is-moving-frame");
        document.body.style.cursor = "move";
        document.body.style.userSelect = "none";

        const startX = e.clientX;
        const startY = e.clientY;

        const work = this.getCurrentWork();
        const cfg = this.getNormalizedConfig(work);
        const pageIdx = (this.currentSpreadPart - 1) * 2 + (slot === 'left' ? 0 : 1);
        if (!cfg.pages[pageIdx]) cfg.pages[pageIdx] = {};
        const insetsKey = (frameNum === 2) ? 'frame_insets_2' : 'frame_insets_1';
        cfg.pages[pageIdx][insetsKey] = cfg.pages[pageIdx][insetsKey] || { top: 0, bottom: 0, left: 0, right: 0 };
        const insets = cfg.pages[pageIdx][insetsKey];

        const initialTop = parseInt(insets.top, 10) || 0;
        const initialBottom = parseInt(insets.bottom, 10) || 0;
        const initialLeft = parseInt(insets.left, 10) || 0;
        const initialRight = parseInt(insets.right, 10) || 0;

        const layout = cfg.pages[pageIdx].image_layout || 'single';

        const onMouseMove = (ev) => {
          const deltaX = ev.clientX - startX;
          const deltaY = ev.clientY - startY;

          // 세로 이동 (top + bottom 합계 보존 -> 높이 불변)
          let newTop = initialTop + deltaY;
          let newBottom = initialBottom - deltaY;

          if (newTop < 0) {
            newBottom += newTop;
            newTop = 0;
          }
          if (newBottom < 0) {
            newTop += newBottom;
            newBottom = 0;
          }

          // 가로 이동 (left + right 합계 보존 -> 너비 불변)
          let newLeft = initialLeft + deltaX;
          let newRight = initialRight - deltaX;

          if (newLeft < 0) {
            newRight += newLeft;
            newLeft = 0;
          }
          if (newRight < 0) {
            newLeft += newRight;
            newRight = 0;
          }

          insets.top = Math.max(0, Math.round(newTop));
          insets.bottom = Math.max(0, Math.round(newBottom));
          insets.left = Math.max(0, Math.round(newLeft));
          insets.right = Math.max(0, Math.round(newRight));

          this.applyFrameInsetsStyle(frameEl, insets, layout, frameNum);
          this.detectAndApplyLineOverlap(slot);
        };

        const onMouseUp = () => {
          frameEl.classList.remove("is-moving-frame");
          document.body.style.cursor = "";
          document.body.style.userSelect = "";
          window.removeEventListener("mousemove", onMouseMove, true);
          window.removeEventListener("mouseup", onMouseUp, true);

          this.saveLayoutConfigToServer(work.episode_no, cfg);
          if (window.showToast) {
            window.showToast(`🖼️ 그림틀 위치가 이동되었습니다.`, "info");
          }
        };

        window.addEventListener("mousemove", onMouseMove, true);
        window.addEventListener("mouseup", onMouseUp, true);
      };
    }

    /**
     * 선택된 그림틀을 크기 변화 없이 통째로 (deltaX, deltaY)만큼 이동
     */
    moveSelectedFrame(deltaX, deltaY) {
      const slot = this.targetPageSlot || 'left';
      const frameNum = this.selectedSubFrame || 1;
      const work = this.getCurrentWork();
      if (!work) return;

      const cfg = this.getNormalizedConfig(work);
      const pageIdx = (this.currentSpreadPart - 1) * 2 + (slot === 'left' ? 0 : 1);
      if (!cfg.pages[pageIdx]) cfg.pages[pageIdx] = {};
      const insetsKey = (frameNum === 2) ? 'frame_insets_2' : 'frame_insets_1';
      cfg.pages[pageIdx][insetsKey] = cfg.pages[pageIdx][insetsKey] || { top: 0, bottom: 0, left: 0, right: 0 };
      const insets = cfg.pages[pageIdx][insetsKey];

      const initialTop = parseInt(insets.top, 10) || 0;
      const initialBottom = parseInt(insets.bottom, 10) || 0;
      const initialLeft = parseInt(insets.left, 10) || 0;
      const initialRight = parseInt(insets.right, 10) || 0;

      let newTop = initialTop + deltaY;
      let newBottom = initialBottom - deltaY;
      if (newTop < 0) {
        newBottom += newTop;
        newTop = 0;
      }
      if (newBottom < 0) {
        newTop += newBottom;
        newBottom = 0;
      }

      let newLeft = initialLeft + deltaX;
      let newRight = initialRight - deltaX;
      if (newLeft < 0) {
        newRight += newLeft;
        newLeft = 0;
      }
      if (newRight < 0) {
        newLeft += newRight;
        newRight = 0;
      }

      insets.top = Math.max(0, Math.round(newTop));
      insets.bottom = Math.max(0, Math.round(newBottom));
      insets.left = Math.max(0, Math.round(newLeft));
      insets.right = Math.max(0, Math.round(newRight));

      const capSide = (slot === 'right' || slot === 'Right') ? 'Right' : 'Left';
      const layer = document.getElementById(`dtpLayerImage${capSide}`);
      const frameEl = layer ? (layer.querySelector(`.dtp-image-frame[data-sub-frame="${frameNum}"]`) || layer.querySelector('.dtp-image-frame')) : null;
      const layout = cfg.pages[pageIdx].image_layout || 'single';

      if (frameEl) {
        this.applyFrameInsetsStyle(frameEl, insets, layout, frameNum);
      }
      this.detectAndApplyLineOverlap(slot);
      this.saveLayoutConfigToServer(work.episode_no, cfg);
    }

    attachFrame4WayResizeHandles(frameEl, side, frameNum) {"""

    assert method_anchor in core, "method_anchor not found"
    core = core.replace(method_anchor, new_methods, 1)

    with open('web/static/js/dtp_editor_core.js', 'w', encoding='utf-8') as f:
        f.write(core)
    print("✓ dtp_editor_core.js 패치 완료!")

    # 2. dtp_editor.css 스타일 추가
    with open('web/static/css/dtp_editor.css', 'r', encoding='utf-8') as f:
        css = f.read()

    css_addition = """
/* 그림틀 통째 위치 이동 핸들 바 */
.dtp-frame-move-bar {
  position: absolute !important;
  top: 6px !important;
  left: 6px !important;
  z-index: 68 !important;
  display: inline-flex !important;
  align-items: center !important;
  gap: 5px !important;
  padding: 3px 9px !important;
  background: rgba(30, 64, 175, 0.92) !important;
  color: #FFFFFF !important;
  font-size: 0.73rem !important;
  font-weight: 600 !important;
  border-radius: 4px !important;
  cursor: move !important;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.3) !important;
  user-select: none !important;
  pointer-events: auto !important;
  transition: background 0.15s ease, transform 0.15s ease !important;
}

.dtp-frame-move-bar:hover {
  background: #1D4ED8 !important;
  transform: scale(1.05) !important;
}

.dtp-frame-move-bar .move-icon {
  font-size: 0.85rem !important;
  line-height: 1 !important;
}

.dtp-image-frame.is-moving-frame {
  box-shadow: 0 0 0 2.5px #2563EB, 0 8px 24px rgba(37, 99, 235, 0.35) !important;
  transition: none !important;
}
"""
    if '.dtp-frame-move-bar' not in css:
        css += css_addition
        with open('web/static/css/dtp_editor.css', 'w', encoding='utf-8') as f:
            f.write(css)
        print("✓ dtp_editor.css 패치 완료!")

    # 3. index.html 도구상자에 그림틀 위치 이동 버튼 그룹 추가
    with open('web/templates/index.html', 'r', encoding='utf-8') as f:
        html = f.read()

    target_html_anchor = """                    <!-- 2-2. 그림틀 조절 및 크기 복원 -->
                    <div class="dtp-control-row" title="그림틀 테두리의 상·하·좌·우 핸들을 마우스로 드래그하여 사각형 크기를 줄일 수 있습니다.">
                      <span class="dtp-row-label">그림틀 조절</span>
                      <div class="dtp-row-control">
                        <button type="button" class="btn-control-sub" style="width: 100%; font-size: 0.72rem;"
                          onclick="dtpEditor.resetSelectedFrameRect()" title="선택된 그림틀을 100% 꽉 채운 원래 크기로 복원합니다.">⟲ 선택 그림틀
                          100% 크기 복원</button>
                      </div>
                    </div>"""

    new_html_content = """                    <!-- 2-2. 그림틀 조절 및 크기 복원 -->
                    <div class="dtp-control-row" title="그림틀 테두리의 상·하·좌·우 핸들을 마우스로 드래그하여 사각형 크기를 줄일 수 있습니다.">
                      <span class="dtp-row-label">그림틀 크기</span>
                      <div class="dtp-row-control">
                        <button type="button" class="btn-control-sub" style="width: 100%; font-size: 0.72rem;"
                          onclick="dtpEditor.resetSelectedFrameRect()" title="선택된 그림틀을 100% 꽉 채운 원래 크기로 복원합니다.">⟲ 선택 그림틀 100% 크기 복원</button>
                      </div>
                    </div>

                    <!-- 2-3. 그림틀 통째 위치 이동 (크기 불변) -->
                    <div class="dtp-control-row" title="그림틀 크기를 유지한 채 캔버스 안에서 위치를 상·하·좌·우로 통째로 이동합니다. (그림틀 좌상단의 ✥ 핸들로도 마우스 드래그 가능)">
                      <span class="dtp-row-label">틀 위치이동</span>
                      <div class="dtp-row-control" style="display: flex; gap: 4px;">
                        <button type="button" class="btn-control-sub" style="flex: 1; padding: 4px 2px; font-size: 0.72rem;" onclick="dtpEditor.moveSelectedFrame(0, -15)" title="위로 15px 이동">▲ 위로</button>
                        <button type="button" class="btn-control-sub" style="flex: 1; padding: 4px 2px; font-size: 0.72rem;" onclick="dtpEditor.moveSelectedFrame(0, 15)" title="아래로 15px 이동">▼ 아래</button>
                        <button type="button" class="btn-control-sub" style="flex: 1; padding: 4px 2px; font-size: 0.72rem;" onclick="dtpEditor.moveSelectedFrame(-15, 0)" title="왼쪽으로 15px 이동">◀ 좌로</button>
                        <button type="button" class="btn-control-sub" style="flex: 1; padding: 4px 2px; font-size: 0.72rem;" onclick="dtpEditor.moveSelectedFrame(15, 0)" title="오른쪽으로 15px 이동">▶ 우로</button>
                      </div>
                    </div>"""

    if target_html_anchor in html:
        html = html.replace(target_html_anchor, new_html_content, 1)
        with open('web/templates/index.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("✓ index.html 도구상자 틀 위치이동 컨트롤 추가 완료!")
    else:
        print("- target_html_anchor not found in index.html")

if __name__ == '__main__':
    patch_frame_move()

