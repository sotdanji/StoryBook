# `dtp_spread_ui` — 2-Layer 양면 책 펼침 조판 뷰어 (Web Component & ES Module)

StoryBook Studio의 양면 펼침(Spread) 조판 렌더러를 **표준 W3C Web Component (`<storybook-dtp-spread>`)** 및 **ES Module (`import`)**로 패키징한 독립 모듈입니다.

## 1. W3C Web Component (`<storybook-dtp-spread>`) 사용법
```html
<script type="module" src="/static/js/main.esm.js"></script>

<storybook-dtp-spread id="myBookSpread" width="960" height="660" spread-part="1"></storybook-dtp-spread>

<script type="module">
  const spreadEl = document.getElementById("myBookSpread");
  spreadEl.work = {
    title: "외갓집 저녁노을",
    body: "장독대 위로 내려앉은 붉은 노을...",
    image: "/projects/노을빛_기억/images/01.png",
    layout_config: {
      page_count: 2,
      font_family: "Nanum Myeongjo",
      font_size_pt: 12,
      line_height_ratio: 1.65,
      pages: [
        { page_num: 1, usage: "image", role: "none" },
        { page_num: 2, usage: "text", role: "start" }
      ]
    }
  };
</script>
```

## 2. ES Module (`import`) 사용법 (Vite / React / Vue / Next.js)
```javascript
import { DtpSpreadViewer, mountDtpSpread } from "./dtp_spread_ui.esm.js";

const viewer = mountDtpSpread("#bookSpreadRoot", workData, { width: 960, height: 660 });
```
