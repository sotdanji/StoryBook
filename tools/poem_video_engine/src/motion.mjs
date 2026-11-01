// All motion is a pure function of composition time; no wall clock or randomness.
export const TRANSITION_SECONDS = 0.42;
export const ease = value => {const x=Math.min(1,Math.max(0,value));return x*x*(3-2*x);};
const mix=(a,b,t)=>a+(b-a)*t;
export function buildLyricTimeline(cues) {
  const events=[];
  const initial={anchor:0,weights:cues.map(()=>0)};
  for(let i=0;i<cues.length;i++) {
    const start=cues[i].start;
    const from=lyricState(events,start,initial);
    events.push({time:start,from,to:{anchor:i,weights:cues.map((_,j)=>i===j?1:0)}});
    if(i===cues.length-1 || cues[i+1].start>cues[i].end) {
      const end=cues[i].end;
      events.push({time:end,from:lyricState(events,end,initial),to:{anchor:i,weights:cues.map(()=>0)}});
    }
  }
  return {events,initial};
}
export function lyricState(events,time,initial) {
  const event=events.findLast(e=>e.time<=time);
  if(!event)return initial;
  const t=ease((time-event.time)/TRANSITION_SECONDS);
  return {anchor:mix(event.from.anchor,event.to.anchor,t),weights:event.to.weights.map((v,i)=>mix(event.from.weights[i],v,t))};
}
export function lyricSlot(offset) {
  // Preserve every approved resting position and box height.
  const lower=Math.floor(offset),t=offset-lower;
  const slot=n=>({top:350+n*(n<0?172:202),height:n===0?180:156});
  const a=slot(lower),b=slot(lower+1);
  return {top:mix(a.top,b.top,t),height:mix(a.height,b.height,t)};
}
export function playbackMotion(frame,fps,duration) {
  const time=Math.min(duration,Math.max(0,frame/fps));
  return {time,progress:Math.min(1,time/duration),rotation:time*6,
    scale:1+0.008*(1-Math.cos(time*Math.PI/60)),
    panX:3*Math.sin(time*Math.PI/60),panY:2*(1-Math.cos(time*Math.PI/60))};
}
