import {execFileSync} from 'node:child_process';
export const SAMPLE_RATE=32000;
export const FFT_SIZE=4096;
export const BAR_COUNT=60;
export const ANALYSIS_FPS=30;
// Hann-windowed radix-2 FFT. Power is averaged across channels, avoiding
// cancellation when a stereo recording has opposite-phase left/right samples.
function powerSpectrum(samples,center,channel,channels) {
  const n=FFT_SIZE,re=new Float64Array(n),im=new Float64Array(n);
  let windowSum=0;
  for(let i=0;i<n;i++) {
    const window=.5-.5*Math.cos(2*Math.PI*i/(n-1));windowSum+=window;
    const index=center+i-n/2;
    re[i]=index>=0 && index*channels+channel<samples.length ? samples[index*channels+channel]*window : 0;
  }
  for(let i=1,j=0;i<n;i++) {let bit=n>>1;for(;j&bit;bit>>=1)j^=bit;j^=bit;if(i<j)[re[i],re[j]]=[re[j],re[i]];}
  for(let size=2;size<=n;size*=2) {
    const angle=-2*Math.PI/size,stepR=Math.cos(angle),stepI=Math.sin(angle);
    for(let start=0;start<n;start+=size) {
      let wr=1,wi=0;
      for(let j=0;j<size/2;j++) {
        const a=start+j,b=a+size/2,tr=wr*re[b]-wi*im[b],ti=wr*im[b]+wi*re[b];
        re[b]=re[a]-tr;im[b]=im[a]-ti;re[a]+=tr;im[a]+=ti;
        const next=wr*stepR-wi*stepI;wi=wr*stepI+wi*stepR;wr=next;
      }
    }
  }
  return Array.from({length:n/2+1},(_,i)=>(re[i]**2+im[i]**2)*(2/windowSum)**2);
}
export const frequencies=Array.from({length:BAR_COUNT},(_,i)=>45*(14000/45)**(i/(BAR_COUNT-1)));
const ratio=frequencies[1]/frequencies[0];
const filters=frequencies.map(f=>{
  const lo=f/ratio,hi=f*ratio,weights=[];
  for(let k=Math.floor(lo*FFT_SIZE/SAMPLE_RATE);k<=Math.ceil(hi*FFT_SIZE/SAMPLE_RATE);k++) {
    const hz=k*SAMPLE_RATE/FFT_SIZE;
    const weight=Math.max(0,hz<f?(hz-lo)/(f-lo):(hi-hz)/(hi-f));
    if(weight>0)weights.push([k,weight]);
  }
  // Very low narrow bands can fall between FFT bins; interpolate those bins.
  if(!weights.length){const bin=f*FFT_SIZE/SAMPLE_RATE,k=Math.floor(bin);return [[k,1-(bin-k)],[k+1,bin-k]];}
  return weights;
});
export function analyzePcm(samples,{channels=2,duration=samples.length/channels/SAMPLE_RATE}={}) {
  if(!Number.isFinite(duration)||duration<=0||!Number.isInteger(channels)||channels<1)throw new Error('오디오 분석 입력을 확인해주세요.');
  const previous=new Float64Array(BAR_COUNT),frames=[];
  for(let frame=0;frame<Math.ceil(duration*ANALYSIS_FPS);frame++) {
    const center=Math.round(frame*SAMPLE_RATE/ANALYSIS_FPS);
    const powers=Array.from({length:channels},(_,c)=>powerSpectrum(samples,center,c,channels));
    frames.push(filters.map((filter,index)=>{
      let power=0,total=0;
      for(const [bin,weight] of filter){for(const p of powers)power+=p[bin]*weight/channels;total+=weight;}
      const db=10*Math.log10(Math.max(1e-14,power/total));
      // Fixed dB scale: quiet passages stay quiet (no per-frame normalization).
      const target=Math.min(1,Math.max(0,(db+66)/54))**1.6;
      const tau = target > previous[index] ? 0.08 : 0.22;
      const alpha=1-Math.exp(-1/(ANALYSIS_FPS*tau));
      previous[index]+=alpha*(target-previous[index]);
      return Math.round(previous[index]*10000)/10000;
    }));
  }
  return {version:1,fps:ANALYSIS_FPS,barCount:BAR_COUNT,duration,frequencies,frames};
}
export function analyzeAudio(file,duration) {
  const buffer=execFileSync('ffmpeg',['-v','error','-i',file,'-map','0:a:0','-vn','-ac','2','-ar',String(SAMPLE_RATE),'-f','f32le','pipe:1'],{maxBuffer:512*1024*1024});
  const samples=new Float32Array(buffer.length/4);
  for(let i=0;i<samples.length;i++)samples[i]=buffer.readFloatLE(i*4);
  return analyzePcm(samples,{channels:2,duration});
}
