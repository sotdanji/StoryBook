// Keep the existing 640px lyric safe area and its 82px screen-right margin.
export const LYRIC_WIDTH = 640;
export const MIN_LYRIC_SIZE = 32;
const MAX_ACTIVE_SIZE = 60;
const MAX_RESTING_SIZE = 40;
const FIT_WIDTH = LYRIC_WIDTH - 1; // Guard against subpixel browser rounding.
const graphemes = new Intl.Segmenter('ko', {granularity:'grapheme'});

// measure(text, size, weight) uses the loaded production font in the browser.
export function createLyricLayout(source, measure) {
  // Display-only joining of SRT line breaks; never edit the original cue text.
  const text = source.replace(/\r\n?|\n/g, ' ').trim();
  const widthAt = (line, size) => Math.max(...[400,500,600].map(weight=>measure(line,size,weight)));
  const fits = (line, size) => widthAt(line,size) <= FIT_WIDTH;
  const fitSingle = maximum => {
    if(fits(text,maximum))return maximum;
    let lower=MIN_LYRIC_SIZE,upper=maximum;
    for(let i=0;i<14;i++) {
      const middle=(lower+upper)/2;
      if(fits(text,middle))lower=middle;else upper=middle;
    }
    return Math.floor(lower*10)/10;
  };
  if(fits(text,MIN_LYRIC_SIZE))return {lines:[text],activeSize:fitSingle(MAX_ACTIVE_SIZE),restingSize:fitSingle(MAX_RESTING_SIZE)};

  // A fixed split is shared by active/inactive states, preventing reflow while scrolling.
  const units=Array.from(graphemes.segment(text),entry=>entry.segment);
  const candidates=[];
  for(let i=1;i<units.length;i++) {
    const first=units.slice(0,i).join('').trimEnd(),second=units.slice(i).join('').trimStart();
    if(!first||!second||/^[,.;:!?…，。！？、)\]}]/u.test(second))continue;
    const a=widthAt(first,MIN_LYRIC_SIZE),b=widthAt(second,MIN_LYRIC_SIZE);
    if(a<=FIT_WIDTH&&b<=FIT_WIDTH)candidates.push({lines:[first,second],wordBoundary:/\s/u.test(units[i-1])||/\s/u.test(units[i]),imbalance:Math.abs(a-b)});
  }
  candidates.sort((a,b)=>Number(b.wordBoundary)-Number(a.wordBoundary)||a.imbalance-b.imbalance);
  if(!candidates.length)throw new Error('한 가사 구간이 최소 글자 크기(32px)에서도 두 줄을 넘습니다. 해당 SRT 구간을 나누어주세요.');
  return {lines:candidates[0].lines,activeSize:MIN_LYRIC_SIZE,restingSize:MIN_LYRIC_SIZE};
}
