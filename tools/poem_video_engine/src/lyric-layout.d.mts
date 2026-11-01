export const LYRIC_WIDTH:number;
export const MIN_LYRIC_SIZE:number;
export type LyricLayout={lines:string[];activeSize:number;restingSize:number};
export function createLyricLayout(source:string,measure:(text:string,size:number,weight:number)=>number):LyricLayout;
