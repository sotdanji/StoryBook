import React, {useEffect, useState, useMemo} from 'react';
import {AbsoluteFill, Html5Audio, Img, staticFile, useCurrentFrame, useVideoConfig, delayRender, continueRender, cancelRender} from 'remotion';
import {AudioVisualizer} from './AudioVisualizer';
import type {Cue, VideoProps, AspectRatio} from './types';
import {playbackMotion} from './motion.mjs';

const font = "'Nanum Myeongjo', 'Gowun Batang', 'Batang', PretendardVariable, serif";
const clock = (s: number) => `${Math.floor(s / 60).toString().padStart(2, '0')}:${Math.floor(s % 60).toString().padStart(2, '0')}`;
const fitCache = new Map<string, number>();

function fit(text: string, max: number, width: number, height: number) {
  const key = JSON.stringify([text, max, width, height]);
  if (fitCache.has(key)) return fitCache.get(key)!;
  const measure = document.createElement('div');
  Object.assign(measure.style, {
    position: 'absolute',
    visibility: 'hidden',
    width: `${width}px`,
    fontFamily: font,
    fontWeight: '800',
    lineHeight: '1.2',
    whiteSpace: 'pre-wrap',
    overflowWrap: 'anywhere'
  });
  measure.textContent = text;
  document.body.appendChild(measure);
  try {
    for (let size = max; size >= 18; size--) {
      measure.style.fontSize = `${size}px`;
      if (measure.getBoundingClientRect().height <= height) {
        fitCache.set(key, size);
        return size;
      }
    }
    return 26;
  } finally {
    measure.remove();
  }
}

/**
 * [StoryBook Studio] 갤러리 일체형 서정 수직 롤링(Gallery Aesthetic Roll-Up) 자막 컴포넌트
 * - 16:9(가로) 및 9:16(세로 쇼츠) 동적 레이아웃 지원
 * - 부드러운 코사인 감속 스크롤로 현재 발화 구절이 화면 중앙 골든존을 우아하게 통과
 */
function PoeticRollLyrics({
  cues,
  time,
  duration,
  aspectRatio = '16:9'
}: {
  cues: Cue[];
  time: number;
  duration: number;
  aspectRatio?: AspectRatio;
}) {
  const isShorts = aspectRatio === '9:16';
  const containerWidth = isShorts ? 960 : 1030;
  const containerHeight = isShorts ? 560 : 980;
  const leftPos = isShorts ? 60 : 810;
  const topPos = isShorts ? 1080 : 50;
  const centerY = containerHeight / 2;
  const lineSpacing = isShorts ? 82 : 90;

  const cueMidtimes = useMemo(() => {
    if (!cues || cues.length === 0) return [];
    return cues.map((c) => (c.start + c.end) / 2);
  }, [cues]);

  const scrollY = useMemo(() => {
    if (!cues || cues.length === 0) return centerY;
    const n = cues.length;
    if (n === 1) return centerY;

    const firstTime = cueMidtimes[0];
    const lastTime = cueMidtimes[n - 1];

    if (time <= firstTime) return centerY;
    if (time >= lastTime) return centerY - (n - 1) * lineSpacing;

    let idx = 0;
    while (idx < n - 1 && cueMidtimes[idx + 1] < time) {
      idx++;
    }

    const t0 = cueMidtimes[idx];
    const t1 = cueMidtimes[idx + 1];
    const dt = Math.max(0.001, t1 - t0);
    const progress = Math.min(1, Math.max(0, (time - t0) / dt));

    const smoothProgress = 0.5 - 0.5 * Math.cos(progress * Math.PI);
    const y0 = centerY - idx * lineSpacing;
    const y1 = centerY - (idx + 1) * lineSpacing;

    return y0 + (y1 - y0) * smoothProgress;
  }, [cues, cueMidtimes, time, centerY, lineSpacing]);

  return (
    <div
      style={{
        position: 'absolute',
        left: leftPos,
        top: topPos,
        width: containerWidth,
        height: containerHeight,
        overflow: 'hidden',
        maskImage: 'linear-gradient(to bottom, transparent 0%, black 16%, black 84%, transparent 100%)',
        WebkitMaskImage: 'linear-gradient(to bottom, transparent 0%, black 16%, black 84%, transparent 100%)',
      }}
    >
      <div
        style={{
          position: 'absolute',
          top: scrollY,
          width: '100%',
        }}
      >
        {cues.map((cue, index) => {
          const itemY = scrollY + index * lineSpacing;
          const distFromCenter = Math.abs(itemY - centerY);

          let opacity = 0.35;
          let fontSize = isShorts ? 34 : 38;
          let fontWeight = 400;
          let scale = 0.98;
          let color = 'rgba(247, 245, 240, 0.55)';
          let shadow = '0 2px 6px rgba(0, 0, 0, 0.7)';

          if (distFromCenter < 52) {
            const factor = 1 - (distFromCenter / 52);
            opacity = 0.96 + 0.04 * factor;
            fontSize = isShorts ? 40 : 44;
            fontWeight = 700;
            scale = 1.0 + 0.03 * factor;
            color = '#FFF9F2';
            shadow = '0 0 24px rgba(212, 175, 55, 0.45), 0 3px 14px rgba(0, 0, 0, 0.9)';
          } else if (distFromCenter < 140) {
            opacity = 0.70;
            fontSize = isShorts ? 36 : 40;
            color = 'rgba(247, 245, 240, 0.78)';
            fontWeight = 500;
            scale = 1.0;
            shadow = '0 2px 10px rgba(0, 0, 0, 0.8)';
          }

          return (
            <div
              key={index}
              style={{
                height: lineSpacing,
                display: 'flex',
                alignItems: 'center',
                justifyContent: isShorts ? 'center' : 'flex-start',
                textAlign: isShorts ? 'center' : 'left',
                fontSize,
                lineHeight: 1.45,
                fontWeight,
                color,
                textShadow: shadow,
                transform: `scale(${scale})`,
                transformOrigin: isShorts ? 'center center' : 'left center',
                whiteSpace: 'pre',
                letterSpacing: '-0.02em',
                fontFamily: font,
                transition: 'font-size 0.2s ease, opacity 0.2s ease',
              }}
            >
              {cue.text}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/**
 * [StoryBook Studio] 리릭비 스타일 2줄 포커스(Focus 2-Line) 가사 컴포넌트
 * - 노래/뮤직비디오 특화: 현재 부르는 행(대형 하이라이트) + 다음 행(미리보기)
 */
function Focus2LineLyrics({
  cues,
  time,
  aspectRatio = '16:9'
}: {
  cues: Cue[];
  time: number;
  aspectRatio?: AspectRatio;
}) {
  const isShorts = aspectRatio === '9:16';

  const currentIdx = cues.findIndex((c) => time >= c.start && time <= c.end);
  const currentCue = currentIdx !== -1 ? cues[currentIdx] : null;
  const nextCue = currentIdx !== -1 && currentIdx + 1 < cues.length ? cues[currentIdx + 1] : null;

  let displayLine1 = currentCue ? currentCue.text : (cues.find((c) => c.start > time)?.text || '');
  let displayLine2 = currentCue ? (nextCue ? nextCue.text : '') : '';

  const containerStyle: React.CSSProperties = isShorts
    ? {
        position: 'absolute',
        left: 60,
        top: 1100,
        width: 960,
        height: 520,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        textAlign: 'center',
        gap: 36,
      }
    : {
        position: 'absolute',
        left: 810,
        top: 120,
        width: 1030,
        height: 820,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'flex-start',
        gap: 44,
      };

  return (
    <div style={containerStyle}>
      {/* 1행: 현재 활성 가사 */}
      <div
        style={{
          fontSize: isShorts ? 42 : 48,
          fontWeight: 800,
          lineHeight: 1.35,
          color: '#FFF9F2',
          textShadow: '0 0 28px rgba(212, 175, 55, 0.65), 0 3px 14px rgba(0, 0, 0, 0.95)',
          fontFamily: font,
          letterSpacing: '-0.02em',
          minHeight: isShorts ? 64 : 72,
          transition: 'all 0.25s ease',
        }}
      >
        {displayLine1 || '♪ ♫'}
      </div>

      {/* 2행: 다음 가사 미리보기 */}
      <div
        style={{
          fontSize: isShorts ? 32 : 36,
          fontWeight: 500,
          lineHeight: 1.35,
          color: 'rgba(247, 245, 240, 0.45)',
          textShadow: '0 2px 8px rgba(0, 0, 0, 0.8)',
          fontFamily: font,
          letterSpacing: '-0.015em',
          minHeight: isShorts ? 46 : 52,
          transition: 'all 0.25s ease',
        }}
      >
        {displayLine2}
      </div>
    </div>
  );
}

export function LyricVideo({
  title,
  audio,
  cover,
  duration,
  cues,
  spectrum,
  aspectRatio = '16:9',
  spectrumStyle = 'bar',
  videoType = 'poem',
  lyricMode = 'rolling'
}: VideoProps) {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const motion = playbackMotion(frame, fps, duration);
  const time = motion.time;

  const [handle] = useState(() => delayRender('글꼴 로딩'));
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const face = new FontFace('MusicStep', `url(${staticFile('assets/PretendardVariable.woff2')})`, {weight: '100 900'});
    face.load().then((f) => {
      document.fonts.add(f);
      setReady(true);
      continueRender(handle);
    }).catch(cancelRender);
  }, [handle]);

  if (!ready) return null;

  const image = staticFile(cover);
  const isShorts = aspectRatio === '9:16';
  const isSong = videoType === 'song';

  const badgeText = isSong
    ? (isShorts ? '🎵 서정 노래 쇼츠' : '🎵 서정 노래 뮤직비디오')
    : (isShorts ? '📖 시화집 낭송 쇼츠' : '📖 시화집 낭송 갤러리');

  // 삽화 켄 번스(Ken Burns) 살아있는 서정 애니메이션
  const progressRatio = duration > 0 ? (time / duration) : 0;
  const kenBurnsScale = 1.05 + 0.11 * Math.sin(progressRatio * Math.PI);
  const kenBurnsPanX = 15 * Math.sin(progressRatio * Math.PI * 2);
  const kenBurnsPanY = 8 * Math.cos(progressRatio * Math.PI * 1.5);

  // ==========================================
  // 📱 [템플릿 1] 9:16 세로형 쇼츠/릴스 레이아웃 (1080 x 1920)
  // ==========================================
  if (isShorts) {
    return (
      <AbsoluteFill style={{fontFamily: font, background: '#14100E', color: '#FAF6F0'}}>
        <Html5Audio src={staticFile(audio)} />

        <Img
          src={image}
          style={{
            position: 'absolute',
            width: '120%',
            height: '120%',
            left: '-10%',
            top: '-10%',
            objectFit: 'cover',
            filter: 'blur(36px) brightness(.32) sepia(.2) saturate(.9)',
            transform: `translate(${motion.panX}px, ${motion.panY}px) scale(${motion.scale})`,
          }}
        />
        <AbsoluteFill style={{background: 'linear-gradient(180deg, rgba(16,12,10,0.88) 0%, rgba(20,15,12,0.65) 50%, rgba(14,10,8,0.92) 100%)'}} />

        {/* 상단 헤더: 배지 및 타이틀 */}
        <div
          style={{
            position: 'absolute',
            left: 60,
            top: 70,
            width: 960,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 10,
            zIndex: 10,
          }}
        >
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              background: isSong ? 'rgba(80, 140, 220, 0.22)' : 'rgba(197, 155, 39, 0.20)',
              border: `1px solid ${isSong ? 'rgba(110, 170, 255, 0.55)' : 'rgba(197, 155, 39, 0.50)'}`,
              borderRadius: 20,
              padding: '4px 14px',
              fontSize: 16,
              fontWeight: 700,
              color: isSong ? '#8BC0FF' : '#D4AF37',
              letterSpacing: '0.04em',
            }}
          >
            {badgeText}
          </div>

          <div
            style={{
              fontSize: fit(title, 46, 960, 56),
              lineHeight: 1.25,
              fontWeight: 800,
              letterSpacing: '-0.025em',
              color: '#FAF6F0',
              fontFamily: font,
              textAlign: 'center',
              textShadow: '0 2px 14px rgba(0,0,0,0.85)',
            }}
          >
            {title}
          </div>
        </div>

        {/* 중앙 상단: 메인 삽화 카드 */}
        <div
          style={{
            position: 'absolute',
            left: 60,
            top: 185,
            width: 960,
            height: 870,
            borderRadius: 24,
            overflow: 'hidden',
            border: '2px solid rgba(212, 175, 55, 0.45)',
            boxShadow: '0 30px 80px rgba(0, 0, 0, 0.85), 0 8px 24px rgba(0, 0, 0, 0.6)',
            background: '#0e0b09',
          }}
        >
          <Img
            src={image}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              transform: `scale(${kenBurnsScale}) translate(${kenBurnsPanX}px, ${kenBurnsPanY}px)`,
            }}
          />
        </div>

        {/* 중앙 하단: 가사 자막 (2줄 포커스 or 서정 롤링) */}
        {lyricMode === 'focus2line' ? (
          <Focus2LineLyrics cues={cues} time={time} aspectRatio="9:16" />
        ) : (
          <PoeticRollLyrics cues={cues} time={time} duration={duration} aspectRatio="9:16" />
        )}

        {/* 음원 오디오 스펙트럼 비주얼라이저 */}
        <AudioVisualizer
          spectrum={spectrum}
          time={time}
          styleType={spectrumStyle}
          left={60}
          top={1680}
          width={960}
          height={55}
        />

        {/* 하단 재생 진행 바 */}
        <div
          style={{
            position: 'absolute',
            left: 60,
            top: 1765,
            width: 960,
            height: 8,
            borderRadius: 8,
            background: 'rgba(255,255,255,0.22)',
          }}
        >
          <div
            style={{
              width: `${motion.progress * 100}%`,
              height: 8,
              borderRadius: 8,
              background: isSong
                ? 'linear-gradient(90deg, #4A709C 0%, #D4AF37 100%)'
                : 'linear-gradient(90deg, #9E6B55 0%, #C59B27 100%)',
            }}
          />
          <div
            style={{
              position: 'absolute',
              left: `${motion.progress * 100}%`,
              top: -6,
              width: 20,
              height: 20,
              borderRadius: '50%',
              background: '#FFF',
              boxShadow: `0 0 14px ${isSong ? '#8BC0FF' : '#C59B27'}`,
            }}
          />
        </div>

        {/* 시간 표시 */}
        <div
          style={{
            position: 'absolute',
            left: 60,
            top: 1790,
            width: 960,
            display: 'flex',
            justifyContent: 'space-between',
            fontSize: 22,
            color: 'rgba(247,245,240,0.72)',
          }}
        >
          <span>{clock(time)}</span>
          <span>{clock(duration)}</span>
        </div>
      </AbsoluteFill>
    );
  }

  // ==========================================
  // 🖥️ [템플릿 2] 16:9 와이드 가로형 갤러리 레이아웃 (1920 x 1080)
  // ==========================================
  return (
    <AbsoluteFill style={{fontFamily: font, background: '#181412', color: '#FAF6F0'}}>
      <Html5Audio src={staticFile(audio)} />

      <Img
        src={image}
        style={{
          position: 'absolute',
          width: '108%',
          height: '108%',
          left: '-4%',
          top: '-4%',
          objectFit: 'cover',
          filter: 'blur(30px) brightness(.38) sepia(.2) saturate(.9)',
          transform: `translate(${motion.panX}px, ${motion.panY}px) scale(${motion.scale})`,
        }}
      />
      <AbsoluteFill style={{background: 'linear-gradient(0deg,rgba(22,17,14,.90),transparent 65%),radial-gradient(ellipse at center,transparent 25%,#120e0c99)'}} />

      {/* 좌측 대형 메인 삽화 카드 */}
      <div
        style={{
          position: 'absolute',
          left: 80,
          top: 50,
          width: 680,
          height: 690,
          borderRadius: 24,
          overflow: 'hidden',
          border: '1.5px solid rgba(212, 175, 55, 0.38)',
          boxShadow: '0 28px 70px rgba(0, 0, 0, 0.75), 0 6px 20px rgba(0, 0, 0, 0.5)',
          background: '#0e0b09',
        }}
      >
        <Img
          src={image}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            transform: `scale(${kenBurnsScale}) translate(${kenBurnsPanX}px, ${kenBurnsPanY}px)`,
          }}
        />
      </div>

      {/* 정보 헤더 */}
      <div
        style={{
          position: 'absolute',
          left: 80,
          top: 760,
          width: 680,
          display: 'flex',
          flexDirection: 'column',
          gap: 6,
        }}
      >
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            alignSelf: 'flex-start',
            background: isSong ? 'rgba(80, 140, 220, 0.20)' : 'rgba(197, 155, 39, 0.16)',
            border: `1px solid ${isSong ? 'rgba(110, 170, 255, 0.50)' : 'rgba(197, 155, 39, 0.42)'}`,
            borderRadius: 6,
            padding: '3px 10px',
            fontSize: 14,
            fontWeight: 700,
            color: isSong ? '#8BC0FF' : '#D4AF37',
            letterSpacing: '0.04em',
          }}
        >
          {badgeText}
        </div>

        <div
          style={{
            fontSize: fit(title, 46, 680, 56),
            lineHeight: 1.2,
            fontWeight: 800,
            letterSpacing: '-0.025em',
            color: '#FAF6F0',
            fontFamily: font,
            textShadow: '0 2px 14px rgba(0,0,0,0.85)',
          }}
        >
          {title}
        </div>
      </div>

      {/* 음원 오디오 스펙트럼 비주얼라이저 */}
      <AudioVisualizer
        spectrum={spectrum}
        time={time}
        styleType={spectrumStyle}
        left={80}
        top={865}
        width={680}
        height={60}
      />

      {/* 재생 진행 바 */}
      <div
        style={{
          position: 'absolute',
          left: 80,
          top: 945,
          width: 680,
          height: 8,
          borderRadius: 8,
          background: 'rgba(255,255,255,0.22)',
        }}
      >
        <div
          style={{
            width: `${motion.progress * 100}%`,
            height: 8,
            borderRadius: 8,
            background: isSong
              ? 'linear-gradient(90deg, #4A709C 0%, #D4AF37 100%)'
              : 'linear-gradient(90deg, #9E6B55 0%, #C59B27 100%)',
          }}
        />
        <div
          style={{
            position: 'absolute',
            left: `${motion.progress * 100}%`,
            top: -6,
            width: 20,
            height: 20,
            borderRadius: '50%',
            background: '#FFF',
            boxShadow: `0 0 14px ${isSong ? '#8BC0FF' : '#C59B27'}`,
          }}
        />
      </div>

      {/* 시간 표시 */}
      <div
        style={{
          position: 'absolute',
          left: 80,
          top: 968,
          width: 680,
          display: 'flex',
          justifyContent: 'space-between',
          fontSize: 22,
          color: 'rgba(247,245,240,0.72)',
        }}
      >
        <span>{clock(time)}</span>
        <span>{clock(duration)}</span>
      </div>

      {/* 우측 가사 자막 (2줄 포커스 or 서정 롤링) */}
      {lyricMode === 'focus2line' ? (
        <Focus2LineLyrics cues={cues} time={time} aspectRatio="16:9" />
      ) : (
        <PoeticRollLyrics cues={cues} time={time} duration={duration} aspectRatio="16:9" />
      )}
    </AbsoluteFill>
  );
}
