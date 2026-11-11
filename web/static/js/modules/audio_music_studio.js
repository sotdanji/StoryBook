// ============================================================================
// [Module] audio_music_studio.js - 서정 노래/음원 제작, 오디오 트리밍, 음성 인터뷰(STT), AI 시낭송(TTS), 육성 녹음실
// ============================================================================
// =========================================================
// 18. 서정 노래 / 음원 제작 (선택 옵션) 로직
// =========================================================
let currentAudioFile = "";
let currentReciteFile = "";
let currentMusicFile = "";
let currentLyrics = "";
let currentMusicGenre = "minyo";
let currentMusicData = null;


function onMusicGenreChange() {
  const selected = document.querySelector('input[name="musicGenre"]:checked');
  if (selected) {
    currentMusicGenre = selected.value;
  }

  const genreNames = {
    recite: "서정 시 낭송 (Spoken Word)",
    minyo: "서정 민요조",
    folk: "어쿠스틱 포크",
    gagok: "서정 예술 가곡",
    dongyo: "서정 동요/동심"
  };
  const gName = genreNames[currentMusicGenre] || "서정 음악";

  const poem = document.getElementById("inputFinalPoem")?.value?.trim();
  const lyricsInput = document.getElementById("musicLyricsInput");

  // 🎙️ 시 낭송 선택 시: 시 본문 원문을 가사창에 그대로 채워넣고 낭송 스타일 준비
  if (currentMusicGenre === "recite") {
    if (poem && lyricsInput) {
      lyricsInput.value = poem;
      if (typeof updateStudioLyricsDisplay === 'function') updateStudioLyricsDisplay();
      lyricsInput.style.backgroundColor = "#FFF9F0";
      setTimeout(() => { lyricsInput.style.backgroundColor = "#FFFFFF"; }, 400);
    }
    showToast(`🎙️ <b>[시 낭송]</b> 모드로 전환되었습니다.<br>시 본문이 입력창에 자동 배치되었으며, <b>Suno/Udio</b>에 붙여넣을 <b>Spoken Word 낭송 스타일 프롬프트</b>가 준비되었습니다.`, "success", 4500);
    return;
  }

  // 이미 노랫말 또는 시 본문이 있다면 새 장르 스킬 블록으로 자동 재편곡
  if (poem || (lyricsInput && lyricsInput.value.trim())) {
    showToast(`🎵 [${gName}] 장르 스킬 블록으로 전환합니다. 이전 추임새를 정리하고 재편곡합니다.`, "info");
    onGenerateLyrics(true);
  }
}


async function onGenerateLyrics(showAlert = true) {
  const title = document.getElementById("inputFinalTitle").value.trim() || "무제";
  const poem = document.getElementById("inputFinalPoem").value.trim();
  const existingLyrics = document.getElementById("musicLyricsInput")?.value?.trim() || "";
  const sourceText = poem || existingLyrics;

  if (!sourceText) {
    if (showAlert) {
      alert("먼저 시 본문을 작성하거나 다듬어주세요.");
      document.getElementById("inputFinalPoem").focus();
    }
    return;
  }

  const btn = document.getElementById("btnGenerateLyrics");
  const origText = btn ? btn.innerHTML : "";
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = "<span>⏳ 모듈러 스킬 블록으로 노랫말 운율화 중... (생성 대기 필요)</span>";
  }

  try {
    const res = await fetch("/api/generate_lyrics", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: title,
        poem_body: sourceText,
        genre: currentMusicGenre
      })
    });
    const resData = await res.json();
    const payload = resData.data || (resData.lyrics ? resData : null);
    if (resData.success && payload) {
      currentMusicData = payload;
      currentLyrics = payload.lyrics || resData.lyrics;
      const lyricsInput = document.getElementById("musicLyricsInput");
      if (lyricsInput) {
        lyricsInput.value = currentLyrics;
        lyricsInput.style.backgroundColor = "#FFF9F0";
        setTimeout(() => { lyricsInput.style.backgroundColor = "#FFFFFF"; }, 400);
      }

      // 🎼 노랫말 정서 & 맞춤 악기 변주 배지 업데이트
      const moodTheme = payload.mood_theme || resData.mood_theme || "";
      const inst = payload.instruments || resData.instruments || "";
      const varBadge = document.getElementById("badgeMusicVariation");
      if (varBadge && moodTheme) {
        const leadInst = inst ? inst.split(',')[0].trim() : "";
        varBadge.textContent = `🎼 ${moodTheme}` + (leadInst ? ` (${leadInst} 등)` : "");
        varBadge.style.display = "inline-block";
        varBadge.title = `[노랫말 맞춤 악기 편성]\n${inst}\n템포: ${payload.bpm || resData.bpm || '72 BPM'}`;
      }

      if (showAlert) {
        const genreName = payload.genre_name || resData.genre_name || "서정 음악";
        setTimeout(() => {
          let extraMsg = "";
          if (moodTheme || inst) {
            extraMsg = `\n[노랫말 맞춤 악기 & 정서 변주]\n• 감성 테마: ${moodTheme || '서정'}\n• 추천 악기: ${inst || '어쿠스틱 편성'}\n`;
          }
          alert(
            `🎵 [${genreName}] 노랫말과 맞춤 악기 편곡이 완료되었습니다!${extraMsg}\n` +
            `노랫말을 확인하신 후, 아래의 [🎵 1. Suno AI] / [🎼 2. Udio AI] / [🚀 3. YuE2 AI] 중 원하시는 도구를 선택하여 세상에 하나뿐인 노래를 만들어 보세요.`
          );
        }, 150);
      }
    } else {
      if (showAlert) alert("노랫말 생성 실패: " + (resData.error || "알 수 없는 오류"));
    }
  } catch (err) {
    if (showAlert) alert("노랫말 생성 중 오류가 발생했습니다: " + err);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = origText;
    }
  }
}

async function copyLyricsText() {
  const lyricsInput = document.getElementById("musicLyricsInput");
  const text = lyricsInput ? lyricsInput.value.trim() : "";
  if (!text) {
    alert("복사할 노랫말이 없습니다. 먼저 '노랫말 운율화하기'를 실행해주세요.");
    return;
  }
  const success = await safeCopyToClipboard(text);
  if (success) {
    showToast("📜 노래 가사(Verse/Chorus)가 클립보드에 복사되었습니다!", "success");
  } else {
    alert("클립보드 복사에 실패했습니다.");
  }
}

// 3대 음악 AI 탭 선택 상태 갱신 헬퍼
function updateMusicTabSelection(selected) {
  const b1 = document.getElementById("btnSelectSunoAI");
  const b2 = document.getElementById("btnSelectUdioAI");
  const b3 = document.getElementById("btnSelectYue2AI");

  [b1, b2, b3].forEach(b => {
    if (!b) return;
    b.classList.remove("active-music-btn");
    b.style.background = "#ffffff";
    b.style.color = "#643e19";
    b.style.borderColor = "#c9a98b";
    b.style.fontWeight = "normal";
  });

  let targetBtn = null;
  if (selected === "suno") targetBtn = b1;
  else if (selected === "udio") targetBtn = b2;
  else if (selected === "yue2") targetBtn = b3;

  if (targetBtn) {
    targetBtn.classList.add("active-music-btn");
    targetBtn.style.background = "#643e19";
    targetBtn.style.color = "#ffffff";
    targetBtn.style.borderColor = "#643e19";
    targetBtn.style.fontWeight = "bold";
  }
}

// 1번 탭: Suno AI 작곡 가이드
function openSunoAIGuide() {
  updateMusicTabSelection("suno");
  const modal = document.getElementById("sunoMusicModal");
  if (modal) modal.style.display = "flex";
}

function closeSunoMusicModal() {
  const modal = document.getElementById("sunoMusicModal");
  if (modal) modal.style.display = "none";
}

// 2번 탭: Udio AI 서정 예술 작곡 가이드
function openUdioAIGuide() {
  updateMusicTabSelection("udio");
  const modal = document.getElementById("udioMusicModal");
  if (modal) modal.style.display = "flex";
}

function closeUdioMusicModal() {
  const modal = document.getElementById("udioMusicModal");
  if (modal) modal.style.display = "none";
}

// 3번 탭: YuE2 고성능 웹 스튜디오 가이드
function openYue2AIGuide() {
  updateMusicTabSelection("yue2");
  const modal = document.getElementById("colabYuE2Modal");
  if (modal) modal.style.display = "flex";
}

function closeColabYuE2Modal() {
  const modal = document.getElementById("colabYuE2Modal");
  if (modal) modal.style.display = "none";
}


function getMusicGenrePrompt(genre) {
  const g = genre || currentMusicGenre || "minyo";
  if (currentMusicData && currentMusicData.music_prompt && currentMusicData.genre === g) {
    return currentMusicData.music_prompt;
  }
  const promptMap = {
    recite: "Spoken word, Korean calm lyrical poetry recitation, warm deep narrator voice, gentle soft ambient piano and cello background, poetic recitation, nostalgic, emotional, cinematic, clean audio, no singing",
    minyo: "Korean traditional lyrical folk song, acoustic gayageum and bamboo daegeum flute, subtle haegum, emotional warm vocal, sorrowful yet uplifting Korean minyo style, traditional janggu percussion, warm acoustic sound, 75 bpm",
    folk: "Korean warm acoustic folk song, delicate nylon acoustic guitar fingerpicking, soft upright piano, intimate emotional vocals, warm 1970s 1980s nostalgic storytelling, peaceful lyrical atmosphere, 78 bpm, warm analog sound",
    gagok: "Korean classical art song, elegant gagok style, expressive concert grand piano, warm cello counter-melody, graceful lyrical classical vocal, poetic and dramatic resonance, majestic and tender emotion, 72 bpm",
    dongyo: "Korean lyrical children song, nostalgic dongyo, pure innocent vocal, bright glockenspiel bells, gentle acoustic piano, soft acoustic guitar, warm heartwarming childhood melody, peaceful and tender, 82 bpm",
    ballad: "Korean emotional acoustic ballad, delicate piano melody, tender string quartet, heartfelt warm vocal, nostalgic and cinematic soundscape, 70 bpm"
  };
  return promptMap[g] || promptMap.minyo;
}

async function copyFullMusicPrompt(silent = false) {
  const lyricsInput = document.getElementById("musicLyricsInput");
  const lyrics = lyricsInput ? lyricsInput.value.trim() : "";
  const title = document.getElementById("inputFinalTitle").value.trim() || "무제";

  const genrePrompt = getMusicGenrePrompt(currentMusicGenre);
  const fullPrompt = `[Title]\n${title}\n\n[Style / Tags]\n${genrePrompt}\n\n[Lyrics]\n${lyrics || "(시 본문을 노랫말로 운율화해주세요)"}`;

  const success = await safeCopyToClipboard(fullPrompt);
  if (success) {
    if (!silent) {
      showToast("✨ <b>[전체 내용(제목·스타일·가사)]</b>이 복사되었습니다!<br>음악 사이트의 <b>Lyrics(가사)</b> 칸에 <b>Ctrl + V</b>로 통째로 붙여넣으시면 AI가 알아서 작곡합니다.", "success");
    }
  } else {
    if (!silent) alert("클립보드 복사에 실패했습니다.");
  }
  return success;
}

// [시니어/초보자 배려 1] 노래 가사만 따로 복사
async function copyLyricsOnly(btn) {
  const lyricsInput = document.getElementById("musicLyricsInput");
  const lyrics = lyricsInput ? lyricsInput.value.trim() : "";
  if (!lyrics) {
    showToast("⚠️ 먼저 [노랫말 운율화하기]를 실행하여 가사를 생성해주세요.", "error");
    return;
  }
  const success = await safeCopyToClipboard(lyrics);
  if (success) {
    const firstLine = lyrics.split("\n").filter(l => l.trim()).slice(0, 2).join(" / ");
    showToast(`📋 <b>[2. 노래 가사]</b> 복사 완료!<br><span style="font-size:0.78rem;color:#f3d9b8;">"${firstLine.substring(0, 45)}..."</span><br>음악 사이트의 <b>Lyrics(가사)</b> 칸에 <b>Ctrl + V</b>로 붙여넣으세요.`, "success");
    if (btn) {
      const orig = btn.innerHTML;
      btn.innerHTML = "<span>✓ 가사 복사 완료!</span>";
      btn.style.borderColor = "#3a7352";
      btn.style.color = "#3a7352";
      setTimeout(() => {
        btn.innerHTML = orig;
        btn.style.borderColor = "";
        btn.style.color = "";
      }, 1800);
    }
  }
}

// [시니어/초보자 배려 2] 음악 스타일(장르) 태그만 따로 복사
async function copyStyleOnly(btn) {
  const genrePrompt = getMusicGenrePrompt(currentMusicGenre);
  const success = await safeCopyToClipboard(genrePrompt);
  if (success) {
    const preview = genrePrompt.length > 50 ? genrePrompt.substring(0, 50) + "..." : genrePrompt;
    showToast(`🎵 <b>[1. 음악 스타일 태그]</b> 복사 완료!<br><span style="font-size:0.78rem;color:#f3d9b8;">"${preview}"</span><br>음악 사이트의 <b>Song description (또는 Style)</b> 칸에 <b>Ctrl + V</b>로 붙여넣으세요.`, "success");
    if (btn) {
      const orig = btn.innerHTML;
      btn.innerHTML = "<span>✓ 스타일 태그 복사 완료!</span>";
      btn.style.borderColor = "#3a7352";
      btn.style.color = "#3a7352";
      setTimeout(() => {
        btn.innerHTML = orig;
        btn.style.borderColor = "";
        btn.style.color = "";
      }, 1800);
    }
  }
}

// [시니어/초보자 배려 3] 곡 제목만 따로 복사
async function copyTitleOnly(btn) {
  const title = document.getElementById("inputFinalTitle").value.trim() || "서정시 노래";
  const success = await safeCopyToClipboard(title);
  if (success) {
    showToast(`📝 곡 제목(<b>「${title}」</b>)이 복사되었습니다!<br>음악 사이트의 <b>Title(제목)</b> 칸에 <b>Ctrl + V</b>로 붙여넣으세요.`, "success");
    if (btn) {
      const orig = btn.innerHTML;
      btn.innerHTML = "<span>✓ 제목 복사 완료!</span>";
      btn.style.borderColor = "#3a7352";
      btn.style.color = "#3a7352";
      setTimeout(() => {
        btn.innerHTML = orig;
        btn.style.borderColor = "";
        btn.style.color = "";
      }, 1800);
    }
  }
}


// 1번 탭: Suno AI 음악 플랫폼 단일 윈도우 인스턴스 (중복 생성 방지)
let sunoMusicPlatformWindow = null;

async function openSunoPlatform() {
  const url = "https://suno.com";
  const windowName = "SunoAIMusicPlatformWindow";

  // 1. 이미 열린 Suno 창이 존재하고 닫히지 않은 경우: 해당 창으로 포커스 이동 (새 탭 중복 생성 방지)
  if (sunoMusicPlatformWindow && !sunoMusicPlatformWindow.closed) {
    try {
      sunoMusicPlatformWindow.focus();
      showToast("🚀 이미 열려 있는 Suno 창으로 이동했습니다!<br><b>Ctrl + V</b>로 가사를 붙여넣으세요.", "info");
      return;
    } catch (e) {
      // 크로스 도메인 보안 예외 방어
    }
  }

  // 2. 창이 없거나 닫힌 경우: 고유 윈도우 이름으로 열기 (브라우저 수준 중복 방지)
  sunoMusicPlatformWindow = window.open(url, windowName);
  if (sunoMusicPlatformWindow) {
    sunoMusicPlatformWindow.focus();
    showToast("🚀 Suno AI 사이트가 새 창으로 열렸습니다!<br>화면 좌측 <b>Create</b> ➜ <b>Custom</b> 켠 후 <b>Ctrl + V</b>로 붙여넣으세요.", "success");
  }
}

// 2번 탭: Udio AI 음악 플랫폼 단일 윈도우 인스턴스 (중복 생성 방지)
let udioMusicPlatformWindow = null;

async function openUdioPlatform() {
  const url = "https://www.udio.com";
  const windowName = "UdioAIMusicPlatformWindow";

  // 1. 이미 열린 Udio 창이 존재하고 닫히지 않은 경우: 해당 창으로 포커스 이동 (새 탭 중복 생성 방지)
  if (udioMusicPlatformWindow && !udioMusicPlatformWindow.closed) {
    try {
      udioMusicPlatformWindow.focus();
      showToast("🚀 이미 열려 있는 Udio 창으로 이동했습니다!<br><b>[Custom]</b> 켠 후 스타일과 가사를 붙여넣으세요.", "info");
      return;
    } catch (e) {
      // 크로스 도메인 보안 예외 방어
    }
  }

  // 2. 창이 없거나 닫힌 경우: 고유 윈도우 이름으로 열기 (브라우저 수준 중복 방지)
  udioMusicPlatformWindow = window.open(url, windowName);
  if (udioMusicPlatformWindow) {
    udioMusicPlatformWindow.focus();
    showToast("🚀 Udio AI 사이트가 새 창으로 열렸습니다!<br>상단 <b>[Custom]</b>을 켠 뒤 스타일과 가사를 붙여넣으세요.", "success");
  }
}

// 3번 탭: YuE2 공식 웹 스튜디오 단일 윈도우 인스턴스 (중복 생성 방지)
let yue2MusicPlatformWindow = null;

async function openYue2Platform() {
  const url = "https://yue.noizai.net/";
  const windowName = "Yue2AIMusicPlatformWindow";

  // 1. 이미 열린 YuE2 창이 존재하고 닫히지 않은 경우: 해당 창으로 포커스 이동 (새 탭 중복 생성 방지)
  if (yue2MusicPlatformWindow && !yue2MusicPlatformWindow.closed) {
    try {
      yue2MusicPlatformWindow.focus();
      showToast("🚀 이미 열려 있는 YuE2 스튜디오 창으로 이동했습니다!<br><b>Ctrl + V</b>로 가사와 스타일을 붙여넣으세요.", "info");
      return;
    } catch (e) {
      // 크로스 도메인 보안 예외 방어
    }
  }

  // 2. 창이 없거나 닫힌 경우: 고유 윈도우 이름으로 열기 (브라우저 수준 중복 방지)
  yue2MusicPlatformWindow = window.open(url, windowName);
  if (yue2MusicPlatformWindow) {
    yue2MusicPlatformWindow.focus();
    showToast("🚀 YuE2 공식 스튜디오가 새 창으로 열렸습니다!<br><b>Ctrl + V</b>로 가사와 스타일을 붙여넣으세요.", "success");
  }
}


function triggerStudioAudioFileInput() {
  const input = document.getElementById("studioAudioFileInput");
  if (input) input.click();
}

function onStudioAudioFileSelected(event) {
  const file = event.target.files && event.target.files[0];
  if (file) {
    uploadStudioAudio(file);
  }
}

async function uploadStudioAudio(file) {
  const ep = document.getElementById("inputEpisode").value || "제01화";
  const statusBox = document.getElementById("studioAudioUploadStatus");
  if (statusBox) {
    statusBox.className = "upload-status-text loading";
    statusBox.style.display = "block";
    statusBox.innerHTML = `<span>⏳ [${ep}] 노래 음원 분석 및 앞뒤 무음 자동 다듬기 진행 중...</span>`;
  }

  const formData = new FormData();
  formData.append("audio_file", file);
  formData.append("episode_no", ep);

  // 📜 현재 입력된 노랫말(Suno 가사)도 함께 원고에 자동 저장
  const lyricsInput = document.getElementById("musicLyricsInput");
  if (lyricsInput && lyricsInput.value.trim()) {
    formData.append("lyrics", lyricsInput.value.trim());
  }

  try {
    const res = await fetch("/api/upload_audio", {
      method: "POST",
      body: formData
    });
    const data = await res.json();
    if (data.success) {
      currentMusicFile = data.music_file || data.audio_file;
      currentAudioFile = currentMusicFile;
      if (statusBox) {
        statusBox.className = "upload-status-text success";
        let msg = `<span>✨ [안실장 최적화] `;
        if (data.trimmed && data.trimmed_seconds > 0) {
          msg += `앞뒤 무음 <strong>${data.trimmed_seconds}초</strong>를 깔끔하게 잘라내고 고음질(320k) MP3로 등록 완료! (${data.orig_duration} ➔ ${data.final_duration})`;
        } else {
          msg += `${data.trim_message || '표준 고음질(320k) MP3로 안전하게 등록되었습니다.'}`;
        }
        msg += `<br><small style="color: #643e19;">💡 노래와 실제 가사가 다를 경우 위의 [📜 완성된 노래 가사] 칸에 Suno 가사를 붙여넣고 [원고 저장]을 누르시면 갤러리에도 즉시 일치됩니다.</small></span>`;
        statusBox.innerHTML = msg;
      }
      // 미리듣기 오디오 플레이어 노출
      const previewArea = document.getElementById("studioAudioPreviewArea");
      const player = document.getElementById("studioAudioPlayer");
      const nameElem = document.getElementById("studioPreviewAudioFilename");
      if (nameElem) {
        let tag = data.filename;
        if (data.trimmed && data.trimmed_seconds > 0) {
          tag += ` (무음 ${data.trimmed_seconds}초 자동 정리)`;
        }
        nameElem.textContent = tag;
      }
      if (player) {
        player.src = data.web_url;
        player.load();
      }
      const dlSongBtn = document.getElementById("btnDownloadStudioSongAudio");
      if (dlSongBtn) {
        dlSongBtn.href = data.web_url;
        dlSongBtn.download = data.filename || "01_노래음원.mp3";
      }
      if (previewArea) previewArea.style.display = "block";

      const toastMsg = data.trimmed
        ? `✨ [안실장] 앞뒤 무음 ${data.trimmed_seconds}초를 깔끔하게 다듬어 고음질 MP3로 등록했습니다!`
        : `✓ [${ep}] 노래 음원이 고음질 MP3로 성공적으로 등록되었습니다!`;
      if (typeof showToast === 'function') showToast(toastMsg, "success");
      if (typeof loadStatus === 'function') await loadStatus();
    } else {
      if (statusBox) {
        statusBox.className = "upload-status-text error";
        statusBox.innerHTML = `<span>❌ 업로드 실패: ${data.error || '오류'}</span>`;
      }
      alert(`음원 등록 실패: ${data.error || '알 수 없는 오류'}`);
    }
  } catch (err) {
    if (statusBox) {
      statusBox.className = "upload-status-text error";
      statusBox.innerHTML = `<span>❌ 네트워크 오류: ${err}</span>`;
    }
    alert(`음원 업로드 중 네트워크 오류가 발생했습니다: ${err}`);
  }
}

function removeAudioFile() {
  currentMusicFile = "";
  currentAudioFile = currentReciteFile || "";
  const previewArea = document.getElementById("studioAudioPreviewArea");
  if (previewArea) previewArea.style.display = "none";
  const player = document.getElementById("studioAudioPlayer");
  if (player) {
    player.pause();
    player.src = "";
  }
  const statusBox = document.getElementById("studioAudioUploadStatus");
  if (statusBox) statusBox.style.display = "none";
  const trimBox = document.getElementById("audioTrimBox");
  if (trimBox) trimBox.style.display = "none";
}


// -------------------------------------------------------------
// 🎶 노래 재생 시 실제 가사 감상 및 태그 정제 (Suno 완벽 연동)
// -------------------------------------------------------------
function cleanStudioMusicLyricsTags() {
  const lyricsInput = document.getElementById("musicLyricsInput");
  if (!lyricsInput) return;
  const originalText = lyricsInput.value;
  if (!originalText.trim()) {
    alert("정제할 노랫말(가사)이 없습니다. 먼저 가사를 입력하거나 Suno에서 복사해 붙여넣어 주세요.");
    return;
  }

  const lines = originalText.split(/\r?\n/);
  const cleanedLines = [];
  let removedCount = 0;

  const bracketLineRegex = /^\s*\[.*?\]\s*$/;
  const parenthesizedMusicRegex = /^\s*\((?:intro|verse|chorus|outro|bridge|hook|solo|guitar|piano|instrumental|간주|후렴|전주|후주)[^)]*\)\s*$/i;

  for (let line of lines) {
    if (bracketLineRegex.test(line) || parenthesizedMusicRegex.test(line)) {
      removedCount++;
      continue;
    }

    let cleaned = line.replace(/\[.*?\]/g, '');
    cleaned = cleaned.replace(/\((?:intro|verse|chorus|outro|bridge|hook|solo|guitar|piano|instrumental|간주|후렴|전주|후주)[^)]*\)/gi, '');
    cleaned = cleaned.trim();

    if (cleaned) {
      cleanedLines.push(cleaned);
    } else if (cleanedLines.length > 0 && cleanedLines[cleanedLines.length - 1] !== '') {
      cleanedLines.push('');
    }
  }

  while (cleanedLines.length > 0 && cleanedLines[cleanedLines.length - 1] === '') {
    cleanedLines.pop();
  }

  const resultText = cleanedLines.join('\n');
  lyricsInput.value = resultText;
  updateStudioLyricsDisplay();

  if (removedCount > 0) {
    showToast(`🧹 [Intro], [Chorus] 등 가사 외 설명어 ${removedCount}개를 깔끔하게 삭제했습니다!`, "success");
  } else {
    showToast("가사에 설명 태그가 없거나 이미 깔끔하게 정제된 상태입니다.", "info");
  }
}

function updateStudioLyricsDisplay() {
  const lyricsInput = document.getElementById("musicLyricsInput");
  const displayEl = document.getElementById("studioLyricsDisplayText");
  if (!displayEl) return;

  const text = lyricsInput ? lyricsInput.value.trim() : "";
  if (text) {
    displayEl.textContent = text;
    displayEl.style.color = "#1E293B";
    displayEl.style.fontStyle = "normal";
  } else {
    displayEl.textContent = "등록된 노래 가사가 없습니다. 위의 [완성된 노래 가사] 칸에 Suno 가사를 입력해 주세요.";
    displayEl.style.color = "#94A3B8";
    displayEl.style.fontStyle = "italic";
  }
}

function toggleStudioLyricsPanel() {
  const panel = document.getElementById("studioLyricsViewPanel");
  const btn = document.getElementById("btnToggleStudioLyricsView");
  if (!panel) return;

  const isHidden = (panel.style.display === "none");
  if (isHidden) {
    updateStudioLyricsDisplay();
    panel.style.display = "block";
    if (btn) {
      btn.innerHTML = "✕ 가사 닫기";
      btn.style.background = "#FED7AA";
      btn.style.color = "#9A3412";
      btn.style.borderColor = "#FDBA74";
    }
  } else {
    panel.style.display = "none";
    if (btn) {
      btn.innerHTML = "📜 노래 가사 보기";
      btn.style.background = "#EBF3FA";
      btn.style.color = "#1E466E";
      btn.style.borderColor = "#7FAAD0";
    }
  }
}

function toggleAudioTrimBox() {
  const box = document.getElementById("audioTrimBox");
  if (!box) return;
  const isHidden = box.style.display === "none";
  box.style.display = isHidden ? "block" : "none";
  if (isHidden) {
    const player = document.getElementById("studioAudioPlayer");
    const endInput = document.getElementById("inputTrimEnd");
    if (player && player.duration && endInput && !endInput.value) {
      endInput.value = formatAudioSeconds(player.duration);
    }
  }
}

function formatAudioSeconds(sec) {
  if (isNaN(sec) || sec < 0) return "00:00";
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

function setTrimStartFromCurrent() {
  const player = document.getElementById("studioAudioPlayer");
  const input = document.getElementById("inputTrimStart");
  if (player && input) {
    input.value = formatAudioSeconds(player.currentTime);
    if (typeof showToast === 'function') showToast(`시작 시간 설정: ${input.value}`, "info");
  }
}

function setTrimEndFromCurrent() {
  const player = document.getElementById("studioAudioPlayer");
  const input = document.getElementById("inputTrimEnd");
  if (player && input) {
    input.value = formatAudioSeconds(player.currentTime);
    if (typeof showToast === 'function') showToast(`끝 시간 설정: ${input.value} (다음 곡 직전 위치)`, "info");
  }
}

async function onApplyAudioTrim() {
  const ep = document.getElementById("inputEpisode")?.value || "제01화";
  const startVal = document.getElementById("inputTrimStart")?.value.trim() || "00:00";
  const endVal = document.getElementById("inputTrimEnd")?.value.trim() || "";

  if (!endVal) {
    alert("끝 시간을 입력하거나, 노래를 들으시다가 다음 곡이 나오기 직전에 [끝: 현재위치] 버튼을 눌러주세요.");
    return;
  }

  const btn = document.getElementById("btnApplyTrim");
  const origBtnText = btn ? btn.innerHTML : "✂️ 자르기 적용";
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = "⏳ 자르는 중...";
  }

  try {
    const res = await fetch("/api/trim_audio", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        episode_no: ep,
        start_time: startVal,
        end_time: endVal
      })
    });
    const data = await res.json();
    if (data.success) {
      const player = document.getElementById("studioAudioPlayer");
      if (player) {
        player.pause();
        player.src = `${data.web_url}&cachebust=${Date.now()}`;
        player.load();
      }
      const dlSongBtn = document.getElementById("btnDownloadStudioSongAudio");
      if (dlSongBtn) {
        dlSongBtn.href = `${data.web_url}&cachebust=${Date.now()}`;
        dlSongBtn.download = data.filename || "01_노래음원.mp3";
      }
      const nameElem = document.getElementById("studioPreviewAudioFilename");
      if (nameElem) {
        nameElem.textContent = `${data.filename} (${data.new_duration_str})`;
      }
      const statusBox = document.getElementById("studioAudioUploadStatus");
      if (statusBox) {
        statusBox.className = "upload-status-text success";
        statusBox.style.display = "block";
        statusBox.innerHTML = `<span>✨ [안실장 미세 다듬기] ${data.message}</span>`;
      }
      if (typeof showToast === 'function') {
        showToast(`✨ [${ep}] ${data.message}`, "success");
      }
      const box = document.getElementById("audioTrimBox");
      if (box) box.style.display = "none";
      if (typeof loadStatus === 'function') await loadStatus();
    } else {
      alert(`자르기 실패: ${data.error || '오류가 발생했습니다.'}`);
    }
  } catch (err) {
    alert(`네트워크 오류: ${err}`);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = origBtnText;
    }
  }
}

function removeReciteFile() {
  currentReciteFile = "";
  currentAudioFile = currentMusicFile || "";
  const previewArea = document.getElementById("studioRecitePreviewArea");
  if (previewArea) previewArea.style.display = "none";
  const player = document.getElementById("studioRecitePlayer");
  if (player) {
    player.pause();
    player.src = "";
  }
}

// =========================================================
// 19. Colab YuE2 맞춤형 노트북 동적 다운로드 및 [3단계] 코드 복사
// =========================================================
async function downloadModularNotebook() {
  const ep = document.getElementById("inputEpisode").value || "제01화";
  const title = document.getElementById("inputFinalTitle").value.trim() || "무제";
  const lyricsInput = document.getElementById("musicLyricsInput");
  const lyrics = lyricsInput ? lyricsInput.value.trim() : "";

  const genrePrompt = getMusicGenrePrompt(currentMusicGenre);

  try {
    const res = await fetch("/api/export_colab_notebook", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        episode_no: ep,
        title: title,
        genre_prompt: genrePrompt,
        lyrics: lyrics
      })
    });
    const data = await res.json();
    if (data.success && data.notebook) {
      const blob = new Blob([JSON.stringify(data.notebook, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = data.filename || "노래음원_YuE2_원클릭.ipynb";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      alert(`🎉 [${ep}] 「${title}」 맞춤형 Colab 노트북이 다운로드되었습니다!\n\n파일명: ${data.filename}\n\nGoogle Colab에서 업로드하여 [런타임 모두 실행]을 누르시면 곧바로 작곡이 시작됩니다.`);
    } else {
      alert("노트북 생성 실패: " + (data.error || "오류"));
    }
  } catch (err) {
    alert("노트북 다운로드 중 오류 발생: " + err);
  }
}



// ========================================================
// 🎙️ 음성 인터뷰 (Web Speech API STT) & 시 낭송 (TTS)
// ========================================================
let currentRecognition = null;
let activeTargetId = null;
let activeBtnId = null;

function toggleVoiceDictation(targetInputId, btnId) {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    alert("현재 브라우저는 음성 인식(STT) 기능을 지원하지 않습니다.\nGoogle Chrome 또는 Microsoft Edge 브라우저를 이용해 주시기 바랍니다.");
    return;
  }

  const btn = document.getElementById(btnId);
  const target = document.getElementById(targetInputId);
  if (!target) return;

  // 이미 실행 중이고 동일한 버튼을 누른 경우 -> 중지
  if (currentRecognition && activeBtnId === btnId) {
    currentRecognition.stop();
    return;
  }

  // 다른 버튼이 실행 중이었던 경우 -> 기존 인식 중지
  if (currentRecognition) {
    currentRecognition.stop();
  }

  try {
    const recognition = new SpeechRecognition();
    recognition.lang = 'ko-KR';
    recognition.continuous = true;
    recognition.interimResults = true;

    currentRecognition = recognition;
    activeTargetId = targetInputId;
    activeBtnId = btnId;

    let baseText = target.value;
    let finalChunk = '';

    if (btn) {
      btn.classList.add('mic-recording');
      btn.innerHTML = `<span class="mic-icon recording-pulse">🔴</span> <span class="mic-label">듣고 있어요... (중지)</span>`;
    }

    recognition.onresult = (event) => {
      let interimChunk = '';
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          finalChunk += event.results[i][0].transcript + ' ';
        } else {
          interimChunk += event.results[i][0].transcript;
        }
      }

      const spoken = (finalChunk + interimChunk).trim();
      if (baseText) {
        const needsSpace = !(baseText.endsWith('\n') || baseText.endsWith(' '));
        target.value = baseText + (needsSpace ? ' ' : '') + spoken;
      } else {
        target.value = spoken;
      }
      target.dispatchEvent(new Event('input'));
    };

    recognition.onerror = (event) => {
      console.warn("음성 인식 이벤트:", event.error);
      if (event.error === 'not-allowed') {
        alert("마이크 사용 권한이 허용되지 않았습니다.\n브라우저 주소창 좌측의 자물쇠/사이트 설정 아이콘을 눌러 마이크 권한을 '허용'해 주세요.");
      }
    };

    recognition.onend = () => {
      if (btn) {
        btn.classList.remove('mic-recording');
        if (targetInputId === 'inputFinalPoem') {
          btn.innerHTML = `<span class="mic-icon">🎙️</span> <span class="mic-label">음성 구술</span>`;
        } else {
          btn.innerHTML = `<span class="mic-icon">🎙️</span> <span class="mic-label">말로 구술하기</span>`;
        }
      }
      currentRecognition = null;
      activeTargetId = null;
      activeBtnId = null;
    };

    recognition.start();

  } catch (err) {
    console.error("음성 인식 시작 실패:", err);
    alert("마이크를 시작할 수 없습니다: " + err.message);
  }
}

// 🎧 시 낭송 듣기 (Google Gemini TTS & Microsoft Edge-TTS 지능형 하이브리드 연동)
let currentGeminiReciteAudio = null;
let currentTtsEngine = 'gemini'; // 'gemini' | 'edge'
let isGeminiCreditExpired = false;

// 1. Google Gemini 전용 AI 서정 성우 목록
const GEMINI_VOICES = [
  { value: "Aoede", text: "🌸 여성 서정 (맑고 따뜻함)" },
  { value: "Charon", text: "🍃 남성 중저음 (깊은 울림)" },
  { value: "Kore", text: "🍵 여성 차분 (온화한 호흡)" },
  { value: "Puck", text: "🌾 남성 담백 (진솔한 청년)" },
  { value: "Fenrir", text: "🕊️ 원로 중후 (세월의 깊이)" }
];

// 2. Microsoft Edge-TTS 전용 고품질 신경망(Neural) 성우 목록 (100% 무료 무제한)
const EDGE_VOICES = [
  { value: "ko-KR-SunHiNeural", text: "🌸 선희 (맑은 서정 여성)" },
  { value: "ko-KR-InJoonNeural", text: "🍃 인준 (중후한 남성 중저음)" },
  { value: "ko-KR-HyunsuMultilingualNeural", text: "🌾 현수 (부드러운 청년 감성)" },
  { value: "ko-KR-BongJinNeural", text: "🕊️ 봉진 (차분하고 성숙한 남성)" }
];

// 성우 드롭다운 옵션 동적 교체
function updateVoiceSelectOptions(engine) {
  const select = document.getElementById("selectVoiceActor");
  if (!select) return;
  const currentVal = select.value;
  select.innerHTML = "";
  const list = (engine === "edge") ? EDGE_VOICES : GEMINI_VOICES;
  list.forEach(v => {
    const opt = document.createElement("option");
    opt.value = v.value;
    opt.textContent = v.text;
    select.appendChild(opt);
  });

  // 이전 선택 성우의 성별/톤에 맞춰 자연스러운 자동 매칭
  if (engine === "edge") {
    if (["Charon", "Fenrir"].includes(currentVal)) select.value = "ko-KR-InJoonNeural";
    else if (currentVal === "Puck") select.value = "ko-KR-HyunsuMultilingualNeural";
    else select.value = "ko-KR-SunHiNeural";
  } else {
    if (currentVal.includes("InJoon") || currentVal.includes("BongJin")) select.value = "Charon";
    else if (currentVal.includes("Hyunsu")) select.value = "Puck";
    else select.value = "Aoede";
  }
}

// TTS 엔진 상태 반영 및 UI 교체
function setTtsEngine(engine, isCreditExpired = false) {
  currentTtsEngine = engine;
  isGeminiCreditExpired = isCreditExpired;

  const badge = document.getElementById("badgeTtsEngine");
  const container = document.getElementById("ttsVoiceContainer");
  const btnCheck = document.getElementById("btnCheckGoogleCredit");

  updateVoiceSelectOptions(engine);

  if (engine === "edge") {
    if (badge) {
      badge.textContent = "⚡ Edge-TTS";
      badge.style.background = "#059669";
      badge.title = "[Edge-TTS 모드] 100% 무료 무제한 고품질 신경망 성우로 낭송합니다. (클릭하여 전환)";
    }
    if (container) {
      container.style.borderColor = "#10B981";
      container.style.background = "#ECFDF5";
    }
    if (btnCheck) {
      btnCheck.style.display = "inline-block";
    }
  } else {
    if (badge) {
      badge.textContent = "🌐 Google TTS";
      badge.style.background = "#E11D48";
      badge.title = "[Google Gemini TTS 모드] 고품질 AI 서정 성우로 낭송합니다. (클릭하여 전환)";
    }
    if (container) {
      container.style.borderColor = "#F43F5E";
      container.style.background = "#FFF1F2";
    }
    if (btnCheck) {
      btnCheck.style.display = "none";
    }
  }
}

// 사용자가 배지를 클릭했을 때 수동 전환 토글
async function toggleTtsEngineManual() {
  if (currentTtsEngine === "gemini") {
    setTtsEngine("edge", isGeminiCreditExpired);
    showToast("⚡ Microsoft Edge-TTS(무료 고음질 신경망) 성우 모드로 전환되었습니다.", "info");
  } else {
    if (isGeminiCreditExpired) {
      checkGoogleCreditRecovery();
    } else {
      setTtsEngine("gemini", false);
      showToast("🌐 Google Gemini TTS 성우 모드로 전환되었습니다.", "info");
    }
  }
}

// 📢 TTS 알림 전용 안전 모달 (절대로 저절로 닫히지 않으며 사용자가 확인할 때까지 유지)
function showTtsNoticeModal(options) {
  const { title, html, icon = 'info', confirmText = '확인', confirmColor = '#059669' } = options;

  if (window.Swal) {
    Swal.fire({
      icon: icon,
      title: title,
      html: html,
      allowOutsideClick: false,
      allowEscapeKey: false,
      showConfirmButton: true,
      confirmButtonText: confirmText,
      confirmButtonColor: confirmColor
    });
    return;
  }

  // SweetAlert2 라이브러리 부재 시 자체 DOM 팝업 모달
  let modalOverlay = document.getElementById("ttsCustomNoticeModal");
  if (!modalOverlay) {
    modalOverlay = document.createElement("div");
    modalOverlay.id = "ttsCustomNoticeModal";
    modalOverlay.style.position = "fixed";
    modalOverlay.style.inset = "0";
    modalOverlay.style.background = "rgba(0, 0, 0, 0.6)";
    modalOverlay.style.backdropFilter = "blur(3px)";
    modalOverlay.style.zIndex = "999999";
    modalOverlay.style.display = "flex";
    modalOverlay.style.alignItems = "center";
    modalOverlay.style.justifyContent = "center";
    modalOverlay.style.padding = "20px";
    document.body.appendChild(modalOverlay);
  }

  modalOverlay.innerHTML = `
    <div style="background: #FFFFFF; border-radius: 12px; width: 100%; max-width: 490px; box-shadow: 0 20px 45px rgba(0,0,0,0.3); overflow: hidden; border: 1.5px solid #E5E7EB;">
      <div style="padding: 18px 22px; border-bottom: 1px solid #E5E7EB; display: flex; align-items: center; justify-content: space-between; background: #FAF5FF;">
        <h3 style="margin: 0; font-size: 1.05rem; font-weight: 700; color: #1F2937;">${title}</h3>
        <button type="button" onclick="closeTtsNoticeModal()" style="border: none; background: transparent; font-size: 1.25rem; line-height: 1; cursor: pointer; color: #6B7280; padding: 2px 6px;">✕</button>
      </div>
      <div style="padding: 22px 24px; max-height: 60vh; overflow-y: auto;">
        ${html}
      </div>
      <div style="padding: 14px 22px; background: #F9FAFB; border-top: 1px solid #E5E7EB; text-align: right;">
        <button type="button" onclick="closeTtsNoticeModal()" style="background: ${confirmColor}; color: #FFFFFF; border: none; border-radius: 6px; padding: 9px 22px; font-size: 0.92rem; font-weight: 700; cursor: pointer; box-shadow: 0 2px 6px rgba(0,0,0,0.15);">${confirmText}</button>
      </div>
    </div>
  `;
  modalOverlay.style.display = "flex";
}

function closeTtsNoticeModal() {
  const modal = document.getElementById("ttsCustomNoticeModal");
  if (modal) modal.style.display = "none";
}

// Google 크레딧 재충전 확인 및 Google TTS 복구
async function checkGoogleCreditRecovery(e) {
  if (e) {
    e.preventDefault();
    e.stopPropagation();
  }

  const btnCheck = document.getElementById("btnCheckGoogleCredit");
  if (btnCheck) {
    btnCheck.disabled = true;
    btnCheck.textContent = "⏳ 확인 중...";
  }

  try {
    const res = await fetch("/api/tts/check_google", { method: "POST" });
    const data = await res.json();
    if (data.success) {
      setTtsEngine("gemini", false);
      showTtsNoticeModal({
        icon: "success",
        title: "🎉 Google TTS 복원 완료!",
        html: `<p style="font-size: 0.95rem; color: #166534; line-height: 1.6; margin: 0;">Google API 크레딧 충전 및 연결이 정상 확인되었습니다.<br><strong style="color: #BE123C;">Google Gemini TTS</strong> 성우 목록으로 자동 복원되었습니다.</p>`,
        confirmColor: "#166534"
      });
    } else {
      showTtsNoticeModal({
        icon: "warning",
        title: "⚠️ 아직 Google 크레딧이 충전되지 않음",
        html: `
          <div style="text-align: left; font-size: 0.9rem; line-height: 1.6; color: #374151;">
            <p style="margin: 0 0 8px 0;">Google Cloud API 크레딧이 아직 충전되지 않았거나 결제 활성화가 진행 중입니다.</p>
            <div style="background: #FFFBEB; border: 1px solid #FCD34D; padding: 10px 12px; border-radius: 6px; font-size: 0.83rem; color: #92400E; word-break: break-all; margin: 10px 0;">
              <strong>Google 응답:</strong> ${data.message || '402 Payment Required'}
            </div>
            <p style="margin: 10px 0 0 0; color: #047857; font-weight: 600;">
              💡 크레딧 충전 전까지 <strong>Edge-TTS(무료 고품질 신경망)</strong> 엔진이 계속 안전하게 유지됩니다.
            </p>
          </div>
        `,
        confirmColor: "#059669"
      });
    }
  } catch (err) {
    console.error("Google TTS 확인 실패:", err);
    showToast("서버 통신 오류로 Google TTS 상태 확인 실패", "error");
  } finally {
    if (btnCheck) {
      btnCheck.disabled = false;
      btnCheck.textContent = "🔄 크레딧 재충전 확인";
    }
  }
}

// 페이지 로드 시 초기 TTS 상태 점검
async function checkInitialTtsStatus() {
  try {
    const res = await fetch("/api/tts/status");
    const data = await res.json();
    if (data && data.gemini_credit_expired) {
      setTtsEngine("edge", true);
    } else if (data && data.engine) {
      setTtsEngine(data.engine, false);
    }
  } catch (err) {
    console.warn("TTS 상태 조회 실패:", err);
  }
}


// -------------------------------------------------------------
// 🎙️ 시 낭송 미리듣기 완료 후 공식 음원 등록 여부 확인 팝업
// (3대 음원: 육성 녹음 / AI 성우 낭송 / 서정 노래 독립 영구 보관)
// -------------------------------------------------------------
function askSaveTtsReciteAudio(data, ep, title) {
  if (typeof Swal === "undefined") {
    const confirmMsg = `「${title}」 시 낭송을 들으셨습니다.\n\n"🎙️ 이 낭송 음성을 이 작품의 공식 음원으로 등록하시겠습니까?"\n\n(기존 육성 녹음이나 노래는 삭제되지 않고 각각 독립 보관되어 감상 시 골라 들으실 수 있습니다)`;
    const ok = confirm(confirmMsg);
    if (ok) {
      applyOfficialReciteAudio(data, ep);
    }
    return;
  }

  Swal.fire({
    title: '🎙️ 시 낭송 음원 등록 확인',
    html: `
      <div style="text-align: left; font-size: 0.92rem; line-height: 1.6; color: #374151;">
        <p style="margin-bottom: 10px;"><strong>「${escapeHtml(title)}」</strong> 시 낭송 음성을 감상하셨습니다.</p>
        
        <div style="color: #1E3A8A; background: #EFF6FF; border: 1.5px solid #93C5FD; padding: 12px 14px; border-radius: 8px; margin-bottom: 12px;">
          <div style="font-weight: 700; font-size: 0.96rem; margin-bottom: 4px; color: #1D4ED8;">
            "🎙️ 이 낭송 음성을 이 작품의 공식 음원으로 등록하시겠습니까?"
          </div>
          <div style="font-size: 0.82rem; color: #2563EB; line-height: 1.5;">
            • <strong>[예, AI 낭송으로 등록]</strong>: 조판실 및 갤러리의 [🎧 오디오] 메뉴에서 언제든 재생할 수 있습니다.<br>
            • <strong>[아니오 (미리듣기만)]</strong>: 등록하지 않고 방금 들으신 테스트 미리듣기로 마칩니다.
          </div>
        </div>

        <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px 12px; font-size: 0.82rem; color: #475569; line-height: 1.5;">
          🛡️ <strong>음원 독립 보관 시스템 안내</strong><br>
          이 음성을 등록하셔도 <strong>[육성 시 낭송], [음악 시 낭송], [노래]는 전혀 삭제되지 않고 각각 독립 보관</strong>됩니다.<br>
          조판실 및 갤러리의 [🎧 오디오] 메뉴에서 원하시는 트랙을 언제든 골라 들으실 수 있습니다.
        </div>
      </div>
    `,
    icon: 'question',
    showCancelButton: true,
    confirmButtonColor: '#2563EB',
    cancelButtonColor: '#64748B',
    confirmButtonText: '✅ 예, AI 낭송 음원으로 등록',
    cancelButtonText: '❌ 아니오 (미리듣기만)',
    backdrop: true
  }).then((result) => {
    if (result.isConfirmed) {
      applyOfficialReciteAudio(data, ep);
    } else {
      showToast("등록하지 않고 시 낭송 미리듣기만 마쳤습니다.", "info");
    }
  });
}

function applyOfficialReciteAudio(data, ep) {
  currentReciteFile = data.rel_path || `music/${data.filename}`;
  const recitePlayer = document.getElementById("studioRecitePlayer");
  const recitePreviewArea = document.getElementById("studioRecitePreviewArea");
  const reciteFilename = document.getElementById("studioPreviewReciteFilename");
  if (recitePlayer && data.audio_url) {
    recitePlayer.src = data.audio_url;
    if (reciteFilename) reciteFilename.textContent = data.filename;
    if (recitePreviewArea) recitePreviewArea.style.display = "block";
  }

  if (currentStatus && currentStatus.works) {
    const curWork = currentStatus.works.find(w => w.episode_no === ep);
    if (curWork) {
      curWork.recite_file = currentReciteFile;
      curWork.aiRecite = data.audio_url;
      curWork.hasAiRecite = true;
    }
  }

  showToast(`✅ [${ep}] AI 시 낭송 음원이 안전하게 등록되었습니다! (육성 녹음 및 노래와 함께 독립 보관됩니다)`, "success");
}

async function toggleSpeakPoem() {
  const btn = document.getElementById("btnSpeakPoem");
  const poemText = document.getElementById("inputFinalPoem") ? document.getElementById("inputFinalPoem").value.trim() : "";
  const title = document.getElementById("inputFinalTitle") ? document.getElementById("inputFinalTitle").value.trim() : "무제";
  const ep = document.getElementById("inputEpisode") ? document.getElementById("inputEpisode").value.trim() : "제01화";

  const voiceSelect = document.getElementById("selectVoiceActor");
  const selectedVoice = voiceSelect ? voiceSelect.value : (currentTtsEngine === 'edge' ? "ko-KR-SunHiNeural" : "Aoede");
  const voiceNameText = voiceSelect && voiceSelect.selectedOptions[0] ? voiceSelect.selectedOptions[0].text : "AI 성우";

  // 1. 이미 재생 중인 경우 즉시 중지
  if (currentGeminiReciteAudio && !currentGeminiReciteAudio.paused) {
    currentGeminiReciteAudio.pause();
    currentGeminiReciteAudio.currentTime = 0;
    if (btn) btn.innerHTML = `🎧 시 낭송 듣기`;
    return;
  }
  if (window.speechSynthesis && window.speechSynthesis.speaking) {
    window.speechSynthesis.cancel();
    if (btn) btn.innerHTML = `🎧 시 낭송 듣기`;
    return;
  }

  if (!poemText) {
    alert("낭송할 시 본문이 비어 있습니다. 먼저 시를 다듬어 주세요.");
    return;
  }

  // 스튜디오 내 기존 육성 낭송 및 노래 플레이어 즉시 중지 (중복 재생 방지)
  const studioRecitePlayer = document.getElementById("studioRecitePlayer");
  const studioAudioPlayer = document.getElementById("studioAudioPlayer");
  if (studioRecitePlayer && !studioRecitePlayer.paused) studioRecitePlayer.pause();
  if (studioAudioPlayer && !studioAudioPlayer.paused) studioAudioPlayer.pause();

  // 2. TTS 호출 시도
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<span>⏳ ${voiceNameText.split(' ')[1] || '성우'} 낭송 빚는 중... (음성 합성 대기 필요)</span>`;
  }

  try {
    const res = await fetch("/api/speak_poem", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: title,
        poem_body: poemText,
        episode_no: ep,
        voice: selectedVoice,
        engine: currentTtsEngine
      })
    });

    const data = await res.json();

    // 📢 Google 크레딧 만료 감지 시 알림 공지 및 Edge-TTS 모드 자동 전환
    if (data.gemini_credit_expired && (!isGeminiCreditExpired || data.just_switched)) {
      setTtsEngine("edge", true);
      showTtsNoticeModal({
        icon: 'warning',
        title: '📢 Google API 크레딧 만료 알림',
        html: `
          <div style="text-align: left; font-size: 0.92rem; line-height: 1.6; color: #374151;">
            <p style="margin-bottom: 8px; font-weight: 700; color: #BE123C;">Google Cloud API 크레딧이 만료(소진)되었습니다.</p>
            <p>시 낭송 감상이 끊기지 않도록 <strong>Microsoft Edge-TTS(고품질 신경망 성우)</strong>로 자동 전환되었습니다.</p>
            <ul style="padding-left: 20px; margin: 10px 0; color: #047857; font-weight: 600;">
              <li>성우 선택란이 Edge-TTS 신경망 성우(선희, 인준, 현수, 봉진)로 교체되었습니다.</li>
              <li>100% 무료·무제한으로 고음질 낭송이 생성되어 재생 및 보존됩니다.</li>
            </ul>
            <div style="background: #F3F4F6; padding: 10px; border-radius: 6px; font-size: 0.84rem; color: #4B5563;">
              💡 <strong>재충전 공지:</strong> Google Cloud 콘솔 결제 후, 성우 상자의 <strong>[🔄 크레딧 재충전 확인]</strong> 버튼을 누르시면 즉시 원래의 Google TTS로 복구됩니다.
            </div>
          </div>
        `,
        confirmText: '확인 및 계속 감상',
        confirmColor: '#059669'
      });
    }

    if (res.ok && data.success && (data.data_uri || data.audio_url)) {
      currentGeminiReciteAudio = new Audio(data.data_uri || data.audio_url);

      currentGeminiReciteAudio.onplay = () => {
        if (btn) {
          btn.disabled = false;
          btn.innerHTML = `⏹️ 낭송 중지`;
        }
      };

      currentGeminiReciteAudio.onended = () => {
        if (btn) btn.innerHTML = `🎧 시 낭송 듣기`;

        // 🎙️ 낭송 감상 완료 후 공식 재생용 음원으로 저장할지 확인
        askSaveTtsReciteAudio(data, ep, title);
      };

      currentGeminiReciteAudio.onerror = () => {
        if (btn) btn.innerHTML = `🎧 시 낭송 듣기`;
      };

      await currentGeminiReciteAudio.play();
      showToast(`✨ [${data.provider_name || voiceNameText}] 고음질 서정 낭송이 재생됩니다. (음원으로 보존됨)`, "success");

      // 🎧 재생 시작 안내 (낭송 종료 시 공식 저장 여부를 확인합니다)
      showToast(`🎧 [${data.provider_name || voiceNameText}] 시 낭송을 미리 듣습니다. (낭송 후 저장 여부 확인)`, "info");
      return;
    } else {
      const errMsg = (data && (data.detail || data.error)) ? String(data.detail || data.error) : "TTS 서비스 호출 실패";
      console.warn("[TTS 실패]:", errMsg);
      showToast(`⚠️ 시 낭송 생성 실패: ${errMsg}`, "error", 6000);
    }
  } catch (err) {
    console.warn("TTS 호출 네트워크 예외 발생:", err);
    showToast("⚠️ <b>시 낭송 연결 실패:</b> 서버 네트워크 연결을 확인해주세요.", "error", 6000);
  } finally {
    if (btn) btn.disabled = false;
  }


  // 3. 폴백: 로컬 Web Speech API 브라우저 TTS
  if ('speechSynthesis' in window) {
    const fallbackText = (title && title !== "무제") ? `${title}.\n\n${poemText}` : poemText;
    const utterance = new SpeechSynthesisUtterance(fallbackText);
    utterance.lang = 'ko-KR';

    // 성우 성별/연령대에 맞춘 피치 및 속도 조절
    const isMale = ["Charon", "Puck", "Fenrir"].includes(selectedVoice);
    if (selectedVoice === "Fenrir") {
      utterance.pitch = 0.78;
      utterance.rate = 0.80;
    } else if (selectedVoice === "Charon") {
      utterance.pitch = 0.82;
      utterance.rate = 0.86;
    } else if (selectedVoice === "Puck") {
      utterance.pitch = 0.94;
      utterance.rate = 0.90;
    } else if (selectedVoice === "Kore") {
      utterance.pitch = 0.98;
      utterance.rate = 0.86;
    } else {
      utterance.pitch = 1.05; // Aoede 기본 여성
      utterance.rate = 0.88;
    }

    const voices = window.speechSynthesis.getVoices();
    const koVoices = voices.filter(v => v.lang.startsWith('ko'));
    if (koVoices.length > 0) {
      if (isMale) {
        const maleVoice = koVoices.find(v => v.name.includes("Male") || v.name.includes("남성") || v.name.includes("InJoon") || v.name.includes("MinHo"));
        utterance.voice = maleVoice || koVoices[0];
      } else {
        const femaleVoice = koVoices.find(v => v.name.includes("Female") || v.name.includes("여성") || v.name.includes("SunHi") || v.name.includes("HeaMi"));
        utterance.voice = femaleVoice || koVoices[0];
      }
    }

    utterance.onstart = () => { if (btn) btn.innerHTML = `⏹️ 낭송 중지`; };
    utterance.onend = () => { if (btn) btn.innerHTML = `🎧 시 낭송 듣기`; };
    utterance.onerror = () => { if (btn) btn.innerHTML = `🎧 시 낭송 듣기`; };

    window.speechSynthesis.speak(utterance);
  } else {
    alert("음성을 재생할 수 없습니다.");
  }
}


// ============================================================
// 16. 시인의 영혼: 내 목소리 육성 낭송 녹음실 (Voice Studio)
// ============================================================
let voiceMediaRecorder = null;
let voiceAudioChunks = [];
let voiceRecordedBlob = null;
let voiceRecTimerInterval = null;
let voiceRecSeconds = 0;

function openVoiceRecModal() {
  const epSelect = document.getElementById("selectWorkToEdit");
  let epNo = epSelect ? epSelect.value : "";
  if (!epNo) {
    const epInput = document.getElementById("inputEpisode");
    epNo = epInput ? epInput.value : "제01화";
  }
  const title = document.getElementById("inputFinalTitle")?.value || "무제";

  const badge = document.getElementById("voiceRecTargetBadge");
  if (badge) badge.textContent = `[${epNo}] ${title}`;

  resetVoiceRecState();

  const modal = document.getElementById("voiceRecModal");
  if (modal) modal.style.display = "flex";
}

function closeVoiceRecModal() {
  if (voiceMediaRecorder && voiceMediaRecorder.state === "recording") {
    voiceMediaRecorder.stop();
  }
  resetVoiceRecState();
  const modal = document.getElementById("voiceRecModal");
  if (modal) modal.style.display = "none";
}

function resetVoiceRecState() {
  if (voiceRecTimerInterval) {
    clearInterval(voiceRecTimerInterval);
    voiceRecTimerInterval = null;
  }
  voiceRecSeconds = 0;
  voiceAudioChunks = [];
  voiceRecordedBlob = null;

  const timerEl = document.getElementById("voiceRecTimerDisplay");
  if (timerEl) timerEl.textContent = "00:00";

  const statusEl = document.getElementById("voiceRecStatusText");
  if (statusEl) statusEl.textContent = "'낭송 녹음 시작' 버튼을 누른 뒤 시를 낭독해 주세요.";

  const indicator = document.getElementById("voiceRecPulsingIndicator");
  if (indicator) {
    indicator.style.background = "#FFFFFF";
    indicator.style.borderColor = "#EBD5C2";
    indicator.style.boxShadow = "none";
  }

  const btnStart = document.getElementById("btnVoiceRecStart");
  const btnStop = document.getElementById("btnVoiceRecStop");
  const btnSave = document.getElementById("btnVoiceRecSave");
  const previewArea = document.getElementById("voiceRecPreviewArea");

  if (btnStart) btnStart.disabled = false;
  if (btnStop) btnStop.disabled = true;
  if (btnSave) btnSave.disabled = true;
  if (previewArea) previewArea.style.display = "none";

  const audioPlayer = document.getElementById("voiceRecAudioPlayer");
  if (audioPlayer) {
    audioPlayer.pause();
    audioPlayer.src = "";
  }
}

async function startVoiceRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    voiceAudioChunks = [];
    voiceRecordedBlob = null;

    voiceMediaRecorder = new MediaRecorder(stream);
    voiceMediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) voiceAudioChunks.push(e.data);
    };

    voiceMediaRecorder.onstop = () => {
      voiceRecordedBlob = new Blob(voiceAudioChunks, { type: "audio/webm" });
      const audioUrl = URL.createObjectURL(voiceRecordedBlob);
      const audioPlayer = document.getElementById("voiceRecAudioPlayer");
      if (audioPlayer) audioPlayer.src = audioUrl;

      const previewArea = document.getElementById("voiceRecPreviewArea");
      if (previewArea) previewArea.style.display = "block";

      const btnSave = document.getElementById("btnVoiceRecSave");
      if (btnSave) btnSave.disabled = false;

      stream.getTracks().forEach(track => track.stop());
    };

    voiceMediaRecorder.start();

    const btnStart = document.getElementById("btnVoiceRecStart");
    const btnStop = document.getElementById("btnVoiceRecStop");
    if (btnStart) btnStart.disabled = true;
    if (btnStop) btnStop.disabled = false;

    const statusEl = document.getElementById("voiceRecStatusText");
    if (statusEl) statusEl.textContent = "🔴 녹음 중... 시인의 따뜻한 육성으로 시를 낭독해 주세요.";

    const indicator = document.getElementById("voiceRecPulsingIndicator");
    if (indicator) {
      indicator.style.background = "#FFF0EE";
      indicator.style.borderColor = "#C84B31";
      indicator.style.boxShadow = "0 0 16px rgba(200, 75, 49, 0.4)";
    }

    voiceRecSeconds = 0;
    voiceRecTimerInterval = setInterval(() => {
      voiceRecSeconds++;
      const mins = String(Math.floor(voiceRecSeconds / 60)).padStart(2, '0');
      const secs = String(voiceRecSeconds % 60).padStart(2, '0');
      const timerEl = document.getElementById("voiceRecTimerDisplay");
      if (timerEl) timerEl.textContent = `${mins}:${secs}`;
    }, 1000);

  } catch (err) {
    alert("마이크 접근 권한이 필요합니다: " + err.message);
  }
}

function stopVoiceRecording() {
  if (voiceMediaRecorder && voiceMediaRecorder.state === "recording") {
    voiceMediaRecorder.stop();
  }
  if (voiceRecTimerInterval) {
    clearInterval(voiceRecTimerInterval);
    voiceRecTimerInterval = null;
  }

  const btnStart = document.getElementById("btnVoiceRecStart");
  const btnStop = document.getElementById("btnVoiceRecStop");
  if (btnStart) btnStart.disabled = false;
  if (btnStop) btnStop.disabled = true;

  const statusEl = document.getElementById("voiceRecStatusText");
  if (statusEl) statusEl.textContent = "✓ 낭송 녹음이 완료되었습니다. 아래에서 들어보실 수 있습니다.";

  const indicator = document.getElementById("voiceRecPulsingIndicator");
  if (indicator) {
    indicator.style.background = "#EEF4EB";
    indicator.style.borderColor = "#436940";
    indicator.style.boxShadow = "none";
  }
}

async function saveVoiceRecordingToWork() {
  if (!voiceRecordedBlob) {
    alert("녹음된 음원 데이터가 없습니다.");
    return;
  }

  const epSelect = document.getElementById("selectWorkToEdit");
  let epNo = epSelect ? epSelect.value : "";
  if (!epNo) {
    const epInput = document.getElementById("inputEpisode");
    epNo = epInput ? epInput.value : "제01화";
  }
  const title = document.getElementById("inputFinalTitle")?.value || "무제";

  const btnSave = document.getElementById("btnVoiceRecSave");
  const origText = btnSave ? btnSave.innerHTML : "";
  if (btnSave) {
    btnSave.disabled = true;
    btnSave.innerHTML = "<span>⏳ 시집에 육성 보관 중...</span>";
  }

  const formData = new FormData();
  formData.append("episode_no", epNo);
  formData.append("title", title);
  formData.append("audio_file", voiceRecordedBlob, `${epNo}_낭송.webm`);

  try {
    const res = await fetch("/api/save_voice_recording", {
      method: "POST",
      body: formData
    });
    const data = await res.json();
    if (res.ok && data.success) {
      alert(`🎉 ${data.message}\n\n가상 북 뷰어와 스튜디오에 시인의 육성이 공식 낭송 음원으로 등록되었습니다.`);
      closeVoiceRecModal();

      currentReciteFile = data.audio_file;
      currentAudioFile = currentMusicFile || currentReciteFile;

      const recitePreviewArea = document.getElementById("studioRecitePreviewArea");
      const reciteFilenameEl = document.getElementById("studioPreviewReciteFilename");
      const recitePlayer = document.getElementById("studioRecitePlayer");

      if (reciteFilenameEl) reciteFilenameEl.textContent = data.filename || data.audio_file.split("/").pop();
      if (recitePlayer) {
        const proj = (currentStatus && currentStatus.project) ? currentStatus.project : null;
        const safeName = (proj && proj.name) ? proj.name.replace(/\s+/g, '_') : "노을빛_기억";
        recitePlayer.src = `/projects/${safeName}/${data.audio_file.replace(/^\.?\//, '')}`;
        recitePlayer.load();
        const dlReciteBtn = document.getElementById("btnDownloadStudioRecite");
        if (dlReciteBtn) {
          dlReciteBtn.href = recitePlayer.src;
          dlReciteBtn.download = data.filename || data.audio_file.split("/").pop() || "01_낭송.mp3";
        }
      }
      if (recitePreviewArea) recitePreviewArea.style.display = "block";

      await loadStatus();
    } else {
      alert("육성 저장 실패: " + (data.detail || data.error || "오류가 발생했습니다."));
    }
  } catch (err) {
    alert("육성 업로드 네트워크 오류: " + err);
  } finally {
    if (btnSave) {
      btnSave.disabled = false;
      btnSave.innerHTML = origText;
    }
  }
}


// (17번 섹션의 중복 정의 함수는 19번 섹션 구현으로 통합되어 제거됨)


