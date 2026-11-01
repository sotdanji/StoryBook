export function parseSrt(source, duration = Infinity) {
  const normalized = source.replace(/^\uFEFF/, '').replace(/\r\n?/g, '\n').trim();
  if (!normalized) throw new Error('SRT에 가사가 없습니다.');
  const time = (h,m,s,ms) => Number(h)*3600 + Number(m)*60 + Number(s) + Number(ms)/1000;
  const cues = [];
  for (const [index, block] of normalized.split(/\n\s*\n/).entries()) {
    const lines = block.split('\n');
    if (/^\s*\d+\s*$/.test(lines[0])) lines.shift();
    const match = lines.shift()?.trim().match(/^(\d{2,}):([0-5]\d):([0-5]\d)[,.](\d{3})\s*-->\s*(\d{2,}):([0-5]\d):([0-5]\d)[,.](\d{3})$/);
    if (!match) throw new Error(`SRT ${index+1}번 구간의 시간을 확인해주세요.`);
    const start = time(...match.slice(1,5)), end = time(...match.slice(5,9));
    if (end <= start) throw new Error(`SRT ${index+1}번 종료 시간은 시작보다 늦어야 합니다.`);
    const text = lines.map(line => line.trim()).filter(Boolean).join('\n');
    if (!text) continue;
    if (end > duration + 0.001) throw new Error(`SRT ${index+1}번 가사가 음원 길이를 초과합니다.`);
    if (cues.length && start < cues.at(-1).end) throw new Error(`SRT ${index+1}번의 순서 또는 겹치는 시간을 확인해주세요.`);
    cues.push({start,end,text});
  }
  if (!cues.length) throw new Error('SRT에 표시할 가사가 없습니다.');
  return cues;
}
