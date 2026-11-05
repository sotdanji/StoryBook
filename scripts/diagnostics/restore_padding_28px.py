# -*- coding: utf-8 -*-
"""
글상자 상하단 14px+14px=28px 정통 대칭 여백 복원 패치 스크립트
"""

def restore_exact_padding_28px():
    with open('web/static/js/dtp_editor_core.js', 'r', encoding='utf-8') as f:
        core = f.read()

    # 1. calculateTextFlowAndPages (line 735 부근)
    old_flow = """        const topOffset = p.top_offset ? parseInt(p.top_offset, 10) : 0;
        // 안전선(593px) - 상단영역(76px) = 517px, 1행 극단 배치 완벽 허용
        const minSingleH = Math.max(34, Math.round(linePx + 16));
        const maxSafeHeight = Math.max(minSingleH, 517 - topOffset);
        const availableHeight = Math.max(linePx, maxSafeHeight - 16);
        const maxSafeLines = Math.max(1, Math.floor((availableHeight + 2) / linePx));"""

    new_flow = """        const topOffset = p.top_offset ? parseInt(p.top_offset, 10) : 0;
        // 안전선(593px) - 상단영역(76px) = 517px, 상/하단 14px+14px=28px 정통 대칭 여백 완벽 준수
        const minSingleH = Math.round(linePx + 28);
        const maxSafeHeight = Math.max(minSingleH, 517 - topOffset);
        const availableHeight = Math.max(linePx, maxSafeHeight - 28);
        const maxSafeLines = Math.max(1, Math.floor((availableHeight + 2) / linePx));"""

    assert old_flow in core, "old_flow not found"
    core = core.replace(old_flow, new_flow, 1)

    # 2. topHandle (line 1133 부근)
    old_top = """        const minBottomH = Math.max(34, Math.round(linePx + 16));
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
          const newHeight = Math.max(minBottomH, Math.round(candidateLines * linePx + 18));"""

    new_top = """        const minBottomH = Math.round(linePx + 28);
        const maxTopOffset = Math.max(0, fixedBottomY - minBottomH); // 하단 기준 1줄 남길 때까지 허용

        const label = topHandle.querySelector(".handle-label");
        if (label) {
          label.textContent = `▲ 본문 시작선 내림: +${initialOffset}px`;
          label.style.display = "block";
        }

        function onMouseMove(ev) {
          const deltaY = ev.clientY - startY;
          currOffset = Math.max(0, Math.min(maxTopOffset, Math.round(initialOffset + deltaY)));
          // 하단선 고정: 상단 14px + 하단 14px = 28px 여백을 정확히 유지
          const rawHeight = Math.max(minBottomH, fixedBottomY - currOffset);
          const candidateLines = Math.max(1, Math.floor((rawHeight - 28 + linePx * 0.45) / linePx));
          const newHeight = Math.max(minBottomH, Math.round(candidateLines * linePx + 28));"""

    assert old_top in core, "old_top not found"
    core = core.replace(old_top, new_top, 1)

    # 3. topHandle onMouseUp (candidateLines 계산식 복원)
    old_top_up = """          if (currOffset !== initialOffset) {
            self.pushUndoState();
            pageData.top_offset = currOffset;
            const rawHeight = Math.max(minBottomH, fixedBottomY - currOffset);
            const candidateLines = Math.max(1, Math.floor((rawHeight - 16) / linePx));
            pageData.max_lines = candidateLines;"""

    new_top_up = """          if (currOffset !== initialOffset) {
            self.pushUndoState();
            pageData.top_offset = currOffset;
            const rawHeight = Math.max(minBottomH, fixedBottomY - currOffset);
            const candidateLines = Math.max(1, Math.floor((rawHeight - 28 + linePx * 0.45) / linePx));
            pageData.max_lines = candidateLines;"""

    assert old_top_up in core, "old_top_up not found"
    core = core.replace(old_top_up, new_top_up, 1)

    # 4. bottomHandle (line 1204 부근)
    old_bottom = """        // 인쇄안전선(517px - topOffset) 기준 최소 1행까지 극단 축소 허용
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

    new_bottom = """        // 인쇄안전선(517px - topOffset) 기준 상/하단 14px+14px=28px 여백을 정확히 유지
        const minBoxH = Math.round(linePx + 28);
        const maxAllowedHeight = Math.max(minBoxH, 517 - topOffset);
        const maxSafeLines = Math.max(1, Math.floor((maxAllowedHeight - 28 + 2) / linePx));

        const initialMaxLines = pageData.max_lines ? Math.min(maxSafeLines, parseInt(pageData.max_lines, 10)) : maxSafeLines;
        let newLines = initialMaxLines;
        let snappedHeight = Math.min(maxAllowedHeight, Math.max(minBoxH, Math.round(newLines * linePx + 28)));

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
          // 상단 14px + 하단 14px = 28px 여백을 제외한 순수 본문 높이에서 행 단위로 정확히 스냅
          const candidateLines = Math.max(1, Math.min(maxSafeLines, Math.floor((rawHeight - 28 + linePx * 0.45) / linePx)));
          snappedHeight = Math.min(maxAllowedHeight, Math.max(minBoxH, Math.round(candidateLines * linePx + 28)));"""

    assert old_bottom in core, "old_bottom not found"
    core = core.replace(old_bottom, new_bottom, 1)

    # 5. renderTextLayer (line 2115 부근)
    old_render = """        const minSingleLineH = Math.max(34, Math.round(linePx + 16));
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

    new_render = """        const minSingleLineH = Math.round(linePx + 28);
        const maxAllowedH = Math.max(minSingleLineH, 517 - topOffset);
        const maxSafeLines = Math.max(1, Math.floor((maxAllowedH - 28 + 2) / linePx));

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
        const targetBoxH = Math.min(maxAllowedH, Math.max(minSingleLineH, Math.round(targetLines * linePx + 28)));"""

    assert old_render in core, "old_render not found"
    core = core.replace(old_render, new_render, 1)

    with open('web/static/js/dtp_editor_core.js', 'w', encoding='utf-8') as f:
        f.write(core)
    print("✓ dtp_editor_core.js 상하단 28px 대칭 여백 공식 복원 완료!")

if __name__ == '__main__':
    restore_exact_padding_28px()

