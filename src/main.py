import os
import time
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import List
import whisper
from pathlib import Path
import traceback

# クリップ動画の長さ設定
CLIP_MIN_MINUTE = 1
CLIP_MAX_MINUTE = 3

@dataclass
class Clip:
    start_time: float
    end_time: float

class Transcriber:
    def __init__(self):
        self.model = whisper.load_model("large-v3", device="cuda")

    def transcribe_to_srt(self, audio_path: str, output_path: str) -> bool:
        try:
            print(f"🎙️ Transcribing {audio_path} ...")
            result = self.model.transcribe(audio_path, language="ja", task="transcribe")

            if not any(segment["text"].strip() for segment in result["segments"]):
                print(f"🤫 Skipping transcription (silent audio): {audio_path}")
                return False

            with open(output_path, "w", encoding="utf-8") as f:
                for i, segment in enumerate(result["segments"]):
                    start = self.format_timestamp(segment["start"])
                    end = self.format_timestamp(segment["end"])
                    f.write(f"{i + 1}\n{start} --> {end}\n{segment['text'].strip()}\n\n")

            print(f"📝 Saved subtitle: {output_path}")
            return True
        except Exception as e:
            print(f"⚠️ Error transcribing {audio_path}: {e}")
            return False

    def format_timestamp(self, seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 1000)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"

class ClipFinder:
    def __init__(self, min_length, max_length):
        self.min_length = min_length
        self.max_length = max_length

    def find_clips(self, video_path: str) -> List[Clip]:
        clips: List[Clip] = []
        duration = get_video_duration(video_path)

        current = 0.0
        while current < duration:
            remaining = duration - current
            if remaining < self.min_length:
                break
            length = min(self.max_length, remaining)
            clips.append(Clip(start_time=current, end_time=current + length))
            current += length
        return clips

def get_video_duration(video_path: str) -> float:
    result = subprocess.run([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "format=duration", "-of", "json", video_path
    ], capture_output=True, text=True, check=True)
    info = json.loads(result.stdout)
    return float(info["format"]["duration"])

def export_clip(i: int, clip_info: Clip, video_path: str, output_dir: str, transcriber: Transcriber):
    try:
        print(f"🎞️ Exporting clip {i}: {clip_info.start_time:.2f} - {clip_info.end_time:.2f}")
        clip_path = Path(output_dir) / f"clip_{i}.mp4"
        subtitled_path = Path(output_dir) / f"clip_{i}_subtitled.mp4"
        srt_path = Path(output_dir) / f"clip_{i}.srt"

        # FFmpegで切り抜き＋GPUエンコード
        subprocess.run([
            "ffmpeg", "-y",
            "-ss", str(clip_info.start_time),
            "-to", str(clip_info.end_time),
            "-i", str(video_path),
            "-c:v", "h264_nvenc",
            "-c:a", "aac",
            str(clip_path)
        ], check=True)

        if not clip_path.exists() or clip_path.stat().st_size < 1024:
            print(f"⚠️ Exported file is missing or too small: {clip_path}")
            return

        # 字幕生成
        has_transcription = transcriber.transcribe_to_srt(str(clip_path), str(srt_path))

        if not has_transcription:
            os.remove(clip_path)
            print(f"🗑️ Removed silent clip {clip_path}")
            return

        if not srt_path.exists():
            print(f"⚠️ Subtitle file missing: {srt_path}")
            return

        # 字幕付き動画を作成
        subtitle_path = escape_ffmpeg_path(srt_path)
        subtitle_filter = f"subtitles='{subtitle_path}'"

        result = subprocess.run([
            "ffmpeg", "-y", "-i", str(clip_path),
            "-vf", subtitle_filter,
            "-c:v", "h264_nvenc",
            "-c:a", "copy",
            str(subtitled_path)
        ], check=True)

        
        if result.returncode != 0:
            print(f"❌ FFmpeg subtitle filter failed for clip {i}")
            print(result.stderr)
        else:
            print(f"✅ Exported subtitled clip {i} to {subtitled_path}")
    except subprocess.TimeoutExpired:
        print(f"⏰ FFmpeg timed out on clip {i}")
    except Exception as e:
        print(f"❌ Failed to export clip {i}: {e}")
        traceback.print_exc()

def escape_ffmpeg_path(path: str) -> str:
    # Windowsでffmpegに渡すパスのエスケープ（特に冒頭の C: 対策）
    path = Path(path).as_posix()
    if ":" in path:
        drive, rest = path.split(":/", 1)
        path = f"{drive}\\:/{rest}"
    return path

def main():
    start_time = time.time()

    video_path = "C:/Vigston/StreamClips/VigslibStreamClip/res/sample_video.mp4"
    output_dir = "C:/Vigston/StreamClips/VigslibStreamClip/clip"
    os.makedirs(output_dir, exist_ok=True)

    transcriber = Transcriber()
    clip_finder = ClipFinder(CLIP_MIN_MINUTE*60, CLIP_MAX_MINUTE*60)

    clips = clip_finder.find_clips(video_path)
    print(f"🎬 Found {len(clips)} clips.")

    max_workers = 1

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(export_clip, i, clip, video_path, output_dir, transcriber)
            for i, clip in enumerate(clips)
        ]
        for f in futures:
            f.result()

    end_time = time.time()
    print(f"⏱️ Total processing time: {end_time - start_time:.2f} seconds")

if __name__ == "__main__":
    main()