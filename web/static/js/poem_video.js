/**
 * StoryBook Studio - 시화 낭송 영상(Poem Video) 좌측 사이드바 연동 스크립트
 */

let currentVideoTaskId = null;
let currentVideoPollTimer = null;
let latestVideoUrl = null;
let customAudioUploadedPath = null;

// 현재 선택된 화 번호 가져오기 (절대 NaN을 반환하지 않음)
function getCurrentEpisodeNo() {
    // 1. currentEditingEpisode 확인 (예: "제11화", "11화", 11, "09")
    if (typeof currentEditingEpisode !== 'undefined' && currentEditingEpisode) {
        const cleaned = String(currentEditingEpisode).replace(/[^0-9]/g, '');
        if (cleaned) {
            const val = parseInt(cleaned, 10);
            if (!isNaN(val) && val > 0) return val;
        }
    }

    // 2. inputEpisode 히든/인풋 필드 확인
    const inputEp = document.getElementById("inputEpisode");
    if (inputEp && inputEp.value) {
        const cleaned = String(inputEp.value).replace(/[^0-9]/g, '');
        if (cleaned) {
            const val = parseInt(cleaned, 10);
            if (!isNaN(val) && val > 0) return val;
        }
    }

    // 3. selectWorkToEdit 회차 선택 드롭다운 확인
    const epSelect = document.getElementById('selectWorkToEdit');
    if (epSelect && epSelect.value && epSelect.value !== 'new') {
        const cleaned = String(epSelect.value).replace(/[^0-9]/g, '');
        if (cleaned) {
            const val = parseInt(cleaned, 10);
            if (!isNaN(val) && val > 0) return val;
        }
    }

    // 4. 편집 배지 확인 (labelCurrentEditingEpBadge)
    const epBadge = document.getElementById('labelCurrentEditingEpBadge');
    if (epBadge && epBadge.textContent) {
        const cleaned = String(epBadge.textContent).replace(/[^0-9]/g, '');
        if (cleaned) {
            const val = parseInt(cleaned, 10);
            if (!isNaN(val) && val > 0) return val;
        }
    }

    // 5. 기본값: 제11화
    return 11;
}

// 현재 활성 프로젝트 이름 가져오기
function getActiveProjectName() {
    if (typeof activeProjectName !== 'undefined' && activeProjectName) {
        return activeProjectName;
    }
    const pTitle = document.getElementById('headerProjectTitle');
    if (pTitle && pTitle.textContent.trim()) {
        return pTitle.textContent.trim();
    }
    return "노을빛_기억";
}

// 사이드바 비디오 상태 업데이트
async function updateSidebarVideoCard(episodeNo) {
    let ep = episodeNo;
    if (typeof ep === 'string') {
        const cleaned = ep.replace(/[^0-9]/g, '');
        ep = cleaned ? parseInt(cleaned, 10) : null;
    }
    if (!ep || isNaN(ep)) {
        ep = getCurrentEpisodeNo();
    }
    if (!ep || isNaN(ep)) ep = 11;

    const project = getActiveProjectName();

    const titleEl = document.getElementById('sidebarVideoCurrentEpText');
    if (titleEl) {
        titleEl.textContent = `제${ep}화 영상 관리`;
    }

    try {
        const resp = await fetch(`/api/poem_video/status/${encodeURIComponent(project)}/${ep}?t=${Date.now()}`);
        const data = await resp.json();

        const badge = document.getElementById('sidebarVideoBadge');
        const actionArea = document.getElementById('sidebarVideoActionArea');
        const dlLink = document.getElementById('sidebarVideoDownloadLink');
        const inlineContainer = document.getElementById('videoInlinePlayerContainer');
        const inlinePlayer = document.getElementById('videoInlinePlayer');
        const videoSelect = document.getElementById('videoWorkSelect');
        const audioBadgeEl = document.getElementById('videoAudioStatusBadge');
        const tracksListEl = document.getElementById('videoReciteTracksList');

        // 최대 3개 낭송 음원 라디오 리스트 렌더링
        if (tracksListEl) {
            const tracks = data.recite_tracks || [];
            if (tracks.length > 0) {
                if (audioBadgeEl) {
                    audioBadgeEl.textContent = `${tracks.length}개 음원 등록됨`;
                    audioBadgeEl.style.background = "#E8F5E9";
                    audioBadgeEl.style.color = "#2B7A4B";
                }

                // 현재 선택된 음원 유지 (없으면 첫 번째 기본 선택)
                let currentSelectedPath = window.selectedPoemVideoAudioPath;
                if (!currentSelectedPath || !tracks.some(t => t.rel_path === currentSelectedPath)) {
                    currentSelectedPath = tracks[0].rel_path;
                    window.selectedPoemVideoAudioPath = currentSelectedPath;
                }

                let html = '';
                tracks.forEach((t, idx) => {
                    const isChecked = (t.rel_path === currentSelectedPath);
                    const tagStyle = (t.type === 'voice') ? 'background:#FDF2F8; border-color:#F472B6; color:#9D174D;' :
                                     ((t.type === 'ai_recite') ? 'background:#EFF6FF; border-color:#93C5FD; color:#1D4ED8;' :
                                     'background:#FEF3C7; border-color:#FCD34D; color:#92400E;');
                    
                    html += `
                        <label style="display: flex; align-items: center; justify-content: space-between; background: ${isChecked ? '#FFF9F2' : '#FFFFFF'}; border: 1.5px solid ${isChecked ? '#7A5335' : '#EFE8DE'}; border-radius: 8px; padding: 7px 10px; cursor: pointer; transition: all 0.2s;">
                            <div style="display: flex; align-items: center; gap: 8px; overflow: hidden; flex: 1;">
                                <input type="radio" name="optVideoReciteTrack" value="${t.rel_path}" ${isChecked ? 'checked' : ''} onchange="onSelectPoemVideoTrack('${t.rel_path}')" style="accent-color: #7A5335; cursor: pointer;">
                                <span style="font-size: 0.75rem; font-weight: 700; padding: 2px 6px; border-radius: 4px; border: 1px solid; ${tagStyle} white-space: nowrap;">
                                    ${t.icon} ${t.label}
                                </span>
                                <span style="font-size: 0.82rem; font-weight: 600; color: #4A3B32; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${t.filename}">
                                    ${t.filename}
                                </span>
                            </div>
                            <button type="button" class="btn-micro" onclick="toggleVideoRecitePreview('${t.url}', this, event)" style="background: #FAF7F2; border: 1px solid #D8C8B8; border-radius: 5px; padding: 3px 8px; font-size: 0.74rem; font-weight: 600; color: #5A4A3E; cursor: pointer; display: flex; align-items: center; gap: 3px; margin-left: 8px;">
                                <span>▶</span> <span>듣기</span>
                            </button>
                        </label>
                    `;
                });
                tracksListEl.innerHTML = html;
            } else {
                if (audioBadgeEl) {
                    audioBadgeEl.textContent = "음원 없음";
                    audioBadgeEl.style.background = "#FBE9E7";
                    audioBadgeEl.style.color = "#D84315";
                }
                tracksListEl.innerHTML = `
                    <div style="padding: 10px 12px; text-align: center; color: #991B1B; background: #FEF2F2; border: 1px solid #FCA5A5; border-radius: 6px; font-size: 0.8rem; line-height: 1.4;">
                        ⚠️ 등록된 낭송 음원이 없습니다.<br>
                        시화 창작 스튜디오에서 <strong>[🎙️ 육성 녹음]</strong> 또는 <strong>[🤖 AI 낭송]</strong>을 먼저 생성해주세요.
                    </div>
                `;
            }
        }

        if (videoSelect && String(videoSelect.value).replace(/[^0-9]/g, '') !== String(ep)) {
            videoSelect.value = ep;
        }

        if (data.success && data.video && data.video.exists) {
            if (badge) {
                badge.textContent = `완성 (${data.video.size_mb}MB)`;
                badge.style.background = "#2B7A4B";
                badge.style.color = "#FFF";
            }
            if (actionArea) actionArea.style.display = "flex";
            if (dlLink) {
                dlLink.href = data.video.url;
                dlLink.setAttribute('download', data.video.filename);
            }
            if (inlineContainer && inlinePlayer) {
                if (inlinePlayer.src !== window.location.origin + data.video.url) {
                    inlinePlayer.src = data.video.url;
                }
                inlineContainer.style.display = "block";
            }
            latestVideoUrl = data.video.url;
        } else {
            if (badge) {
                badge.textContent = "미제작";
                badge.style.background = "#EEE";
                badge.style.color = "#666";
            }
            if (actionArea) actionArea.style.display = "none";
            if (inlineContainer) {
                inlineContainer.style.display = "none";
                if (inlinePlayer) inlinePlayer.src = "";
            }
            latestVideoUrl = null;
        }
    } catch (e) {
        console.warn("[PoemVideo] 상태 조회 실패:", e);
        const audioBadgeEl = document.getElementById('videoAudioStatusBadge');
        const tracksListEl = document.getElementById('videoReciteTracksList');
        if (audioBadgeEl) {
            audioBadgeEl.textContent = "음원 확인 필요";
            audioBadgeEl.style.background = "#FEF3C7";
            audioBadgeEl.style.color = "#92400E";
        }
        if (tracksListEl) {
            tracksListEl.innerHTML = `
                <div style="padding: 10px; text-align: center; color: #78350F; background: #FFFBEB; border: 1px solid #FDE68A; border-radius: 6px; font-size: 0.8rem;">
                    음원 상태를 가져오는 중 일시적 지연이 발생했습니다. 
                    <button type="button" onclick="updateSidebarVideoCard(${ep})" style="margin-left: 6px; padding: 2px 8px; background: #FFF; border: 1px solid #D97706; border-radius: 4px; color: #B45309; font-weight: 700; cursor: pointer;">다시 확인</button>
                </div>
            `;
        }
    }

    // 우측 노래 영상 카드 동기화
    try {
        updateSidebarSongVideoCard(ep);
    } catch (e) {
        console.warn("[SongVideo] 상태 조회 실패:", e);
    }
}

// 음성 소스 라디오 변경 핸들러
function onVideoAudioSourceChange() {
    const radios = document.getElementsByName('videoAudioSource');
    let selected = "tts";
    for (const r of radios) {
        if (r.checked) {
            selected = r.value;
            break;
        }
    }

    const uploadArea = document.getElementById('sidebarAudioUploadArea');
    if (uploadArea) {
        uploadArea.style.display = (selected === "suno") ? "block" : "none";
    }
}

// [앱 표준] 파일 선택 창에서 녹음 파일 선택 시 업로드
async function handleSidebarAudioFileSelected(input) {
    if (!input.files || input.files.length === 0) return;
    const file = input.files[0];
    const project = getActiveProjectName();
    let ep = getCurrentEpisodeNo();
    if (!ep || isNaN(ep)) ep = 11;

    const nameEl = document.getElementById('sidebarUploadedAudioName');
    if (nameEl) {
        nameEl.textContent = `업로드 중: ${file.name}...`;
        nameEl.style.display = "block";
        nameEl.style.color = "#B87333";
    }

    const formData = new FormData();
    formData.append('project_name', project);
    formData.append('episode_no', String(ep));
    formData.append('audio_file', file);

    try {
        const resp = await fetch('/api/poem_video/upload_custom_audio', {
            method: 'POST',
            body: formData
        });
        const res = await resp.json();
        if (res.success) {
            customAudioUploadedPath = res.path;
            if (nameEl) {
                nameEl.textContent = `✓ 선택됨: ${res.filename} (${Math.round(res.size_bytes / 1024)}KB)`;
                nameEl.style.color = "#2B7A4B";
            }
            alert(`음원 파일이 제${ep}화 공식 음원으로 등록되었습니다!`);
            updateSidebarVideoCard(ep);
        } else {
            alert("음원 파일 등록 실패: " + (res.error || "알 수 없는 오류"));
            if (nameEl) nameEl.style.display = "none";
        }
    } catch (e) {
        alert("업로드 중 네트워크 오류가 발생했습니다: " + e.message);
        if (nameEl) nameEl.style.display = "none";
    }
}

// [앱 표준] 윈도우 파일 탐색기로 음악 폴더 열기
async function openProjectMusicFolder() {
    const project = getActiveProjectName();
    const formData = new FormData();
    formData.append('project_name', project);

    try {
        const resp = await fetch('/api/poem_video/open_music_folder', {
            method: 'POST',
            body: formData
        });
        const res = await resp.json();
        if (res.success) {
            console.log(res.message);
        } else {
            alert(res.error || "폴더를 열지 못했습니다.");
        }
    } catch (e) {
        console.error("폴더 열기 에러:", e);
    }
}

// 화면 비율 선택 UI 반응
function handleAspectRatioChange(ratio) {
    const lbl16 = document.getElementById('optLabel16x9');
    const lbl9 = document.getElementById('optLabel9x16');
    if (!lbl16 || !lbl9) return;
    if (ratio === '9:16') {
        lbl9.style.borderColor = '#7A5335';
        lbl9.style.background = '#FAF2E8';
        lbl9.style.color = '#5A3A22';
        lbl9.style.fontWeight = '700';
        lbl16.style.borderColor = '#D8C8B8';
        lbl16.style.background = '#FFF';
        lbl16.style.color = '#6E5340';
        lbl16.style.fontWeight = '600';
    } else {
        lbl16.style.borderColor = '#7A5335';
        lbl16.style.background = '#FAF2E8';
        lbl16.style.color = '#5A3A22';
        lbl16.style.fontWeight = '700';
        lbl9.style.borderColor = '#D8C8B8';
        lbl9.style.background = '#FFF';
        lbl9.style.color = '#6E5340';
        lbl9.style.fontWeight = '600';
    }
}

// 영상 렌더링 요청
async function requestPoemVideoRender() {
    let ep = getCurrentEpisodeNo();
    if (!ep || isNaN(ep)) ep = 11;

    const project = getActiveProjectName();

    const btn = document.getElementById('btnMakePoemVideo');
    const progressArea = document.getElementById('sidebarVideoProgressArea');
    const progressBar = document.getElementById('sidebarVideoProgressBar');
    const progressStatus = document.getElementById('sidebarVideoProgressStatus');
    const progressPercent = document.getElementById('sidebarVideoProgressPercent');

    if (btn) btn.disabled = true;
    if (progressArea) progressArea.style.display = "block";
    if (progressBar) {
        progressBar.className = "video-progress-fill-active";
        progressBar.style.width = "10%";
    }
    if (progressStatus) progressStatus.textContent = "영상 작업 준비 중...";
    if (progressPercent) progressPercent.textContent = "10%";

    // [우리 앱 표준] 마우스 커서를 대기형(스피너 ⏳)으로 즉시 전환
    if (typeof setAppBusy === 'function') {
        setAppBusy(true, "고화질 시화 영상 제작 중...");
    }

    try {
        const ratioRadio = document.querySelector('input[name="videoAspectRatio"]:checked');
        const aspectRatio = ratioRadio ? ratioRadio.value : '16:9';
        const specSelect = document.getElementById('selectVideoSpectrumStyle');
        const spectrumStyle = specSelect ? specSelect.value : 'bar';

        const payload = {
            project_name: project,
            episode_no: ep,
            audio_type: "recite",
            custom_audio_path: customAudioUploadedPath || window.selectedPoemVideoAudioPath || null,
            aspect_ratio: aspectRatio,
            spectrum_style: spectrumStyle
        };

        const resp = await fetch('/api/poem_video/render', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        const data = await resp.json();

        if (!resp.ok || !data.success) {
            const errDetail = data.detail ? (typeof data.detail === 'object' ? JSON.stringify(data.detail) : data.detail) : '';
            const msg = data.error || errDetail || `서버 응답 오류 (${resp.status})`;
            throw new Error(msg);
        }

        currentVideoTaskId = data.task_id;
        startPoemVideoPolling(currentVideoTaskId);

    } catch (e) {
        if (typeof setAppBusy === 'function') {
            setAppBusy(false);
        }
        alert("영상 제작 요청 오류: " + e.message);
        if (btn) btn.disabled = false;
        if (progressArea) progressArea.style.display = "none";
    }
}

// 백그라운드 작업 폴링 (우측으로 움직이는 활동형 진행 애니메이션 & 실시간 100% 도달)
function startPoemVideoPolling(taskId) {
    if (currentVideoPollTimer) clearInterval(currentVideoPollTimer);

    const btn = document.getElementById('btnMakePoemVideo');
    const progressArea = document.getElementById('sidebarVideoProgressArea');
    const progressBar = document.getElementById('sidebarVideoProgressBar');
    const progressStatus = document.getElementById('sidebarVideoProgressStatus');
    const progressPercent = document.getElementById('sidebarVideoProgressPercent');

    let currentVisualPercent = 10;

    // 프론트엔드 활동형 미세 전진 타이머 (렌더링 구간에서 멈추지 않고 우측으로 부드럽게 활동)
    const crawlTimer = setInterval(() => {
        if (currentVisualPercent >= 40 && currentVisualPercent < 88) {
            currentVisualPercent += 0.8;
            const displayVal = Math.round(currentVisualPercent);
            if (progressBar) progressBar.style.width = `${displayVal}%`;
            if (progressPercent) progressPercent.textContent = `${displayVal}%`;
        }
    }, 1200);

    currentVideoPollTimer = setInterval(async () => {
        try {
            const resp = await fetch(`/api/poem_video/task/${taskId}`);
            const res = await resp.json();
            if (!res.success || !res.task) return;

            const task = res.task;
            const serverProgress = task.progress || 0;

            if (serverProgress > currentVisualPercent) {
                currentVisualPercent = serverProgress;
            }

            const displayProgress = Math.round(currentVisualPercent);
            if (progressBar) {
                progressBar.className = "video-progress-fill-active";
                progressBar.style.width = `${displayProgress}%`;
            }
            if (progressPercent) progressPercent.textContent = `${displayProgress}%`;

            if (task.status === "analyzing_audio_sync") {
                if (progressStatus) progressStatus.textContent = "Whisper AI 보컬 싱크 분석 중...";
            } else if (task.status && task.status.startsWith("rendering")) {
                const pctMatch = task.status.match(/\d+%/);
                if (pctMatch) {
                    if (progressStatus) progressStatus.textContent = `고화질 프레임 렌더링 중 (${pctMatch[0]})...`;
                } else {
                    if (progressStatus) progressStatus.textContent = "고화질 프레임 렌더링 중...";
                }
            } else if (task.status === "saving") {
                if (progressStatus) progressStatus.textContent = "완성 영상 프로젝트로 저장 중...";
            } else if (task.status === "complete") {
                clearInterval(currentVideoPollTimer);
                clearInterval(crawlTimer);

                // 100% 꽉 채우고 완료 피드백
                if (progressBar) progressBar.style.width = "100%";
                if (progressPercent) progressPercent.textContent = "100%";
                if (progressStatus) progressStatus.textContent = "✨ 시 낭송 영상 완성!";

                // 마우스 커서 정상 복원
                if (typeof setAppBusy === 'function') {
                    setAppBusy(false);
                }

                if (btn) btn.disabled = false;
                updateSidebarVideoCard();

                setTimeout(() => {
                    alert("🎉 시 낭송 영상이 100% 성공적으로 완성되었습니다!");
                    setTimeout(() => {
                        if (progressArea) progressArea.style.display = "none";
                    }, 1500);
                }, 400);

            } else if (task.status === "error") {
                clearInterval(currentVideoPollTimer);
                clearInterval(crawlTimer);

                if (typeof setAppBusy === 'function') {
                    setAppBusy(false);
                }

                alert("영상 렌더링 오류 발생: " + (task.message || "알 수 없는 오류"));
                if (btn) btn.disabled = false;
                if (progressArea) progressArea.style.display = "none";
            }
        } catch (e) {
            console.warn("폴링 체크 중 오류:", e);
        }
    }, 2000);
}

// 팝업 모달로 영상 감상
function openPoemVideoModal() {
    if (!latestVideoUrl) {
        alert("감상할 영상이 아직 없습니다.");
        return;
    }

    let modal = document.getElementById('poemVideoPlayerModal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'poemVideoPlayerModal';
        modal.style.position = 'fixed';
        modal.style.top = '0';
        modal.style.left = '0';
        modal.style.width = '100vw';
        modal.style.height = '100vh';
        modal.style.backgroundColor = 'rgba(0, 0, 0, 0.85)';
        modal.style.display = 'flex';
        modal.style.flexDirection = 'column';
        modal.style.justifyContent = 'center';
        modal.style.alignItems = 'center';
        modal.style.zIndex = '99999';

        modal.innerHTML = `
            <div style="position: relative; width: 90%; max-width: 960px; background: #111; border-radius: 12px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; background: #222; color: #FFF;">
                    <span style="font-weight: 700; font-size: 1rem;">🎬 StoryBook 시 낭송 영상 플레이어</span>
                    <button onclick="closePoemVideoModal()" style="background: none; border: none; color: #FFF; font-size: 1.5rem; cursor: pointer;">&times;</button>
                </div>
                <div style="position: relative; padding-bottom: 56.25%; height: 0; background: #000;">
                    <video id="poemVideoPlayerElement" controls autoplay style="position: absolute; top:0; left:0; width: 100%; height: 100%;">
                        <source src="" type="video/mp4">
                        브라우저가 비디오 재생을 지원하지 않습니다.
                    </video>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }

    const videoEl = document.getElementById('poemVideoPlayerElement');
    if (videoEl) {
        videoEl.src = latestVideoUrl;
        videoEl.load();
        videoEl.play();
    }
    modal.style.display = 'flex';
}

function closePoemVideoModal() {
    const modal = document.getElementById('poemVideoPlayerModal');
    if (modal) {
        const videoEl = document.getElementById('poemVideoPlayerElement');
        if (videoEl) {
            videoEl.pause();
            videoEl.src = "";
        }
        modal.style.display = 'none';
    }
}

// 영상 제작 탭 내 회차 선택 드롭다운 채우기
async function populateVideoWorkSelect() {
    const videoSelect = document.getElementById('videoWorkSelect');
    if (!videoSelect) return;

    let works = [];
    if (window.currentStatus && window.currentStatus.works && window.currentStatus.works.length > 0) {
        works = window.currentStatus.works;
    } else {
        const mainSelect = document.getElementById('selectWorkToEdit');
        if (mainSelect && mainSelect.options.length > 1) {
            for (let i = 0; i < mainSelect.options.length; i++) {
                const opt = mainSelect.options[i];
                if (opt.value && opt.value !== 'new') {
                    const epDigits = String(opt.value).replace(/[^0-9]/g, '');
                    const epNum = epDigits ? parseInt(epDigits, 10) : i;
                    works.push({ episode_no: `제${epNum < 10 ? '0' + epNum : epNum}화`, title: opt.textContent.replace(/^.*?\]\s*/, '') });
                }
            }
        }
    }

    // 그래도 비어있다면 API에서 직접 fetch
    if (works.length === 0) {
        try {
            const resp = await fetch('/api/status');
            const data = await resp.json();
            if (data.success && data.works) {
                works = data.works;
            }
        } catch (e) {
            console.warn("works fetch 실패:", e);
        }
    }

    if (works.length > 0) {
        videoSelect.innerHTML = "";
        works.forEach(w => {
            const epDigits = String(w.episode_no).replace(/[^0-9]/g, '');
            const epNum = epDigits ? parseInt(epDigits, 10) : 1;
            const opt = document.createElement('option');
            opt.value = String(epNum);
            opt.textContent = `📖 [${w.episode_no}] ${w.title || ''}`;
            videoSelect.appendChild(opt);
        });

        const targetEp = currentVideoSelectedEpisode || getCurrentEpisodeNo();
        if (targetEp) {
            for (let i = 0; i < videoSelect.options.length; i++) {
                const optNum = parseInt(videoSelect.options[i].value, 10);
                if (optNum === targetEp) {
                    videoSelect.selectedIndex = i;
                    break;
                }
            }
        }
    }
}

// 회차 선택기 변경 시 즉시 상태 갱신
function onVideoWorkSelectChange(val) {
    if (!val) return;
    const epNum = parseInt(String(val).replace(/[^0-9]/g, ''), 10);
    if (!isNaN(epNum) && epNum > 0) {
        currentVideoSelectedEpisode = epNum;
        updateSidebarVideoCard(epNum);
    }
}

// DOMContentLoaded 시 초기화 및 화 전환 감지 리스너 등록
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(async () => {
        await populateVideoWorkSelect();
        updateSidebarVideoCard();
        onVideoAudioSourceChange();
    }, 400);

    // 영상 탭 버튼 클릭 시 회차 목록 및 상태 즉각 동기화
    const tabBtnVideo = document.getElementById('tabBtnVideo');
    if (tabBtnVideo) {
        tabBtnVideo.addEventListener('click', async () => {
            await populateVideoWorkSelect();
            updateSidebarVideoCard();
        });
    }

    // 창작 탭에서 사용자가 명시적으로 다른 작품을 선택한 경우에만 영상 탭에도 반영
    const selectWork = document.getElementById('selectWorkToEdit');
    if (selectWork) {
        selectWork.addEventListener('change', (e) => {
            const val = e.target.value;
            if (val && val !== 'new') {
                const cleaned = String(val).replace(/[^0-9]/g, '');
                if (cleaned) {
                    const epNum = parseInt(cleaned, 10);
                    currentVideoSelectedEpisode = epNum;
                    updateSidebarVideoCard(epNum);
                }
            }
        });
    }
});


// 시화집 전편 플레이리스트 영상 무손실 초고속 결합
async function requestMergePlaylist() {
    const project = getActiveProjectName();
    const ratioRadio = document.querySelector('input[name="videoAspectRatio"]:checked');
    const aspectRatio = ratioRadio ? ratioRadio.value : '16:9';

    const btn = document.getElementById('btnMergePlaylist');
    const statusEl = document.getElementById('playlistMergeStatus');

    if (btn) btn.disabled = true;
    if (statusEl) {
        statusEl.style.display = 'block';
        statusEl.style.color = '#B87333';
        statusEl.textContent = '전편 영상들을 무손실 결합하는 중...';
    }

    try {
        const resp = await fetch('/api/poem_video/merge_playlist', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                project_name: project,
                aspect_ratio: aspectRatio
            })
        });

        const res = await resp.json();
        if (res.success) {
            if (statusEl) {
                statusEl.style.color = '#2B7A4B';
                statusEl.innerHTML = `✓ ${res.count}개 영상 결합 완료! <a href="/api/poem_video/stream/${encodeURIComponent(project)}/${encodeURIComponent(res.output_filename)}" download style="color:#7A5335;text-decoration:underline;font-weight:700;margin-left:6px;">[MP4 받기 (${res.size_mb}MB)]</a>`;
            }
            alert(`시화집 전편 ${res.count}편 영상이 성공적으로 결합되었습니다!\n파일명: ${res.output_filename} (${res.size_mb}MB)`);
        } else {
            throw new Error(res.error || '영상 결합에 실패했습니다.');
        }
    } catch (e) {
        if (statusEl) {
            statusEl.style.color = '#C53030';
            statusEl.textContent = `결합 실패: ${e.message}`;
        }
        alert(`플레이리스트 결합 오류: ${e.message}`);
    } finally {
        if (btn) btn.disabled = false;
    }
}


// =========================================================================
// 🎵 서정 노래 영상 (Song Video) 프론트엔드 제어 로직
// =========================================================================

let currentSongVideoTaskId = null;
let currentSongVideoPollTimer = null;
let latestSongVideoUrl = null;
let customSongAudioUploadedPath = null;

// 노래 영상 화면 비율 선택 반응
function handleSongAspectRatioChange(ratio) {
    const lbl16 = document.getElementById('songOptLabel16x9');
    const lbl9 = document.getElementById('songOptLabel9x16');
    if (!lbl16 || !lbl9) return;
    if (ratio === '9:16') {
        lbl9.style.borderColor = '#2B4B6F';
        lbl9.style.background = '#EDF4FB';
        lbl9.style.color = '#1B3550';
        lbl9.style.fontWeight = '700';
        lbl16.style.borderColor = '#BACEDF';
        lbl16.style.background = '#FFF';
        lbl16.style.color = '#4A637D';
        lbl16.style.fontWeight = '600';
    } else {
        lbl16.style.borderColor = '#2B4B6F';
        lbl16.style.background = '#EDF4FB';
        lbl16.style.color = '#1B3550';
        lbl16.style.fontWeight = '700';
        lbl9.style.borderColor = '#BACEDF';
        lbl9.style.background = '#FFF';
        lbl9.style.color = '#4A637D';
        lbl9.style.fontWeight = '600';
    }
}

// [Intro], [Verse], [Chorus] 등 가사 외 설명 문구 자동 정제 필터 (Suno 복사 가사 최적화)
function cleanLyricsMetaTags() {
    const textarea = document.getElementById('songLyricsTextarea');
    if (!textarea) return;
    const originalText = textarea.value;
    if (!originalText.trim()) {
        alert("정제할 가사 텍스트가 없습니다. 먼저 가사를 입력하거나 붙여넣어 주세요.");
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
    textarea.value = resultText;
    textarea.focus();

    if (removedCount > 0) {
        alert(`🧹 [Intro], [Chorus] 등 가사 외 설명어 ${removedCount}개를 깔끔하게 삭제하고 순수 가사만 정제했습니다!`);
    } else {
        alert("가사에 별도의 설명 태그가 없거나 이미 깔끔하게 정제된 상태입니다.");
    }
}

// 시 원문에서 가사 본문 불러오기
function syncLyricsFromPoem() {
    const poemTextarea = document.getElementById('textareaPoemBody');
    const targetTextarea = document.getElementById('songLyricsTextarea');
    if (poemTextarea && targetTextarea) {
        const val = poemTextarea.value.trim();
        if (val) {
            targetTextarea.value = val;
            targetTextarea.focus();
        } else {
            alert('현재 회차에 작성된 시 원문이 없습니다.');
        }
    }
}

// 노래 음원 직접 업로드 변경
async function handleSongAudioFileSelected(input) {
    if (!input.files || input.files.length === 0) return;
    const file = input.files[0];
    let ep = getCurrentEpisodeNo();
    if (!ep || isNaN(ep)) ep = 11;

    const project = getActiveProjectName();
    const nameEl = document.getElementById('songAudioFileName');
    if (nameEl) {
        nameEl.textContent = `업로드 중: ${file.name}...`;
        nameEl.style.color = "#2B4B6F";
    }

    const formData = new FormData();
    formData.append('project_name', project);
    formData.append('episode_no', String(ep));
    formData.append('audio_file', file);

    try {
        const resp = await fetch('/api/poem_video/upload_custom_audio', {
            method: 'POST',
            body: formData
        });
        const res = await resp.json();
        if (res.success) {
            customSongAudioUploadedPath = res.path;
            if (nameEl) {
                nameEl.textContent = `✓ ${res.filename} (${Math.round(res.size_bytes / 1024)}KB)`;
                nameEl.style.color = "#2B7A4B";
            }
            alert(`노래 음원 파일이 제${ep}화 공식 노래 음원으로 등록되었습니다!`);
            updateSidebarSongVideoCard(ep);
        } else {
            alert("노래 음원 등록 실패: " + (res.error || "알 수 없는 오류"));
        }
    } catch (e) {
        alert("업로드 중 네트워크 오류가 발생했습니다: " + e.message);
    }
}

// 노래 영상 상태 카드 업데이트
async function updateSidebarSongVideoCard(episodeNo) {
    let ep = episodeNo;
    if (typeof ep === 'string') {
        const cleaned = ep.replace(/[^0-9]/g, '');
        ep = cleaned ? parseInt(cleaned, 10) : null;
    }
    if (!ep || isNaN(ep)) ep = getCurrentEpisodeNo();
    if (!ep || isNaN(ep)) ep = 11;

    const project = getActiveProjectName();

    try {
        const resp = await fetch(`/api/song_video/status/${encodeURIComponent(project)}/${ep}`);
        const data = await resp.json();

        const badge = document.getElementById('songVideoBadge');
        const audioNameEl = document.getElementById('songAudioFileName');
        const audioBadgeEl = document.getElementById('songAudioStatusBadge');
        const lyricsTextarea = document.getElementById('songLyricsTextarea');
        const actionArea = document.getElementById('songVideoActionArea');
        const dlLink = document.getElementById('songVideoDownloadLink');
        const inlineContainer = document.getElementById('songVideoInlinePlayerContainer');
        const inlinePlayer = document.getElementById('songVideoInlinePlayer');

        if (audioNameEl) {
            if (data.detected_audio) {
                audioNameEl.textContent = data.detected_audio;
                audioNameEl.style.color = '#2B4B6F';
                if (audioBadgeEl) {
                    audioBadgeEl.textContent = '자동 연결됨';
                    audioBadgeEl.style.background = '#E8F5E9';
                    audioBadgeEl.style.color = '#2B7A4B';
                }
            } else {
                audioNameEl.textContent = '노래 음원 없음 (작곡/Suno 음원 필요)';
                audioNameEl.style.color = '#C53030';
                if (audioBadgeEl) {
                    audioBadgeEl.textContent = '음원 필요';
                    audioBadgeEl.style.background = '#FFEBEE';
                    audioBadgeEl.style.color = '#C53030';
                }
            }
        }

        // 가사 본문 채우기 (기존 입력값이 없을 때만 초기화)
        if (lyricsTextarea && !lyricsTextarea.value.trim() && data.lyrics) {
            lyricsTextarea.value = data.lyrics;
        }

        // 완성된 비디오 확인
        if (data.video && data.video.exists) {
            latestSongVideoUrl = data.video.url;
            if (badge) {
                badge.textContent = '제작완료';
                badge.style.background = '#E8F5E9';
                badge.style.color = '#2B7A4B';
            }
            if (actionArea) actionArea.style.display = 'flex';
            if (dlLink) {
                dlLink.href = data.video.url;
                dlLink.download = data.video.filename;
            }
            if (inlineContainer && inlinePlayer) {
                inlineContainer.style.display = 'block';
                inlinePlayer.src = data.video.url;
            }
        } else {
            latestSongVideoUrl = null;
            if (badge) {
                badge.textContent = '미제작';
                badge.style.background = '#EEE';
                badge.style.color = '#666';
            }
            if (actionArea) actionArea.style.display = 'none';
            if (inlineContainer) inlineContainer.style.display = 'none';
        }

    } catch (e) {
        console.error("노래 영상 상태 조회 실패:", e);
    }
}

// 노래 영상 제작 요청
async function requestSongVideoRender() {
    let ep = getCurrentEpisodeNo();
    if (!ep || isNaN(ep)) ep = 11;

    const project = getActiveProjectName();

    const lyricsTextarea = document.getElementById('songLyricsTextarea');
    const lyricsText = lyricsTextarea ? lyricsTextarea.value.trim() : '';

    if (!lyricsText) {
        alert('노래 가사를 입력해 주세요. (우측 상단의 [시 원문 가져오기]를 누르시면 시 원고가 자동으로 채워집니다)');
        if (lyricsTextarea) lyricsTextarea.focus();
        return;
    }

    const ratioRadio = document.querySelector('input[name="songVideoAspectRatio"]:checked');
    const aspectRatio = ratioRadio ? ratioRadio.value : '16:9';

    const specSelect = document.getElementById('selectSongSpectrumStyle');
    const spectrumStyle = specSelect ? specSelect.value : 'mirror';

    const lyricModeSelect = document.getElementById('selectSongLyricMode');
    const lyricMode = lyricModeSelect ? lyricModeSelect.value : 'focus2line';

    const btn = document.getElementById('btnMakeSongVideo');
    const progressArea = document.getElementById('songVideoProgressArea');
    const progressBar = document.getElementById('songVideoProgressBar');
    const progressStatus = document.getElementById('songVideoProgressStatus');
    const progressPercent = document.getElementById('songVideoProgressPercent');

    if (btn) btn.disabled = true;
    if (progressArea) progressArea.style.display = "block";
    if (progressBar) {
        progressBar.className = "video-progress-fill-active";
        progressBar.style.width = "10%";
    }
    if (progressStatus) progressStatus.textContent = "노래 영상 제작 준비 중...";
    if (progressPercent) progressPercent.textContent = "10%";

    if (typeof setAppBusy === 'function') {
        setAppBusy(true, "서정 노래 뮤직비디오 제작 중...");
    }

    try {
        const payload = {
            project_name: project,
            episode_no: ep,
            lyrics_text: lyricsText,
            custom_audio_path: customSongAudioUploadedPath || null,
            aspect_ratio: aspectRatio,
            spectrum_style: spectrumStyle,
            lyric_mode: lyricMode
        };

        const resp = await fetch('/api/song_video/render', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        const data = await resp.json();

        if (!resp.ok || !data.success) {
            const errDetail = data.detail ? (typeof data.detail === 'object' ? JSON.stringify(data.detail) : data.detail) : '';
            const msg = data.error || errDetail || `서버 응답 오류 (${resp.status})`;
            throw new Error(msg);
        }

        currentSongVideoTaskId = data.task_id;
        startSongVideoPolling(currentSongVideoTaskId);

    } catch (e) {
        if (typeof setAppBusy === 'function') {
            setAppBusy(false);
        }
        alert("노래 영상 제작 요청 오류: " + e.message);
        if (btn) btn.disabled = false;
        if (progressArea) progressArea.style.display = "none";
    }
}

// 노래 영상 백그라운드 폴링
function startSongVideoPolling(taskId) {
    if (currentSongVideoPollTimer) clearInterval(currentSongVideoPollTimer);

    const btn = document.getElementById('btnMakeSongVideo');
    const progressArea = document.getElementById('songVideoProgressArea');
    const progressBar = document.getElementById('songVideoProgressBar');
    const progressStatus = document.getElementById('songVideoProgressStatus');
    const progressPercent = document.getElementById('songVideoProgressPercent');

    let currentVisualPercent = 10;

    const crawlTimer = setInterval(() => {
        if (currentVisualPercent >= 40 && currentVisualPercent < 88) {
            currentVisualPercent += 0.8;
            const displayVal = Math.round(currentVisualPercent);
            if (progressBar) progressBar.style.width = `${displayVal}%`;
            if (progressPercent) progressPercent.textContent = `${displayVal}%`;
        }
    }, 1200);

    currentSongVideoPollTimer = setInterval(async () => {
        try {
            const resp = await fetch(`/api/poem_video/task/${taskId}`);
            const res = await resp.json();
            if (!res.success || !res.task) return;

            const task = res.task;
            const serverProgress = task.progress || 0;

            if (serverProgress > currentVisualPercent) {
                currentVisualPercent = serverProgress;
            }

            const displayProgress = Math.round(currentVisualPercent);
            if (progressBar) {
                progressBar.className = "video-progress-fill-active";
                progressBar.style.width = `${displayProgress}%`;
            }
            if (progressPercent) progressPercent.textContent = `${displayProgress}%`;

            if (task.status === "analyzing_audio_sync") {
                if (progressStatus) progressStatus.textContent = "노랫말 보컬 싱크(Whisper AI) 분석 중...";
            } else if (task.status && task.status.startsWith("rendering")) {
                const pctMatch = task.status.match(/\d+%/);
                if (pctMatch) {
                    if (progressStatus) progressStatus.textContent = `고화질 뮤직비디오 렌더링 중 (${pctMatch[0]})...`;
                } else {
                    if (progressStatus) progressStatus.textContent = "고화질 뮤직비디오 렌더링 중...";
                }
            } else if (task.status === "saving") {
                if (progressStatus) progressStatus.textContent = "완성 영상 프로젝트로 저장 중...";
            } else if (task.status === "complete") {
                clearInterval(currentSongVideoPollTimer);
                clearInterval(crawlTimer);

                if (progressBar) progressBar.style.width = "100%";
                if (progressPercent) progressPercent.textContent = "100%";
                if (progressStatus) progressStatus.textContent = "✨ 서정 노래 뮤직비디오 완성!";

                if (typeof setAppBusy === 'function') {
                    setAppBusy(false);
                }

                setTimeout(() => {
                    if (progressArea) progressArea.style.display = "none";
                    if (btn) btn.disabled = false;
                    let ep = getCurrentEpisodeNo();
                    updateSidebarSongVideoCard(ep);
                }, 1200);

            } else if (task.status === "error") {
                clearInterval(currentSongVideoPollTimer);
                clearInterval(crawlTimer);
                if (typeof setAppBusy === 'function') {
                    setAppBusy(false);
                }
                if (progressStatus) progressStatus.textContent = `오류: ${task.message || '렌더링 실패'}`;
                alert(`노래 영상 제작 실패: ${task.message || '알 수 없는 오류'}`);
                if (btn) btn.disabled = false;
            }

        } catch (e) {
            console.error("노래 영상 폴링 에러:", e);
        }
    }, 1500);
}

// 노래 비디오 전체화면 모달 오픈
function openSongVideoModal() {
    if (!latestSongVideoUrl) {
        alert("재생할 노래 영상이 없습니다.");
        return;
    }
    const modal = document.getElementById('poemVideoModal');
    const modalPlayer = document.getElementById('poemVideoModalPlayer');
    if (modal && modalPlayer) {
        modalPlayer.src = latestSongVideoUrl;
        modal.style.display = 'flex';
        modalPlayer.play().catch(() => {});
    }
}


// -------------------------------------------------------------
// 🎙️ 시화 낭송 음원 트랙 선택 및 인라인 미리듣기 제어
// -------------------------------------------------------------
window.selectedPoemVideoAudioPath = null;
let currentRecitePreviewBtn = null;

function onSelectPoemVideoTrack(relPath) {
    window.selectedPoemVideoAudioPath = relPath;
    const labels = document.querySelectorAll('#videoReciteTracksList label');
    labels.forEach(l => {
        const radio = l.querySelector('input[type="radio"]');
        if (radio && radio.checked) {
            l.style.background = '#FFF9F2';
            l.style.borderColor = '#7A5335';
        } else {
            l.style.background = '#FFFFFF';
            l.style.borderColor = '#EFE8DE';
        }
    });
}

function toggleVideoRecitePreview(url, btn, event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    const audioEl = document.getElementById('videoRecitePreviewAudio');
    if (!audioEl) return;

    if (currentRecitePreviewBtn === btn && !audioEl.paused) {
        audioEl.pause();
        onVideoRecitePreviewEnded();
        return;
    }

    if (currentRecitePreviewBtn && currentRecitePreviewBtn !== btn) {
        onVideoRecitePreviewEnded();
    }

    currentRecitePreviewBtn = btn;
    btn.innerHTML = `<span>⏸</span> <span>정지</span>`;
    btn.style.background = '#FED7AA';
    btn.style.borderColor = '#F97316';
    btn.style.color = '#9A3412';

    const bustUrl = url.includes('?') ? url : `${url}?t=${Date.now()}`;
    audioEl.src = bustUrl;
    audioEl.play().catch(e => {
        console.warn('낭송 미리듣기 오류:', e);
        onVideoRecitePreviewEnded();
    });
}

function onVideoRecitePreviewEnded() {
    const audioEl = document.getElementById('videoRecitePreviewAudio');
    if (audioEl) audioEl.pause();
    if (currentRecitePreviewBtn) {
        currentRecitePreviewBtn.innerHTML = `<span>▶</span> <span>듣기</span>`;
        currentRecitePreviewBtn.style.background = '#FAF7F2';
        currentRecitePreviewBtn.style.borderColor = '#D8C8B8';
        currentRecitePreviewBtn.style.color = '#5A4A3E';
        currentRecitePreviewBtn = null;
    }
}
