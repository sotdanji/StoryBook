export type Cue = {start:number; end:number; text:string};
export type AspectRatio = '16:9' | '9:16';
export type SpectrumStyle = 'bar' | 'mirror' | 'wave' | 'off';
export type VideoType = 'poem' | 'song';
export type LyricMode = 'rolling' | 'focus2line';

export type VideoProps = {
  spectrum: string;
  title: string;
  audio: string;
  cover: string;
  duration: number;
  cues: Cue[];
  aspectRatio?: AspectRatio;
  spectrumStyle?: SpectrumStyle;
  videoType?: VideoType;
  lyricMode?: LyricMode;
};
