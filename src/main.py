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
    key_path = Path(__file__).resolve().parent.parent / "assets" / "sec" / "openai_key.txt"
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
    print("🤖 ChatGPT に誤字脱字の修正を依頼中...")

    raw_lines = [f"{i}: {seg['text']}" for i, seg in enumerate(segments)]
    full_text = "\n".join(raw_lines)

    prompt = (
        "以下は音声認識ツール『Whisper』によって自動生成された日本語の文字起こし結果です。\n"
        "各行は音声セグメントに対応しており、インデックス付きで表示されています。\n"
        "あなたの仕事は **音声認識に起因する誤字脱字のみ** を修正することです。\n\n"
        "【重要な指示】\n"
        "- 各行の構文や順序を絶対に変更しないでください。\n"
        "- 文を削除・追加・補完しないでください。\n"
        "- 行の内容を GPT が生成しないでください（例：「ありがとうございました」などを追加しない）。\n"
        "- 各行は `インデックス: 修正後の文` の形式で返してください。\n"
        "- 空白や句読点の修正は最小限にしてください。\n"
        "- 入力と出力の行数・インデックスは完全に一致させてください。\n"
        "- 出力はテキストのみ。説明や補足は不要です。\n\n"
        "以下が修正対象の入力です：\n\n" + full_text
    )

    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたは日本語音声認識の誤字脱字を修正するプロの編集者です。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
    except Exception as e:
        print(f"❌ ChatGPT API エラー:\n\n{e}")
        raise

    print("✅ ChatGPT 校関完了")

    content = response.choices[0].message.content

    corrected_segments = []
    for line in content.strip().splitlines():
        if ':' not in line:
            continue
        try:
            index_str, text = line.split(":", 1)
            index = int(index_str.strip())
            if 0 <= index < len(segments):
                corrected_segments.append({
                    "index": index,
                    "text": text.strip()
                })
        except Exception:
            continue

    return corrected_segments

def call_gpt_group_segments(corrected_segments: List[dict]) -> List[dict]:
    print("📚 ChatGPT に段落構造の抽出を依頼中...")

    raw_lines = [f"{i}: {seg['text']}" for i, seg in enumerate(corrected_segments)]
    full_text = "\n".join(raw_lines)

    prompt = (
        "以下は日本語の音声認識結果（誤字修正済み）です（各行はインデックス付き）。\n"
        "文の内容を変えずに、自然なまとまりで段落を作ってください。\n"
        "各段落には、元のインデックス範囲を `#start=3,end=7` の形式で示してください。\n"
        "テキスト本文は不要です。インデックス範囲だけで構いません。\n\n"
        + full_text
    )

    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたは日本語の発話を自然な段落に区切る編集者です。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
    except Exception as e:
        print(f"❌ ChatGPT API エラー:\n\n{e}")
        return []

    content = response.choices[0].message.content

    # インデックス範囲の抽出
    import re
    blocks = re.findall(r"#start=(\d+),end=(\d+)", content)

    parsed = []
    for start, end in blocks:
        start_idx = int(start)
        end_idx = int(end)
        # 対応するテキストを連結（句点なしも考慮し、スペース区切り）
        joined_text = " ".join(
            corrected_segments[i]["text"] for i in range(start_idx, end_idx + 1)
        ).strip()
        parsed.append({
            "start_index": start_idx,
            "end_index": end_idx,
            "text": joined_text
        })

    print(f"✅ 段落構造抽出完了（{len(parsed)} 段落）")
    return parsed

def remove_redundant_segments(segments: List[dict], max_repeat: int = 2) -> List[dict]:
    """
    同じテキストが連続して max_repeat 回以上出てきたらそれ以降を除外する。
    """
    filtered_segments = []
    last_text = None
    repeat_count = 0

    for seg in segments:
        text = seg["text"].strip()

        if text == last_text:
            repeat_count += 1
        else:
            repeat_count = 0
            last_text = text

        if repeat_count < max_repeat:
            filtered_segments.append(seg)
        else:
            print(f"⚠️ 重複セグメントをスキップ: {text} [{seg['start']} ~ {seg['end']}]")

    return filtered_segments

def escape_ffmpeg_path(path: Path) -> str:
    path = path.as_posix()
    if ":" in path:
        drive, rest = path.split(":/", 1)
        return f"{drive}\\:/{rest}"
    return path

def export_clip(index: int, clip: Clip, video_path: Path, output_dir: Path):
    clip_path = output_dir / f"clip_{index}.mp4"
    srt_path = output_dir / f"clip_{index}.srt"
    raw_srt_path = output_dir / f"clip_{index}_raw.srt"
    diff_path = output_dir / f"clip_{index}_diff.txt"
    subtitled_path = output_dir / f"clip_{index}_subtitled.mp4"
    structure_path = output_dir / f"clip_{index}_structure.json"

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
    
    # 🧼 重複フィルターを適用
    segments = remove_redundant_segments(segments)

    if not any(seg["text"].strip() for seg in segments):
        clip_path.unlink(missing_ok=True)
        return

    # ③ 校閲前字幕を raw_srt に保存
    with open(raw_srt_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments):
            start = format_timestamp(seg["start"])
            end = format_timestamp(seg["end"])
            text = seg["text"].strip()
            f.write(f"{i+1}\n{start} --> {end}\n{text}\n\n")

    # ④ ChatGPTで誤字脱字のみ修正
    corrected = call_gpt_proofread_segments(segments)

    # ⑤ 校閲済み字幕を srt に保存（タイミングはWhisper通り）
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, corr in enumerate(corrected):
            seg = segments[corr["index"]]
            start = format_timestamp(seg["start"])
            end = format_timestamp(seg["end"])
            f.write(f"{i+1}\n{start} --> {end}\n{corr['text']}\n\n")

    # ⑥ 差分ログを出力
    with open(diff_path, "w", encoding="utf-8") as f:
        f.write("📝 修正ログ（インデックスごとの差分）\n\n")
        for corr in corrected:
            original = segments[corr["index"]]["text"].strip()
            corrected_text = corr["text"]
            if original != corrected_text:
                f.write(f"[{corr['index']}]\nBefore: {original}\nAfter:  {corrected_text}\n\n")

    # ⑦ ChatGPTで段落構造を生成（クリップ判定用に別途保持）
    structure = call_gpt_group_segments(segments)
    if structure:
        with open(structure_path, "w", encoding="utf-8") as f:
            json.dump(structure, f, ensure_ascii=False, indent=2)

    # ⑧ 字幕を焼き込み
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
    
    # 設定データ
    settings = {"resolution": "1920x1080"}
    # メニューバー追加
    menubar = tk.Menu(root)
    root.config(menu=menubar)
    
    def open_settings_window():
        settings_window = tk.Toplevel(root)
        settings_window.title("設定")
        settings_window.geometry("300x120")

        tk.Label(settings_window, text="解像度を設定:").pack(pady=10)

        # 現在の設定から横・縦を分離
        current_res = settings.get("resolution", "1920x1080")
        default_width, default_height = current_res.lower().split("x")

        # 横幅・縦幅のエントリボックス
        entry_frame = tk.Frame(settings_window)
        entry_frame.pack()

        width_var = tk.StringVar(value=default_width)
        height_var = tk.StringVar(value=default_height)

        width_entry = tk.Entry(entry_frame, textvariable=width_var, width=6)
        width_entry.pack(side=tk.LEFT)

        tk.Label(entry_frame, text=" x ").pack(side=tk.LEFT)

        height_entry = tk.Entry(entry_frame, textvariable=height_var, width=6)
        height_entry.pack(side=tk.LEFT)

        def save_settings():
            w = width_var.get().strip()
            h = height_var.get().strip()
            if not w.isdigit() or not h.isdigit():
                messagebox.showerror("エラー", "横幅・縦幅には数値を入力してください。")
                return
            settings["resolution"] = f"{w}x{h}"
            messagebox.showinfo("設定保存", f"解像度を {settings['resolution']} に設定しました")
            settings_window.destroy()

        tk.Button(settings_window, text="保存", command=save_settings).pack(pady=10)
    
    # メニュー項目
    setting_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="設定", menu=setting_menu)
    setting_menu.add_command(label="解像度", command=open_settings_window)
    
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

        # 🔹 保存先をエクスプローラーで選択（.mp4 指定）
        initial_name = f"{state['safe_title']}.mp4"
        save_path = filedialog.asksaveasfilename(
            title="保存先を選択してください",
            defaultextension=".mp4",
            filetypes=[("MP4 files", "*.mp4")],
            initialfile=initial_name
        )

        if not save_path:
            print("⚠️ 保存がキャンセルされました。")
            return

        # 🔸 state["video_file"] にセット（後続処理のため）
        state["video_file"] = save_path

        # 🔹 ユーザー指定解像度
        resolution = settings.get("resolution", "1920x1080")
        width_str, height_str = resolution.lower().split("x")
        width = int(width_str)
        height = int(height_str)

        # 🔸 yt-dlpでフルHD（137+140）を一時ファイルにダウンロード
        fullhd_selector = "137+140"

        subprocess.run([
            "yt-dlp",
            "--force-overwrites",  # ← 🔥 強制上書き
            "-f", fullhd_selector,
            "--merge-output-format", "mp4",
            "-o", save_path,
            state["video_url"]
        ], check=True)

        # 🔹 フルHDならそのまま完了
        if resolution == "1920x1080":
            messagebox.showinfo("完了", f"動画ダウンロード完了！（{resolution}）")
            return

        # 🔹 それ以外 → トリミング＋リサイズ
        crop_width = int(720 * width / 1080)
        crop_x = (1920 - crop_width) // 2
        vf_filter = f"crop={crop_width}:1080:{crop_x}:0,scale={width}:{height}"

        output_temp_path = Path(save_path).with_stem(Path(save_path).stem + "_converted")

        subprocess.run([
            "ffmpeg", "-y",
            "-i", save_path,
            "-vf", vf_filter,
            "-c:v", "h264_nvenc",
            "-c:a", "copy",
            str(output_temp_path)
        ], check=True)

        os.replace(output_temp_path, save_path)

        messagebox.showinfo("完了", f"動画ダウンロードと変換完了！（{resolution}）")

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