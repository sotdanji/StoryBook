import {mkdir,open,writeFile,copyFile,unlink,lstat} from 'node:fs/promises';
import {randomUUID} from 'node:crypto';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {outputName} from './output-name.mjs';
import {publishVideo} from './publish-video.mjs';
import {checkEnvironment} from './environment.mjs';
import {validateInput,normalizedSrt,UserError} from './workflow.mjs';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
process.chdir(root);
const checkOnly=process.argv.includes('--check');

// 커맨드라인 옵션 파싱 (화면 비율, 스펙트럼 스타일, 비디오 타입, 가사 연출 모드)
let aspectRatio = '16:9';
let spectrumStyle = 'bar';
let videoType = 'poem';
let lyricMode = 'rolling';

for (let i = 0; i < process.argv.length; i++) {
  if (process.argv[i] === '--aspect-ratio' && process.argv[i + 1]) {
    aspectRatio = process.argv[i + 1];
  } else if (process.argv[i] === '--spectrum' && process.argv[i + 1]) {
    spectrumStyle = process.argv[i + 1];
  } else if (process.argv[i] === '--video-type' && process.argv[i + 1]) {
    videoType = process.argv[i + 1];
  } else if (process.argv[i] === '--lyric-mode' && process.argv[i + 1]) {
    lyricMode = process.argv[i + 1];
  } else if (process.argv[i] === '--shorts') {
    aspectRatio = '9:16';
  }
}

const runId=new Date().toISOString().replace(/[:.]/g,'-')+'-'+randomUUID().slice(0,8);
const run=path.join(root,'.musicstep','runs',runId);
const lockPath=path.join(root,'.musicstep','make-video.lock');
let lock,stage='환경 확인';const details=[];
const detail=value=>details.push(String(value));

try {
  await mkdir(run,{recursive:true});
  try{lock=await open(lockPath,'wx');await lock.writeFile(JSON.stringify({pid:process.pid,started:new Date().toISOString(),run}));}
  catch(error){if(error.code==='EEXIST')throw new UserError('다른 영상 제작 작업이 진행 중이거나 이전 작업이 중단되었습니다. 실행 중인 작업을 기다려주세요.');throw error;}
  console.log('MusicStep · 영상 제작 준비');
  await checkEnvironment(root,{install:!checkOnly,detail});
  stage='입력 파일 확인';
  const input=await validateInput(path.join(root,'input'));
  console.log(`곡 제목: ${input.title}\n음원 길이: ${input.duration.toFixed(3)}초 · 가사 ${input.cues.length}개 · 비율: ${aspectRatio} · 스펙트럼: ${spectrumStyle} · 타입: ${videoType} · 가사모드: ${lyricMode}`);
  if(checkOnly){console.log('준비가 완료되었습니다. 음원·커버·가사와 실행 환경에 문제가 없습니다.');}
  else {
    let suffix = '';
    if (videoType === 'song') suffix += '_song';
    if (aspectRatio === '9:16') suffix += '_shorts';
    const outTitle = `${input.title}${suffix}`;
    const output=path.join(root,'output',outputName(outTitle));
    let previous;
    try{previous=await lstat(output);if(!previous.isFile())throw new UserError('같은 이름의 출력 경로가 일반 파일이 아닙니다. output 폴더의 해당 경로를 확인해주세요.');}catch(error){if(error.code!=='ENOENT')throw error;}
    await writeFile(path.join(run,'normalized.srt'),normalizedSrt(input.cues));
    await writeFile(path.join(run,'input.json'),JSON.stringify({audio:input.audio,cover:input.cover,srt:input.srt,title:input.title,duration:input.duration,aspectRatio,spectrumStyle,videoType,lyricMode,output},null,2));

    const audio=path.join(run,`audio${path.extname(input.audio).toLowerCase()}`),cover=path.join(run,`cover${path.extname(input.cover).toLowerCase()}`);
    await copyFile(input.audio,audio);await copyFile(input.cover,cover);
    stage='영상 생성';
    const {renderVideo}=await import('./render-engine.mjs');
    const temporary=path.join(run,'render.mp4');
    await renderVideo({
      ...input,
      audio,
      cover,
      aspectRatio,
      spectrumStyle,
      videoType,
      lyricMode,
      output:temporary,
      preview:path.join(run,'preview.png'),
      verification:path.join(run,'verification.json')
    },{detail});

    stage='완성 영상 저장';await mkdir(path.dirname(output),{recursive:true});
    const backup=await publishVideo(temporary,output,path.join(root,'output','previous',runId));
    if(backup)console.log(`이전 영상 보관: ${backup}`);
    console.log(`\n영상이 완성되었습니다.\n${output}`);
    await writeFile(path.join(run,'result.json'),JSON.stringify({status:'complete',output,preview:path.join(run,'preview.png'),duration:input.duration,aspectRatio,spectrumStyle,videoType,lyricMode},null,2));
  }
}catch(error){
  detail(JSON.stringify(error, Object.getOwnPropertyNames(error), 2));
  if(error?.stack)detail(error.stack);
  if(error?.cause)detail(JSON.stringify(error.cause, Object.getOwnPropertyNames(error.cause || {}), 2));
  if(error?.stderr)detail(String(error.stderr));
  console.error(`\n${error instanceof UserError?error.message:`${stage} 중 문제가 생겼습니다. 원본 파일은 변경하지 않았습니다.`}`);
  console.error(`제작 기록: ${path.join(run,'details.log')}`);process.exitCode=1;
}finally{
  try{await writeFile(path.join(run,'details.log'),details.join('\n'));}catch{}
  if(lock){await lock.close();await unlink(lockPath);}
}
