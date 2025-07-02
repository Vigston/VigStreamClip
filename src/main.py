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
from tkinter import *
from tkinter import messagebox

plt.rcParams["font.family"] = "Yu Gothic"

BASE_DIR = Path(__file__).resolve().parent.parent
SEGMENT_DIR = BASE_DIR / "output" / "segments"
OUTPUT_BASE_DIR = BASE_DIR / "output" / "clip"
MIN_DURATION = 60
MAX_DURATION = 180

# 字幕スタイル設定用デフォルト
subtitle_style_settings = {
    "Font": "Yu Gothic",
    "FontSize": 26,
    "Outline": 2,
    "OutlineColour": "&H00000000",
    "Shadow": 1,
    "PrimaryColour": "&H00FFFFFF",
    "MarginV": 40,
    "Alignment": 2
}

# 使用可能なフォント一覧
AVAILABLE_FONTS = ["Yu Gothic", "Noto Sans JP", "MS Gothic", "Arial", "Meiryo"]

# # 実測ベースに合わせてチューニング
FONT_CHAR_WIDTH = {
    "Yu Gothic": 24,
    "Noto Sans JP": 22,
    "MS Gothic": 20,
}

# 設定データ
settings = {
    "resolution": "1920x1080",
    "font": "Yu Gothic"
}

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

# フォント名から max_width を推定する関数
def estimate_max_width(resolution: str, font_name: str) -> int:
    screen_width = int(resolution.split("x")[0])
    usable_width = screen_width * 0.7
    font_width = FONT_CHAR_WIDTH.get(font_name, 24)
    print(f"[estimate_max_width]usable_width:{usable_width}")
    print(f"[estimate_max_width]font_width:{font_width}")
    return max(10, int(usable_width / font_width))

# 自動改行処理
def wrap_text_for_subtitles(text: str, max_width: int) -> str:
    lines = []
    current = ""
    for ch in text:
        current += ch
        if len(current) >= max_width:
            lines.append(current)
            current = ""
    if current:
        lines.append(current)
    return "\n".join(lines)

# 動画解像度取得(reuturn str("{width}x{height})")
def get_video_resolution(video_path: Path) -> str:
    result = subprocess.run([
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "json", str(video_path)
    ], capture_output=True, text=True, check=True)

    info = json.loads(result.stdout)
    width = info["streams"][0]["width"]
    height = info["streams"][0]["height"]
    return f"{width}x{height}"

# クリップ動画の作成、出力
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

    # 字幕用 max_width を設定に応じて計算
    font_name = settings.get("font", "Yu Gothic")
    resolution = get_video_resolution(clip_path)
    max_width = estimate_max_width(resolution, font_name)
    
    print(f"[export_clip]max_width:{max_width}")

    # ⑤ 校閲済み字幕を srt に保存（タイミングはWhisper通り）
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, corr in enumerate(corrected):
            seg = segments[corr["index"]]
            start = format_timestamp(seg["start"])
            end = format_timestamp(seg["end"])

            # 🔽 ここで自動改行を適用
            wrapped_text = wrap_text_for_subtitles(corr["text"], max_width)

            f.write(f"{i+1}\n{start} --> {end}\n{wrapped_text}\n\n")

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
    
    font_name = settings.get("font", "Yu Gothic")
    font_size = FONT_CHAR_WIDTH.get(font_name, 24)

    # ⑧ 字幕を焼き込み
    subtitle_filter = generate_subtitle_filter(str(srt_path))
    
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

# 解像度設定メニュー表示
def open_resolution_window(root: tk.Tk):
    res_win = tk.Toplevel(root)
    res_win.title("解像度の設定")
    res_win.geometry("300x120")

    tk.Label(res_win, text="解像度を設定:").pack(pady=5)
    current_res = settings.get("resolution", "1920x1080")
    default_width, default_height = current_res.lower().split("x")

    entry_frame = tk.Frame(res_win)
    entry_frame.pack()
    width_var = tk.StringVar(value=default_width)
    height_var = tk.StringVar(value=default_height)
    tk.Entry(entry_frame, textvariable=width_var, width=6).pack(side=tk.LEFT)
    tk.Label(entry_frame, text=" x ").pack(side=tk.LEFT)
    tk.Entry(entry_frame, textvariable=height_var, width=6).pack(side=tk.LEFT)

    def save_resolution():
        w, h = width_var.get().strip(), height_var.get().strip()
        if not w.isdigit() or not h.isdigit():
            messagebox.showerror("エラー", "横幅・縦幅には数値を入力してください。")
            return
        settings["resolution"] = f"{w}x{h}"
        messagebox.showinfo("保存完了", f"解像度: {settings['resolution']}")
        res_win.destroy()

    tk.Button(res_win, text="保存", command=save_resolution).pack(pady=10)

# 字幕設定ウィンドウ表示
def open_subtitle_style_window(root):
    def show_help():
        help_win = Toplevel(root)
        help_win.title("字幕スタイルの説明")
        help_text = Text(help_win, wrap="word", width=80, height=30)
        help_text.pack(padx=10, pady=10)

        try:
            with open(os.path.join(os.path.dirname(__file__), '..', 'res', 'subtitle_style_help.txt'), encoding="utf-8") as f:
                help_content = f.read()
        except Exception as e:
            help_content = f"[エラー] 説明ファイルの読み込みに失敗しました:{e}"

        help_text.insert("1.0", help_content)
        help_text.configure(state="disabled")
        Button(help_win, text="閉じる", command=help_win.destroy).pack(pady=5)

    style_win = Toplevel(root)
    style_win.title("字幕スタイルの設定")
    Button(style_win, text="❓ 説明", command=show_help).place(relx=1.0, x=-10, y=10, anchor='ne')
    style_win.geometry("400x420")

    entries = {}

    def add_entry(label, key):
        frame = Frame(style_win)
        frame.pack(pady=4, anchor=W)
        Label(frame, text=label, width=15, anchor=W).pack(side=LEFT)
        var = StringVar(value=str(subtitle_style_settings[key]))
        entry = Entry(frame, textvariable=var, width=20)
        entry.pack(side=LEFT)
        entries[key] = var

    # フォント選択（OptionMenu）
    font_frame = Frame(style_win)
    font_frame.pack(pady=4, anchor=W)
    Label(font_frame, text="フォント", width=15, anchor=W).pack(side=LEFT)
    font_var = StringVar(value=subtitle_style_settings["Font"])
    OptionMenu(font_frame, font_var, *AVAILABLE_FONTS).pack(side=LEFT)

    add_entry("フォントサイズ", "FontSize")
    add_entry("文字色", "PrimaryColour")
    add_entry("縁取りサイズ", "Outline")
    add_entry("縁取り色", "OutlineColour")
    add_entry("影のサイズ", "Shadow")
    add_entry("下マージン", "MarginV")
    add_entry("位置 (1~9)", "Alignment")

    def save_style():
        subtitle_style_settings["Font"] = font_var.get()
        for key, var in entries.items():
            val = var.get().strip()
            if key in ["FontSize", "Outline", "Shadow", "MarginV", "Alignment"]:
                if not val.isdigit():
                    messagebox.showerror("エラー", f"{key} は数値である必要があります。")
                    return
                subtitle_style_settings[key] = int(val)
            else:
                subtitle_style_settings[key] = val

        messagebox.showinfo("保存完了", "字幕スタイルが保存されました。")
        style_win.destroy()

    Button(style_win, text="保存", command=save_style).pack(pady=10)

# 字幕生成のフィルター設定を生成
def generate_subtitle_filter(srt_path: str) -> str:
    s = subtitle_style_settings
    style_str = (
        f"FontName={s['Font']},"
        f"FontSize={s['FontSize']},"
        f"PrimaryColour={s['PrimaryColour']},"
        f"Outline={s['Outline']},"
        f"OutlineColour={s['OutlineColour']},"
        f"Shadow={s['Shadow']},"
        f"MarginV={s['MarginV']},"
        f"Alignment={s['Alignment']}"
    )
    return f"subtitles='{srt_path}:force_style={style_str}'"

def main():
    # 使用時にセット
    openai.api_key = load_api_key_from_file()
    
    root = tk.Tk()
    root.title("YouTubeチャット＆動画処理ツール")
    
    # メニューバー追加
    menubar = tk.Menu(root)
    root.config(menu=menubar)
    
    # メニュー項目
    setting_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="設定", menu=setting_menu)
    setting_menu.add_command(label="解像度", command=lambda: open_resolution_window(root))
    setting_menu.add_command(label="字幕スタイル", command=lambda: open_subtitle_style_window(root))
    
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

    def analyze_and_plot() -> threading.Thread:
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

        t = threading.Thread(target=analyze)
        t.start()
        return t  # スレッドオブジェクトを返す

    def generate_segments():
        if not state["valleys"] or not state["peaks"]:
            print("分析を行っていなかったので分析処理を実行します。")
            thread = analyze_and_plot()
            thread.join() # 終わるまで待機

        # 🎥 元動画ファイルを選択
        video_file = filedialog.askopenfilename(
            title="セグメント生成に使う動画ファイルを選択",
            filetypes=[("MP4 Files", "*.mp4")]
        )
        if not video_file:
            print("⚠️ 動画ファイルが選択されませんでした。処理を中止します。")
            return

        # 💾 保存先は固定
        SEGMENT_DIR.mkdir(parents=True, exist_ok=True)

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
                "-i", video_file,
                "-t", str(timedelta(seconds=duration)),
                "-c", "copy", str(segment_path)
            ])
            segment_count += 1

        messagebox.showinfo("完了", f"セグメント生成が完了しました！\n保存先: {SEGMENT_DIR}")

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