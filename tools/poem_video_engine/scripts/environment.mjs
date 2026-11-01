import {readFile,access} from 'node:fs/promises';
import {execFileSync,spawn} from 'node:child_process';
import path from 'node:path';
import {compositorPackage,prepareMediaTools} from './runtime-tools.mjs';
import {UserError} from './workflow.mjs';
export async function dependencyProblems(root){
  const pkg=JSON.parse(await readFile(path.join(root,'package.json'),'utf8'));
  const issues=[];
  for(const [name,version] of Object.entries(pkg.dependencies)){
    try{const installed=JSON.parse(await readFile(path.join(root,'node_modules',name,'package.json'),'utf8'));if(installed.version!==version)issues.push(`${name}: 버전 불일치`);}catch{issues.push(`${name}: 설치 필요`);}
  }
  for(const file of ['node_modules/pretendard/dist/web/variable/woff2/PretendardVariable.woff2','node_modules/@remotion/renderer/dist/index.js','node_modules/@remotion/bundler/dist/index.js']){
    try{await access(path.join(root,file));}catch{issues.push(`${file}: 파일 누락`);}
  }
  return issues;
}
export async function checkEnvironment(root,{install=true,log=console.log,detail=()=>{}}={}){
  if(Number(process.versions.node.split('.')[0])<22)throw new UserError('영상 제작에는 Node.js 22 이상이 필요합니다. 설치 동의를 확인한 뒤 업데이트하고, 버전 확인 후 현재 영상 제작을 이어서 진행합니다.');
  try{await access(path.join(root,'package-lock.json'));await access(path.join(root,'src/index.tsx'));}catch{throw new UserError('프로젝트에 필요한 파일이 없습니다. MusicStep Template 폴더 전체를 열었는지 확인해주세요.');}
  compositorPackage();
  const issues=await dependencyProblems(root);
  const importsReady=()=>{
    try{execFileSync(process.execPath,['--input-type=module','-e',"await Promise.all(['remotion','react','@remotion/renderer','@remotion/bundler'].map(name=>import(name)))"],{cwd:root,stdio:'pipe'});return true;}
    catch(error){detail(error.stderr?String(error.stderr):error.stack);return false;}
  };
  if(!issues.length&&!importsReady())issues.push('구성 요소를 불러올 수 없어 복구가 필요합니다.');
  if(!issues.length){try{prepareMediaTools(root);return;}catch(error){detail(error.cause?.stack||error.stack);issues.push('음악 처리 구성 요소 복구 필요');}}
  detail(issues.join('\n'));
  if(!install)throw new UserError('영상 제작에 필요한 구성 요소가 아직 준비되지 않았습니다. Codex에 “리릭비디오 만들어줘”라고 요청하면 자동으로 준비합니다.');
  log('처음 실행에 필요한 구성 요소를 준비합니다. 인터넷 연결이 필요할 수 있습니다.');
  const npm=process.env.npm_execpath;
  // npm.cmd cannot be spawned safely without a shell on Windows. npm run provides
  // npm_execpath, so execute its JS entrypoint with Node and a real argument array.
  if(!npm)throw new UserError('Codex에서 npm run make-video 명령으로 다시 실행해주세요.');
  const command=process.execPath;
  const args=[npm,'ci','--include=dev','--include=optional','--no-audit','--no-fund'];
  await new Promise((resolve,reject)=>{
    const child=spawn(command,args,{cwd:root,stdio:['ignore','pipe','pipe'],shell:false,windowsHide:true});
    child.stdout.on('data',chunk=>detail(String(chunk)));child.stderr.on('data',chunk=>detail(String(chunk)));
    child.once('error',error=>reject(new UserError('필요한 구성 요소를 준비하지 못했습니다. Codex에서 실행 환경과 인터넷 연결을 확인해주세요.',{cause:error})));
    child.once('close',code=>code===0?resolve():reject(new UserError('필요한 구성 요소를 다운로드하지 못했습니다. 인터넷 연결이나 접근 권한을 확인한 뒤 다시 요청해주세요.')));
  });
  if((await dependencyProblems(root)).length||!importsReady())throw new UserError('구성 요소 설치가 완전히 끝나지 않았습니다. Codex에서 설치 기록을 확인해주세요.');
  prepareMediaTools(root);
}
