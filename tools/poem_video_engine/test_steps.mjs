
import path from 'node:path';
import {bundle} from '@remotion/bundler';
import {selectComposition, renderStill} from '@remotion/renderer';

console.log('1. Testing bundle...');
try {
  const serveUrl = await bundle({entryPoint: path.resolve('src/index.tsx')});
  console.log('Bundle success, serveUrl:', serveUrl);
  
  console.log('2. Testing selectComposition...');
  const inputProps = {
    spectrum: 'assets/spectrum.json',
    title: '밍밭에서',
    audio: 'assets/audio.mp3',
    cover: 'assets/cover.jpg',
    duration: 10,
    cues: [],
    aspectRatio: '16:9',
    spectrumStyle: 'mirror',
    videoType: 'song',
    lyricMode: 'focus2line'
  };
  const composition = await selectComposition({serveUrl, id: 'MusicStep', inputProps, logLevel: 'verbose'});
  console.log('selectComposition success:', composition.id, composition.width, composition.height);

  console.log('3. Testing renderStill...');
  await renderStill({serveUrl, composition, inputProps, frame: 0, output: 'test_preview.png', logLevel: 'verbose'});
  console.log('renderStill success!');
} catch (e) {
  console.error('ERROR in step:');
  console.error(e);
}
