import {createRequire} from 'node:module';
import {execFileSync} from 'node:child_process';
import path from 'node:path';
import {UserError} from './workflow.mjs';
export function compositorPackage(platform=process.platform,arch=process.arch){
  if(platform==='darwin'&&['arm64','x64'].includes(arch))return `@remotion/compositor-darwin-${arch}`;
  if(platform==='win32'&&arch==='x64')return '@remotion/compositor-win32-x64-msvc';
  throw new UserError('이 배포판은 macOS(Apple Silicon/Intel)와 Windows x64용입니다. 현재 운영체제 또는 Node.js 종류를 확인해주세요.');
}
export function mediaEnvironment(env,directory,platform=process.platform,ffmpegDirectory=directory){
  const result={...env},keys=Object.keys(result).filter(k=>k.toLowerCase()==='path');
  const current=keys.map(k=>result[k]).filter(Boolean).join(platform==='win32'?';':':');
  for(const key of keys)delete result[key];
  result.PATH=[...new Set([ffmpegDirectory,directory]),current].filter(Boolean).join(platform==='win32'?';':':');
  // Remotion's macOS binaries use colocated dynamic libraries.
  if(platform==='darwin')result.DYLD_LIBRARY_PATH=directory;
  return result;
}
export function prepareMediaTools(root){
  try{
    const require=createRequire(path.resolve(root,'package.json'));
    const directory=path.dirname(require.resolve(`${compositorPackage()}/package.json`));
    const ffmpegDirectory=path.dirname(require.resolve('ffmpeg-static/package.json'));
    const env=mediaEnvironment(process.env,directory,process.platform,ffmpegDirectory);
    for(const bin of ['ffmpeg','ffprobe'])execFileSync(path.join(bin==='ffmpeg'?ffmpegDirectory:directory,bin+(process.platform==='win32'?'.exe':'')),['-version'],{env,stdio:'pipe',windowsHide:true});
    // Process-local environment only: no user/system PATH changes.
    for(const key of Object.keys(process.env))if(key.toLowerCase()==='path')delete process.env[key];
    process.env.PATH=env.PATH;if(env.DYLD_LIBRARY_PATH)process.env.DYLD_LIBRARY_PATH=env.DYLD_LIBRARY_PATH;
    return directory;
  }catch(error){if(error instanceof UserError)throw error;throw new UserError('음악 처리용 구성 요소가 누락되었거나 실행이 차단되었습니다. Codex에서 패키지 설치 또는 보안 설정을 확인해주세요.',{cause:error});}
}
