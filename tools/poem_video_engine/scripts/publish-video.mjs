import {mkdir,lstat,copyFile,rename} from 'node:fs/promises';
import {constants} from 'node:fs';
import path from 'node:path';
import {UserError} from './workflow.mjs';
export async function publishVideo(temporary,output,backupFolder){
  await mkdir(path.dirname(output),{recursive:true});
  let previous;
  try{previous=await lstat(output);}catch(error){if(error.code!=='ENOENT')throw error;}
  if(previous){
    if(!previous.isFile())throw new UserError('같은 이름의 출력 경로가 일반 파일이 아닙니다. output 폴더의 해당 경로를 확인해주세요.');
    await mkdir(backupFolder,{recursive:true});
    await copyFile(output,path.join(backupFolder,path.basename(output)),constants.COPYFILE_EXCL);
  }
  await rename(temporary,output);
  return previous?backupFolder:null;
}
