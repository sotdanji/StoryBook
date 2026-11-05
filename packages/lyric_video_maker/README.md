# 🎬 `lyric_video_maker` (AI 오디오 마스터링 & 리릭 비디오 엔진)

음원 앞뒤 무음 자동 감지·트리밍(320kbps MP3 마스터링), Whisper 기반 가사/낭송 타임스탬프 동기화, Remotion/FFmpeg 시네마틱 비디오 렌더링을 수행하는 독립 패키지입니다.

## 🚀 다른 프로젝트에서 바로 사용하기

```python
from pathlib import Path
from packages.lyric_video_maker import LyricVideoMaker

maker = LyricVideoMaker()

# 1. 오디오 앞뒤 무음 자동 제거 및 페이드 인/아웃 마스터링
res = maker.master_audio(Path("raw_vocal.wav"), Path("mastered.mp3"))
print(res["final_duration_str"])

# 2. 원하는 구간(초 단위) 수동 트리밍
maker.trim_audio(Path("mastered.mp3"), start_sec=1.5, end_sec=120.0)
```
