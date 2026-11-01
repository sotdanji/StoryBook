import {bundle} from '@remotion/bundler';
import {renderMedia,renderStill,selectComposition} from '@remotion/renderer';
import {copyFile,mkdir,writeFile,stat} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import path from 'node:path';
import {analyzeAudio} from './audio-spectrum.mjs';
import {probe} from './workflow.mjs';

export async function renderVideo(config,{log=console.log,detail=()=>{}}={}) {
  const {
    duration,
    cues,
    aspectRatio = '16:9',
    spectrumStyle = 'bar',
    videoType = 'poem',
    lyricMode = 'rolling'
  } = config;

  await mkdir('public/assets',{recursive:true});await mkdir(path.dirname(config.output),{recursive:true});
  await copyFile('node_modules/pretendard/dist/web/variable/woff2/PretendardVariable.woff2','public/assets/PretendardVariable.woff2');
  const audio=`assets/audio${path.extname(config.audio).toLowerCase()}`,cover=`assets/cover${path.extname(config.cover).toLowerCase()}`;
  await copyFile(config.audio,`public/${audio}`);await copyFile(config.cover,`public/${cover}`);
  log('음악의 움직임을 분석하고 있습니다.');
  const spectrum=analyzeAudio(config.audio,duration);
  await writeFile('public/assets/spectrum.json',JSON.stringify(spectrum));

  const inputProps = {
    spectrum: 'assets/spectrum.json',
    title: config.title,
    audio,
    cover,
    duration,
    cues,
    aspectRatio,
    spectrumStyle,
    videoType,
    lyricMode
  };

  const serveUrl=await bundle({entryPoint:path.resolve('src/index.tsx')});
  const composition=await selectComposition({serveUrl,id:'MusicStep',inputProps,logLevel:'error'});
  await renderStill({serveUrl,composition,inputProps,frame:Math.min(Math.floor(duration*30/2),composition.durationInFrames-1),output:config.preview,logLevel:'error'});
  let last=-1;
  await renderMedia({
    serveUrl,
    composition,
    inputProps,
    codec:'h264',
    audioCodec:'aac',
    pixelFormat:'yuv420p',
    crf:24,
    concurrency:2,
    outputLocation:config.output,
    logLevel:'error',
    onBrowserLog:entry=>detail(JSON.stringify(entry)),
    onProgress:({progress})=>{
      const p=Math.floor(progress*10);
      if(p!==last){last=p;log(`영상 만드는 중 · ${p*10}%`);}
    }
  });

  log('완성된 영상이 정상적으로 재생되는지 확인하고 있습니다.');
  const result=probe(config.output);
  const video=result.streams.find(s=>s.codec_type==='video');
  const audioStream=result.streams.find(s=>s.codec_type==='audio');

  const expectedWidth = aspectRatio === '9:16' ? 1080 : 1920;
  const expectedHeight = aspectRatio === '9:16' ? 1920 : 1080;

  if(
    (await stat(config.output)).size===0||
    video?.codec_name!=='h264'||
    video.width!==expectedWidth||
    video.height!==expectedHeight||
    video.avg_frame_rate!=='30/1'||
    audioStream?.codec_name!=='aac'||
    Math.abs(Number(result.format.duration)-duration)>1/30+.025
  ) {
    throw new Error(`출력 파일 규격 검증에 실패했습니다. (기대 해상도: ${expectedWidth}x${expectedHeight}, 실제: ${video?.width}x${video?.height})`);
  }

  execFileSync('ffmpeg',['-v','error','-xerror','-i',config.output,'-c:v','rawvideo','-f','null','-'],{stdio:['ignore','pipe','pipe']});
  const report={
    sourceDuration:duration,
    frameDuration:composition.durationInFrames/30,
    cueCount:cues.length,
    title:config.title,
    aspectRatio,
    spectrumStyle,
    videoType,
    lyricMode,
    output:result
  };
  await writeFile(config.verification,JSON.stringify(report,null,2));
  return report;
}
