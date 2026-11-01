import React from 'react';
import {Composition, registerRoot} from 'remotion';
import {LyricVideo} from './LyricVideo';
import sampleCues from '../samples/cues.json';
import type {VideoProps} from './types';

const defaults: VideoProps = {
  spectrum: 'assets/spectrum.json',
  title: 'Midnight Glow',
  audio: 'assets/audio.wav',
  cover: 'assets/cover.png',
  duration: 18,
  cues: sampleCues,
  aspectRatio: '16:9',
  spectrumStyle: 'bar'
};

registerRoot(() => (
  <Composition
    id="MusicStep"
    component={LyricVideo}
    width={1920}
    height={1080}
    fps={30}
    durationInFrames={540}
    defaultProps={defaults}
    calculateMetadata={({props}) => {
      const isShorts = props.aspectRatio === '9:16';
      return {
        width: isShorts ? 1080 : 1920,
        height: isShorts ? 1920 : 1080,
        durationInFrames: Math.ceil((props.duration || 18) * 30),
      };
    }}
  />
));
