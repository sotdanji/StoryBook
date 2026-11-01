import type {Cue} from './types';
type State={anchor:number;weights:number[]};
type Event={time:number;from:State;to:State};
export const TRANSITION_SECONDS:number;
export function ease(value:number):number;
export function buildLyricTimeline(cues:Cue[]):{events:Event[];initial:State};
export function lyricState(events:Event[],time:number,initial:State):State;
export function lyricSlot(offset:number):{top:number;height:number};
export function playbackMotion(frame:number,fps:number,duration:number):{time:number;progress:number;rotation:number;scale:number;panX:number;panY:number};
