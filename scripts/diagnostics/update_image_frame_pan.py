# -*- coding: utf-8 -*-
"""
그림틀 내부 원형 비율 보존 및 패닝(Pan) 정상화 패치 스크립트
"""

def patch_image_frame_system():
    # 1. dtp_editor_core.js 패치
    with open('web/static/js/dtp_editor_core.js', 'r', encoding='utf-8') as f:
        core_content = f.read()

    # applyFrameInsetsStyle 내부의 마스크 역보정 코드 교체
    target_insets_old = """      // [핵심: 창문 마스크 원본 보존 시스템]
      // 내부 img가 프레임에 맞춰 찌그러지거나 축소되지 않도록 기준 캔버스 크기(refW, refH)를 유지하고,
      // 프레임 오프셋(-left, -top)만큼 상대 위치를 역보정하여 그림 위치를 제자리에 고정합니다.
      const img = frameEl.querySelector('img');
      if (img && refW > 0 && refH > 0) {
        img.style.setProperty('position', 'absolute', 'important');
        img.style.setProperty('width', `${refW}px`, 'important');
        img.style.setProperty('height', `${refH}px`, 'important');
        img.style.setProperty('max-width', 'none', 'important');
        img.style.setProperty('max-height', 'none', 'important');
        img.style.setProperty('left', `${-left}px`, 'important');
        img.style.setProperty('top', `${-top}px`, 'important');
        img.style.setProperty('object-fit', 'cover', 'important');
      }"""

    target_insets_new = """      // [핵심: 그림틀 원형 보존 및 프레임 중심 안착 시스템]
      // 그림틀(프레임)을 축소하거나 위치를 옮겨도 그림이 엉뚱한 곳으로 잘려나가지 않고,
      // 현재 프레임 크기에 맞추어 원형 비율(Aspect Ratio)을 유지하며 정중앙에 단정하게 배치됩니다.
      const img = frameEl.querySelector('img');
      if (img) {
        img.style.setProperty('position', 'absolute', 'important');
        img.style.setProperty('width', '100%', 'important');
        img.style.setProperty('height', '100%', 'important');
        img.style.setProperty('max-width', 'none', 'important');
        img.style.setProperty('max-height', 'none', 'important');
        img.style.setProperty('left', '0', 'important');
        img.style.setProperty('top', '0', 'important');
        img.style.setProperty('object-fit', 'cover', 'important');
        img.style.setProperty('object-position', 'center center', 'important');
      }"""

    assert target_insets_old in core_content, "target_insets_old not found in dtp_editor_core.js"
    core_content = core_content.replace(target_insets_old, target_insets_new, 1)

    # attachImagePanDrag 드래그 감도 및 커서 피드백 강화
    target_pandrag_old = """        isDown = true;
        containerEl.classList.add('is-panning');
        document.body.style.cursor = 'grabbing';
        document.body.style.userSelect = 'none';"""

    target_pandrag_new = """        isDown = true;
        containerEl.classList.add('is-panning');
        containerEl.style.cursor = 'grabbing';
        document.body.style.cursor = 'grabbing';
        document.body.style.userSelect = 'none';"""

    if target_pandrag_old in core_content:
        core_content = core_content.replace(target_pandrag_old, target_pandrag_new, 1)

    with open('web/static/js/dtp_editor_core.js', 'w', encoding='utf-8') as f:
        f.write(core_content)

    print("✓ dtp_editor_core.js 패치 완료!")

    # 2. dtp_editor.css 패치 (커서 및 프레임 스타일)
    with open('web/static/css/dtp_editor.css', 'r', encoding='utf-8') as f:
        css_content = f.read()

    old_crop_css = """.dtp-frame-crop {
  position: absolute !important;
  inset: 0 !important;
  width: 100% !important;
  height: 100% !important;
  overflow: hidden !important;
  border-radius: 6px !important;
  pointer-events: none !important;
  background: #F5EFEB !important;
}"""

    new_crop_css = """.dtp-frame-crop {
  position: absolute !important;
  inset: 0 !important;
  width: 100% !important;
  height: 100% !important;
  overflow: hidden !important;
  border-radius: 6px !important;
  pointer-events: auto !important;
  cursor: grab !important;
  background: #F5EFEB !important;
}

.dtp-image-frame {
  cursor: grab !important;
}

.dtp-image-frame.is-panning,
.dtp-image-frame.is-panning .dtp-frame-crop {
  cursor: grabbing !important;
}"""

    if old_crop_css in css_content:
        css_content = css_content.replace(old_crop_css, new_crop_css, 1)
        with open('web/static/css/dtp_editor.css', 'w', encoding='utf-8') as f:
            f.write(css_content)
        print("✓ dtp_editor.css 패치 완료!")
    else:
        print("- dtp_editor.css old_crop_css 패턴 불일치, 수동 확인 필요")

if __name__ == '__main__':
    patch_image_frame_system()

