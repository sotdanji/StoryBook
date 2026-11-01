import {readdir,readFile,lstat} from 'node:fs/promises';
import {execFileSync,spawn} from 'node:child_process';
import path from 'node:path';
import {parseSrt} from './parse-srt.mjs';
export class UserError extends Error {constructor(message,options){super(message,options);this.name='UserError';}}
const kinds=[['audio','음원',['.mp3','.wav'],'MP3 또는 WAV'],['cover','커버 이미지',['.jpg','.jpeg','.png'],'JPG, JPEG 또는 PNG'],['srt','가사',['.srt'],'SRT']];
export async function scanInput(folder) {
  let entries;
  try{entries=await readdir(folder,{withFileTypes:true});}catch(error){if(error.code==='ENOENT')throw new UserError('input 폴더가 없습니다. 프로젝트 안에 input 폴더를 만들고 음원·커버 이미지·SRT를 넣어주세요.');throw error;}
  const found={},errors=[];
  for(const [key,label,extensions,hint] of kinds){
    const matches=entries.filter(e=>!e.name.startsWith('.') && extensions.includes(path.extname(e.name).toLowerCase()) && (e.isFile()||e.isSymbolicLink()));
    if(!matches.length)errors.push(`${label} 파일을 찾을 수 없습니다. input 폴더에 ${hint} 파일을 하나 넣어주세요.`);
    else if(matches.length>1)errors.push(`${label} 파일이 ${matches.length}개 있습니다: ${matches.map(e=>e.name).join(', ')}\n사용할 ${label} 파일 하나만 남겨주세요.`);
    else if(matches[0].isSymbolicLink())errors.push(`${matches[0].name}은 원본 파일이 아닌 연결 파일입니다. 원본 파일을 input 폴더로 복사해주세요.`);
    else found[key]=path.join(folder,matches[0].name);
  }
  if(errors.length)throw new UserError(errors.join('\n\n'));
  found.title=path.basename(found.audio,path.extname(found.audio));
  if(!found.title.trim())throw new UserError('음원 파일 이름에 곡 제목을 넣어주세요.');
  return found;
}
export function probe(file){return JSON.parse(execFileSync('ffprobe',['-v','error','-show_format','-show_streams','-of','json',file],{encoding:'utf8',stdio:['ignore','pipe','pipe']}));}
export async function inspectAudio(file){
  try {
    const metadata=probe(file);
    if(!metadata.streams.some(s=>s.codec_type==='audio'))throw new Error('No audio stream');
    // Count decoded samples, not container padding or version-dependent progress timestamps.
    // Stream to avoid buffering the full track merely to determine its duration.
    const bytes=await new Promise((resolve,reject)=>{
      const child=spawn('ffmpeg',['-v','error','-xerror','-i',file,'-map','0:a:0','-vn','-sn','-dn','-ac','1','-ar','48000','-f','s16le','pipe:1'],{stdio:['ignore','pipe','pipe'],shell:false,windowsHide:true});
      let count=0,stderr='';
      child.stdout.on('data',chunk=>{count+=chunk.length;});
      child.stderr.on('data',chunk=>{stderr=(stderr+chunk).slice(-16000);});
      child.once('error',reject);
      child.once('close',code=>code===0?resolve(count):reject(new Error(stderr||`Audio decoder exited ${code}`)));
    });
    const duration=bytes/2/48000;
    if(!Number.isFinite(duration)||duration<=0)throw new Error('Invalid audio duration');
    return {duration,metadata};
  }catch(error){throw new UserError(`음원 “${path.basename(file)}”을 정상적으로 읽을 수 없습니다. 재생 가능한 MP3 또는 WAV 파일로 다시 저장해주세요.`,{cause:error});}
}
export function inspectCover(file){
  try {
    const metadata=probe(file),stream=metadata.streams.find(s=>s.codec_type==='video');
    if(!stream||!['png','mjpeg'].includes(stream.codec_name)||!stream.width||!stream.height)throw new Error('Invalid cover');
    execFileSync('ffmpeg',['-v','error','-xerror','-i',file,'-frames:v','1','-c:v','rawvideo','-f','null','-'],{stdio:['ignore','pipe','pipe']});
    return {width:stream.width,height:stream.height};
  }catch(error){throw new UserError(`커버 이미지 “${path.basename(file)}”을 읽을 수 없습니다. 정상적인 JPG 또는 PNG 파일로 다시 저장해주세요.`,{cause:error});}
}
export function decodeSrt(buffer) {
  try {
    const encoding=buffer[0]===0xff&&buffer[1]===0xfe?'utf-16le':buffer[0]===0xfe&&buffer[1]===0xff?'utf-16be':'utf-8';
    return new TextDecoder(encoding,{fatal:true}).decode(buffer);
  }catch(error){throw new UserError('가사 파일의 글자 인코딩을 읽을 수 없습니다. SRT를 UTF-8 형식으로 저장한 뒤 다시 넣어주세요.',{cause:error});}
}
export function normalizedSrt(cues) {
  const stamp=seconds=>{const ms=Math.round(seconds*1000);return `${String(Math.floor(ms/3600000)).padStart(2,'0')}:${String(Math.floor(ms/60000)%60).padStart(2,'0')}:${String(Math.floor(ms/1000)%60).padStart(2,'0')},${String(ms%1000).padStart(3,'0')}`;};
  return cues.map((cue,i)=>`${i+1}\n${stamp(cue.start)} --> ${stamp(cue.end)}\n${cue.text}`).join('\n\n')+'\n';
}
export async function validateInput(folder){
  const files=await scanInput(folder);
  for(const key of ['audio','cover','srt'])if((await lstat(files[key])).size===0)throw new UserError(`“${path.basename(files[key])}” 파일이 비어 있습니다. 내용을 확인한 뒤 다시 넣어주세요.`);
  const {duration}=await inspectAudio(files.audio),image=inspectCover(files.cover);
  let cues;
  try{cues=parseSrt(decodeSrt(await readFile(files.srt)),duration);}catch(error){if(error instanceof UserError)throw error;throw new UserError(`가사 파일 “${path.basename(files.srt)}”을 확인해주세요.\n${error.message}\n원본 가사와 시간은 임의로 바꾸지 않았습니다.`,{cause:error});}
  return {...files,duration,image,cues};
}
