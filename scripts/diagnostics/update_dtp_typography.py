# -*- coding: utf-8 -*-
"""
DTP 편집기 독립 자유글 타이포그래피 분리 패치 스크립트
"""

def patch_dtp_editor():
    with open('web/static/js/dtp_editor_core.js', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. setFontSizePt & adjustLineHeight 교체
    old_font_size_block = """    /**
     * 폰트 크기(pt) 변경
     */
    setFontSizePt(val) {
      const work = this.getCurrentWork();
      if (!work) return;
      const cfg = this.getNormalizedConfig(work);

      let targetPt = 12;
      if (val === "custom") {
        const input = prompt("본문 글자 크기를 pt 단위로 입력하세요 (8 ~ 24):", String(cfg.font_size_pt || 13));
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
      const curLh = parseFloat(cfg.line_height_ratio) || 1.6;
      const nextLh = Math.max(1.3, Math.min(2.6, Math.round((curLh + delta * 0.1) * 100) / 100));
      cfg.line_height_ratio = nextLh;

      this.renderSpread(this.currentWorkIndex, this.currentSpreadPart, true);
      this.saveLayoutConfigToServer(work.episode_no, cfg);
      if (window.showToast) {
        window.showToast(`본문 줄간격: ${nextLh.toFixed(2)}배`, "info");
      }
    }"""

    new_font_size_block = """    /**
     * 폰트 크기(pt) 변경
     */
    setFontSizePt(val) {
      const work = this.getCurrentWork();
      if (!work) return;
      const cfg = this.getNormalizedConfig(work);
      const { slot, pageIdx, pageData, isIndependent } = this.getTargetPageInfo(cfg);

      let targetPt = 12;
      const curPt = isIndependent && pageData?.font_size_pt ? pageData.font_size_pt : (cfg.font_size_pt || 13);
      if (val === "custom") {
        const input = prompt("본문 글자 크기를 pt 단위로 입력하세요 (8 ~ 24):", String(curPt));
        if (!input || isNaN(parseFloat(input))) {
          this.syncToolboxUI(work, cfg);
          return;
        }
        targetPt = Math.max(8, Math.min(24, parseFloat(input)));
      } else {
        targetPt = Math.max(8, Math.min(24, parseFloat(val) || 12));
      }

      this.pushUndoState();

      if (isIndependent && pageData) {
        pageData.font_size_pt = targetPt;
        this.renderSpread(this.currentWorkIndex, this.currentSpreadPart, false);
        if (window.showToast) {
          window.showToast(`[${pageIdx + 1}면 독립 자유글] 글자 크기: ${targetPt}pt 적용 (시 본문 조판 유지)`, "info");
        }
      } else {
        cfg.font_size_pt = targetPt;
        this.renderSpread(this.currentWorkIndex, this.currentSpreadPart, true);
        if (window.showToast) {
          window.showToast(`본문 글자 크기: ${targetPt}pt 적용`, "info");
        }
      }
      this.syncToolboxUI(work, cfg);
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
      const { slot, pageIdx, pageData, isIndependent } = this.getTargetPageInfo(cfg);
      const curLh = parseFloat((isIndependent && pageData?.line_height_ratio) ? pageData.line_height_ratio : cfg.line_height_ratio) || 1.6;
      const nextLh = Math.max(1.3, Math.min(2.6, Math.round((curLh + delta * 0.1) * 100) / 100));

      if (isIndependent && pageData) {
        pageData.line_height_ratio = nextLh;
        this.renderSpread(this.currentWorkIndex, this.currentSpreadPart, false);
        if (window.showToast) {
          window.showToast(`[${pageIdx + 1}면 독립 자유글] 줄간격: ${nextLh.toFixed(2)}배 적용`, "info");
        }
      } else {
        cfg.line_height_ratio = nextLh;
        this.renderSpread(this.currentWorkIndex, this.currentSpreadPart, true);
        if (window.showToast) {
          window.showToast(`본문 줄간격: ${nextLh.toFixed(2)}배 적용`, "info");
        }
      }
      this.syncToolboxUI(work, cfg);
      this.saveLayoutConfigToServer(work.episode_no, cfg);
    }"""

    assert old_font_size_block in content, "old_font_size_block not found"
    content = content.replace(old_font_size_block, new_font_size_block, 1)

    # 2. setTextAlign 교체
    old_text_align_block = """    setTextAlign(align) {
      const validAligns = ['left', 'center', 'right', 'justify'];
      if (!validAligns.includes(align)) align = 'left';

      const work = this.getCurrentWork();
      if (!work) return;

      this.pushUndoState();
      const cfg = this.getNormalizedConfig(work);
      cfg.text_align = align;
      work.layout_config = cfg;

      // 화면 즉시 반영 (클래스 교체 및 text-align-last 배분 적용)
      document.querySelectorAll('.dtp-body-content, .dtp-body-text').forEach(el => {
        el.classList.remove('text-align-left', 'text-align-center', 'text-align-right', 'text-align-justify');
        el.classList.add(`text-align-${align}`);
        el.style.textAlign = align;
        el.style.textAlignLast = (align === 'justify' ? 'justify' : align);
      });

      // 정렬 드롭다운 동기화
      const selAlign = document.getElementById('selectTbTextAlign');
      if (selAlign) selAlign.value = align;
      if (typeof window.syncPoemEditorWithDtpConfig === 'function') window.syncPoemEditorWithDtpConfig(work);

      this.saveLayoutConfigToServer(work.episode_no, cfg);
      if (window.showToast) {
        const labelMap = { left: '왼쪽', center: '가운데', right: '오른쪽', justify: '양끝 배분' };
        window.showToast(`본문 정렬: ${labelMap[align] || align} 정렬 적용`, 'info');
      }
    }"""

    new_text_align_block = """    setTextAlign(align) {
      const validAligns = ['left', 'center', 'right', 'justify'];
      if (!validAligns.includes(align)) align = 'left';

      const work = this.getCurrentWork();
      if (!work) return;

      this.pushUndoState();
      const cfg = this.getNormalizedConfig(work);
      const { slot, pageIdx, pageData, isIndependent } = this.getTargetPageInfo(cfg);
      const labelMap = { left: '왼쪽', center: '가운데', right: '오른쪽', justify: '양끝 배분' };

      if (isIndependent && pageData) {
        pageData.text_align = align;
        const capSide = (slot === 'left') ? 'Left' : 'Right';
        const bodyElem = document.getElementById(`dtpBody${capSide}`);
        if (bodyElem) {
          bodyElem.classList.remove('text-align-left', 'text-align-center', 'text-align-right', 'text-align-justify');
          bodyElem.classList.add(`text-align-${align}`);
          bodyElem.style.textAlign = align;
          bodyElem.style.textAlignLast = (align === 'justify' ? 'justify' : align);
        }
        if (window.showToast) {
          window.showToast(`[${pageIdx + 1}면 독립 자유글] 본문 정렬: ${labelMap[align] || align} 정렬 적용 (시 본문 유지)`, 'info');
        }
      } else {
        cfg.text_align = align;
        work.layout_config = cfg;

        const spreadPart = this.currentSpreadPart || 1;
        ['left', 'right'].forEach((s, sIdx) => {
          const pIdx = (spreadPart - 1) * 2 + sIdx;
          const p = cfg.pages && cfg.pages[pIdx];
          if (p && p.role === 'independent') return;
          const capSide = (s === 'left') ? 'Left' : 'Right';
          const bodyElem = document.getElementById(`dtpBody${capSide}`);
          if (bodyElem) {
            bodyElem.classList.remove('text-align-left', 'text-align-center', 'text-align-right', 'text-align-justify');
            bodyElem.classList.add(`text-align-${align}`);
            bodyElem.style.textAlign = align;
            bodyElem.style.textAlignLast = (align === 'justify' ? 'justify' : align);
          }
        });
        if (typeof window.syncPoemEditorWithDtpConfig === 'function') window.syncPoemEditorWithDtpConfig(work);
        if (window.showToast) {
          window.showToast(`본문 정렬: ${labelMap[align] || align} 정렬 적용`, 'info');
        }
      }

      const selAlign = document.getElementById('selectTbTextAlign');
      if (selAlign) selAlign.value = align;

      this.saveLayoutConfigToServer(work.episode_no, cfg);
    }"""

    assert old_text_align_block in content, "old_text_align_block not found"
    content = content.replace(old_text_align_block, new_text_align_block, 1)

    # 3. setFontFamily 교체
    old_font_family_block = """    setFontFamily(fontFamily) {
      const work = this.getCurrentWork();
      if (!work) return;

      let targetFont = fontFamily;
      const selFont = document.getElementById('selectTbFontFamily');

      if (fontFamily === "custom") {
        const input = prompt(
          "적용할 서체(글꼴) 이름을 입력하세요:\\n(예: 궁서, 맑은 고딕, 나눔손글씨 붓, KoPubWorldBatang 등 PC에 설치된 폰트)",
          work.layout_config?.font_family ? work.layout_config.font_family.replace(/['",]/g, '').replace('serif', '').trim() : "궁서"
        );
        if (!input || !input.trim()) {
          if (selFont && work.layout_config?.font_family) {
            selFont.value = work.layout_config.font_family;
          }
          return;
        }
        targetFont = `'${input.trim()}', serif`;

        // 드롭다운에 사용자 지정 폰트 옵션 추가 및 선택
        if (selFont) {
          let opt = Array.from(selFont.options).find(o => o.value === targetFont);
          if (!opt) {
            opt = document.createElement("option");
            opt.value = targetFont;
            opt.textContent = `${input.trim()} (사용자 지정)`;
            selFont.insertBefore(opt, selFont.lastElementChild);
          }
          selFont.value = targetFont;
        }
      }

      this.pushUndoState();
      const cfg = this.getNormalizedConfig(work);
      cfg.font_family = targetFont;
      work.layout_config = cfg;

      if (Array.isArray(cfg.pages)) {
        cfg.pages.forEach(p => {
          if (p && p.custom_html) {
            p.custom_html = this.sanitizeCustomHtmlFont(p.custom_html);
          }
        });
      }
      document.querySelectorAll('.dtp-body-content, .dtp-body-text, .dtp-title, .dtp-title-text, .dtp-author-text, .poem-line, .line-text').forEach(el => {
        el.style.setProperty('font-family', targetFont, 'important');
      });
      if (typeof window.syncPoemEditorWithDtpConfig === 'function') {
        window.syncPoemEditorWithDtpConfig(work);
      }

      this.saveLayoutConfigToServer(work.episode_no, cfg);
      if (window.showToast) {
        const displayName = targetFont.replace(/['",]/g, '').replace('serif', '').trim();
        window.showToast(`글꼴: 「${displayName}」 서체 적용 완료`, "info");
      }
    }"""

    new_font_family_block = """    setFontFamily(fontFamily) {
      const work = this.getCurrentWork();
      if (!work) return;

      let targetFont = fontFamily;
      const selFont = document.getElementById('selectTbFontFamily');
      const cfg = this.getNormalizedConfig(work);
      const { slot, pageIdx, pageData, isIndependent } = this.getTargetPageInfo(cfg);
      const curFont = isIndependent && pageData?.font_family ? pageData.font_family : (cfg.font_family || "'BookkMyungjo', '부크크 명조', 'Nanum Myeongjo', serif");

      if (fontFamily === "custom") {
        const input = prompt(
          "적용할 서체(글꼴) 이름을 입력하세요:\\n(예: 궁서, 맑은 고딕, 나눔손글씨 붓, KoPubWorldBatang 등 PC에 설치된 폰트)",
          curFont ? curFont.replace(/['",]/g, '').replace('serif', '').trim() : "궁서"
        );
        if (!input || !input.trim()) {
          if (selFont && curFont) {
            selFont.value = curFont;
          }
          return;
        }
        targetFont = `'${input.trim()}', serif`;

        // 드롭다운에 사용자 지정 폰트 옵션 추가 및 선택
        if (selFont) {
          let opt = Array.from(selFont.options).find(o => o.value === targetFont);
          if (!opt) {
            opt = document.createElement("option");
            opt.value = targetFont;
            opt.textContent = `${input.trim()} (사용자 지정)`;
            selFont.insertBefore(opt, selFont.lastElementChild);
          }
          selFont.value = targetFont;
        }
      }

      this.pushUndoState();

      if (isIndependent && pageData) {
        pageData.font_family = targetFont;
        const capSide = (slot === 'left') ? 'Left' : 'Right';
        const bodyElem = document.getElementById(`dtpBody${capSide}`);
        if (bodyElem) {
          bodyElem.style.setProperty('font-family', targetFont, 'important');
          bodyElem.querySelectorAll('.line-text, .poem-line').forEach(el => {
            el.style.setProperty('font-family', targetFont, 'important');
          });
        }
        if (window.showToast) {
          const displayName = targetFont.replace(/['",]/g, '').replace('serif', '').trim();
          window.showToast(`[${pageIdx + 1}면 독립 자유글] 글꼴: 「${displayName}」 적용 (시 본문 유지)`, "info");
        }
      } else {
        cfg.font_family = targetFont;
        work.layout_config = cfg;

        if (Array.isArray(cfg.pages)) {
          cfg.pages.forEach(p => {
            if (p && p.custom_html) {
              p.custom_html = this.sanitizeCustomHtmlFont(p.custom_html);
            }
          });
        }
        const spreadPart = this.currentSpreadPart || 1;
        ['left', 'right'].forEach((s, sIdx) => {
          const pIdx = (spreadPart - 1) * 2 + sIdx;
          const p = cfg.pages && cfg.pages[pIdx];
          if (p && p.role === 'independent') return;
          const capSide = (s === 'left') ? 'Left' : 'Right';
          const b = document.getElementById(`dtpBody${capSide}`);
          const t = document.getElementById(`dtpTitle${capSide}`);
          const a = document.getElementById(`dtpAuthor${capSide}`);
          if (b) b.style.setProperty('font-family', targetFont, 'important');
          if (t) t.style.setProperty('font-family', targetFont, 'important');
          if (a) a.style.setProperty('font-family', targetFont, 'important');
        });
        if (typeof window.syncPoemEditorWithDtpConfig === 'function') {
          window.syncPoemEditorWithDtpConfig(work);
        }
        if (window.showToast) {
          const displayName = targetFont.replace(/['",]/g, '').replace('serif', '').trim();
          window.showToast(`글꼴: 「${displayName}」 서체 적용 완료`, "info");
        }
      }

      this.saveLayoutConfigToServer(work.episode_no, cfg);
    }"""

    assert old_font_family_block in content, "old_font_family_block not found"
    content = content.replace(old_font_family_block, new_font_family_block, 1)

    # 4. adjustFontSize, setLineHeight, setTargetPageSlot 교체
    old_adj_font_lh_slot = """    adjustFontSize(delta) {
      const work = this.getCurrentWork();
      if (!work) return;

      if (this.hasActiveSelection()) {
        // 선택 영역의 현재 폰트 크기 계산
        const sel = window.getSelection();
        const parent = sel?.anchorNode?.parentElement;
        const compSize = parent ? window.getComputedStyle(parent).fontSize : "16px";
        const currentPt = Math.round(parseFloat(compSize) * 0.75) || 13;
        const nextPt = Math.max(8, Math.min(36, currentPt + delta));
        this.applyInlineStyle({ fontSize: `${nextPt}pt` });
        return;
      }

      const cfg = this.getNormalizedConfig(work);
      const curPt = parseFloat(cfg.font_size_pt) || 13.0;
      const nextPt = Math.max(8.0, Math.min(28.0, Math.round((curPt + delta) * 10) / 10));
      this.setFontSizePt(nextPt);
    }

    /**
     * 줄간격 퍼센트 슬라이더 (130% ~ 220%)
     */
    setLineHeight(percentVal) {
      const work = this.getCurrentWork();
      if (!work) return;
      const ratio = Math.round(parseFloat(percentVal)) / 100.0;
      const cfg = this.getNormalizedConfig(work);
      cfg.line_height_ratio = ratio;

      document.querySelectorAll('.dtp-body-content, .dtp-body-text').forEach(el => {
        el.style.lineHeight = `${ratio}`;
      });

      const lbl = document.getElementById('lblTbLineHeightVal');
      if (lbl) lbl.textContent = `${percentVal}%`;
      if (typeof window.syncPoemEditorWithDtpConfig === 'function') window.syncPoemEditorWithDtpConfig(work);

      clearTimeout(this._lineHeightDebounce);
      this._lineHeightDebounce = setTimeout(() => {
        this.saveLayoutConfigToServer(work.episode_no, cfg);
      }, 400);
    }

    /**
     * 그림 탭: 편집 대상 면 선택 ('left' | 'right')
     */
    setTargetPageSlot(slot) {
      this.targetPageSlot = slot;
      const btnL = document.getElementById('btnTargetLeft');
      const btnR = document.getElementById('btnTargetRight');
      if (btnL) btnL.classList.toggle('active', slot === 'left');
      if (btnR) btnR.classList.toggle('active', slot === 'right');
      this.syncToolboxImageTab();
    }"""

    new_adj_font_lh_slot = """    adjustFontSize(delta) {
      const work = this.getCurrentWork();
      if (!work) return;

      if (this.hasActiveSelection()) {
        // 선택 영역의 현재 폰트 크기 계산
        const sel = window.getSelection();
        const parent = sel?.anchorNode?.parentElement;
        const compSize = parent ? window.getComputedStyle(parent).fontSize : "16px";
        const currentPt = Math.round(parseFloat(compSize) * 0.75) || 13;
        const nextPt = Math.max(8, Math.min(36, currentPt + delta));
        this.applyInlineStyle({ fontSize: `${nextPt}pt` });
        return;
      }

      const cfg = this.getNormalizedConfig(work);
      const { pageData, isIndependent } = this.getTargetPageInfo(cfg);
      const curPt = parseFloat((isIndependent && pageData?.font_size_pt) ? pageData.font_size_pt : cfg.font_size_pt) || 13.0;
      const nextPt = Math.max(8.0, Math.min(28.0, Math.round((curPt + delta) * 10) / 10));
      this.setFontSizePt(nextPt);
    }

    /**
     * 줄간격 퍼센트 슬라이더 (130% ~ 220%)
     */
    setLineHeight(percentVal) {
      const work = this.getCurrentWork();
      if (!work) return;
      const ratio = Math.round(parseFloat(percentVal)) / 100.0;
      const cfg = this.getNormalizedConfig(work);
      const { slot, pageData, isIndependent } = this.getTargetPageInfo(cfg);

      if (isIndependent && pageData) {
        pageData.line_height_ratio = ratio;
        const capSide = (slot === 'left') ? 'Left' : 'Right';
        const bodyElem = document.getElementById(`dtpBody${capSide}`);
        if (bodyElem) {
          const pt = parseFloat(pageData.font_size_pt || cfg.font_size_pt) || 13;
          const fontPx = (pt / 12.0) * 15.2;
          const linePx = fontPx * ratio;
          bodyElem.style.lineHeight = `${linePx.toFixed(2)}px`;
          bodyElem.querySelectorAll('.poem-line').forEach(el => {
            el.style.minHeight = `${linePx.toFixed(2)}px`;
            el.style.lineHeight = `${linePx.toFixed(2)}px`;
          });
        }
      } else {
        cfg.line_height_ratio = ratio;
        const spreadPart = this.currentSpreadPart || 1;
        ['left', 'right'].forEach((s, sIdx) => {
          const pIdx = (spreadPart - 1) * 2 + sIdx;
          const p = cfg.pages && cfg.pages[pIdx];
          if (p && p.role === 'independent') return;
          const capSide = (s === 'left') ? 'Left' : 'Right';
          const bodyElem = document.getElementById(`dtpBody${capSide}`);
          if (bodyElem) {
            const pt = parseFloat(cfg.font_size_pt) || 13;
            const fontPx = (pt / 12.0) * 15.2;
            const linePx = fontPx * ratio;
            bodyElem.style.lineHeight = `${linePx.toFixed(2)}px`;
            bodyElem.querySelectorAll('.poem-line').forEach(el => {
              el.style.minHeight = `${linePx.toFixed(2)}px`;
              el.style.lineHeight = `${linePx.toFixed(2)}px`;
            });
          }
        });
        if (typeof window.syncPoemEditorWithDtpConfig === 'function') window.syncPoemEditorWithDtpConfig(work);
      }

      const lbl = document.getElementById('lblTbLineHeightVal');
      if (lbl) lbl.textContent = `${percentVal}%`;

      clearTimeout(this._lineHeightDebounce);
      this._lineHeightDebounce = setTimeout(() => {
        this.saveLayoutConfigToServer(work.episode_no, cfg);
      }, 400);
    }

    /**
     * 그림 탭: 편집 대상 면 선택 ('left' | 'right')
     */
    setTargetPageSlot(slot) {
      this.targetPageSlot = slot;
      const btnL = document.getElementById('btnTargetLeft');
      const btnR = document.getElementById('btnTargetRight');
      if (btnL) btnL.classList.toggle('active', slot === 'left');
      if (btnR) btnR.classList.toggle('active', slot === 'right');
      this.syncToolboxImageTab();
      const work = this.getCurrentWork();
      if (work) {
        const cfg = this.getNormalizedConfig(work);
        this.syncToolboxUI(work, cfg);
      }
    }"""

    assert old_adj_font_lh_slot in content, "old_adj_font_lh_slot not found"
    content = content.replace(old_adj_font_lh_slot, new_adj_font_lh_slot, 1)

    # 5. renderTextLayer 내부: 클릭/포커스 시 slot 동기화 및 pageData 개별 타이포그래피 우선 적용
    old_boxbody_click = """      if (boxBody) {
        boxBody.onclick = () => {
          if (this.currentToolboxTab !== 'text') {
            this.switchToolboxTab('text');
          }
        };"""

    new_boxbody_click = """      if (boxBody) {
        boxBody.onclick = () => {
          this.setTargetPageSlot(side);
          if (this.currentToolboxTab !== 'text') {
            this.switchToolboxTab('text');
          }
        };
        bodyElem.onfocus = () => {
          this.setTargetPageSlot(side);
        };"""

    assert old_boxbody_click in content, "old_boxbody_click not found"
    content = content.replace(old_boxbody_click, new_boxbody_click, 1)

    old_typo_extract = """        const pt = parseFloat(cfg.font_size_pt) || 13;
        const lh = parseFloat(cfg.line_height_ratio) || 1.6;
        const fontPx = (pt / 12.0) * 15.2;
        const linePx = fontPx * lh;
        const maxAllowedH = Math.max(84, 517 - topOffset);
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
        const targetBoxH = Math.min(maxAllowedH, Math.max(84, Math.round(targetLines * linePx + 28)));
        boxBody.style.setProperty("height", `${targetBoxH}px`, "important");
        boxBody.style.setProperty("flex", "none", "important");

        // 핸들 이벤트 주입
        this.attachResizeHandles(boxBody, side, pageIdx, cfg, work);

        bodyElem.style.fontSize = `${fontPx.toFixed(2)}px`;
        bodyElem.style.lineHeight = `${linePx.toFixed(2)}px`;
        
        // 서체 실시간 적용 (기본값: 부크크 명조 -> 나눔명조 -> 바탕체)
        const fontFam = cfg.font_family || "'BookkMyungjo', '부크크 명조', 'Nanum Myeongjo', serif";
        bodyElem.style.setProperty('font-family', fontFam, 'important');

        // 정렬 4종 (양끝 배분 정렬 시 각 행 좌우 균등 배분 지원)
        const align = cfg.text_align || 'left';
        bodyElem.classList.remove('text-align-left', 'text-align-center', 'text-align-right', 'text-align-justify');
        bodyElem.classList.add(`text-align-${align}`);
        bodyElem.style.textAlign = align;
        bodyElem.style.textAlignLast = (align === 'justify' ? 'justify' : align);"""

    new_typo_extract = """        const isIndep = (pageData.role === 'independent');
        const pt = parseFloat((isIndep && pageData.font_size_pt) ? pageData.font_size_pt : cfg.font_size_pt) || 13;
        const lh = parseFloat((isIndep && pageData.line_height_ratio) ? pageData.line_height_ratio : cfg.line_height_ratio) || 1.6;
        const fontPx = (pt / 12.0) * 15.2;
        const linePx = fontPx * lh;
        const maxAllowedH = Math.max(84, 517 - topOffset);
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
        const targetBoxH = Math.min(maxAllowedH, Math.max(84, Math.round(targetLines * linePx + 28)));
        boxBody.style.setProperty("height", `${targetBoxH}px`, "important");
        boxBody.style.setProperty("flex", "none", "important");

        // 핸들 이벤트 주입
        this.attachResizeHandles(boxBody, side, pageIdx, cfg, work);

        bodyElem.style.fontSize = `${fontPx.toFixed(2)}px`;
        bodyElem.style.lineHeight = `${linePx.toFixed(2)}px`;
        
        // 서체 실시간 적용 (독립 자유글은 개별 font_family 우선)
        const fontFam = (isIndep && pageData.font_family) ? pageData.font_family : (cfg.font_family || "'BookkMyungjo', '부크크 명조', 'Nanum Myeongjo', serif");
        bodyElem.style.setProperty('font-family', fontFam, 'important');

        // 정렬 4종 (독립 자유글은 개별 text_align 우선)
        const align = (isIndep && pageData.text_align) ? pageData.text_align : (cfg.text_align || 'left');
        bodyElem.classList.remove('text-align-left', 'text-align-center', 'text-align-right', 'text-align-justify');
        bodyElem.classList.add(`text-align-${align}`);
        bodyElem.style.textAlign = align;
        bodyElem.style.textAlignLast = (align === 'justify' ? 'justify' : align);"""

    assert old_typo_extract in content, "old_typo_extract not found"
    content = content.replace(old_typo_extract, new_typo_extract, 1)

    # 6. syncToolboxUI 교체
    old_sync_toolbox = """    syncToolboxUI(work, cfg) {
      if (!work || !cfg) return;

      // 1) 안내선 ON/OFF 동기화
      const btnOn = document.getElementById("btnGuideOn");
      const btnOff = document.getElementById("btnGuideOff");
      if (btnOn) btnOn.classList.toggle("active", this.showGuides);
      if (btnOff) btnOff.classList.toggle("active", !this.showGuides);

      // 2) 본문 정렬 드롭다운 동기화
      const align = cfg.text_align || 'left';
      const selAlign = document.getElementById('selectTbTextAlign');
      if (selAlign) selAlign.value = align;
      if (typeof window.syncPoemEditorWithDtpConfig === 'function') window.syncPoemEditorWithDtpConfig(work);

      // 3) 글꼴 드롭다운 동기화 (사용자 지정 폰트 유지)
      const selFont = document.getElementById('selectTbFontFamily');
      if (selFont) {
        const curFont = cfg.font_family || "'BookkMyungjo', '부크크 명조', 'Nanum Myeongjo', serif";
        let matchOpt = Array.from(selFont.options).find(o => o.value === curFont || (curFont.includes('Bookk') && o.value.includes('Bookk')));
        if (matchOpt) {
          selFont.value = matchOpt.value;
        } else {
          let exists = Array.from(selFont.options).some(o => o.value === curFont);
          if (!exists && curFont !== 'custom') {
            const opt = document.createElement("option");
            opt.value = curFont;
            const cleanName = curFont.replace(/['",]/g, '').replace('serif', '').trim();
            opt.textContent = `${cleanName} (사용자 지정)`;
            selFont.insertBefore(opt, selFont.lastElementChild);
          }
          selFont.value = curFont;
        }
      }
      if (false && selFont && cfg.font_family) {
        let exists = Array.from(selFont.options).some(o => o.value === cfg.font_family);
        if (!exists && cfg.font_family !== 'custom') {
          const opt = document.createElement("option");
          opt.value = cfg.font_family;
          const cleanName = cfg.font_family.replace(/['",]/g, '').replace('serif', '').trim();
          opt.textContent = `${cleanName} (사용자 지정)`;
          selFont.insertBefore(opt, selFont.lastElementChild);
        }
        selFont.value = cfg.font_family;
      }

      // 4) 글자 크기 드롭다운 동기화 (사용자 지정 pt 포함)
      const selSize = document.getElementById('selectTbFontSize');
      if (selSize) {
        const ptVal = parseFloat(cfg.font_size_pt) || 13;
        const ptStr = String(Math.round(ptVal * 10) / 10);
        let exists = Array.from(selSize.options).some(o => o.value === ptStr);
        if (!exists && ptVal) {
          const opt = document.createElement("option");
          opt.value = ptStr;
          opt.textContent = `${ptStr}pt (사용자지정)`;
          selSize.insertBefore(opt, selSize.lastElementChild);
        }
        selSize.value = ptStr;
      }

      // 집필실 본문창(#inputFinalPoem)의 글꼴 및 기본 크기도 도구상자 설정과 동기화
      if (typeof window.syncPoemEditorWithDtpConfig === 'function') {
        window.syncPoemEditorWithDtpConfig(work);
      }

      // 4-1) 글자색 버튼 텍스트 동기화
      const btnColor = document.getElementById('btnTbTextColor');
      if (btnColor) {
        const mode = cfg.text_color_mode || 'auto';
        if (mode === 'light') btnColor.textContent = '⚪ 글자색: 전체 백색';
        else if (mode === 'dark') btnColor.textContent = '⚫ 글자색: 전체 먹색';
        else btnColor.textContent = '🌗 글자색: 스마트 자동';
      }

      // 4) 줄간격 동기화
      const inputLh = document.getElementById('inputTbLineHeight');
      const lblLh = document.getElementById('lblTbLineHeightVal');
      const lhPercent = Math.round((parseFloat(cfg.line_height_ratio) || 1.6) * 100);
      if (inputLh) inputLh.value = lhPercent;
      if (lblLh) lblLh.textContent = `${lhPercent}%`;"""

    new_sync_toolbox = """    syncToolboxUI(work, cfg) {
      if (!work || !cfg) return;

      const { pageData, isIndependent } = this.getTargetPageInfo(cfg);

      // 1) 안내선 ON/OFF 동기화
      const btnOn = document.getElementById("btnGuideOn");
      const btnOff = document.getElementById("btnGuideOff");
      if (btnOn) btnOn.classList.toggle("active", this.showGuides);
      if (btnOff) btnOff.classList.toggle("active", !this.showGuides);

      // 2) 본문 정렬 드롭다운 동기화 (독립 자유글은 개별 설정 표시)
      const align = (isIndependent && pageData?.text_align) ? pageData.text_align : (cfg.text_align || 'left');
      const selAlign = document.getElementById('selectTbTextAlign');
      if (selAlign) selAlign.value = align;
      if (!isIndependent && typeof window.syncPoemEditorWithDtpConfig === 'function') window.syncPoemEditorWithDtpConfig(work);

      // 3) 글꼴 드롭다운 동기화 (사용자 지정 폰트 유지)
      const selFont = document.getElementById('selectTbFontFamily');
      if (selFont) {
        const curFont = (isIndependent && pageData?.font_family) ? pageData.font_family : (cfg.font_family || "'BookkMyungjo', '부크크 명조', 'Nanum Myeongjo', serif");
        let matchOpt = Array.from(selFont.options).find(o => o.value === curFont || (curFont.includes('Bookk') && o.value.includes('Bookk')));
        if (matchOpt) {
          selFont.value = matchOpt.value;
        } else {
          let exists = Array.from(selFont.options).some(o => o.value === curFont);
          if (!exists && curFont !== 'custom') {
            const opt = document.createElement("option");
            opt.value = curFont;
            const cleanName = curFont.replace(/['",]/g, '').replace('serif', '').trim();
            opt.textContent = `${cleanName} (사용자 지정)`;
            selFont.insertBefore(opt, selFont.lastElementChild);
          }
          selFont.value = curFont;
        }
      }

      // 4) 글자 크기 드롭다운 동기화 (사용자 지정 pt 포함)
      const selSize = document.getElementById('selectTbFontSize');
      if (selSize) {
        const ptVal = parseFloat((isIndependent && pageData?.font_size_pt) ? pageData.font_size_pt : cfg.font_size_pt) || 13;
        const ptStr = String(Math.round(ptVal * 10) / 10);
        let exists = Array.from(selSize.options).some(o => o.value === ptStr);
        if (!exists && ptVal) {
          const opt = document.createElement("option");
          opt.value = ptStr;
          opt.textContent = `${ptStr}pt (사용자지정)`;
          selSize.insertBefore(opt, selSize.lastElementChild);
        }
        selSize.value = ptStr;
      }

      // 집필실 본문창(#inputFinalPoem)의 글꼴 및 기본 크기도 도구상자 설정과 동기화 (메인 시일 때만)
      if (!isIndependent && typeof window.syncPoemEditorWithDtpConfig === 'function') {
        window.syncPoemEditorWithDtpConfig(work);
      }

      // 4-1) 글자색 버튼 텍스트 동기화
      const btnColor = document.getElementById('btnTbTextColor');
      if (btnColor) {
        const mode = cfg.text_color_mode || 'auto';
        if (mode === 'light') btnColor.textContent = '⚪ 글자색: 전체 백색';
        else if (mode === 'dark') btnColor.textContent = '⚫ 글자색: 전체 먹색';
        else btnColor.textContent = '🌗 글자색: 스마트 자동';
      }

      // 5) 줄간격 동기화
      const inputLh = document.getElementById('inputTbLineHeight');
      const lblLh = document.getElementById('lblTbLineHeightVal');
      const lhRatio = parseFloat((isIndependent && pageData?.line_height_ratio) ? pageData.line_height_ratio : cfg.line_height_ratio) || 1.6;
      const lhPercent = Math.round(lhRatio * 100);
      if (inputLh) inputLh.value = lhPercent;
      if (lblLh) lblLh.textContent = `${lhPercent}%`;"""

    assert old_sync_toolbox in content, "old_sync_toolbox not found"
    content = content.replace(old_sync_toolbox, new_sync_toolbox, 1)

    with open('web/static/js/dtp_editor_core.js', 'w', encoding='utf-8') as f:
        f.write(content)

    print("All patches applied successfully to web/static/js/dtp_editor_core.js!")

if __name__ == '__main__':
    patch_dtp_editor()

