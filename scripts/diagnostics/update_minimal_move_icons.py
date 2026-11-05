# -*- coding: utf-8 -*-
"""
1) 이동 바 긴 텍스트 제거 -> 심플하고 세련된 미니 이모지 '✥' 버튼으로 전환
2) 글상자 이동 바 위치를 상단선 바깥에 밀착 배치하고 라벨과 겹침 완벽 분리
"""

def patch_minimal_move_icons():
    # 1. dtp_editor_core.js 수정
    with open('web/static/js/dtp_editor_core.js', 'r', encoding='utf-8') as f:
        core = f.read()

    # (1) 그림틀 이동 핸들: 텍스트 제거, 미니 '✥' 아이콘만 표시
    old_frame_handle = """      let moveHandle = frameEl.querySelector('.dtp-frame-move-bar');
      if (!moveHandle) {
        moveHandle = document.createElement("div");
        moveHandle.className = "dtp-frame-move-bar";
        const tagText = (frameNum === 2) ? "2번 그림틀 이동" : (frameEl.parentElement && frameEl.parentElement.classList.contains('layout-split_vertical') ? "1번 그림틀 이동" : "그림틀 위치 이동");
        moveHandle.innerHTML = `<span class="move-icon">✥</span> <span class="move-text">${tagText}</span>`;
        moveHandle.title = "마우스로 누른 채 끌면 크기 변화 없이 원하는 위치로 그림틀이 통째로 이동합니다.";
        frameEl.appendChild(moveHandle);
      }"""

    new_frame_handle = """      let moveHandle = frameEl.querySelector('.dtp-frame-move-bar');
      if (!moveHandle) {
        moveHandle = document.createElement("div");
        moveHandle.className = "dtp-frame-move-bar";
        moveHandle.innerHTML = '<span class="move-icon">✥</span>';
        moveHandle.title = (frameNum === 2 ? "2번 그림틀 위치 이동 (마우스로 드래그)" : "그림틀 위치 이동 (마우스로 드래그)");
        frameEl.appendChild(moveHandle);
      }"""

    assert old_frame_handle in core, "old_frame_handle not found in dtp_editor_core.js"
    core = core.replace(old_frame_handle, new_frame_handle, 1)

    # (2) 글상자 이동 핸들: 텍스트 제거, 미니 '✥' 아이콘만 표시
    old_box_handle = """      // 글상자 통째 위치 이동 드래그 핸들 바 (크기 불변 이동)
      let moveBoxHandle = boxBody.querySelector(".dtp-box-move-bar");
      if (!moveBoxHandle) {
        moveBoxHandle = document.createElement("div");
        moveBoxHandle.className = "dtp-box-move-bar";
        moveBoxHandle.innerHTML = '<span class="move-icon">✥</span> <span class="move-text">본문 글상자 이동</span>';
        moveBoxHandle.title = "마우스로 누른 채 끌면 글상자 크기(폭/높이)를 유지한 채 원하는 위치로 통째로 이동합니다.";
        boxBody.appendChild(moveBoxHandle);
      }"""

    new_box_handle = """      // 글상자 통째 위치 이동 드래그 핸들 바 (상단선에 밀착한 미니 ✥ 아이콘)
      let moveBoxHandle = boxBody.querySelector(".dtp-box-move-bar");
      if (!moveBoxHandle) {
        moveBoxHandle = document.createElement("div");
        moveBoxHandle.className = "dtp-box-move-bar";
        moveBoxHandle.innerHTML = '<span class="move-icon">✥</span>';
        moveBoxHandle.title = "본문 글상자 위치 이동 (마우스로 드래그)";
        boxBody.appendChild(moveBoxHandle);
      }"""

    assert old_box_handle in core, "old_box_handle not found in dtp_editor_core.js"
    core = core.replace(old_box_handle, new_box_handle, 1)

    with open('web/static/js/dtp_editor_core.js', 'w', encoding='utf-8') as f:
        f.write(core)
    print("✓ dtp_editor_core.js 패치 완료!")

    # 2. dtp_editor.css 수정 (미니 이모지 버튼 스타일 및 겹침 방지)
    with open('web/static/css/dtp_editor.css', 'r', encoding='utf-8') as f:
        css = f.read()

    # 그림틀 이동 바 스타일 업데이트
    old_frame_bar_css = """/* 그림틀 통째 위치 이동 핸들 바 (언제나 최상단 노출 보장) */
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
}"""

    new_frame_bar_css = """/* 그림틀 통째 위치 이동 핸들 바 (컴팩트 미니 ✥ 버튼) */
.dtp-frame-move-bar {
  position: absolute !important;
  top: 6px !important;
  left: 6px !important;
  z-index: 95 !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  width: 24px !important;
  height: 24px !important;
  padding: 0 !important;
  background: rgba(29, 78, 216, 0.92) !important;
  color: #FFFFFF !important;
  font-size: 0.88rem !important;
  font-weight: 700 !important;
  border-radius: 4px !important;
  cursor: move !important;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.4) !important;
  user-select: none !important;
  pointer-events: auto !important;
  border: 1px solid rgba(255, 255, 255, 0.6) !important;
  visibility: visible !important;
  opacity: 1 !important;
  transition: transform 0.15s ease, background 0.15s ease !important;
}"""

    if old_frame_bar_css in css:
        css = core = css.replace(old_frame_bar_css, new_frame_bar_css, 1)

    # 글상자 이동 바 스타일 업데이트
    old_box_bar_css = """/* 글상자 통째 위치 이동 핸들 바 */
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
}"""

    new_box_bar_css = """/* 글상자 통째 위치 이동 핸들 바 (상단선 바깥에 밀착한 미니 ✥ 버튼) */
.dtp-box-move-bar {
  position: absolute !important;
  top: -11px !important;
  left: 8px !important;
  z-index: 80 !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  width: 22px !important;
  height: 22px !important;
  padding: 0 !important;
  background: #C53030 !important;
  color: #FFFFFF !important;
  font-size: 0.85rem !important;
  font-weight: 700 !important;
  border-radius: 4px !important;
  cursor: move !important;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.35) !important;
  user-select: none !important;
  pointer-events: auto !important;
  border: 1px solid rgba(255, 255, 255, 0.6) !important;
  transition: background 0.15s ease, transform 0.15s ease !important;
}

/* 본문 글상자 텍스트 라벨 위치를 이동 버튼 옆(left: 36px)으로 이동하여 겹침 방지 */
.dtp-page .dtp-guide-label.label-body,
.dtp-guide-box .dtp-guide-label.label-body {
  left: 36px !important;
  top: -11px !important;
}"""

    if old_box_bar_css in css:
        css = css.replace(old_box_bar_css, new_box_bar_css, 1)

    with open('web/static/css/dtp_editor.css', 'w', encoding='utf-8') as f:
        f.write(css)
    print("✓ dtp_editor.css 패치 완료!")

if __name__ == '__main__':
    patch_minimal_move_icons()

