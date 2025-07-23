import os
import subprocess
import json
import re
from collections import defaultdict
import threading
import urllib.parse
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox, filedialog
from pathlib import Path
from dataclasses import dataclass, field
from typing import List
import whisper
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from datetime import timedelta
import openai
from tkinter import *
from tkinter import messagebox
from fontTools.ttLib import TTFont  # ← fontTools を使用
import sys
import logging
from tkinter.scrolledtext import ScrolledText
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont
import tempfile

# 基本ディレクトリ取得
def get_base_dir():
    if hasattr(sys, "_MEIPASS"):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

plt.rcParams["font.family"] = "Yu Gothic"

BASE_DIR = get_base_dir()
FONT_DIR = BASE_DIR / "fonts"
SEGMENT_DIR = BASE_DIR / "output" / "segments"
OUTPUT_BASE_DIR = BASE_DIR / "output" / "clip"
SETTINGS_FILE_DIR = BASE_DIR / "res" / "setting.txt"
MIN_DURATION = 60
MAX_DURATION = 180

# カスタムフォントパス
CUSTOM_FONT_PATHS = {}
# 使用可能なフォント一覧
AVAILABLE_FONTS = ["Yu Gothic", "Noto Sans JP", "MS Gothic", "Arial", "Meiryo"]

# フォントごとの横幅係数（1pt あたり何 px を占有するか）
FONT_WIDTH_RATIO = {
    "Yu Gothic": 3.94,
}

# 設定データ
settings = {
    # 解像度などの一般設定
    "Resolution": "1920x1080",
    
    # 字幕スタイル
    "Font": "Yu Gothic",
    "FontSize": 24,
    "Outline": 2,
    "OutlineColor": "&H00000000",
    "Shadow": 1,
    "PrimaryColor": "&H00FFFFFF",
    "MarginV": 40,
    "Alignment": 2,
    
    # タイトルスタイル
    "TitleFont": "Yu Gothic",
    "TitleFontSize": 120,
    "TitleAreaX": 0,           # 画像左上からのX座標
    "TitleAreaY": 0,           # 画像左上からのY座標
    "TitleAreaWidth": 800,     # 表示エリア幅
    "TitleAreaHeight": 200,    # 表示エリア高さ
    "TitleAlignV": "top",      # 文字の矩形内表示位置(y) 'top', 'center', 'bottom'
    "TitleAlignH": "center",   # 文字の矩形内表示位置(x) 'left', 'center', 'right'
}

# whisperの使用モデルを設定
whisper_model = whisper.load_model("large-v3", device="cuda")

COLOR_MAP = {
    "赤": "&H000033FF&",
    "青": "&H00FF0000&",
    "緑": "&H0000FF00&",
    "黄": "&H0000FFFF&",
    "水": "&H00FFFF00&",
    "ピンク": "&H00FF66FF&",
    "オレンジ": "&H000099FF&",
    "紫": "&H00CC00CC&",
    "茶": "&H00336699&",
    "灰": "&H00808080&",
    "白": "&H00FFFFFF&",
    "黒": "&H00000000&",
    "薄赤": "&H00CCCCFF&",
    "薄青": "&H00FFCCCC&",
    "薄緑": "&H00CCFFCC&",
    "薄黄": "&H00CCFFFF&",
    "濃赤": "&H000000CC&",
    "濃青": "&H00CC0000&",
    "濃緑": "&H0000CC00&",
    "金": "&H0000A5FF&",
    "銀": "&H00C0C0C0&",
    "ベージュ": "&H00CCFFFF&",
    "紺": "&H00660000&",
    "ライム": "&H0000FF80&",
}

# アプリデータ
class App:
    class StdoutRedirector:
        def __init__(self, text_widget):
            self.text_widget = text_widget
        def write(self, message):
            self.text_widget.configure(state='normal')
            self.text_widget.insert('end', message)
            self.text_widget.configure(state='disabled')
            self.text_widget.yview('end')
            self.text_widget.update_idletasks() # 「保留中の描画・レイアウト作業（アイドルタスク）」だけを今すぐ実行
        def flush(self): pass

    class TextHandler(logging.Handler):
        def __init__(self, widget):
            super().__init__()
            self.widget = widget
        def emit(self, record):
            msg = self.format(record)
            def append():
                self.widget.configure(state='normal')
                self.widget.insert('end', msg + '\n')
                self.widget.configure(state='disabled')
                self.widget.yview('end')
            self.widget.after(0, append)
    
    def __init__(self):
        self.root = tk.Tk()
        self.log_frame: Frame = None
        self.log_widget: ScrolledText = None
        self.text_handler: App.TextHandler = None
        self.console_handler: logging.StreamHandler = None
        self.menubar: Menu = None
        self.frame: tk.Frame = None
        self.label: tk.Label = None
        self.entry: tk.Entry = None
        self.stream_analysis: StreamAnalysis = StreamAnalysis()
    
    def run(self):
        self.root.mainloop()
        
    def setup(self, app_name: str):
        self.root.title(app_name)
        
        self.setup_gui()
        self.setup_logging_area()
        self.setup_logging_redirect()
        self.setup_menu()
    
    def setup_gui(self):
        # GUIのレイアウト枠
        self.frame = tk.Frame(self.root, padx=20, pady=20)
        self.frame.pack()
        
        self.label = tk.Label(self.frame, text="YouTube動画URLを入力:")
        self.label.pack()
        self.entry = tk.Entry(self.frame, width=70)
        self.entry.pack(pady=5)
        tk.Button(self.frame, text="🛰️ チャットを取得", command=lambda: threading.Thread(target=download_chat(self)).start()).pack(pady=5)
        tk.Button(self.frame, text="🎬 動画を取得", command=lambda: threading.Thread(target=download_video(self)).start()).pack(pady=5)
        tk.Button(self.frame, text="📊 分析してグラフを表示", command=lambda: analyze_and_plot(self)).pack(pady=5)
        tk.Button(self.frame, text="✂️ セグメント生成", command=lambda: threading.Thread(target=generate_segments(self)).start()).pack(pady=5)
        tk.Button(self.frame, text="🎞️ Clip生成（フォルダ）", command=lambda: threading.Thread(target=generate_clips_from_folder(self)).start()).pack(pady=5)
        tk.Button(self.frame, text="🎞️ Clip生成（ファイル）", command=lambda: threading.Thread(target=generate_clips_from_file(self)).start()).pack(pady=5)
        tk.Button(self.frame, text="🖼️ サムネイル生成", command=lambda: threading.Thread(target=generate_all_thumbnails_gui(self)).start()).pack(pady=5)
    
    def setup_menu(self):
        self.menubar = tk.Menu(self.root)
        self.root.config(menu=self.menubar)
        
        # メニュー項目
        #####設定#####
        setting_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="設定", menu=setting_menu)
        setting_menu.add_command(label="解像度", command=lambda: open_resolution_window(self.root))
        setting_menu.add_command(label="字幕スタイル", command=lambda: open_subtitle_style_window(self.root))
        setting_menu.add_command(label="題名スタイル", command=lambda: open_title_style_dialog(self.root))
        setting_menu.add_separator()
        setting_menu.add_command(label="💾 設定を保存", command=lambda: (
            save_settings(),
            messagebox.showinfo("保存完了", "現在の設定を保存しました。")
        ))

        #####出力#####
        output_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="出力", menu=output_menu)
        output_menu.add_command(label="クリップ焼き直し", command=lambda: threading.Thread(target=clip_reburn_gui).start())
    
    def setup_logging_area(self):
        # ログ用ウィジェット作成
        self.log_frame = tk.Frame(self.root)
        self.log_frame.pack(side="bottom", fill="x")
        self.log_widget = ScrolledText(self.log_frame, state='disabled', height=10)
        self.log_widget.pack(fill="both", expand=True)

    def setup_logging_redirect(self):
        # stdout/stderr をGUIに
        sys.stdout = App.StdoutRedirector(self.log_widget)
        sys.stderr = App.StdoutRedirector(self.log_widget)

        self.text_handler = App.TextHandler(self.log_widget)
        self.text_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))

        self.console_handler = logging.StreamHandler(sys.__stdout__)
        self.console_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))

        logger = logging.getLogger()
        logger.setLevel(logging.WARNING)
        logger.addHandler(self.text_handler)
        logger.addHandler(self.console_handler)

# クリップデータ
@dataclass(slots=True)
class Clip:
    start_time: float
    end_time: float

# 配信データ
@dataclass(slots=True)
class StreamAnalysis:
    video_url: str = ""
    safe_title: str = ""
    raw_title: str = ""
    chat_file: str = ""
    video_file: str = ""
    x: List[int] = field(default_factory=list)
    y: List[int] = field(default_factory=list)
    x_labels: List[str] = field(default_factory=list)
    valleys: List[int] = field(default_factory=list)
    peaks: List[int] = field(default_factory=list)
    audio_x: List[int] = field(default_factory=list)
    audio_y: List[float] = field(default_factory=list)

# 直接ファイルを開く場合はこれを通して行う
def resource_path(relative_path: str) -> Path:
    """
    PyInstaller で実行されているかを判定し、実行時の一時フォルダを解決
    """
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / relative_path
    return Path(__file__).resolve().parent / ".." / relative_path

# ChatGptのAPIキーを読み込み
def load_api_key_from_file() -> str:
    key_path = resource_path("assets/sec/openai_key.txt")
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

# ffmpeg フィルタ用に Windowsパスをエスケープ（\ → /, : → \:）
def escape_ffmpeg_path(path: Path) -> str:
    """
    Windowsパスをffmpegのsubtitlesフィルタ用に変換：
    - \ → /
    - 最初の : → \:
    """
    s = str(path.resolve()).replace("\\", "/")
    if ":" in s:
        s = s.replace(":", "\\:", 1)
    return s

# スペースをバックスラッシュでエスケープ
def escape_font_name(name: str) -> str:
    return name.replace(" ", "\\ ")

#############
###フォント###
#############
# カスタムフォントデータのファイルパスを読み込み
def scan_custom_fonts() -> dict:
    """
    fonts/ 以下のすべてのサブフォルダから .ttf を探し、
    {フォント名: フルパス} を返す
    """
    FONT_DIR.mkdir(exist_ok=True)
    font_map = {}

    for font_path in FONT_DIR.rglob("*.ttf"):  # ← 再帰探索に変更！
        try:
            tt = TTFont(font_path)
            for record in tt["name"].names:
                if record.nameID == 1 and record.platformID == 3:
                    name = record.string.decode("utf-16-be").strip()
                    font_map[name] = str(font_path)
                    break
        except Exception as e:
            print(f"❌ フォント取得失敗: {font_path.name} ({e})")

    return font_map

# フォント名から max_width を推定する関数
def estimate_max_width(resolution: str, font_name: str, font_size: int) -> int:
    screen_width = int(resolution.split("x")[0])
    usable_width = screen_width * 0.7  # 実際に字幕が収まる幅
    ratio = FONT_WIDTH_RATIO.get(font_name, 4)
    font_width = font_size * ratio
    max_chars = int(usable_width / font_width)
    print(f"[estimate_max_width] usable_width: {usable_width}, font_width: {font_width:.2f}, max_width: {max_chars}")
    return max_chars

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

# srtファイルの色タグをASSタグに変換
def convert_color_tags_to_ass(text: str) -> str:
    def replacer(match):
        color_name = match.group(1)
        color_code = COLOR_MAP.get(color_name)
        if color_code:
            return f"{{\\c{color_code}}}"
        else:
            return match.group(0)  # 未定義色はそのまま残す

    converted = re.sub(r"\{(.*?)\}", replacer, text)

    # 既に色タグが含まれていなければ settings["PrimaryColor"] を追加
    #if r"\c&H" not in converted:
    #    color_code = settings.get("PrimaryColor", "&H00FFFFFF&")
    #    converted = f"{{\\c{color_code}}}" + converted

    return converted

# 長い字幕を自動で適切な長さに分割
def split_long_subtitle(text: str, max_chars: int) -> list:
    """長い字幕テキストを句読点・読点・スペースなどで自然に分割"""
    blocks = []
    buf = ""
    for ch in text:
        buf += ch
        # 指定文字数を超えたら区切り文字で分割
        if len(buf) >= max_chars and ch in "。！？、,. ":
            blocks.append(buf.strip())
            buf = ""
    if buf.strip():
        blocks.append(buf.strip())
    return blocks

def generate_comment_to_png_sequence(
    comments,        # チャットデータ（dictリスト）
    video_size,      # (幅, 高さ)
    out_frames_dir,  # PNG保存先ディレクトリ
    start_time,      # クリップの開始秒数
    end_time,        # クリップの終了秒数
    fps=30,
    duration_per_comment=3.0,
    font_path=None
):
    W, H = video_size
    frame_count = int((end_time - start_time) * fps)
    font = ImageFont.truetype(font_path or "arial.ttf", 36)
    num_tracks = 12
    track_height = H // (num_tracks + 2)
    tracks = [track_height * (i+1) for i in range(num_tracks)]
    danmaku = []
    for i, c in enumerate(comments):
        t0 = float(c["time_in_seconds"]) - start_time
        if 0 <= t0 < (end_time - start_time):
            y = tracks[i % num_tracks]
            danmaku.append({
                "text": c["message"],
                "start": t0,
                "y": y,
            })
    out_frames_dir = Path(out_frames_dir)
    out_frames_dir.mkdir(parents=True, exist_ok=True)
    for f in range(frame_count):
        t = f / fps
        img = Image.new("RGBA", (W, H), (0,0,0,0))
        draw = ImageDraw.Draw(img)
        for d in danmaku:
            appear = d["start"]
            if appear <= t < appear + duration_per_comment:
                bbox = draw.textbbox((0, 0), d["text"], font=font)
                w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
                progress = (t - appear) / duration_per_comment
                x = int(W - (W + w) * progress)
                draw.text((x, d["y"]), d["text"], font=font, fill=(255,255,255,255))
        img.save(str(out_frames_dir / f"danmaku_{f:04d}.png"))

def combine_video_with_danmaku_overlay(
    clip_path: Path,
    frames_dir: Path,
    out_path: Path,
    fps: int = 30
):
    # frames_dir 内に danmaku_%04d.png
    frames_pattern = str(frames_dir / "danmaku_%04d.png")
    cmd = [
        "ffmpeg", "-y",
        "-i", str(clip_path),
        "-framerate", str(fps),
        "-i", frames_pattern,
        "-filter_complex", "[0:v][1:v]overlay=shortest=1:format=auto",
        "-c:v", "h264_nvenc",
        "-c:a", "copy",
        str(out_path)
    ]
    subprocess.run(cmd, check=True)

def extract_comments_for_clip(chat_json_path, start_time, end_time):
    with open(chat_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [
        msg for msg in data
        if start_time <= float(msg.get("time_in_seconds", -1)) < end_time
        and msg.get("message")
    ]

def generate_video(
    danmaku_video: Path,    # ここで弾幕動画をinputとする
    srt_path: Path,
    output_path: Path,
    style_str: str = None
):
    if not style_str:
        s = settings
        font_name = s["Font"]
        style_str = (
            f"FontName={escape_font_name(font_name)},"
            f"FontSize={s['FontSize']},"
            f"PrimaryColor={s['PrimaryColor']},"
            f"Outline={s['Outline']},"
            f"OutlineColor={s['OutlineColor']},"
            f"Shadow={s['Shadow']},"
            f"MarginV={s['MarginV']},"
            f"Alignment={s['Alignment']}"
        )

    # 弾幕動画に直接字幕を合成
    filter_complex = (
        f"subtitles='{escape_ffmpeg_path(srt_path)}:force_style={style_str}'"
    )
    subprocess.run([
        "ffmpeg", "-y",
        "-i", str(danmaku_video),
        "-filter_complex", filter_complex,
        "-c:v", "h264_nvenc",
        str(output_path)
    ], check=True)

def export_clip(index: int, clip: Clip, video_path: Path, output_dir: Path, chat_json_path: Path):
    """
    クリップ動画＋字幕生成＋弾幕生成＋合成
    セグメントの絶対秒(start_sec, end_sec)は毎回 segment_info.json からファイル名で検索して取得する。
    """

    # ▼ セグメント情報(絶対秒)を segment_info.json から取得
    segment_info_path = SEGMENT_DIR / "segment_info.json"
    if not segment_info_path.exists():
        print(f"❌ segment_info.json が見つかりません: {segment_info_path}")
        return

    with open(segment_info_path, "r", encoding="utf-8") as f:
        segment_meta = json.load(f)
    my_info = next((item for item in segment_meta if item["file"] == video_path.name), None)
    if my_info is None:
        print(f"❌ {video_path.name} の開始・終了秒情報が segment_info.json に見つかりません")
        return

    segment_start_time = my_info["start_sec"]
    segment_end_time = my_info["end_sec"]

    # clip: 相対（このセグメントの0秒～X秒）→ 配信全体での絶対秒数
    abs_start = segment_start_time + clip.start_time
    abs_end = segment_start_time + clip.end_time

    # クリップごとの作業ディレクトリ
    clip_dir = output_dir / f"clip_{index}"
    clip_dir.mkdir(parents=True, exist_ok=True)

    # 各ファイルパス
    clip_path = clip_dir / f"clip_{index}.mp4"
    srt_path = clip_dir / f"clip_{index}.srt"
    raw_srt_path = clip_dir / f"clip_{index}_raw.srt"
    diff_path = clip_dir / f"clip_{index}_diff.txt"
    structure_path = clip_dir / f"clip_{index}_structure.json"
    frames_dir = clip_dir / "danmaku_frames"  # PNG連番保存用
    overlay_output = clip_dir / f"clip_{index}_danmaku.mp4"
    final_output = clip_dir / f"clip_{index}_final.mp4"

    # ① クリップ切り出し（この関数内の動画は相対秒でOK）
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
    if not segments:
        print(f"⚠️ Whisperのセグメントが空です: {clip_path.name}")
        return

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

    # ④ ChatGPTで誤字脱字修正
    corrected = call_gpt_proofread_segments(segments)

    # 字幕max_width計算
    font_name = settings.get("Font", "Yu Gothic")
    font_size = settings.get("FontSize", 24)
    resolution = get_video_resolution(clip_path)
    max_width = estimate_max_width(resolution, font_name, font_size)

    # ⑤ 校閲済み字幕を srt に保存
    with open(srt_path, "w", encoding="utf-8") as f:
        entry_num = 1
        for i, corr in enumerate(corrected):
            seg = segments[corr["index"]]
            seg_start = seg["start"]
            seg_end = seg["end"]
            blocks = split_long_subtitle(corr['text'], max_width)
            if not blocks:
                blocks = [corr['text']]
            block_count = len(blocks)
            total_duration = seg_end - seg_start
            duration_per_block = total_duration / block_count if block_count > 0 else total_duration
            for b_idx, b in enumerate(blocks):
                block_start = seg_start + duration_per_block * b_idx
                block_end = seg_start + duration_per_block * (b_idx + 1)
                start_str = format_timestamp(block_start)
                end_str = format_timestamp(block_end)
                f.write(f"{entry_num}\n{start_str} --> {end_str}\n{b}\n\n")
                entry_num += 1

    # ⑥ 差分ログ出力
    with open(diff_path, "w", encoding="utf-8") as f:
        f.write("📝 修正ログ（インデックスごとの差分）\n\n")
        for corr in corrected:
            original = segments[corr["index"]]["text"].strip()
            corrected_text = corr["text"]
            if original != corrected_text:
                f.write(f"[{corr['index']}]\nBefore: {original}\nAfter:  {corrected_text}\n\n")

    # ⑦ ChatGPTで段落構造を生成
    structure = call_gpt_group_segments(segments)
    if structure:
        with open(structure_path, "w", encoding="utf-8") as f:
            json.dump(structure, f, ensure_ascii=False, indent=2)

    # ⑧ チャットデータから該当区間コメント抽出（配信全体での絶対秒数）
    comments = extract_comments_for_clip(
        chat_json_path, abs_start, abs_end
    )

    # ⑨ 弾幕PNG連番生成
    video_resolution = get_video_resolution(clip_path)
    w, h = map(int, video_resolution.split("x"))
    font_path = CUSTOM_FONT_PATHS.get(settings.get("Font"), None)
    fps = 30
    generate_comment_to_png_sequence(
        comments,
        video_size=(w, h),
        out_frames_dir=frames_dir,
        start_time=clip.start_time,    # このクリップ内での相対秒
        end_time=clip.end_time,
        fps=fps,
        duration_per_comment=3.0,
        font_path=font_path
    )

    # ⑩ 本編＋弾幕PNG連番 overlay合成
    combine_video_with_danmaku_overlay(
        clip_path=clip_path,
        frames_dir=frames_dir,
        out_path=overlay_output,
        fps=fps
    )

    # ⑪ overlay合成後の動画に字幕焼き付け
    generate_video(
        danmaku_video=overlay_output,
        srt_path=srt_path,
        output_path=final_output
    )

    print(f"✅ 字幕＋弾幕 合成クリップ生成: {final_output}")

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
    current_res = settings.get("Resolution", "1920x1080")
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
        settings["Resolution"] = f"{w}x{h}"
        messagebox.showinfo("保存完了", f"解像度: {settings['Resolution']}")
        save_settings() # 設定保存
        res_win.destroy()

    tk.Button(res_win, text="保存", command=save_resolution).pack(pady=10)

# 字幕設定ウィンドウ表示
def open_subtitle_style_window(root: tk.Tk):
    def show_help():
        help_win = Toplevel(root)
        help_win.title("字幕スタイルの説明")
        help_text = Text(help_win, wrap="word", width=80, height=30)
        help_text.pack(padx=10, pady=10)

        try:
            with open(resource_path(os.path.join(os.path.dirname(__file__), '..', 'res', 'subtitle_style_help.txt')), encoding="utf-8") as f:
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
        var = StringVar(value=str(settings[key]))
        entry = Entry(frame, textvariable=var, width=20)
        entry.pack(side=LEFT)
        entries[key] = var

    # フォント選択（OptionMenu）
    font_frame = Frame(style_win)
    font_frame.pack(pady=4, anchor=W)
    Label(font_frame, text="フォント", width=15, anchor=W).pack(side=LEFT)
    font_var = StringVar(value=settings["Font"])
    OptionMenu(font_frame, font_var, *AVAILABLE_FONTS).pack(side=LEFT)

    add_entry("フォントサイズ", "FontSize")
    add_entry("文字色", "PrimaryColor")
    add_entry("縁取りサイズ", "Outline")
    add_entry("縁取り色", "OutlineColor")
    add_entry("影のサイズ", "Shadow")
    add_entry("下マージン", "MarginV")
    add_entry("位置 (1~9)", "Alignment")
    
    def choose_custom_font():
        custom_fonts = list(CUSTOM_FONT_PATHS.keys())
        if not custom_fonts:
            messagebox.showwarning("フォントなし", "fonts/ フォルダにフォントが見つかりませんでした。")
            return

        choose_win = Toplevel(root)
        choose_win.title("カスタムフォントを選択")
        choose_win.geometry("300x200")

        listbox = Listbox(choose_win, selectmode=SINGLE)
        for font_name in custom_fonts:
            listbox.insert(END, font_name)
        listbox.pack(padx=10, pady=10, fill=BOTH, expand=True)

        def select_font():
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("未選択", "フォントを選択してください。")
                return
            selected = listbox.get(selection[0])
            font_var.set(selected)
            choose_win.destroy()

    def save_style():
        settings["Font"] = font_var.get()
        for key, var in entries.items():
            val = var.get().strip()
            if key in ["FontSize", "Outline", "Shadow", "MarginV", "Alignment"]:
                if not val.isdigit():
                    messagebox.showerror("エラー", f"{key} は数値である必要があります。")
                    return
                settings[key] = int(val)
            else:
                settings[key] = val

        messagebox.showinfo("保存完了", "字幕スタイルが保存されました。")
        save_settings() # 設定保存
        style_win.destroy()

    Button(style_win, text="カスタムフォント", command=choose_custom_font).pack(pady=6)
    Button(style_win, text="保存", command=save_style).pack(pady=10)

def open_title_style_dialog(root: tk.Tk):
    dialog = tk.Toplevel(root)
    dialog.title("題名スタイル設定")

    # ▼ フォント名選択
    tk.Label(dialog, text="フォント名:").grid(row=0, column=0)
    title_font_var = tk.StringVar(value=settings.get("TitleFont", "Yu Gothic"))
    font_choices = ["Yu Gothic", "Noto Sans JP", "MS Gothic", "Arial", "Meiryo"] + list(CUSTOM_FONT_PATHS.keys())
    tk.OptionMenu(dialog, title_font_var, *font_choices).grid(row=0, column=1)

    # ▼ フォントサイズ
    tk.Label(dialog, text="フォントサイズ:").grid(row=1, column=0)
    title_font_size_var = tk.IntVar(value=settings.get("TitleFontSize", 120))
    tk.Spinbox(dialog, from_=10, to=400, textvariable=title_font_size_var).grid(row=1, column=1)

    # エリア
    tk.Label(dialog, text="X座標:").grid(row=2, column=0)
    x_var = tk.IntVar(value=settings.get("TitleAreaX", 0))
    tk.Spinbox(dialog, from_=0, to=9999, textvariable=x_var).grid(row=2, column=1)

    tk.Label(dialog, text="Y座標:").grid(row=3, column=0)
    y_var = tk.IntVar(value=settings.get("TitleAreaY", 0))
    tk.Spinbox(dialog, from_=0, to=9999, textvariable=y_var).grid(row=3, column=1)

    tk.Label(dialog, text="幅:").grid(row=4, column=0)
    w_var = tk.IntVar(value=settings.get("TitleAreaWidth", 800))
    tk.Spinbox(dialog, from_=0, to=9999, textvariable=w_var).grid(row=4, column=1)

    tk.Label(dialog, text="高さ:").grid(row=5, column=0)
    h_var = tk.IntVar(value=settings.get("TitleAreaHeight", 200))
    tk.Spinbox(dialog, from_=0, to=9999, textvariable=h_var).grid(row=5, column=1)

    # 垂直位置
    tk.Label(dialog, text="縦位置:").grid(row=6, column=0)
    v_var = tk.StringVar(value=settings.get("TitleAlignV", "top"))
    ttk.Combobox(dialog, textvariable=v_var, values=["top", "center", "bottom"]).grid(row=6, column=1)

    # 水平位置
    tk.Label(dialog, text="横位置:").grid(row=7, column=0)
    h_align_var = tk.StringVar(value=settings.get("TitleAlignH", "center"))
    ttk.Combobox(dialog, textvariable=h_align_var, values=["left", "center", "right"]).grid(row=7, column=1)

    # 保存
    def save_settings_and_close():
        settings["TitleFont"] = title_font_var.get()
        settings["TitleFontSize"] = title_font_size_var.get()
        settings["TitleAreaX"] = x_var.get()
        settings["TitleAreaY"] = y_var.get()
        settings["TitleAreaWidth"] = w_var.get()
        settings["TitleAreaHeight"] = h_var.get()
        settings["TitleAlignV"] = v_var.get()
        settings["TitleAlignH"] = h_align_var.get()
        # フォントやサイズもあればここで
        save_settings()  # 保存関数呼ぶ
        dialog.destroy()
    tk.Button(dialog, text="保存", command=save_settings_and_close).grid(row=8, column=0, columnspan=2)

# 字幕の焼き直し
def clip_reburn_gui():
    # 元MP4
    mp4_path = filedialog.askopenfilename(
        title="焼き直すMP4ファイルを選択",
        filetypes=[("MP4ファイル", "*.mp4")]
    )
    if not mp4_path:
        print("❌ MP4ファイルが選択されませんでした")
        return

    # 字幕
    srt_path = filedialog.askopenfilename(
        title="対応するSRT字幕ファイルを選択",
        filetypes=[("字幕ファイル", "*.srt *.ass")]
    )
    if not srt_path:
        print("❌ 字幕ファイルが選択されませんでした")
        return

    # 弾幕mp4
    danmaku_path = filedialog.askopenfilename(
        title="重ねる弾幕動画（danmaku.mp4）を選択",
        filetypes=[("MP4ファイル", "*.mp4")]
    )
    if not danmaku_path:
        print("❌ 弾幕動画が選択されませんでした")
        return

    # 出力名決定
    out = Path(mp4_path).with_name(Path(mp4_path).stem + "_subtitled_danmaku.mp4")

    try:
        generate_video(
            danmaku_video=Path(danmaku_path),
            srt_path=Path(srt_path),
            output_path=out
        )
        messagebox.showinfo("完了", f"字幕＋弾幕の焼き直しが完了しました！\n出力: {out.name}")
    except Exception as e:
        messagebox.showerror("エラー", f"字幕＋弾幕焼き直しに失敗しました:\n{e}")

# 字幕生成のフィルター設定を生成
def generate_subtitle_filter(srt_path: Path) -> str:
    s = settings
    font_name = s["Font"]
    style_str = (
        f"FontName={escape_font_name(font_name)},"
        f"FontSize={s['FontSize']},"
        f"PrimaryColor={s['PrimaryColor']},"
        f"Outline={s['Outline']},"
        f"OutlineColor={s['OutlineColor']},"
        f"Shadow={s['Shadow']},"
        f"MarginV={s['MarginV']},"
        f"Alignment={s['Alignment']}"
    )
    
    srt_path_escaped = escape_ffmpeg_path(srt_path)
    font_path = CUSTOM_FONT_PATHS.get(font_name)
    if font_path:
        fontsdir_escaped = escape_ffmpeg_path(Path(font_path).parent)
        return f"subtitles='{srt_path_escaped}:fontsdir={fontsdir_escaped}:force_style={style_str}'"
    else:
        return f"subtitles='{srt_path_escaped}:force_style={style_str}'"

# 設定保存関数
def save_settings():
    try:
        SETTINGS_FILE_DIR.parent.mkdir(parents=True, exist_ok=True)
        with open(resource_path(SETTINGS_FILE_DIR), "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        print("✅ 設定を保存しました")
    except Exception as e:
        print(f"❌ 設定の保存に失敗: {e}")

# wavファイルに変換(音データ取得のため)
def convert_to_wav(input_file, wav_file):
    cmd = [
        "ffmpeg", "-y", "-i", input_file,
        "-ac", "1",
        "-ar", "44100",
        wav_file
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def extract_rms_numpy(wav_file):
    audio, samplerate = sf.read(wav_file)
    duration = len(audio) / samplerate
    rms_values = []
    for i in range(int(duration)):
        start = i * samplerate
        end = (i + 1) * samplerate
        rms = np.sqrt(np.mean(audio[start:end] ** 2))
        rms_db = 20 * np.log10(rms) if rms > 0 else -100
        rms_values.append(rms_db)
    return rms_values

##### クリップ #####
def generate_clips_from_folder(app: App):
        """
        セグメント動画フォルダ指定してクリップ動画を生成する
        """
        segment_dir_path = filedialog.askdirectory(title="セグメントフォルダを選択")
        if not segment_dir_path:
            print("⚠️ セグメントフォルダが選択されませんでした。処理を中止します。")
            return
        
        if update_paths_from_url(app) == False:
            return
    
        def run():
            print(f"📁 フォルダ選択でクリップ動画の生成を開始します・・・: {segment_dir_path}")
            for segment_file_path in Path(segment_dir_path).glob("segment_*.mp4"):
                generate_clips(segment_file_path, app)
            app.root.after(0, lambda: messagebox.showinfo("完了", "フォルダ指定のクリップ動画生成が完了しました"))
    
        threading.Thread(target=run).start()

def generate_clips_from_file(app: App):
    """
    セグメント動画ファイル指定してクリップ動画を生成する
    """
    segment_file_path = filedialog.askopenfilename(filetypes=[("MP4 Files", "*.mp4")])
    if not segment_file_path:
        print("⚠️ ファイルが選択されませんでした。処理を中止します。")
        return
    
    if update_paths_from_url(app) == False:
        return
    
    def run():
        print(f"🎬 ファイル選択でクリップ動画の生成を開始します・・・: {segment_file_path}")
        generate_clips(Path(segment_file_path), app)
        app.root.after(0, lambda: messagebox.showinfo("完了", "ファイル指定のクリップ動画生成が完了しました"))
    threading.Thread(target=run).start()
    
def generate_clips(segment_path: Path, app: App):
    """
    指定セグメント動画からクリップ動画生成する
    Args:
        segment_path (Path): クリップ元となるセグメント動画のファイルパス
    """
    print(f"🎬 クリップ動画生成開始・・・: {segment_path.name}")
    try:
        # ▼ segment_info.json 参照
        segment_info_path = SEGMENT_DIR / "segment_info.json"
        if not segment_info_path.exists():
            print(f"❌ segment_info.json が見つかりません: {segment_info_path}")
            return

        with open(segment_info_path, "r", encoding="utf-8") as f:
            segment_meta = json.load(f)
        # segment_path.name と一致する情報を得る
        my_info = next((item for item in segment_meta if item["file"] == segment_path.name), None)
        if my_info is None:
            print(f"❌ {segment_path.name} の開始・終了秒情報が segment_info.json に見つかりません")
            return

        segment_start_time = my_info["start_sec"]
        segment_end_time = my_info["end_sec"]
        print(f"🔗 このセグメントは元配信の {segment_start_time}s ~ {segment_end_time}s 区間です")

        # --- 以降は従来どおり ---
        result = whisper_model.transcribe(str(segment_path), language="ja", task="transcribe")
        segments = result["segments"]
        print(f"📝 字幕セグメント数: {len(segments)}")
        clips = group_segments_by_duration(segments, MIN_DURATION, MAX_DURATION)
        print(f"📌 抽出されたクリップ数: {len(clips)}")
        output_dir = OUTPUT_BASE_DIR / segment_path.stem
        output_dir.mkdir(parents=True, exist_ok=True)
        
        stream_title = app.stream_analysis.safe_title
        if not stream_title:
            print("❌ stream_titleが空です。動画分析またはURL入力を先に実行してください。")
            return
        chat_json_path = BASE_DIR / "output" / f"{stream_title}_chat.json"
        
        for i, clip in enumerate(clips):
            print(f"🔧 クリップ生成: clip_{i} [{clip.start_time:.2f}s - {clip.end_time:.2f}s]")
            # ここで segment_start_time を使えば「配信全体での絶対秒数」も計算できる
            # 例: clip_abs_start = segment_start_time + clip.start_time
            export_clip(i, clip, segment_path, output_dir, chat_json_path)
    except Exception as e:
        print(f"❌ ファイル {segment_path.name} の処理に失敗しました: {e}")
    print("✅ クリップ動画生成が完了しました")
    
def update_paths_from_url(app: App):
    # アプリケーションが存在しないなら終了
    if app is None:
        return False
        
    
    url_input = app.entry.get().strip()
    if not url_input:
        messagebox.showwarning("URL未入力", "YouTubeのURLを入力してください")
        return False
    normalized_url = normalize_youtube_url(url_input)
    app.stream_analysis.video_url = normalized_url
    result = subprocess.run([
        "python", "-m", "yt_dlp", "--get-title", normalized_url
    ], capture_output=True, text=True, shell=True, encoding="utf-8", errors="replace")
    title = result.stdout.strip()
    if result.returncode != 0 or not title:
        messagebox.showerror("エラー", "動画タイトルが取得できませんでした")
        return False
    app.stream_analysis.raw_title = title
    app.stream_analysis.safe_title = re.sub(r'[\\/*?:"<>|]', "_", title)
    output_dir = BASE_DIR / "output"
    output_dir.mkdir(exist_ok=True)
    app.stream_analysis.chat_file = str(output_dir / f"{app.stream_analysis.safe_title}_chat.json")
    app.stream_analysis.video_file = str(output_dir / f"{app.stream_analysis.safe_title}.mp4")
    return True

def download_chat(app: App):
    # アプリケーションが存在しないなら終了
    if app is None:
        return
    if not update_paths_from_url(app):
        return
    if os.path.exists(app.stream_analysis.chat_file):
        messagebox.showinfo("情報", "チャットファイルは既に存在します。")
        return
    
    print("チャットデータダウンロード開始・・・", flush=True)
    subprocess.run([
        "python", "-m", "chat_downloader", app.stream_analysis.video_url,
        "--output", app.stream_analysis.chat_file
    ])
    print("チャットデータダウンロード終了")
    messagebox.showinfo("完了", "チャットダウンロード完了！")

def download_video(app: App):
    # アプリケーションが存在しないなら終了
    if app is None:
        return
    if not update_paths_from_url(app):
        return
    # 🔹 保存先フォルダを選択（ファイル名は自動決定）
    save_dir = filedialog.askdirectory(title="保存先フォルダを選択してください")
    if not save_dir:
        print("⚠️ 保存がキャンセルされました。")
        return
    
    print("動画ダウンロード開始・・・")
    save_dir = Path(save_dir)
    # 🔸 ユーザー設定解像度
    resolution = settings.get("Resolution", "1920x1080")
    target_width, target_height = map(int, resolution.lower().split("x"))
    # 🔸 保存ファイル名（元タイトルベース）
    base_name = app.stream_analysis.safe_title
    base_output = save_dir / f"{base_name}_1920x1080.mp4"
    final_output = save_dir / f"{base_name}_{target_width}x{target_height}.mp4"
    print("動画(1920x1080)ダウンロード中・・・")
    # 🔹 yt-dlpで 1920x1080 ダウンロード
    subprocess.run([
        "yt-dlp",
        "--force-overwrites",
        "-f", "137+140",
        "--merge-output-format", "mp4",
        "-o", str(base_output),
        app.stream_analysis.video_url
    ], check=True)
    print(f"✅ 動画(1920x1080)をダウンロード完了: {base_output.name}")
    # 🔹 ユーザー指定が1920x1080なら変換不要
    if resolution == "1920x1080":
        app.stream_analysis.video_file = str(base_output)
        messagebox.showinfo("完了", f"動画取得完了: {base_output.name}")
        return
    # 🔹 アスペクト比維持＋黒帯で中央寄せ
    vf_filter = (
        f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease," 
        f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2"
    )
    print(f"動画(1920x1080)を使って{resolution}に編集中・・・")
    subprocess.run([
        "ffmpeg", "-y",
        "-i", str(base_output),
        "-vf", vf_filter,
        "-c:v", "h264_nvenc",
        "-c:a", "copy",
        str(final_output)
    ], check=True)
    print(f"動画({resolution})編集終了")
    print(f"✅ {resolution} 動画をダウンロード完了: {base_output.name}")
    app.stream_analysis.video_file = str(final_output)
    messagebox.showinfo("完了", f"動画取得完了: {final_output.name}")

def analyze_and_plot(app: App) -> threading.Thread:
    # アプリケーションが存在しないなら終了
    if app is None:
        return
    
    def analyze():
        if not update_paths_from_url(app):
            return
        if not os.path.exists(app.stream_analysis.chat_file):
            messagebox.showwarning("警告", "チャットファイルが存在しません。")
            return
        
        # 🎥 分析する動画ファイルを選択
        video_file = filedialog.askopenfilename(
            title="情報分析に使う動画ファイルを選択",
            filetypes=[("MP4 Files", "*.mp4")]
        )
        
        if not video_file:
            print(f"⚠️ 分析の為の動画選択がキャンセルされました。: {video_file}")
            return
        
        print("分析を開始・・・")
        
        print("チャットデータを読み込み")
        with open(app.stream_analysis.chat_file, "r", encoding="utf-8") as f:
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
        app.stream_analysis.x = x
        app.stream_analysis.y = y
        app.stream_analysis.x_labels = x_labels
        app.stream_analysis.valleys = valleys
        app.stream_analysis.peaks = peaks
        print("チャットデータを読み込み終了")
        print("動画音量(RMS)データを抽出中")
        # --- 音量（RMS）データ抽出 ---
        wav_file = "temp_audio.wav"
        
        convert_to_wav(video_file, wav_file)
        rms_values = extract_rms_numpy(wav_file)
        os.remove(wav_file)  # 一時ファイル削除
        
        # X軸は1秒ごと（動画の長さ秒分）
        audio_x = np.arange(len(rms_values))
        app.stream_analysis.audio_x = audio_x
        app.stream_analysis.audio_y = rms_values
        print("動画音量(RMS)データを抽出終了")
        
        app.root.after(0, draw_graph)
    def draw_graph():
        print("グラフ表示開始・・・")
        plt.figure(figsize=(12, 5))
    
        # ① チャット数（5分毎, X軸は時:分ラベル）
        plt.plot(app.stream_analysis.x, app.stream_analysis.y, label="チャット数", color="blue")
        for i in range(1, len(app.stream_analysis.y) - 1):
            if app.stream_analysis.x[i] in app.stream_analysis.valleys:
                plt.plot(app.stream_analysis.x[i], app.stream_analysis.y[i], 'ro')
            elif app.stream_analysis.x[i] in app.stream_analysis.peaks:
                plt.plot(app.stream_analysis.x[i], app.stream_analysis.y[i], 'bo')
    
        # ② 音量RMS（1秒毎, X軸は「秒」→ラベル位置にあわせて右側の軸にプロット）
        if hasattr(app.stream_analysis, "audio_y") and app.stream_analysis.audio_y:
            audio_x = app.stream_analysis.audio_x  # 1秒単位 [0,1,2,...]
            audio_y = app.stream_analysis.audio_y  # RMS(dB)
            ax1 = plt.gca()
            ax2 = ax1.twinx()  # 右Y軸
            ax2.plot(audio_x, audio_y, color="orange", alpha=0.5, label="音量(RMS dB)")
            ax2.set_ylabel("音量（dB, 1秒毎）", fontname="Yu Gothic")
    
        plt.xticks(app.stream_analysis.x, app.stream_analysis.x_labels)
        plt.xlabel("動画時間（時:分）")
        plt.ylabel("チャット数（5分単位）", fontname="Yu Gothic")
        plt.title(app.stream_analysis.raw_title, fontname="Yu Gothic")
        plt.grid()
        plt.legend(loc="upper left")
        plt.tight_layout()
        plt.show()
    t = threading.Thread(target=analyze)
    t.start()
    return t  # スレッドオブジェクトを返す

def generate_segments(app: App):
    # アプリケーションが存在しないなら終了
    if app is None:
        return
    
    if not app.stream_analysis.valleys or not app.stream_analysis.peaks:
        print("分析を行っていなかったので分析処理を実行します。")
        thread = analyze_and_plot(app)
        thread.join() # 終わるまで待機

    video_file = filedialog.askopenfilename(
        title="セグメント生成に使う動画ファイルを選択",
        filetypes=[("MP4 Files", "*.mp4")]
    )
    if not video_file:
        print("⚠️ 動画ファイルが選択されませんでした。処理を中止します。")
        return
    
    print("セグメント生成開始・・・")
    SEGMENT_DIR.mkdir(parents=True, exist_ok=True)
    BUFFER = 300
    segment_count = 1
    segment_meta = []

    # ▼ valley-peakペアで各セグメント動画生成＋区間情報記録
    pairs = extract_valley_peak_pairs(app.stream_analysis.valleys, app.stream_analysis.peaks)
    for start_valley, peak in pairs:
        start = max(0, start_valley - BUFFER)
        end = peak + BUFFER
        duration = end - start
        segment_path = SEGMENT_DIR / f"segment_{segment_count:02}.mp4"
        subprocess.run([
            "ffmpeg", "-ss", str(timedelta(seconds=start)),
            "-i", video_file,
            "-t", str(timedelta(seconds=duration)),
            "-c", "copy", str(segment_path)
        ])
        segment_meta.append({
            "segment_index": segment_count,
            "file": f"segment_{segment_count:02}.mp4",
            "start_sec": int(start),
            "end_sec": int(end)
        })
        segment_count += 1

    # ▼ segment_info.json 保存
    with open(SEGMENT_DIR / "segment_info.json", "w", encoding="utf-8") as f:
        json.dump(segment_meta, f, ensure_ascii=False, indent=2)
    messagebox.showinfo("完了", f"セグメント生成が完了しました！\n保存先: {SEGMENT_DIR}")
    
def extract_valley_peak_pairs(valleys, peaks):
    # 時間順に並んだ山谷をまとめる
    points = []
    for t in valleys:
        points.append(("valley", t))
    for t in peaks:
        points.append(("peak", t))
    points.sort(key=lambda x: x[1])  # 時間でソート
    pairs = []
    prev_valley = None
    for kind, t in points:
        if kind == "valley":
            prev_valley = t
        elif kind == "peak" and prev_valley is not None and t > prev_valley:
            pairs.append((prev_valley, t))
            prev_valley = None  # 次のvalleyまで待つ
    return pairs

def get_text_size(text, font):
    if hasattr(font, "getbbox"):
        bbox = font.getbbox(text)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        return width, height
    else:
        return font.getsize(text)

def wrap_title_text(text, font, max_width):
    """
    1行の横幅がmax_widthを超えないよう自動改行した行リストを返す
    """
    lines = []
    line = ""
    for char in text:
        test_line = line + char
        w, _ = get_text_size(test_line, font)
        if w > max_width and line:
            lines.append(line)
            line = char
        else:
            line = test_line
    if line:
        lines.append(line)
    return lines

def calc_title_position(app: App,img, lines, font, settings):
    """
    settings: TitleAreaX, TitleAreaY, TitleAreaWidth, TitleAreaHeight, TitleAlignV, TitleAlignH
    lines: wrap_textで作成した行リスト
    """
    # アプリケーションが存在しないなら終了
    if app is None:
        return
    x0 = settings.get("TitleAreaX", 0)
    y0 = settings.get("TitleAreaY", 0)
    area_w = settings.get("TitleAreaWidth", img.width)
    area_h = settings.get("TitleAreaHeight", img.height // 3)
    align_v = settings.get("TitleAlignV", "top")
    align_h = settings.get("TitleAlignH", "center")
    # 1行の高さ
    _, line_h = get_text_size("あ", font)
    total_h = line_h * len(lines)
    # 垂直位置
    if align_v == "top":
        y = y0
    elif align_v == "center":
        y = y0 + (area_h - total_h) // 2
    elif align_v == "bottom":
        y = y0 + (area_h - total_h)
    else:
        y = y0
    return x0, y, area_w, align_h, line_h

def draw_title_on_img(app: App, img, title, font, settings):
    # アプリケーションが存在しないなら終了
    if app is None:
        return
    draw = ImageDraw.Draw(img)
    area_w = settings.get("TitleAreaWidth", img.width)
    # ラップ
    lines = wrap_title_text(title, font, area_w)
    # 位置
    x0, y, area_w, align_h, line_h = calc_title_position(app, img, lines, font, settings)
    for line in lines:
        text_w, _ = get_text_size(line, font)
        # 水平
        if align_h == "left":
            x = x0
        elif align_h == "center":
            x = x0 + (area_w - text_w) // 2
        elif align_h == "right":
            x = x0 + (area_w - text_w)
        else:
            x = x0
        # 影
        draw.text((x+2, y+2), line, font=font, fill=(0,0,0,128))
        # 本体
        draw.text((x, y), line, font=font, fill=(255,255,255,255))
        y += line_h
    return img

def generate_all_thumbnails_gui(app: App):
    # アプリケーションが存在しないなら終了
    if app is None:
        return
    
    mp4_path = filedialog.askopenfilename(
        title="サムネイル生成する元動画ファイルを選択",
        filetypes=[("MP4ファイル", "*.mp4")]
    )
    if not mp4_path:
        print("❌ 動画ファイルが選択されませんでした")
        return
    # ▼ サムネイル題名スタイル設定の取得（なければデフォルト）
    title_font_name = settings.get("TitleFont", "Yu Gothic")
    title_font_size = settings.get("TitleFontSize", 120)
    area_x = settings.get("TitleAreaX", 0)
    area_y = settings.get("TitleAreaY", 0)
    area_w = settings.get("TitleAreaWidth")
    area_h = settings.get("TitleAreaHeight")
    align_v = settings.get("TitleAlignV", "top")    # "top", "center", "bottom"
    align_h = settings.get("TitleAlignH", "center") # "left", "center", "right"
    font_path = CUSTOM_FONT_PATHS.get(title_font_name)
    video_path = Path(mp4_path)
    valleys = app.stream_analysis.valleys
    peaks = app.stream_analysis.peaks
    audio_y = app.stream_analysis.audio_y
    title = app.stream_analysis.raw_title or video_path.stem
    if not valleys or not peaks or not audio_y:
        messagebox.showerror("エラー", "グラフ分析データがありません（まず「分析してグラフを表示」を実行してください）")
        return
    # output/thumbnail フォルダ作成
    thumbnail_dir = BASE_DIR / "output" / "thumbnail"
    thumbnail_dir.mkdir(parents=True, exist_ok=True)
    pairs = extract_valley_peak_pairs(valleys, peaks)
    for idx, (start_sec, end_sec) in enumerate(pairs, 1):  # 1から開始
        if end_sec > len(audio_y):
            print(f"⚠️ 区間{idx}: end_sec={end_sec}が音量データ範囲外です。スキップ")
            continue
        segment_rms = audio_y[start_sec:end_sec+1]
        if not segment_rms:
            print(f"⚠️ 区間{idx}: 区間内音量データなし。スキップ")
            continue
        rel_max_idx = int(np.argmax(segment_rms))
        abs_max_sec = start_sec + rel_max_idx
        # サムネイルファイル名例: 元動画名_segment01_thumbnail.jpg
        base_name = f"{video_path.stem}_segment{idx:02}_thumbnail"
        thumbnail_base_pattern = thumbnail_dir / (base_name + "_base_%d.jpg")  # ffmpeg出力パターン
        thumbnail_base_file = thumbnail_dir / (base_name + "_base_1.jpg")      # 実際の出力ファイル
        output_thumbnail = thumbnail_dir / (base_name + ".jpg")
        try:
            subprocess.run([
                "ffmpeg", "-y",
                "-ss", str(abs_max_sec),
                "-i", str(video_path),
                "-frames:v", "1",
                "-q:v", "2",
                str(thumbnail_base_pattern)
            ], check=True)
            img = Image.open(thumbnail_base_file)
            # フォントインスタンス作成
            try:
                if font_path:
                    font = ImageFont.truetype(font_path, title_font_size)
                else:
                    font = ImageFont.truetype("arial.ttf", title_font_size)
            except Exception:
                font = ImageFont.load_default()
            # 描画エリア
            use_area_w = area_w if area_w else img.width
            use_area_h = area_h if area_h else img.height // 3
            # 設定まとめ
            settings_for_pos = {
                "TitleAreaX": area_x,
                "TitleAreaY": area_y,
                "TitleAreaWidth": use_area_w,
                "TitleAreaHeight": use_area_h,
                "TitleAlignV": align_v,
                "TitleAlignH": align_h,
            }
            
            img = draw_title_on_img(app, img, title, font, settings_for_pos)
            img.save(output_thumbnail)
            thumbnail_base_file.unlink(missing_ok=True)
            print(f"✅ サムネイル生成: {output_thumbnail}")
        except Exception as e:
            print(f"❌ サムネイル生成失敗: segment{idx} {e}")
    messagebox.showinfo("完了", f"すべてのサムネイル画像を\noutput/thumbnail/\nに保存しました。")

def main():
    global CUSTOM_FONT_PATHS, AVAILABLE_FONTS
    
    # 使用時にセット
    openai.api_key = load_api_key_from_file()
    
    # 設定情報読み込み
    if SETTINGS_FILE_DIR.exists():
        try:
            with open(SETTINGS_FILE_DIR, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                settings.update(loaded)
                print("✅ 設定ファイルから読み込みました")
        except Exception as e:
            print(f"⚠️ 設定ファイルの読み込みに失敗: {e}")
    
    CUSTOM_FONT_PATHS = scan_custom_fonts()
    AVAILABLE_FONTS += [f for f in CUSTOM_FONT_PATHS if f not in AVAILABLE_FONTS]
    
    app = App()
    app.setup("VigStreamClip")

    # アプリケーションの実行処理
    app.run()

if __name__ == "__main__":
    main()