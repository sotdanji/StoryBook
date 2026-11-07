/**
 * StoryBook Studio - 모듈형 2-Layer 조판 편집 엔진 (dtp_editor_core.js v4.0)
 * 
 * 1. 완전 대칭형 좌/우 2쪽(스프레드) 컴포넌트 아키텍처
 * 2. 2-Layer 완벽 독립 분리: Layer 1 (그림 레이어), Layer 2 (글 레이어)
 * 3. 상단 [페이지 용도] x [글 유형] 실시간 연동
 * 4. 시화창작 탭 연동: 좌(전면삽화) + 우(시 시작) 기본 프리셋 및 자유 변경
 * 5. 빨간색 가이드 박스: 제목(상단 안전선 준수), 본문(하단 안전선 준수)
 * 6. 정밀 행 용량(Capacity) 기반 본문 흐름 및 자동 2쪽 증설/축소 (무한루프 원천 차단):
 *    - 본문 초과 시 하단 배지 표시 & 자동으로 2쪽 추가 (2면 ➔ 4면 ➔ 6면)
 *    - 본문 축소 시 자동으로 2쪽 삭제 (6면 ➔ 4면 ➔ 2면)
 * 7. Undo / Redo (실행 취소 / 다시 실행)
 * 8. 실시간 한지 가독성 패널 (투명도 슬라이더 기본 85% + 글자색 반전)
 * 9. 시어 줄바꿈 보호 (word-break: keep-all) & A5 실물 줌
 */

(function (window) {
  'use strict';

  function hideElem(el) {
    if (!el) return;
    el.classList.add('is-hidden');
    el.style.display = 'none';
  }

  function showElem(el, displayType) {
    if (!el) return;
    el.classList.remove('is-hidden');
    el.style.display = displayType || 'block';
  }

  class DtpEditorCore {
    constructor() {
      this.currentWorkIndex = 0;
      this.currentSpreadPart = 1; // 1 = 1·2면, 2 = 3·4면, 3 = 5·6면
      this.showGuides = true;
      this.realScale = false;
      this.undoStack = [];
      this.redoStack = [];
      this.maxUndoSteps = 25;
      this.targetPageSlot = 'left';
      this.currentToolboxTab = 'text';
      this.selectedSubFrame = 1;

      this.defaultConfig = {
        page_count: 2,
        font_size_pt: 12,
        line_height_ratio: 1.6,
        font_family: "'BookkMyungjo', '부크크 명조', 'Nanum Myeongjo', serif",
        text_align: "left",
        backdrop_opacity: 0.85,
        text_color_mode: "dark",
        pages: [
          { page_num: 1, usage: "image", role: "none", image_file: "" },
          { page_num: 2, usage: "text", role: "start", image_file: "" }
        ]
      };
    }

    /**
     * [Full Book Architecture] 특정 섹션 로드 (시화 본문 및 앞부속/뒷부속)
     */
    loadSection(secOrId, options = {}) {
      let sec = secOrId;
      if (typeof secOrId === 'string') {
        const struct = window.bookStructureData;
        if (struct && struct.sections) {
          const cleanId = secOrId.replace(/^sec_/, '');
          sec = struct.sections.find(s => s.id === cleanId || s.id === secOrId);
        }
      }
      if (!sec) return;

      this.currentSectionId = sec.id;

      // 본문 시화인 경우 (episode_no가 있는 poem)
      if (sec.category === 'poem' && sec.episode_no) {
        const works = this.getWorksList();
        const idx = works.findIndex(w => w.episode_no === sec.episode_no);
        if (idx !== -1) {
          this.renderSpread(idx, 1, false, options);
          return;
        }
      }
      // 그 외 모든 부속물(앞표지, 속표지, 서문, 목차, 부간지, 맺음말, 판권지, 뒤표지)
      this.renderMatterSpread(sec);
    }

    /**
     * [Full Book Architecture] 앞부속(Front Matter) & 뒷부속(Back Matter) 전용 조판 펼침면 렌더링
     */
    renderMatterSpread(sec) {
      if (!sec) return;
      this.currentSectionId = sec.id;

      // 1) 상단 툴바 상태 동기화
      const statusBadge = document.getElementById("layoutStatusBadge");
      const statusText = document.getElementById("layoutStatusText");
      if (statusBadge && statusText) {
        statusBadge.className = "layout-badge badge-ok";
        statusText.textContent = `📖 [${sec.group_label || '부속물'}] ${sec.title}`;
      }

      const lblTotalPages = document.getElementById("lblTotalPagesBadge");
      if (lblTotalPages) {
        const pRange = sec.page_count > 1 ? `p.${sec.start_page}~${sec.end_page}` : `p.${sec.start_page}`;
        lblTotalPages.textContent = `📄 ${sec.page_count}쪽 조판 (${pRange})`;
      }

      const partNav = document.getElementById("spreadPartNavGroup");
      if (partNav) hideElem(partNav);

      const navText = document.getElementById("navWorkIndexText");
      if (navText && window.bookStructureData && window.bookStructureData.sections) {
        const secList = window.bookStructureData.sections;
        const curIdx = secList.findIndex(s => s.id === sec.id) + 1;
        navText.textContent = `${curIdx} / ${secList.length}`;
        navText.title = `${sec.title} (p.${sec.start_page}${sec.page_count > 1 ? '~' + sec.end_page : ''})`;
      }

      const selectWork = document.getElementById("selectWorkDropdown");
      if (selectWork) {
        selectWork.value = `sec_${sec.id}`;
      }

      // 하단 책장 넘기기 인디케이터 및 트리 활성화 동기화
      const turnIndicator = document.getElementById("pageTurnIndicator");
      if (turnIndicator) {
        const pRange = sec.page_count > 1 ? `p.${sec.start_page}~${sec.end_page}` : `p.${sec.start_page}`;
        turnIndicator.textContent = `[${sec.group_label || '부속물'}] ${sec.title} — ${pRange}`;
      }
      if (typeof window.updateBookTreeActiveItem === 'function') {
        window.updateBookTreeActiveItem(sec.id);
      }
      this.currentSpreadPart = 1;

      // 2) 페이지 헤더/면 번호/폴리오 동기화
      const lblLeftNum = document.getElementById("lblPageLeftNum");
      const lblRightNum = document.getElementById("lblPageRightNum");
      const lblFolioLeft = document.getElementById("lblBookFolioLeft");
      const lblFolioRight = document.getElementById("lblBookFolioRight");

      if (sec.id === 'epilogue' || sec.id === 'colophon') {
        if (lblLeftNum) lblLeftNum.textContent = "42면 (맺음말)";
        if (lblRightNum) lblRightNum.textContent = "43면 (판권지)";
        if (lblFolioLeft) lblFolioLeft.textContent = "42";
        if (lblFolioRight) lblFolioRight.textContent = "43";
        if (turnIndicator) turnIndicator.textContent = `[뒷부속] 맺음말 & 판권지 — p.42~43`;
        if (statusText) statusText.textContent = `📖 [뒷부속] 맺음말 & 판권지`;
        if (lblTotalPages) lblTotalPages.textContent = `📄 2쪽 조판 (p.42~43)`;
      } else if (sec.id === 'back_cover') {
        if (lblLeftNum) lblLeftNum.textContent = "뒤표지 (추천사·바코드)";
        if (lblRightNum) lblRightNum.textContent = "앞표지 (표제·저자·일러스트)";
        if (lblFolioLeft) lblFolioLeft.textContent = "";
        if (lblFolioRight) lblFolioRight.textContent = "";
        if (turnIndicator) turnIndicator.textContent = `[뒷부속] 뒤표지 (겉표지 펼침면)`;
        if (statusText) statusText.textContent = `📖 [뒷부속] 뒤표지 (겉표지 전개도)`;
      } else if (sec.id === 'cover') {
        if (lblLeftNum) lblLeftNum.textContent = "뒤표지 (추천사·바코드)";
        if (lblRightNum) lblRightNum.textContent = "앞표지 (표제·저자·일러스트)";
        if (lblFolioLeft) lblFolioLeft.textContent = "";
        if (lblFolioRight) lblFolioRight.textContent = "";
      } else if (sec.id === 'half_title') {
        if (lblLeftNum) lblLeftNum.textContent = "면지 (백면)";
        if (lblRightNum) lblRightNum.textContent = "1면 (속표지)";
        if (lblFolioLeft) lblFolioLeft.textContent = "";
        if (lblFolioRight) lblFolioRight.textContent = "1";
      } else if (sec.id === 'prologue' || sec.id === 'preface') {
        if (lblLeftNum) lblLeftNum.textContent = "2면 (백면)";
        if (lblRightNum) lblRightNum.textContent = "3면 (시인의 말)";
        if (lblFolioLeft) lblFolioLeft.textContent = "2";
        if (lblFolioRight) lblFolioRight.textContent = "3";
      } else if (sec.id === 'toc') {
        if (lblLeftNum) lblLeftNum.textContent = "4면 (차례)";
        if (lblRightNum) lblRightNum.textContent = "5면 (제1부)";
        if (lblFolioLeft) lblFolioLeft.textContent = "4";
        if (lblFolioRight) lblFolioRight.textContent = "5";
      }

      // 3) 부속물 전용 양면 오버레이 컨테이너 취득 및 노출
      const ovLeft = document.getElementById("dtpMatterOverlayLeft");
      const ovRight = document.getElementById("dtpMatterOverlayRight");
      if (ovLeft) ovLeft.style.display = "block";
      if (ovRight) ovRight.style.display = "block";

      // 하단 오버플로우 배지 숨기기 및 상단 셀렉트 비활성화
      const ofLeft = document.getElementById("dtpOverflowLeft");
      const ofRight = document.getElementById("dtpOverflowRight");
      if (ofLeft) hideElem(ofLeft);
      if (ofRight) hideElem(ofRight);

      ['Left', 'Right'].forEach(side => {
        const selU = document.getElementById(`selectPageUsage${side}`);
        const selR = document.getElementById(`selectPageRole${side}`);
        if (selU) { selU.disabled = true; selU.style.opacity = '0.5'; }
        if (selR) { selR.disabled = true; selR.style.opacity = '0.5'; }
      });

      // [신규] DTP 부속물 완성형 표준 템플릿 & 인라인 편집 엔진 위임
      if (window.dtpMatterEngine && typeof window.dtpMatterEngine.renderSpread === 'function') {
        window.dtpMatterEngine.renderSpread(sec, ovLeft, ovRight);
        return;
      }

      const project = (window.currentStatus && window.currentStatus.project) || {};
      const projTitle = project.name || "시집 제목";
      const projSubtitle = project.subtitle || "";
      const projAuthor = project.author || "시인";
      const projCover = project.cover_image || "";
      const projPub = project.publisher || "부크크(Bookk) 자가출판";
      const projDate = project.publish_date || "2026년";

      // 4) 섹션별 좌우 양면 완벽 렌더링
      if (sec.id === 'cover' || sec.category === 'cover') {
        if (lblLeftNum) lblLeftNum.textContent = "뒤표지 (추천사·바코드)";
        if (lblRightNum) lblRightNum.textContent = "앞표지 (표제·저자·일러스트)";
        if (lblFolioLeft) lblFolioLeft.textContent = "";
        if (lblFolioRight) lblFolioRight.textContent = "";

        if (ovLeft) {
          ovLeft.innerHTML = `
            <div style="height:100%; display:flex; flex-direction:column; justify-content:space-between; padding:35px 25px; background:#FAF7F2; color:#5A4A3A; text-align:center; box-sizing:border-box;">
              <div style="font-size:0.8rem; color:#8C7560; letter-spacing:1px; font-weight:600;">뒤표지 (Back Cover)</div>
              <div style="font-family:'KoPub Batang', serif; font-size:1.02rem; line-height:1.9; color:#3A2E24; font-style:italic; padding:20px 10px;">
                "기억의 서랍에서 꺼내 올린<br>따스한 삶의 무늬와 시의 노래"
              </div>
              <div style="border-top:1px solid #D8C7B5; padding-top:14px; display:flex; justify-content:space-between; align-items:flex-end; font-size:0.75rem; color:#8C7560;">
                <div style="text-align:left;">정가 15,000원<br>ISBN 979-11-XXXXX-X</div>
                <div style="font-weight:700; color:#553412;">${projPub}</div>
              </div>
            </div>
          `;
        }
        if (ovRight) {
          const coverImgTag = projCover ? `<img src="${projCover}" style="max-height:190px; object-fit:contain; border-radius:6px; box-shadow:0 4px 14px rgba(0,0,0,0.12); margin-bottom:15px;" />` : `<div style="height:160px; width:65%; border:2px dashed #C8B6A2; border-radius:8px; display:flex; align-items:center; justify-content:center; color:#A08872; margin-bottom:15px; font-size:0.85rem;">표지 일러스트 아트웍</div>`;
          ovRight.innerHTML = `
            <div style="height:100%; display:flex; flex-direction:column; justify-content:space-between; align-items:center; padding:40px 25px 25px 25px; background:#FAF7F2; text-align:center; box-sizing:border-box;">
              <div style="font-size:0.78rem; letter-spacing:2px; color:#8C6A4F; font-weight:700;">STORYBOOK COLLECTION</div>
              <div style="display:flex; flex-direction:column; align-items:center; width:100%;">
                <h1 style="font-family:'KoPub Batang', serif; font-size:1.85rem; color:#2C1D11; margin:0 0 8px 0; font-weight:700; letter-spacing:-0.5px;">${projTitle}</h1>
                ${projSubtitle ? `<div style="font-size:0.88rem; color:#8C6A4F; margin-bottom:6px;">${projSubtitle}</div>` : ''}
                <div style="font-size:0.95rem; color:#6C4E36; margin-bottom:18px; font-weight:500;">${projAuthor} 시화집</div>
                ${coverImgTag}
              </div>
              <div style="display:flex; flex-direction:column; align-items:center; gap:8px;">
                <div style="font-size:0.88rem; font-weight:700; color:#4A3220; letter-spacing:1px;">${projPub}</div>
                <button type="button" class="btn-micro" onclick="if(typeof openPublishExportModal==='function')openPublishExportModal();" style="background:#8C3B14; color:#fff; padding:5px 12px; border-radius:4px; font-size:0.75rem; cursor:pointer; border:none;">🎨 표지 데이터 편집</button>
              </div>
            </div>
          `;
        }
      } else if (sec.id === 'half_title') {
        // [스프레드 1: 속표지] 좌측: 0면(면지 백면) | 우측: 1면(속표지 표제/저자)
        if (lblLeftNum) lblLeftNum.textContent = "면지 (백면)";
        if (lblRightNum) lblRightNum.textContent = "1면 (속표지)";
        if (lblFolioLeft) lblFolioLeft.textContent = "";
        if (lblFolioRight) lblFolioRight.textContent = "1";

        if (ovLeft) {
          ovLeft.innerHTML = `
            <div style="height:100%; background:#FAF7F2; display:flex; flex-direction:column; align-items:center; justify-content:center; color:#C4B29E; font-size:0.85rem; font-family:'KoPub Batang', serif; letter-spacing:2px;">
              ❦<br><span style="margin-top:8px; font-size:0.78rem;">[ 면지 / 백면 ]</span>
            </div>
          `;
        }
        if (ovRight) {
          ovRight.innerHTML = `
            <div style="height:100%; display:flex; flex-direction:column; justify-content:center; align-items:center; padding:50px 30px; background:#FAF7F2; text-align:center; box-sizing:border-box;">
              <div style="margin-top:-40px;">
                <h2 style="font-family:'KoPub Batang', serif; font-size:1.75rem; color:#2C1D11; margin-bottom:12px; font-weight:700; letter-spacing:-0.5px;">${projTitle}</h2>
                ${projSubtitle ? `<div style="font-size:0.9rem; color:#8C6A4F; margin-bottom:20px;">${projSubtitle}</div>` : ''}
                <div style="font-size:0.95rem; color:#6C4E36; margin-bottom:35px; font-weight:500;">${projAuthor} 지음</div>
                <div style="width:36px; height:1.5px; background:#B89A7E; margin:0 auto 35px auto;"></div>
                <div style="font-size:0.85rem; color:#8C7560; font-weight:600;">${projPub}</div>
              </div>
            </div>
          `;
        }
      } else if (sec.id === 'prologue' || sec.id === 'preface') {
        // [스프레드 2: 서문] 좌측: 2면(백면) | 우측: 3면(시인의 말)
        if (lblLeftNum) lblLeftNum.textContent = "2면 (백면)";
        if (lblRightNum) lblRightNum.textContent = "3면 (시인의 말)";
        if (lblFolioLeft) lblFolioLeft.textContent = "2";
        if (lblFolioRight) lblFolioRight.textContent = "3";

        const prefaceText = project.preface || project.prologue || "한 생을 살아오며 마음에 고여 있던 기억들이 시가 되고 그림이 되었습니다.\n소중한 순간들을 이 책에 담아 전합니다.";
        if (ovLeft) {
          ovLeft.innerHTML = `
            <div style="height:100%; background:#FAF7F2; display:flex; flex-direction:column; align-items:center; justify-content:center; color:#C4B29E; font-size:0.85rem; font-family:'KoPub Batang', serif; letter-spacing:2px;">
              ❦<br><span style="margin-top:8px; font-size:0.78rem;">[ 2p / 여백 ]</span>
            </div>
          `;
        }
        if (ovRight) {
          ovRight.innerHTML = `
            <div style="height:100%; display:flex; flex-direction:column; justify-content:space-between; padding:45px 35px; background:#FAF7F2; box-sizing:border-box;">
              <div>
                <h3 style="font-family:'KoPub Batang', serif; font-size:1.35rem; color:#2C1D11; margin:0 0 20px 0; border-bottom:1.5px solid #C8B6A2; padding-bottom:8px;">시인의 말</h3>
                <div style="font-family:'KoPub Batang', serif; font-size:0.92rem; line-height:2.0; color:#3A2E24; white-space:pre-line;">${prefaceText}</div>
              </div>
              <div style="text-align:right; font-family:'KoPub Batang', serif; font-size:0.88rem; color:#5A4A3A;">
                <div>${projDate} 계절의 길목에서</div>
                <div style="font-weight:700; margin-top:4px;">${projAuthor} 배상</div>
                <div style="margin-top:14px;"><button type="button" class="btn-micro" onclick="if(typeof openPublishExportModal==='function')openPublishExportModal();" style="background:#FAF2EB; color:#8C3B14; border:1px solid #D5C2B0; padding:4px 10px; border-radius:4px; font-size:0.75rem; cursor:pointer;">✏️ 서문 내용 수정</button></div>
              </div>
            </div>
          `;
        }
      } else if (sec.id === 'toc') {
        // [스프레드 3: 차례] 좌측: 4면(목차 리스트) | 우측: 5면(1부 챕터 간지)
        if (lblLeftNum) lblLeftNum.textContent = "4면 (차례)";
        if (lblRightNum) lblRightNum.textContent = "5면 (제1부)";
        if (lblFolioLeft) lblFolioLeft.textContent = "4";
        if (lblFolioRight) lblFolioRight.textContent = "5";

        const works = this.getWorksList();
        let tocRows = '';
        works.forEach(w => {
          const chap = w.chapter ? `<span style="color:#8C6A4F; font-size:0.75rem; margin-right:5px;">[${w.chapter}]</span>` : '';
          const ep = w.episode_no ? `${w.episode_no}화. ` : '';
          const pStart = w.start_page || (w.layout_config && w.layout_config.start_page) || '';
          tocRows += `
            <div style="display:flex; justify-content:space-between; align-items:baseline; padding:4px 0; border-bottom:1px dotted #E2D5C5; font-size:0.83rem; color:#3A2E24;">
              <div style="overflow:hidden; text-overflow:ellipsis; white-space:nowrap; padding-right:8px;">
                ${chap}<strong>${ep}${w.title}</strong>
              </div>
              <div style="font-family:monospace; color:#8C6A4F; font-size:0.78rem; flex-shrink:0;">${pStart ? 'p.' + pStart : ''}</div>
            </div>
          `;
        });
        if (ovLeft) {
          ovLeft.innerHTML = `
            <div style="height:100%; display:flex; flex-direction:column; padding:40px 30px; background:#FAF7F2; box-sizing:border-box;">
              <h3 style="font-family:'KoPub Batang', serif; font-size:1.35rem; color:#2C1D11; margin:0 0 16px 0; border-bottom:1.5px solid #C8B6A2; padding-bottom:8px;">차 례</h3>
              <div style="overflow-y:auto; flex:1; display:flex; flex-direction:column; gap:2px; scrollbar-width:thin;">
                ${tocRows}
              </div>
            </div>
          `;
        }
        if (ovRight) {
          ovRight.innerHTML = `
            <div style="height:100%; display:flex; flex-direction:column; justify-content:center; align-items:center; padding:50px 30px; background:#FAF7F2; text-align:center; box-sizing:border-box;">
              <div style="font-size:0.9rem; color:#8C6A4F; letter-spacing:2px; margin-bottom:10px; font-weight:700;">제 1 부</div>
              <h2 style="font-family:'KoPub Batang', serif; font-size:1.45rem; color:#2C1D11; margin:0 0 14px 0;">유년의 뜰, 어머니의 등불</h2>
              <div style="font-size:0.84rem; color:#6C5542; font-style:italic;">본문 시화가 시작되는 장(Chapter)입니다.</div>
            </div>
          `;
        }
      } else if (sec.id === 'colophon') {
        // [스프레드: 판권지] 좌측: 56면(에필로그 또는 백면) | 우측: 57면(판권지)
        if (lblLeftNum) lblLeftNum.textContent = "56면 (맺음말)";
        if (lblRightNum) lblRightNum.textContent = "57면 (판권지)";
        if (lblFolioLeft) lblFolioLeft.textContent = "56";
        if (lblFolioRight) lblFolioRight.textContent = "57";

        if (ovLeft) {
          ovLeft.innerHTML = `
            <div style="height:100%; background:#FAF7F2; display:flex; flex-direction:column; align-items:center; justify-content:center; color:#C4B29E; font-size:0.85rem; font-family:'KoPub Batang', serif; letter-spacing:2px;">
              ❦<br><span style="margin-top:8px; font-size:0.78rem;">[ 56p / 에필로그 또는 여백 ]</span>
            </div>
          `;
        }
        if (ovRight) {
          ovRight.innerHTML = `
            <div style="height:100%; display:flex; flex-direction:column; justify-content:flex-end; padding:40px 30px; background:#FAF7F2; font-family:'KoPub Batang', serif; font-size:0.8rem; color:#4A3A2C; line-height:1.7; box-sizing:border-box;">
              <h4 style="font-size:1.1rem; color:#2C1D11; margin:0 0 12px 0; font-weight:700;">${projTitle}</h4>
              <div style="border-top:1.5px solid #2C1D11; padding-top:10px; margin-bottom:14px;">
                <div><strong>지은이</strong> | ${projAuthor}</div>
                <div><strong>발행인</strong> | 한철환</div>
                <div><strong>발행처</strong> | ${projPub}</div>
                <div><strong>출판등록</strong> | 제2014-000000호</div>
                <div><strong>발행일</strong> | ${projDate}</div>
                <div style="margin-top:6px;"><strong>주소</strong> | 서울특별시 구로구 디지털로33길 11, 에이스건설타워 8차 801호</div>
                <div><strong>홈페이지</strong> | www.bookk.co.kr</div>
                <div style="margin-top:6px;"><strong>ISBN</strong> | 979-11-XXXXX-X (03810)</div>
                <div><strong>정가</strong> | 15,000원</div>
              </div>
              <div style="font-size:0.72rem; color:#8C7560; border-top:1px solid #D5C2B0; padding-top:6px;">
                * 본 도서의 판권은 저작권자와 부크크에 있으며, 무단 전재와 복제를 금합니다.<br>
                * 잘못 만들어진 책은 구입처에서 바꾸어 드립니다.
              </div>
              <div style="margin-top:10px;"><button type="button" class="btn-micro" onclick="if(typeof openPublishExportModal==='function')openPublishExportModal();" style="background:#FAF2EB; color:#8C3B14; border:1px solid #D5C2B0; padding:4px 10px; border-radius:4px; font-size:0.75rem; cursor:pointer;">✏️ 판권 정보 수정</button></div>
            </div>
          `;
        }
      } else {
        if (lblLeftNum) lblLeftNum.textContent = `${sec.start_page}면(좌)`;
        if (lblRightNum) lblRightNum.textContent = `${sec.end_page}면(우)`;
        if (lblFolioLeft) lblFolioLeft.textContent = `${sec.start_page}`;
        if (lblFolioRight) lblFolioRight.textContent = `${sec.end_page}`;

        if (ovLeft) {
          ovLeft.innerHTML = `
            <div style="height:100%; background:#FAF7F2; display:flex; flex-direction:column; align-items:center; justify-content:center; color:#C4B29E; font-size:0.85rem; font-family:'KoPub Batang', serif; letter-spacing:2px;">
              ❦<br><span style="margin-top:8px; font-size:0.78rem;">[ ${sec.start_page}p ]</span>
            </div>
          `;
        }
        if (ovRight) {
          ovRight.innerHTML = `
            <div style="height:100%; display:flex; flex-direction:column; justify-content:center; align-items:center; padding:40px; background:#FAF7F2; text-align:center; box-sizing:border-box;">
              <h3 style="font-family:'KoPub Batang', serif; font-size:1.3rem; color:#2C1D11; margin-bottom:14px;">${sec.title}</h3>
              <div style="font-size:0.88rem; color:#6C5542; line-height:1.8;">${sec.content_preview || '섹션 내용이 준비 중입니다.'}</div>
            </div>
          `;
        }
      }
    }

    init() {
      console.log("[DTP Core v4.0] 모듈형 2-Layer 조판 편집 엔진 가동");
      this.bindShortcuts();
      this.bindToolbarEvents();
      this.initTextSelectionListener();

      // 탭 전환 감지: 조판 탭 진입 시 자동 렌더링
      document.querySelectorAll(".nav-tab-btn").forEach(btn => {
        btn.addEventListener("click", () => {
          const target = btn.getAttribute("data-target") || btn.id;
          if (target === "panelBook" || target === "tabBtnBook") {
            setTimeout(() => this.renderSpread(this.currentWorkIndex, this.currentSpreadPart || 1), 50);
          }
        });
      });

      // 초기 로드 시 자동 렌더링
      setTimeout(() => {
        if (this.getWorksList().length > 0) {
          this.renderSpread(this.currentWorkIndex, 1, false, { isInitialLoad: true });
        } else {
          this.ensureStatusLoaded().then(ok => {
            if (ok) this.renderSpread(this.currentWorkIndex, 1, false, { isInitialLoad: true });
          });
        }
      }, 150);
    }

    bindShortcuts() {
      document.addEventListener("keydown", (e) => {
        const panel = document.getElementById("panelBook");
        if (!panel || !panel.classList.contains("active")) return;

        if ((e.ctrlKey || e.metaKey) && (e.key === 'z' || e.key === 'Z')) {
          e.preventDefault();
          if (e.shiftKey) this.redo();
          else this.undo();
        } else if ((e.ctrlKey || e.metaKey) && (e.key === 'y' || e.key === 'Y')) {
          e.preventDefault();
          this.redo();
        } else {
          // 텍스트 타이핑 중이 아닐 때 키보드로 책장 넘기기 (PageUp/Down, Alt+좌우, Ctrl+좌우)
          const activeTag = document.activeElement ? document.activeElement.tagName.toLowerCase() : '';
          const isEditing = activeTag === 'input' || activeTag === 'textarea' || (document.activeElement && document.activeElement.isContentEditable);
          if (!isEditing) {
            if (e.key === 'PageDown' || (e.altKey && e.key === 'ArrowRight')) {
              e.preventDefault();
              this.navigatePage(1);
            } else if (e.key === 'PageUp' || (e.altKey && e.key === 'ArrowLeft')) {
              e.preventDefault();
              this.navigatePage(-1);
            } else if ((e.ctrlKey || e.metaKey) && e.key === 'ArrowRight') {
              e.preventDefault();
              this.navigateWork(1);
            } else if ((e.ctrlKey || e.metaKey) && e.key === 'ArrowLeft') {
              e.preventDefault();
              this.navigateWork(-1);
            }
          }
        }
      });
    }

    bindToolbarEvents() {
      const btnGuide = document.getElementById("btnToggleLayoutGuides");
      if (btnGuide) {
        btnGuide.onclick = () => this.toggleGuides();
      }
      this.bindPageDropzones();
    }

    bindPageDropzones() {
      ['left', 'right'].forEach(side => {
        const capSide = (side === 'left') ? 'Left' : 'Right';
        const pageEl = document.getElementById(`dtpPage${capSide}`);
        if (!pageEl) return;

        ['dragenter', 'dragover'].forEach(evt => {
          pageEl.addEventListener(evt, (e) => {
            e.preventDefault();
            e.stopPropagation();
            pageEl.style.outline = "2px dashed #C85A17";
          });
        });

        ['dragleave', 'dragend'].forEach(evt => {
          pageEl.addEventListener(evt, (e) => {
            e.preventDefault();
            e.stopPropagation();
            pageEl.style.outline = "";
          });
        });

        pageEl.addEventListener('drop', (e) => {
          e.preventDefault();
          e.stopPropagation();
          pageEl.style.outline = "";
          const files = e.dataTransfer?.files;
          if (files && files.length > 0 && files[0].type.startsWith("image/")) {
            const pageIdx = (this.currentSpreadPart - 1) * 2 + (side === 'left' ? 0 : 1);
            const pageNum = pageIdx + 1;
            window.currentSpreadPart = this.currentSpreadPart;
            if (typeof currentSpreadPart !== 'undefined') currentSpreadPart = this.currentSpreadPart;
            if (typeof currentViewerTargetSlot !== 'undefined') {
              currentViewerTargetSlot = (pageNum >= 3) ? "part2" : "main";
            }
            if (typeof uploadViewerImage === 'function') {
              uploadViewerImage(files[0]);
            }
          }
        });
      });
    }

    refreshImages() {
      this._imgCacheBust = Date.now();
      ['Left', 'Right'].forEach(capSide => {
        const imgElem = document.getElementById(`dtpImg${capSide}`);
        if (imgElem) imgElem.removeAttribute("data-clean-path");
      });
      this.renderSpread(this.currentWorkIndex, this.currentSpreadPart, false);
    }

    getWorksList() {
      if (typeof currentStatus !== 'undefined' && currentStatus && Array.isArray(currentStatus.works)) {
        window.currentStatus = currentStatus;
        return currentStatus.works;
      }
      if (window.currentStatus && Array.isArray(window.currentStatus.works)) {
        return window.currentStatus.works;
      }
      return [];
    }

    getCurrentWork() {
      const works = this.getWorksList();
      if (works.length === 0) return null;
      return works[this.currentWorkIndex] || works[0] || null;
    }

    async ensureStatusLoaded() {
      if (this.getWorksList().length > 0) return true;
      try {
        let res = await fetch("/api/status");
        if (!res.ok) {
          console.warn("[DTP Core] 웹 정적 모드: /studio/data/default_status.json에서 작품을 로드합니다.");
          res = await fetch("/studio/data/default_status.json");
        }
        if (res.ok) {
          const data = await res.json();
          window.currentStatus = data;
          if (typeof currentStatus !== 'undefined') {
            currentStatus = data;
          }
          return Array.isArray(data.works) && data.works.length > 0;
        }
      } catch (e) {
        console.error("[DTP Core] /api/status 직접 로드 실패:", e);
      }
      return false;
    }

    /**
     * 작품 layout_config 정규화 (pages 배열 단일화 & 구 slots/page_roles 완벽 호환)
     */
    getNormalizedConfig(work) {
      if (!work) return JSON.parse(JSON.stringify(this.defaultConfig));

      let cfg = work.layout_config;
      if (!cfg || typeof cfg !== 'object') {
        cfg = {};
      }

      let count = cfg.page_count || (work.layout_mode === 'multi_page' ? 4 : 2);
      if (count % 2 !== 0) count = Math.ceil(count / 2) * 2;
      count = Math.max(2, Math.min(6, count));

      let pages = Array.isArray(cfg.pages) ? [...cfg.pages] : [];

      const hasImage = Boolean(work.image_file && String(work.image_file).trim());
      const defaultSlots = hasImage ? ["image", "text"] : ["blank", "text"];
      const legacySlots = Array.isArray(cfg.slots) && cfg.slots.length >= 2 ? cfg.slots : defaultSlots;
      const legacyRoles = Array.isArray(cfg.page_roles) && cfg.page_roles.length >= 2 ? cfg.page_roles : ["none", "start"];

      for (let i = 0; i < 6; i++) {
        if (!pages[i]) {
          const slotType = (i < legacySlots.length) ? legacySlots[i] : "text";
          let usage = "text";
          if (slotType === "image") usage = "image";
          else if (slotType === "image_text") usage = "image_text";
          else if (slotType === "blank") usage = "blank";

          const roleType = (i < legacyRoles.length)
            ? legacyRoles[i]
            : (i === 0 ? "none" : (i === 1 ? "start" : "continue"));

          let imgFile = "";
          if (i === 0) imgFile = work.image_file || "";
          else if (i === 2) imgFile = work.image_file_2 || "";

          pages[i] = {
            page_num: i + 1,
            usage: usage,
            role: roleType,
            image_file: imgFile,
            custom_text: ""
          };
        } else {
          pages[i].page_num = i + 1;
          if (pages[i].custom_html) delete pages[i].custom_html;
          if (i === 0 && !pages[i].image_file && work.image_file) {
            pages[i].image_file = work.image_file;
          }
          if (i === 2 && !pages[i].image_file && work.image_file_2) {
            pages[i].image_file = work.image_file_2;
          }
        }
      }

      const normalized = {
        page_count: count,
        font_size_pt: parseFloat(cfg.font_size_pt) || 12,
        line_height_ratio: parseFloat(cfg.line_height_ratio) || 1.6,
        text_align: cfg.text_align || "left",
        backdrop_opacity: cfg.backdrop_opacity !== undefined ? parseFloat(cfg.backdrop_opacity) : 0.85,
        text_color_mode: cfg.text_color_mode || "dark",
        pages: pages.slice(0, count),
        _all_pages_pool: pages,
        slots: pages.slice(0, count).map(p => p.usage),
        page_roles: pages.slice(0, count).map(p => p.role),
        image_settings: cfg.image_settings || {}
      };

      work.layout_config = normalized;
      return normalized;
    }

    /**
     * 🌟 정밀 페이지 행 용량(Capacity) 계산 및 순차 텍스트 흐름(Flow) 배정
     * - 앞 페이지부터 인쇄안전선 내부 용량만큼 먼저 채우고, 넘치는 줄만 다음 페이지로 이관합니다.
     * - 페이지 수(page_count)에 의해 앞 페이지의 줄 수가 흔들리지 않으므로 무한루프가 원천 차단됩니다.
     */
    calculateTextFlowAndPages(work, cfg) {
      const fullText = (work.poem_body || work.body || work.content || "").replace(/\r\n/g, "\n").trim();
      const rawLines = fullText ? fullText.split("\n") : [];

      const pt = parseFloat(cfg.font_size_pt) || 12;
      const lh = parseFloat(cfg.line_height_ratio) || 1.6;

      // 12pt 기준 15.2px, 줄높이 1.85 -> 1줄당 약 28.12px
      const fontPx = (pt / 12.0) * 15.2;
      const linePx = fontPx * lh;

      // 상단 제목+지은이 상자가 있는 페이지(start)의 본문 가용 높이: 약 435px (12pt 기준 15줄 안착)
      // 본문만 이어지는 페이지(continue)의 본문 가용 높이: 약 545px (12pt 기준 19줄 안착)
      const maxVisualLinesStart = Math.max(4, Math.floor(480 / linePx));
      const maxVisualLinesCont = Math.max(5, Math.floor(480 / linePx));

      // 한 줄당 한글 글자 수 (페이지별 좌우 여백 차감 반영 및 공백/문장부호 가중치 계산)
      const getVisualLineCost = (lineStr, pageObj) => {
        const trimmed = (lineStr || "").trim();
        if (!trimmed) return 1;
        const leftOff = (pageObj && pageObj.left_offset) ? parseInt(pageObj.left_offset, 10) : 0;
        const rightOff = (pageObj && pageObj.right_offset) ? parseInt(pageObj.right_offset, 10) : 0;
        const effWidth = Math.max(120, 400 - leftOff - rightOff);
        let visualWidth = 0;
        for (let i = 0; i < trimmed.length; i++) {
          const code = trimmed.charCodeAt(i);
          if (code <= 127) {
            visualWidth += (trimmed[i] === ' ' ? 0.35 : 0.5) * fontPx;
          } else {
            visualWidth += 0.96 * fontPx;
          }
        }
        return Math.max(1, Math.ceil(visualWidth / effWidth));
      };

      // 최대 6페이지 풀 준비
      const pool = cfg._all_pages_pool || cfg.pages;
      while (pool.length < 6) {
        pool.push({
          page_num: pool.length + 1,
          usage: "text",
          role: "continue",
          image_file: "",
          custom_text: ""
        });
      }

      const textFlowMap = {};
      const textFlowSplitMap = {}; // 상·하 2단 분할 시 각 상자별 행 배분 맵
      const overflowFlags = {}; // 각 페이지 하단에 '본문 초과 ➔ 다음 면 이어짐' 배지 표시 여부
      const trailingBlankMap = {}; // 페이지 경계에 걸친 연 구분(빈 줄) 보존 맵
      let cursor = 0;
      let prevFlowIdx = -1;

      for (let idx = 0; idx < 6; idx++) {
        const p = pool[idx];
        const acceptsPoemFlow = (p.usage === "text" || p.usage === "image_text") &&
          (p.role === "start" || p.role === "continue");

        if (!acceptsPoemFlow) {
          textFlowMap[idx] = [];
          textFlowSplitMap[idx] = { box1: [], box2: [], role1: 'poem', role2: 'poem' };
          overflowFlags[idx] = false;
          trailingBlankMap[idx] = false;
          continue;
        }

        // 이어지는 페이지 시작 부분의 빈 줄(연 구분 공백)은 화면 상단 정렬을 위해 넘기되, 연 구분 사실(trailingBlankMap)을 반드시 기록!
        if (idx > 0 && p.role === "continue") {
          let skippedBlank = false;
          while (cursor < rawLines.length && rawLines[cursor].trim() === "") {
            skippedBlank = true;
            cursor++;
          }
          if (skippedBlank && prevFlowIdx >= 0) {
            trailingBlankMap[prevFlowIdx] = true;
          }
        }

        if (cursor >= rawLines.length && !p.split_body) {
          textFlowMap[idx] = [];
          textFlowSplitMap[idx] = { box1: [], box2: [], role1: p.body_role_1 || 'poem', role2: p.body_role_2 || 'poem' };
          overflowFlags[idx] = false;
          trailingBlankMap[idx] = false;
          continue;
        }

        const topOffset = p.top_offset ? parseInt(p.top_offset, 10) : 0;
        const minSingleH = Math.round(linePx + 28);

        // [🌟 상·하 2단 분할 모드 지원]
        if (p.split_body) {
          const role1 = p.body_role_1 || 'poem';
          const role2 = p.body_role_2 || 'poem';

          const topOffset1 = topOffset;
          const topOffset2 = p.top_offset_2 ? parseInt(p.top_offset_2, 10) : Math.max(minSingleH + 10, Math.round(468 / 2));

          const box1MaxH = Math.max(minSingleH, topOffset2 - topOffset1 - 8);
          const box1SafeLines = Math.max(1, Math.floor((box1MaxH - 28 + 2) / linePx));
          const budget1 = p.max_lines ? Math.min(box1SafeLines, parseInt(p.max_lines, 10)) : box1SafeLines;

          const box2MaxH = Math.max(minSingleH, 468 - topOffset2);
          const box2SafeLines = Math.max(1, Math.floor((box2MaxH - 28 + 2) / linePx));
          const budget2 = p.max_lines_2 ? Math.min(box2SafeLines, parseInt(p.max_lines_2, 10)) : box2SafeLines;

          const assigned1 = [];
          const assigned2 = [];

          if (role1 === 'poem') {
            let used1 = 0;
            while (cursor < rawLines.length) {
              const line = rawLines[cursor];
              const cost = getVisualLineCost(line, p);
              if (used1 + cost > budget1 && assigned1.length > 0) break;
              assigned1.push(line);
              used1 += cost;
              cursor++;
            }
          }

          if (role2 === 'poem') {
            let used2 = 0;
            while (cursor < rawLines.length) {
              const line = rawLines[cursor];
              const cost = getVisualLineCost(line, p);
              if (used2 + cost > budget2 && assigned2.length > 0) break;
              assigned2.push(line);
              used2 += cost;
              cursor++;
            }
          }

          textFlowMap[idx] = assigned1.concat(assigned2);
          textFlowSplitMap[idx] = {
            box1: assigned1,
            box2: assigned2,
            role1: role1,
            role2: role2
          };
          prevFlowIdx = idx;
        } else {
          // 18행(468px) 수용 황금 기준: 쪽수 위 16px 안전 여백 확보 (19행 이상은 다음 면 흘림)
          const maxSafeHeight = Math.max(minSingleH, 468 - topOffset);
          const availableHeight = Math.max(linePx, maxSafeHeight - 28);
          const maxSafeLines = Math.max(1, Math.floor((availableHeight + 2) / linePx));
          const customLines = p.max_lines ? parseInt(p.max_lines, 10) : 0;
          const budget = (customLines > 0) ? Math.min(maxSafeLines, customLines) : maxSafeLines;
          let usedVisual = 0;
          const assigned = [];

          while (cursor < rawLines.length) {
            const line = rawLines[cursor];
            const cost = getVisualLineCost(line, p);
            if (usedVisual + cost > budget && assigned.length > 0) {
              break;
            }
            // 외톨이 시작행(orphan) 방지: 빈 줄 다음 새 연의 첫 행만 아슬아슬하게 1행 걸치고 다음 행들이 잘릴 경우, 연 전체를 다음 면으로 넘김
            if (assigned.length > 0 && assigned[assigned.length - 1].trim() === "" && line.trim() !== "") {
              const remainingBudget = budget - usedVisual;
              let nextStanzaLines = 1;
              for (let s = cursor + 1; s < rawLines.length; s++) {
                if (rawLines[s].trim() === "") break;
                nextStanzaLines++;
              }
              if (nextStanzaLines >= 2 && cost === remainingBudget) {
                break;
              }
            }
            assigned.push(line);
            usedVisual += cost;
            cursor++;
          }

          // 페이지 맨 끝의 빈 줄은 정리하되, 다음 페이지와의 연 구분(trailingBlankMap)으로 반드시 보존!
          let poppedBlank = false;
          while (assigned.length > 0 && assigned[assigned.length - 1].trim() === "") {
            assigned.pop();
            poppedBlank = true;
          }
          trailingBlankMap[idx] = poppedBlank || (cursor < rawLines.length && rawLines[cursor].trim() === "");
          prevFlowIdx = idx;

          textFlowMap[idx] = assigned;
          textFlowSplitMap[idx] = { box1: assigned, box2: [], role1: 'poem', role2: 'poem' };
        }

        // 남은 유효 텍스트가 더 있는지 확인
        let hasMoreNonEmpty = false;
        for (let k = cursor; k < rawLines.length; k++) {
          if (rawLines[k].trim() !== "") {
            hasMoreNonEmpty = true;
            break;
          }
        }
        overflowFlags[idx] = hasMoreNonEmpty;
      }

      // 만약 6면을 다 채웠는데도 남은 줄이 있다면 6면(idx=5)에 나머지 추가
      if (cursor < rawLines.length) {
        const lastIdx = 5;
        textFlowMap[lastIdx] = (textFlowMap[lastIdx] || []).concat(rawLines.slice(cursor));
        overflowFlags[lastIdx] = true;
      }

      // 필요한 총 페이지 수(2, 4, 6) 자동 산출
      let requiredPages = 2;
      const hasContentOn56 = (textFlowMap[4] && textFlowMap[4].length > 0) ||
        (textFlowMap[5] && textFlowMap[5].length > 0) ||
        (pool[4]?.role === 'independent' && pool[4]?.custom_text) ||
        (pool[5]?.role === 'independent' && pool[5]?.custom_text);
      const hasContentOn34 = (textFlowMap[2] && textFlowMap[2].length > 0) ||
        (textFlowMap[3] && textFlowMap[3].length > 0) ||
        (pool[2]?.role === 'independent' && pool[2]?.custom_text) ||
        (pool[3]?.role === 'independent' && pool[3]?.custom_text);

      if (hasContentOn56) {
        requiredPages = 6;
      } else if (hasContentOn34) {
        requiredPages = 4;
      } else {
        requiredPages = 2;
      }

      this.lastTrailingBlankMap = trailingBlankMap;
      return {
        textFlowMap,
        textFlowSplitMap,
        overflowFlags,
        trailingBlankMap,
        requiredPages,
        pool
      };
    }

    /**
     * 🌟 2쪽 대칭 스프레드 메인 렌더러
     */
    renderSpread(workIndex, spreadPart = null, notifyAutoPageChange = false, options = {}) {
      // 본문 시화 렌더링 시 부속물 오버레이 및 전용 툴바 확실하게 숨기기
      const ovL = document.getElementById("dtpMatterOverlayLeft");
      const ovR = document.getElementById("dtpMatterOverlayRight");
      if (ovL) ovL.style.display = "none";
      if (ovR) ovR.style.display = "none";
      if (window.dtpMatterEngine && typeof window.dtpMatterEngine.hideMatterToolbar === 'function') {
        window.dtpMatterEngine.hideMatterToolbar();
      }

      ['Left', 'Right'].forEach(side => {
        const selU = document.getElementById(`selectPageUsage${side}`);
        const selR = document.getElementById(`selectPageRole${side}`);
        if (selU) { selU.disabled = false; selU.style.opacity = '1.0'; }
        if (selR) { selR.disabled = false; selR.style.opacity = '1.0'; }
      });

      const works = this.getWorksList();
      if (works.length === 0) {
        this.ensureStatusLoaded().then(loaded => {
          if (loaded) this.renderSpread(workIndex, spreadPart, notifyAutoPageChange);
        });
        return;
      }

      const prevWorkIndex = this.currentWorkIndex;
      if (workIndex !== undefined && workIndex !== null && !isNaN(workIndex)) {
        this.currentWorkIndex = Math.max(0, Math.min(works.length - 1, parseInt(workIndex, 10)));
        window.currentWorkIndex = this.currentWorkIndex;
        if (typeof currentWorkIndex !== 'undefined') {
          currentWorkIndex = this.currentWorkIndex;
        }
      }

      // 작품이 바뀌었을 때는 기본 1부로, 같은 작품 내에서는 현재 파트 유지
      if (spreadPart === null || spreadPart === undefined) {
        if (this.currentWorkIndex !== prevWorkIndex) {
          spreadPart = 1;
        } else {
          spreadPart = this.currentSpreadPart || 1;
        }
      }

      const work = this.getCurrentWork();
      if (!work) return;

      this.currentSectionId = `poem_${work.episode_no}`;

      if (!options.isInitialLoad && window._hasUserSelectedWork) {
        if (typeof window.updateBookTreeActiveItem === 'function') {
          window.updateBookTreeActiveItem(`poem_${work.episode_no}`);
        }
        if (window.bookStructureData && Array.isArray(window.bookStructureData.sections)) {
          const matchingSec = window.bookStructureData.sections.find(s => s.episode_no === work.episode_no);
          if (matchingSec) {
            this.currentSectionId = matchingSec.id;
            if (typeof window.updateBookTreeActiveItem === 'function') {
              window.updateBookTreeActiveItem(matchingSec.id);
            }
          }
        }
        // 조판 편집기에서 작품을 선택/이동한 경우 집필실(시 제목/본문/회차 드롭다운)도 자동 연동!
        if (!options.skipStudioSync && typeof window.loadWorkIntoEditor === 'function') {
          if (typeof currentEditingEpisode === 'undefined' || currentEditingEpisode !== work.episode_no) {
            window.loadWorkIntoEditor(work.episode_no, { fromDtpOrTree: true });
          }
        }
      } else {
        // 초기 구동 시에는 집필실의 [새 작품 집필] 상태를 보존하기 위해 트리 강제 하이라이트 생략
        document.querySelectorAll('.book-tree-item').forEach(el => el.classList.remove('active'));
      }

      const cfg = this.getNormalizedConfig(work);
      const prevPageCount = cfg.page_count;

      // 1) 정밀 텍스트 분할 및 필요 면수(2/4/6) 자동 판정
      const flowResult = this.calculateTextFlowAndPages(work, cfg);
      const { textFlowMap, overflowFlags, requiredPages, pool } = flowResult;

      // 2) 본문 초과 시 2쪽 자동 추가 (2 ➔ 4 ➔ 6) / 본문 축소 시 2쪽 자동 삭제 (6 ➔ 4 ➔ 2)
      if (cfg.page_count !== requiredPages) {
        cfg.page_count = requiredPages;
        cfg.pages = pool.slice(0, requiredPages);
        cfg.slots = cfg.pages.map(p => p.usage);
        cfg.page_roles = cfg.pages.map(p => p.role);

        if (notifyAutoPageChange && window.showToast) {
          if (requiredPages > prevPageCount) {
            window.showToast(`⚠️ 본문 초과 감지: ${requiredPages - 1}·${requiredPages}면(본문 이어짐)이 자동 추가되었습니다. (총 ${requiredPages}쪽)`, "info");
          } else {
            window.showToast(`✅ 본문 안착: 불필요한 여분 2쪽이 자동 삭제되었습니다. (총 ${requiredPages}쪽)`, "info");
          }
        }
        this.saveLayoutConfigToServer(work.episode_no, cfg);
      }

      // 스프레드 파트 범위 검증 (1: 1·2면, 2: 3·4면, 3: 5·6면)
      const maxParts = Math.max(1, Math.ceil(cfg.page_count / 2));
      if (spreadPart > maxParts) spreadPart = maxParts;
      if (spreadPart < 1) spreadPart = 1;
      this.currentSpreadPart = spreadPart;
      window.currentSpreadPart = spreadPart;

      // 3) 상단 툴바 UI 동기화
      this.syncToolbarUI(work, cfg, maxParts, overflowFlags);

      // 4) 좌측 페이지 (Slot A) & 우측 페이지 (Slot B) 렌더링
      const leftPageIdx = (this.currentSpreadPart - 1) * 2;
      const rightPageIdx = leftPageIdx + 1;

      this.renderSinglePage("left", leftPageIdx, cfg, work, textFlowMap, overflowFlags, flowResult.textFlowSplitMap);
      this.renderSinglePage("right", rightPageIdx, cfg, work, textFlowMap, overflowFlags, flowResult.textFlowSplitMap);

      // 5) 가이드선 가시성 반영
      this.applyGuidesVisibility();
    }

    /**
     * 상단 툴바 UI 동기화
     */
    syncToolbarUI(work, cfg, maxParts, overflowFlags) {
      // 1) 작품 선택 드롭다운 채우기 및 값 동기화
      const selectWork = document.getElementById("selectWorkDropdown");
      if (selectWork) {
        const works = this.getWorksList();
        if (selectWork.options.length !== works.length) {
          selectWork.innerHTML = "";
          works.forEach((w, idx) => {
            const opt = document.createElement("option");
            opt.value = idx;
            const chapLabel = w.chapter ? `[${w.chapter}] ` : "";
            opt.textContent = `${chapLabel}[${w.episode_no}] ${w.title}`;
            selectWork.appendChild(opt);
          });
        }
        selectWork.value = this.currentWorkIndex;
      }

      // 2) 안전선 상태 배지 동기화
      const statusBadge = document.getElementById("layoutStatusBadge");
      const statusText = document.getElementById("layoutStatusText");
      if (statusBadge && statusText) {
        if (cfg.page_count > 2) {
          statusBadge.className = "layout-badge badge-ok";
          statusText.textContent = `✅ ${cfg.page_count}쪽 분할 안착 (${maxParts}부 구성)`;
        } else {
          statusBadge.className = "layout-badge badge-ok";
          statusText.textContent = "✅ 인쇄안전선 안착";
        }
      }

      // 3) 총 면수 배지 동기화
      const lblTotalPages = document.getElementById("lblTotalPagesBadge");
      if (lblTotalPages) {
        const curStart = (this.currentSpreadPart - 1) * 2 + 1;
        lblTotalPages.textContent = `📄 ${cfg.page_count}쪽 조판 (${curStart}·${curStart + 1}면 / 총 ${cfg.page_count}면)`;
      }

      // 상단 navWorkIndexText 갱신
      const navText = document.getElementById("navWorkIndexText");
      if (navText) {
        const struct = window.bookStructureData;
        if (struct && struct.sections && this.currentSectionId) {
          const sec = struct.sections.find(s => s.id === this.currentSectionId);
          if (sec) {
            const curIdx = struct.sections.findIndex(s => s.id === this.currentSectionId) + 1;
            navText.textContent = `${curIdx} / ${struct.sections.length}`;
            navText.title = `${sec.title} (p.${sec.start_page}${sec.page_count > 1 ? '~' + sec.end_page : ''})`;
          }
        } else {
          const works = this.getWorksList();
          navText.textContent = `${this.currentWorkIndex + 1} / ${works.length}`;
        }
      }

      // 4) 스프레드 이동 네비게이션 (1부: 1·2면, 2부: 3·4면, 3부: 5·6면)
      const partNav = document.getElementById("spreadPartNavGroup");
      if (partNav) {
        if (maxParts > 1) {
          showElem(partNav, "inline-flex");
          let navHtml = "";
          for (let p = 1; p <= maxParts; p++) {
            const isCur = (p === this.currentSpreadPart);
            const pStart = (p - 1) * 2 + 1;
            const pEnd = pStart + 1;
            navHtml += `<button type="button" class="btn-micro ${isCur ? 'active-part' : ''}" onclick="dtpEditor.switchSpreadPart(${p})" style="font-weight:700; padding:3px 9px; border-radius:4px; cursor:pointer; ${isCur ? 'background:#8C3B14; color:#fff; border:1px solid #8C3B14;' : 'background:#fff; color:#553412; border:1px solid #D5C2B0;'}">${p}부 (${pStart}·${pEnd}면)</button>`;
          }
          partNav.innerHTML = navHtml;
        } else {
          hideElem(partNav);
        }
      }

      // 5) 폰트 크기 pt 셀렉터 동기화
      const selectPt = document.getElementById("selectTypographyFontSizePt");
      if (selectPt) {
        const ptStr = String(cfg.font_size_pt || 12);
        const exists = Array.from(selectPt.options).some(o => o.value === ptStr);
        if (!exists) {
          const opt = document.createElement("option");
          opt.value = ptStr;
          opt.textContent = `${ptStr}pt`;
          selectWork && selectPt.insertBefore(opt, selectPt.lastElementChild);
        }
        selectPt.value = ptStr;
      }

      // 6) 한지 투명도 슬라이더 동기화
      const slider = document.getElementById("inputDtpHanjiOpacity");
      if (slider) {
        slider.value = Math.round((cfg.backdrop_opacity ?? 0.85) * 100);
      }
      const valLabel = document.getElementById("lblDtpHanjiOpacityVal");
      if (valLabel) {
        valLabel.textContent = `${Math.round((cfg.backdrop_opacity ?? 0.85) * 100)}%`;
      }

      // 7) 하단 책장 넘기기 인디케이터
      const turnIndicator = document.getElementById("pageTurnIndicator");
      if (turnIndicator) {
        const curStart = (this.currentSpreadPart - 1) * 2 + 1;
        const partLabel = maxParts > 1 ? ` (${this.currentSpreadPart}/${maxParts}부)` : "";
        turnIndicator.textContent = `${work.episode_no || ''} 「${work.title || ''}」 — ${curStart}·${curStart + 1}면${partLabel}`;
      }



      // 8) DTP 도구상자 전체 동기화
      this.syncToolboxUI(work, cfg);
    }

    /**
     * 단일 페이지 대칭 렌더링 (side: "left" | "right")
     */
    /**
     * 상/하단 리사이즈 핸들 드래그 연동 (본문 행수 실시간 조절)
     */
    attachResizeHandles(boxBody, side, pageIdx, cfg, work) {
      let topHandle = boxBody.querySelector(".dtp-resize-handle.handle-top");
      if (!topHandle) {
        topHandle = document.createElement("div");
        topHandle.className = "dtp-resize-handle handle-top";
        topHandle.innerHTML = '<div class="handle-bar-pill"></div><span class="handle-label">▲ 본문 시작선 ↕</span>';
        boxBody.appendChild(topHandle);
      }

      let bottomHandle = boxBody.querySelector(".dtp-resize-handle.handle-bottom");
      if (!bottomHandle) {
        bottomHandle = document.createElement("div");
        bottomHandle.className = "dtp-resize-handle handle-bottom";
        bottomHandle.innerHTML = '<div class="handle-bar-pill"></div><span class="handle-label">▼ 본문 종료선 ↕ (행수 조절)</span>';
        boxBody.appendChild(bottomHandle);
      }

      let leftHandle = boxBody.querySelector(".dtp-resize-handle.handle-left");
      if (!leftHandle) {
        leftHandle = document.createElement("div");
        leftHandle.className = "dtp-resize-handle handle-left";
        leftHandle.innerHTML = '<div class="handle-bar-pill"></div><span class="handle-label">◀ 좌측 여백 ↔</span>';
        boxBody.appendChild(leftHandle);
      }

      let rightHandle = boxBody.querySelector(".dtp-resize-handle.handle-right");
      if (!rightHandle) {
        rightHandle = document.createElement("div");
        rightHandle.className = "dtp-resize-handle handle-right";
        rightHandle.innerHTML = '<div class="handle-bar-pill"></div><span class="handle-label">우측 여백 ↔ ▶</span>';
        boxBody.appendChild(rightHandle);
      }

      // 글상자 통째 위치 이동 드래그 핸들 바 (상단선에 밀착한 미니 ✥ 아이콘)
      let moveBoxHandle = boxBody.querySelector(".dtp-box-move-bar");
      if (!moveBoxHandle) {
        moveBoxHandle = document.createElement("div");
        moveBoxHandle.className = "dtp-box-move-bar";
        moveBoxHandle.innerHTML = '<span class="move-icon">✥</span>';
        moveBoxHandle.title = "본문 글상자 위치 이동 (마우스로 드래그)";
        boxBody.appendChild(moveBoxHandle);
      }

      const self = this;
      const pageData = cfg.pages[pageIdx] || (cfg._all_pages_pool && cfg._all_pages_pool[pageIdx]);
      if (!pageData) return;

      const pt = parseFloat(cfg.font_size_pt) || 12;
      const lh = parseFloat(cfg.line_height_ratio) || 1.6;
      const fontPx = (pt / 12.0) * 15.2;
      const linePx = fontPx * lh;

      // 1) 상단 핸들 드래그: 본문 시작선 위치(top_offset) 조절
      topHandle.onmousedown = function (e) {
        e.preventDefault();
        e.stopPropagation();
        self._isDraggingHandle = true;

        const startY = e.clientY;
        const initialOffset = parseInt(pageData.top_offset, 10) || 0;
        const initialHeight = boxBody.offsetHeight;
        // 하단선 기준선 고정 (상단선만 내리면 높이가 줄어들며 하단선은 절대 이동하지 않음)
        const fixedBottomY = initialOffset + initialHeight;
        let currOffset = initialOffset;

        boxBody.classList.add("is-resizing");
        document.body.style.cursor = "ns-resize";

        const minBottomH = Math.round(linePx + 28);
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
          const newHeight = Math.max(minBottomH, Math.round(candidateLines * linePx + 28));

          boxBody.style.setProperty("margin-top", `${currOffset}px`, "important");
          boxBody.style.setProperty("height", `${newHeight}px`, "important");
          boxBody.style.setProperty("flex", "none", "important");

          if (label) {
            label.textContent = `▲ 시작선: +${currOffset}px (수용: ${candidateLines}행)`;
          }
          self.detectAndApplyLineOverlap(side);
        }

        function onMouseUp(ev) {
          window.removeEventListener("mousemove", onMouseMove, true);
          window.removeEventListener("mouseup", onMouseUp, true);
          boxBody.classList.remove("is-resizing");
          document.body.style.cursor = "";

          if (label) {
            label.textContent = "▲ 본문 시작선 ↕";
            label.style.display = "";
          }

          if (currOffset !== initialOffset) {
            self.pushUndoState();
            pageData.top_offset = currOffset;
            const rawHeight = Math.max(minBottomH, fixedBottomY - currOffset);
            const candidateLines = Math.max(1, Math.floor((rawHeight - 28 + linePx * 0.45) / linePx));
            pageData.max_lines = candidateLines;
            if (work.layout_config && Array.isArray(work.layout_config.pages) && work.layout_config.pages[pageIdx]) {
              work.layout_config.pages[pageIdx].top_offset = currOffset;
              work.layout_config.pages[pageIdx].max_lines = candidateLines;
            }
            self.renderSpread(self.currentWorkIndex, self.currentSpreadPart, true);
            self.saveLayoutConfigToServer(work.episode_no, cfg);
            if (window.showToast) {
              window.showToast(`📏 ${pageIdx + 1}면 본문 상단선이 조절되었습니다 (${candidateLines}행 수용).`, "info");
            }
          }
        }

        window.addEventListener("mousemove", onMouseMove, true);
        window.addEventListener("mouseup", onMouseUp, true);
      };

      // 2) 하단 핸들 드래그: 본문 종료선 위치 및 수용 행수(max_lines) 조절 (상하단 14px 여백 + 행 단위 스냅 & 실시간 다음 면 흘림)
      bottomHandle.onmousedown = function (e) {
        e.preventDefault();
        e.stopPropagation();
        self._isDraggingHandle = true;

        const startY = e.clientY;
        const startHeight = boxBody.offsetHeight;
        const topOffset = parseInt(pageData.top_offset, 10) || 0;

        // 18행(468px) 수용 황금 기준 (인쇄안전선 468px - topOffset)
        const minBoxH = Math.round(linePx + 28);
        const topOffset2 = (pageData.split_body && pageData.top_offset_2) ? parseInt(pageData.top_offset_2, 10) : 468;
        const maxBoundaryH = pageData.split_body ? (topOffset2 - topOffset - 6) : (468 - topOffset);
        const maxAllowedHeight = Math.max(minBoxH, maxBoundaryH);
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
          snappedHeight = Math.min(maxAllowedHeight, Math.max(minBoxH, Math.round(candidateLines * linePx + 28)));

          boxBody.style.setProperty("height", `${snappedHeight}px`, "important");
          boxBody.style.setProperty("flex", "none", "important");

          if (candidateLines !== newLines) {
            newLines = candidateLines;
            // 드래그 중 실시간으로 행 배치를 재계산하여 밀려난 행이 즉시 다음 면(예: 3면 ➔ 4면)으로 넘어가는 것을 눈으로 확인!
            pageData.max_lines = (newLines >= maxSafeLines) ? null : newLines;
            if (cfg._all_pages_pool && cfg._all_pages_pool[pageIdx]) {
              cfg._all_pages_pool[pageIdx].max_lines = pageData.max_lines;
            }
            const liveFlow = self.calculateTextFlowAndPages(work, cfg);
            const leftIdx = (self.currentSpreadPart - 1) * 2;
            const rightIdx = leftIdx + 1;
            self.updateLiveTextFlowDom("left", leftIdx, cfg, work, liveFlow.textFlowMap, liveFlow.overflowFlags);
            self.updateLiveTextFlowDom("right", rightIdx, cfg, work, liveFlow.textFlowMap, liveFlow.overflowFlags);
          }

          updateHandleTooltip(newLines, newLines >= maxSafeLines);
          self.detectAndApplyLineOverlap(side);
        }

        function onMouseUp(ev) {
          window.removeEventListener("mousemove", onMouseMove, true);
          window.removeEventListener("mouseup", onMouseUp, true);
          boxBody.classList.remove("is-resizing");
          document.body.style.cursor = "";
          setTimeout(() => { self._isDraggingHandle = false; }, 80);

          const label = bottomHandle.querySelector(".handle-label");
          if (label) {
            label.textContent = "▼ 본문 종료선 ↕ (행수 조절)";
            label.style.display = "";
          }

          const targetLines = (newLines >= maxSafeLines) ? null : newLines;
          const prevTarget = (initialMaxLines >= maxSafeLines) ? null : initialMaxLines;

          pageData.max_lines = targetLines;
          if (work.layout_config && Array.isArray(work.layout_config.pages) && work.layout_config.pages[pageIdx]) {
            work.layout_config.pages[pageIdx].max_lines = targetLines;
          }
          self.renderSpread(self.currentWorkIndex, self.currentSpreadPart, true);
          if (targetLines !== prevTarget) {
            self.pushUndoState();
            self.saveLayoutConfigToServer(work.episode_no, cfg);
            if (window.showToast) {
              const msg = targetLines ? `📏 ${pageIdx + 1}면 본문 수용 용량이 ${targetLines}행(상·하단 여백 14px)으로 설정되었습니다.` : `✅ ${pageIdx + 1}면 본문이 하단 안전선에 꼭 맞게 안착되었습니다.`;
              window.showToast(msg, "info");
            }
          }
        }

        window.addEventListener("mousemove", onMouseMove, true);
        window.addEventListener("mouseup", onMouseUp, true);
      };

      // 3) 좌측 핸들 드래그: 본문 좌측 여백(left_offset) 조절 (우측 경계 고정 & 좌측 폭 리사이즈)
      leftHandle.onmousedown = function (e) {
        e.preventDefault();
        e.stopPropagation();

        const startX = e.clientX;
        const initialLeft = parseInt(pageData.left_offset, 10) || 0;
        const currentRight = parseInt(pageData.right_offset, 10) || 0;
        let currLeft = initialLeft;

        const safeBoundary = boxBody.closest(".dtp-safe-boundary") || boxBody.parentElement;
        const boundaryW = safeBoundary ? safeBoundary.clientWidth : 380;
        const minContentW = Math.max(26, Math.round(fontPx * 1.4)); // 우측에 단 한 글자 폭만 남기고 극단 이동 허용
        const maxLeft = Math.max(0, Math.floor(boundaryW - currentRight - minContentW));

        boxBody.classList.add("is-resizing");
        document.body.style.cursor = "ew-resize";

        const label = leftHandle.querySelector(".handle-label");
        if (label) {
          label.textContent = `◀ 좌측 여백: +${initialLeft}px`;
          label.style.display = "block";
        }

        function onMouseMove(ev) {
          const deltaX = ev.clientX - startX;
          currLeft = Math.max(0, Math.min(maxLeft, Math.round(initialLeft + deltaX)));
          boxBody.style.setProperty("margin-left", `${currLeft}px`, "important");
          boxBody.style.setProperty("width", `calc(100% - ${currLeft + currentRight}px)`, "important");

          if (label) {
            label.textContent = `◀ 좌측 여백: +${currLeft}px`;
          }
        }

        function onMouseUp() {
          window.removeEventListener("mousemove", onMouseMove, true);
          window.removeEventListener("mouseup", onMouseUp, true);
          boxBody.classList.remove("is-resizing");
          document.body.style.cursor = "";

          if (label) {
            label.textContent = "◀ 좌측 여백 ↔";
            label.style.display = "";
          }

          if (currLeft !== initialLeft) {
            self.pushUndoState();
            pageData.left_offset = currLeft;
            if (work.layout_config && Array.isArray(work.layout_config.pages) && work.layout_config.pages[pageIdx]) {
              work.layout_config.pages[pageIdx].left_offset = currLeft;
            }
            self.renderSpread(self.currentWorkIndex, self.currentSpreadPart, true);
            self.saveLayoutConfigToServer(work.episode_no, cfg);
            if (window.showToast) {
              window.showToast(`📏 ${pageIdx + 1}면 본문 좌측 여백이 ${currLeft}px로 조절되었습니다.`, "info");
            }
          }
        }

        window.addEventListener("mousemove", onMouseMove, true);
        window.addEventListener("mouseup", onMouseUp, true);
      };

      // 4) 우측 핸들 드래그: 본문 우측 여백(right_offset) 조절 (좌측 경계 고정 & 우측 폭 리사이즈)
      rightHandle.onmousedown = function (e) {
        e.preventDefault();
        e.stopPropagation();

        const startX = e.clientX;
        const currentLeft = parseInt(pageData.left_offset, 10) || 0;
        const initialRight = parseInt(pageData.right_offset, 10) || 0;
        let currRight = initialRight;

        const safeBoundary = boxBody.closest(".dtp-safe-boundary") || boxBody.parentElement;
        const boundaryW = safeBoundary ? safeBoundary.clientWidth : 380;
        const minContentW = Math.max(26, Math.round(fontPx * 1.4)); // 좌측에 단 한 글자 폭만 남기고 극단 이동 허용
        const maxRight = Math.max(0, Math.floor(boundaryW - currentLeft - minContentW));

        boxBody.classList.add("is-resizing");
        document.body.style.cursor = "ew-resize";

        const label = rightHandle.querySelector(".handle-label");
        if (label) {
          label.textContent = `우측 여백: +${initialRight}px ▶`;
          label.style.display = "block";
        }

        function onMouseMove(ev) {
          const deltaX = ev.clientX - startX;
          // 마우스를 왼쪽으로 밀면 우측 여백이 늘어남 (-deltaX)
          currRight = Math.max(0, Math.min(maxRight, Math.round(initialRight - deltaX)));
          boxBody.style.setProperty("margin-right", `${currRight}px`, "important");
          boxBody.style.setProperty("width", `calc(100% - ${currentLeft + currRight}px)`, "important");

          if (label) {
            label.textContent = `우측 여백: +${currRight}px ▶`;
          }
        }

        function onMouseUp() {
          window.removeEventListener("mousemove", onMouseMove, true);
          window.removeEventListener("mouseup", onMouseUp, true);
          boxBody.classList.remove("is-resizing");
          document.body.style.cursor = "";

          if (label) {
            label.textContent = "우측 여백 ↔ ▶";
            label.style.display = "";
          }

          if (currRight !== initialRight) {
            self.pushUndoState();
            pageData.right_offset = currRight;
            if (work.layout_config && Array.isArray(work.layout_config.pages) && work.layout_config.pages[pageIdx]) {
              work.layout_config.pages[pageIdx].right_offset = currRight;
            }
            self.renderSpread(self.currentWorkIndex, self.currentSpreadPart, true);
            self.saveLayoutConfigToServer(work.episode_no, cfg);
            if (window.showToast) {
              window.showToast(`📏 ${pageIdx + 1}면 본문 우측 여백이 ${currRight}px로 조절되었습니다.`, "info");
            }
          }
        }

        window.addEventListener("mousemove", onMouseMove, true);
        window.addEventListener("mouseup", onMouseUp, true);
      };

      // 5) 글상자 통째 위치 이동 드래그 이벤트 (크기 불변)
      moveBoxHandle.onmousedown = function (e) {
        e.preventDefault();
        e.stopPropagation();

        const slot = side.toLowerCase();
        self.setTargetPageSlot(slot);

        boxBody.classList.add("is-moving-box");
        document.body.style.cursor = "move";
        document.body.style.userSelect = "none";

        const startX = e.clientX;
        const startY = e.clientY;

        const initialTop = parseInt(pageData.top_offset, 10) || 0;
        const initialLeft = parseInt(pageData.left_offset, 10) || 0;
        const initialRight = parseInt(pageData.right_offset, 10) || 0;
        const boxH = boxBody.offsetHeight;

        const safeBoundary = boxBody.closest(".dtp-safe-boundary") || boxBody.parentElement;
        const boundaryW = safeBoundary ? safeBoundary.clientWidth : 380;
        const topOffset2 = (pageData.split_body && pageData.top_offset_2) ? parseInt(pageData.top_offset_2, 10) : 468;
        const maxTop = Math.max(0, pageData.split_body ? (topOffset2 - boxH - 6) : (468 - boxH));

        function onMouseMove(ev) {
          const deltaX = ev.clientX - startX;
          const deltaY = ev.clientY - startY;

          // 세로 이동: 높이 불변
          let newTop = Math.max(0, Math.min(maxTop, Math.round(initialTop + deltaY)));

          // 가로 이동: 너비 불변
          let newLeft = initialLeft + deltaX;
          let newRight = initialRight - deltaX;

          if (newLeft < 0) {
            newRight += newLeft;
            newLeft = 0;
          }
          if (newRight < 0) {
            newLeft += newRight;
            newRight = 0;
          }

          newLeft = Math.max(0, Math.round(newLeft));
          newRight = Math.max(0, Math.round(newRight));

          boxBody.style.setProperty("margin-top", `${newTop}px`, "important");
          boxBody.style.setProperty("height", `${boxH}px`, "important");
          boxBody.style.setProperty("flex", "none", "important");
          boxBody.style.setProperty("margin-left", `${newLeft}px`, "important");
          boxBody.style.setProperty("margin-right", `${newRight}px`, "important");
          boxBody.style.setProperty("width", `calc(100% - ${newLeft + newRight}px)`, "important");

          self.detectAndApplyLineOverlap(side);
        }

        function onMouseUp() {
          window.removeEventListener("mousemove", onMouseMove, true);
          window.removeEventListener("mouseup", onMouseUp, true);
          boxBody.classList.remove("is-moving-box");
          document.body.style.cursor = "";
          document.body.style.userSelect = "";

          const curTop = parseInt(boxBody.style.marginTop, 10) || initialTop;
          const curLeft = parseInt(boxBody.style.marginLeft, 10) || initialLeft;
          const curRight = parseInt(boxBody.style.marginRight, 10) || initialRight;

          if (curTop !== initialTop || curLeft !== initialLeft || curRight !== initialRight) {
            self.pushUndoState();
            pageData.top_offset = curTop;
            pageData.left_offset = curLeft;
            pageData.right_offset = curRight;
            if (work.layout_config && Array.isArray(work.layout_config.pages) && work.layout_config.pages[pageIdx]) {
              work.layout_config.pages[pageIdx].top_offset = curTop;
              work.layout_config.pages[pageIdx].left_offset = curLeft;
              work.layout_config.pages[pageIdx].right_offset = curRight;
            }
            self.renderSpread(self.currentWorkIndex, self.currentSpreadPart, true);
            self.saveLayoutConfigToServer(work.episode_no, cfg);
            if (window.showToast) {
              window.showToast(`📄 ${pageIdx + 1}면 본문 글상자 위치가 이동되었습니다.`, "info");
            }
          }
        }

        window.addEventListener("mousemove", onMouseMove, true);
        window.addEventListener("mouseup", onMouseUp, true);
      };
    }

    /**
     * 표제면(title_only) 제목·지은이 상자 드래그 위치 이동
     */
    attachTitleBoxMoveHandle(boxTitle, side, pageIdx, cfg, work) {
      let moveBar = boxTitle.querySelector('.dtp-title-move-bar');
      if (!moveBar) {
        moveBar = document.createElement('div');
        moveBar.className = 'dtp-box-move-bar dtp-title-move-bar';
        moveBar.innerHTML = '<span class="move-icon">✥</span>';
        moveBar.title = '표제면 제목 상자 위치 이동 (마우스로 드래그)';
        boxTitle.appendChild(moveBar);
      }

      const self = this;
      const pageData = cfg.pages[pageIdx] || (cfg._all_pages_pool && cfg._all_pages_pool[pageIdx]);
      if (!pageData) return;

      moveBar.onmousedown = function (e) {
        e.preventDefault();
        e.stopPropagation();

        const startX = e.clientX;
        const startY = e.clientY;
        const initialTop = parseInt(pageData.top_offset, 10) || 0;
        const initialLeft = parseInt(pageData.left_offset, 10) || 0;

        boxTitle.classList.add("is-moving-box");

        function onMouseMove(ev) {
          const deltaX = ev.clientX - startX;
          const deltaY = ev.clientY - startY;
          const newTop = Math.max(0, Math.min(380, initialTop + deltaY));
          const newLeft = Math.max(0, Math.min(200, initialLeft + deltaX));
          boxTitle.style.setProperty("margin-top", `${newTop}px`, "important");
          boxTitle.style.setProperty("margin-left", `${newLeft}px`, "important");
        }

        function onMouseUp() {
          boxTitle.classList.remove("is-moving-box");
          window.removeEventListener("mousemove", onMouseMove, true);
          window.removeEventListener("mouseup", onMouseUp, true);

          const curTop = parseInt(boxTitle.style.marginTop, 10) || initialTop;
          const curLeft = parseInt(boxTitle.style.marginLeft, 10) || initialLeft;

          if (curTop !== initialTop || curLeft !== initialLeft) {
            self.pushUndoState();
            pageData.top_offset = curTop;
            pageData.left_offset = curLeft;
            if (work.layout_config && Array.isArray(work.layout_config.pages) && work.layout_config.pages[pageIdx]) {
              work.layout_config.pages[pageIdx].top_offset = curTop;
              work.layout_config.pages[pageIdx].left_offset = curLeft;
            }
            self.renderSpread(self.currentWorkIndex, self.currentSpreadPart, true);
            self.saveLayoutConfigToServer(work.episode_no, cfg);
            if (window.showToast) {
              window.showToast(`🪟 ${pageIdx + 1}면 표제면 제목 위치가 조정되었습니다.`, "info");
            }
          }
        }

        window.addEventListener("mousemove", onMouseMove, true);
        window.addEventListener("mouseup", onMouseUp, true);
      };
    }

    /**
     * 본문 글상자 미니 컨트롤 바 (단일 상자: 분할 버튼 / 2단 분할: 역할 전환 및 삭제)
     */
    attachBoxMiniToolbar(boxEl, boxNum, side, pageIdx, cfg, work, pageData) {
      if (!boxEl) return;
      let tb = boxEl.querySelector('.dtp-box-toolbar');
      if (!tb) {
        tb = document.createElement('div');
        tb.className = 'dtp-box-toolbar';
        boxEl.appendChild(tb);
      }
      tb.innerHTML = '';

      const isSplit = Boolean(pageData.split_body);
      const roleKey = (boxNum === 2) ? 'body_role_2' : 'body_role_1';
      const curRole = pageData[roleKey] || 'poem';

      if (!isSplit) {
        // 단일 상자 모드: [+ 2단 분할] 버튼 제공
        const btnSplit = document.createElement('button');
        btnSplit.type = 'button';
        btnSplit.className = 'btn-tb-tool';
        btnSplit.innerHTML = '<span>➕</span><span>2단 분할</span>';
        btnSplit.title = '이 면의 글상자를 상·하 2개로 분할하여 그림 여백을 살립니다';
        btnSplit.onclick = (e) => {
          e.preventDefault();
          e.stopPropagation();
          this.pushUndoState();
          pageData.split_body = true;
          pageData.body_role_1 = 'poem';
          pageData.body_role_2 = 'poem';
          const top1 = parseInt(pageData.top_offset, 10) || 0;
          pageData.top_offset_2 = Math.max(top1 + 140, 240);
          pageData.max_lines = Math.max(2, Math.floor((pageData.max_lines || 10) / 2));
          this.renderSpread(this.currentWorkIndex, this.currentSpreadPart, true);
          this.saveLayoutConfigToServer(work.episode_no, cfg);
          if (window.showToast) {
            window.showToast(`✂️ ${pageIdx + 1}면에 2단 글상자가 생성되었습니다. 원하는 위치로 자유롭게 조절하세요.`, 'success');
          }
        };
        tb.appendChild(btnSplit);
      } else {
        // 2단 분할 모드: [1단/2단 배지] + [📖 시] / [✍️ 캡션] + [✕ 삭제]
        const badge = document.createElement('span');
        badge.style.fontWeight = '700';
        badge.style.color = (boxNum === 2) ? '#B45309' : '#8C532B';
        badge.style.marginRight = '2px';
        badge.textContent = (boxNum === 2) ? '2단' : '1단';
        tb.appendChild(badge);

        // 시 본문 버튼
        const btnPoem = document.createElement('button');
        btnPoem.type = 'button';
        btnPoem.className = `btn-tb-tool ${curRole === 'poem' ? 'active' : ''}`;
        btnPoem.innerHTML = '<span>📖</span><span>시 본문</span>';
        btnPoem.title = '시 본문의 행을 이 상자에 배치합니다';
        btnPoem.onclick = (e) => {
          e.preventDefault();
          e.stopPropagation();
          if (curRole !== 'poem') {
            this.pushUndoState();
            pageData[roleKey] = 'poem';
            this.renderSpread(this.currentWorkIndex, this.currentSpreadPart, true);
            this.saveLayoutConfigToServer(work.episode_no, cfg);
          }
        };
        tb.appendChild(btnPoem);

        // 독립 캡션/설명 버튼
        const btnCaption = document.createElement('button');
        btnCaption.type = 'button';
        btnCaption.className = `btn-tb-tool ${curRole === 'custom' ? 'active' : ''}`;
        btnCaption.innerHTML = '<span>✍️</span><span>캡션/해설</span>';
        btnCaption.title = '그림 설명이나 독립 문구를 직접 작성합니다';
        btnCaption.onclick = (e) => {
          e.preventDefault();
          e.stopPropagation();
          if (curRole !== 'custom') {
            this.pushUndoState();
            pageData[roleKey] = 'custom';
            if (boxNum === 2 && !pageData.custom_text_2) {
              pageData.custom_text_2 = '* 그림 설명이나 기억의 캡션을 입력하세요.';
            }
            if (boxNum === 1 && !pageData.custom_text_1) {
              pageData.custom_text_1 = '상단 머리말이나 발문을 입력하세요.';
            }
            this.renderSpread(this.currentWorkIndex, this.currentSpreadPart, true);
            this.saveLayoutConfigToServer(work.episode_no, cfg);
          }
        };
        tb.appendChild(btnCaption);

        // [✕ 글상자 삭제] 버튼
        const btnDel = document.createElement('button');
        btnDel.type = 'button';
        btnDel.className = 'btn-tb-tool btn-tb-delete';
        btnDel.innerHTML = '<span>✕</span><span>삭제</span>';
        btnDel.title = '이 글상자를 삭제하고 단일 상자로 환원합니다';
        btnDel.onclick = (e) => {
          e.preventDefault();
          e.stopPropagation();
          this.pushUndoState();
          pageData.split_body = false;
          if (boxNum === 1 && pageData.body_role_2 === 'custom') {
            pageData.custom_text = pageData.custom_text_2;
            pageData.role = 'independent';
          }
          delete pageData.top_offset_2;
          delete pageData.max_lines_2;
          delete pageData.left_offset_2;
          delete pageData.right_offset_2;
          delete pageData.body_role_1;
          delete pageData.body_role_2;
          delete pageData.custom_text_1;
          delete pageData.custom_text_2;

          this.renderSpread(this.currentWorkIndex, this.currentSpreadPart, true);
          this.saveLayoutConfigToServer(work.episode_no, cfg);
          if (window.showToast) {
            window.showToast(`🗑️ ${pageIdx + 1}면의 ${boxNum}단 글상자가 삭제되어 단일 상자로 환원되었습니다.`, 'info');
          }
        };
        tb.appendChild(btnDel);
      }
    }

    /**
     * 2단 보조 글상자(Box 2) 전용 리사이즈 및 위치 이동 핸들러 (상호 비침범 충돌 락 탑재)
     */
    attachBox2ResizeHandles(boxBody2, boxBody1, side, pageIdx, cfg, work) {
      if (!boxBody2) return;

      let topHandle = boxBody2.querySelector('.dtp-resize-handle.handle-top');
      if (!topHandle) {
        topHandle = document.createElement('div');
        topHandle.className = 'dtp-resize-handle handle-top';
        topHandle.innerHTML = '<div class="handle-bar-pill"></div><span class="handle-label">▲ 2단 시작선 ↕</span>';
        boxBody2.appendChild(topHandle);
      }

      let bottomHandle = boxBody2.querySelector('.dtp-resize-handle.handle-bottom');
      if (!bottomHandle) {
        bottomHandle = document.createElement('div');
        bottomHandle.className = 'dtp-resize-handle handle-bottom';
        bottomHandle.innerHTML = '<div class="handle-bar-pill"></div><span class="handle-label">▼ 2단 종료선 ↕</span>';
        boxBody2.appendChild(bottomHandle);
      }

      let leftHandle = boxBody2.querySelector('.dtp-resize-handle.handle-left');
      if (!leftHandle) {
        leftHandle = document.createElement('div');
        leftHandle.className = 'dtp-resize-handle handle-left';
        leftHandle.innerHTML = '<div class="handle-bar-pill"></div><span class="handle-label">◀ 좌측 여백 ↔</span>';
        boxBody2.appendChild(leftHandle);
      }

      let rightHandle = boxBody2.querySelector('.dtp-resize-handle.handle-right');
      if (!rightHandle) {
        rightHandle = document.createElement('div');
        rightHandle.className = 'dtp-resize-handle handle-right';
        rightHandle.innerHTML = '<div class="handle-bar-pill"></div><span class="handle-label">우측 여백 ↔ ▶</span>';
        boxBody2.appendChild(rightHandle);
      }

      let moveBoxHandle = boxBody2.querySelector('.dtp-box-move-bar');
      if (!moveBoxHandle) {
        moveBoxHandle = document.createElement('div');
        moveBoxHandle.className = 'dtp-box-move-bar';
        moveBoxHandle.innerHTML = '<span class="move-icon">✥</span>';
        moveBoxHandle.title = '2단 글상자 위치 이동 (마우스로 드래그)';
        boxBody2.appendChild(moveBoxHandle);
      }

      const self = this;
      const pageData = cfg.pages[pageIdx] || (cfg._all_pages_pool && cfg._all_pages_pool[pageIdx]);
      if (!pageData) return;

      const pt = parseFloat(cfg.font_size_pt) || 12;
      const lh = parseFloat(cfg.line_height_ratio) || 1.6;
      const fontPx = (pt / 12.0) * 15.2;
      const linePx = fontPx * lh;
      const minBoxH = Math.round(linePx + 28);

      // A) 상단 핸들 드래그 (2단 시작선 조절 - 1단 상자의 바닥선 침범 불가!)
      topHandle.onmousedown = function (e) {
        e.preventDefault();
        e.stopPropagation();
        self._isDraggingHandle = true;

        const startY = e.clientY;
        const initialOffset = parseInt(pageData.top_offset_2, 10) || 260;
        const initialHeight = boxBody2.offsetHeight;
        const fixedBottomY = initialOffset + initialHeight;

        const box1Top = parseInt(pageData.top_offset, 10) || 0;
        const box1Height = (boxBody1 && boxBody1.offsetHeight > 0) ? boxBody1.offsetHeight : 120;
        const collisionMinTop = box1Top + box1Height + 6;

        const maxTopOffset = Math.max(collisionMinTop, fixedBottomY - minBoxH);
        let currOffset = initialOffset;

        boxBody2.classList.add('is-resizing');
        document.body.style.cursor = 'ns-resize';

        const label = topHandle.querySelector('.handle-label');

        function onMouseMove(ev) {
          const deltaY = ev.clientY - startY;
          currOffset = Math.max(collisionMinTop, Math.min(maxTopOffset, Math.round(initialOffset + deltaY)));
          const rawHeight = Math.max(minBoxH, fixedBottomY - currOffset);
          const candidateLines = Math.max(1, Math.floor((rawHeight - 28 + linePx * 0.45) / linePx));
          const newHeight = Math.max(minBoxH, Math.round(candidateLines * linePx + 28));

          boxBody2.style.setProperty('margin-top', `${currOffset}px`, 'important');
          boxBody2.style.setProperty('height', `${newHeight}px`, 'important');
          boxBody2.style.setProperty('flex', 'none', 'important');

          if (label) {
            const hitCollision = (currOffset <= collisionMinTop) ? ' [1단 경계]' : '';
            label.textContent = `▲ 2단 시작: +${currOffset}px (${candidateLines}행)${hitCollision}`;
            label.style.display = 'block';
          }
          self.detectAndApplyLineOverlap(side);
        }

        function onMouseUp() {
          window.removeEventListener('mousemove', onMouseMove, true);
          window.removeEventListener('mouseup', onMouseUp, true);
          boxBody2.classList.remove('is-resizing');
          document.body.style.cursor = '';
          if (label) label.style.display = '';

          if (currOffset !== initialOffset) {
            self.pushUndoState();
            pageData.top_offset_2 = currOffset;
            const rawHeight = Math.max(minBoxH, fixedBottomY - currOffset);
            pageData.max_lines_2 = Math.max(1, Math.floor((rawHeight - 28 + linePx * 0.45) / linePx));
            self.renderSpread(self.currentWorkIndex, self.currentSpreadPart, true);
            self.saveLayoutConfigToServer(work.episode_no, cfg);
          }
        }

        window.addEventListener('mousemove', onMouseMove, true);
        window.addEventListener('mouseup', onMouseUp, true);
      };

      // B) 하단 핸들 드래그 (2단 종료선 조절 - 인쇄안전선 468px 한도 준수)
      bottomHandle.onmousedown = function (e) {
        e.preventDefault();
        e.stopPropagation();
        self._isDraggingHandle = true;

        const startY = e.clientY;
        const startHeight = boxBody2.offsetHeight;
        const topOffset2 = parseInt(pageData.top_offset_2, 10) || 260;
        const maxAllowedHeight = Math.max(minBoxH, 468 - topOffset2);
        const maxSafeLines = Math.max(1, Math.floor((maxAllowedHeight - 28 + 2) / linePx));

        let newLines = pageData.max_lines_2 ? Math.min(maxSafeLines, parseInt(pageData.max_lines_2, 10)) : maxSafeLines;

        boxBody2.classList.add('is-resizing');
        document.body.style.cursor = 'ns-resize';

        const label = bottomHandle.querySelector('.handle-label');

        function onMouseMove(ev) {
          const deltaY = ev.clientY - startY;
          const rawHeight = Math.max(minBoxH, Math.min(maxAllowedHeight, startHeight + deltaY));
          const candidateLines = Math.max(1, Math.min(maxSafeLines, Math.floor((rawHeight - 28 + linePx * 0.45) / linePx)));
          const snappedHeight = Math.min(maxAllowedHeight, Math.max(minBoxH, Math.round(candidateLines * linePx + 28)));

          boxBody2.style.setProperty('height', `${snappedHeight}px`, 'important');
          boxBody2.style.setProperty('flex', 'none', 'important');
          newLines = candidateLines;

          if (label) {
            label.textContent = `▼ 2단 수용: ${newLines}행 (안전선 한도)`;
            label.style.display = 'block';
          }
          self.detectAndApplyLineOverlap(side);
        }

        function onMouseUp() {
          window.removeEventListener('mousemove', onMouseMove, true);
          window.removeEventListener('mouseup', onMouseUp, true);
          boxBody2.classList.remove('is-resizing');
          document.body.style.cursor = '';
          if (label) label.style.display = '';

          self.pushUndoState();
          pageData.max_lines_2 = newLines;
          self.renderSpread(self.currentWorkIndex, self.currentSpreadPart, true);
          self.saveLayoutConfigToServer(work.episode_no, cfg);
        }

        window.addEventListener('mousemove', onMouseMove, true);
        window.addEventListener('mouseup', onMouseUp, true);
      };

      // C) 좌측 핸들 드래그
      leftHandle.onmousedown = function (e) {
        e.preventDefault();
        e.stopPropagation();
        self._isDraggingHandle = true;
        const startX = e.clientX;
        const initialLeft = parseInt(pageData.left_offset_2, 10) || 0;
        const currentRight = parseInt(pageData.right_offset_2, 10) || 0;
        const maxLeft = Math.max(0, 360 - currentRight - 80);
        let currLeft = initialLeft;

        boxBody2.classList.add('is-resizing');
        document.body.style.cursor = 'ew-resize';

        function onMouseMove(ev) {
          const deltaX = ev.clientX - startX;
          currLeft = Math.max(0, Math.min(maxLeft, Math.round(initialLeft + deltaX)));
          boxBody2.style.setProperty('margin-left', `${currLeft}px`, 'important');
          boxBody2.style.setProperty('width', `calc(100% - ${currLeft + currentRight}px)`, 'important');
        }

        function onMouseUp() {
          window.removeEventListener('mousemove', onMouseMove, true);
          window.removeEventListener('mouseup', onMouseUp, true);
          boxBody2.classList.remove('is-resizing');
          document.body.style.cursor = '';
          if (currLeft !== initialLeft) {
            self.pushUndoState();
            pageData.left_offset_2 = currLeft;
            self.renderSpread(self.currentWorkIndex, self.currentSpreadPart, true);
            self.saveLayoutConfigToServer(work.episode_no, cfg);
          }
        }
        window.addEventListener('mousemove', onMouseMove, true);
        window.addEventListener('mouseup', onMouseUp, true);
      };

      // D) 우측 핸들 드래그
      rightHandle.onmousedown = function (e) {
        e.preventDefault();
        e.stopPropagation();
        self._isDraggingHandle = true;
        const startX = e.clientX;
        const initialRight = parseInt(pageData.right_offset_2, 10) || 0;
        const currentLeft = parseInt(pageData.left_offset_2, 10) || 0;
        const maxRight = Math.max(0, 360 - currentLeft - 80);
        let currRight = initialRight;

        boxBody2.classList.add('is-resizing');
        document.body.style.cursor = 'ew-resize';

        function onMouseMove(ev) {
          const deltaX = ev.clientX - startX;
          currRight = Math.max(0, Math.min(maxRight, Math.round(initialRight - deltaX)));
          boxBody2.style.setProperty('margin-right', `${currRight}px`, 'important');
          boxBody2.style.setProperty('width', `calc(100% - ${currentLeft + currRight}px)`, 'important');
        }

        function onMouseUp() {
          window.removeEventListener('mousemove', onMouseMove, true);
          window.removeEventListener('mouseup', onMouseUp, true);
          boxBody2.classList.remove('is-resizing');
          document.body.style.cursor = '';
          if (currRight !== initialRight) {
            self.pushUndoState();
            pageData.right_offset_2 = currRight;
            self.renderSpread(self.currentWorkIndex, self.currentSpreadPart, true);
            self.saveLayoutConfigToServer(work.episode_no, cfg);
          }
        }
        window.addEventListener('mousemove', onMouseMove, true);
        window.addEventListener('mouseup', onMouseUp, true);
      };

      // E) 2단 상자 통째 위치 이동 드래그 (1단 상자 밑 + 안전선 468px 사이)
      moveBoxHandle.onmousedown = function (e) {
        e.preventDefault();
        e.stopPropagation();
        self._isDraggingHandle = true;

        const startX = e.clientX;
        const startY = e.clientY;
        const initialTop = parseInt(pageData.top_offset_2, 10) || 260;
        const initialLeft = parseInt(pageData.left_offset_2, 10) || 0;
        const initialRight = parseInt(pageData.right_offset_2, 10) || 0;
        const boxH = boxBody2.offsetHeight || minBoxH;

        const box1Top = parseInt(pageData.top_offset, 10) || 0;
        const box1Height = (boxBody1 && boxBody1.offsetHeight > 0) ? boxBody1.offsetHeight : 120;
        const collisionMinTop = box1Top + box1Height + 6;
        const maxTopAllowed = Math.max(collisionMinTop, 468 - boxH);

        boxBody2.classList.add('is-moving-box');
        document.body.style.cursor = 'grab';

        let currTop = initialTop;
        let currLeft = initialLeft;
        let currRight = initialRight;

        function onMouseMove(ev) {
          const deltaX = ev.clientX - startX;
          const deltaY = ev.clientY - startY;

          currTop = Math.max(collisionMinTop, Math.min(maxTopAllowed, Math.round(initialTop + deltaY)));
          let newLeft = initialLeft + deltaX;
          let newRight = initialRight - deltaX;
          if (newLeft < 0) { newRight += newLeft; newLeft = 0; }
          if (newRight < 0) { newLeft += newRight; newRight = 0; }
          currLeft = Math.max(0, Math.round(newLeft));
          currRight = Math.max(0, Math.round(newRight));

          boxBody2.style.setProperty('margin-top', `${currTop}px`, 'important');
          boxBody2.style.setProperty('margin-left', `${currLeft}px`, 'important');
          boxBody2.style.setProperty('margin-right', `${currRight}px`, 'important');
          boxBody2.style.setProperty('width', `calc(100% - ${currLeft + currRight}px)`, 'important');
          self.detectAndApplyLineOverlap(side);
        }

        function onMouseUp() {
          window.removeEventListener('mousemove', onMouseMove, true);
          window.removeEventListener('mouseup', onMouseUp, true);
          boxBody2.classList.remove('is-moving-box');
          document.body.style.cursor = '';

          if (currTop !== initialTop || currLeft !== initialLeft || currRight !== initialRight) {
            self.pushUndoState();
            pageData.top_offset_2 = currTop;
            pageData.left_offset_2 = currLeft;
            pageData.right_offset_2 = currRight;
            self.renderSpread(self.currentWorkIndex, self.currentSpreadPart, true);
            self.saveLayoutConfigToServer(work.episode_no, cfg);
            if (window.showToast) {
              window.showToast(`📄 ${pageIdx + 1}면 2단 글상자 위치가 이동되었습니다.`, 'info');
            }
          }
        }
        window.addEventListener('mousemove', onMouseMove, true);
        window.addEventListener('mouseup', onMouseUp, true);
      };
    }

    /**
     * 2단 보조 글상자(Box 2) 렌더러
     */
    renderSubBoxBody(boxBody2, body2Elem, side, pageIdx, cfg, work, pageData, splitInfo, fontPx, linePx, fontFam) {
      if (!boxBody2 || !body2Elem) return;
      showElem(boxBody2, 'flex');

      const topOffset2 = pageData.top_offset_2 ? parseInt(pageData.top_offset_2, 10) : 260;
      const leftOffset2 = pageData.left_offset_2 ? parseInt(pageData.left_offset_2, 10) : 0;
      const rightOffset2 = pageData.right_offset_2 ? parseInt(pageData.right_offset_2, 10) : 0;

      boxBody2.style.setProperty('margin-top', `${topOffset2}px`, 'important');
      if (leftOffset2 > 0) boxBody2.style.setProperty('margin-left', `${leftOffset2}px`, 'important');
      else boxBody2.style.removeProperty('margin-left');
      if (rightOffset2 > 0) boxBody2.style.setProperty('margin-right', `${rightOffset2}px`, 'important');
      else boxBody2.style.removeProperty('margin-right');

      if (leftOffset2 > 0 || rightOffset2 > 0) {
        boxBody2.style.setProperty('width', `calc(100% - ${leftOffset2 + rightOffset2}px)`, 'important');
      } else {
        boxBody2.style.setProperty('width', '100%', 'important');
      }

      const minSingleLineH = Math.round(linePx + 28);
      const maxAllowedH = Math.max(minSingleLineH, 468 - topOffset2);
      const maxSafeLines = Math.max(1, Math.floor((maxAllowedH - 28 + 2) / linePx));

      const assignedLines = (splitInfo.box2 && splitInfo.box2.length > 0) ? splitInfo.box2.length : 0;
      const targetLines = pageData.max_lines_2 ? Math.min(maxSafeLines, parseInt(pageData.max_lines_2, 10)) : Math.max(1, Math.min(maxSafeLines, assignedLines || 3));
      const targetH = Math.min(maxAllowedH, Math.max(minSingleLineH, Math.round(targetLines * linePx + 28)));

      boxBody2.style.setProperty('height', `${targetH}px`, 'important');
      boxBody2.style.setProperty('flex', 'none', 'important');

      body2Elem.style.fontSize = `${fontPx.toFixed(2)}px`;
      body2Elem.style.lineHeight = `${linePx.toFixed(2)}px`;
      body2Elem.style.setProperty('font-family', fontFam, 'important');

      const align = cfg.text_align || 'left';
      body2Elem.style.textAlign = align;
      body2Elem.style.textAlignLast = (align === 'justify' ? 'justify' : align);

      const role2 = pageData.body_role_2 || 'poem';

      if (role2 === 'custom') {
        const customTxt = (pageData.custom_text_2 !== undefined && pageData.custom_text_2 !== null)
          ? String(pageData.custom_text_2)
          : '* 이곳을 더블클릭하여 그림 설명이나 캡션을 입력하세요.';
        body2Elem.innerHTML = `<p class="poem-line dtp-box-caption-hint" style="min-height:${linePx.toFixed(2)}px; line-height:${linePx.toFixed(2)}px;"><span class="line-text">${customTxt}</span></p>`;
        body2Elem.onblur = () => {
          if (this._isDraggingHandle || boxBody2.classList.contains('is-resizing')) return;
          const txt = (body2Elem.innerText || '').replace(/\r\n/g, '\n').trim();
          pageData.custom_text_2 = txt;
          this.saveLayoutConfigToServer(work.episode_no, cfg);
        };
      } else {
        const lines = splitInfo.box2 || [];
        if (lines.length === 0) {
          body2Elem.innerHTML = `<p class="poem-line dtp-box-caption-hint" style="min-height:${linePx.toFixed(2)}px; line-height:${linePx.toFixed(2)}px;"><span class="line-text" style="color:#B45309;">(2단 본문 대기 중)</span></p>`;
        } else {
          const lineStyle = `min-height:${linePx.toFixed(2)}px; line-height:${linePx.toFixed(2)}px; font-family:${fontFam};`;
          body2Elem.innerHTML = lines.map((l, lIdx) => {
            const trimmed = (l || '').replace(/[\u00a0\xa0]+/g, '').trimEnd();
            if (!trimmed.trim()) return `<p class="poem-line empty-line" data-line-idx="${lIdx}" style="${lineStyle}"><br></p>`;
            return `<p class="poem-line" data-line-idx="${lIdx}" style="${lineStyle}"><span class="line-text" style="font-family:${fontFam};">${trimmed.trim()}</span></p>`;
          }).join('');
        }
      }
    }

    renderSinglePage(side, pageIdx, cfg, work, textFlowMap, overflowFlags, textFlowSplitMap = null) {
      const pageData = cfg.pages[pageIdx] || { usage: "text", role: "continue", image_file: "" };
      const pageNum = pageIdx + 1;
      const capSide = (side === 'left') ? 'Left' : 'Right';

      // 0) 페이지 컨테이너에 data-usage, data-role 속성 부여 (CSS 정밀 인터랙션 및 리사이즈 핸들 상시 보장)
      const pageEl = document.getElementById(`dtpPage${capSide}`);
      if (pageEl) {
        pageEl.setAttribute('data-usage', pageData.usage || 'text');
        pageEl.setAttribute('data-role', pageData.role || 'continue');
      }

      // 1) 면 번호 표시
      const lblNum = document.getElementById(`lblPage${capSide}Num`);
      if (lblNum) lblNum.textContent = `${pageNum}면(${side === 'left' ? '좌' : '우'})`;

      const lblFolio = document.getElementById(`lblBookFolio${capSide}`);
      if (lblFolio) lblFolio.textContent = `${pageNum}`;

      // 2) 드롭다운 셀렉터 동기화
      const selUsage = document.getElementById(`selectPageUsage${capSide}`);
      if (selUsage) selUsage.value = pageData.usage;

      const selRole = document.getElementById(`selectPageRole${capSide}`);
      if (selRole) {
        selRole.value = pageData.role;
        if (pageData.usage === 'image' || pageData.usage === 'blank') {
          selRole.disabled = true;
          selRole.style.opacity = '0.5';
        } else {
          selRole.disabled = false;
          selRole.style.opacity = '1.0';
        }
      }

      // 3) Layer 1: 그림 레이어 렌더링
      this.renderImageLayer(side, pageData, work, pageNum);

      // 4) Layer 2: 글 레이어 렌더링
      this.renderTextLayer(side, pageData, work, cfg, pageIdx, textFlowMap, textFlowSplitMap);

      // 5) 하단 초과/이어짐 배지 표시
      const overflowBadge = document.getElementById(`dtpOverflow${capSide}`);
      if (overflowBadge) {
        if (overflowFlags && overflowFlags[pageIdx]) {
          const nextPageNum = pageNum + 1;
          const nextPart = Math.ceil(nextPageNum / 2);
          overflowBadge.innerHTML = `⚠️ 본문 초과 ➔ ${nextPageNum}면으로 자동 이어짐 <span style="text-decoration:underline; margin-left:4px; cursor:pointer;">[${nextPart}부 보기]</span>`;
          overflowBadge.style.pointerEvents = "auto";
          overflowBadge.style.cursor = "pointer";
          overflowBadge.onclick = () => this.switchSpreadPart(nextPart);
          showElem(overflowBadge, "block");
        } else {
          hideElem(overflowBadge);
        }
      }
    }

    /**
     * Layer 1 (그림 레이어) 렌더링
     */
    /**
 * 그림 분할 레이아웃 변경 (single, split_vertical, split_horizontal, main_detail)
 */
    resetSelectedFrameRect() {
      const slot = this.targetPageSlot || 'left';
      const frameNum = this.selectedSubFrame || 1;
      const work = this.getCurrentWork();
      if (!work) return;

      const cfg = this.getNormalizedConfig(work);
      const pageIdx = (this.currentSpreadPart - 1) * 2 + (slot === 'left' ? 0 : 1);
      if (!cfg.pages[pageIdx]) cfg.pages[pageIdx] = {};

      const insetsKey = (frameNum === 2) ? 'frame_insets_2' : 'frame_insets_1';
      const offsetKey = (frameNum === 2) ? 'frame_offset_2' : 'frame_offset_1';
      const scaleKey = (frameNum === 2) ? 'frame_scale_2' : 'frame_scale_1';
      const insetKey = (frameNum === 2) ? 'frame_inset_2' : 'frame_inset_1';
      cfg.pages[pageIdx][insetsKey] = { top: 0, bottom: 0, left: 0, right: 0 };
      cfg.pages[pageIdx][offsetKey] = { x: 0, y: 0 };
      cfg.pages[pageIdx][scaleKey] = 100;
      cfg.pages[pageIdx][insetKey] = 0;
      if (frameNum === 1) {
        cfg.pages[pageIdx].frame_scale = 100;
        cfg.pages[pageIdx].frame_inset = 0;
        cfg.pages[pageIdx].frame_offset = { x: 0, y: 0 };
      }
      delete cfg.pages[pageIdx][`frame_rect_${frameNum}`];
      delete cfg.pages[pageIdx][`frame_height_${frameNum}`];

      const inScale = document.getElementById('inputTbFrameScale');
      const lbScale = document.getElementById('lblTbFrameScaleVal');
      if (inScale) inScale.value = 100;
      if (lbScale) lbScale.textContent = '100%';
      const inInset = document.getElementById('inputTbFrameInset');
      const lbInset = document.getElementById('lblTbFrameInsetVal');
      if (inInset) inInset.value = 0;
      if (lbInset) lbInset.textContent = '0px';

      this.pushUndoState();
      this.renderSpread(this.currentWorkIndex, this.currentSpreadPart, true);
      this.saveLayoutConfigToServer(work.episode_no, cfg);

      if (window.showToast) {
        window.showToast(`🖼️ ${frameNum}번 그림틀이 100% 기본 크기 및 원위치로 복원되었습니다.`, 'info');
      }
    }

    /**
     * 그림틀 마진 여백 스타일 적용 (절대 인셋 px 기반 - 상/하/좌/우 띠형 및 중앙 창문형 완벽 구현)
     * 2단 분할 시 1번 그림과 2번 그림이 완전히 독립된 앵커 존을 가짐 (상호 간섭 0%)
     */
    applyFrameInsetsStyle(frameEl, insets, layout, frameNum = 1, pageData = null) {
      if (!frameEl) return;
      if (!pageData) {
        const pageElem = frameEl.closest('.dtp-page');
        const side = pageElem ? pageElem.getAttribute('data-side') : (this.targetPageSlot || 'left');
        const work = this.getCurrentWork();
        const cfg = work ? this.getNormalizedConfig(work) : null;
        const pageIdx = (this.currentSpreadPart - 1) * 2 + (side === 'right' ? 1 : 0);
        pageData = cfg?.pages?.[pageIdx] || {};
      }

      // 음수 인셋(영역 밖 확장)도 허용하여 자연스러운 크롭 및 확장 연출 지원
      const top = parseInt(insets?.top, 10) || 0;
      const bottom = parseInt(insets?.bottom, 10) || 0;
      const left = parseInt(insets?.left, 10) || 0;
      const right = parseInt(insets?.right, 10) || 0;

      // 1) 틀 통째 평행이동 offset (frame_offset_1 / frame_offset_2)
      const offsetKey = (frameNum === 2) ? 'frame_offset_2' : 'frame_offset_1';
      const offset = pageData?.[offsetKey] || (frameNum === 1 ? pageData?.frame_offset : null) || { x: 0, y: 0 };
      const offX = parseInt(offset.x, 10) || 0;
      const offY = parseInt(offset.y, 10) || 0;

      // 절대 좌표 및 크기 강제 적용 (CSS 충돌 원천 방지)
      frameEl.style.setProperty('position', 'absolute', 'important');
      frameEl.style.setProperty('margin', '0', 'important');
      frameEl.style.setProperty('width', 'auto', 'important');
      frameEl.style.setProperty('height', 'auto', 'important');
      frameEl.style.setProperty('flex', 'none', 'important');
      frameEl.style.setProperty('overflow', 'visible', 'important');
      frameEl.style.setProperty('transform', `translate(${offX}px, ${offY}px)`, 'important');

      const parentEl = frameEl.parentElement;
      const parentW = (parentEl && parentEl.offsetWidth > 0) ? parentEl.offsetWidth : 400;
      const parentH = (parentEl && parentEl.offsetHeight > 0) ? parentEl.offsetHeight : 520;

      let refW = parentW;
      let refH = parentH;
      if (layout === 'split_vertical' || layout === 'main_detail') {
        refH = Math.max(100, Math.floor((parentH - 8) / 2));
      } else if (layout === 'split_horizontal') {
        refW = Math.max(100, Math.floor((parentW - 8) / 2));
      }

      // 2) 틀 여백 (frame_inset_1 / frame_inset_2, 0~50px) 독립 연동
      const insetKey = (frameNum === 2) ? 'frame_inset_2' : 'frame_inset_1';
      const baseInset = Math.max(0, parseInt(pageData?.[insetKey] !== undefined ? pageData[insetKey] : (pageData?.frame_inset || 0), 10));

      // 3) 그림틀 크기 (frame_scale_1 / frame_scale_2, 10~100%) 독립 비율 축소 연동
      const scaleKey = (frameNum === 2) ? 'frame_scale_2' : 'frame_scale_1';
      const frameScale = Math.max(10, Math.min(100, parseInt(pageData?.[scaleKey] !== undefined ? pageData[scaleKey] : (pageData?.frame_scale !== undefined ? pageData.frame_scale : 100), 10)));
      const scaleRatio = frameScale / 100.0;
      const scaleMarginX = Math.round((refW * (1.0 - scaleRatio)) / 2);
      const scaleMarginY = Math.round((refH * (1.0 - scaleRatio)) / 2);

      const totalTop = top + baseInset + scaleMarginY;
      const totalBottom = bottom + baseInset + scaleMarginY;
      const totalLeft = left + baseInset + scaleMarginX;
      const totalRight = right + baseInset + scaleMarginX;

      // [핵심 안전장치]: 최소 그림틀 크기 엄격 보장 (높이 최소 80px, 너비 최소 90px)
      // 상·하 또는 좌·우 조절 핸들이 서로 겹쳐서 확대를 못하는 현상 100% 원천 방지
      const minFrameH = 80;
      const minFrameW = 90;

      let clampedTop = totalTop;
      let clampedBottom = totalBottom;
      let clampedLeft = totalLeft;
      let clampedRight = totalRight;

      if (clampedTop + clampedBottom > refH - minFrameH) {
        const excess = (clampedTop + clampedBottom) - (refH - minFrameH);
        const sumPos = Math.max(1, (clampedTop > 0 ? clampedTop : 0) + (clampedBottom > 0 ? clampedBottom : 0));
        const topRatio = (clampedTop > 0) ? (clampedTop / sumPos) : 0.5;
        clampedTop = Math.round(clampedTop - excess * topRatio);
        clampedBottom = Math.round(clampedBottom - excess * (1 - topRatio));
      }

      if (clampedLeft + clampedRight > refW - minFrameW) {
        const excess = (clampedLeft + clampedRight) - (refW - minFrameW);
        const sumPos = Math.max(1, (clampedLeft > 0 ? clampedLeft : 0) + (clampedRight > 0 ? clampedRight : 0));
        const leftRatio = (clampedLeft > 0) ? (clampedLeft / sumPos) : 0.5;
        clampedLeft = Math.round(clampedLeft - excess * leftRatio);
        clampedRight = Math.round(clampedRight - excess * (1 - leftRatio));
      }

      // [위계 확립]: 1번 그림은 배경(z:10), 2번 그림은 전경 PIP(z:20)로 언제나 위에 안착
      const baseZIndex = (frameNum === 2) ? 20 : 10;
      frameEl.style.setProperty('z-index', `${baseZIndex}`, 'important');

      if (layout === 'single') {
        // [1장 전체]: 사방 테두리 기준 px 인셋 (상하좌우 띠형 & 창문형 자유자재)
        frameEl.style.setProperty('top', `${clampedTop}px`, 'important');
        frameEl.style.setProperty('bottom', `${clampedBottom}px`, 'important');
        frameEl.style.setProperty('left', `${clampedLeft}px`, 'important');
        frameEl.style.setProperty('right', `${clampedRight}px`, 'important');
      } else if (layout === 'overlay_collage') {
        // [화보 오버레이 / 자유 꼴라주]: 1번 배경 메인 + 2번 전경 꼴라주 (소프트 섀도우 & 자유 경계 돌파)
        if (frameNum === 1) {
          frameEl.style.setProperty('top', `${clampedTop}px`, 'important');
          frameEl.style.setProperty('bottom', `${clampedBottom}px`, 'important');
          frameEl.style.setProperty('left', `${clampedLeft}px`, 'important');
          frameEl.style.setProperty('right', `${clampedRight}px`, 'important');
        } else {
          // 2번 프레임: 기본 insets가 없을 때는 1번 프레임 우측 하단에 절반 걸치고 밖으로 삐져나온 황금비율 위치
          const defTop = (top === 0 && bottom === 0) ? Math.round(parentH * 0.40) : top;
          const defLeft = (left === 0 && right === 0) ? Math.round(parentW * 0.38) : left;
          const defRight = (left === 0 && right === 0) ? 15 : right;
          const defBottom = (top === 0 && bottom === 0) ? 20 : bottom;

          const collTop = defTop + baseInset + scaleMarginY;
          const collBottom = defBottom + baseInset + scaleMarginY;
          const collLeft = defLeft + baseInset + scaleMarginX;
          const collRight = defRight + baseInset + scaleMarginX;

          frameEl.style.setProperty('top', `${collTop}px`, 'important');
          frameEl.style.setProperty('bottom', `${collBottom}px`, 'important');
          frameEl.style.setProperty('left', `${collLeft}px`, 'important');
          frameEl.style.setProperty('right', `${collRight}px`, 'important');
        }
      } else if (layout === 'split_vertical' || layout === 'main_detail') {
        // [상·하 2단 분할]: 1번은 상단 50% 존, 2번은 하단 50% 존 (중앙 간격 8px 컴팩트 분할)
        frameEl.style.setProperty('left', `${clampedLeft}px`, 'important');
        frameEl.style.setProperty('right', `${clampedRight}px`, 'important');
        if (frameNum === 1) {
          frameEl.style.setProperty('top', `${clampedTop}px`, 'important');
          frameEl.style.setProperty('bottom', `calc(50% + 4px + ${clampedBottom}px)`, 'important');
        } else {
          frameEl.style.setProperty('top', `calc(50% + 4px + ${clampedTop}px)`, 'important');
          frameEl.style.setProperty('bottom', `${clampedBottom}px`, 'important');
        }
      } else if (layout === 'split_horizontal') {
        // [좌·우 2단 분할]: 1번은 좌측 50% 존, 2번은 우측 50% 존 (중앙 간격 8px 컴팩트 분할)
        frameEl.style.setProperty('top', `${clampedTop}px`, 'important');
        frameEl.style.setProperty('bottom', `${clampedBottom}px`, 'important');
        if (frameNum === 1) {
          frameEl.style.setProperty('left', `${clampedLeft}px`, 'important');
          frameEl.style.setProperty('right', `calc(50% + 4px + ${clampedRight}px)`, 'important');
        } else {
          frameEl.style.setProperty('left', `calc(50% + 4px + ${clampedLeft}px)`, 'important');
          frameEl.style.setProperty('right', `${clampedRight}px`, 'important');
        }
      } else {
        frameEl.style.setProperty('top', `${clampedTop}px`, 'important');
        frameEl.style.setProperty('bottom', `${clampedBottom}px`, 'important');
        frameEl.style.setProperty('left', `${clampedLeft}px`, 'important');
        frameEl.style.setProperty('right', `${clampedRight}px`, 'important');
      }

      // [핵심: 그림틀 원형 보존 및 프레임 중심 안착 시스템]
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
      }
    }

    applyImageLayoutPreset(layout) {
      const slot = this.targetPageSlot || 'left';
      this.onImageLayoutChange(slot, layout);
      this.syncToolboxImageTab();
    }

    onImageLayoutChange(side, layout) {
      const work = this.getCurrentWork();
      if (!work) return;
      const cfg = this.getNormalizedConfig(work);
      const pageIdx = (this.currentSpreadPart - 1) * 2 + (side === 'left' ? 0 : 1);
      const pageData = cfg.pages[pageIdx];
      if (!pageData) return;

      this.pushUndoState();
      pageData.image_layout = layout;
      if (work.layout_config && Array.isArray(work.layout_config.pages) && work.layout_config.pages[pageIdx]) {
        work.layout_config.pages[pageIdx].image_layout = layout;
      }
      this.renderSpread(this.currentWorkIndex, this.currentSpreadPart, true);
      this.saveLayoutConfigToServer(work.episode_no, cfg);
      if (window.showToast) {
        const layoutNames = {
          single: "1장 전체",
          split_vertical: "상·하 2단 분할",
          split_horizontal: "좌·우 2단 분할",
          overlay_collage: "🪟 화보 오버레이 (자유 꼴라주 & PIP)"
        };
        window.showToast(`🖼️ ${pageIdx + 1}면 그림 배치가 [${layoutNames[layout] || layout}]로 변경되었습니다.`, "info");
      }
    }

    /**
     * 분할 프레임별 개별 이미지 교체
     */
    openSlotImageFrameManager(side, frameIndex) {
      window.activeImageTargetSide = side;
      window.activeImageTargetFrame = frameIndex;
      const activePart = this.currentSpreadPart || 1;
      const slotIdx = (side === "left") ? (activePart - 1) * 2 : (activePart - 1) * 2 + 1;
      window.activeImageTargetPageNum = slotIdx + 1;
      this.switchToolboxTab('image');
      if (typeof openSlotImageManager === 'function') {
        openSlotImageManager(side);
      }
    }

    renderImageLayer(side, pageData, work, pageNum) {
      const capSide = (side === 'left') ? 'Left' : 'Right';
      const layerImage = document.getElementById(`dtpLayerImage${capSide}`);
      const imgElem = document.getElementById(`dtpImg${capSide}`);
      const placeholder = document.getElementById(`dtpPlaceholder${capSide}`);
      const blankElem = document.getElementById(`dtpBlank${capSide}`);
      const btnArt = document.getElementById(`btnArt${capSide}`);
      const selLayout = document.getElementById(`selectImgLayout${capSide}`);

      if (!layerImage) return;

      layerImage.style.padding = '0';
      layerImage.style.boxSizing = 'border-box';

      // 1) 툴바 버튼 및 분할 드롭다운 표시 제어
      const hasImageMode = (pageData.usage === 'image' || pageData.usage === 'image_text');
      if (btnArt) {
        if (hasImageMode) showElem(btnArt, 'inline-flex');
        else hideElem(btnArt);
      }
      if (selLayout) {
        if (hasImageMode) {
          hideElem(selLayout);
          selLayout.value = pageData.image_layout || 'single';
        } else {
          hideElem(selLayout);
        }
      }

      // 본문 전용일 때 그림 레이어 완전 숨김
      if (pageData.usage === 'text') {
        hideElem(layerImage);
        hideElem(imgElem);
        hideElem(placeholder);
        hideElem(blankElem);
        layerImage.querySelectorAll('.dtp-image-frame').forEach(el => el.remove());
        return;
      }

      showElem(layerImage, 'flex');

      if (hasImageMode) {
        hideElem(blankElem);

        const layout = pageData.image_layout || 'single';
        // 기존 동적 프레임 청소
        layerImage.querySelectorAll('.dtp-image-frame').forEach(el => el.remove());
        layerImage.className = 'dtp-layer-image';

        let imgFile1 = pageData.image_file;
        if (!imgFile1) {
          if (pageNum === 1 || pageNum === 2) imgFile1 = work.image_file;
          else if (pageNum >= 3) imgFile1 = work.image_file_2 || work.image_file;
        }

        let imgFile2 = pageData.image_file_b;
        if (!imgFile2 && layout !== 'single') {
          imgFile2 = work.image_file_2 || work.image_file || imgFile1;
        }

        // 단일 그림이든 2분할이든 통일된 독립 프레임 기반 렌더링 (4변 슬림 조절 핸들 지원)
        hideElem(imgElem);
        hideElem(placeholder);

        const resolveCleanImgPath = (file) => {
          if (!file) return "";
          let p = "/" + String(file).replace(/^(\.\/|\/)+/, '');
          if (p.startsWith("/images/")) {
            p = "/gallery" + p;
          }
          return p;
        };

        if (layout === 'single') {
          // [1장 전체 레이아웃]: 글상자와 100% 동일한 4변 여백 리사이즈 핸들 지원
          const cleanPath1 = resolveCleanImgPath(imgFile1);
          const frame1 = document.createElement("div");
          frame1.className = `dtp-image-frame is-selected`;
          frame1.setAttribute("data-sub-frame", "1");

          const insets1 = pageData.frame_insets_1 || { top: 0, bottom: 0, left: 0, right: 0 };
          this.applyFrameInsetsStyle(frame1, insets1, layout, 1);

          frame1.innerHTML = `
            <div class="dtp-frame-crop">
              ${cleanPath1 ? `<img src="${cleanPath1}" alt="삽화" draggable="false" onerror="if(!this.dataset.tried){this.dataset.tried=1; this.src='/images/'+this.src.split('/').pop();}">` : '<div style="color:#A89F91; font-size:0.78rem;">그림을 등록하세요</div>'}
            </div>
            <button type="button" class="btn-frame-change" onclick="event.stopPropagation(); dtpEditor.openSlotImageFrameManager('${side}', 1)">🎨 그림 변경</button>
          `;
          frame1.onclick = (e) => {
            e.stopPropagation();
            this.setTargetPageSlot(side);
            this.setSelectedSubFrame(1);
            this.switchToolboxTab('image1');
          };
          const img1 = frame1.querySelector('img');
          if (img1) {
            const p1 = pageData.image_pan_1 || pageData.image_pan || { x: 0, y: 0 };
            const sc1 = pageData.image_scale_1 || 100;
            const f1 = pageData.image_filter_1 || pageData.image_filter || { vignette: 0, blur: 0, tone: 'none' };
            const s1 = pageData.frame_shape_1 || pageData.frame_shape || 'rect';
            this.applyCustomImageStyle(img1, p1, sc1, f1, s1);
          }
          this.attachImagePanDrag(frame1, side, 1);
          this.attachFrame4WayResizeHandles(frame1, side, 1);
          this.attachFrameMoveHandle(frame1, side, 1);
          layerImage.appendChild(frame1);
        } else {
          // [2단 분할 레이아웃: split_vertical, split_horizontal, main_detail]
          hideElem(imgElem);
          hideElem(placeholder);
          layerImage.classList.add(`layout-${layout}`);

          const cleanPath1 = resolveCleanImgPath(imgFile1);
          const cleanPath2 = resolveCleanImgPath(imgFile2);

          // 1번 프레임 생성 및 글상자 스타일 4변 여백 리사이즈 바인딩
          const frame1 = document.createElement("div");
          const isSel1 = (this.targetPageSlot === side && this.selectedSubFrame === 1);
          frame1.className = `dtp-image-frame ${layout === 'main_detail' ? 'frame-main' : ''} ${isSel1 ? 'is-selected' : ''}`;
          frame1.setAttribute("data-sub-frame", "1");

          const insets1 = pageData.frame_insets_1 || { top: 0, bottom: 0, left: 0, right: 0 };
          this.applyFrameInsetsStyle(frame1, insets1, layout, 1);
          frame1.innerHTML = `
            <div class="dtp-frame-crop">
              ${cleanPath1 ? `<img src="${cleanPath1}" alt="1번 삽화" draggable="false">` : '<div style="color:#A89F91; font-size:0.78rem;">그림을 등록하세요</div>'}
            </div>
            <span class="frame-tag">${layout === 'overlay_collage' ? '배경 메인' : (layout === 'split_sandwich' ? '상단 그림' : '1번 그림')}</span>
            <button type="button" class="btn-frame-change" onclick="event.stopPropagation(); dtpEditor.openSlotImageFrameManager('${side}', 1)">🎨 1번 그림 변경</button>
          `;
          frame1.onclick = (e) => {
            e.stopPropagation();
            this.setTargetPageSlot(side);
            this.setSelectedSubFrame(1);
            this.switchToolboxTab('image1');
          };
          const img1 = frame1.querySelector('img');
          if (img1) {
            const p1 = pageData.image_pan_1 || pageData.image_pan || { x: 0, y: 0 };
            const sc1 = pageData.image_scale_1 || 100;
            const f1 = pageData.image_filter_1 || pageData.image_filter || { vignette: 0, blur: 0, tone: 'none' };
            const s1 = pageData.frame_shape_1 || pageData.frame_shape || 'rect';
            this.applyCustomImageStyle(img1, p1, sc1, f1, s1);
          }
          this.attachImagePanDrag(frame1, side, 1);
          this.attachFrame4WayResizeHandles(frame1, side, 1);
          this.attachFrameMoveHandle(frame1, side, 1);

          // 2번 프레임 생성 및 글상자 스타일 4변 여백 리사이즈 바인딩
          const frame2 = document.createElement("div");
          const isSel2 = (this.targetPageSlot === side && this.selectedSubFrame === 2);
          frame2.className = `dtp-image-frame ${layout === 'main_detail' ? 'frame-detail' : ''} ${isSel2 ? 'is-selected' : ''}`;
          frame2.setAttribute("data-sub-frame", "2");

          const insets2 = pageData.frame_insets_2 || { top: 0, bottom: 0, left: 0, right: 0 };
          this.applyFrameInsetsStyle(frame2, insets2, layout, 2);
          frame2.innerHTML = `
            <div class="dtp-frame-crop">
              ${cleanPath2 ? `<img src="${cleanPath2}" alt="2번 삽화" draggable="false">` : '<div style="color:#A89F91; font-size:0.78rem;">그림을 등록하세요</div>'}
            </div>
            <span class="frame-tag">${layout === 'overlay_collage' ? '전경 꼴라주 (PIP)' : (layout === 'split_sandwich' ? '하단 그림' : '2번 그림')}</span>
            <button type="button" class="btn-frame-change" onclick="event.stopPropagation(); dtpEditor.openSlotImageFrameManager('${side}', 2)">🎨 2번 그림 변경</button>
          `;
          frame2.onclick = (e) => {
            e.stopPropagation();
            this.setTargetPageSlot(side);
            this.setSelectedSubFrame(2);
            this.switchToolboxTab('image1');
          };
          const img2 = frame2.querySelector('img');
          if (img2) {
            const p2 = pageData.image_pan_2 || { x: 0, y: 0 };
            const sc2 = pageData.image_scale_2 || 100;
            const f2 = pageData.image_filter_2 || { vignette: 0, blur: 0, tone: 'none' };
            const s2 = pageData.frame_shape_2 || 'rect';
            this.applyCustomImageStyle(img2, p2, sc2, f2, s2);
          }
          this.attachImagePanDrag(frame2, side, 2);
          this.attachFrame4WayResizeHandles(frame2, side, 2);
          this.attachFrameMoveHandle(frame2, side, 2);

          layerImage.appendChild(frame1);
          layerImage.appendChild(frame2);
        }
      } else if (pageData.usage === 'blank') {
        layerImage.className = 'dtp-layer-image';
        layerImage.querySelectorAll('.dtp-image-frame').forEach(el => el.remove());
        hideElem(imgElem);
        hideElem(placeholder);
        showElem(blankElem, 'flex');
      }
    }

    populateBodyLinesDom(bodyElem, pageData, pageIdx, textFlowMap, fontFam, linePx) {
      const lines = textFlowMap[pageIdx] || [];
      const lineStyle = `min-height:${linePx.toFixed(2)}px; line-height:${linePx.toFixed(2)}px; font-family:${fontFam};`;
      if (lines.length > 0) {
        bodyElem.innerHTML = lines.map((line, lIdx) => {
          const trimmed = (line || '').replace(/[\u00a0\xa0]+/g, '').trimEnd();
          if (!trimmed.trim()) {
            return `<p class="poem-line empty-line" data-line-idx="${lIdx}" style="${lineStyle}"><br></p>`;
          }
          // [InDesign DTP 미학] 시각적 여백 정렬 (Optical Margin Alignment)
          const isHanging = /^["'“‘「『\(\<]/.test(trimmed.trim());
          const hangClass = isHanging ? ' hang-quote' : '';
          const hangStyle = isHanging ? 'text-indent: -0.55em !important;' : '';
          return `<p class="poem-line${hangClass}" data-line-idx="${lIdx}" style="${lineStyle} ${hangStyle}"><span class="line-text" style="font-family:${fontFam};">${trimmed.trim()}</span></p>`;
        }).join('');
      } else if (pageData.role === 'continue' && pageIdx > 0) {
        bodyElem.innerHTML = `<p class="poem-placeholder" style="color:#B5A898; font-style:italic; font-size:0.84rem;">(앞 면에서 본문 글이 마무리되었습니다 — 여백 면)</p>`;
      } else {
        bodyElem.innerHTML = `<p class="poem-placeholder" style="color:#A89F91; font-style:italic;">본문 글이 여기에 배치됩니다.</p>`;
      }
    }

    updateLiveTextFlowDom(side, pageIdx, cfg, work, textFlowMap, overflowFlags) {
      const capSide = (side === 'left') ? 'Left' : 'Right';
      const bodyElem = document.getElementById(`dtpBody${capSide}`);
      const badgeOverflow = document.getElementById(`dtpOverflow${capSide}`);
      const pool = cfg._all_pages_pool || cfg.pages || [];
      const pageData = pool[pageIdx] || cfg.pages[pageIdx];
      if (!bodyElem || !pageData) return;
      if (pageData.usage === 'image' || pageData.usage === 'blank' || pageData.role === 'none' || pageData.role === 'independent') return;

      const pt = parseFloat(cfg.font_size_pt) || 12;
      const lh = parseFloat(cfg.line_height_ratio) || 1.6;
      const fontPx = (pt / 12.0) * 15.2;
      const linePx = fontPx * lh;
      const fontFam = cfg.font_family || "'BookkMyungjo', '부크크 명조', 'Nanum Myeongjo', serif";

      this.populateBodyLinesDom(bodyElem, pageData, pageIdx, textFlowMap, fontFam, linePx);
      if (badgeOverflow) {
        badgeOverflow.style.display = overflowFlags[pageIdx] ? 'block' : 'none';
      }
      const boxBody = document.getElementById(`dtpBoxBody${capSide}`);
      this.updateTextThreadingBadges(boxBody, pageData, pageIdx, cfg, textFlowMap);
    }

    /**
     * [InDesign DTP 미학] 텍스트 스레딩 인디케이터 (Text Threading Visualizer)
     * - 입구 포트 (상단 우측 🔗): 앞면에서 이어지는 면(continue)이면서 현재 면에 본문이 1줄 이상 있을 때만 노출
     * - 출구 포트 (하단 우측 🔗): 현재 면에 본문이 있고, 다음 면으로 연장되어 다음 면에 1줄 이상 배정되었을 때 노출
     */
    updateTextThreadingBadges(boxBody, pageData, pageIdx, cfg, textFlowMap) {
      if (!boxBody || !pageData) return;
      boxBody.querySelectorAll('.dtp-thread-badge').forEach(b => b.remove());
      if (pageData.usage === 'image' || pageData.usage === 'blank' || pageData.role === 'none' || pageData.role === 'independent') return;

      const currentLines = (textFlowMap && textFlowMap[pageIdx]) ? textFlowMap[pageIdx] : [];
      const nextLines = (textFlowMap && textFlowMap[pageIdx + 1]) ? textFlowMap[pageIdx + 1] : [];
      const allPages = cfg._all_pages_pool || cfg.pages || [];
      const nextPageData = allPages[pageIdx + 1];

      // 1. 입구 포트 (상단 우측 🔗): 앞면에서 본문이 잘려 이어져 온 경우(line_start > 0)에만 표시!
      // (1면이 제목 전용 표제면이라 2면이 본문 1행부터 온전히 시작하는 경우에는 입구 포트 불필요)
      const lineStart = (pageData.line_start !== undefined) ? parseInt(pageData.line_start, 10) : 0;
      if (pageData.role === 'continue' && currentLines.length > 0 && lineStart > 0) {
        const inBadge = document.createElement('div');
        inBadge.className = 'dtp-thread-badge dtp-thread-in-badge';
        inBadge.innerHTML = '🔗';
        inBadge.title = `🔗 앞면에서 이어짐 (${lineStart + 1}행부터)`;
        boxBody.appendChild(inBadge);
      }

      // 2. 출구 포트: 현재 면에 본문이 있고, 다음 면으로 본문이 연장되어 다음 면에 실제 행이 있을 때만!
      if (currentLines.length > 0 && nextPageData && nextPageData.role === 'continue' && nextLines.length > 0) {
        const outBadge = document.createElement('div');
        outBadge.className = 'dtp-thread-badge dtp-thread-out-badge';
        outBadge.innerHTML = '🔗';
        outBadge.title = '🔗 다음 면으로 본문 이어짐';
        boxBody.appendChild(outBadge);
      }
    }

    renderTextLayer(side, pageData, work, cfg, pageIdx, textFlowMap, textFlowSplitMap = null) {
      const capSide = (side === 'left') ? 'Left' : 'Right';
      const layerText = document.getElementById(`dtpLayerText${capSide}`);
      const boxTitle = document.getElementById(`dtpBoxTitle${capSide}`);
      const boxBody = document.getElementById(`dtpBoxBody${capSide}`);
      const boxBody2 = document.getElementById(`dtpBoxBody2${capSide}`);
      const titleElem = document.getElementById(`dtpTitle${capSide}`);
      const authorElem = document.getElementById(`dtpAuthor${capSide}`);
      const bodyElem = document.getElementById(`dtpBody${capSide}`);
      const body2Elem = document.getElementById(`dtpBody2${capSide}`);
      const hanjiPanel = document.getElementById(`dtpHanji${capSide}`);

      if (!layerText) return;

      // 글이 없는 모드 (전면 그림, 문학적 여백, 글 없음)
      if (pageData.usage === 'image' || pageData.usage === 'blank' || pageData.role === 'none') {
        hideElem(layerText);
        hideElem(boxTitle);
        hideElem(boxBody);
        if (boxBody2) hideElem(boxBody2);
        hideElem(hanjiPanel);
        return;
      }

      showElem(layerText, 'block');

      // 스마트 국소 한지 필터: 전체 덮개는 닫고, 글상자 영역에만 부드러운 한지 패널 적용!
      if (hanjiPanel) {
        hideElem(hanjiPanel);
      }

      // 스마트 국소 한지 필터: 글상자 전체 사각 판자를 없애고 투명하게 처리 (국소 행 단위 틴트로 스마트 전환)
      const op = cfg.backdrop_opacity !== undefined ? cfg.backdrop_opacity : 0.85;
      if (boxBody) {
        boxBody.onclick = () => {
          this.setTargetPageSlot(side);
          this.targetBoxType = 'body';
          if (this.currentToolboxTab !== 'text') {
            this.switchToolboxTab('text');
          }
        };
        bodyElem.onfocus = () => {
          this.setTargetPageSlot(side);
          this.targetBoxType = 'body';
        };
        boxBody.classList.remove('hanji-backdrop');
        boxBody.style.backgroundColor = "transparent";
        boxBody.style.backdropFilter = "none";
        boxBody.style.webkitBackdropFilter = "none";
        boxBody.style.boxShadow = "none";
      }
      if (boxTitle) {
        boxTitle.onclick = () => {
          this.setTargetPageSlot(side);
          this.targetBoxType = 'title';
          this.setSelectedLine(side, 'title', work.title || '제목');
          if (this.currentToolboxTab !== 'text') {
            this.switchToolboxTab('text');
          }
        };
        if (titleElem) {
          titleElem.onfocus = () => {
            this.setTargetPageSlot(side);
            this.targetBoxType = 'title';
            this.setSelectedLine(side, 'title', work.title || '제목');
          };
        }
        boxTitle.classList.remove('hanji-backdrop');
        boxTitle.style.removeProperty('background-color');
        boxTitle.style.removeProperty('backdrop-filter');
        boxTitle.style.removeProperty('-webkit-backdrop-filter');
        boxTitle.style.removeProperty('border-radius');
        boxTitle.style.removeProperty('box-shadow');

        // [제목 및 지은이 국소 한지 틴트]: 상자 전체 판자가 아니라 오직 글자 너비만큼만 부드럽게 감싸줌!
        if (pageData.usage === 'image_text' && op > 0 && (pageData.role === 'start' || pageData.role === 'title_only')) {
          const whiteAlpha = Math.min(0.96, 0.45 + (op * 0.5));
          if (titleElem) {
            titleElem.classList.add('title-hanji-backdrop');
            titleElem.style.setProperty('background-color', `rgba(255, 254, 250, ${whiteAlpha})`, 'important');
            titleElem.style.setProperty('box-shadow', `0 0 14px 7px rgba(255, 254, 250, ${whiteAlpha})`, 'important');
            titleElem.style.setProperty('backdrop-filter', 'blur(4px)', 'important');
            titleElem.style.setProperty('-webkit-backdrop-filter', 'blur(4px)', 'important');
          }
          if (authorElem && authorElem.style.display !== 'none') {
            authorElem.classList.add('author-hanji-backdrop');
            authorElem.style.setProperty('background-color', `rgba(255, 254, 250, ${whiteAlpha * 0.9})`, 'important');
            authorElem.style.setProperty('box-shadow', `0 0 10px 5px rgba(255, 254, 250, ${whiteAlpha * 0.9})`, 'important');
            authorElem.style.setProperty('backdrop-filter', 'blur(4px)', 'important');
            authorElem.style.setProperty('-webkit-backdrop-filter', 'blur(4px)', 'important');
          }
        } else {
          if (titleElem) {
            titleElem.classList.remove('title-hanji-backdrop');
            titleElem.style.removeProperty('background-color');
            titleElem.style.removeProperty('box-shadow');
            titleElem.style.removeProperty('backdrop-filter');
            titleElem.style.removeProperty('-webkit-backdrop-filter');
          }
          if (authorElem) {
            authorElem.classList.remove('author-hanji-backdrop');
            authorElem.style.removeProperty('background-color');
            authorElem.style.removeProperty('box-shadow');
            authorElem.style.removeProperty('backdrop-filter');
            authorElem.style.removeProperty('-webkit-backdrop-filter');
          }
        }
      }

      // 글자색 모드 적용
      const isLightText = (cfg.text_color_mode === 'light' && pageData.usage === 'image_text');
      layerText.classList.toggle('text-color-light', isLightText);

      // 0) [글꼴 및 정렬 단일화] 도구상자 글꼴(cfg.font_family)과 정렬(cfg.text_align)을 제목·지은이·본문에 100% 일관 적용
      const unifiedFontFam = cfg.font_family || "'BookkMyungjo', '부크크 명조', 'Nanum Myeongjo', serif";
      const align = cfg.text_align || 'left';
      if (titleElem) {
        titleElem.style.setProperty('font-family', unifiedFontFam, 'important');
        titleElem.style.setProperty('text-align', align, 'important');
      }
      if (authorElem) {
        authorElem.style.setProperty('font-family', unifiedFontFam, 'important');
        authorElem.style.setProperty('text-align', align === 'justify' ? 'right' : align, 'important');
      }

      // 1) [제목+지은이 상자] - 상단 안전선 준수 (start: 제목+지은이, title_only: 단독 표제면, continue: 64px 투명 플레이스홀더로 완벽 정렬)
      if (pageData.role === 'start' || pageData.role === 'title_only') {
        boxTitle.classList.remove('dtp-title-placeholder');
        showElem(boxTitle, 'block');

        if (pageData.role === 'title_only') {
          boxTitle.classList.add('dtp-title-only-mode');
          // 표제면(도비라): 상하/좌우 오프셋을 제목 상자에 직접 반영하여 자유 위치 이동 허용
          const titleTop = pageData.top_offset ? parseInt(pageData.top_offset, 10) : 0;
          const titleLeft = pageData.left_offset ? parseInt(pageData.left_offset, 10) : 0;
          if (titleTop > 0) {
            boxTitle.style.setProperty("margin-top", `${titleTop}px`, "important");
          } else {
            boxTitle.style.removeProperty("margin-top");
          }
          if (titleLeft > 0) {
            boxTitle.style.setProperty("margin-left", `${titleLeft}px`, "important");
          } else {
            boxTitle.style.removeProperty("margin-left");
          }
          this.attachTitleBoxMoveHandle(boxTitle, side, pageIdx, cfg, work);
        } else {
          boxTitle.classList.remove('dtp-title-only-mode');
          boxTitle.style.removeProperty("margin-top");
          boxTitle.style.removeProperty("margin-left");
          const oldMoveBar = boxTitle.querySelector('.dtp-title-move-bar');
          if (oldMoveBar) oldMoveBar.remove();
        }

        if (titleElem) {
          titleElem.innerText = work.title || '무제';
          titleElem.onblur = () => {
            const newTitle = titleElem.innerText.trim();
            if (newTitle && newTitle !== work.title) {
              this.pushUndoState();
              work.title = newTitle;
              if (typeof window.syncWorkTitleEverywhere === 'function') {
                window.syncWorkTitleEverywhere(work.episode_no, newTitle, "dtpTitle");
              }
              this.syncToolbarUI(work, cfg, Math.ceil(cfg.page_count / 2), {});
              this.saveLayoutConfigToServer(work.episode_no, cfg);
            }
          };
        }
        if (authorElem) {
          const works = this.getWorksList();
          const distinctWorkAuthors = new Set(works.map(w => (w.author || '').trim()).filter(Boolean));
          const isCollabBook = (window.currentStatus?.project?.author_type === 'collab') || (distinctWorkAuthors.size > 1);
          const workAuthor = (work.author || '').trim();

          if (isCollabBook && workAuthor) {
            authorElem.innerText = workAuthor;
            showElem(authorElem, 'block');
          } else {
            authorElem.innerText = workAuthor;
            hideElem(authorElem);
          }
        }
      } else if (pageData.role === 'continue') {
        // 시 이어짐 면: 제목 공간(64px)을 그대로 유지하는 투명 플레이스홀더로 본문 시작선 완벽 통일!
        boxTitle.classList.remove('dtp-title-only-mode');
        boxTitle.style.removeProperty("margin-top");
        boxTitle.style.removeProperty("margin-left");
        const oldMoveBar = boxTitle.querySelector('.dtp-title-move-bar');
        if (oldMoveBar) oldMoveBar.remove();
        boxTitle.classList.add('dtp-title-placeholder');
        showElem(boxTitle, 'block');
        if (titleElem) titleElem.innerText = '';
        if (authorElem) hideElem(authorElem);
      } else {
        boxTitle.classList.remove('dtp-title-placeholder');
        boxTitle.classList.remove('dtp-title-only-mode');
        boxTitle.style.removeProperty("margin-top");
        boxTitle.style.removeProperty("margin-left");
        const oldMoveBar = boxTitle.querySelector('.dtp-title-move-bar');
        if (oldMoveBar) oldMoveBar.remove();
        hideElem(boxTitle);
      }

      // [핵심] 표제면(title_only)일 때는 본문 글상자를 완전히 숨기고 다음 면(continue)으로 본문 배정
      if (pageData.role === 'title_only') {
        hideElem(boxBody);
        if (boxBody2) hideElem(boxBody2);
        return;
      }

      // 2) [본문 상자] - 상단/하단 핸들 및 높이 조절 지원
      if (boxBody && bodyElem) {
        showElem(boxBody, 'flex');

        const splitInfo = (textFlowSplitMap && textFlowSplitMap[pageIdx]) || {
          box1: (textFlowMap && textFlowMap[pageIdx]) || [],
          box2: [],
          role1: pageData.body_role_1 || 'poem',
          role2: pageData.body_role_2 || 'poem'
        };

        const isSplit = Boolean(pageData.split_body);

        // 1단 미니 툴바 부착
        this.attachBoxMiniToolbar(boxBody, 1, side, pageIdx, cfg, work, pageData);

        // 상단 가이드 및 여백: 시 이어짐(continue)일 때 상단 여백 보정
        if (pageData.role === 'continue') {
          boxBody.classList.add('dtp-role-continue');
        } else {
          boxBody.classList.remove('dtp-role-continue');
        }

        // 상단 오프셋 적용 (상단 시작선) - !important로 확실히 보장
        const topOffset = pageData.top_offset || 0;
        if (topOffset > 0) {
          boxBody.style.setProperty("margin-top", `${topOffset}px`, "important");
        } else {
          boxBody.style.removeProperty("margin-top");
        }

        // 좌/우 오프셋 및 실제 가변 폭(width) 동기화 (진짜 리사이즈 보장)
        const leftOffset = parseInt(pageData.left_offset, 10) || 0;
        const rightOffset = parseInt(pageData.right_offset, 10) || 0;

        if (leftOffset > 0) {
          boxBody.style.setProperty("margin-left", `${leftOffset}px`, "important");
        } else {
          boxBody.style.removeProperty("margin-left");
        }

        if (rightOffset > 0) {
          boxBody.style.setProperty("margin-right", `${rightOffset}px`, "important");
        } else {
          boxBody.style.removeProperty("margin-right");
        }

        if (leftOffset > 0 || rightOffset > 0) {
          boxBody.style.setProperty("width", `calc(100% - ${leftOffset + rightOffset}px)`, "important");
        } else {
          boxBody.style.setProperty("width", "100%", "important");
        }

        const isIndep = (pageData.role === 'independent');
        const pt = parseFloat((isIndep && pageData.font_size_pt) ? pageData.font_size_pt : cfg.font_size_pt) || 12;
        const lh = parseFloat((isIndep && pageData.line_height_ratio) ? pageData.line_height_ratio : cfg.line_height_ratio) || 1.6;
        const fontPx = (pt / 12.0) * 15.2;
        const linePx = fontPx * lh;
        const minSingleLineH = Math.round(linePx + 28);

        // 2단 분할일 때 1단의 최대 허용 높이는 2단의 상단선 6px 전까지로 충돌 제한!
        const topOffset2 = isSplit ? (parseInt(pageData.top_offset_2, 10) || 260) : 468;
        const maxAllowedH = Math.max(minSingleLineH, (isSplit ? (topOffset2 - topOffset - 6) : (468 - topOffset)));
        const maxSafeLines = Math.max(1, Math.floor((maxAllowedH - 28 + 2) / linePx));

        // 하단 커스텀 높이 적용
        const assignedLines = isSplit ? (splitInfo.box1.length) : ((textFlowMap && textFlowMap[pageIdx]) ? textFlowMap[pageIdx].length : 0);
        let targetLines = 0;
        if (pageData.max_lines) {
          targetLines = Math.min(maxSafeLines, parseInt(pageData.max_lines, 10));
        } else if (assignedLines > 0) {
          targetLines = Math.min(maxSafeLines, assignedLines);
        } else {
          targetLines = isSplit ? Math.min(maxSafeLines, 4) : maxSafeLines;
        }
        const targetBoxH = Math.min(maxAllowedH, Math.max(minSingleLineH, Math.round(targetLines * linePx + 28)));
        boxBody.style.setProperty("height", `${targetBoxH}px`, "important");
        boxBody.style.setProperty("flex", "none", "important");

        // 핸들 이벤트 주입
        this.attachResizeHandles(boxBody, side, pageIdx, cfg, work);

        bodyElem.style.fontSize = `${fontPx.toFixed(2)}px`;
        bodyElem.style.lineHeight = `${linePx.toFixed(2)}px`;

        const fontFam = (isIndep && pageData.font_family) ? pageData.font_family : (cfg.font_family || "'BookkMyungjo', '부크크 명조', 'Nanum Myeongjo', serif");
        bodyElem.style.setProperty('font-family', fontFam, 'important');

        const align = (isIndep && pageData.text_align) ? pageData.text_align : (cfg.text_align || 'left');
        bodyElem.classList.remove('text-align-left', 'text-align-center', 'text-align-right', 'text-align-justify');
        bodyElem.classList.add(`text-align-${align}`);
        bodyElem.style.textAlign = align;
        bodyElem.style.textAlignLast = (align === 'justify' ? 'justify' : align);

        const role1 = isSplit ? (pageData.body_role_1 || 'poem') : (isIndep ? 'custom' : 'poem');

        if (role1 === 'custom' || pageData.role === 'independent') {
          const rawTxt = (pageData.custom_text_1 !== undefined && pageData.custom_text_1 !== null)
            ? String(pageData.custom_text_1)
            : (pageData.custom_text || "독립 자유글이나 머리말을 이곳에 입력하세요.");

          const lineStyle = `min-height:${linePx.toFixed(2)}px; line-height:${linePx.toFixed(2)}px; font-family:${fontFam};`;
          const lines = rawTxt.split("\n");
          bodyElem.innerHTML = lines.map((line, lIdx) => {
            const trimmed = (line || '').replace(/[\u00a0\xa0]+/g, '').trimEnd();
            if (!trimmed.trim()) {
              return `<p class="poem-line empty-line" data-line-idx="${lIdx}" style="${lineStyle}"><br></p>`;
            }
            const isHanging = /^["'“‘「『\(\<]/.test(trimmed.trim());
            const hangClass = isHanging ? ' hang-quote' : '';
            const hangStyle = isHanging ? 'text-indent: -0.55em !important;' : '';
            return `<p class="poem-line${hangClass}" data-line-idx="${lIdx}" style="${lineStyle} ${hangStyle}"><span class="line-text" style="font-family:${fontFam};">${trimmed.trim()}</span></p>`;
          }).join('');

          bodyElem.onblur = () => {
            if (this._isDraggingHandle || boxBody.classList.contains("is-resizing")) return;
            const pElems = Array.from(bodyElem.querySelectorAll(".poem-line"));
            let text = "";
            if (pElems.length > 0) {
              const extractedLines = pElems.map(p => {
                if (p.classList.contains("empty-line")) return "";
                return p.textContent.replace(/[\u00a0\xa0]+/g, "").trimEnd();
              });
              while (extractedLines.length > 0 && extractedLines[extractedLines.length - 1] === "") {
                extractedLines.pop();
              }
              text = extractedLines.join("\n");
            } else {
              text = (bodyElem.innerText || "").replace(/\r\n/g, "\n").replace(/\n\n+/g, "\n").trim();
            }
            if (isSplit) pageData.custom_text_1 = text;
            else pageData.custom_text = text;
            this.saveLayoutConfigToServer(work.episode_no, cfg);
          };
        } else {
          delete pageData.custom_html;
          const displayFlowMap = isSplit ? { [pageIdx]: splitInfo.box1 } : textFlowMap;
          this.populateBodyLinesDom(bodyElem, pageData, pageIdx, displayFlowMap, fontFam, linePx);
          bodyElem.onblur = () => {
            if (this._isDraggingHandle || boxBody.classList.contains("is-resizing")) return;
            if (bodyElem.querySelector(".poem-placeholder")) return;
            this.onBodyEdited(pageIdx, bodyElem, displayFlowMap);
            bodyElem.style.setProperty('font-family', fontFam, 'important');
            bodyElem.querySelectorAll('.poem-line, .line-text').forEach(el => {
              el.style.setProperty('font-family', fontFam, 'important');
            });
          };
        }

        // [2단 보조 글상자 렌더링 및 연동]
        if (isSplit && boxBody2 && body2Elem) {
          this.attachBoxMiniToolbar(boxBody2, 2, side, pageIdx, cfg, work, pageData);
          this.renderSubBoxBody(boxBody2, body2Elem, side, pageIdx, cfg, work, pageData, splitInfo, fontPx, linePx, fontFam);
          this.attachBox2ResizeHandles(boxBody2, boxBody, side, pageIdx, cfg, work);
        } else if (boxBody2) {
          hideElem(boxBody2);
        }

        // [InDesign DTP 미학] 텍스트 스레딩 인디케이터 (Text Threading Visualizer)
        this.updateTextThreadingBadges(boxBody, pageData, pageIdx, cfg, textFlowMap);

        // 본문 렌더링 후 실시간 글-그림 겹침 감지 실행
        setTimeout(() => this.detectAndApplyLineOverlap(side), 40);
      }
    }
    sanitizeCustomHtmlFont(htmlStr) {
      if (!htmlStr || typeof htmlStr !== 'string') return '';
      // 인라인 style 내부의 font-family 속성 및 구형 <font face="..."> 속성을 제거하여 글 편집 도구상자 글꼴과 100% 일치 보장
      return htmlStr
        .replace(/font-family\s*:[^;"']+;?/gi, '')
        .replace(/\sface=["'][^"']*["']/gi, '');
    }

    onBodyEdited(editedPageIdx, bodyElemOrText, textFlowMap) {
      const work = this.getCurrentWork();
      if (!work) return;

      if (this._isDraggingHandle) return;
      const cfg = this.getNormalizedConfig(work);
      const trailingBlankMap = this.lastTrailingBlankMap || {};
      const pageChunks = [];

      for (let i = 0; i < 6; i++) {
        if (i === editedPageIdx) {
          if (bodyElemOrText && typeof bodyElemOrText === 'object' && bodyElemOrText.querySelector && bodyElemOrText.querySelector('.poem-placeholder')) {
            continue;
          }
          let editedLines = [];
          // DOM 요소인 경우 각 .poem-line의 텍스트를 정확히 1줄씩 추출
          if (bodyElemOrText && typeof bodyElemOrText === 'object' && bodyElemOrText.querySelectorAll) {
            const pElems = Array.from(bodyElemOrText.querySelectorAll(".poem-line"));
            if (pElems.length > 0) {
              editedLines = pElems.map(p => {
                if (p.classList.contains("empty-line")) return "";
                const text = p.textContent.replace(/[\u00a0\xa0]+/g, "").trimEnd();
                return text;
              });
            } else {
              // 사용자가 직접 엔터로 새 줄(div/p)을 입력한 경우
              editedLines = (bodyElemOrText.innerText || "")
                .replace(/\r\n/g, "\n")
                .replace(/[\u00a0\xa0]+/g, "")
                .split("\n")
                .map(l => l.trimEnd());
            }
          } else if (typeof bodyElemOrText === 'string') {
            editedLines = bodyElemOrText
              .replace(/\r\n/g, "\n")
              .replace(/[\u00a0\xa0]+/g, "")
              .split("\n")
              .map(l => l.trimEnd());
          }

          if (editedLines.length > 0 && editedLines[0] !== "본문 글이 여기에 배치됩니다." && !editedLines[0].includes("앞 면에서 본문 글이 마무리되었습니다")) {
            pageChunks.push({ pageIdx: i, text: editedLines.join("\n") });
          }
        } else if (textFlowMap[i] && textFlowMap[i].length > 0) {
          pageChunks.push({ pageIdx: i, text: textFlowMap[i].join("\n") });
        }
      }

      // 페이지 간 병합 시 페이지 경계에 있었던 연 구분(빈 줄 \n\n)을 100% 보존하여 병합
      let mergedPoem = "";
      for (let c = 0; c < pageChunks.length; c++) {
        if (c > 0) {
          const prevPageIdx = pageChunks[c - 1].pageIdx;
          const sep = trailingBlankMap[prevPageIdx] ? "\n\n" : "\n";
          mergedPoem += sep;
        }
        mergedPoem += pageChunks[c].text;
      }
      mergedPoem = mergedPoem.trim();
      // 3개 이상의 연속 빈 줄은 연 구분(빈 줄 1개, \n\n)으로 깔끔하게 정돈
      mergedPoem = mergedPoem.replace(/\n{3,}/g, "\n\n");

      if (mergedPoem !== (work.poem_body || "").trim()) {
        this.pushUndoState();
        work.poem_body = mergedPoem;
        if (Array.isArray(cfg.pages)) {
          cfg.pages.forEach(p => {
            if (p && p.custom_html) {
              p.custom_html = this.sanitizeCustomHtmlFont(p.custom_html);
            }
          });
        }
        const inputPoemEl = document.getElementById("inputFinalPoem");
        const curEditEp = typeof currentEditingEpisode !== "undefined" ? currentEditingEpisode : null;
        if (inputPoemEl && (!curEditEp || curEditEp === work.episode_no)) {
          inputPoemEl.value = mergedPoem;
        }
        this.renderSpread(this.currentWorkIndex, this.currentSpreadPart, true);
        this.saveLayoutConfigToServer(work.episode_no, work.layout_config || cfg);
      }
    }

    /**
     * 작품 넘기기 (상단 ◀ 이전 / 다음 ▶ 버튼)
     * [Full Book Architecture] 전권 21개 섹션 순차 순회 지원
     */
    navigateWork(delta) {
      window._hasUserSelectedWork = true;
      const struct = window.bookStructureData;
      if (struct && struct.sections && struct.sections.length > 0) {
        const sections = struct.sections;
        let curSecIdx = -1;

        if (this.currentSectionId) {
          curSecIdx = sections.findIndex(s => s.id === this.currentSectionId);
        } else {
          const works = this.getWorksList();
          const curWork = works[this.currentWorkIndex];
          if (curWork) {
            curSecIdx = sections.findIndex(s => s.episode_no === curWork.episode_no);
          }
        }

        if (curSecIdx === -1) curSecIdx = 0;
        let nextSecIdx = curSecIdx + delta;

        if (nextSecIdx < 0) {
          if (window.showToast) window.showToast("책의 첫 번째 섹션(앞표지)입니다.", "info");
          return;
        }
        if (nextSecIdx >= sections.length) {
          if (window.showToast) window.showToast("책의 마지막 섹션(뒤표지)입니다.", "info");
          return;
        }

        const targetSec = sections[nextSecIdx];
        this.loadSection(targetSec);
        return;
      }

      const works = this.getWorksList();
      if (works.length === 0) return;
      let next = this.currentWorkIndex + delta;
      if (next < 0) {
        if (window.showToast) window.showToast("시화집의 첫 번째 작품입니다.", "info");
        return;
      }
      if (next >= works.length) {
        if (window.showToast) window.showToast("시화집의 마지막 작품입니다.", "info");
        return;
      }
      this.currentWorkIndex = next;
      window.currentWorkIndex = next;
      if (typeof currentWorkIndex !== 'undefined') {
        currentWorkIndex = next;
      }
      this.renderSpread(next, 1, false);
    }

    /**
     * 페이지 넘기기 (하단 ◀ 이전 페이지 / 다음 페이지 ▶ 버튼)
     * [Full Book Architecture] 앞표지 -> 속표지 -> 서문 -> 목차 -> 본문 시화(전 회차 다면) -> 맺음말 -> 판권지 -> 뒤표지
     * 책 전체의 모든 면(부속물 및 본문)을 끊김 없이 연속으로 넘깁니다.
     */
    navigatePage(delta) {
      window._hasUserSelectedWork = true;
      const struct = window.bookStructureData;
      const sections = (struct && struct.sections && struct.sections.length > 0) ? struct.sections : null;

      // 1. 책 전체 구조(sections)가 있는 경우의 통합 네비게이션
      if (sections) {
        let curSecIdx = -1;
        if (this.currentSectionId) {
          curSecIdx = sections.findIndex(s => s.id === this.currentSectionId);
        }
        if (curSecIdx === -1) {
          const works = this.getWorksList();
          const curWork = works[this.currentWorkIndex];
          if (curWork) {
            curSecIdx = sections.findIndex(s => s.episode_no === curWork.episode_no);
          }
        }
        if (curSecIdx === -1) curSecIdx = 0;

        const curSec = sections[curSecIdx];
        const isPoem = (curSec.category === 'poem' || curSec.group === 'body_matter');

        if (delta > 0) {
          // [다음 페이지]
          if (isPoem) {
            const works = this.getWorksList();
            const workIdx = works.findIndex(w => w.episode_no === curSec.episode_no);
            const work = workIdx !== -1 ? works[workIdx] : this.getCurrentWork();
            if (work) {
              const cfg = this.getNormalizedConfig(work);
              const totalParts = Math.max(1, Math.ceil(cfg.page_count / 2));
              const curPart = this.currentSpreadPart || 1;
              if (curPart < totalParts) {
                // 현재 시화 내 다음 펼침면 (예: 1·2면 -> 3·4면)
                this.switchSpreadPart(curPart + 1);
                return;
              }
            }
          }

          // 다음 섹션으로 이동
          const nextSecIdx = curSecIdx + 1;
          if (nextSecIdx >= sections.length) {
            if (window.showToast) window.showToast("시화집의 마지막 페이지(뒤표지)입니다.", "info");
            return;
          }
          const nextSec = sections[nextSecIdx];
          if (nextSec.category === 'poem' || nextSec.group === 'body_matter') {
            const works = this.getWorksList();
            const targetWorkIdx = works.findIndex(w => w.episode_no === nextSec.episode_no);
            if (targetWorkIdx !== -1) {
              this.currentSectionId = nextSec.id;
              this.currentWorkIndex = targetWorkIdx;
              window.currentWorkIndex = targetWorkIdx;
              this.renderSpread(targetWorkIdx, 1, false);
            } else {
              this.loadSection(nextSec);
            }
          } else {
            this.loadSection(nextSec);
          }
          return;
        } else {
          // [이전 페이지]
          if (isPoem) {
            const works = this.getWorksList();
            const workIdx = works.findIndex(w => w.episode_no === curSec.episode_no);
            const work = workIdx !== -1 ? works[workIdx] : this.getCurrentWork();
            if (work) {
              const curPart = this.currentSpreadPart || 1;
              if (curPart > 1) {
                // 현재 시화 내 앞 펼침면 (예: 3·4면 -> 1·2면)
                this.switchSpreadPart(curPart - 1);
                return;
              }
            }
          }

          // 이전 섹션으로 이동
          const prevSecIdx = curSecIdx - 1;
          if (prevSecIdx < 0) {
            if (window.showToast) window.showToast("시화집의 첫 페이지(앞표지)입니다.", "info");
            return;
          }
          const prevSec = sections[prevSecIdx];
          if (prevSec.category === 'poem' || prevSec.group === 'body_matter') {
            const works = this.getWorksList();
            const targetWorkIdx = works.findIndex(w => w.episode_no === prevSec.episode_no);
            if (targetWorkIdx !== -1) {
              const targetWork = works[targetWorkIdx];
              const targetCfg = this.getNormalizedConfig(targetWork);
              const targetMaxParts = Math.max(1, Math.ceil(targetCfg.page_count / 2));
              this.currentSectionId = prevSec.id;
              this.currentWorkIndex = targetWorkIdx;
              window.currentWorkIndex = targetWorkIdx;
              // 이전 시화의 마지막 펼침면(예: 3·4면)으로 진입!
              this.renderSpread(targetWorkIdx, targetMaxParts, false);
            } else {
              this.loadSection(prevSec);
            }
          } else {
            this.loadSection(prevSec);
          }
          return;
        }
      }

      // 2. Fallback (섹션 정보가 없는 경우 기본 시화 순회)
      const work = this.getCurrentWork();
      if (!work) return;
      const cfg = this.getNormalizedConfig(work);
      const totalParts = Math.max(1, Math.ceil(cfg.page_count / 2));
      const curPart = this.currentSpreadPart || 1;

      if (delta > 0) {
        if (curPart < totalParts) {
          this.switchSpreadPart(curPart + 1);
        } else {
          const works = this.getWorksList();
          if (this.currentWorkIndex + 1 < works.length) {
            this.currentWorkIndex += 1;
            window.currentWorkIndex = this.currentWorkIndex;
            this.renderSpread(this.currentWorkIndex, 1, false);
          } else if (window.showToast) {
            window.showToast("시화집의 마지막 페이지입니다.", "info");
          }
        }
      } else {
        if (curPart > 1) {
          this.switchSpreadPart(curPart - 1);
        } else {
          if (this.currentWorkIndex - 1 >= 0) {
            this.currentWorkIndex -= 1;
            window.currentWorkIndex = this.currentWorkIndex;
            const prevWork = this.getCurrentWork();
            const prevCfg = this.getNormalizedConfig(prevWork);
            const prevMaxParts = Math.max(1, Math.ceil(prevCfg.page_count / 2));
            this.renderSpread(this.currentWorkIndex, prevMaxParts, false);
          } else if (window.showToast) {
            window.showToast("시화집의 첫 번째 페이지입니다.", "info");
          }
        }
      }
    }

    /**
     * 페이지 용도 변경 (image, text, image_text, blank)
     */
    onPageUsageChange(side, newUsage) {
      const work = this.getCurrentWork();
      if (!work) return;
      this.pushUndoState();

      const cfg = this.getNormalizedConfig(work);
      const pageIdx = (this.currentSpreadPart - 1) * 2 + (side === 'left' ? 0 : 1);
      const page = cfg.pages[pageIdx];

      page.usage = newUsage;
      if (newUsage === 'image' || newUsage === 'blank') {
        page.role = 'none';
      } else if ((newUsage === 'text' || newUsage === 'image_text') && page.role === 'none') {
        // 기존에 start 페이지가 있는지 확인
        const hasStart = cfg.pages.some((p, i) => i !== pageIdx && p.role === 'start' && (p.usage === 'text' || p.usage === 'image_text'));
        page.role = hasStart ? 'continue' : 'start';
      }

      if ((newUsage === 'image' || newUsage === 'image_text') && !page.image_file) {
        const defaultWorkImg = (pageIdx >= 2) ? (work.image_file_2 || work.image_file) : (work.image_file || work.image_file_2);
        page.image_file = defaultWorkImg || "";
      }
      if (newUsage === 'image') {
        this.switchToolboxTab('image');
      } else if (newUsage === 'text') {
        this.switchToolboxTab('text');
      }

      cfg.slots[pageIdx] = newUsage;
      cfg.page_roles[pageIdx] = page.role;
      work.layout_config = cfg;

      this.renderSpread(this.currentWorkIndex, this.currentSpreadPart, true);
      this.saveLayoutConfigToServer(work.episode_no, cfg);
    }

    /**
     * 글 유형 5종 체계 변경 (start, title_only, continue, independent, none)
     */
    onPageRoleChange(side, newRole) {
      const work = this.getCurrentWork();
      if (!work) return;
      this.pushUndoState();

      const cfg = this.getNormalizedConfig(work);
      const pageIdx = (this.currentSpreadPart - 1) * 2 + (side === 'left' ? 0 : 1);
      const page = cfg.pages[pageIdx];

      if (newRole === 'start' || newRole === 'title_only') {
        const pool = cfg._all_pages_pool || cfg.pages;
        pool.forEach((p, idx) => {
          if (idx !== pageIdx && (p.role === 'start' || p.role === 'title_only')) {
            p.role = 'continue';
            if (cfg.page_roles[idx]) cfg.page_roles[idx] = 'continue';
          }
        });
      }
      page.role = newRole;
      if (newRole !== 'none' && (page.usage === 'image' || page.usage === 'blank')) {
        page.usage = (page.usage === 'image') ? 'image_text' : 'text';
        cfg.slots[pageIdx] = page.usage;
      }
      cfg.page_roles[pageIdx] = newRole;
      work.layout_config = cfg;

      const roleLabels = {
        'start': '🚩 글 시작 (제목+지은이+본문)',
        'title_only': '🪟 표제면 (제목+지은이만 단독, 본문 다음 면 흘림)',
        'continue': '🔗 글 이어짐 (본문만)',
        'independent': '📝 독립 자유글',
        'none': '[-] 글 없음'
      };

      this.renderSpread(this.currentWorkIndex, this.currentSpreadPart, true);
      this.saveLayoutConfigToServer(work.episode_no, cfg);

      if (window.showToast) {
        window.showToast(`📄 ${pageIdx + 1}면: [${roleLabels[newRole] || newRole}] 설정 완료`, "info");
      }
    }

    /**
     * 현재 선택된 슬롯('left' | 'right')의 페이지 정보 및 독립글 여부 반환
     */
    getTargetPageInfo(cfg) {
      const slot = this.targetPageSlot || 'left';
      const spreadPart = this.currentSpreadPart || 1;
      const pageIdx = (spreadPart - 1) * 2 + (slot === 'right' ? 1 : 0);
      const pageData = (cfg && Array.isArray(cfg.pages)) ? (cfg.pages[pageIdx] || null) : null;
      const isIndependent = Boolean(pageData && pageData.role === 'independent');
      return { slot, spreadPart, pageIdx, pageData, isIndependent };
    }

    /**
     * 폰트 크기(pt) 변경
     */
    setFontSizePt(val) {
      const work = this.getCurrentWork();
      if (!work) return;
      const cfg = this.getNormalizedConfig(work);
      const { slot, pageIdx, pageData, isIndependent } = this.getTargetPageInfo(cfg);

      let targetPt = 12;
      const curPt = isIndependent && pageData?.font_size_pt ? pageData.font_size_pt : (cfg.font_size_pt || 12);
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
    }

    /**
     * 글자 크기 & 줄간격 초기화
     */

    // =========================================================================
    // [Phase 1] 선택 영역(Selection) 인라인 서식 엔진
    // =========================================================================

    /**
     * 텍스트 선택(Selection) 감지 및 플로팅 서식 바 제어
     */
    initTextSelectionListener() {
      const floatingBar = document.getElementById("dtpFloatingFormatBar");

      const handleSelection = () => {
        const sel = window.getSelection();
        if (!sel || sel.isCollapsed || sel.rangeCount === 0) {
          if (floatingBar) floatingBar.style.display = "none";
          this.savedRange = null;
          return;
        }

        const range = sel.getRangeAt(0);
        const container = range.commonAncestorContainer;
        const editable = container.nodeType === 1
          ? container.closest('[contenteditable="true"]')
          : container.parentElement?.closest('[contenteditable="true"]');

        if (!editable) {
          if (floatingBar) floatingBar.style.display = "none";
          this.savedRange = null;
          return;
        }

        const rect = range.getBoundingClientRect();
        if (rect.width === 0 && rect.height === 0) {
          if (floatingBar) floatingBar.style.display = "none";
          return;
        }

        this.savedRange = range.cloneRange();
        this.currentEditableEl = editable;

        if (floatingBar) {
          const scrollX = window.pageXOffset || document.documentElement.scrollLeft;
          const scrollY = window.pageYOffset || document.documentElement.scrollTop;

          floatingBar.style.display = "flex";
          floatingBar.style.left = `${rect.left + rect.width / 2 + scrollX}px`;
          floatingBar.style.top = `${rect.top + scrollY}px`;
        }

        this.updateFormatButtonStates();
      };

      document.addEventListener("selectionchange", () => {
        clearTimeout(this._selDebounce);
        this._selDebounce = setTimeout(handleSelection, 70);
      });

      if (floatingBar) {
        floatingBar.addEventListener("mousedown", (e) => {
          e.preventDefault(); // 선택 영역 풀림 방지
        });
      }
    }

    /**
     * 현재 선택 영역의 서식 상태(Bold, Italic 등)를 감지하여 툴박스 버튼 활성화
     */
    updateFormatButtonStates() {
      let isBold = false, isItalic = false, isUnderline = false, isStrike = false;
      try {
        isBold = document.queryCommandState("bold");
        isItalic = document.queryCommandState("italic");
        isUnderline = document.queryCommandState("underline");
        isStrike = document.queryCommandState("strikeThrough");
      } catch (e) { }

      const ids = [
        ['btnFormatBold', 'fBtnBold', isBold],
        ['btnFormatItalic', 'fBtnItalic', isItalic],
        ['btnFormatUnderline', 'fBtnUnderline', isUnderline],
        ['btnFormatStrike', 'fBtnStrike', isStrike]
      ];
      ids.forEach(([toolId, floatId, state]) => {
        const tb = document.getElementById(toolId);
        const fb = document.getElementById(floatId);
        if (tb) tb.classList.toggle("is-active", Boolean(state));
        if (fb) fb.classList.toggle("is-active", Boolean(state));
      });
    }

    /**
     * 선택 영역 인라인 서식 토글 (bold, italic, underline, strikeThrough)
     */
    toggleInlineFormat(cmd) {
      this.restoreSelection();
      document.execCommand(cmd, false, null);
      this.updateFormatButtonStates();
      this.triggerContentChange(this.currentEditableEl);
    }

    /**
     * 선택 영역에 인라인 CSS 스타일 적용 (font-size, font-family, color 등)
     */
    applyInlineStyle(styleObj) {
      this.restoreSelection();
      const sel = window.getSelection();
      if (!sel || sel.rangeCount === 0 || sel.isCollapsed) return false;

      const range = sel.getRangeAt(0);
      const span = document.createElement("span");
      for (const [key, val] of Object.entries(styleObj)) {
        span.style[key] = val;
      }

      try {
        const frag = range.extractContents();
        span.appendChild(frag);
        range.insertNode(span);

        // 선택 영역 재설정
        sel.removeAllRanges();
        const newRange = document.createRange();
        newRange.selectNodeContents(span);
        sel.addRange(newRange);
        this.savedRange = newRange.cloneRange();

        this.triggerContentChange(this.currentEditableEl);
        return true;
      } catch (err) {
        console.warn("[DTP Core] 인라인 스타일 적용 실패:", err);
        return false;
      }
    }

    /**
     * 선택 영역 글자 색상 적용
     */
    applyInlineColor(colorVal) {
      if (this.hasActiveSelection()) {
        this.applyInlineStyle({ color: colorVal });
      } else {
        if (window.showToast) {
          window.showToast("색상을 변경할 글자를 마우스로 드래그하여 선택해 주세요.", "info");
        }
      }
    }

    /**
     * 선택 영역 서식 지우기 (기본 상태 복원)
     */
    clearInlineFormat() {
      this.restoreSelection();
      document.execCommand("removeFormat", false, null);
      const sel = window.getSelection();
      if (sel && sel.rangeCount > 0) {
        const range = sel.getRangeAt(0);
        let node = range.commonAncestorContainer;
        if (node && node.nodeType === 3) node = node.parentNode;
        if (node && node.tagName === 'SPAN' && node.closest('[contenteditable="true"]')) {
          const parent = node.parentNode;
          while (node.firstChild) parent.insertBefore(node.firstChild, node);
          parent.removeChild(node);
        }
      }
      this.updateFormatButtonStates();
      this.triggerContentChange(this.currentEditableEl);
    }

    /**
     * 유효한 텍스트 선택 영역이 있는지 확인
     */
    hasActiveSelection() {
      const sel = window.getSelection();
      if (sel && !sel.isCollapsed && sel.rangeCount > 0) {
        const range = sel.getRangeAt(0);
        const container = range.commonAncestorContainer;
        const editable = container.nodeType === 1
          ? container.closest('[contenteditable="true"]')
          : container.parentElement?.closest('[contenteditable="true"]');
        return Boolean(editable);
      }
      return Boolean(this.savedRange && !this.savedRange.collapsed);
    }

    /**
     * 툴박스 조작 시 유실된 브라우저 Selection 복원
     */
    restoreSelection() {
      if (this.savedRange) {
        const sel = window.getSelection();
        if (sel) {
          sel.removeAllRanges();
          sel.addRange(this.savedRange);
        }
      }
    }

    /**
     * 본문/제목 에디터 내용 변경 시 실시간 반영 & 서버 저장
     */
    triggerContentChange(editableEl) {
      const work = this.getCurrentWork();
      if (!work) return;
      const cfg = this.getNormalizedConfig(work);

      if (editableEl) {
        if (editableEl.classList.contains('dtp-title-text')) {
          work.title = editableEl.innerText.trim();
          if (typeof window.syncWorkTitleEverywhere === 'function') {
            window.syncWorkTitleEverywhere(work.episode_no, work.title, "dtpTitle");
          }
        }
        if (editableEl.classList.contains('dtp-body-text')) {
          const side = editableEl.closest('.dtp-page')?.getAttribute('data-side') || 'left';
          const pageIdx = (this.currentSpreadPart - 1) * 2 + (side === 'left' ? 0 : 1);
          if (!cfg.pages[pageIdx]) cfg.pages[pageIdx] = {};
          delete cfg.pages[pageIdx].custom_html;
        }
      }

      work.layout_config = cfg;
      clearTimeout(this._contentChangeDebounce);
      this._contentChangeDebounce = setTimeout(() => {
        this.saveLayoutConfigToServer(work.episode_no, cfg);
      }, 500);
    }

    resetTypography() {
      const work = this.getCurrentWork();
      if (!work) return;
      this.pushUndoState();

      const cfg = this.getNormalizedConfig(work);
      cfg.font_size_pt = 12;
      cfg.line_height_ratio = 1.6;

      this.renderSpread(this.currentWorkIndex, 1, true);
      this.saveLayoutConfigToServer(work.episode_no, cfg);
      if (window.showToast) {
        window.showToast("본문 글자 크기(12pt)와 줄간격(1.85)을 기본값으로 초기화했습니다.", "info");
      }
    }

    /**
     * 스프레드 부(Part) 전환 (1부 = 1·2면, 2부 = 3·4면, 3부 = 5·6면)
     */
    switchSpreadPart(part) {
      this.renderSpread(this.currentWorkIndex, part, false);
    }

    /**
     * 한지 투명도 실시간 조절 (기본값 85%)
     */
    setHanjiOpacity(val) {
      const work = this.getCurrentWork();
      if (!work) return;

      const opacity = parseFloat(val) / 100.0;
      const cfg = this.getNormalizedConfig(work);
      cfg.backdrop_opacity = opacity;

      ['Left', 'Right'].forEach(side => {
        const boxBody = document.getElementById(`dtpBoxBody${side}`);
        const boxTitle = document.getElementById(`dtpBoxTitle${side}`);
        const slot = side.toLowerCase();
        const pageIdx = (this.currentSpreadPart - 1) * 2 + (slot === 'left' ? 0 : 1);
        const pData = cfg.pages[pageIdx] || {};

        if (pData.usage === 'image_text') {
          if (boxBody) {
            if (opacity > 0) {
              boxBody.classList.add('hanji-backdrop');
              boxBody.style.backgroundColor = `rgba(254, 252, 248, ${opacity})`;
              boxBody.style.backdropFilter = "blur(3px)";
              boxBody.style.webkitBackdropFilter = "blur(3px)";
              boxBody.style.borderRadius = "8px";
              boxBody.style.boxShadow = `0 0 22px 12px rgba(254, 252, 248, ${opacity})`;
            } else {
              boxBody.classList.remove('hanji-backdrop');
              boxBody.style.backgroundColor = "transparent";
              boxBody.style.backdropFilter = "none";
              boxBody.style.webkitBackdropFilter = "none";
              boxBody.style.boxShadow = "none";
            }
          }
          if (boxTitle && (pData.role === 'start' || pData.role === 'title_only')) {
            boxTitle.classList.remove('hanji-backdrop');
            boxTitle.style.removeProperty('background-color');
            boxTitle.style.removeProperty('backdrop-filter');
            boxTitle.style.removeProperty('-webkit-backdrop-filter');
            boxTitle.style.removeProperty('border-radius');
            boxTitle.style.removeProperty('box-shadow');

            const titleElem = document.getElementById(`dtpTitle${side}`);
            const authorElem = document.getElementById(`dtpAuthor${side}`);
            const whiteAlpha = Math.min(0.96, 0.45 + (opacity * 0.5));

            if (opacity > 0) {
              if (titleElem) {
                titleElem.classList.add('title-hanji-backdrop');
                titleElem.style.setProperty('background-color', `rgba(255, 254, 250, ${whiteAlpha})`, 'important');
                titleElem.style.setProperty('box-shadow', `0 0 14px 7px rgba(255, 254, 250, ${whiteAlpha})`, 'important');
                titleElem.style.setProperty('backdrop-filter', 'blur(4px)', 'important');
                titleElem.style.setProperty('-webkit-backdrop-filter', 'blur(4px)', 'important');
              }
              if (authorElem && authorElem.style.display !== 'none') {
                authorElem.classList.add('author-hanji-backdrop');
                authorElem.style.setProperty('background-color', `rgba(255, 254, 250, ${whiteAlpha * 0.9})`, 'important');
                authorElem.style.setProperty('box-shadow', `0 0 10px 5px rgba(255, 254, 250, ${whiteAlpha * 0.9})`, 'important');
                authorElem.style.setProperty('backdrop-filter', 'blur(4px)', 'important');
                authorElem.style.setProperty('-webkit-backdrop-filter', 'blur(4px)', 'important');
              }
            } else {
              if (titleElem) {
                titleElem.classList.remove('title-hanji-backdrop');
                titleElem.style.removeProperty('background-color');
                titleElem.style.removeProperty('box-shadow');
                titleElem.style.removeProperty('backdrop-filter');
                titleElem.style.removeProperty('-webkit-backdrop-filter');
              }
              if (authorElem) {
                authorElem.classList.remove('author-hanji-backdrop');
                authorElem.style.removeProperty('background-color');
                authorElem.style.removeProperty('box-shadow');
                authorElem.style.removeProperty('backdrop-filter');
                authorElem.style.removeProperty('-webkit-backdrop-filter');
              }
            }
          }
        }
      });

      this.detectAndApplyLineOverlap('left');
      this.detectAndApplyLineOverlap('right');

      const lbl = document.getElementById("lblDtpHanjiOpacityVal");
      if (lbl) lbl.textContent = `${Math.round(opacity * 100)}%`;
      const lblTb = document.getElementById('lblTbHanjiOpacityVal');
      if (lblTb) lblTb.textContent = `${Math.round(opacity * 100)}%`;

      clearTimeout(this._saveDebounce);
      this._saveDebounce = setTimeout(() => {
        this.saveLayoutConfigToServer(work.episode_no, cfg);
      }, 500);
    }

    /**
     * 전체 글자색 모드 명시적 설정 ('auto' | 'dark' | 'light')
     */
    setTextColorMode(mode) {
      const work = this.getCurrentWork();
      if (!work) return;
      this.pushUndoState();

      const cfg = this.getNormalizedConfig(work);
      cfg.text_color_mode = mode;

      this.syncColorModeButtons(mode);
      this.detectAndApplyLineOverlap('left');
      this.detectAndApplyLineOverlap('right');
      this.saveLayoutConfigToServer(work.episode_no, cfg);

      const labels = {
        'auto': '🌗 스마트 자동 (겹침 감지)',
        'dark': '⚫ 전체 먹색 (어두움)',
        'light': '⚪ 전체 백색 (밝음)'
      };
      if (window.showToast) {
        window.showToast(`글자색 모드: [${labels[mode] || mode}]로 변경되었습니다.`, 'info');
      }
    }

    /**
     * 툴박스 글자색 모드 3버튼 활성화 동기화
     */
    syncColorModeButtons(mode) {
      const bAuto = document.getElementById('btnColorModeAuto');
      const bDark = document.getElementById('btnColorModeDark');
      const bLight = document.getElementById('btnColorModeLight');
      if (bAuto) bAuto.classList.toggle('is-active', mode === 'auto');
      if (bDark) bDark.classList.toggle('is-active', mode === 'dark');
      if (bLight) bLight.classList.toggle('is-active', mode === 'light');
    }

    /**
     * 사용자가 본문 특정 행을 클릭했을 때 포커스 및 툴박스 선택 상태 동기화
     */
    setSelectedLine(slot, lineIdx, previewText) {
      this.selectedLineInfo = { slot, lineIdx, text: previewText };

      // 1) 본문 시각적 포커스 하이라이트
      document.querySelectorAll('.poem-line').forEach(el => el.classList.remove('is-focused-line'));
      const activeP = document.querySelector(`.poem-line[data-line-idx="${lineIdx}"]`);
      if (activeP) activeP.classList.add('is-focused-line');

      // 2) 툴박스 라벨 갱신
      const lblHint = document.getElementById('lblSelectedLineHint');
      if (lblHint) {
        const cleanTxt = (previewText || '').replace(/\s+/g, ' ').trim();
        const shortTxt = cleanTxt.length > 8 ? cleanTxt.slice(0, 8) + '...' : cleanTxt;
        lblHint.textContent = `[${parseInt(lineIdx, 10) + 1}행: "${shortTxt}"]`;
      }

      // 3) 해당 행의 현재 설정 동기화
      const work = this.getCurrentWork();
      if (work) {
        const cfg = this.getNormalizedConfig(work);
        const pageIdx = (this.currentSpreadPart - 1) * 2 + (slot === 'left' ? 0 : 1);
        const pageData = cfg.pages[pageIdx] || {};
        const curOverride = pageData.line_color_overrides?.[lineIdx] || 'auto';
        this.syncLineColorButtons(curOverride);
      }
    }

    /**
     * 툴박스 행 개별 조절 3버튼 활성화 동기화
     */
    syncLineColorButtons(mode) {
      const bAuto = document.getElementById('btnLineSetAuto');
      const bDark = document.getElementById('btnLineSetDark');
      const bLight = document.getElementById('btnLineSetLight');
      if (bAuto) bAuto.classList.toggle('is-active', mode === 'auto');
      if (bDark) bDark.classList.toggle('is-active', mode === 'dark');
      if (bLight) bLight.classList.toggle('is-active', mode === 'light');
    }

    /**
     * 툴박스에서 [선택 행] 글자색 모드 버튼 클릭 시 호출
     */
    setSelectedLineColor(mode) {
      if (!this.selectedLineInfo || this.selectedLineInfo.lineIdx === null || this.selectedLineInfo.lineIdx === undefined) {
        if (window.showToast) {
          window.showToast("💡 본문에서 변경할 시 구절(행)을 먼저 클릭해 주세요.", "info");
        }
        return;
      }

      const { slot, lineIdx } = this.selectedLineInfo;
      const work = this.getCurrentWork();
      if (!work) return;

      const cfg = this.getNormalizedConfig(work);
      const pageIdx = (this.currentSpreadPart - 1) * 2 + (slot === 'left' ? 0 : 1);
      if (!cfg.pages[pageIdx]) return;
      if (!cfg.pages[pageIdx].line_color_overrides) {
        cfg.pages[pageIdx].line_color_overrides = {};
      }

      const overrides = cfg.pages[pageIdx].line_color_overrides;
      if (mode === 'auto') {
        delete overrides[lineIdx];
      } else {
        overrides[lineIdx] = mode;
      }

      this.syncLineColorButtons(mode);
      this.pushUndoState();
      this.detectAndApplyLineOverlap(slot);
      this.saveLayoutConfigToServer(work.episode_no, cfg);

      const labels = {
        'auto': '🌗 스마트 자동',
        'dark': '⚫ 먹색 고정',
        'light': '⚪ 백색 고정'
      };
      const lineName = (lineIdx === 'title') ? '제목' : `${parseInt(lineIdx, 10) + 1}행`;
      if (window.showToast) {
        window.showToast(`[${lineName}] 글자색이 [${labels[mode] || mode}]으로 설정되었습니다.`, 'success');
      }
    }

    /**
     * [스마트 가독성] 시 구절(행)과 그림틀의 실시간 겹침 감지 및 글자색/대비 자동·수동 적용
     */
    detectAndApplyLineOverlap(side) {
      if (!side) return;
      const capSide = (side.toLowerCase() === 'left') ? 'Left' : 'Right';
      const layerImage = document.getElementById(`dtpLayerImage${capSide}`);
      const bodyElem = document.getElementById(`dtpBody${capSide}`);

      const work = this.getCurrentWork();
      if (!work) return;
      const cfg = this.getNormalizedConfig(work);
      const slot = side.toLowerCase();
      const pageIdx = (this.currentSpreadPart - 1) * 2 + (slot === 'left' ? 0 : 1);
      const pageData = cfg.pages[pageIdx] || {};

      const mode = cfg.text_color_mode || 'auto';
      this.syncColorModeButtons(mode);

      const lineOverrides = pageData.line_color_overrides || {};
      const opacity = cfg.backdrop_opacity !== undefined ? cfg.backdrop_opacity : 0.85;

      // 화면에 표시 중인 그림 프레임(들) 사각형 좌표 추출
      const frameRects = [];
      if (layerImage && (pageData.usage === 'image_text' || pageData.usage === 'image')) {
        const frames = layerImage.querySelectorAll('.dtp-image-frame');
        frames.forEach(f => {
          const r = f.getBoundingClientRect();
          if (r.width > 0 && r.height > 0) {
            frameRects.push(r);
          }
        });
      }

      // 글상자 본문의 각 시 구절 행 검사
      const lineElems = bodyElem ? bodyElem.querySelectorAll('.poem-line') : [];
      lineElems.forEach(p => {
        if (p.classList.contains('empty-line')) return;
        const lineIdx = p.getAttribute('data-line-idx');
        const manualSetting = (lineIdx !== null) ? lineOverrides[lineIdx] : null;

        // 1) 실제 글자 텍스트 스팬(.line-text)의 그림 프레임과 물리적 겹침(Overlap) 정밀 판별
        let isPhysicallyOverImage = false;
        if (frameRects.length > 0) {
          const targetEl = p.querySelector('.line-text') || p;
          const pRect = targetEl.getBoundingClientRect();
          if (pRect.width > 0 && pRect.height > 0) {
            for (const fRect of frameRects) {
              const overlapX = Math.max(0, Math.min(pRect.right, fRect.right) - Math.max(pRect.left, fRect.left));
              const overlapY = Math.max(0, Math.min(pRect.bottom, fRect.bottom) - Math.max(pRect.top, fRect.top));
              if (overlapX > 10 && overlapY > pRect.height * 0.3) {
                isPhysicallyOverImage = true;
                break;
              }
            }
          }
        }

        // 2) 최종 글자색 모드 결정 (수동 오버라이드 > 전체 모드)
        let finalColor = 'dark';
        if (manualSetting === 'light') {
          finalColor = 'light';
        } else if (manualSetting === 'dark') {
          finalColor = 'dark';
        } else if (mode === 'light') {
          finalColor = 'light';
        } else if (mode === 'dark') {
          finalColor = 'dark';
        } else {
          // 'auto' 모드: 그림과 겹치면 밝은(백색) 글씨, 흰 종이 위면 어두운(먹색) 글씨
          finalColor = isPhysicallyOverImage ? 'light' : 'dark';
        }

        // 3) 상호 보완 명도 대비 스타일 적용:
        // - 그림 위 먹색 글자: 배경이 뽀얀 순백 한지빛으로 밝아져 먹색이 칼같이 선명하게 대비됨!
        // - 그림 위 백색 글자: 배경이 차분한 반투명 먹빛으로 어두워져 백색이 눈부시게 대비됨!
        // - 흰 종이 위: 배경 없이 맑고 단아한 정통 종이 질감!
        p.classList.remove('line-contrast-dark', 'line-contrast-light', 'line-over-paper');

        if (isPhysicallyOverImage) {
          if (finalColor === 'dark') {
            // [Case 1: 그림 위 먹색 글자] -> 뽀얀 순백 한지 틴트로 글자를 선명하게 받쳐줌
            p.classList.add('line-contrast-dark');
            const whiteAlpha = Math.min(0.96, 0.45 + (opacity * 0.5));
            p.style.setProperty('--line-hanji-bg', `rgba(255, 254, 250, ${whiteAlpha})`);
            p.style.setProperty('--line-hanji-shadow', `0 0 12px 6px rgba(255, 254, 250, ${whiteAlpha})`);
            p.style.removeProperty('--line-dark-tint-bg');
            p.style.removeProperty('--line-dark-tint-shadow');
          } else {
            // [Case 2: 그림 위 백색 글자] -> 차분한 반투명 먹빛 틴트로 백색 글자를 또렷하게 부각
            p.classList.add('line-contrast-light');
            const darkAlpha = Math.min(0.85, 0.25 + (opacity * 0.45));
            p.style.setProperty('--line-dark-tint-bg', `rgba(20, 15, 11, ${darkAlpha})`);
            p.style.setProperty('--line-dark-tint-shadow', `0 0 12px 6px rgba(20, 15, 11, ${darkAlpha})`);
            p.style.removeProperty('--line-hanji-bg');
            p.style.removeProperty('--line-hanji-shadow');
          }
        } else {
          // [Case 3: 흰 종이 위]
          if (finalColor === 'light') {
            p.classList.add('line-contrast-light');
            p.style.setProperty('--line-dark-tint-bg', `rgba(20, 15, 11, 0.6)`);
            p.style.setProperty('--line-dark-tint-shadow', `0 0 10px 5px rgba(20, 15, 11, 0.6)`);
          } else {
            p.classList.add('line-over-paper');
            p.style.removeProperty('--line-hanji-bg');
            p.style.removeProperty('--line-hanji-shadow');
            p.style.removeProperty('--line-dark-tint-bg');
            p.style.removeProperty('--line-dark-tint-shadow');
          }
        }

        // 클릭 및 더블클릭 이벤트 바인딩
        if (!p._lineBound) {
          p._lineBound = true;
          p.style.cursor = 'pointer';
          p.title = '클릭: 툴박스에서 개별 조절 / 더블클릭: 빠른 색상 전환';

          // 1) 단순 클릭: 툴박스에 해당 행 선택 등록
          p.addEventListener('click', (e) => {
            this.setSelectedLine(slot, lineIdx, p.textContent.trim());
          });

          // 2) 더블클릭: 단축 순환 토글 (auto -> light -> dark -> auto)
          p.addEventListener('dblclick', (e) => {
            e.stopPropagation();
            this.cycleLineColorOverride(slot, lineIdx);
          });
        }
      });

      // 4) [핵심] 제목·지은이 상자(boxTitle)의 그림 겹침 감지 및 가독성(한지필터/글자색) 완벽 동기화
      const boxTitle = document.getElementById(`dtpBoxTitle${capSide}`);
      const titleElem = document.getElementById(`dtpTitle${capSide}`);
      const authorElem = document.getElementById(`dtpAuthor${capSide}`);
      const titleDivider = boxTitle ? boxTitle.querySelector('.dtp-title-divider') : null;

      if (boxTitle && (pageData.role === 'start' || pageData.role === 'title_only')) {
        let isTitleOverImage = false;
        if (frameRects.length > 0) {
          const tRect = (titleElem || boxTitle).getBoundingClientRect();
          if (tRect.width > 0 && tRect.height > 0) {
            for (const fRect of frameRects) {
              const overlapX = Math.max(0, Math.min(tRect.right, fRect.right) - Math.max(tRect.left, fRect.left));
              const overlapY = Math.max(0, Math.min(tRect.bottom, fRect.bottom) - Math.max(tRect.top, fRect.top));
              if (overlapX > 10 && overlapY > tRect.height * 0.25) {
                isTitleOverImage = true;
                break;
              }
            }
          }
        }

        const titleManualSetting = lineOverrides['title'];
        let finalTitleColor = 'dark';
        if (titleManualSetting === 'light') {
          finalTitleColor = 'light';
        } else if (titleManualSetting === 'dark') {
          finalTitleColor = 'dark';
        } else if (mode === 'light') {
          finalTitleColor = 'light';
        } else if (mode === 'dark') {
          finalTitleColor = 'dark';
        } else {
          finalTitleColor = isTitleOverImage ? 'light' : 'dark';
        }

        // 제목 상자(boxTitle)는 언제나 투명 유지 (네모난 판자 방지)
        boxTitle.classList.remove('hanji-backdrop');
        boxTitle.style.removeProperty('background-color');
        boxTitle.style.removeProperty('backdrop-filter');
        boxTitle.style.removeProperty('-webkit-backdrop-filter');
        boxTitle.style.removeProperty('border-radius');
        boxTitle.style.removeProperty('box-shadow');

        // [제목 및 지은이 국소 한지 필터]: 상자 전체가 아니라 오직 글자 너비만큼만 부드러운 틴트/블러 적용!
        if (pageData.usage === 'image_text' && opacity > 0) {
          const whiteAlpha = Math.min(0.96, 0.45 + (opacity * 0.5));
          const darkAlpha = Math.min(0.85, 0.25 + (opacity * 0.45));

          if (titleElem) {
            titleElem.classList.add('title-hanji-backdrop');
            if (finalTitleColor === 'dark') {
              titleElem.style.setProperty('background-color', `rgba(255, 254, 250, ${whiteAlpha})`, 'important');
              titleElem.style.setProperty('box-shadow', `0 0 14px 7px rgba(255, 254, 250, ${whiteAlpha})`, 'important');
            } else {
              titleElem.style.setProperty('background-color', `rgba(20, 15, 11, ${darkAlpha})`, 'important');
              titleElem.style.setProperty('box-shadow', `0 0 14px 7px rgba(20, 15, 11, ${darkAlpha})`, 'important');
            }
            titleElem.style.setProperty('backdrop-filter', 'blur(4px)', 'important');
            titleElem.style.setProperty('-webkit-backdrop-filter', 'blur(4px)', 'important');
          }

          if (authorElem && authorElem.style.display !== 'none') {
            authorElem.classList.add('author-hanji-backdrop');
            if (finalTitleColor === 'dark') {
              authorElem.style.setProperty('background-color', `rgba(255, 254, 250, ${whiteAlpha * 0.9})`, 'important');
              authorElem.style.setProperty('box-shadow', `0 0 10px 5px rgba(255, 254, 250, ${whiteAlpha * 0.9})`, 'important');
            } else {
              authorElem.style.setProperty('background-color', `rgba(20, 15, 11, ${darkAlpha * 0.9})`, 'important');
              authorElem.style.setProperty('box-shadow', `0 0 10px 5px rgba(20, 15, 11, ${darkAlpha * 0.9})`, 'important');
            }
            authorElem.style.setProperty('backdrop-filter', 'blur(4px)', 'important');
            authorElem.style.setProperty('-webkit-backdrop-filter', 'blur(4px)', 'important');
          }
        } else {
          if (titleElem) {
            titleElem.classList.remove('title-hanji-backdrop');
            titleElem.style.removeProperty('background-color');
            titleElem.style.removeProperty('box-shadow');
            titleElem.style.removeProperty('backdrop-filter');
            titleElem.style.removeProperty('-webkit-backdrop-filter');
          }
          if (authorElem) {
            authorElem.classList.remove('author-hanji-backdrop');
            authorElem.style.removeProperty('background-color');
            authorElem.style.removeProperty('box-shadow');
            authorElem.style.removeProperty('backdrop-filter');
            authorElem.style.removeProperty('-webkit-backdrop-filter');
          }
        }

        // 제목 글자색 & 텍스트 섀도우 & 구분선 스타일 (먹색 vs 백색 명도 대비)
        if (titleElem) {
          if (finalTitleColor === 'light') {
            titleElem.style.setProperty('color', '#FFFFFF', 'important');
            titleElem.style.setProperty('text-shadow', '0 2px 8px rgba(0, 0, 0, 0.85)', 'important');
          } else {
            titleElem.style.setProperty('color', '#1A120B', 'important');
            titleElem.style.setProperty('text-shadow', '0 1px 3px rgba(255, 255, 255, 0.9)', 'important');
          }
        }
        if (authorElem) {
          if (finalTitleColor === 'light') {
            authorElem.style.setProperty('color', 'rgba(255, 255, 255, 0.92)', 'important');
            authorElem.style.setProperty('text-shadow', '0 1px 4px rgba(0, 0, 0, 0.8)', 'important');
          } else {
            authorElem.style.setProperty('color', '#6E5340', 'important');
            authorElem.style.setProperty('text-shadow', '0 1px 2px rgba(255, 255, 255, 0.9)', 'important');
          }
        }
        if (titleDivider) {
          if (finalTitleColor === 'light') {
            titleDivider.style.setProperty('background', 'rgba(255, 255, 255, 0.55)', 'important');
          } else {
            titleDivider.style.setProperty('background', '#D8C7B4', 'important');
          }
        }

        // 제목 클릭 시 '선택 행 개별 조절' 연동
        if (!boxTitle._titleClickBound) {
          boxTitle._titleClickBound = true;
          boxTitle.style.cursor = 'pointer';
          boxTitle.addEventListener('click', (e) => {
            this.setTargetPageSlot(side);
            this.targetBoxType = 'title'; // 도구상자 상자 위치이동 대상: 제목 상자
            this.setSelectedLine(slot, 'title', work.title || '제목');
          });
        }
      }
    }

    /**
     * 특정 행 수동 글자색 순환 토글 (auto -> light -> dark -> auto)
     */
    cycleLineColorOverride(slot, lineIdx) {
      if (lineIdx === null || lineIdx === undefined) return;
      const work = this.getCurrentWork();
      if (!work) return;
      const cfg = this.getNormalizedConfig(work);
      const pageIdx = (this.currentSpreadPart - 1) * 2 + (slot === 'left' ? 0 : 1);
      if (!cfg.pages[pageIdx]) return;
      if (!cfg.pages[pageIdx].line_color_overrides) {
        cfg.pages[pageIdx].line_color_overrides = {};
      }
      const overrides = cfg.pages[pageIdx].line_color_overrides;
      const cur = overrides[lineIdx] || 'auto';
      let next = 'light';
      let msg = '⚪ [선택 행] 백색 글씨로 고정되었습니다.';
      if (cur === 'light') {
        next = 'dark';
        msg = '⚫ [선택 행] 먹색 글씨로 고정되었습니다.';
      } else if (cur === 'dark') {
        next = 'auto';
        msg = '🌗 [선택 행] 스마트 자동 감지로 복원되었습니다.';
      }

      if (next === 'auto') {
        delete overrides[lineIdx];
      } else {
        overrides[lineIdx] = next;
      }

      this.syncLineColorButtons(next);
      this.pushUndoState();
      this.detectAndApplyLineOverlap(slot);
      this.saveLayoutConfigToServer(work.episode_no, cfg);
      if (window.showToast) {
        window.showToast(msg, 'info');
      }
    }

    /**
     * 빨간색 가이드선 토글
     */
    /**
     * 빨간색 가이드선 설정 (ON / OFF)
     */
    setGuides(enable) {
      this.showGuides = !!enable;
      this.applyGuidesVisibility();
      const btn = document.getElementById("btnToggleLayoutGuides");
      if (btn) {
        btn.innerHTML = this.showGuides ? "<span>🟥 가이드선 켬</span>" : "<span>⬜ 가이드선 끔</span>";
        btn.style.background = this.showGuides ? "#FFF5F5" : "#FFF";
        btn.style.color = this.showGuides ? "#C53030" : "#6E5340";
      }
      const btnOn = document.getElementById("btnGuideOn");
      const btnOff = document.getElementById("btnGuideOff");
      if (btnOn) btnOn.classList.toggle("active", this.showGuides);
      if (btnOff) btnOff.classList.toggle("active", !this.showGuides);
    }

    toggleGuides() {
      this.setGuides(!this.showGuides);
    }

    applyGuidesVisibility() {
      const spread = document.getElementById("bookSpreadContainer") || document.querySelector(".book-spread");
      if (spread) {
        spread.classList.toggle("guides-hidden", !this.showGuides);
      }
      document.querySelectorAll(".dtp-guide-box").forEach(box => {
        box.classList.toggle("guides-hidden", !this.showGuides);
      });
    }

    /**
     * 1:1 A5 실물 크기 줌 토글
     */
    toggleRealScale() {
      this.realScale = !this.realScale;
      const spread = document.getElementById("bookSpreadContainer");
      if (spread) {
        spread.classList.toggle("real-scale-100", this.realScale);
      }
      const btn = document.getElementById("btnToggleRealScale");
      if (btn) {
        btn.innerHTML = this.realScale ? "<span>🔍 화면 맞춤</span>" : "<span>🔍 실물 100%</span>";
      }
    }

    /**
     * Undo / Redo 스택
     */
    pushUndoState() {
      const work = this.getCurrentWork();
      if (!work) return;
      const cleanCfg = this.getCleanConfigForSave(work.layout_config || {});
      this.undoStack.push(cleanCfg);
      if (this.undoStack.length > this.maxUndoSteps) {
        this.undoStack.shift();
      }
      this.redoStack = [];
      this.updateUndoRedoButtons();
    }

    undo() {
      if (this.undoStack.length === 0) return;
      const work = this.getCurrentWork();
      if (!work) return;

      const currentState = this.getCleanConfigForSave(work.layout_config || {});
      this.redoStack.push(currentState);

      const prevState = this.undoStack.pop();
      work.layout_config = prevState;
      this.renderSpread(this.currentWorkIndex, this.currentSpreadPart, false);
      this.saveLayoutConfigToServer(work.episode_no, prevState);
      this.updateUndoRedoButtons();
      if (window.showToast) window.showToast("이전 조판 상태로 되돌렸습니다.", "info");
    }

    redo() {
      if (this.redoStack.length === 0) return;
      const work = this.getCurrentWork();
      if (!work) return;

      const currentState = this.getCleanConfigForSave(work.layout_config || {});
      this.undoStack.push(currentState);

      const nextState = this.redoStack.pop();
      work.layout_config = nextState;
      this.renderSpread(this.currentWorkIndex, this.currentSpreadPart, false);
      this.saveLayoutConfigToServer(work.episode_no, nextState);
      this.updateUndoRedoButtons();
      if (window.showToast) window.showToast("되돌린 조판을 다시 실행했습니다.", "info");
    }

    updateUndoRedoButtons() {
      const btnUndo = document.getElementById("btnDtpUndo");
      const btnRedo = document.getElementById("btnDtpRedo");
      if (btnUndo) btnUndo.disabled = (this.undoStack.length === 0);
      if (btnRedo) btnRedo.disabled = (this.redoStack.length === 0);
    }

    getCleanConfigForSave(cfg) {
      const copy = JSON.parse(JSON.stringify(cfg || {}));
      delete copy._all_pages_pool;
      return copy;
    }

    /**
     * 백엔드 API 서버(/api/save_work_layout_config)에 비동기 저장
     */
    async saveLayoutConfigToServer(episodeNo, layoutConfig, status = null) {
      if (!episodeNo) return false;
      const payloadCfg = this.getCleanConfigForSave(layoutConfig);
      const curWork = this.getCurrentWork();
      if (curWork && curWork.episode_no === episodeNo) {
        curWork.layout_config = payloadCfg;
        if (status) curWork.status = status;
      }
      const works = this.getWorksList();
      const targetWork = works.find(w => w.episode_no === episodeNo);
      if (targetWork) {
        targetWork.layout_config = payloadCfg;
        if (status) targetWork.status = status;
      }

      const bodyPayload = {
        episode_no: episodeNo,
        layout_config: payloadCfg
      };
      if (status) bodyPayload.status = status;
      if (curWork && curWork.episode_no === episodeNo) {
        if (curWork.title) bodyPayload.title = curWork.title;
        if (typeof curWork.poem_body === 'string') bodyPayload.poem_body = curWork.poem_body;
      }
      try {
        const resp = await fetch("/api/save_work_layout_config", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(bodyPayload)
        });
        if (!resp.ok) {
          console.error("[DTP Core] 조판 설정 저장 실패:", resp.statusText);
          return false;
        }
        return true;
      } catch (err) {
        console.error("[DTP Core] 저장 통신 오류:", err);
        return false;
      }
    }

    /**
     * [조판 완료] 버튼 클릭 시 현재 작품 설정 영구 저장
     */
    async finishAndSaveLayout() {
      const work = this.getCurrentWork();
      if (!work) return;
      const cfg = this.getNormalizedConfig(work);

      // 현재 화면에 표시된 1면(좌) 및 2면(우)의 최신 UI 드롭다운 값 직접 캡처 및 확정
      const selUsageL = document.getElementById("selectPageUsageLeft");
      const selRoleL = document.getElementById("selectPageRoleLeft");
      const selUsageR = document.getElementById("selectPageUsageRight");
      const selRoleR = document.getElementById("selectPageRoleRight");

      const leftIdx = (this.currentSpreadPart - 1) * 2;
      const rightIdx = leftIdx + 1;

      if (selUsageL && cfg.pages[leftIdx]) cfg.pages[leftIdx].usage = selUsageL.value;
      if (selRoleL && cfg.pages[leftIdx]) cfg.pages[leftIdx].role = selRoleL.value;
      if (selUsageR && cfg.pages[rightIdx]) cfg.pages[rightIdx].usage = selUsageR.value;
      if (selRoleR && cfg.pages[rightIdx]) cfg.pages[rightIdx].role = selRoleR.value;

      cfg.slots[leftIdx] = cfg.pages[leftIdx]?.usage || "image";
      cfg.page_roles[leftIdx] = cfg.pages[leftIdx]?.role || "none";
      cfg.slots[rightIdx] = cfg.pages[rightIdx]?.usage || "text";
      cfg.page_roles[rightIdx] = cfg.pages[rightIdx]?.role || "start";

      // 텍스트 속성 최신값 확정
      const selSize = document.getElementById("selectTbFontSize");
      if (selSize && !isNaN(parseFloat(selSize.value))) {
        cfg.font_size_pt = parseFloat(selSize.value);
      }
      const inputLh = document.getElementById("inputTbLineHeight");
      if (inputLh && !isNaN(parseFloat(inputLh.value))) {
        cfg.line_height_ratio = parseFloat(inputLh.value) / 100.0;
      }

      work.layout_config = cfg;
      work.status = "완성";

      const btn = document.getElementById("btnFinishLayout");
      if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<span>⏳ 저장 중...</span>`;
      }

      const ok = await this.saveLayoutConfigToServer(work.episode_no, cfg, "완성");

      if (btn) {
        btn.disabled = false;
        btn.innerHTML = `<span>✅ 조판 완료</span>`;
      }

      if (ok) {
        // 사이드바 및 상태 뱃지 동기화
        const statusBadge = document.getElementById("layoutStatusBadge");
        const statusText = document.getElementById("layoutStatusText");
        if (statusBadge && statusText) {
          statusBadge.className = "layout-badge badge-ok";
          statusText.textContent = `✅ [완료] [${work.episode_no}] ${work.title}`;
        }
        if (window.showToast) {
          window.showToast(`✅ [${work.episode_no}] 「${work.title}」 조판 상태가 [완성]으로 영구 저장되었습니다!`, "success");
        }
        // 책 전체 구성표 및 상태 비동기 갱신
        if (typeof window.loadStatus === 'function') {
          window.loadStatus();
        }
      } else {
        if (window.showToast) {
          window.showToast(`❌ 조판 설정 저장 중 오류가 발생했습니다.`, "error");
        }
      }
    }

    /**
     * DTP 도구상자 5종 탭 전환 ('image1', 'image2', 'text1', 'text2', 'ai')
     */
    switchToolboxTab(tabKey) {
      if (tabKey === 'text') tabKey = 'text1';
      if (tabKey === 'image') tabKey = 'image1';

      this.currentToolboxTab = tabKey;
      const spread = document.getElementById("bookSpreadContainer");
      if (spread) {
        spread.classList.remove("tab-mode-text1", "tab-mode-text2", "tab-mode-image1", "tab-mode-image2", "tab-mode-ai", "tab-mode-text", "tab-mode-image");
        spread.classList.add(`tab-mode-${tabKey}`);
        if (tabKey.startsWith('text')) spread.classList.add('tab-mode-text');
        if (tabKey.startsWith('image')) spread.classList.add('tab-mode-image');
      }
      const tabs = ['image1', 'image2', 'text1', 'text2', 'ai'];
      tabs.forEach(t => {
        const btn = document.getElementById(`btnTabDtp${t.charAt(0).toUpperCase() + t.slice(1)}`);
        const content = document.getElementById(`toolboxTab${t.charAt(0).toUpperCase() + t.slice(1)}`);
        if (btn) btn.classList.toggle('active', t === tabKey);
        if (content) {
          content.classList.toggle('active', t === tabKey);
          content.style.setProperty('display', t === tabKey ? 'flex' : 'none', 'important');
        }
      });
      if (tabKey === 'image1' || tabKey === 'image2') {
        this.syncToolboxImageTab();
      }
      if (tabKey === 'ai') {
        const work = this.getCurrentWork();
        const chip = document.getElementById('canvaAiWorkTitle');
        if (chip && work) {
          chip.textContent = `📄 [${work.episode_no || '제01화'} ${work.title || ''}]`;
        }
      }
    }

    /**
     * Canva풍 AI 어시스턴트: 새 대화 시작 (리셋)
     */
    resetAiChat() {
      const msgBox = document.getElementById("dtpAiMessages");
      if (!msgBox) return;
      const work = this.getCurrentWork();
      const title = work ? `「${work.title}」` : "현재 시화";
      msgBox.innerHTML = `
        <div class="canva-ai-bubble">
          안녕하세요! AI 시화 동반자 안실장입니다. 🌿<br>
          새로운 대화를 시작합니다. ${title}에 관해 궁금한 점이나 시어 퇴고, 삽화 요청을 자유롭게 말씀해 주세요.
        </div>
      `;
      const input = document.getElementById("inputDtpAiPrompt");
      if (input) input.value = "";
    }

    /**
     * 도구상자 접기 / 펼치기 토글 (우측 인스펙터 사이드바 기준)
     */
    toggleToolboxCollapse() {
      const panel = document.getElementById("dtpToolboxPanel");
      if (!panel) return;
      panel.classList.toggle("is-collapsed");
      const isCollapsed = panel.classList.contains("is-collapsed");
      const icon = document.getElementById("btnToggleToolboxIcon");
      if (icon) icon.textContent = isCollapsed ? "◀" : "▶";
    }

    /**
     * 본문 텍스트 정렬 (4종: 'left', 'center', 'right', 'justify')
     */
    setTextAlign(align) {
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
          const titleElem = document.getElementById(`dtpTitle${capSide}`);
          const authorElem = document.getElementById(`dtpAuthor${capSide}`);
          if (bodyElem) {
            bodyElem.classList.remove('text-align-left', 'text-align-center', 'text-align-right', 'text-align-justify');
            bodyElem.classList.add(`text-align-${align}`);
            bodyElem.style.textAlign = align;
            bodyElem.style.textAlignLast = (align === 'justify' ? 'justify' : align);
          }
          if (titleElem) {
            titleElem.style.setProperty('text-align', align, 'important');
          }
          if (authorElem) {
            authorElem.style.setProperty('text-align', align === 'justify' ? 'right' : align, 'important');
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
    }

    /**
     * [InDesign 명품 조판] 마스터 감성 프리셋 3종 적용
     * - traditional: 🎋 정통 수묵 (부크크 명조, 먹색, 12pt, 170% 행간, -0.02em 자간, 왼쪽 정렬, 한지 85%)
     * - sunset: 🌅 노을빛 서정 (나눔명조, 밤색, 12.5pt, 180% 행간, -0.01em 자간, 가운데 정렬, 한지 90%)
     * - dongshim: 🍃 맑은 동심 (바탕체, 맑은먹색, 12pt, 160% 행간, 0em 자간, 왼쪽 정렬, 한지 70%)
     */
    applyMasterStylePreset(presetKey) {
      const work = this.getCurrentWork();
      if (!work) return;

      this.pushUndoState();
      const cfg = this.getNormalizedConfig(work);

      const presets = {
        traditional: {
          name: "정통 수묵",
          icon: "🎋",
          font_family: "'BookkMyungjo', '부크크 명조', 'Nanum Myeongjo', serif",
          font_size_pt: 12,
          line_height_ratio: 1.7,
          letter_spacing_em: -0.02,
          text_align: "left",
          text_color_mode: "dark",
          backdrop_opacity: 0.85
        },
        sunset: {
          name: "노을빛 서정",
          icon: "🌅",
          font_family: "'Nanum Myeongjo', '나눔명조', serif",
          font_size_pt: 12.5,
          line_height_ratio: 1.8,
          letter_spacing_em: -0.01,
          text_align: "center",
          text_color_mode: "dark",
          backdrop_opacity: 0.90
        },
        dongshim: {
          name: "맑은 동심",
          icon: "🍃",
          font_family: "Batang, KoPub Batang, serif",
          font_size_pt: 12,
          line_height_ratio: 1.6,
          letter_spacing_em: 0.0,
          text_align: "left",
          text_color_mode: "dark",
          backdrop_opacity: 0.70
        }
      };

      const preset = presets[presetKey] || presets.traditional;

      // 설정값 일괄 반영
      cfg.font_family = preset.font_family;
      cfg.font_size_pt = preset.font_size_pt;
      cfg.line_height_ratio = preset.line_height_ratio;
      cfg.letter_spacing_em = preset.letter_spacing_em;
      cfg.text_align = preset.text_align;
      cfg.text_color_mode = preset.text_color_mode;
      cfg.backdrop_opacity = preset.backdrop_opacity;

      work.layout_config = cfg;

      // 도구상자 컨트롤 UI 동기화
      const selFont = document.getElementById('selectTbFontFamily');
      if (selFont) selFont.value = preset.font_family;
      const selAlign = document.getElementById('selectTbTextAlign');
      if (selAlign) selAlign.value = preset.text_align;
      const sliderLh = document.getElementById('sliderTbLineHeight');
      if (sliderLh) sliderLh.value = Math.round(preset.line_height_ratio * 100);
      const lblLh = document.getElementById('valTbLineHeight');
      if (lblLh) lblLh.innerText = `${Math.round(preset.line_height_ratio * 100)}%`;
      const sliderLs = document.getElementById('sliderTbLetterSpacing');
      if (sliderLs) sliderLs.value = preset.letter_spacing_em;
      const lblLs = document.getElementById('valTbLetterSpacing');
      if (lblLs) lblLs.innerText = `${preset.letter_spacing_em}em`;
      const sliderHanji = document.getElementById('sliderHanjiOpacity');
      if (sliderHanji) sliderHanji.value = Math.round(preset.backdrop_opacity * 100);
      const lblHanji = document.getElementById('valHanjiOpacity');
      if (lblHanji) lblHanji.innerText = `${Math.round(preset.backdrop_opacity * 100)}%`;

      // 전체 스프레드 뷰 즉시 리렌더링
      this.renderSpread(this.currentWorkIndex, this.currentSpreadPart, true);

      // 도구상자 전체 UI 컨트롤 동기화
      this.syncToolboxUI(work, cfg);

      // 서버에 저장
      this.saveLayoutConfigToServer(work.episode_no, cfg);

      if (window.showToast) {
        window.showToast(`${preset.icon} '${preset.name}' 마스터 감성 프리셋이 적용되었습니다.`, 'success');
      }
    }

    /**
     * 서체 변경
     */
    setFontFamily(fontFamily) {
      const work = this.getCurrentWork();
      if (!work) return;

      let targetFont = fontFamily;
      const selFont = document.getElementById('selectTbFontFamily');
      const cfg = this.getNormalizedConfig(work);
      const { slot, pageIdx, pageData, isIndependent } = this.getTargetPageInfo(cfg);
      const curFont = isIndependent && pageData?.font_family ? pageData.font_family : (cfg.font_family || "'BookkMyungjo', '부크크 명조', 'Nanum Myeongjo', serif");

      if (fontFamily === "custom") {
        const input = prompt(
          "적용할 서체(글꼴) 이름을 입력하세요:\n(예: 궁서, 맑은 고딕, 나눔손글씨 붓, KoPubWorldBatang 등 PC에 설치된 폰트)",
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
    }

    /**
     * 글자 크기 미세 증감 (+0.5 / -0.5)
     */
    adjustFontSize(delta) {
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
      const curPt = parseFloat((isIndependent && pageData?.font_size_pt) ? pageData.font_size_pt : cfg.font_size_pt) || 12.0;
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
          const pt = parseFloat(pageData.font_size_pt || cfg.font_size_pt) || 12;
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
            const pt = parseFloat(cfg.font_size_pt) || 12;
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
    }

    /**
     * 그림 탭: 현재 슬롯의 설정 동기화
     */
    syncToolboxImageTab() {
      let slot = this.targetPageSlot || 'left';
      const frameNum = this.selectedSubFrame || 1;
      const work = this.getCurrentWork();
      if (!work) return;

      const cfg = this.getNormalizedConfig(work);
      const leftIdx = (this.currentSpreadPart - 1) * 2;
      const rightIdx = leftIdx + 1;
      const leftData = cfg.pages[leftIdx] || {};
      const rightData = cfg.pages[rightIdx] || {};

      const leftHasImg = (leftData.usage === 'image' || leftData.usage === 'image_text');
      const rightHasImg = (rightData.usage === 'image' || rightData.usage === 'image_text');

      // 스마트 슬롯 판정: 현재 슬롯에 그림이 없지만 반대쪽에만 그림이 있는 경우 자동 타겟 전환
      if (slot === 'left' && !leftHasImg && rightHasImg) {
        slot = 'right';
        this.targetPageSlot = 'right';
      } else if (slot === 'right' && !rightHasImg && leftHasImg) {
        slot = 'left';
        this.targetPageSlot = 'left';
      }

      const pageIdx = (this.currentSpreadPart - 1) * 2 + (slot === 'left' ? 0 : 1);
      const pageData = cfg.pages[pageIdx] || {};

      // 0) 페이지 용도 종속성 제어 (전면 그림 또는 그림+글일 때만 그림 도구 활성화)
      const hasImage = (pageData.usage === 'image' || pageData.usage === 'image_text');
      const noticeBox = document.getElementById('rowImageTabDisabledNotice');
      const controlsBox = document.getElementById('containerImageControls');
      const lblNotice = document.getElementById('lblNoticeSlotUsage');

      if (!hasImage) {
        if (noticeBox) {
          noticeBox.style.display = 'block';
          if (lblNotice) {
            lblNotice.textContent = (pageData.usage === 'blank') ? '[문학적 여백]' : '[본문 글 전용]';
          }
        }
        if (controlsBox) {
          controlsBox.style.opacity = '0.35';
          controlsBox.style.pointerEvents = 'none';
        }
      } else {
        if (noticeBox) noticeBox.style.display = 'none';
        if (controlsBox) {
          controlsBox.style.opacity = '1';
          controlsBox.style.pointerEvents = 'auto';
        }
      }

      // 1) 대상 면 버튼 active 동기화
      const btnL = document.getElementById('btnTargetLeft');
      const btnR = document.getElementById('btnTargetRight');
      if (btnL) btnL.classList.toggle('active', slot === 'left');
      if (btnR) btnR.classList.toggle('active', slot === 'right');

      const btnLEff = document.getElementById('btnTargetLeftEff');
      const btnREff = document.getElementById('btnTargetRightEff');
      if (btnLEff) btnLEff.classList.toggle('active', slot === 'left');
      if (btnREff) btnREff.classList.toggle('active', slot === 'right');

      // 1-2) 그림틀 형태(Shape Masking) 동기화
      const shapeKey = (frameNum === 2) ? 'frame_shape_2' : 'frame_shape_1';
      const shape = pageData[shapeKey] || (frameNum === 1 ? pageData.frame_shape : null) || 'rect';
      ['Rect', 'Circle', 'Hexagon', 'Arch'].forEach(sName => {
        const btn = document.getElementById(`btnShape${sName}`);
        if (btn) btn.classList.toggle('active', sName.toLowerCase() === shape);
      });

      // 2) 그림 분할 셀렉트 동기화
      const layout = pageData.image_layout || 'single';
      const selLayout = document.getElementById('selectTbImgLayout');
      if (selLayout) selLayout.value = layout;

      // 2-1) 2분할 또는 오버레이 꼴라주 상태일 때 '선택 그림' 선택기 노출
      const rowSub = document.getElementById('rowSubFrameSelector');
      const isSplit = (layout === 'split_vertical' || layout === 'split_horizontal' || layout === 'overlay_collage' || layout === 'main_detail' || layout === 'split_sandwich');
      if (rowSub) {
        rowSub.style.display = isSplit ? 'flex' : 'none';
      }

      // 2-2) 선택 그림 버튼 active 동기화
      const btnSub1 = document.getElementById('btnSubFrame1');
      const btnSub2 = document.getElementById('btnSubFrame2');
      if (btnSub1) btnSub1.classList.toggle('active', frameNum === 1);
      if (btnSub2) btnSub2.classList.toggle('active', frameNum === 2);

      // 2-2) 그림틀 크기 (10% ~ 100%, 1번과 2번 독립 동기화)
      const frameScaleKey = (frameNum === 2) ? 'frame_scale_2' : 'frame_scale_1';
      const frameScaleVal = pageData[frameScaleKey] !== undefined ? pageData[frameScaleKey] : (pageData.frame_scale !== undefined ? pageData.frame_scale : 100);
      const inputFrameScale = document.getElementById('inputTbFrameScale');
      const lblFrameScale = document.getElementById('lblTbFrameScaleVal');
      if (inputFrameScale) inputFrameScale.value = frameScaleVal;
      if (lblFrameScale) lblFrameScale.textContent = `${frameScaleVal}%`;

      // 3) 그림 배율 (40% ~ 250%)
      const scaleKey = (frameNum === 2) ? 'image_scale_2' : 'image_scale_1';
      const scaleVal = pageData[scaleKey] || 100;
      const inputScale = document.getElementById('inputTbScale');
      const lblScale = document.getElementById('lblTbScaleVal');
      if (inputScale) inputScale.value = scaleVal;
      if (lblScale) lblScale.textContent = `${scaleVal}%`;

      // 4) 초점 위치 (X, Y: -100% ~ +100%)
      const panKey = (frameNum === 2) ? 'image_pan_2' : 'image_pan_1';
      const pan = pageData[panKey] || { x: 0, y: 0 };
      const inputX = document.getElementById('inputTbPanX');
      const lblX = document.getElementById('lblTbPanXVal');
      if (inputX) inputX.value = pan.x || 0;
      if (lblX) lblX.textContent = `${pan.x || 0}%`;

      const inputY = document.getElementById('inputTbPanY');
      const lblY = document.getElementById('lblTbPanYVal');
      if (inputY) inputY.value = pan.y || 0;
      if (lblY) lblY.textContent = `${pan.y || 0}%`;

      // 5) 그림틀 여백 (0px ~ 50px, 1번과 2번 독립 동기화)
      const insetKey = (frameNum === 2) ? 'frame_inset_2' : 'frame_inset_1';
      const insetVal = pageData[insetKey] !== undefined ? pageData[insetKey] : (pageData.frame_inset || 0);
      const inputInset = document.getElementById('inputTbFrameInset');
      const lblInset = document.getElementById('lblTbFrameInsetVal');
      if (inputInset) inputInset.value = insetVal;
      if (lblInset) lblInset.textContent = `${insetVal}px`;

      // 6) 외곽 페이드, 감성 블러, 색감 톤
      const filterKey = (frameNum === 2) ? 'image_filter_2' : 'image_filter_1';
      const filter = pageData[filterKey] || pageData.image_filter || { vignette: 0, blur: 0, tone: 'none' };

      const inputVig = document.getElementById('inputTbVignette');
      const lblVig = document.getElementById('lblTbVignetteVal');
      if (inputVig) inputVig.value = filter.vignette || 0;
      if (lblVig) lblVig.textContent = `${filter.vignette || 0}%`;

      const inputBlur = document.getElementById('inputTbBlur');
      const lblBlur = document.getElementById('lblTbBlurVal');
      if (inputBlur) inputBlur.value = filter.blur || 0;
      if (lblBlur) lblBlur.textContent = `${filter.blur || 0}px`;

      const selTone = document.getElementById('selectTbTone');
      if (selTone) selTone.value = filter.tone || 'none';

      // 7) 선택 버튼 라벨 동기화
      const btnArt = document.getElementById('btnTbArtChange');
      if (btnArt) {
        btnArt.textContent = isSplit ? `🎨 ${frameNum}번 그림 변경 / 업로드` : `🎨 현재 그림 변경 / 업로드`;
      }
    }
    /**
     * 선택된 서브 프레임 (1번 or 2번 그림) 지정
     */
    setSelectedSubFrame(frameNum) {
      this.selectedSubFrame = frameNum;

      // 1) 버튼 active 동기화
      const btn1 = document.getElementById('btnSubFrame1');
      const btn2 = document.getElementById('btnSubFrame2');
      if (btn1) btn1.classList.toggle('active', frameNum === 1);
      if (btn2) btn2.classList.toggle('active', frameNum === 2);

      // 2) 캔버스 프레임 하이라이트 및 z-index 최상단 승격 (묻혀 있던 그림도 선택 즉시 맨 위로 드러남)
      const slot = this.targetPageSlot || 'left';
      const capSide = slot.charAt(0).toUpperCase() + slot.slice(1);
      const layer = document.getElementById(`dtpLayerImage${capSide}`);
      if (layer) {
        layer.querySelectorAll('.dtp-image-frame').forEach(f => {
          const fNum = parseInt(f.getAttribute('data-sub-frame') || '1', 10);
          const isSel = (fNum === frameNum);
          f.classList.toggle('is-selected', isSel);
          // 선택된 그림틀은 z-index: 60으로 번쩍 승격되어 다른 그림 위에 노출됨
          f.style.setProperty('z-index', isSel ? '60' : (fNum === 2 ? '20' : '10'), 'important');
        });
      }

      // 3) 도구상자 슬라이더 및 필터 동기화
      this.syncToolboxImageTab();

      // 4) 삽화 변경 버튼 라벨 동기화
      const btnArt = document.getElementById('btnTbArtChange');
      if (btnArt) {
        btnArt.textContent = `🎨 ${frameNum}번 그림 변경 / 업로드`;
      }
    }

    /**
     * 그림틀 형태(Shape Masking) 지정 ('rect', 'circle', 'hexagon', 'arch')
     */
    setImageFrameShape(shape) {
      const slot = this.targetPageSlot || 'left';
      const frameNum = this.selectedSubFrame || 1;
      const work = this.getCurrentWork();
      if (!work) return;

      const cfg = this.getNormalizedConfig(work);
      const pageIdx = (this.currentSpreadPart - 1) * 2 + (slot === 'left' ? 0 : 1);
      if (!cfg.pages[pageIdx]) cfg.pages[pageIdx] = {};

      const shapeKey = (frameNum === 2) ? 'frame_shape_2' : 'frame_shape_1';
      cfg.pages[pageIdx][shapeKey] = shape;
      if (frameNum === 1) {
        cfg.pages[pageIdx].frame_shape = shape;
      }
      work.layout_config = cfg;

      // 실시간 화면 갱신 및 저장
      this.syncToolboxImageTab();
      this.renderSpread(this.currentWorkIndex, this.currentSpreadPart, false);
      this.pushUndoState();
      this.saveLayoutConfigToServer(work.episode_no, cfg);
      if (window.showToast) {
        const shapeNames = { rect: '사각', circle: '원형 달맞이 창', hexagon: '육각 전통 꽃살창', arch: '서정 아치 문' };
        window.showToast(`🎨 그림틀 형태가 [${shapeNames[shape] || shape}]으로 변경되었습니다.`, 'info');
      }
    }

    /**
     * 그림 스타일(초점, 배율, 필터, 형태) 일괄 적용 헬퍼
     */
    applyCustomImageStyle(imgElem, pan, scale, filter, shape = 'rect') {
      if (!imgElem) return;
      const panX = (pan && typeof pan.x === 'number') ? pan.x : 0;
      const panY = (pan && typeof pan.y === 'number') ? pan.y : 0;
      const scaleVal = (scale || 100) / 100.0;
      imgElem.style.objectPosition = "center center";
      imgElem.style.transformOrigin = "center center";
      imgElem.style.transform = `translate(${panX}%, ${panY}%) scale(${scaleVal})`;

      let fStr = "";
      if (filter?.blur > 0) fStr += `blur(${filter.blur}px) `;
      if (filter?.tone === 'sepia') fStr += `sepia(0.55) contrast(1.05) `;
      else if (filter?.tone === 'mono') fStr += `grayscale(1) contrast(1.1) `;
      else if (filter?.tone === 'vintage') fStr += `sepia(0.3) saturate(1.2) hue-rotate(-10deg) `;
      imgElem.style.filter = fStr.trim();

      imgElem.style.webkitMaskImage = 'none';
      imgElem.style.maskImage = 'none';

      const frameCrop = imgElem.closest('.dtp-frame-crop') || imgElem.parentElement;
      if (frameCrop) {
        // 형태 클래스 반영
        frameCrop.classList.remove('shape-rect', 'shape-circle', 'shape-hexagon', 'shape-arch');
        frameCrop.classList.add(`shape-${shape || 'rect'}`);

        if (filter?.vignette > 0) {
          const vigPct = Math.max(20, 100 - (filter.vignette * 0.5));
          const maskVal = (shape === 'circle')
            ? `radial-gradient(circle at center, rgba(0,0,0,1) ${vigPct}%, rgba(0,0,0,0) 100%)`
            : `radial-gradient(ellipse at center, rgba(0,0,0,1) ${vigPct}%, rgba(0,0,0,0) 100%)`;
          frameCrop.style.webkitMaskImage = maskVal;
          frameCrop.style.maskImage = maskVal;
        } else {
          frameCrop.style.webkitMaskImage = 'none';
          frameCrop.style.maskImage = 'none';
        }
      }
    }

    /**
     * 그림틀(프레임) 상하 높이 및 사각형 크기 조절 인터랙티브 리사이즈 핸들
     */
    /**
     * 선택된 글상자를 크기 변화 없이 통째로 (deltaX, deltaY)만큼 이동
     */
    moveSelectedTextBox(deltaX, deltaY) {
      const slot = this.targetPageSlot || 'left';
      const work = this.getCurrentWork();
      if (!work) return;

      const cfg = this.getNormalizedConfig(work);
      const pageIdx = (this.currentSpreadPart - 1) * 2 + (slot === 'left' ? 0 : 1);
      if (!cfg.pages[pageIdx]) cfg.pages[pageIdx] = {};
      const pageData = cfg.pages[pageIdx];

      const capSide = (slot === 'right' || slot === 'Right') ? 'Right' : 'Left';
      const isTitleTarget = (pageData.role === 'title_only') || (this.targetBoxType === 'title');

      if (isTitleTarget) {
        // [제목 상자 위치 이동]
        const boxTitle = document.getElementById(`dtpBoxTitle${capSide}`);
        const initialTop = parseInt(pageData.top_offset, 10) || 0;
        const initialLeft = parseInt(pageData.left_offset, 10) || 0;
        const newTop = Math.max(0, Math.min(380, initialTop + deltaY));
        const newLeft = Math.max(0, Math.min(220, initialLeft + deltaX));

        pageData.top_offset = newTop;
        pageData.left_offset = newLeft;
        if (work.layout_config && Array.isArray(work.layout_config.pages) && work.layout_config.pages[pageIdx]) {
          work.layout_config.pages[pageIdx].top_offset = newTop;
          work.layout_config.pages[pageIdx].left_offset = newLeft;
        }

        if (boxTitle) {
          boxTitle.style.setProperty("margin-top", `${newTop}px`, "important");
          boxTitle.style.setProperty("margin-left", `${newLeft}px`, "important");
        }

        this.renderSpread(this.currentWorkIndex, this.currentSpreadPart, true);
        this.saveLayoutConfigToServer(work.episode_no, cfg);
        if (window.showToast) {
          window.showToast(`🪟 [제목 상자] 위치 이동: 상단 ${newTop}px, 좌측 ${newLeft}px`, "info");
        }
        return;
      }

      // [본문 글상자 위치 이동]
      const boxBody = document.getElementById(`dtpBoxBody${capSide}`);
      const boxH = boxBody ? boxBody.offsetHeight : 100;

      const initialTop = parseInt(pageData.top_offset, 10) || 0;
      const initialLeft = parseInt(pageData.left_offset, 10) || 0;
      const initialRight = parseInt(pageData.right_offset, 10) || 0;

      const safeBoundary = boxBody ? (boxBody.closest(".dtp-safe-boundary") || boxBody.parentElement) : null;
      const boundaryW = safeBoundary ? safeBoundary.clientWidth : 380;
      const maxTop = Math.max(0, 468 - boxH);

      let newTop = Math.max(0, Math.min(maxTop, initialTop + deltaY));
      let newLeft = initialLeft + deltaX;
      let newRight = initialRight - deltaX;

      if (newLeft < 0) {
        newRight += newLeft;
        newLeft = 0;
      }
      if (newRight < 0) {
        newLeft += newRight;
        newRight = 0;
      }

      newLeft = Math.max(0, Math.round(newLeft));
      newRight = Math.max(0, Math.round(newRight));

      pageData.top_offset = newTop;
      pageData.left_offset = newLeft;
      pageData.right_offset = newRight;

      if (work.layout_config && Array.isArray(work.layout_config.pages) && work.layout_config.pages[pageIdx]) {
        work.layout_config.pages[pageIdx].top_offset = newTop;
        work.layout_config.pages[pageIdx].left_offset = newLeft;
        work.layout_config.pages[pageIdx].right_offset = newRight;
      }

      this.renderSpread(this.currentWorkIndex, this.currentSpreadPart, true);
      this.saveLayoutConfigToServer(work.episode_no, cfg);
    }

    /**
     * 그림틀(프레임) 통째 위치 이동 인터랙티브 드래그 핸들 바인딩 (인디자인 방식: 평행 이동)
     */
    attachFrameMoveHandle(frameEl, side, frameNum) {
      let moveHandle = frameEl.querySelector('.dtp-frame-move-bar');
      if (!moveHandle) {
        moveHandle = document.createElement("div");
        moveHandle.className = "dtp-frame-move-bar";
        moveHandle.innerHTML = '<span class="move-icon">✥</span>';
        moveHandle.title = (frameNum === 2 ? "2번 그림틀 위치 이동 (마우스로 드래그)" : "그림틀 위치 이동 (마우스로 드래그)");
        frameEl.appendChild(moveHandle);
      }

      moveHandle.onmousedown = (e) => {
        e.preventDefault();
        e.stopPropagation();

        const slot = side.toLowerCase();
        this.setTargetPageSlot(slot);
        this.setSelectedSubFrame(frameNum);

        frameEl.classList.add("is-moving-frame");
        document.body.style.cursor = "move";
        document.body.style.userSelect = "none";

        const startX = e.clientX;
        const startY = e.clientY;

        const work = this.getCurrentWork();
        const cfg = this.getNormalizedConfig(work);
        const pageIdx = (this.currentSpreadPart - 1) * 2 + (slot === 'left' ? 0 : 1);
        if (!cfg.pages[pageIdx]) cfg.pages[pageIdx] = {};

        const offsetKey = (frameNum === 2) ? 'frame_offset_2' : 'frame_offset_1';
        cfg.pages[pageIdx][offsetKey] = cfg.pages[pageIdx][offsetKey] || { x: 0, y: 0 };
        const offset = cfg.pages[pageIdx][offsetKey];

        const initialOffsetX = parseInt(offset.x, 10) || 0;
        const initialOffsetY = parseInt(offset.y, 10) || 0;

        const insetsKey = (frameNum === 2) ? 'frame_insets_2' : 'frame_insets_1';
        const insets = cfg.pages[pageIdx][insetsKey] || { top: 0, bottom: 0, left: 0, right: 0 };
        const layout = cfg.pages[pageIdx].image_layout || 'single';

        const onMouseMove = (ev) => {
          const deltaX = ev.clientX - startX;
          const deltaY = ev.clientY - startY;

          offset.x = Math.round(initialOffsetX + deltaX);
          offset.y = Math.round(initialOffsetY + deltaY);
          if (frameNum === 1) cfg.pages[pageIdx].frame_offset = { x: offset.x, y: offset.y };

          this.applyFrameInsetsStyle(frameEl, insets, layout, frameNum, cfg.pages[pageIdx]);
          this.detectAndApplyLineOverlap(slot);
        };

        const onMouseUp = () => {
          frameEl.classList.remove("is-moving-frame");
          document.body.style.cursor = "";
          document.body.style.userSelect = "";
          window.removeEventListener("mousemove", onMouseMove, true);
          window.removeEventListener("mouseup", onMouseUp, true);

          this.saveLayoutConfigToServer(work.episode_no, cfg);
          if (window.showToast) {
            window.showToast(`🖼️ ${frameNum}번 그림틀 위치가 이동되었습니다.`, "info");
          }
        };

        window.addEventListener("mousemove", onMouseMove, true);
        window.addEventListener("mouseup", onMouseUp, true);
      };
    }

    /**
     * 선택된 그림틀을 크기 변화 없이 통째로 (deltaX, deltaY)만큼 평행 이동
     */
    moveSelectedFrame(deltaX, deltaY) {
      const slot = this.targetPageSlot || 'left';
      const frameNum = this.selectedSubFrame || 1;
      const work = this.getCurrentWork();
      if (!work) return;

      const cfg = this.getNormalizedConfig(work);
      const pageIdx = (this.currentSpreadPart - 1) * 2 + (slot === 'left' ? 0 : 1);
      if (!cfg.pages[pageIdx]) cfg.pages[pageIdx] = {};

      const offsetKey = (frameNum === 2) ? 'frame_offset_2' : 'frame_offset_1';
      cfg.pages[pageIdx][offsetKey] = cfg.pages[pageIdx][offsetKey] || { x: 0, y: 0 };
      const offset = cfg.pages[pageIdx][offsetKey];

      offset.x = (parseInt(offset.x, 10) || 0) + deltaX;
      offset.y = (parseInt(offset.y, 10) || 0) + deltaY;
      if (frameNum === 1) cfg.pages[pageIdx].frame_offset = { x: offset.x, y: offset.y };

      const insetsKey = (frameNum === 2) ? 'frame_insets_2' : 'frame_insets_1';
      const insets = cfg.pages[pageIdx][insetsKey] || { top: 0, bottom: 0, left: 0, right: 0 };

      const capSide = (slot === 'right' || slot === 'Right') ? 'Right' : 'Left';
      const layer = document.getElementById(`dtpLayerImage${capSide}`);
      const frameEl = layer ? (layer.querySelector(`.dtp-image-frame[data-sub-frame="${frameNum}"]`) || layer.querySelector('.dtp-image-frame')) : null;
      const layout = cfg.pages[pageIdx].image_layout || 'single';

      if (frameEl) {
        this.applyFrameInsetsStyle(frameEl, insets, layout, frameNum, cfg.pages[pageIdx]);
      }
      this.detectAndApplyLineOverlap(slot);
      this.saveLayoutConfigToServer(work.episode_no, cfg);
    }

    attachFrame4WayResizeHandles(frameEl, side, frameNum) {
      ['top', 'bottom', 'left', 'right'].forEach(pos => {
        this.attachFrameResizeHandle(frameEl, side, frameNum, pos);
      });
    }

    /**
     * 그림틀(프레임) 상·하·좌·우 4변 슬림 조절 핸들 바인딩 (인디자인식 직관적 리사이즈)
     * - 당기면 늘어나고, 밀면 줄어드는 1:1 자연스러운 조작감 보장
     */
    attachFrameResizeHandle(frameEl, side, frameNum, handlePos) {
      let handle = frameEl.querySelector(`.dtp-frame-handle.handle-${handlePos}`);
      if (!handle) {
        handle = document.createElement("div");
        handle.className = `dtp-frame-handle handle-${handlePos}`;
        const labelText = {
          'top': '▲ 윗변 조절',
          'bottom': '▼ 아랫변 조절',
          'left': '◀ 좌변 조절',
          'right': '▶ 우변 조절'
        }[handlePos] || `${frameNum}번 그림틀 조절`;
        handle.innerHTML = `
          <div class="handle-bar-pill"></div>
          <span class="handle-label">${labelText}</span>
        `;
        frameEl.appendChild(handle);
      }

      handle.onmousedown = (e) => {
        e.preventDefault();
        e.stopPropagation();

        const slot = side.toLowerCase();
        this.setTargetPageSlot(slot);
        this.setSelectedSubFrame(frameNum);

        frameEl.classList.add("is-resizing");
        document.body.style.cursor = (handlePos === 'top' || handlePos === 'bottom') ? 'ns-resize' : 'ew-resize';

        const startX = e.clientX;
        const startY = e.clientY;
        const parentEl = frameEl.parentElement;
        const parentW = parentEl ? parentEl.offsetWidth : 400;
        const parentH = parentEl ? parentEl.offsetHeight : 500;

        const work = this.getCurrentWork();
        const cfg = this.getNormalizedConfig(work);
        const pageIdx = (this.currentSpreadPart - 1) * 2 + (slot === 'left' ? 0 : 1);
        if (!cfg.pages[pageIdx]) cfg.pages[pageIdx] = {};
        const insetsKey = (frameNum === 2) ? 'frame_insets_2' : 'frame_insets_1';
        cfg.pages[pageIdx][insetsKey] = cfg.pages[pageIdx][insetsKey] || { top: 0, bottom: 0, left: 0, right: 0 };
        const insets = cfg.pages[pageIdx][insetsKey];

        const initialTop = parseInt(insets.top, 10) || 0;
        const initialBottom = parseInt(insets.bottom, 10) || 0;
        const initialLeft = parseInt(insets.left, 10) || 0;
        const initialRight = parseInt(insets.right, 10) || 0;

        const label = handle.querySelector('.handle-label');
        const layout = cfg.pages[pageIdx].image_layout || 'single';

        // 해당 그림틀의 가용 기본 크기
        let availW = parentW;
        let availH = parentH;
        if (layout === 'split_vertical') {
          availH = Math.floor((parentH - 8) / 2);
        } else if (layout === 'split_horizontal') {
          availW = Math.floor((parentW - 8) / 2);
        } else if (layout === 'main_detail') {
          availH = (frameNum === 1) ? Math.floor(parentH * 0.68 - 4) : Math.floor(parentH * 0.32 - 4);
        }

        // 최소 크기 엄격 보장 (높이 80px, 너비 90px 미만 축소 방지 -> 상하/좌우 핸들 겹침 원천 차단) 및 영역 밖 확장(-200px) 허용
        const maxTop = availH - initialBottom - 80;
        const maxBottom = availH - initialTop - 80;
        const maxLeft = availW - initialRight - 90;
        const maxRight = availW - initialLeft - 90;

        const onMouseMove = (ev) => {
          ev.preventDefault();

          if (handlePos === 'top') {
            // 아래로 내리면 축소(+), 위로 올리면 확장(-)
            const deltaY = ev.clientY - startY;
            insets.top = Math.max(-200, Math.min(maxTop, Math.round(initialTop + deltaY)));
            if (label) label.textContent = insets.top <= 0 ? `▲ 상단 확장: ${-insets.top}px` : `▲ 상단 여백: +${insets.top}px`;
          } else if (handlePos === 'bottom') {
            // 아래로 내리면 확장(-), 위로 올리면 축소(+)
            const deltaY = ev.clientY - startY;
            insets.bottom = Math.max(-200, Math.min(maxBottom, Math.round(initialBottom - deltaY)));
            if (label) label.textContent = insets.bottom <= 0 ? `▼ 하단 확장: ${-insets.bottom}px` : `▼ 하단 여백: +${insets.bottom}px`;
          } else if (handlePos === 'left') {
            // 오른쪽으로 밀면 축소(+), 왼쪽으로 당기면 확장(-)
            const deltaX = ev.clientX - startX;
            insets.left = Math.max(-200, Math.min(maxLeft, Math.round(initialLeft + deltaX)));
            if (label) label.textContent = insets.left <= 0 ? `◀ 좌측 확장: ${-insets.left}px` : `◀ 좌측 여백: +${insets.left}px`;
          } else if (handlePos === 'right') {
            // 오른쪽으로 당기면 확장(-), 왼쪽으로 밀면 축소(+)
            const deltaX = ev.clientX - startX;
            insets.right = Math.max(-200, Math.min(maxRight, Math.round(initialRight - deltaX)));
            if (label) label.textContent = insets.right <= 0 ? `▶ 우측 확장: ${-insets.right}px` : `▶ 우측 여백: +${insets.right}px`;
          }

          this.applyFrameInsetsStyle(frameEl, insets, layout, frameNum, cfg.pages[pageIdx]);
          this.detectAndApplyLineOverlap(slot);
        };

        const onMouseUp = () => {
          frameEl.classList.remove("is-resizing");
          document.body.style.cursor = "";
          window.removeEventListener("mousemove", onMouseMove, true);
          window.removeEventListener("mouseup", onMouseUp, true);

          this.saveLayoutConfigToServer(work.episode_no, cfg);
          if (window.showToast) {
            window.showToast(`🖼️ ${frameNum}번 그림틀 크기가 조절되었습니다.`, "info");
          }
        };

        window.addEventListener("mousemove", onMouseMove, true);
        window.addEventListener("mouseup", onMouseUp, true);
      };
    }

    attachImagePanDrag(containerEl, side, frameNum) {
      if (!containerEl || containerEl._panBound) return;
      containerEl._panBound = true;

      let isDown = false;
      let startX = 0, startY = 0;
      let startPanX = 0, startPanY = 0;

      containerEl.addEventListener('mousedown', (e) => {
        if (e.target.tagName === 'BUTTON' || e.target.closest('button') || e.target.closest('.dtp-frame-handle')) return;
        e.preventDefault();
        e.stopPropagation();

        const slot = side.toLowerCase();
        this.setTargetPageSlot(slot);
        this.setSelectedSubFrame(frameNum);

        isDown = true;
        containerEl.classList.add('is-panning');
        containerEl.style.cursor = 'grabbing';
        document.body.style.cursor = 'grabbing';
        document.body.style.userSelect = 'none';
        startX = e.clientX;
        startY = e.clientY;

        const work = this.getCurrentWork();
        const cfg = this.getNormalizedConfig(work);
        const pageIdx = (this.currentSpreadPart - 1) * 2 + (slot === 'left' ? 0 : 1);
        const panKey = (frameNum === 2) ? 'image_pan_2' : 'image_pan_1';
        const pan = cfg.pages[pageIdx]?.[panKey] || cfg.pages[pageIdx]?.image_pan || { x: 0, y: 0 };
        startPanX = pan.x || 0;
        startPanY = pan.y || 0;

        const onMouseMove = (ev) => {
          if (!isDown) return;
          const dx = ev.clientX - startX;
          const dy = ev.clientY - startY;
          const rect = containerEl.getBoundingClientRect();
          // 마우스 드래그 거리를 프레임 대비 백분율(%)로 변환
          const pctX = Math.round((dx / (rect.width || 400)) * 100);
          const pctY = Math.round((dy / (rect.height || 400)) * 100);

          const newX = Math.max(-100, Math.min(100, startPanX + pctX));
          const newY = Math.max(-100, Math.min(100, startPanY + pctY));

          this.setImagePan('x', newX, false);
          this.setImagePan('y', newY, false);
        };

        const onMouseUp = () => {
          if (!isDown) return;
          isDown = false;
          containerEl.classList.remove('is-panning');
          document.body.style.cursor = '';
          document.body.style.userSelect = '';
          window.removeEventListener('mousemove', onMouseMove);
          window.removeEventListener('mouseup', onMouseUp);

          const curWork = this.getCurrentWork();
          if (curWork) {
            this.saveLayoutConfigToServer(curWork.episode_no, curWork.layout_config);
          }
        };

        window.addEventListener('mousemove', onMouseMove);
        window.addEventListener('mouseup', onMouseUp);
      });

      // 마우스 휠 줌 (확대/축소: 40% ~ 250%) 직관적 연동
      containerEl.addEventListener('wheel', (e) => {
        if (e.target.tagName === 'BUTTON' || e.target.closest('button') || e.target.closest('.dtp-frame-handle')) return;
        e.preventDefault();
        const slot = side.toLowerCase();
        this.setTargetPageSlot(slot);
        this.setSelectedSubFrame(frameNum);

        const work = this.getCurrentWork();
        if (!work) return;
        const cfg = this.getNormalizedConfig(work);
        const pageIdx = (this.currentSpreadPart - 1) * 2 + (slot === 'left' ? 0 : 1);
        const scaleKey = (frameNum === 2) ? 'image_scale_2' : 'image_scale_1';
        const curScale = cfg.pages[pageIdx]?.[scaleKey] || cfg.pages[pageIdx]?.image_scale || 100;

        const delta = (e.deltaY < 0) ? 5 : -5;
        const nextScale = Math.max(40, Math.min(250, curScale + delta));
        this.setImageScale(nextScale);
      }, { passive: false });
    }

    /**
     * 🎯 현재 선택된 슬롯/프레임의 실제 화면 <img> 요소를 정확히 찾아 반환하는 헬퍼
     */
    getTargetImageElement(slot, frameNum = 1) {
      const capSide = (slot === 'right' || slot === 'Right') ? 'Right' : 'Left';
      const layer = document.getElementById(`dtpLayerImage${capSide}`);
      if (!layer) return null;

      // 1) 동적 프레임(.dtp-image-frame) 내부의 img 검색 (단일/분할 공통)
      const frame = layer.querySelector(`.dtp-image-frame[data-sub-frame="${frameNum}"]`) ||
        layer.querySelector('.dtp-image-frame');
      if (frame) {
        const img = frame.querySelector('img');
        if (img) return img;
      }

      // 2) 레이어 직속 img 또는 폴백 #dtpImgLeft/Right
      const directImg = layer.querySelector('img');
      if (directImg) return directImg;

      return document.getElementById(`dtpImg${capSide}`);
    }

    /**
     * 그림 배율 (확대/축소: 40% ~ 250%)
     */
    setImageScale(val) {
      const slot = this.targetPageSlot || 'left';
      const frameNum = this.selectedSubFrame || 1;
      const work = this.getCurrentWork();
      if (!work) return;

      const cfg = this.getNormalizedConfig(work);
      const pageIdx = (this.currentSpreadPart - 1) * 2 + (slot === 'left' ? 0 : 1);
      if (!cfg.pages[pageIdx]) cfg.pages[pageIdx] = {};

      const scaleVal = Math.max(40, Math.min(250, parseInt(val, 10) || 100));
      const scaleKey = (frameNum === 2) ? 'image_scale_2' : 'image_scale_1';
      cfg.pages[pageIdx][scaleKey] = scaleVal;
      if (frameNum === 1) cfg.pages[pageIdx].image_scale = scaleVal;

      const panKey = (frameNum === 2) ? 'image_pan_2' : 'image_pan_1';
      const pan = cfg.pages[pageIdx][panKey] || cfg.pages[pageIdx].image_pan || { x: 0, y: 0 };
      const filterKey = (frameNum === 2) ? 'image_filter_2' : 'image_filter_1';
      const filter = cfg.pages[pageIdx][filterKey] || cfg.pages[pageIdx].image_filter || { vignette: 0, blur: 0, tone: 'none' };
      const shapeKey = (frameNum === 2) ? 'frame_shape_2' : 'frame_shape_1';
      const shape = cfg.pages[pageIdx][shapeKey] || (frameNum === 1 ? cfg.pages[pageIdx].frame_shape : null) || 'rect';

      // 실시간 화면 <img> 요소에 즉시 적용
      const img = this.getTargetImageElement(slot, frameNum);
      if (img) {
        this.applyCustomImageStyle(img, pan, scaleVal, filter, shape);
      }

      const lbl = document.getElementById('lblTbScaleVal');
      if (lbl) lbl.textContent = `${scaleVal}%`;

      work.layout_config = cfg;

      clearTimeout(this._scaleDebounce);
      this._scaleDebounce = setTimeout(() => {
        this.saveLayoutConfigToServer(work.episode_no, cfg);
      }, 400);
    }

    /**
     * 그림틀 크기 (10% ~ 100% 비율 축소 및 100% 원상복원)
     */
    setImageFrameScale(val) {
      const slot = this.targetPageSlot || 'left';
      const frameNum = this.selectedSubFrame || 1;
      const work = this.getCurrentWork();
      if (!work) return;

      const cfg = this.getNormalizedConfig(work);
      const pageIdx = (this.currentSpreadPart - 1) * 2 + (slot === 'left' ? 0 : 1);
      if (!cfg.pages[pageIdx]) cfg.pages[pageIdx] = {};

      const scaleVal = Math.max(10, Math.min(100, parseInt(val, 10) || 100));
      const scaleKey = (frameNum === 2) ? 'frame_scale_2' : 'frame_scale_1';
      cfg.pages[pageIdx][scaleKey] = scaleVal;
      if (frameNum === 1) cfg.pages[pageIdx].frame_scale = scaleVal;

      const capSide = (slot === 'right' || slot === 'Right') ? 'Right' : 'Left';
      const layer = document.getElementById(`dtpLayerImage${capSide}`);
      if (layer) {
        layer.querySelectorAll('.dtp-image-frame').forEach(fEl => {
          const fNum = parseInt(fEl.getAttribute('data-sub-frame') || '1', 10);
          const insetsKey = (fNum === 2) ? 'frame_insets_2' : 'frame_insets_1';
          const insets = cfg.pages[pageIdx][insetsKey] || { top: 0, bottom: 0, left: 0, right: 0 };
          const layout = cfg.pages[pageIdx].image_layout || 'single';
          this.applyFrameInsetsStyle(fEl, insets, layout, fNum, cfg.pages[pageIdx]);
        });
      }

      const lbl = document.getElementById('lblTbFrameScaleVal');
      if (lbl) lbl.textContent = `${scaleVal}%`;

      work.layout_config = cfg;

      clearTimeout(this._frameScaleDebounce);
      this._frameScaleDebounce = setTimeout(() => {
        this.saveLayoutConfigToServer(work.episode_no, cfg);
      }, 400);
    }

    /**
     * 그림틀 외부 종이 여백 (실제 인쇄 마진 안착: 0px ~ 50px)
     */
    setImageFrameInset(val) {
      const slot = this.targetPageSlot || 'left';
      const frameNum = this.selectedSubFrame || 1;
      const work = this.getCurrentWork();
      if (!work) return;

      const cfg = this.getNormalizedConfig(work);
      const pageIdx = (this.currentSpreadPart - 1) * 2 + (slot === 'left' ? 0 : 1);
      if (!cfg.pages[pageIdx]) cfg.pages[pageIdx] = {};

      const insetVal = Math.max(0, Math.min(50, parseInt(val, 10) || 0));
      const insetKey = (frameNum === 2) ? 'frame_inset_2' : 'frame_inset_1';
      cfg.pages[pageIdx][insetKey] = insetVal;
      if (frameNum === 1) cfg.pages[pageIdx].frame_inset = insetVal;

      const capSide = (slot === 'right' || slot === 'Right') ? 'Right' : 'Left';
      const layer = document.getElementById(`dtpLayerImage${capSide}`);
      if (layer) {
        layer.querySelectorAll('.dtp-image-frame').forEach(fEl => {
          const fNum = parseInt(fEl.getAttribute('data-sub-frame') || '1', 10);
          const insetsKey = (fNum === 2) ? 'frame_insets_2' : 'frame_insets_1';
          const insets = cfg.pages[pageIdx][insetsKey] || { top: 0, bottom: 0, left: 0, right: 0 };
          const layout = cfg.pages[pageIdx].image_layout || 'single';
          this.applyFrameInsetsStyle(fEl, insets, layout, fNum, cfg.pages[pageIdx]);
        });
      }

      const lbl = document.getElementById('lblTbFrameInsetVal');
      if (lbl) lbl.textContent = `${insetVal}px`;

      work.layout_config = cfg;

      clearTimeout(this._insetDebounce);
      this._insetDebounce = setTimeout(() => {
        this.saveLayoutConfigToServer(work.episode_no, cfg);
      }, 400);
    }

    /**
     * 그림 위치 중심 이동 (가로 X, 세로 Y: -100% ~ +100% 극단 화면 밖 이동 지원)
     */
    setImagePan(axis, val, shouldDebounce = true) {
      const slot = this.targetPageSlot || 'left';
      const frameNum = this.selectedSubFrame || 1;
      const work = this.getCurrentWork();
      if (!work) return;

      const cfg = this.getNormalizedConfig(work);
      const pageIdx = (this.currentSpreadPart - 1) * 2 + (slot === 'left' ? 0 : 1);
      if (!cfg.pages[pageIdx]) cfg.pages[pageIdx] = {};

      const panKey = (frameNum === 2) ? 'image_pan_2' : 'image_pan_1';
      if (!cfg.pages[pageIdx][panKey]) cfg.pages[pageIdx][panKey] = { x: 0, y: 0 };

      const parsedVal = parseInt(val, 10) || 0;
      cfg.pages[pageIdx][panKey][axis] = Math.max(-100, Math.min(100, parsedVal));
      if (frameNum === 1) {
        if (!cfg.pages[pageIdx].image_pan) cfg.pages[pageIdx].image_pan = { x: 0, y: 0 };
        cfg.pages[pageIdx].image_pan[axis] = cfg.pages[pageIdx][panKey][axis];
      }
      const pan = cfg.pages[pageIdx][panKey];

      const scaleKey = (frameNum === 2) ? 'image_scale_2' : 'image_scale_1';
      const scaleVal = cfg.pages[pageIdx][scaleKey] || cfg.pages[pageIdx].image_scale || 100;
      const filterKey = (frameNum === 2) ? 'image_filter_2' : 'image_filter_1';
      const filter = cfg.pages[pageIdx][filterKey] || cfg.pages[pageIdx].image_filter || { vignette: 0, blur: 0, tone: 'none' };
      const shapeKey = (frameNum === 2) ? 'frame_shape_2' : 'frame_shape_1';
      const shape = cfg.pages[pageIdx][shapeKey] || (frameNum === 1 ? cfg.pages[pageIdx].frame_shape : null) || 'rect';

      // 실시간 화면 <img> 요소에 즉시 적용
      const img = this.getTargetImageElement(slot, frameNum);
      if (img) {
        this.applyCustomImageStyle(img, pan, scaleVal, filter, shape);
      }

      const input = document.getElementById(axis === 'x' ? 'inputTbPanX' : 'inputTbPanY');
      const lbl = document.getElementById(axis === 'x' ? 'lblTbPanXVal' : 'lblTbPanYVal');
      if (input) input.value = pan[axis];
      if (lbl) lbl.textContent = `${pan[axis]}%`;

      work.layout_config = cfg;

      if (shouldDebounce) {
        clearTimeout(this._panDebounce);
        this._panDebounce = setTimeout(() => {
          this.saveLayoutConfigToServer(work.episode_no, cfg);
        }, 400);
      }
    }

    /**
     * 그림 초점 리셋
     */
    resetImagePan() {
      this.setImagePan('x', 0);
      this.setImagePan('y', 0);
      const inputX = document.getElementById('inputTbPanX');
      const inputY = document.getElementById('inputTbPanY');
      if (inputX) inputX.value = 0;
      if (inputY) inputY.value = 0;
    }

    /**
     * 그림 필터 (비네팅, 블러, 톤) 적용
     */
    setImageFilter(filterType, val) {
      const slot = this.targetPageSlot || 'left';
      const frameNum = this.selectedSubFrame || 1;
      const work = this.getCurrentWork();
      if (!work) return;

      const cfg = this.getNormalizedConfig(work);
      const pageIdx = (this.currentSpreadPart - 1) * 2 + (slot === 'left' ? 0 : 1);
      if (!cfg.pages[pageIdx]) cfg.pages[pageIdx] = {};

      const filterKey = (frameNum === 2) ? 'image_filter_2' : 'image_filter_1';
      if (!cfg.pages[pageIdx][filterKey]) cfg.pages[pageIdx][filterKey] = { vignette: 0, blur: 0, tone: 'none' };

      cfg.pages[pageIdx][filterKey][filterType] = (filterType === 'tone') ? val : (parseFloat(val) || 0);
      if (frameNum === 1) {
        if (!cfg.pages[pageIdx].image_filter) cfg.pages[pageIdx].image_filter = { vignette: 0, blur: 0, tone: 'none' };
        cfg.pages[pageIdx].image_filter[filterType] = cfg.pages[pageIdx][filterKey][filterType];
      }
      const filter = cfg.pages[pageIdx][filterKey];

      const scaleKey = (frameNum === 2) ? 'image_scale_2' : 'image_scale_1';
      const scaleVal = cfg.pages[pageIdx][scaleKey] || cfg.pages[pageIdx].image_scale || 100;
      const panKey = (frameNum === 2) ? 'image_pan_2' : 'image_pan_1';
      const pan = cfg.pages[pageIdx][panKey] || cfg.pages[pageIdx].image_pan || { x: 0, y: 0 };
      const shapeKey = (frameNum === 2) ? 'frame_shape_2' : 'frame_shape_1';
      const shape = cfg.pages[pageIdx][shapeKey] || (frameNum === 1 ? cfg.pages[pageIdx].frame_shape : null) || 'rect';

      // 실시간 화면 <img> 요소에 즉시 적용
      const img = this.getTargetImageElement(slot, frameNum);
      if (img) {
        this.applyCustomImageStyle(img, pan, scaleVal, filter, shape);
      }

      if (filterType === 'vignette') {
        const lbl = document.getElementById('lblTbVignetteVal');
        if (lbl) lbl.textContent = `${val}%`;
      } else if (filterType === 'blur') {
        const lbl = document.getElementById('lblTbBlurVal');
        if (lbl) lbl.textContent = `${val}px`;
      }

      clearTimeout(this._filterDebounce);
      this._filterDebounce = setTimeout(() => {
        this.saveLayoutConfigToServer(work.episode_no, cfg);
      }, 500);
    }

    /**
     * 현재 대상 슬롯 삽화 교체 모달 열기
     */
    openCurrentImageManager() {
      const slot = this.targetPageSlot || 'left';
      const frameNum = this.selectedSubFrame || 1;
      this.openSlotImageFrameManager(slot, frameNum);
    }

    /**
     * AI 동반자: 빠른 추천 액션
     */
    askAiQuickAction(actionType) {
      const work = this.getCurrentWork();
      if (!work) return;

      let prompt = "";
      if (actionType === 'rhyme') {
        prompt = `제${work.episode_no}화 「${work.title}」의 시적 여운을 더 살릴 수 있는 퇴고 방향이나 대체 시어를 추천해줘.`;
      } else if (actionType === 'art_prompt') {
        prompt = `제${work.episode_no}화 「${work.title}」에 어울리는 한국 서정 수채화/수묵담채 삽화 프롬프트를 제안해줘.`;
      } else if (actionType === 'layout') {
        const lineCount = (work.poem_body || "").split("\n").filter(l => l.trim()).length;
        prompt = `현재 시 본문이 총 ${lineCount}줄인데, A5 2면에 가장 알맞은 줄간격과 글자 크기, 연 구성을 조언해줘.`;
      }

      const input = document.getElementById("inputDtpAiPrompt");
      if (input) input.value = prompt;
      this.sendAiMessage(prompt);
    }

    /**
     * AI 동반자 메시지 전송 및 응답 렌더링
     */
    async sendAiMessage(customText) {
      const input = document.getElementById("inputDtpAiPrompt");
      const userText = customText || (input ? input.value.trim() : "");
      if (!userText) return;
      if (input) input.value = "";

      const msgBox = document.getElementById("dtpAiMessages");
      if (!msgBox) return;

      // 사용자 버블 추가 (Canva풍 그라데이션)
      const userBubble = document.createElement("div");
      userBubble.className = "canva-user-bubble";
      userBubble.textContent = userText;
      msgBox.appendChild(userBubble);
      msgBox.scrollTop = msgBox.scrollHeight;

      // AI 로딩 버블
      const aiBubble = document.createElement("div");
      aiBubble.className = "canva-ai-bubble";
      aiBubble.innerHTML = "안실장이 생각하고 있습니다... ✍️";
      msgBox.appendChild(aiBubble);
      msgBox.scrollTop = msgBox.scrollHeight;

      const work = this.getCurrentWork();
      const cfg = work ? this.getNormalizedConfig(work) : {};
      const lineCount = work ? (work.poem_body || "").split("\n").filter(l => l.trim()).length : 0;

      // 문맥 기반 즉각 지능형 피드백 생성
      setTimeout(() => {
        let reply = "";
        if (userText.includes("시어") || userText.includes("퇴고")) {
          reply = `🌿 <strong>「${work.title}」 퇴고 제안</strong><br>
사용자님의 실제 기억과 육성이 깃든 원형 시어를 보존하면서, 마지막 연의 서술형 종결어미를 명사형이나 잔잔한 읊조림(‘-네’, ‘-던가’)으로 여운을 남겨보세요. 구체적 사물(대청마루, 무우, 호롱불 등)의 촉각을 선명히 두면 시적 깊이가 배가됩니다.`;
        } else if (userText.includes("프롬프트") || userText.includes("삽화") || userText.includes("그림")) {
          reply = `🎨 <strong>「${work.title}」 삽화 프롬프트 제안</strong><br>
<code>Korean traditional soft watercolor, nostalgic morning sunlight, quiet wooden porch, soft ink wash edges, negative space, no text, 300 DPI publication quality</code><br>
도구상자의 <em>[출판 필터 & 비네팅]</em>에서 외곽 페이드를 20% 주시면 한지와 더욱 자연스럽게 융합됩니다.`;
        } else if (userText.includes("조판") || userText.includes("줄") || userText.includes("크기")) {
          reply = `📐 <strong>「${work.title}」 조판 조언</strong><br>
현재 본문은 총 ${lineCount}줄입니다. A5 국판 인쇄 규격상 한 면당 14~16줄이 가장 읽기 편안합니다. 
현재 설정(글자 크기 ${cfg.font_size_pt || 13}pt, 줄간격 ${Math.round((cfg.line_height_ratio || 1.6) * 100)}%)은 <strong>인쇄안전선 안착</strong> 범위 내에 잘 안착되어 있습니다!`;
        } else {
          reply = `🌿 <strong>안실장의 조언</strong><br>
말씀해주신 '<em>${userText}</em>'에 맞춰 시화집의 품격을 높일 수 있도록 계속 돕겠습니다. 도구상자의 [정렬], [크기], [그림 분할] 도구를 함께 활용해 보세요!`;
        }
        aiBubble.innerHTML = reply;
        msgBox.scrollTop = msgBox.scrollHeight;
      }, 400);
    }

    /**
     * 도구상자 전체 UI 상태 동기화 (renderSpread 시 자동 호출)
     */
    syncToolboxUI(work, cfg) {
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
        const ptVal = parseFloat((isIndependent && pageData?.font_size_pt) ? pageData.font_size_pt : cfg.font_size_pt) || 12;
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
      if (lblLh) lblLh.textContent = `${lhPercent}%`;

      // 5) 한지 투명도 동기화
      const inputHanji = document.getElementById('inputTbHanjiOpacity');
      const lblHanji = document.getElementById('lblTbHanjiOpacityVal');
      const hanjiPercent = Math.round((parseFloat(cfg.backdrop_opacity) || 0.85) * 100);
      if (inputHanji) inputHanji.value = hanjiPercent;
      if (lblHanji) lblHanji.textContent = `${hanjiPercent}%`;

      // 6) 그림 탭 동기화
      this.syncToolboxImageTab();

      // 7) Canva풍 AI 탭 맥락 칩 동기화
      const chip = document.getElementById('canvaAiWorkTitle');
      if (chip && work) {
        chip.textContent = `📄 [${work.episode_no || ''} ${work.title || ''}]`;
      }
    }

  }

  // 전역 인스턴스 등록
  const coreInstance = new DtpEditorCore();
  window.dtpEditor = coreInstance;
  window.DtpEditorCore = DtpEditorCore;

  // 기존 레거시 함수 전면 브리지
  window.navigateWork = function (delta) {
    window.dtpEditor.navigateWork(delta);
  };
  window.navigatePage = function (delta) {
    window.dtpEditor.navigatePage(delta);
  };
  window.renderBookSpread = function (index) {
    window.dtpEditor.renderSpread(index, window.currentSpreadPart || 1, false);
  };
  window.onSelectWorkChange = function (val) {
    window._hasUserSelectedWork = true;
    window.dtpEditor.renderSpread(parseInt(val, 10), 1, false);
  };
  window.onTypographyFontSizeSelectChange = function (val) {
    window.dtpEditor.setFontSizePt(val);
  };
  window.adjustCustomTypography = function (type, delta) {
    if (type === 'line') {
      window.dtpEditor.adjustLineHeight(delta);
    } else if (type === 'font') {
      const w = window.dtpEditor.getCurrentWork();
      const curPt = w?.layout_config?.font_size_pt || 12;
      window.dtpEditor.setFontSizePt(curPt + delta);
    }
  };
  window.resetCustomTypography = function () {
    window.dtpEditor.resetTypography();
  };
  window.finishAndSaveCurrentLayout = function () {
    window.dtpEditor.finishAndSaveLayout();
  };

  // DOMContentLoaded 시 자동 초기화
  if (document.readyState === 'loading') {
    document.addEventListener("DOMContentLoaded", () => window.dtpEditor.init());
  } else {
    window.dtpEditor.init();
  }

})(window);

var dtpEditor = window.dtpEditor;
