# -*- coding: utf-8 -*-
"""
1) 그림틀 이동 바 '✥ ✥' 중복 제거 -> 단일 '✥ 그림틀 위치 이동'으로 정돈
2) 글상자에도 '✥ 본문 글상자 이동' 드래그 무브 핸들 바 및 위치이동 컨트롤 추가
"""

def patch_textbox_and_frame_move():
    # 1. dtp_editor_core.js 수정
    with open('web/static/js/dtp_editor_core.js', 'r', encoding='utf-8') as f:
        core = f.read()

    # (1) 그림틀 이동 바 태그 중복 제거
    old_tag_text = """        const tagText = (frameNum === 2) ? "✥ 2번 그림틀 이동" : (frameEl.parentElement && frameEl.parentElement.classList.contains('layout-split_vertical') ? "✥ 1번 그림틀 이동" : "✥ 그림틀 위치 이동");
        moveHandle.innerHTML = `<span class="move-icon">✥</span> <span class="move-text">${tagText}</span>`;"""

    new_tag_text = """        const tagText = (frameNum === 2) ? "2번 그림틀 이동" : (frameEl.parentElement && frameEl.parentElement.classList.contains('layout-split_vertical') ? "1번 그림틀 이동" : "그림틀 위치 이동");
        moveHandle.innerHTML = `<span class="move-icon">✥</span> <span class="move-text">${tagText}</span>`;"""

    assert old_tag_text in core, "old_tag_text not found in dtp_editor_core.js"
    core = core.replace(old_tag_text, new_tag_text, 1)

    # (2) attachResizeHandles 내부에 글상자 통째 이동 핸들(dtp-box-move-bar) 추가
    old_attach_resize = """      let rightHandle = boxBody.querySelector(".dtp-resize-handle.handle-right");
      if (!rightHandle) {
        rightHandle = document.createElement("div");
        rightHandle.className = "dtp-resize-handle handle-right";
        rightHandle.innerHTML = '<div class="handle-bar-pill"></div><span class="handle-label">우측 여백 ↔ ▶</span>';
        boxBody.appendChild(rightHandle);
      }"""

    new_attach_resize = """      let rightHandle = boxBody.querySelector(".dtp-resize-handle.handle-right");
      if (!rightHandle) {
        rightHandle = document.createElement("div");
        rightHandle.className = "dtp-resize-handle handle-right";
        rightHandle.innerHTML = '<div class="handle-bar-pill"></div><span class="handle-label">우측 여백 ↔ ▶</span>';
        boxBody.appendChild(rightHandle);
      }

      // 글상자 통째 위치 이동 드래그 핸들 바 (크기 불변 이동)
      let moveBoxHandle = boxBody.querySelector(".dtp-box-move-bar");
      if (!moveBoxHandle) {
        moveBoxHandle = document.createElement("div");
        moveBoxHandle.className = "dtp-box-move-bar";
        moveBoxHandle.innerHTML = '<span class="move-icon">✥</span> <span class="move-text">본문 글상자 이동</span>';
        moveBoxHandle.title = "마우스로 누른 채 끌면 글상자 크기(폭/높이)를 유지한 채 원하는 위치로 통째로 이동합니다.";
        boxBody.appendChild(moveBoxHandle);
      }"""

    assert old_attach_resize in core, "old_attach_resize not found"
    core = core.replace(old_attach_resize, new_attach_resize, 1)

    # (3) attachResizeHandles 내부 moveBoxHandle.onmousedown 이벤트 바인딩
    old_resize_event_end = """        window.addEventListener("mousemove", onMouseMove, true);
        window.addEventListener("mouseup", onMouseUp, true);
      };
    }"""

    new_resize_event_end = """        window.addEventListener("mousemove", onMouseMove, true);
        window.addEventListener("mouseup", onMouseUp, true);
      };

      // 5) 글상자 통째 위치 이동 드래그 이벤트 (크기 불변)
      moveBoxHandle.onmousedown = function(e) {
        e.preventDefault();
        e.stopPropagation();

        const slot = side.toLowerCase();
        self.setTargetPageSlot(slot);

        boxBody.classList.add("is-moving-box");
        document.body.style.cursor = "move";
        document.body.style.userSelect = "none";

        const startX = e.clientX;
        const startY = e.clientY;

        const initialTop = parseInt(pageData.top_offset, 10) || 0;
        const initialLeft = parseInt(pageData.left_offset, 10) || 0;
        const initialRight = parseInt(pageData.right_offset, 10) || 0;
        const boxH = boxBody.offsetHeight;

        const safeBoundary = boxBody.closest(".dtp-safe-boundary") || boxBody.parentElement;
        const boundaryW = safeBoundary ? safeBoundary.clientWidth : 380;
        const maxTop = Math.max(0, 517 - boxH);

        function onMouseMove(ev) {
          const deltaX = ev.clientX - startX;
          const deltaY = ev.clientY - startY;

          // 세로 이동: 높이 불변
          let newTop = Math.max(0, Math.min(maxTop, Math.round(initialTop + deltaY)));

          // 가로 이동: 너비 불변
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

          newLeft = Math.max(0, Math.round(newLeft));
          newRight = Math.max(0, Math.round(newRight));

          boxBody.style.setProperty("margin-top", `${newTop}px`, "important");
          boxBody.style.setProperty("height", `${boxH}px`, "important");
          boxBody.style.setProperty("flex", "none", "important");
          boxBody.style.setProperty("margin-left", `${newLeft}px`, "important");
          boxBody.style.setProperty("margin-right", `${newRight}px`, "important");
          boxBody.style.setProperty("width", `calc(100% - ${newLeft + newRight}px)`, "important");

          self.detectAndApplyLineOverlap(side);
        }

        function onMouseUp() {
          window.removeEventListener("mousemove", onMouseMove, true);
          window.removeEventListener("mouseup", onMouseUp, true);
          boxBody.classList.remove("is-moving-box");
          document.body.style.cursor = "";
          document.body.style.userSelect = "";

          const curTop = parseInt(boxBody.style.marginTop, 10) || initialTop;
          const curLeft = parseInt(boxBody.style.marginLeft, 10) || initialLeft;
          const curRight = parseInt(boxBody.style.marginRight, 10) || initialRight;

          if (curTop !== initialTop || curLeft !== initialLeft || curRight !== initialRight) {
            self.pushUndoState();
            pageData.top_offset = curTop;
            pageData.left_offset = curLeft;
            pageData.right_offset = curRight;
            if (work.layout_config && Array.isArray(work.layout_config.pages) && work.layout_config.pages[pageIdx]) {
              work.layout_config.pages[pageIdx].top_offset = curTop;
              work.layout_config.pages[pageIdx].left_offset = curLeft;
              work.layout_config.pages[pageIdx].right_offset = curRight;
            }
            self.renderSpread(self.currentWorkIndex, self.currentSpreadPart, true);
            self.saveLayoutConfigToServer(work.episode_no, cfg);
            if (window.showToast) {
              window.showToast(`📄 ${pageIdx + 1}면 본문 글상자 위치가 이동되었습니다.`, "info");
            }
          }
        }

        window.addEventListener("mousemove", onMouseMove, true);
        window.addEventListener("mouseup", onMouseUp, true);
      };
    }"""

    assert old_resize_event_end in core, "old_resize_event_end not found"
    core = core.replace(old_resize_event_end, new_resize_event_end, 1)

    # (4) moveSelectedTextBox 메서드 추가
    move_tb_anchor = """    /**
     * 그림틀(프레임) 통째 위치 이동 인터랙티브 드래그 핸들 바인딩
     */"""

    new_move_tb_method = """    /**
     * 선택된 글상자를 크기 변화 없이 통째로 (deltaX, deltaY)만큼 이동
     */
    moveSelectedTextBox(deltaX, deltaY) {
      const slot = this.targetPageSlot || 'left';
      const work = this.getCurrentWork();
      if (!work) return;

      const cfg = this.getNormalizedConfig(work);
      const pageIdx = (this.currentSpreadPart - 1) * 2 + (slot === 'left' ? 0 : 1);
      if (!cfg.pages[pageIdx]) cfg.pages[pageIdx] = {};
      const pageData = cfg.pages[pageIdx];

      const capSide = (slot === 'right' || slot === 'Right') ? 'Right' : 'Left';
      const boxBody = document.getElementById(`dtpBoxBody${capSide}`);
      const boxH = boxBody ? boxBody.offsetHeight : 100;

      const initialTop = parseInt(pageData.top_offset, 10) || 0;
      const initialLeft = parseInt(pageData.left_offset, 10) || 0;
      const initialRight = parseInt(pageData.right_offset, 10) || 0;

      const safeBoundary = boxBody ? (boxBody.closest(".dtp-safe-boundary") || boxBody.parentElement) : null;
      const boundaryW = safeBoundary ? safeBoundary.clientWidth : 380;
      const maxTop = Math.max(0, 517 - boxH);

      let newTop = Math.max(0, Math.min(maxTop, initialTop + deltaY));
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

      newLeft = Math.max(0, Math.round(newLeft));
      newRight = Math.max(0, Math.round(newRight));

      pageData.top_offset = newTop;
      pageData.left_offset = newLeft;
      pageData.right_offset = newRight;

      if (work.layout_config && Array.isArray(work.layout_config.pages) && work.layout_config.pages[pageIdx]) {
        work.layout_config.pages[pageIdx].top_offset = newTop;
        work.layout_config.pages[pageIdx].left_offset = newLeft;
        work.layout_config.pages[pageIdx].right_offset = newRight;
      }

      this.renderSpread(this.currentWorkIndex, this.currentSpreadPart, true);
      this.saveLayoutConfigToServer(work.episode_no, cfg);
    }

    /**
     * 그림틀(프레임) 통째 위치 이동 인터랙티브 드래그 핸들 바인딩
     */"""

    assert move_tb_anchor in core, "move_tb_anchor not found"
    core = core.replace(move_tb_anchor, new_move_tb_method, 1)

    with open('web/static/js/dtp_editor_core.js', 'w', encoding='utf-8') as f:
        f.write(core)
    print("✓ dtp_editor_core.js 패치 완료!")

    # 2. dtp_editor.css 수정 (글상자 이동 바 스타일)
    with open('web/static/css/dtp_editor.css', 'r', encoding='utf-8') as f:
        css = f.read()

    css_box_addition = """
/* 글상자 통째 위치 이동 핸들 바 */
.dtp-box-move-bar {
  position: absolute !important;
  top: -13px !important;
  left: 6px !important;
  z-index: 78 !important;
  display: inline-flex !important;
  align-items: center !important;
  gap: 4px !important;
  padding: 2px 8px !important;
  background: #C53030 !important;
  color: #FFFFFF !important;
  font-size: 0.72rem !important;
  font-weight: 700 !important;
  border-radius: 4px !important;
  cursor: move !important;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.3) !important;
  user-select: none !important;
  pointer-events: auto !important;
  border: 1px solid rgba(255, 255, 255, 0.45) !important;
  transition: background 0.15s ease, transform 0.15s ease !important;
}

.dtp-box-move-bar:hover {
  background: #9B2C2C !important;
  transform: scale(1.05) !important;
}

.dtp-box-move-bar .move-icon {
  font-size: 0.8rem !important;
  line-height: 1 !important;
}

.dtp-guide-box.is-moving-box {
  box-shadow: 0 0 0 2.5px #E53E3E, 0 8px 24px rgba(229, 62, 62, 0.3) !important;
  transition: none !important;
}
"""
    if '.dtp-box-move-bar' not in css:
        css += css_box_addition
        with open('web/static/css/dtp_editor.css', 'w', encoding='utf-8') as f:
            f.write(css)
        print("✓ dtp_editor.css 글상자 이동 바 스타일 추가 완료!")

    # 3. index.html 도구상자 글 탭에 '상자 위치이동' 버튼 그룹 추가
    with open('web/templates/index.html', 'r', encoding='utf-8') as f:
        html = f.read()

    html_anchor = """                  <!-- 구분선: [그림+글] 겹침 전용 가독성 조율기 -->
                  <div
                    style="margin-top: 8px; padding-top: 8px; border-top: 1px dashed #E2D7C8; display: flex; align-items: center; justify-content: space-between;">"""

    html_addition = """                  <!-- 4-2. 본문 글상자 통째 위치 이동 (크기 불변) -->
                  <div class="dtp-control-row" title="글상자 크기를 유지한 채 캔버스 안에서 위치를 상·하·좌·우로 통째로 이동합니다. (글상자 좌상단의 ✥ 핸들로도 마우스 드래그 가능)">
                    <span class="dtp-row-label">상자 위치이동</span>
                    <div class="dtp-row-control" style="display: flex; gap: 4px;">
                      <button type="button" class="btn-control-sub" style="flex: 1; padding: 4px 2px; font-size: 0.72rem;" onclick="dtpEditor.moveSelectedTextBox(0, -15)" title="위로 15px 이동">▲ 위로</button>
                      <button type="button" class="btn-control-sub" style="flex: 1; padding: 4px 2px; font-size: 0.72rem;" onclick="dtpEditor.moveSelectedTextBox(0, 15)" title="아래로 15px 이동">▼ 아래</button>
                      <button type="button" class="btn-control-sub" style="flex: 1; padding: 4px 2px; font-size: 0.72rem;" onclick="dtpEditor.moveSelectedTextBox(-15, 0)" title="왼쪽으로 15px 이동">◀ 좌로</button>
                      <button type="button" class="btn-control-sub" style="flex: 1; padding: 4px 2px; font-size: 0.72rem;" onclick="dtpEditor.moveSelectedTextBox(15, 0)" title="오른쪽으로 15px 이동">▶ 우로</button>
                    </div>
                  </div>

                  <!-- 구분선: [그림+글] 겹침 전용 가독성 조율기 -->
                  <div
                    style="margin-top: 8px; padding-top: 8px; border-top: 1px dashed #E2D7C8; display: flex; align-items: center; justify-content: space-between;">"""

    if html_anchor in html and '상자 위치이동' not in html:
        html = html.replace(html_anchor, html_addition, 1)
        with open('web/templates/index.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("✓ index.html 글 조판 도구상자에 '상자 위치이동' 컨트롤 추가 완료!")

if __name__ == '__main__':
    patch_textbox_and_frame_move()

