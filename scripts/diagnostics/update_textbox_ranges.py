# -*- coding: utf-8 -*-
"""
글상자 조절 범위 극단 허용(상하 1줄, 좌우 1글자 한계 완화) 패치 스크립트
"""

def patch_textbox_extreme_ranges():
    with open('web/static/js/dtp_editor_core.js', 'r', encoding='utf-8') as f:
        core = f.read()

    # 1. attachResizeHandles 내부 상단 핸들(topHandle) max_offset 완화
    old_top_handle = """        function onMouseMove(ev) {
          const deltaY = ev.clientY - startY;
          currOffset = Math.max(0, Math.min(240, Math.round(initialOffset + deltaY)));
          boxBody.style.setProperty("margin-top", `${currOffset}px`, "important");"""

    new_top_handle = """        const minBottomH = Math.max(34, Math.round(linePx + 16));
        const maxTopOffset = Math.max(0, 517 - minBottomH); // 하단 기준 1줄 남길 때까지 극단 허용 (~470px)

        function onMouseMove(ev) {
          const deltaY = ev.clientY - startY;
          currOffset = Math.max(0, Math.min(maxTopOffset, Math.round(initialOffset + deltaY)));
          boxBody.style.setProperty("margin-top", `${currOffset}px`, "important");"""

    assert old_top_handle in core, "old_top_handle not found"
    core = core.replace(old_top_handle, new_top_handle, 1)

    # 2. attachResizeHandles 내부 하단 핸들(bottomHandle) 최소 1행 완화
    old_bottom_handle = """        // 인쇄안전선(517px - topOffset) 기준 정확한 최대 허용 높이 및 최대 행수 산출 (calculateTextFlowAndPages와 100% 동일 공식)
        const maxAllowedHeight = Math.max(84, 517 - topOffset);
        const maxSafeLines = Math.max(2, Math.floor((maxAllowedHeight - 28 + 2) / linePx));

        const initialMaxLines = pageData.max_lines ? Math.min(maxSafeLines, parseInt(pageData.max_lines, 10)) : maxSafeLines;
        let newLines = initialMaxLines;
        let snappedHeight = Math.min(maxAllowedHeight, Math.round(newLines * linePx + 28));

        boxBody.classList.add("is-resizing");
        document.body.style.cursor = "ns-resize";

        const updateHandleTooltip = (linesCnt, isAtMax) => {
          const label = bottomHandle.querySelector(".handle-label");
          if (!label) return;
          const pElems = Array.from(boxBody.querySelectorAll(".poem-line"));
          let lastLinePreview = "";
          for (let k = pElems.length - 1; k >= 0; k--) {
            const t = (pElems[k].textContent || "").trim();
            if (t) {
              lastLinePreview = t.length > 12 ? t.slice(0, 12) + "…" : t;
              break;
            }
          }
          const maxHint = isAtMax ? " [안전선 한도]" : "";
          const lineHint = lastLinePreview ? ` · 끝행: "${lastLinePreview}"` : "";
          label.textContent = `▼ 수용: ${linesCnt}행 (빈줄 포함)${lineHint}${maxHint}`;
          label.style.display = "block";
        };

        updateHandleTooltip(newLines, newLines >= maxSafeLines);

        function onMouseMove(ev) {
          const deltaY = ev.clientY - startY;
          const rawHeight = Math.max(84, Math.min(maxAllowedHeight, startHeight + deltaY));
          // 상단 14px + 하단 14px = 28px 여백을 제외한 순수 본문 높이에서 행 단위로 정확히 스냅!
          const candidateLines = Math.max(2, Math.min(maxSafeLines, Math.floor((rawHeight - 28 + linePx * 0.45) / linePx)));
          snappedHeight = Math.min(maxAllowedHeight, Math.round(candidateLines * linePx + 28));"""

    new_bottom_handle = """        // 인쇄안전선(517px - topOffset) 기준 최소 1행까지 극단 축소 허용
        const minBoxH = Math.max(34, Math.round(linePx + 16));
        const maxAllowedHeight = Math.max(minBoxH, 517 - topOffset);
        const maxSafeLines = Math.max(1, Math.floor((maxAllowedHeight - 16) / linePx));

        const initialMaxLines = pageData.max_lines ? Math.min(maxSafeLines, parseInt(pageData.max_lines, 10)) : maxSafeLines;
        let newLines = initialMaxLines;
        let snappedHeight = Math.min(maxAllowedHeight, Math.max(minBoxH, Math.round(newLines * linePx + 18)));

        boxBody.classList.add("is-resizing");
        document.body.style.cursor = "ns-resize";

        const updateHandleTooltip = (linesCnt, isAtMax) => {
          const label = bottomHandle.querySelector(".handle-label");
          if (!label) return;
          const pElems = Array.from(boxBody.querySelectorAll(".poem-line"));
          let lastLinePreview = "";
          for (let k = pElems.length - 1; k >= 0; k--) {
            const t = (pElems[k].textContent || "").trim();
            if (t) {
              lastLinePreview = t.length > 12 ? t.slice(0, 12) + "…" : t;
              break;
            }
          }
          const maxHint = isAtMax ? " [안전선 한도]" : "";
          const lineHint = lastLinePreview ? ` · 끝행: "${lastLinePreview}"` : "";
          label.textContent = `▼ 수용: ${linesCnt}행 (빈줄 포함)${lineHint}${maxHint}`;
          label.style.display = "block";
        };

        updateHandleTooltip(newLines, newLines >= maxSafeLines);

        function onMouseMove(ev) {
          const deltaY = ev.clientY - startY;
          const rawHeight = Math.max(minBoxH, Math.min(maxAllowedHeight, startHeight + deltaY));
          // 상단 기준 1행까지 극단 조절 허용
          const candidateLines = Math.max(1, Math.min(maxSafeLines, Math.floor((rawHeight - 16 + linePx * 0.45) / linePx)));
          snappedHeight = Math.min(maxAllowedHeight, Math.max(minBoxH, Math.round(candidateLines * linePx + 18)));"""

    assert old_bottom_handle in core, "old_bottom_handle not found"
    core = core.replace(old_bottom_handle, new_bottom_handle, 1)

    # 3. 좌측 핸들(leftHandle)과 우측 핸들(rightHandle) 60% 제한 -> 1글자 한계까지 극단 완화
    old_left_right = """        const safeBoundary = boxBody.closest(".dtp-safe-boundary") || boxBody.parentElement;
        const boundaryW = safeBoundary ? safeBoundary.clientWidth : 380;
        const maxLeft = Math.max(0, Math.floor(boundaryW * 0.60 - currentRight));"""

    new_left_right = """        const safeBoundary = boxBody.closest(".dtp-safe-boundary") || boxBody.parentElement;
        const boundaryW = safeBoundary ? safeBoundary.clientWidth : 380;
        const minContentW = Math.max(26, Math.round(fontPx * 1.4)); // 우측에 단 한 글자 폭만 남기고 극단 이동 허용
        const maxLeft = Math.max(0, Math.floor(boundaryW - currentRight - minContentW));"""

    assert old_left_right in core, "old_left_right not found"
    core = core.replace(old_left_right, new_left_right, 1)

    old_right = """        const safeBoundary = boxBody.closest(".dtp-safe-boundary") || boxBody.parentElement;
        const boundaryW = safeBoundary ? safeBoundary.clientWidth : 380;
        const maxRight = Math.max(0, Math.floor(boundaryW * 0.60 - currentLeft));"""

    new_right = """        const safeBoundary = boxBody.closest(".dtp-safe-boundary") || boxBody.parentElement;
        const boundaryW = safeBoundary ? safeBoundary.clientWidth : 380;
        const minContentW = Math.max(26, Math.round(fontPx * 1.4)); // 좌측에 단 한 글자 폭만 남기고 극단 이동 허용
        const maxRight = Math.max(0, Math.floor(boundaryW - currentLeft - minContentW));"""

    assert old_right in core, "old_right not found"
    core = core.replace(old_right, new_right, 1)

    # 4. renderTextLayer 내부 maxAllowedH & targetBoxH 완화
    old_render_text = """        const maxAllowedH = Math.max(84, 517 - topOffset);
        const maxSafeLines = Math.max(2, Math.floor((maxAllowedH - 28 + 2) / linePx));

        // 하단 커스텀 높이 적용: 상단 14px + 하단 14px = 28px 여백을 정확히 유지하며 행 높이 100% 일치 보장
        const assignedLines = (textFlowMap && textFlowMap[pageIdx]) ? textFlowMap[pageIdx].length : 0;
        let targetLines = 0;
        if (pageData.max_lines) {
          targetLines = Math.min(maxSafeLines, parseInt(pageData.max_lines, 10));
        } else if (assignedLines > 0) {
          targetLines = Math.min(maxSafeLines, assignedLines);
        } else {
          targetLines = maxSafeLines;
        }
        const targetBoxH = Math.min(maxAllowedH, Math.max(84, Math.round(targetLines * linePx + 28)));"""

    new_render_text = """        const minSingleLineH = Math.max(34, Math.round(linePx + 16));
        const maxAllowedH = Math.max(minSingleLineH, 517 - topOffset);
        const maxSafeLines = Math.max(1, Math.floor((maxAllowedH - 16) / linePx));

        // 하단 커스텀 높이 적용: 1행부터 안전하게 수용
        const assignedLines = (textFlowMap && textFlowMap[pageIdx]) ? textFlowMap[pageIdx].length : 0;
        let targetLines = 0;
        if (pageData.max_lines) {
          targetLines = Math.min(maxSafeLines, parseInt(pageData.max_lines, 10));
        } else if (assignedLines > 0) {
          targetLines = Math.min(maxSafeLines, assignedLines);
        } else {
          targetLines = maxSafeLines;
        }
        const targetBoxH = Math.min(maxAllowedH, Math.max(minSingleLineH, Math.round(targetLines * linePx + 18)));"""

    assert old_render_text in core, "old_render_text not found"
    core = core.replace(old_render_text, new_render_text, 1)

    # 5. calculateTextFlowAndPages 내부 maxSafeHeight & maxSafeLines 완화
    old_flow_calc = """        const topOffset = p.top_offset ? parseInt(p.top_offset, 10) : 0;
        // 안전선(593px) - 상단영역(76px) = 517px, 상/하단 패딩(14px+14px=28px) 차감
        const maxSafeHeight = Math.max(84, 517 - topOffset);
        const availableHeight = Math.max(56, maxSafeHeight - 28);
        const maxSafeLines = Math.max(2, Math.floor((availableHeight + 2) / linePx));"""

    new_flow_calc = """        const topOffset = p.top_offset ? parseInt(p.top_offset, 10) : 0;
        // 안전선(593px) - 상단영역(76px) = 517px, 1행 극단 배치 완벽 허용
        const minSingleH = Math.max(34, Math.round(linePx + 16));
        const maxSafeHeight = Math.max(minSingleH, 517 - topOffset);
        const availableHeight = Math.max(linePx, maxSafeHeight - 16);
        const maxSafeLines = Math.max(1, Math.floor((availableHeight + 2) / linePx));"""

    assert old_flow_calc in core, "old_flow_calc not found"
    core = core.replace(old_flow_calc, new_flow_calc, 1)

    with open('web/static/js/dtp_editor_core.js', 'w', encoding='utf-8') as f:
        f.write(core)

    print("✓ dtp_editor_core.js 글상자 조절 범위 극단 허용 패치 완료!")

if __name__ == '__main__':
    patch_textbox_extreme_ranges()

