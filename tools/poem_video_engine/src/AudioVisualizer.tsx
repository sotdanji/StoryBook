import React, {useEffect, useState} from 'react';
import {cancelRender, continueRender, delayRender, staticFile} from 'remotion';
import type {SpectrumStyle} from './types';

type Spectrum = {
  version: number;
  fps: number;
  barCount: number;
  duration: number;
  frames: number[][];
};

interface VisualizerProps {
  spectrum: string;
  time: number;
  styleType?: SpectrumStyle;
  left?: number;
  top?: number;
  width?: number;
  height?: number;
}

export function AudioVisualizer({
  spectrum,
  time,
  styleType = 'bar',
  left = 80,
  top = 865,
  width = 680,
  height = 60,
}: VisualizerProps) {
  const [handle] = useState(() => delayRender('음원 주파수 데이터 로딩'));
  const [data, setData] = useState<Spectrum | null>(null);

  useEffect(() => {
    if (styleType === 'off') return;
    let cancelled = false;
    fetch(staticFile(spectrum))
      .then((response) => {
        if (!response.ok) throw new Error('음원 분석 파일을 찾을 수 없습니다.');
        return response.json();
      })
      .then((value: Spectrum) => {
        if (
          value.version !== 1 ||
          value.barCount !== 60 ||
          value.fps !== 30 ||
          !Array.isArray(value.frames) ||
          !value.frames.length
        ) {
          throw new Error('음원 분석 데이터가 올바르지 않습니다.');
        }
        if (!cancelled) {
          setData(value);
          continueRender(handle);
        }
      })
      .catch((error) => {
        if (!cancelled) cancelRender(error);
      });
    return () => {
      cancelled = true;
    };
  }, [spectrum, handle, styleType]);

  if (styleType === 'off') {
    return null;
  }

  if (!data) return null;

  const position = Math.min(data.frames.length - 1, Math.max(0, time * data.fps));
  const lower = Math.floor(position);
  const upper = Math.min(data.frames.length - 1, lower + 1);
  const fraction = position - lower;

  const barCount = 60;
  const barWidth = Math.max(2, (width / barCount) * 0.72);
  const barGap = (width - barWidth * barCount) / Math.max(1, barCount - 1);

  // 1. 중앙 대칭 미러형 (Mirror Spectrum)
  if (styleType === 'mirror') {
    const halfH = height / 2;
    return (
      <div
        style={{
          position: 'absolute',
          left,
          top,
          width,
          height,
          display: 'flex',
          alignItems: 'center',
          gap: barGap,
        }}
      >
        {Array.from({length: barCount}, (_, i) => {
          const energy = data.frames[lower][i] * (1 - fraction) + data.frames[upper][i] * fraction;
          const barH = Math.max(4, halfH * 1.8 * energy);
          const isGold = i < 22;
          return (
            <div
              key={i}
              style={{
                width: barWidth,
                height: barH,
                borderRadius: barWidth / 2,
                background: isGold
                  ? 'linear-gradient(180deg, #E6CA65 0%, #C59B27 50%, #9E6B55 100%)'
                  : 'linear-gradient(180deg, rgba(255,255,255,0.95) 0%, rgba(220,215,205,0.85) 100%)',
                boxShadow: isGold ? '0 0 10px rgba(197, 155, 39, 0.45)' : undefined,
                opacity: 0.9,
              }}
            />
          );
        })}
      </div>
    );
  }

  // 2. 부드러운 웨이브형 (Smooth Waveform)
  if (styleType === 'wave') {
    return (
      <div
        style={{
          position: 'absolute',
          left,
          top,
          width,
          height,
          display: 'flex',
          alignItems: 'end',
          gap: barGap,
        }}
      >
        {Array.from({length: barCount}, (_, i) => {
          const energy = data.frames[lower][i] * (1 - fraction) + data.frames[upper][i] * fraction;
          const barH = 5 + (height - 8) * Math.sin(energy * Math.PI * 0.5);
          const isGold = i < 24;
          return (
            <div
              key={i}
              style={{
                width: barWidth,
                height: barH,
                borderRadius: '4px 4px 1px 1px',
                background: isGold
                  ? 'linear-gradient(0deg, #9E6B55 0%, #D4AF37 100%)'
                  : 'linear-gradient(0deg, rgba(180,170,160,0.6) 0%, rgba(255,255,255,0.9) 100%)',
                boxShadow: isGold ? '0 0 12px rgba(212, 175, 55, 0.5)' : undefined,
              }}
            />
          );
        })}
      </div>
    );
  }

  // 3. 기본 바 스타일 (Standard Bottom-Up Bar)
  return (
    <div
      style={{
        position: 'absolute',
        left,
        top,
        width,
        height,
        display: 'flex',
        alignItems: 'end',
        gap: barGap,
      }}
    >
      {Array.from({length: barCount}, (_, i) => {
        const energy = data.frames[lower][i] * (1 - fraction) + data.frames[upper][i] * fraction;
        const isGold = i < 18;
        return (
          <div
            key={i}
            style={{
              width: barWidth,
              height: 6 + (height - 8) * energy,
              borderRadius: 2,
              background: isGold ? '#C59B27' : 'rgba(255,255,255,0.85)',
              boxShadow: isGold ? '0 0 12px rgba(197,155,39,0.5)' : undefined,
            }}
          />
        );
      })}
    </div>
  );
}
