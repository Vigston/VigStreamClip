import os
import json
import subprocess
import whisper
from pathlib import Path
from dataclasses import dataclass
from typing import List

# 📁 ベースディレクトリ
BASE_DIR = Path(__file__).resolve().parent.parent
SEGMENT_DIR = BASE_DIR / "output" / "segments"
OUTPUT_BASE_DIR = BASE_DIR / "clip_output"

# ⏱️ クリップの長さ（秒）
MIN_DURATION = 60
MAX_DURATION = 180

# 🧠 Whisper モデル
model = whisper.load_model("large-v3", device="cuda")

@dataclass
class Clip:
    start_time: float
    end_time: float

def group_segments_by_duration(segments: List[dict], min_dur: int, max_dur: int) -> List[Clip]:
    clips = []
    current_start = None
    current_end = None

    for seg in segments:
        seg_start = seg["start"]
        seg_end = seg["end"]

        if current_start is None:
            current_start = seg_start
            current_end = seg_end
            continue

        duration = seg_end - current_start
        if duration < max_dur:
            current_end = seg_end
        else:
            if duration >= min_dur:
                clips.append(Clip(start_time=current_start, end_time=current_end))
            current_start = seg_start
            current_end = seg_end

    if current_start is not None and current_end - current_start >= min_dur:
        clips.append(Clip(start_time=current_start, end_time=current_end))

    return clips

def format_timestamp(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def escape_ffmpeg_path(path: Path) -> str:
    path = path.as_posix()
    if ":" in path:
        drive, rest = path.split(":/", 1)
        return f"{drive}\\:/{rest}"
    return path

def export_clip(index: int, clip: Clip, video_path: Path, output_dir: Path):
    clip_path = output_dir / f"clip_{index}.mp4"
    srt_path = output_dir / f"clip_{index}.srt"
    subtitled_path = output_dir / f"clip_{index}_subtitled.mp4"

    print(f"🎬 Exporting clip {index}: {clip.start_time:.1f} - {clip.end_time:.1f}")

    # 🎞️ 切り抜き
    subprocess.run([
        "ffmpeg", "-y",
        "-ss", str(clip.start_time),
        "-to", str(clip.end_time),
        "-i", str(video_path),
        "-c:v", "h264_nvenc",
        "-c:a", "aac",
        str(clip_path)
    ], check=True)

    # 📝 字幕生成
    result = model.transcribe(str(clip_path), language="ja", task="transcribe")
    if not any(seg["text"].strip() for seg in result["segments"]):
        clip_path.unlink(missing_ok=True)
        return

    with open(srt_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(result["segments"]):
            start = format_timestamp(seg["start"])
            end = format_timestamp(seg["end"])
            text = seg["text"].strip()
            f.write(f"{i+1}\n{start} --> {end}\n{text}\n\n")

    # 🎞️ 字幕焼き込み
    subtitle_filter = f"subtitles='{escape_ffmpeg_path(srt_path)}'"
    subprocess.run([
        "ffmpeg", "-y", "-i", str(clip_path),
        "-vf", subtitle_filter,
        "-c:v", "h264_nvenc",
        "-c:a", "copy",
        str(subtitled_path)
    ], check=True)

    print(f"✅ 完成: {subtitled_path.name}")

# 🧠 全セグメント動画を処理
for segment_file in SEGMENT_DIR.glob("segment_*.mp4"):
    try:
        print(f"\n==============================\n▶️ 処理開始: {segment_file.name}")
        result = model.transcribe(str(segment_file), language="ja", task="transcribe")
        segments = result["segments"]

        clips = group_segments_by_duration(segments, MIN_DURATION, MAX_DURATION)

        output_dir = OUTPUT_BASE_DIR / segment_file.stem
        output_dir.mkdir(parents=True, exist_ok=True)

        for i, clip in enumerate(clips):
            try:
                export_clip(i, clip, segment_file, output_dir)
            except Exception as e:
                print(f"❌ Clip {i} failed: {e}")

    except Exception as e:
        print(f"❌ {segment_file.name} の処理に失敗しました: {e}")