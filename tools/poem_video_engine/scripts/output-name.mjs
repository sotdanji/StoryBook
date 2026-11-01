import {createHash} from 'node:crypto';
// Keep normal Korean/English/space names; make other names valid on Windows too.
export function outputName(title){
  let safe=title.normalize('NFC').replace(/[<>:"/\\|?*\u0000-\u001f]/g,'_').replace(/[. ]+$/g,'');
  if(!safe)safe='MusicStep';
  if(Buffer.byteLength(safe,'utf8')>180){const suffix=createHash('sha256').update(title).digest('hex').slice(0,8);let prefix='';for(const char of safe){if(Buffer.byteLength(prefix+char,'utf8')>160)break;prefix+=char;}safe=prefix+'_'+suffix;}
  return `${safe}_lyric-video.mp4`;
}
