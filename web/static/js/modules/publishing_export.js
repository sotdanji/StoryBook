// ============================================================================
// [Module] publishing_export.js - 부크크 책등 계산기, 이미지 규격 검사, 서문/에필로그/판권지(Book Extras) 연동
// ============================================================================
// 12. 부크크 책등 계산기 실시간 연동
async function calculateSpecs() {
  const pages = document.getElementById("inputPages").value || 80;
  try {
    const res = await fetch(`/api/book_spec?pages=${pages}`);
    const data = await res.json();

    document.getElementById("specSpine").textContent = `${data.spine_thickness_mm} mm`;
    document.getElementById("specCoverSize").textContent = `${data.cover_canvas_width_mm} × ${data.cover_canvas_height_mm} mm`;
  } catch (err) {
    console.error("규격 계산 실패:", err);
  }
}

// 13. 이미지 규격 검사 리스트 로드
async function loadImagesInspection() {
  const container = document.getElementById("imagesInspectionContainer");
  try {
    const res = await fetch("/api/images");
    const list = await res.json();

    if (list.length === 0) {
      container.innerHTML = `<p style="color: var(--text-muted); font-size: 0.9rem;">현재 시집에 등록된 이미지가 없습니다.</p>`;
      return;
    }

    let html = `<div style="display: flex; flex-direction: column; gap: 8px;">`;
    list.forEach(item => {
      const isOk = item.is_ready;
      const statusColor = isOk ? "var(--accent-green)" : "#C84B31";
      html += `
        <div style="background: #FCFAF7; padding: 10px 14px; border-radius: 6px; border: 1px solid var(--border-subtle); display: flex; justify-content: space-between; align-items: center; font-size: 0.9rem;">
          <div>
            <strong>${item.filename}</strong>
            <span style="color: var(--text-muted); font-size: 0.82rem; margin-left: 8px;">${item.resolution} | ${item.dpi}</span>
          </div>
          <span style="color: ${statusColor}; font-weight: 600;">${item.status}</span>
        </div>
      `;
    });
    html += `</div>`;
    container.innerHTML = html;
  } catch (err) {
    container.innerHTML = `<p style="color: red;">검사 실패: ${err}</p>`;
  }
}


// =============================================================
// 📖 시집 본문 외 출판 완결 편집실 (Front & Back Matter) 연동
// =============================================================

async function loadBookExtras() {
  try {
    const res = await fetch("/api/book_extras");
    if (!res.ok) return;
    const data = await res.json();
    if (!data.success) return;

    const extras = data.extras || {};

    const prologueInput = document.getElementById("bookPrologueInput");
    if (prologueInput && !prologueInput.value) {
      prologueInput.value = extras.prologue || "";
    }

    const epilogueInput = document.getElementById("bookEpilogueInput");
    if (epilogueInput && !epilogueInput.value) {
      epilogueInput.value = extras.epilogue || "";
    }

    const blurbInput = document.getElementById("bookBlurbInput");
    if (blurbInput && !blurbInput.value) {
      blurbInput.value = extras.back_cover_blurb || "";
    }

    const pubInput = document.getElementById("bookPublisherInput");
    if (pubInput && extras.publisher) {
      pubInput.value = extras.publisher;
    }

    const dateInput = document.getElementById("bookPublishedDateInput");
    if (dateInput && extras.published_date) {
      dateInput.value = extras.published_date;
    }

    const priceInput = document.getElementById("bookPriceInput");
    if (priceInput && extras.price) {
      priceInput.value = extras.price;
    }

    const isbnInput = document.getElementById("bookIsbnInput");
    if (isbnInput && extras.isbn) {
      isbnInput.value = extras.isbn;
    }

    // 앞표지 삽화 목록 채우기
    const coverSelect = document.getElementById("bookCoverImageSelect");
    if (coverSelect && data.available_images) {
      const currentSelected = extras.cover_image || "";
      coverSelect.innerHTML = `<option value="">(삽화 없음 - 타이포그래피 표지)</option>`;
      data.available_images.forEach(img => {
        const isSel = (img === currentSelected || `images/${img}` === currentSelected) ? "selected" : "";
        coverSelect.innerHTML += `<option value="images/${img}" ${isSel}>${img}</option>`;
      });
    }
  } catch (err) {
    console.error("Error loading book extras:", err);
  }
}

async function saveBookExtras() {
  const btn = document.getElementById("btnSaveBookExtras");
  const origText = btn ? btn.innerHTML : "";

  try {
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = `<span>⏳ 저장 중...</span>`;
    }

    const payload = {
      prologue: document.getElementById("bookPrologueInput")?.value || "",
      epilogue: document.getElementById("bookEpilogueInput")?.value || "",
      back_cover_blurb: document.getElementById("bookBlurbInput")?.value || "",
      cover_image: document.getElementById("bookCoverImageSelect")?.value || "",
      publisher: document.getElementById("bookPublisherInput")?.value || "부크크 (Bookk) 자가출판",
      published_date: document.getElementById("bookPublishedDateInput")?.value || "",
      price: document.getElementById("bookPriceInput")?.value || "13,000원",
      isbn: document.getElementById("bookIsbnInput")?.value || ""
    };

    const res = await fetch("/api/book_extras/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.detail || data.message || "저장 실패");
    }

    alert("✨ 시인의 말, 맺음말, 뒷표지 카피, 판권 정보가 시집 출판 메타데이터에 안전하게 저장되었습니다!\n\n이제 [부크크 내지/표지 완제본 PDF]나 [Canva 출판 CSV]를 내려받으시면 완벽히 반영됩니다.");
  } catch (err) {
    alert("출판 구성 요소 저장 중 오류가 발생했습니다: " + err.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = origText;
    }
  }
}

async function generateBookExtra(target, btnId, inputId) {
  const btn = document.getElementById(btnId);
  const input = document.getElementById(inputId);
  const origHtml = btn ? btn.innerHTML : "";

  try {
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = `<span>✨ 감성 집필 중...</span>`;
    }

    const res = await fetch("/api/book_extras/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target })
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.detail || "AI 생성 실패");
    }

    if (input) {
      input.value = data.generated_text;
      input.style.backgroundColor = "#FFFDF0";
      setTimeout(() => {
        input.style.backgroundColor = "#FFFFFF";
      }, 1000);
      input.focus();
    }
  } catch (err) {
    alert("AI 문구 생성 중 오류가 발생했습니다: " + err.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = origHtml;
    }
  }
}

// 이벤트 리스너 등록
document.addEventListener("DOMContentLoaded", () => {
  // 출판 데이터 탭 진입 시 로드
  const tabBtnExport = document.getElementById("tabBtnExport");
  if (tabBtnExport) {
    tabBtnExport.addEventListener("click", () => {
      loadBookExtras();
    });
  }

  // 출판 저장 버튼
  const btnSave = document.getElementById("btnSaveBookExtras");
  if (btnSave) {
    btnSave.addEventListener("click", saveBookExtras);
  }

  // AI 생성 버튼들
  const btnPrologue = document.getElementById("btnGenPrologue");
  if (btnPrologue) {
    btnPrologue.addEventListener("click", () => generateBookExtra("prologue", "btnGenPrologue", "bookPrologueInput"));
  }

  const btnEpilogue = document.getElementById("btnGenEpilogue");
  if (btnEpilogue) {
    btnEpilogue.addEventListener("click", () => generateBookExtra("epilogue", "btnGenEpilogue", "bookEpilogueInput"));
  }

  const btnBlurb = document.getElementById("btnGenBlurb");
  if (btnBlurb) {
    btnBlurb.addEventListener("click", () => generateBookExtra("back_cover_blurb", "btnGenBlurb", "bookBlurbInput"));
  }

  // 초기 1회 로드
  setTimeout(loadBookExtras, 800);
  initAudioMutualExclusion();
  checkInitialTtsStatus();
});

// 🎧 오디오 중복 재생 방지 (낭송, 노래, TTS 상호 배타적 제어)
function initAudioMutualExclusion() {
  const recitePlayer = document.getElementById("studioRecitePlayer");
  const musicPlayer = document.getElementById("studioAudioPlayer");

  if (recitePlayer) {
    recitePlayer.addEventListener("play", () => {
      // 낭송이 시작되면 노래 및 TTS 즉시 중단
      if (musicPlayer && !musicPlayer.paused) {
        musicPlayer.pause();
      }
      if (currentGeminiReciteAudio && !currentGeminiReciteAudio.paused) {
        currentGeminiReciteAudio.pause();
        const btn = document.getElementById("btnSpeakPoem");
        if (btn) btn.innerHTML = "🎧 시 낭송 듣기";
      }
      if (window.speechSynthesis && window.speechSynthesis.speaking) {
        window.speechSynthesis.cancel();
      }
    });
  }

  if (musicPlayer) {
    musicPlayer.addEventListener("play", () => {
      // 노래가 시작되면 낭송 및 TTS 즉시 중단
      if (recitePlayer && !recitePlayer.paused) {
        recitePlayer.pause();
      }
      if (currentGeminiReciteAudio && !currentGeminiReciteAudio.paused) {
        currentGeminiReciteAudio.pause();
        const btn = document.getElementById("btnSpeakPoem");
        if (btn) btn.innerHTML = "🎧 시 낭송 듣기";
      }
      if (window.speechSynthesis && window.speechSynthesis.speaking) {
        window.speechSynthesis.cancel();
      }
    });
  }
}







