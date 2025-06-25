import os
import subprocess
import json
import re
from collections import defaultdict
import threading
import urllib.parse
import tkinter as tk
from tkinter import messagebox, filedialog
from pathlib import Path
from dataclasses import dataclass
from typing import List
import whisper
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from datetime import timedelta
import openai

plt.rcParams["font.family"] = "Yu Gothic"

BASE_DIR = Path(__file__).resolve().parent.parent
SEGMENT_DIR = BASE_DIR / "output" / "segments"
OUTPUT_BASE_DIR = BASE_DIR / "clip_output"
MIN_DURATION = 60
MAX_DURATION = 180
whisper_model = whisper.load_model("large-v3", device="cuda")

@dataclass
class Clip:
    start_time: float
    end_time: float

def load_api_key_from_file() -> str:
    # 現在のスクリプトの一つ上のディレクトリの assets/openai_key.txt を参照
    key_path = Path(__file__).resolve().parent.parent / "assets" / "openai_key.txt"
    with open(key_path, "r", encoding="utf-8") as f:
        return f.readline().strip()

def group_segments_by_duration(segments: List[dict], min_dur: int, max_dur: int) -> List[Clip]:
    clips = []

    # 最初のセグメントは必ず無視する（＝発話途中の可能性がある）
    i = 1
    while i < len(segments):
        current_start = segments[i]["start"]
        current_end = segments[i]["end"]
        i += 1

        while i < len(segments):
            duration = segments[i]["end"] - current_start
            if duration < max_dur:
                current_end = segments[i]["end"]
                i += 1
            else:
                break

        clip_duration = current_end - current_start
        if clip_duration >= min_dur:
            clips.append(Clip(start_time=current_start, end_time=current_end))

    return clips

def format_timestamp(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def call_gpt_proofread_segments(segments: List[dict]) -> List[dict]:
    """
    Whisperのsegmentsから校閲された字幕データ（段落単位）をChatGPT APIで取得
    戻り値は List[{start_index, end_index, text}]
    """
    print("🤖 ChatGPT に字幕校閲を依頼中...")

    raw_lines = [f"{i}: {seg['text']}" for i, seg in enumerate(segments)]
    full_text = "\n".join(raw_lines)

    prompt = (
        "以下は日本語の音声認識結果です（各行はインデックス付き）。\n"
        "誤字脱字を修正し、自然な段落にまとめ直してください。\n"
        "各段落には、元の発話インデックス範囲を `#start=3,end=7` のように付けてください。\n\n"
        + full_text
    )

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたは日本語音声認識結果を自然な文章に整えるプロ編集者です。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
    except Exception as e:
        print(f"❌ ChatGPT API エラー: {e}")
        raise

    print("✅ ChatGPT 校閲完了")

    content = response["choices"][0]["message"]["content"]

    # パース：#start=x,end=y のブロックとテキストを抽出
    import re
    blocks = re.split(r"#start=(\d+),end=(\d+)", content)
    parsed = []
    for i in range(1, len(blocks)-1, 3):
        start_idx = int(blocks[i])
        end_idx = int(blocks[i+1])
        text = blocks[i+2].strip()
        parsed.append({
            "start_index": start_idx,
            "end_index": end_idx,
            "text": text
        })
    return parsed

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

    # ① 動画を切り出し
    subprocess.run([
        "ffmpeg", "-y",
        "-ss", str(clip.start_time),
        "-to", str(clip.end_time),
        "-i", str(video_path),
        "-c:v", "h264_nvenc",
        "-c:a", "aac",
        str(clip_path)
    ], check=True)

    # ② Whisperで字幕セグメント取得
    result = whisper_model.transcribe(str(clip_path), language="ja", task="transcribe")
    segments = result["segments"]

    if not any(seg["text"].strip() for seg in segments):
        clip_path.unlink(missing_ok=True)
        return

    # ③ ChatGPTで誤字脱字＋段落整形
    gpt_segments = call_gpt_proofread_segments(segments)

    # ④ SRT出力（GPT整形済み）
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, item in enumerate(gpt_segments):
            start = format_timestamp(segments[item["start_index"]]["start"])
            end = format_timestamp(segments[item["end_index"]]["end"])
            f.write(f"{i+1}\n{start} --> {end}\n{item['text']}\n\n")

    # ⑤ 字幕を焼き込み
    subtitle_filter = f"subtitles='{escape_ffmpeg_path(srt_path)}'"
    subprocess.run([
        "ffmpeg", "-y", "-i", str(clip_path),
        "-vf", subtitle_filter,
        "-c:v", "h264_nvenc",
        "-c:a", "copy",
        str(subtitled_path)
    ], check=True)

def normalize_youtube_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query)
    query.pop("t", None)
    new_query = urllib.parse.urlencode(query, doseq=True)
    return urllib.parse.urlunparse(parsed._replace(query=new_query))

def main():
    # 使用時にセット
    openai.api_key = load_api_key_from_file()
    
    root = tk.Tk()
    root.title("YouTubeチャット＆動画処理ツール")
    frame = tk.Frame(root, padx=20, pady=20)
    frame.pack()

    state = {
        "video_url": "",
        "safe_title": "",
        "raw_title": "",
        "chat_file": "",
        "video_file": "",
        "x": [],
        "y": [],
        "x_labels": [],
        "valleys": [],
        "peaks": []
    }

    def update_paths_from_url():
        url_input = entry.get().strip()
        if not url_input:
            messagebox.showwarning("URL未入力", "YouTubeのURLを入力してください")
            return False
        normalized_url = normalize_youtube_url(url_input)
        state["video_url"] = normalized_url
        result = subprocess.run([
            "python", "-m", "yt_dlp", "--get-title", normalized_url
        ], capture_output=True, text=True, shell=True, encoding="utf-8", errors="replace")
        title = result.stdout.strip()
        if result.returncode != 0 or not title:
            messagebox.showerror("エラー", "動画タイトルが取得できませんでした")
            return False
        state["raw_title"] = title
        state["safe_title"] = re.sub(r'[\\/*?:"<>|]', "_", title)
        output_dir = BASE_DIR / "output"
        output_dir.mkdir(exist_ok=True)
        state["chat_file"] = str(output_dir / f"{state['safe_title']}_chat.json")
        state["video_file"] = str(output_dir / f"{state['safe_title']}.mp4")
        return True

    def download_chat():
        if not update_paths_from_url():
            return
        if os.path.exists(state["chat_file"]):
            messagebox.showinfo("情報", "チャットファイルは既に存在します。")
            return
        subprocess.run([
            "python", "-m", "chat_downloader", state["video_url"],
            "--output", state["chat_file"]
        ])
        messagebox.showinfo("完了", "チャットダウンロード完了！")

    def download_video():
        if not update_paths_from_url():
            return
        if os.path.exists(state["video_file"]):
            messagebox.showinfo("情報", "動画ファイルは既に存在します。")
            return
        subprocess.run([
            "yt-dlp",
            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]",
            "--merge-output-format", "mp4",
            "-o", state["video_file"],
            state["video_url"]
        ])
        messagebox.showinfo("完了", "動画ダウンロード完了！")

    def analyze_and_plot():
        def analyze():
            if not update_paths_from_url():
                return
            if not os.path.exists(state["chat_file"]):
                messagebox.showwarning("警告", "チャットファイルが存在しません。")
                return
            with open(state["chat_file"], "r", encoding="utf-8") as f:
                data = json.load(f)
            chat_counts = defaultdict(int)
            for msg in data:
                try:
                    t = float(msg["time_in_seconds"])
                    if t < 0:
                        continue
                    bucket = int(t // 300) * 300
                    chat_counts[bucket] += 1
                except (KeyError, ValueError):
                    continue
            x = sorted(chat_counts.keys())
            y = [chat_counts[t] for t in x]
            x_labels = [f"{s//3600}:{(s//60)%60:02}" for s in x]
            valleys, peaks = [], []
            for i in range(1, len(y) - 1):
                t = x[i]
                if y[i - 1] > y[i] < y[i + 1]:
                    valleys.append(t)
                elif y[i - 1] < y[i] > y[i + 1]:
                    peaks.append(t)
            state.update({"x": x, "y": y, "x_labels": x_labels, "valleys": valleys, "peaks": peaks})
            root.after(0, draw_graph)

        def draw_graph():
            plt.figure(figsize=(12, 5))
            plt.plot(state["x_labels"], state["y"], label="チャット数")
            for i in range(1, len(state["y"]) - 1):
                if state["x"][i] in state["valleys"]:
                    plt.plot(state["x_labels"][i], state["y"][i], 'ro')
                elif state["x"][i] in state["peaks"]:
                    plt.plot(state["x_labels"][i], state["y"][i], 'bo')
            plt.xlabel("動画時間（時:分）")
            plt.ylabel("チャット数（5分単位）")
            plt.title(state["raw_title"])
            plt.grid()
            plt.legend()
            plt.tight_layout()
            plt.show()

        threading.Thread(target=analyze).start()

    def generate_segments():
        if not state["valleys"] or not state["peaks"]:
            messagebox.showwarning("警告", "分析が先に必要です。")
            return
        if not os.path.exists(state["video_file"]):
            messagebox.showwarning("警告", "動画ファイルが見つかりません。")
            return
        BUFFER = 300
        segment_count = 1
        for v_sec in state["valleys"]:
            next_peaks = [p for p in state["peaks"] if p > v_sec]
            if not next_peaks:
                continue
            p_sec = next_peaks[0]
            start = max(0, v_sec - BUFFER)
            end = p_sec + BUFFER
            duration = end - start
            segment_path = SEGMENT_DIR / f"segment_{segment_count:02}.mp4"
            subprocess.run([
                "ffmpeg", "-ss", str(timedelta(seconds=start)),
                "-i", state["video_file"],
                "-t", str(timedelta(seconds=duration)),
                "-c", "copy", str(segment_path)
            ])
            segment_count += 1
        messagebox.showinfo("完了", "セグメント生成が完了しました！")

    def generate_clips_from_folder():
        folder = filedialog.askdirectory(title="セグメントフォルダを選択")
        if not folder:
            print("⚠️ セグメントフォルダが選択されませんでした。処理を中止します。")
            return
    
        def run():
            print(f"📁 セグメントフォルダ: {folder}")
            for segment_file in Path(folder).glob("segment_*.mp4"):
                print(f"🎞️ セグメント処理開始: {segment_file.name}")
                try:
                    result = whisper_model.transcribe(str(segment_file), language="ja", task="transcribe")
                    segments = result["segments"]
                    print(f"📝 字幕セグメント数: {len(segments)}")
                    clips = group_segments_by_duration(segments, MIN_DURATION, MAX_DURATION)
                    print(f"📌 抽出されたクリップ数: {len(clips)}")
                    output_dir = OUTPUT_BASE_DIR / segment_file.stem
                    output_dir.mkdir(parents=True, exist_ok=True)
                    for i, clip in enumerate(clips):
                        print(f"🔧 クリップ生成: clip_{i} [{clip.start_time:.2f}s - {clip.end_time:.2f}s]")
                        export_clip(i, clip, segment_file, output_dir)
                except Exception as e:
                    print(f"❌ {segment_file.name} の処理に失敗しました: {e}")
            print("✅ フォルダ内すべてのセグメント処理が完了しました")
            root.after(0, lambda: messagebox.showinfo("完了", "フォルダ内セグメントのクリップ生成が完了しました"))
    
        threading.Thread(target=run).start()

    def generate_clips_from_file():
        filepath = filedialog.askopenfilename(filetypes=[("MP4 Files", "*.mp4")])
        if not filepath:
            print("⚠️ ファイルが選択されませんでした。処理を中止します。")
            return

        def run():
            file = Path(filepath)
            print(f"🎬 ファイル処理開始: {file.name}")
            try:
                result = whisper_model.transcribe(str(file), language="ja", task="transcribe")
                segments = result["segments"]
                print(f"📝 字幕セグメント数: {len(segments)}")
                clips = group_segments_by_duration(segments, MIN_DURATION, MAX_DURATION)
                print(f"📌 抽出されたクリップ数: {len(clips)}")
                output_dir = OUTPUT_BASE_DIR / file.stem
                output_dir.mkdir(parents=True, exist_ok=True)
                for i, clip in enumerate(clips):
                    print(f"🔧 クリップ生成: clip_{i} [{clip.start_time:.2f}s - {clip.end_time:.2f}s]")
                    export_clip(i, clip, file, output_dir)
            except Exception as e:
                print(f"❌ ファイル {file.name} の処理に失敗しました: {e}")
            print("✅ ファイルのクリップ生成が完了しました")
            root.after(0, lambda: messagebox.showinfo("完了", "ファイルのクリップ生成が完了しました"))

        threading.Thread(target=run).start()

    label = tk.Label(frame, text="YouTube動画URLを入力:")
    label.pack()
    entry = tk.Entry(frame, width=70)
    entry.pack(pady=5)
    tk.Button(frame, text="🛰️ チャットを取得", command=lambda: threading.Thread(target=download_chat).start()).pack(pady=5)
    tk.Button(frame, text="🎬 動画を取得", command=lambda: threading.Thread(target=download_video).start()).pack(pady=5)
    tk.Button(frame, text="📊 分析してグラフを表示", command=analyze_and_plot).pack(pady=5)
    tk.Button(frame, text="✂️ セグメント生成", command=generate_segments).pack(pady=5)
    tk.Button(frame, text="🎞️ Clip生成（フォルダ）", command=generate_clips_from_folder).pack(pady=5)
    tk.Button(frame, text="🎞️ Clip生成（ファイル）", command=generate_clips_from_file).pack(pady=5)

    root.mainloop()

if __name__ == "__main__":
    main()