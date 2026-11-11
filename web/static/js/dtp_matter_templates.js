/**
 * ==============================================================================
 * StoryBook Studio | DTP 부속물 완성형 표준 템플릿 & 인라인 편집 엔진
 * (dtp_matter_templates.js)
 * ------------------------------------------------------------------------------
 * 앞표지/뒤표지, 속표지(도비라), 시인의 말(서문), 차례(목차), 부 간지,
 * 맺음말(에필로그), 정식 출판 판권지 등 정형화된 부속 페이지에 대해
 * 1) 고품격 표준 예시 템플릿(Pre-filled Presets) 기본 제공
 * 2) 화면에서 직접 클릭하여 수정 가능한 contenteditable 인터랙션
 * 3) 선택 영역 인라인 서식 엔진 연동 (글자 크기, 볼드, 색상, 서체)
 * 4) [💾 부속물 저장], [✨ 기본 예시 불러오기], [🎨 템플릿 스타일 변경]
 * 5) 백엔드 /api/book/structure/update_section 영구 저장 및 책 전체 구성표 동기화
 * ==============================================================================
 */

(function (window) {
  'use strict';

  // 1. 부속물 기본 표준 예시 프리셋 (Default Presets)
  const MATTER_PRESETS = {
    // -------------------------------------------------------------
    // 앞표지 & 뒤표지 (Cover)
    // -------------------------------------------------------------
    cover: {
      left: { // 뒤표지 (Back Cover)
        badge: "STORYBOOK POETRY COLLECTION",
        blurb: `기억의 서랍에서 꺼내 올린
따스한 삶의 무늬와 시의 노래.

지나간 시절의 아련한 온기가
오늘을 살아가는 당신에게
작은 위로의 등불이 되기를 바랍니다.`,
        price: "15,000원",
        isbn: "ISBN 979-11-XXXXX-X (03810)",
        publisher: "부크크 (Bookk) 자가출판"
      },
      right: { // 앞표지 (Front Cover)
        collection: "STORYBOOK COLLECTION",
        title: "노을빛 기억",
        subtitle: "어머니의 등불과 유년의 뜰",
        author: "임정환 시화집",
        publisher: "부크크 (Bookk) 자가출판"
      }
    },

    // -------------------------------------------------------------
    // 속표지 / 도비라 (Half Title)
    // -------------------------------------------------------------
    half_title: {
      left: { // 면지 / 백면
        symbol: "❦",
        note: "[ 면지 / 여백 ]"
      },
      right: { // 속표지 본문
        title: "노을빛 기억",
        subtitle: "어머니의 등불과 유년의 뜰",
        author: "임정환 지음",
        publisher: "부크크 (Bookk) 자가출판"
      }
    },

    // -------------------------------------------------------------
    // 시인의 말 / 서문 (Prologue / Preface)
    // -------------------------------------------------------------
    prologue: {
      left: {
        symbol: "❦",
        note: "[ 2p / 여백 ]"
      },
      right: {
        title: "시인의 말",
        content: `가장 개인적인 기억이 가장 깊은 문학이자 예술이 된다.

이 시화집은 화려하게 꾸며낸 허구를 담지 않았습니다.
마음속 깊은 곳에 오래 고여 있던 찰나의 순간,
차갑게 식어가던 툇마루의 새벽과 그 시절 들었던 다정한 말 한마디를
온전한 나의 목소리와 수채의 빛깔로 빚어낸 삶의 기록입니다.

책장을 넘길 때마다 그날의 서정적 온기가
그리운 당신의 마음에 가만히 가닿기를 소망합니다.`,
        date_author: "2026년 늦가을\n지은이 임정환 배상"
      }
    },

    // -------------------------------------------------------------
    // 차례 / 목차 (Table of Contents)
    // -------------------------------------------------------------
    toc: {
      title: "차 례",
      quote: `삶의 가장 따스한 순간들은\n언제나 가장 고요한 기억 속에 머물러 있다.`
    },

    // -------------------------------------------------------------
    // 부 / 챕터 간지 (Part Divider)
    // -------------------------------------------------------------
    part_divider: {
      left: {
        symbol: "❦",
        note: "[ 여백의 장 ]"
      },
      right: {
        part_no: "제 1 부",
        part_title: "유년의 뜰, 어머니의 등불",
        part_desc: `어스름 내리는 저녁,
부엌에서 흘러나오던 구수한 된장찌개 냄새와
마당 귀퉁이를 비추던 어머니의 작은 등불.`
      }
    },

    // -------------------------------------------------------------
    // 맺음말 / 에필로그 (Epilogue / Afterword)
    // -------------------------------------------------------------
    epilogue: {
      left: {
        symbol: "❦",
        note: "[ 여백 ]"
      },
      right: {
        title: "맺음말",
        content: `책장을 덮으며,
한 편 한 편 시를 쓰고 그림을 빚는 동안
오래전 떠나보낸 시간들이 다시 살아와 내 곁에 머물렀습니다.

나의 작은 기억 조각들이
당신에게도 따스한 유년의 뜰을 거니는 시간이 되었기를 바라며,
사랑하는 가족과 곁을 지켜준 모든 이들에게 깊은 감사를 전합니다.`,
        date_author: "2026년 겨울의 문턱에서\n지은이 임정환 지음"
      }
    },

    // -------------------------------------------------------------
    // 정식 출판 판권지 (Colophon)
    // -------------------------------------------------------------
    colophon: {
      left: {
        symbol: "❦",
        note: "[ 맺음말 또는 여백 ]"
      },
      right: {
        title: "노을빛 기억",
        author: "임종훈",
        publisher_ceo: "한건희",
        publisher: "주식회사 부크크",
        reg_no: "2014.07.15.(제2014-16호)",
        published_date: "2026년   월   일",
        address: "서울특별시 금천구 가산디지털1로 119 SK트윈타워 A동 305호",
        phone: "1670-8316",
        email: "info@bookk.co.kr",
        homepage: "www.bookk.co.kr",
        isbn: "",
        price: "",
        copyright: "본 책은 저작자의 지적 재산으로서 무단 전재와 복제를 금합니다.\n\n이 책의 글과 그림은 저자의 실제 경험과 선택을 바탕으로\n생성형 AI의 도움을 받아 제작·편집되었습니다."
      }
    }
  };

  /**
   * DtpMatterTemplateEngine 싱글톤 클래스
   */
  class DtpMatterTemplateEngine {
    constructor() {
      this.currentSection = null;
      this.currentTheme = "lyrical"; // "lyrical" | "classic" | "modern"
    }

    /**
     * 프로젝트 정보와 프리셋을 병합하여 최종 템플릿 데이터 도출
     */
    getSectionData(sec) {
      if (!sec) return {};
      const project = (window.currentStatus && window.currentStatus.project) || {};
      const secType = sec.section_type || sec.id || "cover";
      const preset = MATTER_PRESETS[secType] || MATTER_PRESETS.cover;

      const title = sec.data?.title || project.name || preset.right?.title || "시집 제목";
      const subtitle = sec.data?.subtitle !== undefined ? sec.data.subtitle : (project.subtitle || preset.right?.subtitle || "");
      const author = sec.data?.author || project.author || preset.right?.author || "시인";
      const publisher = sec.data?.publisher || project.publisher || preset.right?.publisher || "부크크 (Bookk) 자가출판";
      const coverImage = sec.data?.cover_image || project.cover_image || "";
      const price = sec.data?.price || project.price || preset.left?.price || "15,000원";
      const isbn = sec.data?.isbn || project.isbn || preset.left?.isbn || "979-11-XXXXX-X (03810)";
      const publishedDate = sec.data?.published_date || project.published_date || preset.right?.published_date || "2026년 11월 10일";

      const prologueContent = sec.data?.content || project.prologue || project.preface || preset.right?.content || "";
      const epilogueContent = sec.data?.content || project.epilogue || preset.right?.content || "";
      const blurbContent = sec.data?.blurb || project.back_cover_blurb || preset.left?.blurb || "";

      return {
        secType,
        preset,
        title,
        subtitle,
        author,
        publisher,
        coverImage,
        price,
        isbn,
        publishedDate,
        prologueContent,
        epilogueContent,
        blurbContent
      };
    }

    /**
     * 부속물 양면(스프레드) 렌더링
     */
    renderSpread(sec, ovLeft, ovRight) {
      if (!sec || !ovLeft || !ovRight) return;
      this.currentSection = sec;

      const d = this.getSectionData(sec);
      const theme = this.currentTheme;

      // 상단 툴바에 부속물 퀵 액션 바 노출
      this.renderMatterToolbar();

      if (sec.id === 'cover' || d.secType === 'cover' || sec.id === 'back_cover' || d.secType === 'back_cover') {
        this.renderCover(d, ovLeft, ovRight);
      } else if (sec.id === 'half_title' || d.secType === 'half_title') {
        this.renderHalfTitle(d, ovLeft, ovRight);
      } else if (sec.id === 'prologue' || sec.id === 'preface' || d.secType === 'prologue') {
        this.renderPrologue(d, ovLeft, ovRight);
      } else if (sec.id === 'toc' || d.secType === 'toc') {
        this.renderToc(d, ovLeft, ovRight);
      } else if (d.secType === 'part_divider' || (sec.id && sec.id.startsWith('part_'))) {
        this.renderPartDivider(sec, d, ovLeft, ovRight);
      } else if (sec.id === 'epilogue' || sec.id === 'colophon' || d.secType === 'epilogue' || d.secType === 'colophon') {
        // [출판 표준 뒷부속 완제 스프레드] 좌측: 42면(맺음말) & 우측: 43면(판권지)
        this.renderBackMatterSpread(sec, d, ovLeft, ovRight);
      } else {
        this.renderGenericMatter(sec, d, ovLeft, ovRight);
      }

      // 렌더링 완료 후 editable 필드들에 이벤트 리스너 바인딩
      this.bindEditableEvents(ovLeft, ovRight);
    }

    /**
     * 상단 툴바 부속물 퀵 액션 바 렌더링
     */
    renderMatterToolbar() {
      // 2-Layer 통합으로 인해 액션바는 더 이상 생성하지 않음 (단일 2-Layer 헤더로 통합)
      const bar = document.getElementById("dtpMatterActionBar");
      if (bar) bar.remove();
      return;
    }

    /**
     * 부속물 편집 종료 시 툴바 숨기기
     */
    hideMatterToolbar() {
      const bar = document.getElementById("dtpMatterActionBar");
      if (bar) bar.style.display = "none";
    }

    // -------------------------------------------------------------
    // 1. 앞표지 & 뒤표지 (Cover) 렌더링
    // -------------------------------------------------------------
    renderCover(d, ovLeft, ovRight) {
      // 좌측: 뒤표지 (Back Cover)
      ovLeft.innerHTML = `
        <div class="matter-page-inner matter-theme-${this.currentTheme}" style="height:100%; display:flex; flex-direction:column; justify-content:space-between; padding:45px 30px 30px 30px; background:#FAF7F2; color:#5A4A3A; text-align:center; box-sizing:border-box;">
          <div>
            <div class="matter-badge" style="font-size:0.75rem; color:#8C7560; letter-spacing:2px; font-weight:700; margin-bottom:30px;">
              ${d.preset.left.badge}
            </div>
            <div class="matter-editable" data-field="blurb" contenteditable="true" style="font-family:'BookkMyungjo', '부크크 명조', 'Nanum Myeongjo', serif; font-size:1.02rem; line-height:2.0; color:#3A2E24; font-style:italic; padding:15px; border-radius:6px; white-space:pre-line;" title="더블클릭하거나 드래그하여 뒤표지 추천 카피를 자유롭게 수정하세요.">
              ${d.blurbContent || d.preset.left.blurb}
            </div>
          </div>
          <div style="border-top:1.5px solid #D8C7B5; padding-top:16px; display:flex; justify-content:space-between; align-items:flex-end; font-size:0.78rem; color:#8C7560;">
            <div style="text-align:left; line-height:1.6;">
              <div>정가 <span class="matter-editable" data-field="price" contenteditable="true" style="font-weight:700; color:#3A2E24;">${d.price}</span></div>
              <div class="matter-editable" data-field="isbn" contenteditable="true" style="letter-spacing:0.5px;">${d.isbn}</div>
            </div>
            <div style="text-align:right;">
              <div class="matter-editable" data-field="publisher" contenteditable="true" style="font-weight:700; color:#553412; font-size:0.85rem;">${d.publisher}</div>
              <div style="font-size:0.7rem; color:#A08C7D; margin-top:2px;">[ 바코드 부착 영역 ]</div>
            </div>
          </div>
        </div>
      `;

      // 우측: 앞표지 (Front Cover)
      const coverImgTag = d.coverImage
        ? `<div style="position:relative; display:inline-block; margin-bottom:15px;">
             <img src="${d.coverImage}" style="max-height:200px; max-width:85%; object-fit:contain; border-radius:6px; box-shadow:0 6px 18px rgba(0,0,0,0.14);" />
             <button type="button" onclick="dtpMatterEngine.openCoverImagePicker()" style="position:absolute; bottom:8px; right:8px; background:rgba(255,255,255,0.9); border:1px solid #D5C2B0; border-radius:4px; padding:3px 8px; font-size:0.72rem; font-weight:700; color:#643E19; cursor:pointer;">📷 표지 교체</button>
           </div>`
        : `<div onclick="dtpMatterEngine.openCoverImagePicker()" style="height:170px; width:68%; border:2px dashed #C8B6A2; border-radius:8px; display:flex; flex-direction:column; align-items:center; justify-content:center; color:#A08872; margin-bottom:18px; font-size:0.82rem; cursor:pointer; background:#FFFDF9;" title="클릭하여 표지 대표 일러스트를 등록합니다.">
             <span style="font-size:1.6rem; margin-bottom:6px;">🎨</span>
             <span>클릭하여 표지 일러스트 선택</span>
           </div>`;

      ovRight.innerHTML = `
        <div class="matter-page-inner matter-theme-${this.currentTheme}" style="height:100%; display:flex; flex-direction:column; justify-content:space-between; align-items:center; padding:45px 30px 25px 30px; background:#FAF7F2; text-align:center; box-sizing:border-box;">
          <div style="font-size:0.78rem; letter-spacing:2px; color:#8C6A4F; font-weight:700;">
            ${d.preset.right.collection}
          </div>
          <div style="display:flex; flex-direction:column; align-items:center; width:100%;">
            <h1 class="matter-editable" data-field="title" contenteditable="true" style="font-family:'BookkMyungjo', '부크크 명조', 'Nanum Myeongjo', serif; font-size:1.95rem; color:#2C1D11; margin:0 0 10px 0; font-weight:700; letter-spacing:-0.5px; width:90%;" title="시집 제목을 클릭하여 수정하세요.">
              ${d.title}
            </h1>
            <div class="matter-editable" data-field="subtitle" contenteditable="true" style="font-size:0.92rem; color:#8C6A4F; margin-bottom:12px; font-weight:500; width:85%;" title="부제를 클릭하여 수정하세요.">
              ${d.subtitle}
            </div>
            <div class="matter-editable" data-field="author" contenteditable="true" style="font-size:0.98rem; color:#6C4E36; margin-bottom:18px; font-weight:600;" title="저자명을 클릭하여 수정하세요.">
              ${d.author} 시화집
            </div>
            ${coverImgTag}
          </div>
          <div style="font-size:0.85rem; font-weight:700; color:#553412; letter-spacing:0.5px;">
            <span class="matter-editable" data-field="publisher" contenteditable="true">${d.publisher}</span>
          </div>
        </div>
      `;
    }

    // -------------------------------------------------------------
    // 2. 속표지 / 도비라 (Half Title) 렌더링
    // -------------------------------------------------------------
    renderHalfTitle(d, ovLeft, ovRight) {
      ovLeft.innerHTML = `
        <div style="height:100%; background:#FAF7F2; display:flex; flex-direction:column; align-items:center; justify-content:center; color:#C4B29E; font-size:0.85rem; font-family:'BookkMyungjo', '부크크 명조', 'Nanum Myeongjo', serif; letter-spacing:2px;">
          ${d.preset.left.symbol}<br><span style="margin-top:8px; font-size:0.78rem;">${d.preset.left.note}</span>
        </div>
      `;

      ovRight.innerHTML = `
        <div class="matter-page-inner matter-theme-${this.currentTheme}" style="height:100%; display:flex; flex-direction:column; justify-content:center; align-items:center; padding:55px 35px; background:#FAF7F2; text-align:center; box-sizing:border-box;">
          <div style="margin-top:-35px; width:100%;">
            <h2 class="matter-editable" data-field="title" contenteditable="true" style="font-family:'BookkMyungjo', '부크크 명조', 'Nanum Myeongjo', serif; font-size:1.85rem; color:#2C1D11; margin-bottom:12px; font-weight:700; letter-spacing:-0.5px;" title="속표지 제목">
              ${d.title}
            </h2>
            <div class="matter-editable" data-field="subtitle" contenteditable="true" style="font-size:0.92rem; color:#8C6A4F; margin-bottom:24px;" title="속표지 부제">
              ${d.subtitle}
            </div>
            <div class="matter-editable" data-field="author" contenteditable="true" style="font-size:0.98rem; color:#6C4E36; margin-bottom:35px; font-weight:500;" title="속표지 지은이">
              ${d.author} 지음
            </div>
            <div style="width:40px; height:1.5px; background:#B89A7E; margin:0 auto 35px auto;"></div>
            <div class="matter-editable" data-field="publisher" contenteditable="true" style="font-size:0.88rem; color:#8C7560; font-weight:600;" title="출판사">
              ${d.publisher}
            </div>
          </div>
        </div>
      `;
    }

    // -------------------------------------------------------------
    // 3. 시인의 말 / 서문 (Prologue) 렌더링
    // -------------------------------------------------------------
    renderPrologue(d, ovLeft, ovRight) {
      ovLeft.innerHTML = `
        <div style="height:100%; background:#FAF7F2; display:flex; flex-direction:column; align-items:center; justify-content:center; color:#C4B29E; font-size:0.85rem; font-family:'BookkMyungjo', '부크크 명조', 'Nanum Myeongjo', serif; letter-spacing:2px;">
          ${d.preset.left.symbol}<br><span style="margin-top:8px; font-size:0.78rem;">${d.preset.left.note}</span>
        </div>
      `;

      ovRight.innerHTML = `
        <div class="matter-page-inner matter-theme-${this.currentTheme}" style="height:100%; display:flex; flex-direction:column; justify-content:space-between; padding:45px 35px 35px 35px; background:#FAF7F2; box-sizing:border-box;">
          <div>
            <h3 class="matter-editable" data-field="prologue_title" contenteditable="true" style="font-family:'BookkMyungjo', '부크크 명조', 'Nanum Myeongjo', serif; font-size:1.45rem; color:#2C1D11; margin:0 0 20px 0; border-bottom:1.5px solid #C8B6A2; padding-bottom:8px; font-weight:700;">
              ${d.preset.right.title}
            </h3>
            <div class="matter-editable" data-field="prologue_content" contenteditable="true" style="font-family:'BookkMyungjo', '부크크 명조', 'Nanum Myeongjo', serif; font-size:0.95rem; line-height:2.05; color:#3A2E24; white-space:pre-line; padding:8px 0;" title="서문 본문을 클릭하거나 드래그하여 자유롭게 수정하세요.">
              ${d.prologueContent || d.preset.right.content}
            </div>
          </div>
          <div style="text-align:right; font-family:'BookkMyungjo', '부크크 명조', 'Nanum Myeongjo', serif; font-size:0.9rem; color:#5A4A3A; line-height:1.7;">
            <div class="matter-editable" data-field="prologue_date_author" contenteditable="true" style="white-space:pre-line; display:inline-block;" title="날짜 및 서명">
              2026년 늦가을\n지은이 ${d.author} 배상
            </div>
          </div>
        </div>
      `;
    }

    // -------------------------------------------------------------
    // 4. 차례 / 목차 (Table of Contents) 렌더링
    // -------------------------------------------------------------
    renderToc(d, ovLeft, ovRight) {
      const works = (typeof dtpEditor !== 'undefined' && dtpEditor.getWorksList) ? dtpEditor.getWorksList() : [];
      let tocRows = '';

      if (works.length > 0) {
        let currentChapter = null;

        works.forEach((w, idx) => {
          const chap = (w.chapter || '').trim();

          // 회차 번호 정규화: "제01화" or "01" -> "제01화" (중복 접두/접미사 방지)
          let rawEp = String(w.episode_no || (idx + 1)).trim();
          let epNum = rawEp.replace(/[^0-9]/g, '');
          let epStr = epNum ? `제${epNum.padStart(2, '0')}화` : rawEp;

          // 실제 책 구조에서의 페이지 쪽수 자동 연동
          let pageNo = 8 + (idx * 2);
          if (window.bookStructureData && Array.isArray(window.bookStructureData.sections)) {
            const sec = window.bookStructureData.sections.find(s => s.episode_no === w.episode_no);
            if (sec) {
              pageNo = sec.start_page !== undefined ? sec.start_page : (sec.page_start || pageNo);
            }
          }

          // 📚 새로운 부(Chapter) 등장 시 상단에 독립된 한 줄 헤더 삽입!
          if (chap && chap !== currentChapter) {
            currentChapter = chap;

            // 해당 부의 도비라(간지) 페이지 번호 연동
            let partPageNo = "";
            if (window.bookStructureData && Array.isArray(window.bookStructureData.sections)) {
              const partSec = window.bookStructureData.sections.find(s => s.section_type === 'part_divider' && (s.title === chap || s.chapter === chap));
              if (partSec) {
                partPageNo = partSec.start_page !== undefined ? partSec.start_page : (partSec.page_start || "");
              }
            }

            // 부 표제 및 제목 포맷팅 (예: "제1부: 솜꽃의 전설" -> "제 1 부 · 솜꽃의 전설")
            let displayChap = chap.replace(/^(제\s*\d+\s*부|특별부|외전)\s*[:|-]?\s*(.*)$/, function(m, p1, p2) {
              const cleanP1 = p1.replace(/\s+/g, '').replace(/제(\d+)부/, '제 $1 부');
              return p2 ? `${cleanP1} · ${p2}` : cleanP1;
            });

            tocRows += `
              <div style="margin-top:${idx === 0 ? '6px' : '20px'}; margin-bottom:8px; padding-bottom:5px; border-bottom:1.5px solid #C8B6A2; display:flex; justify-content:space-between; align-items:baseline;">
                <span style="font-family:'BookkMyungjo', '부크크 명조', 'Nanum Myeongjo', serif; font-size:0.96rem; font-weight:700; color:#52361B; letter-spacing:1px;">
                  📁 ${displayChap}
                </span>
                ${partPageNo ? `<span style="font-size:0.8rem; font-weight:700; color:#8C6A4F; font-family:'BookkMyungjo', serif;">${partPageNo}</span>` : ''}
              </div>
            `;
          }

          // 시화 개별 항목 (단아한 들여쓰기와 제목, 쪽수)
          tocRows += `
            <div style="display:flex; justify-content:space-between; align-items:baseline; padding:6px 0 6px 12px; border-bottom:1px dotted #EADCC9; font-size:0.86rem; color:#3A2E24;">
              <div style="display:flex; align-items:baseline; gap:8px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; flex:1; padding-right:10px;">
                <span style="font-weight:600; color:#8C6A4F; font-size:0.78rem; min-width:44px; letter-spacing:0.5px;">${epStr}</span>
                <span style="font-weight:600; font-family:'BookkMyungjo', '부크크 명조', 'Nanum Myeongjo', serif; font-size:0.88rem; color:#2C1D11;">${w.title}</span>
              </div>
              <span style="color:#8C7560; font-size:0.84rem; font-weight:700; min-width:32px; text-align:right; font-family:'BookkMyungjo', serif;">${pageNo}</span>
            </div>
          `;
        });
      } else {
        tocRows = `<div style="text-align:center; color:#A08C7D; padding:30px 0; font-size:0.85rem;">등록된 시화가 없습니다.</div>`;
      }

      ovLeft.innerHTML = `
        <div class="matter-page-inner matter-theme-${this.currentTheme}" style="height:100%; display:flex; flex-direction:column; padding:45px 35px 35px 35px; background:#FAF7F2; box-sizing:border-box;">
          <h3 style="font-family:'BookkMyungjo', '부크크 명조', 'Nanum Myeongjo', serif; font-size:1.45rem; color:#2C1D11; margin:0 0 20px 0; border-bottom:1.5px solid #C8B6A2; padding-bottom:8px; font-weight:700;">
            ${d.preset.title}
          </h3>
          <div style="overflow-y:auto; flex:1; padding-right:5px;">
            ${tocRows}
          </div>
        </div>
      `;

      const tocQuote = d.tocRightQuote || (MATTER_PRESETS.toc && MATTER_PRESETS.toc.quote) || `삶의 가장 따스한 순간들은\n언제나 가장 고요한 기억 속에 머물러 있다.`;

      ovRight.innerHTML = `
        <div class="matter-page-inner matter-theme-${this.currentTheme}" style="height:100%; display:flex; flex-direction:column; justify-content:center; align-items:center; padding:55px 40px; background:#FAF7F2; text-align:center; box-sizing:border-box;">
          <div style="font-size:1.15rem; color:#B89A7E; margin-bottom:16px;">❦</div>
          <div class="matter-editable" data-field="toc_right_quote" contenteditable="true" style="font-family:'BookkMyungjo', '부크크 명조', 'Nanum Myeongjo', serif; font-size:0.95rem; line-height:2.2; color:#5A4A3A; font-style:italic; white-space:pre-line;" title="권두 헌사 문구 (자유롭게 수정하거나 비워둘 수 있습니다)">
            ${tocQuote}
          </div>
        </div>
      `;
    }

    // -------------------------------------------------------------
    // 5. 부 / 챕터 간지 (Part Divider) 렌더링
    // -------------------------------------------------------------
    renderPartDivider(sec, d, ovLeft, ovRight) {
      const partLeft = (MATTER_PRESETS.part_divider && MATTER_PRESETS.part_divider.left) || {};
      const partRight = (MATTER_PRESETS.part_divider && MATTER_PRESETS.part_divider.right) || {};

      ovLeft.innerHTML = `
        <div style="height:100%; background:#FAF7F2; display:flex; flex-direction:column; align-items:center; justify-content:center; color:#C4B29E; font-size:0.85rem; font-family:'BookkMyungjo', '부크크 명조', 'Nanum Myeongjo', serif; letter-spacing:2px;">
          ${partLeft.symbol || "❦"}<br><span style="margin-top:8px; font-size:0.78rem;">${partLeft.note || "[ 여백의 장 ]"}</span>
        </div>
      `;

      // 원본 챕터명 보존
      const rawTitle = sec.title || (sec.data && sec.data.chapter_title) || "";
      
      // 1) 부 번호 (Part No): 크고 당당한 메인 헤더
      let partNo = (sec.data && sec.data.part_no) || sec.subtitle || "";
      if (!partNo && rawTitle) {
        const m = rawTitle.match(/^(제\s*\d+\s*부|특별부|외전)/);
        if (m) partNo = m[1];
      }
      if (!partNo) partNo = partRight.part_no || "제 1 부";

      // 2) 부 고유 제목 (Part Title): 접두사 '제N부:' 제거하여 순수 제목만 추출
      let cleanPartTitle = (sec.data && sec.data.part_title !== undefined) ? sec.data.part_title : rawTitle;
      cleanPartTitle = cleanPartTitle.replace(/^(?:제\s*\d+\s*부|특별부|외전)\s*[:|-]?\s*/, '').trim();
      cleanPartTitle = cleanPartTitle.replace(/\((?:지은이\s*[:|]?\s*)?[^\)]+\)$/, '').trim();

      // 3) 작가명 (Author): 앤솔로지 또는 다인 시집용
      let partAuthor = (sec.data && sec.data.author) || sec.author || "";
      if (!partAuthor && rawTitle) {
        const mAuth = rawTitle.match(/\((?:지은이\s*[:|]?\s*)?([^\)]+)\)$/);
        if (mAuth) partAuthor = mAuth[1].trim();
      }

      ovRight.innerHTML = `
        <div class="matter-page-inner matter-theme-${this.currentTheme}" style="height:100%; display:flex; flex-direction:column; justify-content:center; align-items:center; padding:55px 40px; background:#FAF7F2; text-align:center; box-sizing:border-box;">
          <!-- 1. 메인 부 표제 (크고 품격 있는 서체) -->
          <div class="matter-editable" data-field="part_no" contenteditable="true" style="font-family:'BookkMyungjo', '부크크 명조', 'Nanum Myeongjo', serif; font-size:2.0rem; letter-spacing:4px; color:#2C1D11; font-weight:700; margin:0 0 16px 0;" title="메인 부 표제 (예: 제 1 부)">
            ${partNo}
          </div>

          <!-- 2. 부 고유 제목 (선택 사항 / 미입력 시 생략) -->
          <h2 class="matter-editable" data-field="part_title" data-old-title="${rawTitle}" contenteditable="true" style="font-family:'BookkMyungjo', '부크크 명조', 'Nanum Myeongjo', serif; font-size:1.45rem; color:#4A3525; margin:0 0 12px 0; font-weight:600; min-height:1.4em; letter-spacing:1px;" title="부 고유 제목 (필요 없으면 비워둘 수 있습니다)">
            ${cleanPartTitle}
          </h2>

          <!-- 3. 작가명 (선택 사항 / 앤솔로지 및 부별 작가 표기용) -->
          <div class="matter-editable" data-field="part_author" contenteditable="true" style="font-family:'BookkMyungjo', '부크크 명조', 'Nanum Myeongjo', serif; font-size:0.95rem; color:#8C6A4F; font-weight:500; margin:0 0 20px 0; min-height:1.2em; letter-spacing:2px;" title="지은이/시인명 (앤솔로지 시 입력, 단독 시집은 비워두셔도 됩니다)">
            ${partAuthor ? `지은이 | ${partAuthor}` : ""}
          </div>

          <!-- 구분선 -->
          <div style="width:36px; height:1.5px; background:#B89A7E; margin:0 auto 24px auto;"></div>

          <!-- 4. 서정 소개글 -->
          <div class="matter-editable" data-field="part_desc" contenteditable="true" style="font-family:'BookkMyungjo', '부크크 명조', 'Nanum Myeongjo', serif; font-size:0.92rem; line-height:2.0; color:#5A4A3A; font-style:italic; white-space:pre-line;">
            ${partRight.part_desc || ""}
          </div>
        </div>
      `;
    }

    // -------------------------------------------------------------
    // 6 & 7. [출판 표준 뒷부속 완제 스프레드] 좌측(42p 맺음말) & 우측(43p 판권지)
    // -------------------------------------------------------------
    renderBackMatterSpread(sec, d, ovLeft, ovRight) {
      const epPreset = (MATTER_PRESETS.epilogue && MATTER_PRESETS.epilogue.right) || {};
      const colPreset = (MATTER_PRESETS.colophon && MATTER_PRESETS.colophon.right) || {};

      // 좌측 42면: 맺음말 (에필로그 / Epilogue)
      ovLeft.innerHTML = `
        <div class="matter-page-inner matter-theme-${this.currentTheme}" style="height:100%; display:flex; flex-direction:column; justify-content:space-between; padding:45px 35px 35px 35px; background:#FAF7F2; box-sizing:border-box;">
          <div>
            <h3 class="matter-editable" data-field="epilogue_title" contenteditable="true" style="font-family:'BookkMyungjo', '부크크 명조', 'Nanum Myeongjo', serif; font-size:1.45rem; color:#2C1D11; margin:0 0 20px 0; border-bottom:1.5px solid #C8B6A2; padding-bottom:8px; font-weight:700;">
              ${epPreset.title || "맺음말"}
            </h3>
            <div class="matter-editable" data-field="epilogue_content" contenteditable="true" style="font-family:'BookkMyungjo', '부크크 명조', 'Nanum Myeongjo', serif; font-size:0.95rem; line-height:2.05; color:#3A2E24; white-space:pre-line; padding:8px 0;" title="맺음말 본문을 클릭하거나 드래그하여 자유롭게 수정하세요.">
              ${d.epilogueContent || epPreset.content || ""}
            </div>
          </div>
          <div style="text-align:right; font-family:'BookkMyungjo', '부크크 명조', 'Nanum Myeongjo', serif; font-size:0.9rem; color:#5A4A3A; line-height:1.7;">
            <div class="matter-editable" data-field="epilogue_date_author" contenteditable="true" style="white-space:pre-line; display:inline-block;" title="날짜 및 서명">
              2026년 겨울의 문턱에서\n지은이 ${d.author || "임종훈"} 지음
            </div>
          </div>
        </div>
      `;

      // 우측 43면: 정식 출판 판권지 (Colophon)
      const bookTitle = d.title || colPreset.title || "노을빛 기억";
      const bookAuthor = d.author || colPreset.author || "임종훈";
      const pubDate = d.publishedDate || colPreset.published_date || "2026년   월   일";
      const pubCeo = colPreset.publisher_ceo || "한건희";
      const pubCompany = d.publisher || colPreset.publisher || "주식회사 부크크";
      const regNo = colPreset.reg_no || "2014.07.15.(제2014-16호)";
      const addr = colPreset.address || "서울특별시 금천구 가산디지털1로 119 SK트윈타워 A동 305호";
      const tel = colPreset.phone || "1670-8316";
      const email = colPreset.email || "info@bookk.co.kr";
      const site = colPreset.homepage || "www.bookk.co.kr";
      const isbnVal = d.isbn || colPreset.isbn || "";
      const copyNotice = colPreset.copyright || `본 책은 저작자의 지적 재산으로서 무단 전재와 복제를 금합니다.\n\n이 책의 글과 그림은 저자의 실제 경험과 선택을 바탕으로\n생성형 AI의 도움을 받아 제작·편집되었습니다.`;

      ovRight.innerHTML = `
        <div class="matter-page-inner matter-theme-${this.currentTheme}" style="height:100%; display:flex; flex-direction:column; justify-content:flex-end; padding:45px 36px 36px 36px; background:#FAF7F2; font-family:'BookkMyungjo', '부크크 명조', 'Nanum Myeongjo', serif; font-size:0.83rem; color:#4A3A2C; line-height:1.8; box-sizing:border-box;">
          <h4 class="matter-editable" data-field="colophon_title" contenteditable="true" style="font-size:1.3rem; color:#2C1D11; margin:0 0 6px 0; font-weight:700;" title="도서명">
            ${bookTitle}
          </h4>
          <div style="font-size:0.9rem; color:#5A4A3A; margin-bottom:20px;">
            지은이 &nbsp;<span class="matter-editable" data-field="colophon_author" contenteditable="true" style="font-weight:600;">${bookAuthor}</span>
          </div>

          <div style="border-top:1.5px solid #2C1D11; padding-top:16px; margin-bottom:20px; font-size:0.82rem; line-height:1.9;">
            <div>발 &nbsp; 행 &nbsp; <span class="matter-editable" data-field="colophon_published_date" contenteditable="true">${pubDate}</span></div>
            <div>펴 낸 이 &nbsp; <span class="matter-editable" data-field="colophon_publisher_ceo" contenteditable="true">${pubCeo}</span></div>
            <div>펴 낸 곳 &nbsp; <span class="matter-editable" data-field="colophon_publisher" contenteditable="true">${pubCompany}</span></div>
            <div style="margin-top:8px;">출판사등록 &nbsp; <span class="matter-editable" data-field="colophon_reg_no" contenteditable="true">${regNo}</span></div>
            <div>주 &nbsp; 소 &nbsp; <span class="matter-editable" data-field="colophon_address" contenteditable="true">${addr}</span></div>
            <div>전 &nbsp; 화 &nbsp; <span class="matter-editable" data-field="colophon_phone" contenteditable="true">${tel}</span></div>
            <div>이 메 일 &nbsp; <span class="matter-editable" data-field="colophon_email" contenteditable="true">${email}</span></div>
            <div>ISBN &nbsp; &nbsp;<span class="matter-editable" data-field="colophon_isbn" contenteditable="true">${isbnVal}</span></div>
            <div>${site}</div>
            <div style="margin-top:8px; font-weight:600;">ⓒ[ ${bookAuthor} ] 2026</div>
          </div>

          <div class="matter-editable" data-field="colophon_copyright" contenteditable="true" style="font-size:0.75rem; color:#6E5D4E; border-top:1px solid #D5C2B0; padding-top:14px; white-space:pre-line; line-height:1.7;" title="저작권 및 생성형 AI 윤리 표기">
${copyNotice}
          </div>
        </div>
      `;
    }

    renderGenericMatter(sec, d, ovLeft, ovRight) {
      ovLeft.innerHTML = `
        <div style="height:100%; background:#FAF7F2; display:flex; flex-direction:column; align-items:center; justify-content:center; color:#C4B29E; font-size:0.85rem; font-family:'BookkMyungjo', '부크크 명조', 'Nanum Myeongjo', serif; letter-spacing:2px;">
          ❦<br><span style="margin-top:8px; font-size:0.78rem;">[ ${sec.start_page}p ]</span>
        </div>
      `;
      ovRight.innerHTML = `
        <div class="matter-page-inner matter-theme-${this.currentTheme}" style="height:100%; display:flex; flex-direction:column; justify-content:center; align-items:center; padding:40px; background:#FAF7F2; text-align:center; box-sizing:border-box;">
          <h3 style="font-family:'BookkMyungjo', '부크크 명조', 'Nanum Myeongjo', serif; font-size:1.4rem; color:#2C1D11; margin-bottom:12px;">${sec.title}</h3>
          <div style="font-size:0.9rem; color:#8C7560;">${sec.subtitle || ''}</div>
        </div>
      `;
    }

    /**
     * 편집 가능한 필드들에 포커스 및 인라인 서식 바 이벤트 연결
     */
    bindEditableEvents(ovLeft, ovRight) {
      const editables = document.querySelectorAll(".matter-editable");
      editables.forEach(elem => {
        elem.addEventListener("focus", () => {
          elem.style.outline = "2px solid #C89B6D";
          elem.style.background = "rgba(255, 255, 255, 0.85)";
          elem.style.borderRadius = "4px";
        });
        elem.addEventListener("blur", () => {
          elem.style.outline = "none";
          elem.style.background = "transparent";
        });
      });
    }

    /**
     * [💾 부속물 저장]: 화면의 수정 필드를 수집하여 API로 영구 저장
     */
    async saveCurrentMatter() {
      if (!this.currentSection) return;
      const sec = this.currentSection;
      const payloadData = {};

      const editables = document.querySelectorAll(".matter-editable");
      editables.forEach(elem => {
        const field = elem.dataset.field;
        if (!field) return;
        const val = elem.innerText.trim();

        if (field === "title" || field === "colophon_title") payloadData.title = val;
        else if (field === "part_no") {
          payloadData.part_no = val;
          payloadData.subtitle = val;
        }
        else if (field === "part_title") {
          payloadData.part_title = val;
          if (elem.dataset.oldTitle) payloadData.old_part_title = elem.dataset.oldTitle;
        }
        else if (field === "part_author") {
          const cleanAuth = val.replace(/^지은이\s*[:|]?\s*/, '').trim();
          payloadData.part_author = cleanAuth;
          payloadData.author = cleanAuth;
        }
        else if (field === "subtitle") payloadData.subtitle = val;
        else if (field === "author" || field === "colophon_author") payloadData.author = val;
        else if (field === "publisher" || field === "colophon_publisher") payloadData.publisher = val;
        else if (field === "price" || field === "colophon_price") payloadData.price = val;
        else if (field === "isbn" || field === "colophon_isbn") payloadData.isbn = val;
        else if (field === "blurb") payloadData.blurb = val;
        else if (field === "prologue_content") payloadData.prologue_content = val;
        else if (field === "epilogue_content") payloadData.epilogue_content = val;
        else if (field === "colophon_published_date") payloadData.published_date = val;
        else if (field === "toc_right_quote") payloadData.toc_right_quote = val;
        else payloadData[field] = val;
      });

      // 부 / 챕터 간지(Part Divider)일 때 통합 목차 타이틀 조합
      if (sec.id && sec.id.startsWith('part_')) {
        const pNo = (payloadData.part_no || sec.subtitle || "제1부").trim();
        const pTitle = (payloadData.part_title !== undefined ? payloadData.part_title : (sec.data && sec.data.part_title) || "").trim();
        const pAuth = (payloadData.part_author !== undefined ? payloadData.part_author : (sec.data && sec.data.author) || "").trim();

        let fullTitle = pNo;
        if (pTitle) {
          fullTitle = `${pNo}: ${pTitle}`;
        }
        if (pAuth) {
          fullTitle += ` (${pAuth})`;
        }
        payloadData.title = fullTitle;
      }

      try {
        if (sec.id === 'epilogue' || sec.id === 'colophon') {
          // 맺음말(epilogue)과 판권지(colophon) 동시 영구 저장
          const epContent = payloadData.epilogue_content || payloadData.content;
          if (epContent) {
            await fetch("/api/book/structure/update_section", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                section_id: "epilogue",
                data: { content: epContent }
              })
            });
          }
          await fetch("/api/book/structure/update_section", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              section_id: "colophon",
              data: payloadData
            })
          });
        } else if (sec.id === 'back_cover') {
          // 뒤표지 저장
          await fetch("/api/book/structure/update_section", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              section_id: "back_cover",
              data: {
                blurb: payloadData.blurb,
                price: payloadData.price,
                isbn: payloadData.isbn
              }
            })
          });
        } else {
          // 기타 일반 부속물 저장
          await fetch("/api/book/structure/update_section", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              section_id: sec.id,
              data: payloadData
            })
          });
        }

        if (typeof Swal !== 'undefined') {
          Swal.fire({
            icon: "success",
            title: "조판 완료 및 저장",
            text: `[${sec.title || sec.subtitle || '부속물'}] 조판 상태가 책 전체 구성에 영구 반영되었습니다.`,
            timer: 1600,
            showConfirmButton: false
          });
        } else {
          alert(`[${sec.title || sec.subtitle || '부속물'}] 조판 완료 및 저장 성공!`);
        }
        if (typeof window.loadStatus === 'function') {
          await window.loadStatus();
        }
        if (typeof window.refreshBookStructure === 'function') {
          await window.refreshBookStructure();
        }
        if (window.dtpEditor && typeof window.dtpEditor.ensureStatusLoaded === 'function') {
          await window.dtpEditor.ensureStatusLoaded(true);
        }
      } catch (err) {
        console.error("부속물 저장 예외:", err);
        alert(`저장 중 오류 발생: ${err.message}`);
      }
    }

    /**
     * [✨ 기본 예시 불러오기]: 표준 예시 템플릿으로 원클릭 리셋
     */
    resetToDefaultPreset() {
      if (!this.currentSection) return;
      const sec = this.currentSection;

      const doReset = () => {
        const ovLeft = document.getElementById("dtpMatterOverlayLeft");
        const ovRight = document.getElementById("dtpMatterOverlayRight");
        if (ovLeft && ovRight) {
          // 세부 데이터를 프리셋 기본값으로 강제 리셋하여 다시 렌더링
          sec.data = {};
          this.renderSpread(sec, ovLeft, ovRight);
          if (typeof Swal !== 'undefined') {
            Swal.fire({
              icon: "info",
              title: "기본 예시 불러오기 완료",
              text: "품격 있는 시집 표준 예시 템플릿이 로드되었습니다. 자유롭게 수정 후 [부속물 저장]을 누르세요.",
              timer: 2000,
              showConfirmButton: false
            });
          }
        }
      };

      if (typeof Swal !== 'undefined') {
        Swal.fire({
          title: "기본 예시 템플릿으로 복원하시겠습니까?",
          text: "현재 화면에서 수정한 내용이 표준 예시 문안으로 초기화됩니다.",
          icon: "question",
          showCancelButton: true,
          confirmButtonText: "예, 기본 예시로 복원",
          cancelButtonText: "취소",
          confirmButtonColor: "#D97706"
        }).then((result) => {
          if (result.isConfirmed) doReset();
        });
      } else {
        if (confirm("기본 예시 템플릿으로 복원하시겠습니까?")) doReset();
      }
    }

    /**
     * [🎨 스타일 변경]: 서정 수채 / 정통 문학 / 모던 미니멀
     */
    changeTheme(newTheme) {
      this.currentTheme = newTheme;
      const ovLeft = document.getElementById("dtpMatterOverlayLeft");
      const ovRight = document.getElementById("dtpMatterOverlayRight");
      if (this.currentSection && ovLeft && ovRight) {
        this.renderSpread(this.currentSection, ovLeft, ovRight);
      }
    }

    /**
     * 표지 일러스트 변경 트리거
     */
    openCoverImagePicker() {
      const fileInput = document.getElementById("viewerFileInput");
      if (fileInput) {
        fileInput.click();
      }
    }
  }

  // 전역 인스턴스 노출
  window.DtpMatterTemplateEngine = DtpMatterTemplateEngine;
  window.dtpMatterEngine = new DtpMatterTemplateEngine();

})(window);
