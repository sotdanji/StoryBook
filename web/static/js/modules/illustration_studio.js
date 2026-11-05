// ============================================================================
// [Module] illustration_studio.js - 감성 삽화 생성, 참조 이미지, 일괄 생성, 300 DPI 보정, Colab SDXL
// ============================================================================
// =========================================================
// 14. 2원화 감성 삽화 관리: 무료 원클릭 자동 생성 & 드래그 앤 드롭 업로드
// =========================================================

// 14-1. 드래그 앤 드롭 이벤트 초기화
function initDropzones() {
  // 1) 스튜디오 드롭존
  const studioDropzone = document.getElementById("studioDropzone");
  if (studioDropzone) {
    ['dragenter', 'dragover'].forEach(eventName => {
      studioDropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        studioDropzone.classList.add('drag-over');
      }, false);
    });

    ['dragleave', 'dragend'].forEach(eventName => {
      studioDropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        studioDropzone.classList.remove('drag-over');
      }, false);
    });

    studioDropzone.addEventListener('drop', (e) => {
      e.preventDefault();
      e.stopPropagation();
      studioDropzone.classList.remove('drag-over');
      const dt = e.dataTransfer;
      const files = dt.files;
      if (files && files.length > 0) {
        uploadStudioImage(files[0]);
      }
    }, false);
  }

  // 2) 가상 북 뷰어 좌측 페이지 드롭존
  const viewerDropzone = document.getElementById("viewerDropzone");
  const viewerDropOverlay = document.getElementById("viewerDropOverlay");

  if (viewerDropzone && viewerDropOverlay) {
    ['dragenter', 'dragover'].forEach(eventName => {
      viewerDropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        viewerDropOverlay.style.display = 'flex';
      }, false);
    });

    viewerDropOverlay.addEventListener('dragleave', (e) => {
      e.preventDefault();
      e.stopPropagation();
      viewerDropOverlay.style.display = 'none';
    }, false);

    viewerDropOverlay.addEventListener('drop', (e) => {
      e.preventDefault();
      e.stopPropagation();
      viewerDropOverlay.style.display = 'none';
      const dt = e.dataTransfer;
      const files = dt.files;
      if (files && files.length > 0) {
        currentViewerTargetSlot = (currentSpreadPart === 2) ? "part2" : "main";
        uploadViewerImage(files[0]);
      }
    }, false);
  }

  // 3) 스튜디오 오디오 음원 드롭존
  const audioDropzone = document.getElementById("studioAudioDropzone");
  if (audioDropzone) {
    ['dragenter', 'dragover'].forEach(eventName => {
      audioDropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        audioDropzone.classList.add('drag-over');
      }, false);
    });

    ['dragleave', 'dragend'].forEach(eventName => {
      audioDropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        audioDropzone.classList.remove('drag-over');
      }, false);
    });

    audioDropzone.addEventListener('drop', (e) => {
      e.preventDefault();
      e.stopPropagation();
      audioDropzone.classList.remove('drag-over');
      const dt = e.dataTransfer;
      const files = dt.files;
      if (files && files.length > 0) {
        uploadStudioAudio(files[0]);
      }
    }, false);
  }
}

// 14-2. 스튜디오: 파일 선택창 트리거 & 체인지
function triggerStudioFileInput() {
  const input = document.getElementById("studioFileInput");
  if (input) input.click();
}

function onStudioFileSelected(event) {
  const file = event.target.files && event.target.files[0];
  if (file) {
    uploadStudioImage(file);
  }
}

// 14-3. 스튜디오: 방법 2 (나노바나나/Gemini 이미지 업로드 실행)
async function uploadStudioImage(file) {
  if (!file.type.startsWith("image/")) {
    alert("이미지 파일(JPG, PNG, WebP 등)만 업로드할 수 있습니다.");
    return;
  }

  const ep = document.getElementById("inputEpisode").value || "제01화";
  const statusBox = document.getElementById("studioUploadStatus");
  statusBox.className = "upload-status-text loading";
  statusBox.style.display = "block";
  statusBox.innerHTML = `<span>⏳ [${ep}] 그림 파일 업로드 및 적용 중...</span>`;

  const formData = new FormData();
  formData.append("file", file);
  formData.append("episode_no", ep);

  try {
    const res = await fetch("/api/upload_image", {
      method: "POST",
      body: formData
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.detail || "업로드 실패");
    }

    statusBox.className = "upload-status-text success";
    statusBox.innerHTML = `<span>✓ ${data.message}</span>`;

    // 미리보기 바 갱신
    const previewArea = document.getElementById("studioImagePreviewArea");
    const previewImg = document.getElementById("studioPreviewImg");
    const previewFilename = document.getElementById("studioPreviewFilename");
    if (previewArea && previewImg && previewFilename) {
      previewArea.style.display = "flex";
      previewImg.src = data.image_url;
      previewFilename.textContent = data.filename;
    }

    await loadStatus();
    await loadImagesInspection();

  } catch (err) {
    statusBox.className = "upload-status-text error";
    statusBox.innerHTML = `<span>⚠️ 오류: ${err.message}</span>`;
  }
}

let currentCandidateData = null;

let currentPreviewCandidate = null; // { episode_no, title, filename, image_url }

// 14-4. 스튜디오: 방법 1 (무료 API 단일 삽화 생성 후 미리보기 모달 팝업)
async function onStudioGenerateFreeImage() {
  const ep = document.getElementById("inputEpisode").value || "제01화";
  const title = document.getElementById("inputFinalTitle").value || "";
  const memory = document.getElementById("inputCoreMemory").value || "";
  const promptElem = document.getElementById("imagePromptDisplay");
  const prompt = promptElem ? (promptElem.value || promptElem.textContent || "").trim() : "";

  const btn = document.getElementById("btnStudioGenerateFree");
  const statusBox = document.getElementById("studioGenStatus");
  const originalText = btn.innerHTML;
  const meta = artStyleMeta[currentArtStyle] || artStyleMeta.watercolor;

  btn.disabled = true;
  btn.innerHTML = `<span>⏳ ${meta.name} 삽화 그리는 중... (생성 대기 필요)</span>`;
  if (statusBox) {
    statusBox.className = "gen-status-text loading";
    statusBox.style.display = "block";
    statusBox.innerHTML = `<span>🎨 무료 한도 절약을 위해 단 1장의 최적 ${meta.name} 삽화를 그리는 중입니다...</span>`;
  }

  try {
    const res = await fetch("/api/generate_image_candidates", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        episode_no: ep,
        title: title,
        memory_anchor: memory,
        prompt: prompt,
        art_style: currentArtStyle
      })
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.detail || "삽화 생성 실패");
    }

    if (data.used_prompt && promptElem) {
      promptElem.value = data.used_prompt;
    }

    if (statusBox) {
      statusBox.className = "gen-status-text success";
      statusBox.innerHTML = `<span>✓ 삽화가 생성되었습니다. 미리보기 창에서 확인하세요.</span>`;
    }

    // 미리보기 모달 팝업 열기 (사용자가 [삽입]을 선택할 때만 본문에 반영)
    openImagePreviewConfirmModal({
      episode_no: ep,
      title: title,
      filename: data.filename,
      image_url: data.image_url
    });

  } catch (err) {
    if (statusBox) {
      statusBox.className = "gen-status-text error";
      statusBox.innerHTML = `<span>⚠️ 생성 실패: ${err.message}</span>`;
    }
    showToast(`⚠️ 삽화 생성 실패: ${err.message}`, "error");
  } finally {
    btn.disabled = false;
    btn.innerHTML = originalText;
  }
}

// 🎨 생성된 삽화 미리보기 모달 열기 (1~4면 및 분할 프레임별 정확한 타겟 레이블 지원)
function openImagePreviewConfirmModal(item) {
  currentPreviewCandidate = item;
  const modal = document.getElementById("imagePreviewConfirmModal");
  if (!modal) return;

  const pageNum = item.page_num || (item.target_slot === "part2" ? 4 : (currentSpreadPart === 2 ? 4 : 2));
  const frameIdx = item.frame_idx || 1;
  const isPart2 = (item.target_slot === "part2") || (pageNum >= 3);
  const frameDesc = frameIdx === 2 ? " 2번" : "";

  const titleEl = document.getElementById("labelPreviewModalTitle");
  if (titleEl) {
    titleEl.textContent = `[${item.episode_no}] 「${item.title || '새벽 대청'}」 ${pageNum}면${frameDesc} 삽화 미리보기`;
  }

  const descEl = modal.querySelector(".modal-desc");
  if (descEl) {
    descEl.innerHTML = isPart2
      ? `시의 후반부 정경을 바탕으로 그린 <strong>${pageNum}면${frameDesc} 수채화</strong>입니다. 마음에 드시면 <strong>[삽화로 삽입]</strong>을 누르세요.`
      : `새로 생성된 그림을 확인하세요. 마음에 드시면 <strong>[삽화로 삽입]</strong>을 누르고, 마음에 들지 않으면 <strong>[다시 생성]</strong> 또는 <strong>[취소]</strong>를 누르세요.`;
  }

  const imgEl = document.getElementById("imgPreviewConfirm");
  if (imgEl) {
    imgEl.src = item.image_url;
  }

  const overlay = document.getElementById("imgPreviewLoadingOverlay");
  if (overlay) overlay.style.display = "none";

  const btnInsert = document.getElementById("btnConfirmInsertImage");
  if (btnInsert) {
    btnInsert.disabled = false;
    btnInsert.innerHTML = `<span>✨ ${pageNum}면${frameDesc} 삽화로 삽입</span>`;
  }

  modal.style.display = "flex";
}

// 모달 닫기 (취소: 기존 그림 유지)
function closeImagePreviewConfirmModal() {
  const modal = document.getElementById("imagePreviewConfirmModal");
  if (modal) modal.style.display = "none";
  currentPreviewCandidate = null;
  clearArtReferenceImage();
}

// [✨ 삽화로 삽입] 클릭 시: 원고에 공식 반영 (정확한 면/프레임별 독립 저장 및 서버 영구 동기화)
async function onConfirmInsertImage() {
  if (!currentPreviewCandidate) return;

  const btn = document.getElementById("btnConfirmInsertImage");
  const origText = btn ? btn.innerHTML : "";
  const pageNum = currentPreviewCandidate.page_num || (currentPreviewCandidate.target_slot === "part2" ? 4 : (currentSpreadPart === 2 ? 4 : 2));
  const frameIdx = currentPreviewCandidate.frame_idx || 1;
  const isPart2 = (currentPreviewCandidate.target_slot === "part2") || (pageNum >= 3);
  const targetIdx = pageNum - 1;

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<span>⏳ ${pageNum}면 삽화 반영 중...</span>`;
  }

  try {
    const res = await fetch("/api/select_image_candidate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        episode_no: currentPreviewCandidate.episode_no,
        candidate_filename: currentPreviewCandidate.filename,
        candidate_name: isPart2 ? "2부 연작 시안" : "생성 시안",
        target_slot: currentPreviewCandidate.target_slot || (pageNum >= 3 ? "part2" : "part1"),
        page_num: pageNum,
        frame_idx: frameIdx
      })
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.detail || "삽화 반영 실패");
    }

    const frameDesc = frameIdx === 2 ? " 2번" : "";
    showToast(`✅ [${currentPreviewCandidate.episode_no}] ${pageNum}면${frameDesc} 삽화가 성공적으로 본문에 삽입되었습니다!`, "success");
    closeImagePreviewConfirmModal();

    // 상태 동기화 & 조판 화면 갱신 (현재 스프레드 위치 유지)
    const savedPart = (pageNum >= 3) ? 2 : (currentSpreadPart || 1);
    await loadStatus();
    await loadImagesInspection();

    if (currentStatus && currentStatus.works && typeof currentWorkIndex !== 'undefined') {
      const curWork = currentStatus.works[currentWorkIndex];
      if (curWork) {
        if (!curWork.layout_config || !Array.isArray(curWork.layout_config.pages)) {
          if (window.dtpEditor) curWork.layout_config = window.dtpEditor.getNormalizedConfig(curWork);
        }
        if (curWork.layout_config && Array.isArray(curWork.layout_config.pages)) {
          while (curWork.layout_config.pages.length <= targetIdx) {
            const pNum = curWork.layout_config.pages.length + 1;
            curWork.layout_config.pages.push({
              page_num: pNum,
              usage: pNum === 1 ? "image" : (pNum === 3 ? "image_text" : "text"),
              role: pNum === 1 ? "none" : (pNum === 2 ? "start" : "continue"),
              image_file: "",
              custom_text: ""
            });
          }
          if (frameIdx === 2) {
            curWork.layout_config.pages[targetIdx].image_file_b = `./images/${data.filename}`;
          } else {
            curWork.layout_config.pages[targetIdx].image_file = `./images/${data.filename}`;
          }
          if (curWork.layout_config.pages[targetIdx].usage === "text") {
            curWork.layout_config.pages[targetIdx].usage = "image_text";
          }
        }
        if (pageNum === 1 && frameIdx === 1) {
          curWork.image_file = `./images/${data.filename}`;
        } else if (pageNum === 3 && frameIdx === 1) {
          curWork.image_file_2 = `./images/${data.filename}`;
          curWork.part2_mode = "image";
          curWork.layout_mode = "multi_page";
        } else if (pageNum >= 3 && !curWork.image_file_2) {
          curWork.image_file_2 = `./images/${data.filename}`;
          curWork.part2_mode = "image";
          curWork.layout_mode = "multi_page";
        }

        // 백엔드에 즉시 저장
        if (window.dtpEditor && typeof window.dtpEditor.saveLayoutConfigToServer === 'function') {
          window.dtpEditor.saveLayoutConfigToServer(curWork.episode_no, curWork.layout_config);
        } else if (typeof saveWorkLayoutConfigToServer === 'function') {
          saveWorkLayoutConfigToServer(curWork.episode_no, curWork.layout_config);
        }
      }
    }

    currentSpreadPart = savedPart;
    window.currentSpreadPart = savedPart;
    if (window.dtpEditor && typeof window.dtpEditor.refreshImages === 'function') {
      window.dtpEditor.currentSpreadPart = savedPart;
      window.dtpEditor.refreshImages();
    } else if (typeof renderBookSpread === 'function' && typeof currentWorkIndex !== 'undefined') {
      renderBookSpread(currentWorkIndex);
    }

  } catch (err) {
    alert("삽화 반영 중 오류: " + err.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = origText;
    }
  }
}

// ========================================================
// 📷 [신규] 삽화 참조 사진 / 그림 첨부 및 비전 분석 처리
// ========================================================
let currentArtReferenceBase64 = null;

function handleArtReferenceBlob(blob, filename = "참조사진.jpg") {
  if (!blob || !blob.type.startsWith("image/")) {
    alert("이미지 파일만 첨부할 수 있습니다.");
    return;
  }
  const reader = new FileReader();
  reader.onload = function(e) {
    currentArtReferenceBase64 = e.target.result;
    const box = document.getElementById("artReferencePreviewBox");
    const thumb = document.getElementById("imgArtReferenceThumb");
    const nameEl = document.getElementById("artReferenceFileName");
    const optBox = document.getElementById("artReferenceOptionsBox");

    if (thumb) thumb.src = currentArtReferenceBase64;
    if (nameEl) nameEl.textContent = filename;
    if (box) box.style.display = "flex";
    if (optBox) optBox.style.display = "flex";

    showToast("📷 참조 사진이 첨부되었습니다! [🔄 다시 생성]을 누르면 사진 구도를 반영합니다.", "info");
  };
  reader.readAsDataURL(blob);
}

function handleArtReferenceFileSelected(input) {
  if (input && input.files && input.files[0]) {
    const file = input.files[0];
    handleArtReferenceBlob(file, file.name);
  }
}

function clearArtReferenceImage() {
  currentArtReferenceBase64 = null;
  const fileInput = document.getElementById("inputArtReferenceFile");
  if (fileInput) fileInput.value = "";
  const box = document.getElementById("artReferencePreviewBox");
  if (box) box.style.display = "none";
  const optBox = document.getElementById("artReferenceOptionsBox");
  if (optBox) optBox.style.display = "none";
  const thumb = document.getElementById("imgArtReferenceThumb");
  if (thumb) thumb.src = "";
  const radioVision = document.getElementById("radioRefAiVision");
  if (radioVision) radioVision.checked = true;
}

// 드래그 앤 드롭 지원
document.addEventListener("DOMContentLoaded", function() {
  const dropZone = document.getElementById("artReferenceDropZone");
  if (!dropZone) return;

  dropZone.addEventListener("dragover", function(e) {
    e.preventDefault();
    dropZone.style.borderColor = "#643E19";
    dropZone.style.background = "#F7EFE9";
  });
  dropZone.addEventListener("dragleave", function(e) {
    e.preventDefault();
    dropZone.style.borderColor = "#C8B9A6";
    dropZone.style.background = "#FFFFFF";
  });
  dropZone.addEventListener("drop", function(e) {
    e.preventDefault();
    dropZone.style.borderColor = "#C8B9A6";
    dropZone.style.background = "#FFFFFF";
    if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      handleArtReferenceBlob(file, file.name);
    }
  });
});

// 클립보드 이미지 붙여넣기 (Ctrl+V) 지원: 미리보기 모달이 열려 있을 때 이미지 붙여넣기 시 즉시 참조 사진으로 장착!
window.addEventListener("paste", function(e) {
  const modal = document.getElementById("imagePreviewConfirmModal");
  if (!modal || modal.style.display === "none") return;

  if (e.clipboardData && e.clipboardData.items) {
    for (let i = 0; i < e.clipboardData.items.length; i++) {
      const item = e.clipboardData.items[i];
      if (item.type.indexOf("image") !== -1) {
        const blob = item.getAsFile();
        if (blob) {
          handleArtReferenceBlob(blob, `클립보드_캡처_${new Date().toLocaleTimeString().replace(/:/g, '')}.jpg`);
          e.preventDefault();
          break;
        }
      }
    }
  }
});

// [🔄 다시 생성] 클릭 시: 모달 내부에서 즉시 새로운 시드로 재생성 (참조 사진/직접 사용 옵션 완벽 지원)
async function onRegeneratePreviewImage() {
  if (!currentPreviewCandidate) return;

  const ep = currentPreviewCandidate.episode_no;
  const title = currentPreviewCandidate.title;
  const isPart2 = (currentPreviewCandidate.target_slot === "part2");
  const memory = document.getElementById("inputCoreMemory") ? document.getElementById("inputCoreMemory").value : "";
  const promptElem = document.getElementById("imagePromptDisplay");
  const prompt = promptElem ? (promptElem.value || promptElem.textContent || "").trim() : "";
  const customGuide = document.getElementById("inputArtCustomGuide") ? document.getElementById("inputArtCustomGuide").value.trim() : "";

  // [신규] 참조 사진 및 직접 사용 여부 판별
  const radioDirect = document.getElementById("radioRefDirectPhoto");
  const isDirectUsePhoto = Boolean(radioDirect && radioDirect.checked && currentArtReferenceBase64);

  // [신규: 방법 1] 현재 그림 유지하며 부분 수정 (Image-to-Image) 체크 상태
  const chkUseBase = document.getElementById("chkUseCurrentImageAsBase");
  const useCurrentAsBase = chkUseBase ? chkUseBase.checked : true;

  const overlay = document.getElementById("imgPreviewLoadingOverlay");
  const btnRegen = document.getElementById("btnRegeneratePreviewImage");
  const btnInsert = document.getElementById("btnConfirmInsertImage");

  if (overlay) {
    const spinnerText = overlay.querySelector("span");
    if (spinnerText) {
      if (isDirectUsePhoto) {
        spinnerText.textContent = "소장 사진을 300 DPI 출판용 순백 여백으로 보정 중... (처리 대기 필요)";
      } else if (currentArtReferenceBase64) {
        spinnerText.textContent = "참조 사진의 구도를 비전 분석하여 수채화 그리는 중... (생성 대기 필요)";
      } else if (useCurrentAsBase && customGuide) {
        spinnerText.textContent = `현재 그림의 구도를 유지하며 [${customGuide}] 부분 수정 중... (생성 대기 필요)`;
      } else {
        spinnerText.textContent = "새로운 감성 삽화 그리는 중... (생성 대기 필요)";
      }
    }
    overlay.style.display = "flex";
  }
  if (btnRegen) btnRegen.disabled = true;
  if (btnInsert) btnInsert.disabled = true;

  try {
    const endpoint = isPart2 ? "/api/generate_part2_image" : "/api/generate_image_candidates";
    const bodyPayload = isPart2
      ? {
          episode_no: ep,
          title: title,
          memory_anchor: memory,
          prompt: "",
          custom_guide: customGuide,
          art_style: currentArtStyle,
          reference_image: currentArtReferenceBase64,
          direct_use_photo: isDirectUsePhoto,
          base_image_filename: currentPreviewCandidate.filename,
          use_current_as_base: useCurrentAsBase
        }
      : {
          episode_no: ep,
          title: title,
          memory_anchor: memory,
          prompt: prompt,
          custom_guide: customGuide,
          art_style: currentArtStyle,
          reference_image: currentArtReferenceBase64,
          direct_use_photo: isDirectUsePhoto,
          base_image_filename: currentPreviewCandidate.filename,
          use_current_as_base: useCurrentAsBase
        };

    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(bodyPayload)
    });

    let data;
    try {
      data = await res.json();
    } catch (parseErr) {
      const errText = await res.text().catch(() => "");
      throw new Error(errText || `서버 응답 오류 (상태 코드: ${res.status})`);
    }

    if (!res.ok || !data.success) {
      throw new Error(data.detail || data.error || "재생성 실패");
    }

    currentPreviewCandidate.filename = data.filename;
    currentPreviewCandidate.image_url = data.image_url;

    const imgEl = document.getElementById("imgPreviewConfirm");
    if (imgEl) {
      imgEl.src = data.image_url;
    }

    if (data.used_prompt && promptElem) {
      promptElem.value = data.used_prompt;
    }

    let toastMsg = "🎨 새로운 삽화가 다시 생성되었습니다!";
    if (isDirectUsePhoto) {
      toastMsg = "📷 소장 사진이 300 DPI 순백 여백 규격으로 보정되어 시안에 등록되었습니다!";
    } else if (currentArtReferenceBase64) {
      toastMsg = "🎨 첨부하신 사진의 실제 구도와 피사체를 분석하여 새 수채화 삽화를 그렸습니다!";
    } else if (useCurrentAsBase && customGuide) {
      toastMsg = `🎨 기존 구도를 유지하며 [${customGuide}] 연출이 반영되었습니다!`;
    } else if (customGuide) {
      toastMsg = `🎨 [${customGuide}] 연출이 반영된 새 삽화가 생성되었습니다!`;
    }
    showToast(toastMsg, "success");

  } catch (err) {
    alert("삽화 재생성 실패: " + err.message);
  } finally {
    if (overlay) overlay.style.display = "none";
    if (btnRegen) btnRegen.disabled = false;
    if (btnInsert) btnInsert.disabled = false;
  }
}

// 🎨 삽화 2안 모달 열기
function openImageCandidatesModal(data) {
  currentCandidateData = data;
  const modal = document.getElementById("imageCandidatesModal");
  if (!modal) return;

  const titleEl = document.getElementById("labelCandModalTitle");
  if (titleEl) {
    titleEl.textContent = `[${data.episode_no}] 삽화 시안 선택 (2가지 시안 중 마음에 드는 그림 선택)`;
  }

  const imgA = document.getElementById("candImgA");
  const imgB = document.getElementById("candImgB");
  if (imgA && data.candidate_a) imgA.src = data.candidate_a.image_url;
  if (imgB && data.candidate_b) imgB.src = data.candidate_b.image_url;

  // 선택 버튼 리셋
  const btnA = document.getElementById("btnSelectCandA");
  const btnB = document.getElementById("btnSelectCandB");
  if (btnA) {
    btnA.disabled = false;
    btnA.innerHTML = "<span>✨ [1안] 이 그림으로 최종 반영하기</span>";
  }
  if (btnB) {
    btnB.disabled = false;
    btnB.innerHTML = "<span>✨ [2안] 이 그림으로 최종 반영하기</span>";
  }

  modal.style.display = "flex";
}

// 닫기
function closeImageCandidatesModal() {
  const modal = document.getElementById("imageCandidatesModal");
  if (modal) modal.style.display = "none";
}

// 1안 또는 2안 선택 확정
async function onSelectCandidate(candId) {
  if (!currentCandidateData) return;
  const cand = candId === 'A' ? currentCandidateData.candidate_a : currentCandidateData.candidate_b;
  if (!cand) return;

  const targetBtn = candId === 'A' 
    ? document.getElementById("btnSelectCandA") 
    : document.getElementById("btnSelectCandB");
  const origBtnText = targetBtn ? targetBtn.innerHTML : "";

  if (targetBtn) {
    targetBtn.disabled = true;
    targetBtn.innerHTML = `<span>⏳ [${candId === 'A' ? '1안' : '2안'}] 삽화 확정 반영 중...</span>`;
  }

  try {
    const res = await fetch("/api/select_image_candidate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        episode_no: currentCandidateData.episode_no,
        candidate_filename: cand.filename,
        candidate_name: candId === 'A' ? "1안" : "2안"
      })
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.detail || "선택 반영 실패");
    }

    showToast(`✅ [${candId === 'A' ? '1안' : '2안'}] 그림이 최종 삽화로 성공적으로 채택되었습니다!`, "success");

    // 모달 닫기
    closeImageCandidatesModal();

    // 스튜디오 미리보기 바 갱신
    const previewArea = document.getElementById("studioImagePreviewArea");
    const previewImg = document.getElementById("studioPreviewImg");
    const previewFilename = document.getElementById("studioPreviewFilename");
    if (previewArea && previewImg && previewFilename) {
      previewArea.style.display = "flex";
      previewImg.src = data.image_url;
      previewFilename.textContent = data.filename;
    }

    // 상태 동기화 & 뷰어 갱신
    await loadStatus();
    await loadImagesInspection();
    if (window.dtpEditor && typeof window.dtpEditor.refreshImages === 'function') {
      window.dtpEditor.refreshImages();
    } else if (typeof renderBookSpread === 'function' && typeof currentWorkIndex !== 'undefined') {
      renderBookSpread(currentWorkIndex);
    }

  } catch (err) {
    alert("시안 반영 중 오류가 발생했습니다: " + err.message);
  } finally {
    if (targetBtn) {
      targetBtn.disabled = false;
      targetBtn.innerHTML = origBtnText;
    }
  }
}

// 모달 안에서 새 2안 다시 생성
async function onRegenerateCandidates() {
  closeImageCandidatesModal();
  await onStudioGenerateFreeImage();
}

// 14-5. 뷰어: 파일 선택창 트리거 & 체인지
function triggerViewerFileInput() {
  const input = document.getElementById("viewerFileInput");
  if (input) input.click();
}

function onViewerFileSelected(event) {
  const file = event.target.files && event.target.files[0];
  if (file) {
    uploadViewerImage(file);
  }
}

// 14-6. 뷰어: 현재 보고 있는 페이지에 이미지 업로드 및 실시간 교체
async function uploadViewerImage(file) {
  if (!file.type.startsWith("image/")) {
    alert("이미지 파일만 업로드할 수 있습니다.");
    return;
  }

  if (!currentStatus || !currentStatus.works || currentStatus.works.length === 0) {
    alert("작품이 존재하지 않습니다.");
    return;
  }

  const work = currentStatus.works[currentWorkIndex];
  if (!work) return;

  const loadingOverlay = document.getElementById("viewerLoadingOverlay");
  const loadingText = document.getElementById("viewerLoadingText");
  if (loadingOverlay && loadingText) {
    loadingText.textContent = `[${work.episode_no}] 그림 파일 업로드 및 교체 중...`;
    loadingOverlay.style.display = "flex";
  }

  const activePart = (window.dtpEditor && window.dtpEditor.currentSpreadPart) ? window.dtpEditor.currentSpreadPart : (window.currentSpreadPart || currentSpreadPart || 1);
  const side = window.activeImageTargetSide || "left";
  const frameIdx = window.activeImageTargetFrame || 1;
  const pageIdx = (activePart - 1) * 2 + (side === "left" ? 0 : 1);
  const pageNum = window.activeImageTargetPageNum || (pageIdx + 1);
  const targetSlot = (pageNum >= 3) ? "part2" : "main";

  const formData = new FormData();
  formData.append("file", file);
  formData.append("episode_no", work.episode_no);
  formData.append("target_slot", targetSlot);
  formData.append("page_num", pageNum);
  formData.append("frame_idx", frameIdx);

  try {
    const res = await fetch("/api/upload_image", {
      method: "POST",
      body: formData
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.detail || "업로드 실패");
    }

    currentViewerTargetSlot = null;
    const savedSpreadPart = (pageNum >= 3) ? 2 : activePart;
    await loadStatus();
    await loadImagesInspection();

    if (currentStatus && currentStatus.works && typeof currentWorkIndex !== 'undefined') {
      const curWork = currentStatus.works[currentWorkIndex];
      if (curWork) {
        if (!curWork.layout_config || !Array.isArray(curWork.layout_config.pages)) {
          if (window.dtpEditor) curWork.layout_config = window.dtpEditor.getNormalizedConfig(curWork);
        }
        if (curWork.layout_config && Array.isArray(curWork.layout_config.pages)) {
          while (curWork.layout_config.pages.length <= pageIdx) {
            const pNum = curWork.layout_config.pages.length + 1;
            curWork.layout_config.pages.push({
              page_num: pNum,
              usage: pNum === 1 ? "image" : (pNum === 3 ? "image_text" : "text"),
              role: pNum === 1 ? "none" : (pNum === 2 ? "start" : "continue"),
              image_file: "",
              custom_text: ""
            });
          }
          if (frameIdx === 2) {
            curWork.layout_config.pages[pageIdx].image_file_b = `./images/${data.filename}`;
          } else {
            curWork.layout_config.pages[pageIdx].image_file = `./images/${data.filename}`;
          }
          if (curWork.layout_config.pages[pageIdx].usage === "text") {
            curWork.layout_config.pages[pageIdx].usage = "image_text";
          }
        }
        if (pageNum === 1 && frameIdx === 1) {
          curWork.image_file = `./images/${data.filename}`;
        } else if (pageNum === 3 && frameIdx === 1) {
          curWork.image_file_2 = `./images/${data.filename}`;
          curWork.part2_mode = "image";
          curWork.layout_mode = "multi_page";
        } else if (pageNum >= 3 && !curWork.image_file_2) {
          curWork.image_file_2 = `./images/${data.filename}`;
          curWork.part2_mode = "image";
          curWork.layout_mode = "multi_page";
        }

        if (window.dtpEditor && typeof window.dtpEditor.saveLayoutConfigToServer === 'function') {
          window.dtpEditor.saveLayoutConfigToServer(curWork.episode_no, curWork.layout_config);
        } else if (typeof saveWorkLayoutConfigToServer === 'function') {
          saveWorkLayoutConfigToServer(curWork.episode_no, curWork.layout_config);
        }
      }
    }

    currentSpreadPart = savedSpreadPart;
    window.currentSpreadPart = savedSpreadPart;
    if (window.dtpEditor && typeof window.dtpEditor.refreshImages === 'function') {
      window.dtpEditor.currentSpreadPart = savedSpreadPart;
      window.dtpEditor.refreshImages();
    } else {
      renderBookSpread(currentWorkIndex);
    }

  } catch (err) {
    alert("이미지 등록 실패: " + err.message);
  } finally {
    if (loadingOverlay) loadingOverlay.style.display = "none";
  }
}

// 14-7. 뷰어: 현재 보고 있는 페이지의 2가지 삽화 시안 동시 생성 & 모달 선택
async function onViewerGenerateFreeImage(customPageNum, customFrameIdx) {
  if (!currentStatus || !currentStatus.works || currentStatus.works.length === 0) {
    alert("작품이 존재하지 않습니다.");
    return;
  }

  const work = currentStatus.works[currentWorkIndex];
  if (!work) return;

  const activePart = (window.dtpEditor && window.dtpEditor.currentSpreadPart) ? window.dtpEditor.currentSpreadPart : (window.currentSpreadPart || currentSpreadPart || 1);
  const side = window.activeImageTargetSide || "left";
  const frameIdx = customFrameIdx || window.activeImageTargetFrame || 1;
  const pageIdx = (activePart - 1) * 2 + (side === "left" ? 0 : 1);
  const targetPage = customPageNum || window.activeImageTargetPageNum || (pageIdx + 1);

  const loadingOverlay = document.getElementById("viewerLoadingOverlay");
  const loadingText = document.getElementById("viewerLoadingText");
  if (loadingOverlay && loadingText) {
    loadingText.textContent = `[${work.episode_no}] 「${work.title}」 ${targetPage}면 감성 삽화 생성 중... (생성 대기 필요)`;
    loadingOverlay.style.display = "flex";
  }

  try {
    const res = await fetch("/api/generate_image_candidates", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        episode_no: work.episode_no,
        title: work.title,
        memory_anchor: work.memory_anchor || "",
        prompt: "",
        art_style: currentArtStyle
      })
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.detail || "시안 생성 실패");
    }

    // ★ [기존 3번 캡처창으로 복원]: 단일 시안 검토 및 추가 연출/재생성 지원 모달 열기
    const curSlot = (targetPage >= 3) ? "part2" : "main";
    openImagePreviewConfirmModal({
      episode_no: work.episode_no,
      title: work.title,
      filename: data.filename,
      image_url: data.image_url,
      page_label: `${targetPage}면 ${frameIdx === 2 ? '2번 ' : ''}삽화`,
      page_num: targetPage,
      frame_idx: frameIdx,
      target_slot: curSlot
    });

  } catch (err) {
    alert("삽화 시안 생성 실패: " + err.message);
  } finally {
    if (loadingOverlay) loadingOverlay.style.display = "none";
  }
}


// =========================================================
// 16. 전편 서정 수채화 삽화 일괄 자동 생성 (Batch Image Generation)
// =========================================================

let isBatchGenRunning = false;
let batchCancelRequested = false;

function openBatchGenModal() {
  const modal = document.getElementById("batchGenModal");
  if (modal) modal.style.display = "flex";

  const works = (currentStatus && currentStatus.works) ? currentStatus.works : [];
  const total = works.length;

  document.getElementById("batchProgressBar").style.width = "0%";
  document.getElementById("batchProgressPercentText").textContent = "0%";
  document.getElementById("batchProgressCountText").textContent = `0 / ${total}편 완료`;
  document.getElementById("batchProgressCurrentTitle").textContent = "시작 버튼을 누르면 자동 생성이 시작됩니다.";
  document.getElementById("batchThumbnailGrid").innerHTML = "";

  const startBtn = document.getElementById("btnStartBatchGen");
  startBtn.disabled = false;
  startBtn.innerHTML = `<span>🎨 전편 삽화 일괄 생성 시작 (${total}편)</span>`;
}

function closeBatchGenModal() {
  if (isBatchGenRunning) {
    const confirmStop = confirm("현재 삽화 생성이 진행 중입니다. 정말 중단하시겠습니까?");
    if (!confirmStop) return;
    batchCancelRequested = true;
  }
  const modal = document.getElementById("batchGenModal");
  if (modal) modal.style.display = "none";
}

function onBatchGenOverlayClick(event) {
  if (!isBatchGenRunning) {
    closeBatchGenModal();
  }
}

function cancelBatchGen() {
  if (isBatchGenRunning) {
    batchCancelRequested = true;
    document.getElementById("batchProgressCurrentTitle").textContent = "중단 요청 중... 잠시만 기다려주세요.";
  } else {
    closeBatchGenModal();
  }
}

async function startBatchGen() {
  if (!currentStatus || !currentStatus.works || currentStatus.works.length === 0) {
    alert("등록된 시 작품이 없습니다. 먼저 원고를 등록해주세요.");
    return;
  }

  const works = currentStatus.works;
  const total = works.length;
  const startBtn = document.getElementById("btnStartBatchGen");
  const cancelBtn = document.getElementById("btnCancelBatchGen");
  const progressBar = document.getElementById("batchProgressBar");
  const percentText = document.getElementById("batchProgressPercentText");
  const countText = document.getElementById("batchProgressCountText");
  const currentTitle = document.getElementById("batchProgressCurrentTitle");
  const grid = document.getElementById("batchThumbnailGrid");

  isBatchGenRunning = true;
  batchCancelRequested = false;
  startBtn.disabled = true;
  cancelBtn.textContent = "작업 중단";

  let successCount = 0;

  for (let i = 0; i < total; i++) {
    if (batchCancelRequested) {
      currentTitle.textContent = "사용자에 의해 일괄 생성이 중단되었습니다.";
      break;
    }

    const work = works[i];
    const progressPercent = Math.round((i / total) * 100);

    progressBar.style.width = `${progressPercent}%`;
    percentText.textContent = `${progressPercent}%`;
    countText.textContent = `${i} / ${total}편 완료`;
    currentTitle.textContent = `[${work.episode_no}] 「${work.title}」 수채화 빚어내는 중...`;

    try {
      const res = await fetch("/api/generate_image_free", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          episode_no: work.episode_no,
          title: work.title,
          memory_anchor: work.memory_anchor || "",
          prompt: work.image_prompt || "",
          art_style: currentArtStyle
        })
      });

      const data = await res.json();
      if (res.ok && data.success) {
        successCount++;
        // 썸네일 그리드에 카드 추가
        const card = document.createElement("div");
        card.className = "batch-thumb-card";
        card.innerHTML = `
          <img src="${data.image_url}" alt="${work.title}" class="batch-thumb-img">
          <span class="batch-thumb-title">[${work.episode_no}] ${work.title}</span>
        `;
        grid.prepend(card);
      }
    } catch (err) {
      console.warn(`[${work.episode_no}] 생성 건너뜀:`, err);
    }
  }

  isBatchGenRunning = false;
  startBtn.disabled = false;
  cancelBtn.textContent = "닫기";

  if (!batchCancelRequested) {
    progressBar.style.width = "100%";
    percentText.textContent = "100%";
    countText.textContent = `${total} / ${total}편 완료`;
    currentTitle.textContent = `🎉 전편(${successCount}편)의 수채화 삽화가 모두 완성되었습니다!`;
  }

  // 상태 리로드 및 뷰어 갱신
  await loadStatus();
  renderBookSpread(currentWorkIndex);
}

// =========================================================
// 17. 300 DPI 출판 규격 전체 일괄 자동 보정 실행
// =========================================================
async function onEnhanceAllImages300Dpi() {
  const btn = document.getElementById("btnEnhance300Dpi");
  const origText = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = `<span>⏳ 300 DPI 보정 중...</span>`;

  try {
    const res = await fetch("/api/images/enhance_300dpi", { method: "POST" });
    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.detail || "보정 실패");
    }

    alert(`🎉 ${data.message}`);
    await loadImagesInspection();
    await loadStatus();
  } catch (err) {
    alert("300 DPI 보정 오류: " + err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = origText;
  }
}


// =========================================================
// 19-2. Colab SDXL 맞춤형 삽화 노트북 동적 다운로드 및 [3단계] 코드 복사
// =========================================================
let colabImageTargetEpisode = null;
let colabImageTargetTitle = null;

function onOpenGoogleFlowLink(e) {
  const promptElem = document.getElementById("imagePromptDisplay");
  let promptStr = promptElem ? (promptElem.value || promptElem.textContent || "").trim() : "";
  if (!promptStr) {
    const title = document.getElementById("inputFinalTitle")?.value?.trim() || "무제";
    promptStr = `Korean lyric watercolor illustration, ${title}, soft warm lighting, poetic negative space, delicate ink wash, 300 dpi, masterpiece`;
  }

  // 프롬프트 클립보드 자동 복사
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(promptStr);
  }

  // 차단 없는 토스트 안내
  showToast("📋 현재 시의 300 DPI 프롬프트가 복사되었습니다! 새 창 Flow 입력창에 [Ctrl+V] 하세요.", "success");
}


function openColabImageGuide() {
  colabImageTargetEpisode = null;
  colabImageTargetTitle = null;
  const modal = document.getElementById("colabImageModal");
  if (modal) modal.style.display = "flex";
}


function closeColabImageModal() {
  const modal = document.getElementById("colabImageModal");
  if (modal) modal.style.display = "none";
}

async function downloadModularImageNotebook() {
  let ep = colabImageTargetEpisode || document.getElementById("inputEpisode")?.value || "제01화";
  let title = colabImageTargetTitle || document.getElementById("inputFinalTitle")?.value?.trim() || "무제";
  
  // 프롬프트 취득
  let promptStr = "";
  const promptElem = document.getElementById("imagePromptDisplay");
  if (promptElem) {
    promptStr = (promptElem.value || promptElem.textContent || "").trim();
  }
  if (!promptStr) {
    const memory = document.getElementById("inputCoreMemory")?.value || "";
    promptStr = memory ? `${title}, ${memory}` : `${title}의 정경`;
  }

  const artStyle = typeof currentArtStyle !== "undefined" ? currentArtStyle : "watercolor";

  try {
    const res = await fetch("/api/export_colab_image_notebook", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        episode_no: ep,
        title: title,
        prompt: promptStr,
        art_style: artStyle,
        width: 768,
        height: 1024
      })
    });
    const data = await res.json();
    if (data.success && data.notebook) {
      const blob = new Blob([JSON.stringify(data.notebook, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = data.filename || "삽화_Colab_원클릭.ipynb";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      alert(`🎉 [${ep}] 「${title}」 맞춤형 Colab 삽화 노트북이 다운로드되었습니다!\n\n파일명: ${data.filename}\n\nGoogle Colab에서 업로드하여 [런타임 모두 실행]을 누르시면 T4 GPU에서 고화질 삽화가 생성(생성 대기 필요)됩니다.`);
    } else {
      alert("노트북 생성 실패: " + (data.error || "오류"));
    }
  } catch (err) {
    alert("노트북 다운로드 중 오류 발생: " + err);
  }
}

function copyStep3ImageCode() {
  let ep = colabImageTargetEpisode || document.getElementById("inputEpisode")?.value || "제01화";
  let title = colabImageTargetTitle || document.getElementById("inputFinalTitle")?.value?.trim() || "무제";
  const cleanEp = ep.replace(/[^0-9]/g, '').padStart(2, '0') || "01";
  const cleanTitle = title.replace(/[\s\\/*?:"<>|]/g, '_') || "삽화";
  const fileA = `${cleanEp}_${cleanTitle}_시안A.jpg`;
  const fileB = `${cleanEp}_${cleanTitle}_시안B.jpg`;

  let promptStr = "";
  const promptElem = document.getElementById("imagePromptDisplay");
  if (promptElem) {
    promptStr = (promptElem.value || promptElem.textContent || "").trim();
  }
  if (!promptStr) {
    promptStr = `${title}의 정경`;
  }

  const step3Code = `# @title [3단계] 삽화 메타데이터 및 프롬프트 설정 (동적 조립 모듈)
EPISODE_NO = "${ep}"
WORK_TITLE = "${title}"
FILE_A = "${fileA}"
FILE_B = "${fileB}"
IMAGE_WIDTH = 768
IMAGE_HEIGHT = 1024
STEPS = 4

PROMPT_A = """${promptStr}, tranquil poetic negative space, minimalist composition, korean lyric watercolor painting, delicate brush strokes, soft watercolor wash, poetic negative space, gentle morning light, nostalgic mood, masterpiece, highly detailed, 300 dpi illustration"""
PROMPT_B = """${promptStr}, warm nostalgic ambiance, intimate poetic harmony, rich atmospheric details, korean lyric watercolor painting, delicate brush strokes, soft watercolor wash, poetic negative space, gentle morning light, nostalgic mood, masterpiece, highly detailed, 300 dpi illustration"""
NEGATIVE_PROMPT = """ugly, deformed, disfigured, poor anatomy, bad hands, blurry, low quality, oversaturated, text, watermark, signature, modern electronics, photo frame"""

print(f"✅ 3단계: [{EPISODE_NO}] {WORK_TITLE} 삽화 프롬프트 준비 완료!")`;

  navigator.clipboard.writeText(step3Code).then(() => {
    alert("📋 [3단계 파이썬 코드]가 클립보드에 복사되었습니다!\n\nColab 삽화 노트북의 [3단계] 셀에 그대로 [Ctrl+V] 붙여넣기 하시면 됩니다.");
  });
}

