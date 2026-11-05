// ============================================================================
// [Module] thesaurus_palette.js - 시어 감각 사전, 방언/토속어, 공간의 시학 타이포그래피, 인라인 플로팅 시어 팔레트
// ============================================================================
// ============================================================
// 18. 시인의 집필실: 시어(詩語) 감각 사전 & 방언/토속어
// ============================================================
let thesaurusSelectedWordRange = null;

async function openThesaurusModal() {
  const textarea = document.getElementById("inputFinalPoem");
  let queryWord = "";

  if (textarea && textarea.selectionStart !== textarea.selectionEnd) {
    queryWord = textarea.value.substring(textarea.selectionStart, textarea.selectionEnd).trim();
    thesaurusSelectedWordRange = {
      start: textarea.selectionStart,
      end: textarea.selectionEnd
    };
  } else {
    thesaurusSelectedWordRange = null;
  }

  const modal = document.getElementById("thesaurusModal");
  if (modal) modal.style.display = "flex";

  const searchInput = document.getElementById("thesaurusSearchInput");
  if (searchInput) {
    searchInput.value = queryWord || "어머니";
  }

  await loadThesaurusThemes();
  await searchThesaurusWord(queryWord || "어머니");
}

function closeThesaurusModal() {
  const modal = document.getElementById("thesaurusModal");
  if (modal) modal.style.display = "none";
}

async function loadThesaurusThemes() {
  const container = document.getElementById("thesaurusTagsContainer");
  if (!container) return;

  try {
    const res = await fetch("/api/thesaurus/all");
    const data = await res.json();
    if (res.ok && data.success) {
      container.innerHTML = "";
      data.categories.forEach(item => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "btn-copy";
        btn.style.padding = "4px 10px";
        btn.style.fontSize = "0.78rem";
        btn.style.color = "#4A3B80";
        btn.style.borderColor = "#DCD6F7";
        btn.style.background = "#F9F8FF";
        btn.innerHTML = `<strong>#${item.key}</strong> <span style="color: #8C827A; font-size: 0.72rem;">(${item.category_preview})</span>`;
        btn.onclick = () => {
          const searchInput = document.getElementById("thesaurusSearchInput");
          if (searchInput) searchInput.value = item.key;
          searchThesaurusWord(item.key);
        };
        container.appendChild(btn);
      });
    }
  } catch (err) {
    console.error("Thesaurus themes load error:", err);
  }
}

async function searchThesaurusWord(customQuery = null) {
  const searchInput = document.getElementById("thesaurusSearchInput");
  const word = (customQuery !== null ? customQuery : (searchInput ? searchInput.value : "")).trim();
  const resultArea = document.getElementById("thesaurusResultArea");
  if (!resultArea) return;

  if (!word) {
    resultArea.innerHTML = "<div style='color: var(--text-muted); padding: 20px; text-align: center;'>검색할 시어를 입력해 주세요.</div>";
    return;
  }

  resultArea.innerHTML = "<div style='color: var(--text-muted); padding: 20px; text-align: center;'>시어의 결을 탐색하는 중...</div>";

  try {
    const res = await fetch(`/api/thesaurus/lookup?word=${encodeURIComponent(word)}`);
    const data = await res.json();

    if (res.ok && data.success && data.found) {
      renderThesaurusResult(data.matched_key, data.data);
    } else {
      resultArea.innerHTML = `
        <div style="background: #FFF9F5; border: 1px dashed #EBD0B5; border-radius: 8px; padding: 20px; text-align: center;">
          <div style="font-weight: 700; color: #643E19; margin-bottom: 6px;">'${escapeHtml(word)}'에 대한 직관 사전 결과가 없습니다.</div>
          <p style="font-size: 0.82rem; color: var(--text-muted); margin-bottom: 12px;">아래의 정통 서정 시어 테마(#어머니, #목화, #비, #바람, #새벽, #그리움 등)를 클릭해 보세요.</p>
        </div>
      `;
    }
  } catch (err) {
    resultArea.innerHTML = `<div style='color: #c84b31;'>검색 오류: ${err.message}</div>`;
  }
}

function renderThesaurusResult(key, dbItem) {
  const resultArea = document.getElementById("thesaurusResultArea");
  if (!resultArea || !dbItem) return;

  let html = `
    <div style="background: #FDFBFF; border: 1px solid #E8E2F7; border-radius: 8px; padding: 14px 16px;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; border-bottom: 1px solid #EFEAFD; padding-bottom: 8px;">
        <span style="font-size: 1.05rem; font-weight: 700; color: #4A3B80; font-family: var(--font-serif);">
          『${escapeHtml(key)}』의 정서적 온도와 시어 팔레트
        </span>
        <span style="font-size: 0.74rem; color: #7B719B;">클릭 시 본문에 즉시 적용</span>
      </div>
      <div style="display: flex; flex-direction: column; gap: 12px;">
  `;

  for (const [catName, words] of Object.entries(dbItem.categories || {})) {
    html += `
      <div>
        <div style="font-size: 0.82rem; font-weight: 700; color: #5B4E8C; margin-bottom: 6px; display: flex; align-items: center; gap: 4px;">
          <span>🔹</span> <span>${escapeHtml(catName)}</span>
        </div>
        <div style="display: flex; flex-wrap: wrap; gap: 6px;">
    `;

    words.forEach(w => {
      const cleanWord = w.split('(')[0].trim();
      html += `
        <button type="button" class="btn-copy" onclick="applyThesaurusWord('${escapeHtml(cleanWord)}')" style="padding: 5px 12px; font-size: 0.84rem; background: #FFFFFF; border-color: #D6CEF0; color: #2C2520; transition: all 0.15s;" title="[클릭] 이 시어로 본문 교체하기">
          <strong>${escapeHtml(cleanWord)}</strong>
          ${w.includes('(') ? `<span style="font-size: 0.7rem; color: #8C827A;">(${escapeHtml(w.split('(')[1])}</span>` : ''}
        </button>
      `;
    });

    html += `
        </div>
      </div>
    `;
  }

  html += `
      </div>
    </div>
  `;

  resultArea.innerHTML = html;
}

function applyThesaurusWord(newWord) {
  const textarea = document.getElementById("inputFinalPoem");
  if (!textarea) return;

  const targetRange = thesaurusSelectedWordRange || activePaletteRange;
  if (targetRange && targetRange.start !== targetRange.end) {
    const value = textarea.value;
    textarea.value = value.substring(0, targetRange.start) + newWord + value.substring(targetRange.end);
    textarea.selectionStart = targetRange.start;
    textarea.selectionEnd = targetRange.start + newWord.length;
  } else {
    const pos = textarea.selectionStart || textarea.value.length;
    textarea.value = textarea.value.substring(0, pos) + " " + newWord + textarea.value.substring(pos);
    textarea.selectionStart = textarea.selectionEnd = pos + newWord.length + 1;
  }

  closeThesaurusModal();
  closePoeticPalette();
  textarea.focus();
  textarea.dispatchEvent(new Event("input", { bubbles: true }));

  try {
    navigator.clipboard.writeText(newWord);
  } catch (_) {}

  showCustomFloatingAlert(`✨ 시어 『${newWord}』가 본문에 아름답게 적용되었습니다!`);
}

// ============================================================
// 19. 시인의 집필실: [기둥 3] 공간의 시학 (행간·들여쓰기 타이포그래피 바)
// ============================================================

// 19-1. 들여쓰기 (선택된 행들 또는 현재 행의 시작에 공백 n칸 삽입)
function formatPoemIndent(spaces = 2) {
  const textarea = document.getElementById("inputFinalPoem");
  if (!textarea) return;

  const indentStr = " ".repeat(spaces);
  const start = textarea.selectionStart;
  const end = textarea.selectionEnd;
  const val = textarea.value;

  const lineStart = val.lastIndexOf("\n", start - 1) + 1;
  let lineEnd = val.indexOf("\n", end);
  if (lineEnd === -1) lineEnd = val.length;

  const targetText = val.substring(lineStart, lineEnd);
  const lines = targetText.split("\n");
  const indentedLines = lines.map(line => indentStr + line);
  const newText = indentedLines.join("\n");

  textarea.value = val.substring(0, lineStart) + newText + val.substring(lineEnd);
  
  textarea.selectionStart = start + spaces;
  textarea.selectionEnd = end + (spaces * lines.length);
  textarea.focus();
  textarea.dispatchEvent(new Event("input", { bubbles: true }));
}

// 19-2. 내어쓰기 (선택된 행들 또는 현재 행의 앞 공백 최대 n칸 삭제)
function formatPoemOutdent(spaces = 2) {
  const textarea = document.getElementById("inputFinalPoem");
  if (!textarea) return;

  const start = textarea.selectionStart;
  const end = textarea.selectionEnd;
  const val = textarea.value;

  const lineStart = val.lastIndexOf("\n", start - 1) + 1;
  let lineEnd = val.indexOf("\n", end);
  if (lineEnd === -1) lineEnd = val.length;

  const targetText = val.substring(lineStart, lineEnd);
  const lines = targetText.split("\n");
  let totalRemoved = 0;
  let firstLineRemoved = 0;

  const outdentedLines = lines.map((line, idx) => {
    let removed = 0;
    while (removed < spaces && line.startsWith(" ")) {
      line = line.substring(1);
      removed++;
    }
    if (idx === 0) firstLineRemoved = removed;
    totalRemoved += removed;
    return line;
  });

  const newText = outdentedLines.join("\n");
  textarea.value = val.substring(0, lineStart) + newText + val.substring(lineEnd);

  textarea.selectionStart = Math.max(lineStart, start - firstLineRemoved);
  textarea.selectionEnd = Math.max(lineStart, end - totalRemoved);
  textarea.focus();
  textarea.dispatchEvent(new Event("input", { bubbles: true }));
}

// 19-3. 깊은 여백 (연과 연 사이 깊은 침묵: 빈 줄 2칸 삽입)
function insertPoemDeepSpace() {
  const textarea = document.getElementById("inputFinalPoem");
  if (!textarea) return;

  const start = textarea.selectionStart;
  const end = textarea.selectionEnd;
  const val = textarea.value;

  const deepSpace = "\n\n";
  textarea.value = val.substring(0, start) + deepSpace + val.substring(end);
  textarea.selectionStart = textarea.selectionEnd = start + deepSpace.length;
  textarea.focus();
  textarea.dispatchEvent(new Event("input", { bubbles: true }));
}

// 19-4. 오른쪽 치우침 (>> 표식 토글)
function formatPoemAlignRight() {
  const textarea = document.getElementById("inputFinalPoem");
  if (!textarea) return;

  const start = textarea.selectionStart;
  const end = textarea.selectionEnd;
  const val = textarea.value;

  const lineStart = val.lastIndexOf("\n", start - 1) + 1;
  let lineEnd = val.indexOf("\n", end);
  if (lineEnd === -1) lineEnd = val.length;

  const targetText = val.substring(lineStart, lineEnd);
  const lines = targetText.split("\n");

  const toggledLines = lines.map(line => {
    const trimmed = line.trim();
    if (trimmed.startsWith(">>") || trimmed.startsWith("》》")) {
      return line.replace(/^(\s*)(>>\s*|》》\s*)/, '$1');
    } else {
      return ">> " + line.trim();
    }
  });

  const newText = toggledLines.join("\n");
  textarea.value = val.substring(0, lineStart) + newText + val.substring(lineEnd);
  textarea.selectionStart = lineStart;
  textarea.selectionEnd = lineStart + newText.length;
  textarea.focus();
  textarea.dispatchEvent(new Event("input", { bubbles: true }));
}

// 19-5. 에디터 Tab / Shift+Tab 단축키 등록
function setupPoemEditorKeybindings() {
  const textarea = document.getElementById("inputFinalPoem");
  if (!textarea) return;

  textarea.addEventListener("keydown", function(e) {
    if (e.key === "Tab") {
      e.preventDefault();
      if (e.shiftKey) {
        formatPoemOutdent(2);
      } else {
        formatPoemIndent(2);
      }
    }
  });
}

// ============================================================
// 20. 시인의 집필실: [기둥 1] 인라인 미니 플로팅 시어 팔레트
// ============================================================
let activePaletteWord = "";
let activePaletteRange = null;

function setupPoeticFloatingPalette() {
  const textarea = document.getElementById("inputFinalPoem");
  if (!textarea) return;

  const handleSelection = () => {
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    if (start === end) return;

    const selectedText = textarea.value.substring(start, end).trim();
    // 2자 이상 15자 이하의 단어 선택 시 미니 플로팅 팔레트 트리거
    if (selectedText.length >= 2 && selectedText.length <= 15) {
      activePaletteWord = selectedText;
      activePaletteRange = { start, end };
      thesaurusSelectedWordRange = { start, end };
      openPoeticFloatingPalette(selectedText);
    }
  };

  textarea.addEventListener("mouseup", () => {
    setTimeout(handleSelection, 20);
  });

  textarea.addEventListener("keyup", (e) => {
    if (e.shiftKey && ["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(e.key)) {
      handleSelection();
    }
  });

  // ESC 누르면 닫기
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      closePoeticPalette();
    }
  });

  // 팔레트 바깥 클릭 시 닫기
  document.addEventListener("mousedown", (e) => {
    const palette = document.getElementById("poeticFloatingPalette");
    if (!palette || palette.style.display === "none") return;
    if (!palette.contains(e.target) && e.target !== textarea) {
      closePoeticPalette();
    }
  });
}

async function openPoeticFloatingPalette(word) {
  const palette = document.getElementById("poeticFloatingPalette");
  const textarea = document.getElementById("inputFinalPoem");
  if (!palette || !textarea) return;

  const titleElem = document.getElementById("floatingWordTitle");
  if (titleElem) titleElem.textContent = `『${escapeHtml(word)}』의 시어 결`;

  const chipsContainer = document.getElementById("floatingChipsContainer");
  if (chipsContainer) {
    chipsContainer.innerHTML = '<div class="palette-loading" style="font-size: 0.8rem; color: #8C827A; padding: 6px;">시어의 결을 벼리는 중...</div>';
  }

  // 팔레트 위치 지정 (textarea 상단 또는 커서 주변 안전 위치)
  const rect = textarea.getBoundingClientRect();
  palette.style.display = "block";
  palette.style.position = "absolute";

  const topPos = window.scrollY + rect.top + 36;
  const leftPos = Math.min(window.scrollX + rect.left + 24, window.innerWidth - 340);
  palette.style.top = `${topPos}px`;
  palette.style.left = `${Math.max(10, leftPos)}px`;

  // 1차: 사전 검색
  try {
    const res = await fetch(`/api/thesaurus/lookup?word=${encodeURIComponent(word)}`);
    const data = await res.json();

    if (res.ok && data.success && data.found && data.data) {
      renderPaletteChipsFromDb(data.data);
    } else {
      // 사전에 없을 때 실시간 AI 감각 추천 자동 호출
      await requestAiPoeticPalette(word);
    }
  } catch (err) {
    if (chipsContainer) {
      chipsContainer.innerHTML = `<div style="font-size: 0.78rem; color: #8C827A; padding: 4px;">사전 대기 중. <a href="#" onclick="requestAiPoeticPalette(); return false;" style="color: #4A3B80; font-weight: 700;">[AI 추천받기]</a></div>`;
    }
  }
}

function renderPaletteChipsFromDb(dbItem) {
  const chipsContainer = document.getElementById("floatingChipsContainer");
  if (!chipsContainer || !dbItem) return;

  chipsContainer.innerHTML = "";
  const categories = dbItem.categories || {};
  let count = 0;

  for (const [catName, words] of Object.entries(categories)) {
    for (const w of words) {
      if (count >= 8) break;
      const cleanWord = w.split("(")[0].trim();
      const desc = w.includes("(") ? w.split("(")[1].replace(")", "") : catName;

      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "poetic-chip-btn";
      btn.title = `[클릭] '${cleanWord}'(으)로 본문 교체하기`;
      btn.innerHTML = `<strong>${escapeHtml(cleanWord)}</strong> <span class="poetic-chip-desc">(${escapeHtml(desc)})</span>`;
      btn.onclick = () => replaceSelectedWord(cleanWord);
      chipsContainer.appendChild(btn);
      count++;
    }
    if (count >= 8) break;
  }
}

async function requestAiPoeticPalette(customWord = null) {
  const word = customWord || activePaletteWord;
  if (!word) return;

  const chipsContainer = document.getElementById("floatingChipsContainer");
  if (chipsContainer) {
    chipsContainer.innerHTML = '<div class="palette-loading" style="font-size: 0.8rem; color: #5B4E8C; padding: 6px;">💫 AI가 서정적 시어의 결을 빚는 중...</div>';
  }

  const textarea = document.getElementById("inputFinalPoem");
  const poemContext = textarea ? textarea.value.substring(0, 300) : "";

  try {
    const res = await fetch(`/api/thesaurus/suggest?word=${encodeURIComponent(word)}&context=${encodeURIComponent(poemContext)}`);
    const data = await res.json();

    if (res.ok && data.success && data.suggestions && data.suggestions.length > 0) {
      chipsContainer.innerHTML = "";
      data.suggestions.forEach(item => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "poetic-chip-btn";
        btn.title = `[클릭] '${item.word}'(으)로 본문 교체하기`;
        btn.innerHTML = `<strong>${escapeHtml(item.word)}</strong> <span class="poetic-chip-desc">(${escapeHtml(item.desc || item.category)})</span>`;
        btn.onclick = () => replaceSelectedWord(item.word);
        chipsContainer.appendChild(btn);
      });
    } else {
      if (chipsContainer) {
        chipsContainer.innerHTML = '<div style="font-size: 0.78rem; color: #8C827A; padding: 6px;">추천된 시어가 없습니다. 감각 사전을 열어보세요.</div>';
      }
    }
  } catch (err) {
    if (chipsContainer) {
      chipsContainer.innerHTML = `<div style="font-size: 0.78rem; color: #C84B31; padding: 6px;">추천 오류: ${err.message}</div>`;
    }
  }
}

function replaceSelectedWord(newWord) {
  const textarea = document.getElementById("inputFinalPoem");
  if (!textarea) return;

  const targetRange = activePaletteRange || thesaurusSelectedWordRange;
  if (targetRange && targetRange.start !== targetRange.end) {
    const val = textarea.value;
    textarea.value = val.substring(0, targetRange.start) + newWord + val.substring(targetRange.end);
    textarea.selectionStart = targetRange.start;
    textarea.selectionEnd = targetRange.start + newWord.length;
  } else {
    const pos = textarea.selectionStart || textarea.value.length;
    const val = textarea.value;
    textarea.value = val.substring(0, pos) + newWord + val.substring(pos);
    textarea.selectionStart = textarea.selectionEnd = pos + newWord.length;
  }

  textarea.focus();
  textarea.dispatchEvent(new Event("input", { bubbles: true }));
  closePoeticPalette();

  showCustomFloatingAlert(`✨ 시어 『${newWord}』가 본문에 아름답게 교체되었습니다!`);
}

function closePoeticPalette() {
  const palette = document.getElementById("poeticFloatingPalette");
  if (palette) palette.style.display = "none";
}

function expandToThesaurusModal() {
  closePoeticPalette();
  openThesaurusModal();
}

function showCustomFloatingAlert(msg) {
  const alertBox = document.createElement("div");
  alertBox.style.position = "fixed";
  alertBox.style.bottom = "24px";
  alertBox.style.right = "24px";
  alertBox.style.zIndex = "9999";
  alertBox.style.background = "#4A3B80";
  alertBox.style.color = "#FFFFFF";
  alertBox.style.padding = "10px 18px";
  alertBox.style.borderRadius = "8px";
  alertBox.style.boxShadow = "0 6px 18px rgba(74, 59, 128, 0.35)";
  alertBox.style.fontSize = "0.88rem";
  alertBox.style.fontFamily = "var(--font-serif)";
  alertBox.textContent = msg;
  document.body.appendChild(alertBox);

  setTimeout(() => {
    alertBox.style.opacity = "0";
    alertBox.style.transition = "opacity 0.4s ease";
    setTimeout(() => alertBox.remove(), 400);
  }, 2200);
}

// 초기화 바인딩
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => {
    bindEvents();
    setupPoemEditorKeybindings();
    setupPoeticFloatingPalette();
    setTimeout(alignPoemEditorWithAudioDropzone, 200);
    checkGeminiKeyStatus();
  });
} else {
  bindEvents();
  setupPoemEditorKeybindings();
  setupPoeticFloatingPalette();
  setTimeout(alignPoemEditorWithAudioDropzone, 200);
  checkGeminiKeyStatus();
}

