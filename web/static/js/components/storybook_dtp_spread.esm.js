/**
 * web/static/js/components/storybook_dtp_spread.esm.js
 * ES Module Web Component (<storybook-dtp-spread>) for StoryBook Studio & Vite
 */

export const FONT_FAMILY_MAP = {
  "Nanum Myeongjo": "'Nanum Myeongjo', serif",
  "Gowun Batang": "'Gowun Batang', serif",
  "Noto Serif KR": "'Noto Serif KR', serif",
  "KoPub Batang": "'KoPub Batang', 'Nanum Myeongjo', serif",
  "MaruBuri": "'MaruBuri', 'Nanum Myeongjo', serif"
};

export class DtpSpreadViewer {
  constructor(container, options = {}) {
    this.container = typeof container === "string" ? document.querySelector(container) : container;
    this.options = Object.assign({
      width: 960,
      height: 660,
      defaultFontFamily: "Nanum Myeongjo",
      defaultFontSizePt: 13,
      defaultLineHeight: 1.6,
    }, options);
    this.currentWork = null;
    this.currentSpreadPart = 1;
  }

  ptToPx(pt) {
    return ((parseFloat(pt) || 12) / 12.0) * 15.2;
  }

  getTotalSpreads(work) {
    const cfg = (work && work.layout_config) || {};
    const pageCount = parseInt(cfg.page_count, 10) || (Array.isArray(cfg.pages) ? cfg.pages.length : 2);
    return Math.max(1, Math.ceil(pageCount / 2));
  }

  renderWork(work, spreadPart = 1) {
    if (!this.container || !work) return;
    this.currentWork = work;
    this.currentSpreadPart = spreadPart;

    const cfg = work.layout_config || {};
    const pages = Array.isArray(cfg.pages) && cfg.pages.length >= 2
      ? cfg.pages
      : [
          { page_num: 1, usage: "image", role: "none", image_file: work.image || work.image_file || "" },
          { page_num: 2, usage: "text", role: "start" }
        ];

    const leftIdx = (spreadPart - 1) * 2;
    const rightIdx = leftIdx + 1;

    this.container.innerHTML = `
      <div class="dtp-standalone-spread" style="width:${this.options.width}px; height:${this.options.height}px; display:flex; position:relative; background:#FAF6F0; border:1px solid #D8C8B4; border-radius:6px; overflow:hidden; box-shadow:0 12px 32px rgba(45,30,15,0.18);">
        <div class="dtp-standalone-page dtp-left" style="width:50%; height:100%; position:relative; border-right:1px solid rgba(138,109,86,0.22);"></div>
        <div class="dtp-standalone-page dtp-right" style="width:50%; height:100%; position:relative;"></div>
      </div>
    `;

    const leftEl = this.container.querySelector(".dtp-left");
    const rightEl = this.container.querySelector(".dtp-right");
    this._renderSinglePage(leftEl, pages[leftIdx] || { usage: "blank" }, work, cfg);
    this._renderSinglePage(rightEl, pages[rightIdx] || { usage: "blank" }, work, cfg);
  }

  _renderSinglePage(pageEl, pageCfg, work, cfg) {
    const usage = pageCfg.usage || "blank";
    const fontFamily = FONT_FAMILY_MAP[cfg.font_family] || FONT_FAMILY_MAP[this.options.defaultFontFamily];
    const fontPx = this.ptToPx(cfg.font_size_pt || this.options.defaultFontSizePt);
    const lineHeight = parseFloat(cfg.line_height_ratio) || this.options.defaultLineHeight;
    const textAlign = cfg.text_align || "left";

    if (usage === "image" || usage === "image_text") {
      const imgSrc = pageCfg.image_file || work.image || work.image_file || "";
      if (imgSrc) {
        const imgWrap = document.createElement("div");
        imgWrap.style.cssText = "position:absolute; inset:28px; display:flex; align-items:center; justify-content:center; overflow:hidden;";
        imgWrap.innerHTML = `<img src="${imgSrc}" style="max-width:100%; max-height:100%; object-fit:contain; border-radius:2px;">`;
        pageEl.appendChild(imgWrap);
      }
    }

    if (usage === "text" || usage === "image_text") {
      const textWrap = document.createElement("div");
      textWrap.style.cssText = `position:absolute; inset:48px 40px 44px 40px; font-family:${fontFamily}; font-size:${fontPx}px; line-height:${lineHeight}; text-align:${textAlign}; color:#2C221E; white-space:pre-wrap; overflow:hidden;`;
      const bodyText = pageCfg.custom_text || work.body || work.poem_body || "";
      const titleHtml = (pageCfg.role !== "continue" && work.title)
        ? `<h3 style="font-size:${(fontPx * 1.28).toFixed(1)}px; font-weight:700; margin:0 0 18px 0; color:#3A2618;">${work.title}</h3>`
        : "";
      textWrap.innerHTML = `${titleHtml}<div>${bodyText}</div>`;
      pageEl.appendChild(textWrap);
    }
  }
}

export class StorybookDtpSpreadElement extends HTMLElement {
  static get observedAttributes() {
    return ["width", "height", "spread-part"];
  }

  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._work = null;
    this._mountEl = document.createElement("div");
    this.shadowRoot.appendChild(this._mountEl);
    this._viewer = new DtpSpreadViewer(this._mountEl, {
      width: parseInt(this.getAttribute("width"), 10) || 960,
      height: parseInt(this.getAttribute("height"), 10) || 660,
    });
  }

  connectedCallback() {
    if (this._work) {
      const part = parseInt(this.getAttribute("spread-part"), 10) || 1;
      this._viewer.renderWork(this._work, part);
    }
  }

  attributeChangedCallback(name, oldVal, newVal) {
    if (oldVal === newVal || !this._viewer) return;
    if (name === "width" || name === "height") {
      this._viewer.options[name] = parseInt(newVal, 10) || (name === "width" ? 960 : 660);
    }
    if (this._work) {
      const part = parseInt(this.getAttribute("spread-part"), 10) || 1;
      this._viewer.renderWork(this._work, part);
    }
  }

  set work(val) {
    this._work = val;
    if (this._viewer && val) {
      const part = parseInt(this.getAttribute("spread-part"), 10) || 1;
      this._viewer.renderWork(val, part);
    }
  }

  get work() {
    return this._work;
  }
}

export function registerStorybookDtpSpreadComponent() {
  if (typeof customElements !== "undefined" && !customElements.get("storybook-dtp-spread")) {
    customElements.define("storybook-dtp-spread", StorybookDtpSpreadElement);
  }
}

export function mount(container, work, options) {
  const viewer = new DtpSpreadViewer(container, options);
  if (work) viewer.renderWork(work, 1);
  return viewer;
}

if (typeof window !== "undefined") {
  registerStorybookDtpSpreadComponent();
  window.DtpSpreadUI = { DtpSpreadViewer, StorybookDtpSpreadElement, mount };
}

