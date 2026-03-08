import os
import subprocess
import json
import re
from collections import defaultdict
import threading
import urllib.parse
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
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
from fontTools.ttLib import TTFont
import sys
import logging
from tkinter.scrolledtext import ScrolledText
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont
import tempfile
import traceback
import copy
from shutil import which
import http.cookiejar
from yt_chat_downloader import YouTubeChatDownloader
from io import BytesIO
import urllib.request
import queue
import time
import math
import shutil

# GPUプレビュー（OpenGL）
try:
    from pyopengltk import OpenGLFrame
    from OpenGL.GL import *
    from OpenGL.GLU import *
    from OpenGL.error import GLError
    GPU_PREVIEW_AVAILABLE = True
except Exception:
    GPU_PREVIEW_AVAILABLE = False

# 基本ディレクトリ取得
def get_base_dir():
    if getattr(sys, 'frozen', False):
        # PyInstaller でビルドされた .exe を実行中
        return Path(sys.executable).parent.parent
    else:
        # 通常のスクリプト実行
        return Path(__file__).resolve().parent.parent

# exe実行でUTF-8の使用を強制
os.environ["PYTHONUTF8"] = "1"
# matplotlibで使うフォント指定
plt.rcParams["font.family"] = "Noto Sans JP"

BASE_DIR_PATH = get_base_dir()
MODEL_DIR_PATH = BASE_DIR_PATH / "models"
FONT_DIR_PATH = BASE_DIR_PATH / "fonts"
LIB_DIR_PATH = BASE_DIR_PATH / "libs"
RES_DIR_PATH = BASE_DIR_PATH / "res"
FFMPEG_PATH = LIB_DIR_PATH / "ffmpeg.exe"
FFPROBE_PATH = LIB_DIR_PATH / "ffprobe.exe"
YTDLP_PATH = LIB_DIR_PATH / "yt-dlp.exe"
MIN_DURATION = 60
MAX_DURATION = 180

# ffmpeg/ffprobe の実行パスを追加
os.environ["PATH"] = str(LIB_DIR_PATH) + os.pathsep + os.environ.get("PATH", "")
# pydubにffmpeg.exeの実行パスを追加
from pydub import AudioSegment, silence, utils
AudioSegment.converter = str(FFMPEG_PATH)
utils.get_encoder_name = lambda: str(AudioSegment.converter)
#print(f"[DEBUG] ffmpeg_path = {ffmpeg_path}")
#print(f"[DEBUG] ffmpeg.exe exists? {ffmpeg_path.exists()}")
#print(f"[DEBUG] shutil.which('ffmpeg') = {which('ffmpeg')}")

# カスタムフォントパス
CUSTOM_FONT_PATHS = {}
# 使用可能なフォント一覧
AVAILABLE_FONTS = [
    "Noto Sans",
    "Noto Sans Black",
    "Noto Sans Condensed",
    "Noto Sans Condensed Black",
    "Noto Sans Condensed ExtraBold",
    "Noto Sans Condensed ExtraLight",
    "Noto Sans Condensed Light",
    "Noto Sans Condensed Medium",
    "Noto Sans Condensed SemiBold",
    "Noto Sans Condensed Thin",
    "Noto Sans ExtraBold",
    "Noto Sans ExtraCondensed",
    "Noto Sans ExtraCondensed Black",
    "Noto Sans ExtraCondensed ExtraBold",
    "Noto Sans ExtraCondensed ExtraLight",
    "Noto Sans ExtraCondensed Light",
    "Noto Sans ExtraCondensed Medium",
    "Noto Sans ExtraCondensed SemiBold",
    "Noto Sans ExtraCondensed Thin",
    "Noto Sans ExtraLight",
    "Noto Sans JP",
    "Noto Sans JP Black",
    "Noto Sans JP ExtraBold",
    "Noto Sans JP ExtraLight",
    "Noto Sans JP Light",
    "Noto Sans JP Medium",
    "Noto Sans JP SemiBold",
    "Noto Sans JP Thin",
    "Noto Sans Light",
    "Noto Sans Medium",
    "Noto Sans SemiBold",
    "Noto Sans SemiCondensed",
    "Noto Sans SemiCondensed Black",
    "Noto Sans SemiCondensed ExtraBold",
    "Noto Sans SemiCondensed ExtraLight",
    "Noto Sans SemiCondensed Light",
    "Noto Sans SemiCondensed Medium",
    "Noto Sans SemiCondensed SemiBold",
    "Noto Sans SemiCondensed Thin",
    "Noto Sans Thin",
    "Noto Serif",
    "Noto Serif Black",
    "Noto Serif Condensed",
    "Noto Serif Condensed Black",
    "Noto Serif Condensed ExtraBold",
    "Noto Serif Condensed ExtraLight",
    "Noto Serif Condensed Light",
    "Noto Serif Condensed Medium",
    "Noto Serif Condensed SemiBold",
    "Noto Serif Condensed Thin",
    "Noto Serif ExtraBold",
    "Noto Serif ExtraCondensed",
    "Noto Serif ExtraCondensed Black",
    "Noto Serif ExtraCondensed ExtraBold",
    "Noto Serif ExtraCondensed ExtraLight",
    "Noto Serif ExtraCondensed Light",
    "Noto Serif ExtraCondensed Medium",
    "Noto Serif ExtraCondensed SemiBold",
    "Noto Serif ExtraCondensed Thin",
    "Noto Serif ExtraLight",
    "Noto Serif Light",
    "Noto Serif Medium",
    "Noto Serif SemiBold",
    "Noto Serif SemiCondensed",
    "Noto Serif SemiCondensed Black",
    "Noto Serif SemiCondensed ExtraBold",
    "Noto Serif SemiCondensed ExtraLight",
    "Noto Serif SemiCondensed Light",
    "Noto Serif SemiCondensed Medium",
    "Noto Serif SemiCondensed SemiBold",
    "Noto Serif SemiCondensed Thin",
    "Noto Serif Thin",
    "Source Sans 3",
    "Source Sans 3 Black",
    "Source Sans 3 ExtraBold",
    "Source Sans 3 ExtraLight",
    "Source Sans 3 Light",
    "Source Sans 3 Medium",
    "Source Sans 3 SemiBold",
    "Tanuki Permanent Marker",
]

# フォントごとの横幅係数（1pt あたり何 px を占有するか）
FONT_WIDTH_RATIO = {
    "Noto Sans JP": 3.94,
}

# デバッグ出力(Tkinterの方のログをVScodeでも確認できるようにするため)
class DualWriter:
    def __init__(self, *writers):
        self.writers = writers
    def write(self, msg):
        for w in self.writers:
            try:
                w.write(msg)
                w.flush()
            except Exception:
                pass
    def flush(self):
        for w in self.writers:
            try:
                w.flush()
            except Exception:
                pass

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
    locked: bool = False  # キュー登録時に確定したURL/タイトル/パスを再利用するためのロック

# ジョブ型
@dataclass(slots=True)
class OneClickJob:
    id: int
    sa: StreamAnalysis              # URL等ロック用
    settings_snapshot: dict         # ← 追加：登録時の設定スナップショット
    project_dir: str | None = None  # ← 追加：登録時に開いていたプロジェクトの絶対パス
    status: str = "QUEUED"          # QUEUED / RUNNING / DONE / ERROR

# アプリデータ
class App:
    class FileManager:
        def __init__(self, app: "App", base_dir: "Path"):
            self.app = app
            self.base_dir = Path(base_dir)
            self.files_dir = self.base_dir / "projects"
            self.files_dir.mkdir(exist_ok=True)
            self._project_file_path: Path = None

        @property
        def project_file_path(self):
            return self._project_file_path

        def list_files(self):
            return [p.name for p in self.files_dir.iterdir() if p.is_dir()]

        def create_file(self, name, settings=None):
            file_dir = self.files_dir / name
            file_dir.mkdir(parents=True, exist_ok=True)
            self._project_file_path = file_dir

            # 必要なサブフォルダ
            (file_dir / "res").mkdir(exist_ok=True)

            # res/settings.txt だけ初期化
            if settings is not None:
                setting_txt_file = file_dir / "res" / "settings.txt"
                with open(setting_txt_file, "w", encoding="utf-8") as f:
                    json.dump(settings, f, ensure_ascii=False, indent=2)

            return file_dir

        def select_file(self, name):
            file_dir = self.files_dir / name
            if file_dir.exists():
                self._project_file_path = file_dir
                return True
            return False

        def delete_file(self, name):
            file_dir = self.files_dir / name
            if file_dir.exists():
                import shutil
                shutil.rmtree(file_dir)
                if self._project_file_path == file_dir:
                    self._project_file_path = None
                return True
            return False

        @property
        def font_dir_path(self):
            path: Path = None
            if self.app.current_job is not None:
                path = Path(self.app.current_job.project_dir) / "fonts"
            elif not self._project_file_path:
                path = BASE_DIR_PATH / "fonts"
            else:
                path = self._project_file_path / "fonts"
            return path

        def segment_dir_path(self, title_name):
            # ✨ title_name が空なら即エラー（None を返さない）
            if not title_name:
                raise RuntimeError("title_name が未確定です。update_paths_from_url() を先に実行してください。")
            
            path: Path = None
            if self.app.current_job is not None:
                path = Path(self.app.current_job.project_dir) / "output" / title_name / "segments"
            elif not self._project_file_path:
                path = BASE_DIR_PATH / "output" / title_name / "segments"
            else:
                path = self._project_file_path / "output" / title_name / "segments"
            return path

        def output_dir_path(self, title_name):
            # ✨ title_name が空なら即エラー（None を返さない）
            if not title_name:
                raise RuntimeError("title_name が未確定です。update_paths_from_url() を先に実行してください。")
            
            path: Path = None
            if self.app.current_job is not None:
                path = Path(self.app.current_job.project_dir) / "output" / title_name
            elif not self._project_file_path:
                path = BASE_DIR_PATH / "output" / title_name
            else:
                path = self._project_file_path / "output" / title_name
            return path

        @property
        def settings_file_path(self):
            if self.app.current_job is not None:
                path = Path(self.app.current_job.project_dir) / "res" / "settings.txt"
            elif not self._project_file_path:
                path = BASE_DIR_PATH / "res" / "settings.txt"
            else:
                path = self._project_file_path / "res" / "settings.txt"
            
            return path

        def load_file_settings(self, settings: dict):
            path = self.settings_file_path
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    settings.clear()
                    settings.update(json.load(f))
                    print(f"✅ ファイルごとの設定を読み込みました: {path}")

        def save_file_settings(self, settings: dict):
            path = self.settings_file_path
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            print(f"✅ ファイルごとの設定を保存しました: {path}")
        
        def load_analysis_results(self, stream_analysis):
            def_output_dir = BASE_DIR_PATH / "output"
            def_in_file = def_output_dir / "analysis.json"

            # デフォルトの分析結果があれば読み込む
            if def_in_file.exists():
                with open(def_in_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                stream_analysis.x = data.get("x", [])
                stream_analysis.y = data.get("y", [])
                stream_analysis.x_labels = data.get("x_labels", [])
                stream_analysis.valleys = data.get("valleys", [])
                stream_analysis.peaks = data.get("peaks", [])
                stream_analysis.audio_x = np.array(data.get("audio_x", []))
                stream_analysis.audio_y = data.get("audio_y", [])
                stream_analysis.raw_title = data.get("raw_title", "")
                stream_analysis.safe_title = data.get("safe_title", "")
                stream_analysis.video_url = data.get("video_url", "")

                print(f"✅ 分析結果を読み込みました: {def_in_file}")

             # 🔹 URLを入力欄に反映
            if hasattr(app, "entry") and stream_analysis.video_url:
                app.entry.delete(0, tk.END)
                app.entry.insert(0, stream_analysis.video_url)
                

        # App.FileManager 内
        def save_analysis_results(self, stream_analysis):
            # 既存のdata構築はそのまま
            data = {
                "x": stream_analysis.x,
                "y": stream_analysis.y,
                "x_labels": stream_analysis.x_labels,
                "valleys": stream_analysis.valleys,
                "peaks": stream_analysis.peaks,
                "audio_x": list(stream_analysis.audio_x),
                "audio_y": list(stream_analysis.audio_y),
                "raw_title": stream_analysis.raw_title,
                "safe_title": stream_analysis.safe_title,
                "video_url": stream_analysis.video_url,
            }

            # ① 共通のデフォルト保存（従来通り）
            def_output_dir = BASE_DIR_PATH / "output"
            def_output_dir.mkdir(parents=True, exist_ok=True)
            def_out_file = def_output_dir / "analysis.json"
            with open(def_out_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=conv_json_from_py)

            # ② “ジョブの出力ルート”へも保存（video_file を錨にする）
            job_root = None
            try:
                if stream_analysis.video_file:
                    job_root = Path(stream_analysis.video_file).parent
            except Exception:
                job_root = None

            # video_file がまだ無い場合は従来ロジックにフォールバック
            if job_root is None:
                job_root = (self.project_file_path or BASE_DIR_PATH) / "output" / stream_analysis.safe_title

            job_root.mkdir(parents=True, exist_ok=True)
            out_file = job_root / "analysis.json"
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=conv_json_from_py)

            print(f"✅ 分析結果を保存しました: {(def_out_file, out_file)}")
    
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
        self.name: str = ""
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
        self.file_manager = self.FileManager(self, BASE_DIR_PATH)
        self._project_file_path_name = None  # UI選択中ファイル名
        self.settings = settings  # 各ファイルごとの設定をこのdictに切り替え保存する
        self.is_oneclick_mode = False
        # キュー状態
        self.queue_items: list[OneClickJob] = []
        self.queue_lock = threading.Lock()
        self.queue_worker: threading.Thread | None = None
        self.job_seq = 0
        # 右ペインUI
        self.queue_tree: ttk.Treeview | None = None
        self.running_label: tk.Label | None = None
        # 実行中ジョブ
        self.current_job: OneClickJob | None = None
    
    def run(self):
        self.root.mainloop()
        
    def setup(self, app_name: str):
        self.name = app_name

        self.root.title(self.name)
        self.root.report_callback_exception = self.custom_callback_exception
        
        self.setup_gui()
        self.setup_logging_area()
        self.setup_logging_redirect()
        self.setup_menu()
    
    def setup_gui(self):
        # 左右2ペイン
        main = tk.Frame(self.root)
        main.pack(fill="both", expand=True)

        left = tk.Frame(main)
        left.pack(side="left", fill="both", expand=True)

        right = tk.Frame(main, width=360, padx=12, pady=12)
        right.pack(side="right", fill="y")

        # 上部URL入力（左）
        self.frame = tk.Frame(left, padx=20, pady=20)
        self.frame.pack()
        self.label = tk.Label(self.frame, text="YouTube動画URLを入力:")
        self.label.pack()
        self.entry = tk.Entry(self.frame, width=70)
        self.entry.pack(pady=5)

        # タブ（左）
        self.tabs = ttk.Notebook(left)
        self.tabs.pack(fill="both", expand=True, padx=20, pady=10)

        # === 1ページ目：ワンボタン ===
        self.page_quick = tk.Frame(self.tabs)
        self.tabs.add(self.page_quick, text="クリップ生成（自動一括）")

        tk.Button(
            self.page_quick,
            text="🚀 クリップ生成（ワンボタン）→ キュー登録",
            font=("Noto Sans JP", 16, "bold"),
            height=2,
            command=enqueue_current_url   # ← one_click_pipeline から差し替え
        ).pack(pady=12, fill="x")

        # === 2ページ目：従来のボタン群 ===
        self.page_detail = tk.Frame(self.tabs)
        self.tabs.add(self.page_detail, text="詳細操作")

        tk.Button(self.page_detail, text="🛰️ チャットを取得",
                  command=lambda: threading.Thread(target=download_chat).start()).pack(pady=5, fill="x")
        tk.Button(self.page_detail, text="🎬 動画を取得",
                  command=lambda: threading.Thread(target=download_video).start()).pack(pady=5, fill="x")
        tk.Button(self.page_detail, text="📊 分析してグラフを表示",
                  command=lambda: analyze_and_plot()).pack(pady=5, fill="x")
        tk.Button(self.page_detail, text="✂️ セグメント生成",
                  command=lambda: threading.Thread(target=generate_segments).start()).pack(pady=5, fill="x")
        tk.Button(self.page_detail, text="🎞️ Clip生成（フォルダ）",
                  command=lambda: threading.Thread(target=generate_clips_from_folder).start()).pack(pady=5, fill="x")
        tk.Button(self.page_detail, text="🎞️ Clip生成（ファイル）",
                  command=lambda: threading.Thread(target=generate_clips_from_file).start()).pack(pady=5, fill="x")
        tk.Button(self.page_detail, text="セグメントに字幕&弾幕追加",
                  command=lambda: threading.Thread(target=subtitle_and_danmaku_for_video_gui).start()).pack(pady=5, fill="x")
        tk.Button(self.page_detail, text="💬 弾幕追加（フル動画）",
                  command=add_danmaku_full_video_gui).pack(pady=5, fill="x")
        tk.Button(self.page_detail, text="🖼️ サムネイル生成",
                  command=lambda: threading.Thread(target=generate_all_thumbnails_gui).start()).pack(pady=5, fill="x")

        # ---- 右ペイン：キューUI ----
        tk.Label(right, text="ワンボタン処理キュー", font=("Noto Sans JP", 12, "bold")).pack(anchor="w")
        self.running_label = tk.Label(right, text="実行中: なし", anchor="w")
        self.running_label.pack(fill="x", pady=(4, 8))

        cols = ("id", "title", "status")
        self.queue_tree = ttk.Treeview(right, columns=cols, show="headings", height=18)
        for c, w in (("id", 50), ("title", 220), ("status", 70)):
            self.queue_tree.heading(c, text=c.upper())
            self.queue_tree.column(c, width=w, anchor="w")
        self.queue_tree.pack(fill="both", expand=True)

        btns = tk.Frame(right)
        btns.pack(fill="x", pady=8)
        tk.Button(btns, text="選択削除", command=remove_selected_queue_items).pack(side="left")
        tk.Button(btns, text="全クリア", command=clear_all_queue_items).pack(side="left", padx=6)
    
    def setup_menu(self):
        self.menubar = tk.Menu(self.root)
        self.root.config(menu=self.menubar)
        
        # メニュー項目
        #####ファイル#####
        file_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="ファイル", menu=file_menu)
        file_menu.add_command(label="新規ファイル", command=lambda: create_new_file())
        file_menu.add_command(label="ファイルを開く", command=lambda: open_file())
        file_menu.add_command(label="ファイルを削除", command=lambda: delete_file())

        #####設定#####
        setting_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="設定", menu=setting_menu)
        setting_menu.add_command(label="解像度", command=lambda: open_resolution_window())
        setting_menu.add_command(label="字幕", command=lambda: open_subtitle_style_window())
        setting_menu.add_command(label="サムネイル", command=lambda: open_title_style_dialog())
        setting_menu.add_command(label="弾幕", command=lambda: open_danmaku_style_window())
        setting_menu.add_command(label="クリップ", command=lambda: open_clip_setting_window())
        setting_menu.add_command(label="背景", command=lambda: open_background_style_window())
        setting_menu.add_separator()
        setting_menu.add_command(label="💾 設定を保存", command=lambda: (
            save_settings(),
            self.show_info_message("保存完了", "現在の設定を保存しました。")
        ))

        #####出力#####
        output_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="出力", menu=output_menu)
        output_menu.add_command(label="クリップ焼き直し(ファイル)", command=lambda: threading.Thread(target=clip_reburn_file_gui).start())
        output_menu.add_command(label="クリップ焼き直し(フォルダ)", command=lambda: threading.Thread(target=clip_reburn_folder_gui).start())
        
        #####出力#####
        preview_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="プレビュー", menu=preview_menu)
        preview_menu.add_command(label="色コード", command=lambda: open_color_code_preview())
        preview_menu.add_command(label="弾幕プレビュー(GPU)", command=lambda: threading.Thread(target=preview_danmaku_as_temp_video, daemon=True).start())
    
    def setup_logging_area(self):
        # ログ用ウィジェット作成
        self.log_frame = tk.Frame(self.root)
        self.log_frame.pack(side="bottom", fill="x")
        self.log_widget = ScrolledText(self.log_frame, state='disabled', height=10)
        self.log_widget.pack(fill="both", expand=True)

    def setup_logging_redirect(self):
        # stdout/stderr をGUIに
        # stdout/stderr をGUIとターミナルに二重出力
        dual_out = DualWriter(sys.__stdout__, App.StdoutRedirector(self.log_widget))
        dual_err = DualWriter(sys.__stderr__, App.StdoutRedirector(self.log_widget))
        sys.stdout = dual_out
        sys.stderr = dual_err

        self.text_handler = App.TextHandler(self.log_widget)
        self.text_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))

        self.console_handler = logging.StreamHandler(sys.__stdout__)
        self.console_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))

        logger = logging.getLogger()
        logger.setLevel(logging.WARNING)
        logger.addHandler(self.text_handler)
        logger.addHandler(self.console_handler)
    
    def update_window_title(self):
        # 現在のプロジェクト名があればタイトルに付加
        if self.project_file_path_name:
            self.root.title(f"{self.name} - [{self.project_file_path_name}]")
        else:
            self.root.title(self.name)
    
    # Tkinter例外をターミナルにも出す
    def custom_callback_exception(self, exc, val, tb):
        # GUIのログウィジェットとターミナルの両方に出す
        msg = ''.join(traceback.format_exception(exc, val, tb))
        try:
            self.log_widget.configure(state='normal')
            self.log_widget.insert('end', msg)
            self.log_widget.configure(state='disabled')
            self.log_widget.yview('end')
        except Exception:
            pass
        print(msg, file=sys.__stderr__)  # ターミナルにも
    
    # GUIにメッセージボックス表示
    def show_info_message(self, title, message):
        if self.is_oneclick_mode: return
        self.root.after(0, lambda: messagebox.showinfo(title, message))
    # GUIに警告メッセージボックス表示
    def show_warning_message(self, title, message):
        if self.is_oneclick_mode: return
        self.root.after(0, lambda: messagebox.showwarning(title, message))
    # GUIにエラーメッセージボックス表示
    def show_error_message(self, title, message):
        if self.is_oneclick_mode: return
        self.root.after(0, lambda: messagebox.showerror(title, message))

# 設定データ
settings = {
    # 解像度などの一般設定
    "Resolution": "1080x1920",          # 出力動画の解像度（横x縦）

    # 字幕スタイル
    "Font": "Noto Sans JP",             # 字幕に使用するフォント名
    "FontSize": 24,                     # 字幕のフォントサイズ（pt）
    "PrimaryColour": "FF000000",        # 字幕文字色（AARRGGBB形式）
    "Outline": 0.8,                     # 字幕の縁取りの太さ（px）
    "OutlineColour": "FFFFFFFF",        # 縁取りの色（AARRGGBB形式）
    "Shadow": 1.0,                      # 影の太さ（px）
    "MarginV": 80,                      # 字幕の下マージン（px）
    "Alignment": 2,                     # 字幕位置（1〜9, ASS形式の配置コード）1=左下 2=中央下 3=右下 4=左中央 5=中央中央 6=右中央 7=左上 8=中央上 9=右上

    # タイトルスタイル
    "TitleFont": "Noto Sans JP",        # サムネイルタイトルのフォント名
    "TitleFontSize": 120,               # タイトルのフォントサイズ（pt）
    "TitleAreaX": 0,                    # タイトル描画エリアの左上X座標（px）
    "TitleAreaY": 0,                    # タイトル描画エリアの左上Y座標（px）
    "TitleAreaWidth": 800,              # タイトル描画エリアの幅（px）
    "TitleAreaHeight": 200,             # タイトル描画エリアの高さ（px）
    "TitleAlignV": "top",               # タイトルの縦位置（top, center, bottom）
    "TitleAlignH": "center",            # タイトルの横位置（left, center, right）
    "ThumbnailTitle": "",               # サムネイル用タイトル文字列（空文字なら元動画タイトルを使用）

    # 弾幕スタイル
    "DanmakuEnabled": True,             # 弾幕表示の有効/無効
    "DanmakuFont": "Noto Sans JP",      # 弾幕に使用するフォント名
    "DanmakuFontSize": 36,              # 弾幕フォントサイズ（pt）
    "DanmakuColour": "FFFFFFFF",        # 弾幕文字色（AARRGGBB形式）
    "DanmakuShadow": False,             # 弾幕に影を付けるか
    "DanmakuShadowColour": "FF000000",  # 弾幕影の色（AARRGGBB形式）
    "DanmakuTrackCount": 6,             # 弾幕の表示レーン数
    "DanmakuDuration": 3.0,             # 弾幕1つの表示時間（秒）
    "DanmakuSpeed": 1.0,                # 弾幕スクロール速度係数（1.0が標準）
    "DanmakuOutline": 2,                # 外枠の太さ(px) 0で無効
    "DanmakuOutlineColour": "FF000000", # 外枠色 AARRGGBB
    "DanmakuMode": "Default",           # 弾幕表示モード(弾幕の表示位置[Default/Top/Bottom])

    # Clip関連（クリップ長・無音閾値）
    "MinClipLength": 30,                # クリップの最小長さ（秒）
    "MaxClipLength": 60,                # クリップの最大長さ（秒）
    "SilenceGap": 1.0,                  # セグメント間の無音とみなす間隔（秒）
    
    # 背景スタイル
    "BackgroundColour": "FF000000",     # 背景色（AARRGGBB形式, 例: 黒）
}

app: App = None
whisper_model: whisper = None

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

# ChatGptのAPIキーを読み込み
def load_api_key_from_file() -> str:
    key_path =  RES_DIR_PATH / "openai_key.txt"
    with open(key_path, "r", encoding="utf-8") as f:
        return f.readline().strip()

def conv_py_from_json(o):
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)

def conv_json_from_py(o):
    if isinstance(o, dict):
        return {k: conv_json_from_py(v) for k, v in o.items()}
    if isinstance(o, (list, tuple, set)):
        return [conv_json_from_py(v) for v in o]
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    return o  # str, int, float, None, bool などはそのまま

def group_segments_by_duration(
    segments: List[dict],
    min_dur: int,
    max_dur: int,
    silence_gap: float = 1.0
) -> List[Clip]:
    """
    無音区間（Whisperセグメント間gap）がsilence_gap以上あるときに分割。
    実際に「何も喋っていない時間」は字幕ブロックが発生しない。
    """
    clips = []
    n = len(segments)
    i = 0

    while i < n:
        current_start = segments[i]["start"]
        current_end = segments[i]["end"]

        # 次のセグメントとつなげられるか
        j = i + 1
        while j < n:
            gap = segments[j]["start"] - current_end
            duration = segments[j]["end"] - current_start
            if gap >= silence_gap or duration >= max_dur:
                break
            current_end = segments[j]["end"]
            j += 1

        # 必要に応じてmin_durチェック
        clip_duration = current_end - current_start
        if clip_duration >= min_dur:
            clips.append(Clip(start_time=current_start, end_time=current_end))
        i = j

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
        "以下の日本語文章を「。」または「、」でのみ区切ってください。\n"
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

def adjust_segment_ends(audio_file, segments, min_silence_len=1000, silence_thresh=-40):
    """
    各セグメントの末尾無音を検知し、喋りが終わったタイミングでendを短縮する
    """
    # mp4→wav変換
    wav_file = str(Path(tempfile.gettempdir()) / "temp_clip.wav")
    subprocess.run([
        str(FFMPEG_PATH), "-y", "-i", audio_file,
        "-ac", "1", "-ar", "16000",
        wav_file
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    audio = AudioSegment.from_file(wav_file)
    adjusted_segments = []
    for seg in segments:
        start_ms = int(seg["start"] * 1000)
        end_ms = int(seg["end"] * 1000)
        seg_audio = audio[start_ms:end_ms]
        nonsilence = silence.detect_nonsilent(seg_audio, min_silence_len=min_silence_len, silence_thresh=silence_thresh)
        if nonsilence:
            # 発話の最終地点まで
            new_end = start_ms + nonsilence[-1][1]
            # ただし極端に短くなりすぎないよう、最低0.3秒残す
            if new_end - start_ms > 300:
                seg["end"] = new_end / 1000
        adjusted_segments.append(seg)
    try:
        os.remove(wav_file)
    except Exception:
        pass
    return adjusted_segments

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
    FONT_DIR_PATH.mkdir(exist_ok=True)
    font_map = {}

    for font_path in FONT_DIR_PATH.rglob("*.ttf"):  # ← 再帰探索に変更！
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
        str(FFPROBE_PATH), "-v", "error",
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

    # 既に色タグが含まれていなければ settings["PrimaryColour"] を追加
    #if r"\c&H" not in converted:
    #    color_code = settings.get("PrimaryColour")
    #    converted = f"{{\\c{color_code}}}" + converted

    return converted

# 長い字幕を自動で適切な長さに分割
def split_long_subtitle(text: str, max_chars: int = 40, words: list = None) -> list:
    """
    句点（。！？）で文単位に区切り、1文がmax_charsを超える場合は読点（、）や空白で折り返し。
    words: Whisperの"words"リスト(単語単位でstart/endあり)を渡すと
           各ブロックに対応する単語区間のstart/endも返す。
           例: [(start, end, block_text), ...]
    """
    blocks = []

    # 1. 句点・感嘆符・疑問符などでまず文ごとに分割
    sentences = re.split(r'(?<=[。！？])', text)

    for sentence in sentences:
        s = sentence.strip()
        if not s:
            continue
        # 2. 1文がmax_charsを超える場合、読点や空白で折り返し
        while len(s) > max_chars:
            # 読点で分割
            comma_pos = s.rfind("、", 0, max_chars)
            if comma_pos == -1:
                # 空白で分割
                space_pos = s.rfind(" ", 0, max_chars)
                if space_pos == -1:
                    # 強制分割
                    split_pos = max_chars
                else:
                    split_pos = space_pos + 1
            else:
                split_pos = comma_pos + 1
            blocks.append(s[:split_pos].strip())
            s = s[split_pos:].strip()
        if s:
            blocks.append(s)

    # 単語情報なし → 今まで通り
    if not words or len(words) == 0:
        return blocks

    # 単語割り当て（ざっくり文字長で割る。日本語は単語長のブレに注意）
    result = []
    word_idx = 0
    for b in blocks:
        b_len = len(b.replace(" ", ""))  # 空白除去で比較
        acc = ""
        start_idx = word_idx
        # 単語のつなぎで全体を埋めていく
        while word_idx < len(words) and len(acc + words[word_idx]['word'].strip()) <= b_len:
            acc += words[word_idx]['word'].strip()
            word_idx += 1
            if len(acc) >= b_len:
                break
        end_idx = word_idx - 1 if word_idx > start_idx else start_idx
        if start_idx <= end_idx and end_idx < len(words):
            start = words[start_idx].get("start", None)
            end = words[end_idx].get("end", None)
            result.append((start, end, b))
        else:
            result.append((None, None, b))
    return result

# --- 追加: emote画像キャッシュ ---
_emote_cache_raw = {}        # URL -> Image(RGBA)
_emote_cache_sized = {}      # (URL, size) -> Image(RGBA)

def _load_emote_raw(url: str) -> Image.Image:
    if url not in _emote_cache_raw:
        #print(f"[EmoteDL] ダウンロード開始: {url}")
        with urllib.request.urlopen(url) as resp:
            data = resp.read()
        _emote_cache_raw[url] = Image.open(BytesIO(data)).convert("RGBA")
        #print(f"[EmoteDL] ダウンロード完了: {url}")
    #else:
        #print(f"[EmoteDL] キャッシュ使用: {url}")
    return _emote_cache_raw[url]

def get_emote_image(emote: dict, size: int) -> Image.Image:
    """emote辞書から指定サイズのPIL.Imageを取得（キャッシュあり）"""
    # 48x48 を優先、それ以外は先頭
    img_info = next((img for img in emote.get("images", []) if img.get("id") == "48x48"),
                    (emote.get("images") or [])[0])
    url = img_info["url"]
    key = (url, size)
    if key not in _emote_cache_sized:
        base = _load_emote_raw(url)
        _emote_cache_sized[key] = base.resize((size, size), Image.LANCZOS)
        #print(f"[EmoteDL] リサイズ＆キャッシュ: {url} → {size}x{size}")
    #else:
        #print(f"[EmoteDL] リサイズキャッシュ使用: {url} ({size}x{size})")
    return _emote_cache_sized[key]

# --- 追加: テキスト+emoteをトークン化 ---
def tokenize_rich_message(message: str, emotes: list[dict]) -> list[dict]:
    """
    例: [{"type":"text","value":"やったー "},
         {"type":"emote","name":":_ペンライト:"},
         {"type":"text","value":" 最高！"}]
    """
    if not emotes:
        return [{"type":"text","value": message}]

    # nameの長い順でマッチ（部分一致の衝突を避ける）
    names = sorted([e["name"] for e in emotes if "name" in e], key=len, reverse=True)
    i = 0
    parts = []
    while i < len(message):
        hit = None
        for nm in names:
            if message.startswith(nm, i):
                hit = nm
                break
        if hit:
            if i > 0 and (not parts or parts[-1]["type"] != "text"):
                # 直前までのテキストを切り出す
                pass
            # 直前テキスト
            prev_text = message[:i]
            if prev_text:
                # 直前のtextが既にあるなら結合
                if parts and parts[-1]["type"] == "text":
                    parts[-1]["value"] += prev_text
                else:
                    parts.append({"type": "text", "value": prev_text})
            # emote
            parts.append({"type": "emote", "name": hit})
            # 残りを対象に再開
            message = message[i+len(hit):]
            i = 0
        else:
            i += 1
    if message:
        if parts and parts[-1]["type"] == "text":
            parts[-1]["value"] += message
        else:
            parts.append({"type":"text","value": message})
    return parts

# --- 追加: 幅計測（emote幅を含む） ---
def measure_rich_width(parts: list[dict], font: ImageFont.FreeTypeFont, emote_size: int) -> int:
    if not parts:
        return 0
    dummy = Image.new("RGBA", (1,1), (0,0,0,0))
    draw = ImageDraw.Draw(dummy)

    width = 0
    for p in parts:
        if p["type"] == "text" and p["value"]:
            bbox = draw.textbbox((0,0), p["value"], font=font)
            width += (bbox[2] - bbox[0])
        elif p["type"] == "emote":
            width += emote_size
        # 文字とemoteの間は狭めのスペースを入れて見栄え安定（任意）
        # ただし行末は不要
    return width

# --- 追加: 描画（影対応／emoteはベースライン揃え） ---
def draw_comment_with_emotes(
    img: Image.Image,
    x: int,
    y: int,
    parts: list[dict],
    emotes: list[dict],
    font: ImageFont.FreeTypeFont,
    fill,
    show_shadow: bool,
    shadow_color,
    emote_size: int,
    outline_width: int = 0,
    outline_color = (0, 0, 0, 255),
):
    draw = ImageDraw.Draw(img)
    cursor_x = x
    emote_map = {e["name"]: e for e in (emotes or []) if "name" in e}

    try:
        ascent, descent = font.getmetrics()
    except Exception:
        ascent, descent = 0, 0
    baseline = y + ascent

    def _draw_text(xx, yy, text):
        # 影（任意）
        if show_shadow:
            draw.text((xx + 0.5, yy + 0.5), text, font=font, fill=shadow_color)

        # Pillowのstroke対応があればそれを使う
        try:
            if outline_width > 0:
                draw.text(
                    (xx, yy), text, font=font, fill=fill,
                    stroke_width=int(outline_width),
                    stroke_fill=outline_color
                )
            else:
                draw.text((xx, yy), text, font=font, fill=fill)
            return
        except TypeError:
            # 古いPillow向けフォールバック：8方向にアウトラインを手描き
            if outline_width > 0:
                offs = range(-outline_width, outline_width + 1)
                for ox in offs:
                    for oy in offs:
                        if ox == 0 and oy == 0: 
                            continue
                        draw.text((xx + ox, yy + oy), text, font=font, fill=outline_color)
            draw.text((xx, yy), text, font=font, fill=fill)

    for p in parts:
        if p["type"] == "text" and p["value"]:
            _draw_text(cursor_x, y, p["value"])
            w = draw.textbbox((0, 0), p["value"], font=font)
            cursor_x += (w[2] - w[0])

        elif p["type"] == "emote":
            e = emote_map.get(p["name"])
            if not e:
                continue
            icon = get_emote_image(e, emote_size)
            paste_y = baseline - emote_size
            img.alpha_composite(icon, (int(cursor_x), int(paste_y)))
            cursor_x += emote_size

def _render_sprite(parts, emotes, font, fill, show_shadow, shadow_color, emote_size, outline_width, outline_color):
    """
    1コメントぶんを『完成品の横長RGBA画像』にプリレンダーし、Imageを返す。
    """
    # 幅を実測
    width = measure_rich_width(parts, font, emote_size)
    if width <= 0:
        width = 1  # Pillow要件: 幅0は不可
    try:
        ascent, descent = font.getmetrics()
        height = ascent + descent
        if height <= 0:
            height = max(font.size, 1)
    except Exception:
        height = max(font.size, 1)

    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    # x=0, y=0 から描画（影込み）
    draw_comment_with_emotes(
        img=canvas, x=0, y=0,
        parts=parts, emotes=emotes or [],
        font=font, fill=fill,
        show_shadow=show_shadow, shadow_color=shadow_color,
        emote_size=emote_size,
        outline_width=outline_width, outline_color=outline_color
    )
    return canvas

# --- emotes対応の弾幕フレーム生成 ---
def generate_comment_to_png_sequence(
    comments,
    video_size,
    out_frames_dir,
    start_time,
    end_time,
    fps=30,
    duration_per_comment=None,
    font_path=None
):
    """
    【互換維持】従来はPNG連番を書き出していたが、
    ここでは『描画計画（plan）』を JSON に保存するだけに変更。
    実際の描画とffmpegへのストリーミングは combine_video_with_danmaku_overlay() が行う。

    保存先: out_frames_dir / 'overlay_plan.json'
    """
    if not settings.get("DanmakuEnabled"):
        # 無効時も空の plan を出しておく（後段が素通しコピーできるように）
        out_frames_dir = Path(out_frames_dir)
        out_frames_dir.mkdir(parents=True, exist_ok=True)
        plan_path = out_frames_dir / "overlay_plan.json"
        with open(plan_path, "w", encoding="utf-8") as f:
            json.dump({"items": [], "meta": {}}, f, ensure_ascii=False)
        return

    W, H = video_size
    out_frames_dir = Path(out_frames_dir)
    out_frames_dir.mkdir(parents=True, exist_ok=True)

    # スタイル
    font_size = settings.get("DanmakuFontSize")
    color_str = aarrggbb_to_rgba(settings.get("DanmakuColour"))
    show_shadow = settings.get("DanmakuShadow")
    shadow_color = aarrggbb_to_rgba(settings.get("DanmakuShadowColour"))
    track_count = settings.get("DanmakuTrackCount")
    duration = duration_per_comment or settings.get("DanmakuDuration")
    speed_factor = settings.get("DanmakuSpeed")
    outline_w = int(settings.get("DanmakuOutline", 0))
    outline_color = aarrggbb_to_rgba(settings.get("DanmakuOutlineColour", "FF000000"))
    emote_size = int(round(font_size * 1.1))

    # ▼ 表示モード（"Default" / "Top" / "Bottom" / 日本語 "上" / "下" にも対応）
    mode = str(settings.get("DanmakuMode", "Default")).lower()

    # ▼ 行高をフォントとアウトライン、エモートから推定（Top/Bottom で隙間ゼロに詰める用）
    #    - combine側の実描画とは独立だが、重なりを避けるため十分に大きく見積もる
    try:
        base_font = ImageFont.truetype(
            font_path or CUSTOM_FONT_PATHS.get(settings.get("DanmakuFont")) or "arial.ttf",
            font_size
        )
        ascent, descent = base_font.getmetrics()
        font_height = ascent + descent
    except Exception:
        base_font = None
        font_height = font_size

    line_height = max(font_height, emote_size) + outline_w * 2
    if line_height <= 0:
        line_height = max(1, font_size)

    # ▼ トラックY座標をモード別に計算
    # Default … 従来通り（上下に余白、レーン間に実質的な「隙間」が出る）
    # Top     … 隙間ゼロで上に詰める
    # Bottom  … 隙間ゼロで下に詰める
    def _cap(n):
        # 画面内に収まる最大行数に制限（最低1）
        return max(1, min(int(n), max(1, H // max(1, line_height))))

    if mode in ("top", "上"):
        track_count_eff = _cap(track_count)
        tracks = [int(i * line_height) for i in range(track_count_eff)]
    elif mode in ("bottom", "下"):
        track_count_eff = _cap(track_count)
        tracks = [int(H - (i + 1) * line_height) for i in range(track_count_eff)]
    else:
        # 従来通り：上下に1レーン分の余白を設けた等間隔
        track_count_eff = max(1, int(track_count))
        track_height = H // (track_count_eff + 2)
        tracks = [int(track_height * (i + 1)) for i in range(track_count_eff)]

    # JSONに保存できる形の「parts」へ（テキスト/エモートの列）
    plan_items = []
    for i, c in enumerate(comments):
        try:
            t0 = float(c.get("time_in_seconds", -1)) - start_time
        except Exception:
            continue
        if not (0 <= t0 < (end_time - start_time)):
            continue

        message = c.get("message", "")
        emotes = c.get("emotes") or []
        parts = tokenize_rich_message(message, emotes)

        # 幅ヒント（フォントが変わるとズレるので、metaとセットで扱う前提）
        try:
            if base_font is not None:
                msg_width = measure_rich_width(parts, base_font, emote_size)
            else:
                # フォールバックで再生成を試す
                tmp_font = ImageFont.truetype(
                    font_path or CUSTOM_FONT_PATHS.get(settings.get("DanmakuFont")) or "arial.ttf",
                    font_size
                )
                msg_width = measure_rich_width(parts, tmp_font, emote_size)
        except Exception:
            msg_width = None  # combine側で再計算

        plan_items.append({
            "parts": parts,            # [{"type":"text","value":...}|{"type":"emote","name":...}, ...]
            "emotes": emotes,          # 元のemote辞書列（URL等を含む）
            "start": t0,               # 区間相対秒
            "duration": float(duration),
            "y": tracks[i % track_count_eff],  # ★ モード別に求めた実効トラック数で割る
            "width_hint": msg_width,   # ヒント（無い場合はNone）
        })

    plan = {
        "meta": {
            "W": W, "H": H,
            "fps": fps,
            "colour": color_str,
            "shadow": show_shadow,
            "shadow_colour": shadow_color,
            "font_size": font_size,
            "font_name": settings.get("DanmakuFont"),
            "font_path": font_path or CUSTOM_FONT_PATHS.get(settings.get("DanmakuFont")) or None,
            "emote_size": emote_size,
            "speed": speed_factor,
            "abs_start": float(start_time),
            "abs_end": float(end_time),
            "outline_width": outline_w,
            "outline_colour": outline_color,
            "mode": settings.get("DanmakuMode", "Default"),
            "line_height_hint": line_height,  # 参考情報（combine側で使わなくても可）
        },
        "items": plan_items
    }

    plan_path = out_frames_dir / "overlay_plan.json"
    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

def combine_video_with_danmaku_overlay(
    clip_path: Path,
    frames_dir: Path,
    out_path: Path,
    fps: int = 30
):
    frames_dir = Path(frames_dir)
    plan_path = frames_dir / "overlay_plan.json"

    with open(plan_path, "r", encoding="utf-8") as f:
        plan = json.load(f)

    items = plan.get("items") or []
    meta = plan.get("meta") or {}
    if len(items) == 0:
        subprocess.run([
            str(FFMPEG_PATH), "-y",
            "-i", str(clip_path),
            "-c:v", "h264_nvenc", "-c:a", "copy",
            str(out_path)
        ], check=True)
        return

    W = int(meta.get("W", 1080))
    H = int(meta.get("H", 1920))
    fps = int(meta.get("fps", fps))
    fill = tuple(meta.get("colour", (255,255,255,255)))
    show_shadow = bool(meta.get("shadow", False))
    shadow_color = tuple(meta.get("shadow_colour", (0,0,0,255)))
    font_size = int(meta.get("font_size", 36))
    font_name = meta.get("font_name") or settings.get("DanmakuFont")
    font_path = meta.get("font_path") or CUSTOM_FONT_PATHS.get(font_name) or "arial.ttf"
    emote_size = int(meta.get("emote_size", max(1, round(font_size*1.1))))
    # speed は「表示時間を縮める／伸ばす」ためだけに使う
    speed = float(meta.get("speed", 1.0))
    if not math.isfinite(speed) or speed <= 0:
        speed = 1.0

    abs_start = float(meta.get("abs_start", 0.0))
    abs_end = float(meta.get("abs_end", 0.0))
    total_sec = max(0.0, abs_end - abs_start)
    frame_count = int(math.ceil(total_sec * fps))

    try:
        font = ImageFont.truetype(font_path, font_size)
    except Exception:
        font = ImageFont.truetype("arial.ttf", font_size)

    # ---- スプライトをプリレンダー ----
    sprites = []
    for it in items:
        parts = it.get("parts") or []
        emotes = it.get("emotes") or []
        start_rel = float(it.get("start", 0.0))
        base_dur = float(it.get("duration", 3.0))  # 設定上の基準表示時間
        y = int(it.get("y", 0))

        sprite_img = _render_sprite(
            parts=parts, emotes=emotes,
            font=font, fill=fill,
            show_shadow=show_shadow, shadow_color=shadow_color,
            emote_size=emote_size,
            outline_width=int(settings.get("DanmakuOutline", 0)),
            outline_color=aarrggbb_to_rgba(settings.get("DanmakuOutlineColour", "FF000000"))
        )

        # 速度は「表示時間」を 1/speed 倍にする
        # → 線形補間の progress は 0→1 になり、end 到達で x==-width（完全に抜け切り）
        effective_dur = base_dur / speed
        end_rel = start_rel + max(1e-6, effective_dur)

        sprites.append({
            "img": sprite_img,
            "y": y,
            "start": start_rel,
            "end": end_rel,
            "width": sprite_img.width,
            # "speed": speed  # 移動式では使わないので保持しなくてOK
        })

    sprites_by_start = sorted(sprites, key=lambda s: s["start"])
    sprites_by_end = sorted(sprites, key=lambda s: s["end"])
    i_start = 0
    i_end = 0
    active = []

    proc = subprocess.Popen([
        str(FFMPEG_PATH), "-y",
        "-i", str(clip_path),
        "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(fps), "-i", "pipe:0",
        "-filter_complex", "[0:v][1:v]overlay=shortest=1:format=auto",
        "-c:v", "h264_nvenc", "-c:a", "copy",
        str(out_path)
    ], stdin=subprocess.PIPE)

    try:
        for f in range(frame_count):
            t = f / fps

            while i_start < len(sprites_by_start) and sprites_by_start[i_start]["start"] <= t:
                active.append(sprites_by_start[i_start])
                i_start += 1
            while i_end < len(sprites_by_end) and sprites_by_end[i_end]["end"] <= t:
                try:
                    active.remove(sprites_by_end[i_end])
                except ValueError:
                    pass
                i_end += 1

            frame = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            for s in active:
                if not (s["start"] <= t <= s["end"]):
                    continue
                # 速度は end-start に反映済み。位置は純粋な 0→1 線形。
                progress = (t - s["start"]) / (s["end"] - s["start"] + 1e-9)
                x = int(W - (W + s["width"]) * progress)

                # 画面に見えているときだけ貼る（任意の最適化）
                if x < W and (x + s["width"]) > 0:
                    frame.alpha_composite(s["img"], (x, s["y"]))

            proc.stdin.write(frame.tobytes())
    finally:
        try:
            proc.stdin.close()
        except Exception:
            pass
        proc.wait()

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
        font_name = settings["Font"]
        style_str = (
            f"FontName={escape_font_name(font_name)},"
            f"FontSize={settings['FontSize']},"
            f"PrimaryColour={aarrggbb_to_ass_code(settings['PrimaryColour'])},"
            f"Outline={settings['Outline']},"
            f"OutlineColour={aarrggbb_to_ass_code(settings['OutlineColour'])},"
            f"Shadow={settings['Shadow']},"
            f"MarginV={settings['MarginV']},"
            f"Alignment={settings['Alignment']}"
        )

    # 弾幕動画に直接字幕を合成
    filter_complex = (
        f"subtitles='{escape_ffmpeg_path(srt_path)}:force_style={style_str}'"
    )
    subprocess.run([
        str(FFMPEG_PATH), "-y",
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
    global app
    global whisper_model
    fileMgr = app.file_manager
    segment_dir_path = fileMgr.segment_dir_path(app.stream_analysis.safe_title)

    # ▼ セグメント情報(絶対秒)を segment_info.json から取得
    segment_info_path = segment_dir_path / "segment_info.json"
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

    # ① クリップ切り出し
    subprocess.run([
        str(FFMPEG_PATH), "-y",
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

    segments = adjust_segment_ends(str(clip_path), segments)
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
    font_name = settings.get("Font")
    font_size = settings.get("FontSize")
    resolution = get_video_resolution(clip_path)
    max_width = estimate_max_width(resolution, font_name, font_size)

    # ⑤ 校閲済み字幕を srt に保存
    with open(srt_path, "w", encoding="utf-8") as f:
        entry_num = 1
        for i, corr in enumerate(corrected):
            seg = segments[corr["index"]]
            text = corr['text'].strip()
            blocks = split_long_subtitle(text, 40)  # ←words無し！

            if not blocks:
                blocks = [text]

            seg_start = seg["start"]
            seg_end = seg["end"]
            total_chars = sum(len(b) for b in blocks)
            if total_chars == 0:
                continue

            t = seg_start
            for j, b in enumerate(blocks):
                block_len = len(b)
                block_duration = (seg_end - seg_start) * (block_len / total_chars)
                next_t = t + block_duration
                # 最後のブロックは必ずseg_endまで
                if j == len(blocks) - 1:
                    next_t = seg_end
                start_str = format_timestamp(t)
                end_str = format_timestamp(next_t)
                f.write(f"{entry_num}\n{start_str} --> {end_str}\n{b}\n\n")
                entry_num += 1
                t = next_t

    # ⑥ 差分ログ出力
    with open(diff_path, "w", encoding="utf-8") as f:
        f.write("📝 修正ログ（インデックスごとの差分）\n\n")
        for corr in corrected:
            original = segments[corr["index"]]["text"].strip()
            corrected_text = corr["text"]
            if original != corrected_text:
                f.write(f"[{corr['index']}]\nBefore: {original}\nAfter:  {corrected_text}\n\n")

    # ⑦ ChatGPTで段落構造を生成
    structure = call_gpt_group_segments(corrected)
    if structure:
        with open(structure_path, "w", encoding="utf-8") as f:
            json.dump(structure, f, ensure_ascii=False, indent=2)

    # ⑧ チャットデータから該当区間コメント抽出
    comments = extract_comments_for_clip(
        chat_json_path, abs_start, abs_end
    )
    print(f"abs_start: {abs_start}, abs_end: {abs_end}")
    print(f"comments件数: {len(comments)}")

    # ⑨ 弾幕PNG連番生成
    video_resolution = get_video_resolution(clip_path)
    w, h = map(int, video_resolution.split("x"))
    font_path = CUSTOM_FONT_PATHS.get(settings.get("DanmakuFont"))
    fps = 30
    generate_comment_to_png_sequence(
        comments,
        video_size=(w, h),
        out_frames_dir=frames_dir,
        start_time=abs_start,
        end_time=abs_end,
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

def _run_yt_dlp_title_command(video_url: str, cookie_path: Path | None = None) -> str | None:
    cmd = [
        str(YTDLP_PATH),
        "--ignore-config",
        "--skip-download",
    ]
    if cookie_path is not None:
        cmd += ["--cookies", str(cookie_path)]
    cmd += ["--print", "%(title)s", video_url]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="cp932",
            errors="replace",
            env=_build_yt_dlp_env()
        )
    except Exception as e:
        print("yt-dlp実行中に想定外のエラー:", e)
        traceback.print_exc()
        return None

    title = result.stdout.strip()
    if result.returncode == 0 and title:
        return title

    mode = "with cookies" if cookie_path is not None else "without cookies"
    print(f"[title] yt-dlp failed ({mode})")
    print("returncode:", result.returncode)
    print("stdout:", result.stdout)
    print("stderr:", result.stderr)
    print("args:", result.args)
    return None

def _build_yt_dlp_env() -> dict:
    env = os.environ.copy()
    tmp_dir = BASE_DIR_PATH / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    env["TEMP"] = str(tmp_dir)
    env["TMP"] = str(tmp_dir)
    return env

def _fetch_youtube_oembed_title(video_url: str) -> str | None:
    params = urllib.parse.urlencode({"url": video_url, "format": "json"})
    oembed_url = f"https://www.youtube.com/oembed?{params}"
    req = urllib.request.Request(
        oembed_url,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urllib.request.urlopen(req, timeout=15) as resp:
        payload = resp.read().decode("utf-8", errors="replace")

    obj = json.loads(payload)
    title = str(obj.get("title", "")).strip()
    return title or None

def resolve_video_title(video_url: str) -> str | None:
    cookie_path = RES_DIR_PATH / "cookies.txt"

    if cookie_path.exists():
        print("Title fetch: try yt-dlp (with cookies)")
        title = _run_yt_dlp_title_command(video_url, cookie_path)
        if title:
            return title

    print("Title fetch: try yt-dlp (without cookies)")
    title = _run_yt_dlp_title_command(video_url)
    if title:
        return title

    print("Title fetch: try YouTube oEmbed fallback")
    try:
        return _fetch_youtube_oembed_title(video_url)
    except Exception as e:
        print("Title fetch failed on oEmbed:", e)
        traceback.print_exc()
        return None

def _load_cookies_into_session(session, cookie_path: Path) -> int:
    jar = http.cookiejar.MozillaCookieJar(str(cookie_path))
    try:
        jar.load(ignore_discard=True, ignore_expires=True)
    except Exception as e:
        raise RuntimeError(f"cookies.txt の読み込みに失敗しました: {e}")

    count = 0
    for cookie in jar:
        session.cookies.set_cookie(cookie)
        count += 1
    return count

def _parse_chat_timestamp_to_seconds(timestamp_text: str | None) -> float | None:
    text = (timestamp_text or "").strip()
    if not text or text.startswith("-"):
        return None

    parts = text.split(":")
    if len(parts) == 0 or len(parts) > 3:
        return None

    try:
        values = [float(part) for part in parts]
    except ValueError:
        return None

    if any(v < 0 for v in values):
        return None

    if len(values) == 3:
        hours, minutes, seconds = values
        return (hours * 3600.0) + (minutes * 60.0) + seconds
    if len(values) == 2:
        minutes, seconds = values
        return (minutes * 60.0) + seconds
    return values[0]

def _normalize_yt_chat_messages(raw_messages: list[dict]) -> list[dict]:
    normalized = []
    for item in raw_messages:
        if not isinstance(item, dict):
            continue

        message = str(item.get("comment", "")).strip()
        if not message:
            continue

        time_in_seconds = None
        offset_ms = item.get("video_offset_ms")
        if offset_ms not in (None, ""):
            try:
                time_in_seconds = float(offset_ms) / 1000.0
            except (TypeError, ValueError):
                time_in_seconds = None

        if time_in_seconds is None:
            time_in_seconds = _parse_chat_timestamp_to_seconds(str(item.get("timestamp", "")))

        if time_in_seconds is None or (not math.isfinite(time_in_seconds)) or time_in_seconds < 0:
            continue

        normalized.append({
            "time_in_seconds": time_in_seconds,
            "message": message,
            "emotes": []
        })

    normalized.sort(key=lambda x: x["time_in_seconds"])
    return normalized

def _download_chat_via_yt_chat_downloader(video_url: str, cookie_path: Path | None = None) -> list[dict]:
    downloader = YouTubeChatDownloader()
    if cookie_path is not None:
        loaded = _load_cookies_into_session(downloader.session, cookie_path)
        print(f"yt-chat-downloader: cookiesを読み込み ({loaded}件)")

    raw_messages = downloader.download_chat(
        video_url=video_url,
        chat_type="live",
        output_file=None,
        quiet=True
    )
    return _normalize_yt_chat_messages(raw_messages)

def create_new_file():
    global app
    name = simpledialog.askstring("新規ファイル", "ファイル名（例: プロジェクト名）を入力してください")
    if not name:
        return
    project_settings = copy.deepcopy(app.settings)
    app.file_manager.create_file(name, project_settings)
    app.project_file_path_name = name
    app.update_window_title()
    app.show_info_message("ファイル作成", f"新しいファイル「{name}」を作成しました。")
    app.file_manager.load_file_settings(app.settings)

def open_file():
    global app
    files = app.file_manager.list_files()
    if not files:
        app.show_info_message("情報", "まだファイルがありません。新規ファイルを作成してください。")
        return
    win = tk.Toplevel(app.root)
    win.title("ファイルを開く")
    tk.Label(win, text="作業ファイル選択:").pack()
    lb = tk.Listbox(win)
    for f in files:
        lb.insert(tk.END, f)
    lb.pack()
    def do_select():
        sel = lb.curselection()
        if not sel:
            return
        name = lb.get(sel[0])
        app.file_manager.select_file(name)
        app.project_file_path_name = name
        app.update_window_title()
        app.file_manager.load_file_settings(app.settings)
        win.destroy()
        app.show_info_message("ファイル切替", f"「{name}」を開きました。")
    tk.Button(win, text="開く", command=do_select).pack()

def delete_file():
    global app
    files = app.file_manager.list_files()
    if not files:
        app.show_info_message("情報", "削除できるファイルがありません。")
        return
    win = tk.Toplevel(app.root)
    win.title("ファイルを削除")
    tk.Label(win, text="削除するファイル選択:").pack()
    lb = tk.Listbox(win)
    for f in files:
        lb.insert(tk.END, f)
    lb.pack()
    def do_delete():
        sel = lb.curselection()
        if not sel:
            return
        name = lb.get(sel[0])
        if messagebox.askyesno("確認", f"「{name}」を本当に削除しますか？"):
            app.file_manager.delete_file(name)
            win.destroy()
            app.show_info_message("削除", f"「{name}」を削除しました。")
    tk.Button(win, text="削除", command=do_delete).pack()

# 解像度設定メニュー表示
def open_resolution_window():
    global app
    root = app.root
    res_win = tk.Toplevel(root)
    res_win.title("解像度の設定")
    res_win.geometry("300x120")

    tk.Label(res_win, text="解像度を設定:").pack(pady=5)
    current_res = settings.get("Resolution")
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
            app.show_error_message("エラー", "横幅・縦幅には数値を入力してください。")
            return
        settings["Resolution"] = f"{w}x{h}"
        app.show_info_message("保存完了", f"解像度: {settings['Resolution']}")
        save_settings() # 設定保存
        res_win.destroy()

    tk.Button(res_win, text="保存", command=save_resolution).pack(pady=10)

# 字幕設定ウィンドウ表示
def open_subtitle_style_window():
    global app
    root = app.root

    def show_help():
        help_win = Toplevel(root)
        help_win.title("字幕スタイルの説明")
        help_text = Text(help_win, wrap="word", width=80, height=30)
        help_text.pack(padx=10, pady=10)

        try:
            with open(BASE_DIR_PATH / "res" / "subtitle_style_help.txt", encoding="utf-8") as f:
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
    add_entry("文字色", "PrimaryColour")
    add_entry("縁取りサイズ", "Outline")
    add_entry("縁取り色", "OutlineColour")
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
            if key in ["FontSize", "MarginV", "Alignment"]:
                if not val.isdigit():
                    app.show_error_message("エラー", f"{key} は数値である必要があります。")
                    return
                settings[key] = int(val)
            elif key == "Outline" or key == "Shadow":
                try:
                    settings[key] = float(val)
                except ValueError:
                    app.show_error_message("エラー", "Outline は数値である必要があります。")
                    return
            else:
                settings[key] = val

        app.show_info_message("保存完了", "字幕スタイルが保存されました。")
        save_settings() # 設定保存
        style_win.destroy()

    Button(style_win, text="カスタムフォント", command=choose_custom_font).pack(pady=6)
    Button(style_win, text="保存", command=save_style).pack(pady=10)

def open_title_style_dialog():
    global app
    root = app.root

    dialog = tk.Toplevel(root)
    dialog.title("題名スタイル設定")

    # ▼ フォント名選択
    tk.Label(dialog, text="フォント名:").grid(row=0, column=0)
    title_font_var = tk.StringVar(value=settings.get("TitleFont"))
    font_choices = AVAILABLE_FONTS
    tk.OptionMenu(dialog, title_font_var, *font_choices).grid(row=0, column=1)

    # ▼ フォントサイズ
    tk.Label(dialog, text="フォントサイズ:").grid(row=1, column=0)
    title_font_size_var = tk.IntVar(value=settings.get("TitleFontSize"))
    tk.Spinbox(dialog, from_=10, to=400, textvariable=title_font_size_var).grid(row=1, column=1)

    # エリア
    tk.Label(dialog, text="X座標:").grid(row=2, column=0)
    x_var = tk.IntVar(value=settings.get("TitleAreaX"))
    tk.Spinbox(dialog, from_=0, to=9999, textvariable=x_var).grid(row=2, column=1)

    tk.Label(dialog, text="Y座標:").grid(row=3, column=0)
    y_var = tk.IntVar(value=settings.get("TitleAreaY"))
    tk.Spinbox(dialog, from_=0, to=9999, textvariable=y_var).grid(row=3, column=1)

    tk.Label(dialog, text="幅:").grid(row=4, column=0)
    w_var = tk.IntVar(value=settings.get("TitleAreaWidth"))
    tk.Spinbox(dialog, from_=0, to=9999, textvariable=w_var).grid(row=4, column=1)

    tk.Label(dialog, text="高さ:").grid(row=5, column=0)
    h_var = tk.IntVar(value=settings.get("TitleAreaHeight"))
    tk.Spinbox(dialog, from_=0, to=9999, textvariable=h_var).grid(row=5, column=1)

    # 垂直位置
    tk.Label(dialog, text="縦位置:").grid(row=6, column=0)
    v_var = tk.StringVar(value=settings.get("TitleAlignV"))
    ttk.Combobox(dialog, textvariable=v_var, values=["top", "center", "bottom"]).grid(row=6, column=1)

    # 水平位置
    tk.Label(dialog, text="横位置:").grid(row=7, column=0)
    h_align_var = tk.StringVar(value=settings.get("TitleAlignH"))
    ttk.Combobox(dialog, textvariable=h_align_var, values=["left", "center", "right"]).grid(row=7, column=1)
    
    # タイトルテキスト（手動入力）
    tk.Label(dialog, text="サムネイル表示文字:").grid(row=8, column=0)
    title_text_var = tk.StringVar(value=settings.get("ThumbnailTitle"))
    tk.Entry(dialog, textvariable=title_text_var, width=30).grid(row=8, column=1)

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
        settings["ThumbnailTitle"] = title_text_var.get()
        # フォントやサイズもあればここで
        save_settings()  # 保存関数呼ぶ
        dialog.destroy()
    tk.Button(dialog, text="保存", command=save_settings_and_close).grid(row=9, column=0, columnspan=2)

def open_danmaku_style_window():
    global app
    root = app.root
    win = Toplevel(root)
    win.title("弾幕スタイルの設定")
    win.geometry("400x520")

    entries = {}

    def add_entry(label, key, var_type=str):
        frame = Frame(win)
        frame.pack(pady=4, anchor=W)
        Label(frame, text=label, width=18, anchor=W).pack(side=LEFT)
        val = settings.get(key)
        var = StringVar(value=str(val))
        entry = Entry(frame, textvariable=var, width=20)
        entry.pack(side=LEFT)
        entries[key] = (var, var_type)

    # 表示ON/OFF
    enabled_var = BooleanVar(value=settings.get("DanmakuEnabled"))
    Checkbutton(win, text="弾幕を表示する", variable=enabled_var).pack(pady=5)

    # フォント選択
    font_frame = Frame(win)
    font_frame.pack(pady=4, anchor=W)
    Label(font_frame, text="フォント", width=18, anchor=W).pack(side=LEFT)
    font_var = StringVar(value=settings.get("DanmakuFont"))
    all_fonts = AVAILABLE_FONTS + [f for f in CUSTOM_FONT_PATHS if f not in AVAILABLE_FONTS]
    OptionMenu(font_frame, font_var, *all_fonts).pack(side=LEFT)

    # 弾幕表示モード
    Label(win, text="表示モード").pack(pady=4, anchor=W)
    mode_var = StringVar(value=settings.get("DanmakuMode", "Default"))
    mode_box = ttk.Combobox(win, state="readonly", width=18,
                        values=["Default", "Top", "Bottom"],
                        textvariable=mode_var)
    mode_box.pack(pady=2, anchor=W)

    add_entry("フォントサイズ", "DanmakuFontSize", int)
    add_entry("フォント色 (#FFRRGGBB)", "DanmakuColour", str)
    add_entry("影の色 (#FFRRGGBB)", "DanmakuShadowColour", str)
    add_entry("表示時間（秒）", "DanmakuDuration", float)
    add_entry("表示レーン数", "DanmakuTrackCount", int)
    add_entry("スクロール速度", "DanmakuSpeed", float)
    add_entry("外枠の太さ(px)", "DanmakuOutline", int)
    add_entry("外枠の色(AARRGGBB)", "DanmakuOutlineColour", str)

    shadow_var = BooleanVar(value=settings.get("DanmakuShadow"))
    Checkbutton(win, text="影を付ける", variable=shadow_var).pack(pady=5)

    def save_danmaku_style():
        try:
            settings["DanmakuEnabled"] = enabled_var.get()
            settings["DanmakuFont"] = font_var.get()
            settings["DanmakuShadow"] = shadow_var.get()
            settings["DanmakuMode"] = mode_var.get()
            for key, (var, vartype) in entries.items():
                val = var.get().strip()
                if vartype == int:
                    settings[key] = int(val)
                elif vartype == float:
                    settings[key] = float(val)
                else:
                    settings[key] = val
            save_settings()
            app.show_info_message("保存完了", "弾幕スタイルが保存されました。")
            win.destroy()
        except Exception as e:
            app.show_error_message("エラー", f"保存中にエラーが発生しました: {e}")

    Button(win, text="保存", command=save_danmaku_style).pack(pady=10)

def open_clip_setting_window():
    global app
    root = app.root
    win = Toplevel(root)
    win.title("クリップ設定")
    win.geometry("300x200")

    entries = {}

    def add_entry(label, key, var_type):
        frame = Frame(win)
        frame.pack(pady=5, anchor=W)
        Label(frame, text=label, width=15, anchor=W).pack(side=LEFT)
        val = settings.get(key)
        var = StringVar(value=str(val))
        entry = Entry(frame, textvariable=var, width=10)
        entry.pack(side=LEFT)
        entries[key] = (var, var_type)

    add_entry("最小長（秒）", "MinClipLength", int)
    add_entry("最大長（秒）", "MaxClipLength", int)
    add_entry("無音閾値（秒）", "SilenceGap", float)

    def save_clip_settings():
        try:
            for key, (var, var_type) in entries.items():
                value = var.get().strip()
                if var_type == int:
                    settings[key] = int(value)
                else:
                    settings[key] = float(value)
            save_settings()
            app.show_info_message("保存完了", "クリップ設定を保存しました。")
            win.destroy()
        except Exception as e:
            app.show_error_message("エラー", f"保存に失敗しました: {e}")

    Button(win, text="保存", command=save_clip_settings).pack(pady=10)

def open_background_style_window():
    global app
    root = app.root
    win = Toplevel(root)
    win.title("背景の設定")
    win.geometry("300x200")

    # 背景色（AARRGGBB）
    Label(win, text="背景色 (AARRGGBB)").pack(pady=5)
    colour_var = StringVar(value=settings.get("BackgroundColour"))
    Entry(win, textvariable=colour_var, width=20).pack()

    def save_background_style():
        val = colour_var.get().strip()
        if len(val) != 8:
            app.show_error_message("エラー", "背景色は AARRGGBB 形式で入力してください。")
            return
        settings["BackgroundColour"] = val
        save_settings()
        app.show_info_message("保存完了", "背景設定が保存されました。")
        win.destroy()

    Button(win, text="保存", command=save_background_style).pack(pady=10)

# 字幕の焼き直し
def clip_reburn_file_gui():
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
    out = Path(mp4_path).with_name(Path(mp4_path).stem + "_final.mp4")

    try:
        generate_video(
            danmaku_video=Path(danmaku_path),
            srt_path=Path(srt_path),
            output_path=Path(out)
        )
        app.show_info_message("完了", f"字幕＋弾幕の焼き直しが完了しました！\n出力: {mp4_path}")
    except Exception as e:
        app.show_error_message("エラー", f"字幕＋弾幕焼き直しに失敗しました:\n{e}")

def clip_reburn_folder_gui():
    # ① clipフォルダ選択
    folder = filedialog.askdirectory(title="クリップの焼き直しを行うフォルダを選択")
    if not folder:
        print("❌ フォルダが選択されませんでした")
        return

    folder = Path(folder)
    # ② クリップごとに処理
    count = 0
    for clip_dir in folder.glob("clip_*"):
        if not clip_dir.is_dir():
            continue
        # クリップmp4/srt/弾幕動画パス探索
        mp4s = list(clip_dir.glob("*.mp4"))
        srts = list(clip_dir.glob("*.srt")) + list(clip_dir.glob("*.ass"))
        danmaku_mp4s = [p for p in mp4s if "danmaku" in p.stem]
        base_mp4s = [p for p in mp4s if "final" not in p.stem and "danmaku" not in p.stem]
        # 最終出力ファイル名
        for base_mp4 in base_mp4s:
            stem = base_mp4.stem
            # 対応するsrt/ass, danmaku.mp4
            srt = next((s for s in srts if stem in s.stem), None)
            danmaku = next((d for d in danmaku_mp4s if stem in d.stem), None)
            if not srt or not danmaku:
                print(f"⚠️ {clip_dir.name} の素材が揃っていません: {base_mp4.name}")
                continue
            out_path = clip_dir / f"{stem}_final.mp4"
            try:
                generate_video(
                    danmaku_video=danmaku,
                    srt_path=srt,
                    output_path=out_path
                )
                print(f"✅ クリップ焼き直し完了: {out_path}")
                count += 1
            except Exception as e:
                print(f"❌ {clip_dir.name} 焼き直し失敗: {e}")

    app.show_info_message("完了", f"{count}個のクリップ焼き直しが完了しました！")

#####色コード変換#####
def aarrggbb_to_rgba(color: str):
    s = color.lstrip("#")
    if len(s) != 8:
        return (0,0,0,255)
    a = int(s[0:2], 16)
    r = int(s[2:4], 16)
    g = int(s[4:6], 16)
    b = int(s[6:8], 16)
    return (r, g, b, a)

def aarrggbb_to_ass_code(color: str) -> str:
    c = color.lstrip("#")
    if len(c) != 8:
        raise ValueError("AARRGGBB形式のみを受け付けます")
    aa, rr, gg, bb = c[0:2], c[2:4], c[4:6], c[6:8]
    # ASSの透明度仕様に合わせてUIのアルファ値を反転
    aa_val = 255 - int(aa, 16)
    aa = f"{aa_val:02X}"
    return f"&H{aa}{bb}{gg}{rr}"
    
def rgba_to_aarrggbb(r, g, b, a):
    return f"{a:02X}{r:02X}{g:02X}{b:02X}"

def aarrggbb_to_ffmpeg_color(aarrggbb: str) -> str:
    s = aarrggbb.lstrip("#").upper()
    if len(s) != 8:
        return "0x000000"
    rr = s[2:4]
    gg = s[4:6]
    bb = s[6:8]
    aa = int(s[0:2], 16)
    color = f"0x{rr}{gg}{bb}"
    if aa < 255:
        return f"{color}@{aa/255:.3f}"
    return color

def open_color_code_preview():
    dlg = Toplevel()
    dlg.title("色コード生成ウィンドウ（AARRGGBB）")
    dlg.geometry("340x500")

    a, r, g, b = 255, 255, 0, 0

    r_scale = Scale(dlg, from_=0, to=255, orient=HORIZONTAL, label="R")
    r_scale.set(r)
    g_scale = Scale(dlg, from_=0, to=255, orient=HORIZONTAL, label="G")
    g_scale.set(g)
    b_scale = Scale(dlg, from_=0, to=255, orient=HORIZONTAL, label="B")
    b_scale.set(b)
    a_scale = Scale(dlg, from_=0, to=255, orient=HORIZONTAL, label="A(透明度)")
    a_scale.set(a)

    r_scale.pack()
    g_scale.pack()
    b_scale.pack()
    a_scale.pack()

    # キャンバスで色＋Color文字を重ねる
    canvas = Canvas(dlg, width=160, height=48, bg="#FFF", highlightthickness=0)
    canvas.pack(pady=14)

    code_label = Label(dlg, text="", font=("Consolas", 14), fg="#000000")
    code_label.pack()

    def update_preview(*_):
        aa = a_scale.get()
        rr = r_scale.get()
        gg = g_scale.get()
        bb = b_scale.get()
        hexval = rgba_to_aarrggbb(rr, gg, bb, aa)
        code_label["text"] = f"AARRGGBB: {hexval}"

        # 背景色（アルファなしの見た目色で塗る）
        canvas.delete("all")
        # Checker-board pattern to visualize alpha (optional, but helpful)
        for y in range(0, 48, 8):
            for x in range(0, 160, 8):
                if (x//8 + y//8) % 2 == 0:
                    canvas.create_rectangle(x, y, x+8, y+8, fill="#ccc", outline="")
                else:
                    canvas.create_rectangle(x, y, x+8, y+8, fill="#fff", outline="")
        # 透明度を考慮した色（Tkinterはアルファ不可なので、重ねて近い見た目にする）
        bg_hex = f'#{rr:02x}{gg:02x}{bb:02x}'
        alpha = aa / 255
        # 疑似的に不透明度を再現（色を透明度に応じて白と合成）
        def blend(bg, fg, alpha):
            return int(fg*alpha + bg*(1-alpha))
        r_disp = blend(255, rr, alpha)
        g_disp = blend(255, gg, alpha)
        b_disp = blend(255, bb, alpha)
        disp_color = f'#{r_disp:02x}{g_disp:02x}{b_disp:02x}'
        canvas.create_rectangle(0, 0, 160, 48, fill=disp_color, outline="")

    for scale in (r_scale, g_scale, b_scale, a_scale):
        scale.config(command=lambda *_: update_preview())
    update_preview()

    def copy_to_clipboard():
        dlg.clipboard_clear()
        dlg.clipboard_append(code_label["text"].split()[-1])

    Button(dlg, text="色コードをコピー", command=copy_to_clipboard).pack(pady=8)

def open_in_default_viewer(path: Path):
    """OS既定のプレイヤーでファイルを開く"""
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(path))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except Exception as e:
        print(f"⚠️ 自動再生に失敗しました: {e}")

def attach_cleanup_on_window_close(win: tk.Toplevel, targets: list[Path]):
    """
    Toplevel が閉じられたタイミングで targets（ファイル/フォルダ）を削除。
    """
    targets = [Path(t) for t in (targets or [])]
    _done = {"v": False}

    def _cleanup():
        if _done["v"]:
            return
        _done["v"] = True
        for t in targets:
            try:
                if t.is_dir():
                    shutil.rmtree(t, ignore_errors=True)
                else:
                    t.unlink(missing_ok=True)
                print(f"🧹 削除: {t}")
            except Exception as e:
                print(f"⚠️ 削除失敗: {t} ({e})")

    def _on_close():
        try:
            win.destroy()
        finally:
            # ちょい待ち（ハンドル解放・描画解放のため）
            app.root.after(150, _cleanup)

    win.protocol("WM_DELETE_WINDOW", _on_close)
    win.bind("<Destroy>", lambda e: app.root.after(150, _cleanup))

def preview_danmaku_as_temp_video(duration: float = 8.0, fps: int = 30):
    """
    8秒の無地動画に弾幕を重ねてプレビュー。
    ・まず “弾幕ウィンドウ(Toplevel)” を作る（←ここにクリーンアップひも付け）
    ・重い生成処理は別スレッド
    ・生成完了後、外部プレイヤーで再生ボタン
    ・ウィンドウを閉じたら一時フォルダごと削除
    """
    global app, settings, CUSTOM_FONT_PATHS

    # ---- 弾幕ウィンドウ（メインスレッドで作成）----
    win = tk.Toplevel(app.root)
    win.title("弾幕プレビュー")
    win.geometry("420x160")

    status_var = tk.StringVar(value="準備中…")
    ttk.Label(win, textvariable=status_var).pack(anchor="w", padx=12, pady=(12, 6))

    btn_frame = ttk.Frame(win)
    btn_frame.pack(fill="x", padx=12, pady=8)

    play_btn = ttk.Button(btn_frame, text="再生", state="disabled")
    play_btn.pack(side="left")

    ttk.Button(btn_frame, text="閉じる", command=win.destroy).pack(side="right")

    # 一時作業フォルダ（毎回ユニーク）
    work_root = Path(tempfile.mkdtemp(prefix="danmaku_preview-"))
    frames_dir = work_root / "frames"
    base_clip  = work_root / "base.mp4"
    out_path   = work_root / "danmaku_preview.mp4"

    # ← このウィンドウが “弾幕ウィンドウ”。閉じたら work_root ごと消す
    attach_cleanup_on_window_close(win, [work_root])

    def worker():
        try:
            # 1) 解像度・背景色
            res = str(settings.get("Resolution", "1080x1920")).lower()
            try:
                W, H = map(int, res.split("x"))
            except Exception:
                W, H = 1080, 1920
            bgColor = aarrggbb_to_ffmpeg_color(settings.get("BackgroundColour", "FF000000"))

            # 2) サンプルコメント生成
            words = ["おはよう", "テストです", "さようなら", "ありがとう"]
            comments, t, i = [], 0.5, 0
            while t < duration - 0.2:
                comments.append({"time_in_seconds": t, "message": words[i % len(words)], "emotes": []})
                t += 0.5; i += 1

            # 3) plan(JSON)作成
            frames_dir.mkdir(parents=True, exist_ok=True)
            font_path = CUSTOM_FONT_PATHS.get(settings.get("DanmakuFont"))
            generate_comment_to_png_sequence(
                comments=comments,
                video_size=(W, H),
                out_frames_dir=frames_dir,
                start_time=0.0,
                end_time=float(duration),
                fps=fps,
                duration_per_comment=settings.get("DanmakuDuration"),
                font_path=font_path
            )

            # 4) ベース動画生成（NVENC → 失敗時 libx264）
            cmd_nvenc = [
                str(FFMPEG_PATH), "-y",
                "-f", "lavfi", "-i", f"color=c={bgColor}:s={W}x{H}:r={fps}:d={duration}",
                "-c:v", "h264_nvenc", "-pix_fmt", "yuv420p",
                str(base_clip)
            ]
            ret = subprocess.run(cmd_nvenc, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if ret.returncode != 0:
                cmd_x264 = [
                    str(FFMPEG_PATH), "-y",
                    "-f", "lavfi", "-i", f"color=c={bgColor}:s={W}x{H}:r={fps}:d={duration}",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    str(base_clip)
                ]
                subprocess.run(cmd_x264, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # 5) 弾幕オーバーレイ合成
            combine_video_with_danmaku_overlay(
                clip_path=base_clip,
                frames_dir=frames_dir,
                out_path=out_path,
                fps=fps
            )

            def on_ready():
                status_var.set(f"完了: {out_path}")
                play_btn.config(state="normal", command=lambda: open_in_default_viewer(out_path))
            app.root.after(0, on_ready)

        except Exception as e:
            def on_err():
                status_var.set(f"エラー: {e}")
            app.root.after(0, on_err)

    # 重い処理は別スレッド
    threading.Thread(target=worker, daemon=True).start()

# 字幕生成のフィルター設定を生成
def generate_subtitle_filter(srt_path: Path) -> str:
    font_name = settings["Font"]
    style_str = (
        f"FontName={escape_font_name(font_name)},"
        f"FontSize={settings['FontSize']},"
        f"PrimaryColour={aarrggbb_to_ass_code(settings['PrimaryColour'])},"
        f"Outline={settings['Outline']},"
        f"OutlineColour={aarrggbb_to_ass_code(settings['OutlineColour'])},"
        f"Shadow={settings['Shadow']},"
        f"MarginV={settings['MarginV']},"
        f"Alignment={settings['Alignment']}"
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
    global app
    fileMgr = app.file_manager
    try:
        if fileMgr.project_file_path:  # プロジェクト選択中なら個別に
            setting_file_path = fileMgr.project_file_path / "res" / "settings.txt"
        else:  # 何も開いてなければ共通設定
            setting_file_path = BASE_DIR_PATH / "res" / "settings.txt"
        setting_file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(setting_file_path, "w", encoding="utf-8") as f:
            import json
            json.dump(settings, f, ensure_ascii=False, indent=2)
        print(f"✅ 設定を保存しました: {setting_file_path}")
    except Exception as e:
        print(f"❌ 設定の保存に失敗: {e}")

# wavファイルに変換(音データ取得のため)
def convert_to_wav(input_file, wav_file):
    if not os.path.exists(str(input_file)):
        print(f"❌ 入力ファイルが存在しません: {input_file}")
        raise RuntimeError(f"入力ファイルが存在しません: {input_file}")
    cmd = [
        str(FFMPEG_PATH), "-y",
        "-i", str(input_file),
        "-ac", "1",
        "-ar", "44100",
        str(wav_file)
    ]
    print("実行コマンド:", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, encoding="utf-8")
    if result.returncode != 0:
        print(f"❌ ffmpeg変換失敗: {input_file}")
        print("ffmpeg stderr:\n", result.stderr)
        raise RuntimeError(f"ffmpeg変換失敗: {input_file}")

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

def wait_for_segments_ready(timeout_sec: int = 600, poll_sec: float = 0.5) -> bool:
    """
    segment_info.json が存在し、JSONが読めて、列挙された segment_*.mp4 が
    すべて存在し、かつファイルサイズが安定するまで待つ。
    （tmp などは使わず、現行の書き出し方法のままで“出来上がり”を判断）
    """
    global app
    fileMgr = app.file_manager
    segdir = fileMgr.segment_dir_path(app.stream_analysis.safe_title)
    if not segdir:
        print("❌ セグメントフォルダが未確定（safe_title 未設定の可能性）")
        return False

    info_path = segdir / "segment_info.json"
    t0 = time.time()
    last_sizes = None
    stable_hits = 0          # 連続してサイズが同じ回数
    need_stable_hits = 2     # 2回連続で同じ＝安定とみなす

    while time.time() - t0 < timeout_sec:
        if not info_path.exists():
            time.sleep(poll_sec)
            continue

        # 書きかけ等で読めない瞬間はスルー
        try:
            with open(info_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            time.sleep(poll_sec)
            continue

        # 期待形式か確認
        if not isinstance(meta, list) or not meta:
            time.sleep(poll_sec)
            continue

        files = []
        ok = True
        for m in meta:
            fn = m.get("file")
            if not fn:
                ok = False
                break
            p = segdir / fn
            files.append(p)
            if not p.exists():
                ok = False
                break
        if not ok:
            time.sleep(poll_sec)
            continue

        # サイズ安定チェック
        sizes = tuple((str(p), p.stat().st_size) for p in files)
        if sizes == last_sizes:
            stable_hits += 1
        else:
            stable_hits = 0
            last_sizes = sizes

        if stable_hits >= need_stable_hits:
            return True

        time.sleep(poll_sec)

    print("⏰ セグメント出来上がり待ちでタイムアウトしました")
    return False

##### クリップ #####
def generate_clips_from_folder(*, run_in_thread: bool = True):
    """
    セグメント動画フォルダを自動参照してクリップ動画を生成する
    run_in_thread=True: GUIからの手動ボタン時などにバックグラウンド実行
    run_in_thread=False: ワーカー内での同期実行（逐次処理保証）
    """
    global app

    if update_paths_from_url() == False:
        return

    fileMgr = app.file_manager
    segment_dir_path = fileMgr.segment_dir_path(app.stream_analysis.safe_title)
    
    if not segment_dir_path or not segment_dir_path.exists():
        print("⚠️ セグメントフォルダが存在しません。先にセグメント生成をしてください。")
        return

    def _run():
        print(f"📁 自動選択フォルダからクリップ動画生成を開始します: {segment_dir_path}")
        for segment_file_path in Path(segment_dir_path).glob("segment_*.mp4"):
            generate_clips(segment_file_path)
        app.show_info_message("完了", "クリップ動画生成が完了しました")

    # ワンボタン/キューワーカー中は同期実行（並列禁止）
    if app.is_oneclick_mode or not run_in_thread:
        _run()
    else:
        threading.Thread(target=_run).start()

def generate_clips_from_file(*, run_in_thread: bool = True):
    """
    セグメント動画ファイル指定してクリップ動画を生成する
    """
    global app
    segment_file_path = filedialog.askopenfilename(filetypes=[("MP4 Files", "*.mp4")])
    if not segment_file_path:
        print("⚠️ ファイルが選択されませんでした。処理を中止します。")
        return
    
    if update_paths_from_url() == False:
        return
    
    def _run():
        print(f"🎬 ファイル選択でクリップ動画の生成を開始します・・・: {segment_file_path}")
        generate_clips(Path(segment_file_path))
        app.show_info_message("完了", "ファイル指定のクリップ動画生成が完了しました")

    # ワンボタン/キューワーカー中は同期実行（並列禁止）
    if app.is_oneclick_mode or not run_in_thread:
        _run()
    else:
        threading.Thread(target=_run).start()
    
def generate_clips(segment_path: Path):
    """
    指定セグメント動画からクリップ動画生成する
    Args:
        segment_path (Path): クリップ元となるセグメント動画のファイルパス
    """
    global app
    global whisper_model
    fileMgr = app.file_manager
    segment_dir_path = fileMgr.segment_dir_path(app.stream_analysis.safe_title)
    output_dir_path = fileMgr.output_dir_path(app.stream_analysis.safe_title)

    print(f"🎬 クリップ動画生成開始・・・: {segment_path.name}")
    try:
        # ▼ segment_info.json 参照
        segment_info_path = segment_dir_path / "segment_info.json"
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

        result = whisper_model.transcribe(str(segment_path), language="ja", task="transcribe")
        segments = result["segments"]
        print(f"📝 字幕セグメント数: {len(segments)}")
        clips = group_segments_by_duration(
            segments,
            settings.get("MinClipLength"),
            settings.get("MaxClipLength"),
            settings.get("SilenceGap")
        )
        print(f"📌 抽出されたクリップ数: {len(clips)}")
        output_dir = output_dir_path / "clip" / segment_path.stem
        output_dir.mkdir(parents=True, exist_ok=True)
        
        stream_title = app.stream_analysis.safe_title
        if not stream_title:
            print("❌ stream_titleが空です。動画分析またはURL入力を先に実行してください。")
            return
        chat_json_path = output_dir_path / f"{stream_title}_chat.json"
        
        for i, clip in enumerate(clips):
            print(f"🔧 クリップ生成: clip_{i} [{clip.start_time:.2f}s - {clip.end_time:.2f}s]")
            # ここで segment_start_time を使えば「配信全体での絶対秒数」も計算できる
            # 例: clip_abs_start = segment_start_time + clip.start_time
            export_clip(i, clip, segment_path, output_dir, chat_json_path)
    except Exception as e:
        print(f"❌ ファイル {segment_path.name} の処理に失敗しました: {e}")
    print("✅ クリップ動画生成が完了しました")
    
def update_paths_from_url() -> bool:
    """
    URL→各種パスを更新する。
    - preset_url があればそれを最優先で使う（GUI入力欄は参照しない）
    - target_sa があればそこを書き換える。無ければ app.stream_analysis を更新
    - sa.locked の有無に関係なく、safe_title 決定後は必ず
      output/<safe_title>/... をベースに矯正する
    """
    global app
    sa = app.stream_analysis
    preset_url: str = None
         

    # どのURLを使うかの優先順位
    if preset_url:
        url_input = preset_url.strip()
    elif getattr(sa, "locked", False) and sa.video_url:
        url_input = sa.video_url
    elif app.is_oneclick_mode and sa.video_url:
        url_input = sa.video_url
    else:
        url_input = app.entry.get().strip()

    if not url_input:
        messagebox.showwarning("URL未入力", "YouTubeのURLを入力してください")
        return False

    normalized_url = normalize_youtube_url(url_input)
    sa.video_url = normalized_url

    # タイトル取得（yt-dlp: cookiesあり -> cookiesなし -> oEmbed）
    title = resolve_video_title(normalized_url)
    if not title:
        print("YTDLP_PATH exists:", os.path.exists(str(YTDLP_PATH)))
        app.show_error_message("エラー", "動画タイトルが取得できませんでした")
        return False

    # safe_title 確定
    sa.raw_title = title
    title = title.replace("…", "_")
    sa.safe_title = re.sub(r'[\\/*?:"\'<>|#]', "", title)
    print(f"safe_title: {sa.safe_title}")

    # 以降は必ず output/<safe_title> をベースにする（locked でも矯正）
    base = app.file_manager.output_dir_path(sa.safe_title)  # 従来のUI動作
    base.mkdir(parents=True, exist_ok=True)

    # chat_file は毎回ベースから再計算
    sa.chat_file = str(base / f"{sa.safe_title}_chat.json")

    # video_file：親が base と違う/未設定なら必ず矯正（locked でも上書き）
    expected_video = base / f"{sa.safe_title}_1920x1080.mp4"
    if (not sa.video_file) or (Path(sa.video_file).parent != base):
        sa.video_file = str(expected_video)

    return True

def one_click_pipeline():
    """URL欄の動画に対して、全工程を順番に自動実行する"""
    def run():
        # URL → 各パス更新
        if update_paths_from_url() == False:
            return

        print("🚀 クリップ生成（ワンボタン）パイプライン開始")

        # ① チャット取得
        if not download_chat(skip_update_paths=True):
            return

        # ② 動画取得
        download_video()

        # ③ 分析（スレッド完了を待つことで ④ が先行しないようにする）
        t = analyze_and_plot(show_graph=False)
        t.join()  # valleys/peaks 完了を待つ

        # ④ セグメント生成（設定解像度のファイル名を優先）
        sa = app.stream_analysis

        video_path = sa.video_file
        #if not video_path:
        #    # 念のためURLから再設定を試みる
        #    update_paths_from_url()
        #   video_path = app.stream_analysis.video_file

        # 設定解像度（例: "1920x1080"）から期待ファイル名を組み立て
        res = str(settings.get("Resolution", "1920x1080")).lower()
        try:
            w, h = map(int, res.split("x"))
        except Exception:
            w, h = 1920, 1080  # 不正値は1080pにフォールバック

        # ベースディレクトリ（既存video_pathの親 or 作品ごとの出力先）
        base_dir = Path(video_path).parent if video_path else app.file_manager.output_dir_path(sa.safe_title)
        expected = base_dir / f"{sa.safe_title}_{w}x{h}.mp4"

        # 実在する最適なパスを選択
        if expected.exists():
            chosen = expected
        elif video_path and Path(video_path).exists():
            chosen = Path(video_path)
        else:
            fallback_1080 = base_dir / f"{sa.safe_title}_1920x1080.mp4"
            chosen = fallback_1080 if fallback_1080.exists() else expected  # 最後の手段としてexpected名

        generate_segments(str(chosen))

        # ⑤ クリップ生成（フォルダ）— セグメントフォルダを自動参照します
        generate_clips_from_folder(run_in_thread=False)

        app.show_info_message("完了", "『クリップ生成（ワンボタン）』の実行を開始しました。各工程の進捗はログに表示されます。")
        print("✅ パイプラインのキックまで完了")
    threading.Thread(target=run, daemon=True).start()

def download_chat(skip_update_paths: bool = False) -> bool:
    global app

    if (not skip_update_paths) and (not update_paths_from_url()):
        return False
    if os.path.exists(app.stream_analysis.chat_file):
        print("チャットファイルは既に存在します。")
        app.show_info_message("情報", "チャットファイルは既に存在します。")
        return True
    
    print("チャットデータダウンロード開始・・・", flush=True)
    cookie_path = RES_DIR_PATH / "cookies.txt"
    attempts = []
    if cookie_path.exists():
        attempts.append((
            "yt-chat-downloader(cookies)",
            lambda: _download_chat_via_yt_chat_downloader(app.stream_analysis.video_url, cookie_path)
        ))
    attempts.append((
        "yt-chat-downloader(no-cookies)",
        lambda: _download_chat_via_yt_chat_downloader(app.stream_analysis.video_url)
    ))

    errors = []
    for label, fetcher in attempts:
        print(f"チャット取得を試行: {label}")
        try:
            data = fetcher()
            if not data:
                raise RuntimeError("チャット件数が0でした")
            with open(app.stream_analysis.chat_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"✅ チャット保存完了 ({label}, {len(data)}件)")
            print("チャットデータダウンロード終了")
            app.show_info_message("完了", "チャットダウンロード完了！")
            return True
        except Exception as e:
            errors.append(f"{label}: {e}")
            print(f"⚠️ {label} 失敗: {e}")
            traceback.print_exc()

    err_text = "\n".join(errors[-4:])
    app.show_error_message("エラー", f"チャット取得に失敗しました:\n{err_text}")
    print("チャットデータダウンロード終了(失敗)")
    return False

def download_video():
    global app

    if not update_paths_from_url():
        return
    fileMgr = app.file_manager
    base_name = app.stream_analysis.safe_title
    save_dir = fileMgr.output_dir_path(base_name)
    print("動画ダウンロード開始・・・")
    # 🔸 ユーザー設定解像度
    resolution = settings.get("Resolution")
    target_width, target_height = map(int, resolution.lower().split("x"))
    # 🔸 保存ファイル名（元タイトルベース）
    base_output = save_dir / f"{base_name}_1920x1080.mp4"
    final_output = save_dir / f"{base_name}_{target_width}x{target_height}.mp4"
    print("動画(1920x1080)ダウンロード中・・・")
    # 🔹 yt-dlpで 1920x1080 ダウンロード
    subprocess.run([
        str(YTDLP_PATH),
        "--force-overwrites",
        "-f", "312+234/617+234/270+234/614+234/299+140/137+140/298+140/136+140/135+140/134+140/22/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best",
        "--merge-output-format", "mp4",
        "-o", str(base_output),
        "--cookies", str(RES_DIR_PATH / "cookies.txt"),
        app.stream_analysis.video_url
    ], check=True)
    print(f"✅ 動画(1920x1080)をダウンロード完了: {base_output.name}")
    # 🔹 ユーザー指定が1920x1080なら変換不要
    if resolution == "1920x1080":
        app.stream_analysis.video_file = str(base_output)
        app.show_info_message("完了", f"動画取得完了: {base_output.name}")
        return
    
    bgColor = aarrggbb_to_ffmpeg_color(settings.get("BackgroundColour"))
    # 🔹 アスペクト比維持＋黒帯で中央寄せ
    vf_filter = (
        f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease," 
        f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2:color={bgColor}"
    )
    print(f"動画(1920x1080)を使って{resolution}に編集中・・・")
    subprocess.run([
        str(FFMPEG_PATH), "-y",
        "-i", str(base_output),
        "-vf", vf_filter,
        "-c:v", "h264_nvenc",
        "-c:a", "copy",
        str(final_output)
    ], check=True)
    print(f"動画({resolution})編集終了")
    print(f"✅ {resolution} 動画をダウンロード完了: {base_output.name}")
    app.stream_analysis.video_file = str(final_output)
    app.show_info_message("完了", f"動画取得完了: {final_output.name}")

def analyze_and_plot(show_graph: bool = True) -> threading.Thread:
    global app

    def analyze():
        if not update_paths_from_url():
            return
        if not os.path.exists(app.stream_analysis.chat_file):
            app.show_warning_message("警告", "チャットファイルが存在しません。")
            return
        
        # 🎥 分析する動画ファイルを選択
        video_file = app.stream_analysis.video_file
        if not video_file:
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
        try:
            convert_to_wav(video_file, wav_file)
            if not os.path.exists(wav_file):
                raise FileNotFoundError(f"wav変換に失敗: {wav_file}")
            rms_values = extract_rms_numpy(wav_file)
        finally:
            if os.path.exists(wav_file):
                os.remove(wav_file)
        
        # X軸は1秒ごと（動画の長さ秒分）
        audio_x = np.arange(len(rms_values))
        app.stream_analysis.audio_x = audio_x
        app.stream_analysis.audio_y = rms_values
        print("動画音量(RMS)データを抽出終了")
        
        if show_graph:
            app.root.after(0, draw_graph)
        app.file_manager.save_analysis_results(app.stream_analysis)
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
            ax2.set_ylabel("音量（dB, 1秒毎）", fontname="Noto Sans JP")
    
        plt.xticks(app.stream_analysis.x, app.stream_analysis.x_labels)
        plt.xlabel("動画時間（時:分）")
        plt.ylabel("チャット数（5分単位）", fontname="Noto Sans JP")
        plt.title(app.stream_analysis.raw_title, fontname="Noto Sans JP")
        plt.grid()
        plt.legend(loc="upper left")
        plt.tight_layout()
        plt.show()
    t = threading.Thread(target=analyze)
    t.start()
    return t  # スレッドオブジェクトを返す

def generate_segments(video_file: str | None = None):
    global app
    fileMgr = app.file_manager
    segment_dir_path = fileMgr.segment_dir_path(app.stream_analysis.safe_title)

    if not app.stream_analysis.valleys or not app.stream_analysis.peaks:
        print("分析を行っていないのでセグメント生成を実行できませんでした。")
        return

    # ★引数が無いときだけダイアログを出す（既存の動作）
    if video_file is None:
        video_file = filedialog.askopenfilename(
            title="セグメント生成に使う動画ファイルを選択",
            filetypes=[("MP4 Files", "*.mp4")]
        )
        if not video_file:
            print("⚠️ 動画ファイルが選択されませんでした。処理を中止します。")
            return

    print("セグメント生成開始・・・")
    segment_dir_path.mkdir(parents=True, exist_ok=True)
    BUFFER = 180
    segment_count = 1
    segment_meta = []

    # ▼ valley-peak ペアで各セグメント作成（既存ロジックそのまま）
    pairs = extract_valley_peak_pairs(app.stream_analysis.valleys, app.stream_analysis.peaks)
    for start_valley, peak in pairs:
        start = start_valley - BUFFER
        if start <= 0:
            start = start_valley
        end = peak + BUFFER
        duration = end - start
        segment_path = segment_dir_path / f"segment_{segment_count:02}.mp4"
        subprocess.run([
            str(FFMPEG_PATH), "-y",
            "-ss", str(timedelta(seconds=start)),
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

    with open(segment_dir_path / "segment_info.json", "w", encoding="utf-8") as f:
        json.dump(segment_meta, f, ensure_ascii=False, indent=2)
    print("✅ セグメント生成が完了しました")
    
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

def get_video_duration_seconds(video_path: Path) -> float:
    """ffprobeで動画の実長(秒)を取得"""
    result = subprocess.run([
        str(FFPROBE_PATH), "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_path)
    ], capture_output=True, text=True, check=True)
    try:
        return float(result.stdout.strip())
    except Exception:
        return 0.0

def subtitle_and_danmaku_for_video_gui():
    """
    エクスプローラーで動画を1本選び、その動画に対して
    Whisper→校正→SRT→（あれば）弾幕→焼き付け までを一括実行
    """
    global app
    file_path = filedialog.askopenfilename(
        title="字幕＆弾幕を追加する動画を選択",
        filetypes=[("MP4ファイル", "*.mp4")]
    )
    if not file_path:
        print("⚠️ 動画ファイルが選択されませんでした。処理を中止します。")
        return

    # URL欄からsafe_title/chatパスなどを確定（未入力時は警告）
    if update_paths_from_url() == False:
        return

    try:
        apply_subtitle_and_danmaku_to_video(Path(file_path))
        app.show_info_message("完了", "選択した動画への字幕＆弾幕の追加が完了しました。")
    except Exception as e:
        traceback.print_exc()
        app.show_error_message("エラー", f"字幕＆弾幕の追加に失敗しました:\n{e}")
        
def add_danmaku_full_video_gui():
    """
    フル動画に chat.json のコメントを流す弾幕動画を生成（字幕は焼かない）。
    入力ダイアログ（ファイル選択/オフセット入力）はメインスレッドで行い、
    その後の重い処理（PNG生成/overlay）はワーカースレッドで実行する。
    出力: <元動画名>_danmaku.mp4（元動画と同じフォルダ）
    """
    global app

    # --- ① ここはメインスレッドで実行：入力ダイアログ ---
    vfile = filedialog.askopenfilename(
        parent=app.root,
        title="弾幕を焼き付けるフル動画を選択",
        filetypes=[("動画ファイル","*.mp4;*.mkv;*.mov;*.m4v;*.webm;*.avi"), ("すべてのファイル","*.*")]
    )
    if not vfile:
        print("⚠️ 動画が選択されませんでした。処理を中止します。")
        return
    video_path = Path(vfile)

    jfile = filedialog.askopenfilename(
        parent=app.root,
        title="chat.json を選択",
        filetypes=[("JSONファイル","*.json"), ("すべてのファイル","*.*")]
    )
    if not jfile:
        print("⚠️ chat.json が選択されませんでした。処理を中止します。")
        return
    chat_json_path = Path(jfile)

    off_text = simpledialog.askstring(
        "開始オフセット（任意）",
        "この動画が配信全体の中で開始する“絶対秒”を入力してください。\n"
        "（例）12345。未入力なら0として処理します。",
        parent=app.root
    )
    try:
        offset_sec = float(off_text.strip()) if (off_text and off_text.strip()) else 0.0
    except Exception:
        offset_sec = 0.0

    # --- ② 重い処理はワーカースレッドで ---
    def worker():
        try:
            dur = get_video_duration_seconds(video_path)
            abs_start = offset_sec
            abs_end   = offset_sec + dur

            comments = extract_comments_for_clip(chat_json_path, abs_start, abs_end)
            print(f"💬 対象コメント件数: {len(comments)}（範囲: {abs_start}〜{abs_end} 秒）")
            if not comments:
                app.show_warning_message(
                    "コメントなし",
                    "指定範囲にコメントが見つかりませんでした。\nオフセット秒が合っているかをご確認ください。"
                )
                return

            video_resolution = get_video_resolution(video_path)
            w, h = map(int, video_resolution.split("x"))
            font_path = CUSTOM_FONT_PATHS.get(settings.get("DanmakuFont"))
            fps = 30

            work_dir = video_path.parent / (video_path.stem + "_danmaku_frames")
            work_dir.mkdir(parents=True, exist_ok=True)

            print("🖼️ 弾幕PNG連番 生成中・・・")
            generate_comment_to_png_sequence(
                comments=comments,
                video_size=(w, h),
                out_frames_dir=work_dir,
                start_time=abs_start,
                end_time=abs_end,
                fps=fps,
                duration_per_comment=settings.get("DanmakuDuration"),
                font_path=font_path
            )

            out_path = video_path.with_name(video_path.stem + "_danmaku.mp4")
            print("🎛️ 動画と弾幕PNGの overlay 合成中・・・")
            combine_video_with_danmaku_overlay(
                clip_path=video_path,
                frames_dir=work_dir,
                out_path=out_path,
                fps=fps
            )

            print(f"✅ 完了: {out_path}")
            app.show_info_message("完了", f"弾幕動画を出力しました。\n{out_path}")

        except Exception as e:
            traceback.print_exc()
            app.show_error_message("エラー", f"弾幕追加に失敗しました:\n{e}")

    threading.Thread(target=worker, daemon=True).start()

def apply_subtitle_and_danmaku_to_video(video_path: Path):
    """
    1本の動画に対して、クリップ生成でやっている処理を“動画全体”に適用する。
    - segment_info.jsonにマッチすれば、その絶対秒でチャット抽出して弾幕生成
    - 見つからない場合は開始秒をダイアログで尋ね、未入力なら弾幕なしで字幕のみ
    出力は元動画と同じフォルダに *_final.mp4 を作る
    """
    global app, whisper_model
    fileMgr = app.file_manager
    segment_dir_path = fileMgr.segment_dir_path(app.stream_analysis.safe_title)
    output_dir_path = fileMgr.output_dir_path(app.stream_analysis.safe_title)
    segment_info_path = segment_dir_path / "segment_info.json"

    # 出力名
    stem = video_path.stem
    work_dir = output_dir_path / "clip" / stem
    work_dir.mkdir(parents=True, exist_ok=True)

    raw_srt_path = work_dir / f"{stem}_raw.srt"
    srt_path     = work_dir / f"{stem}.srt"
    frames_dir   = work_dir / f"danmaku_frames"
    overlay_out  = work_dir / f"{stem}_danmaku.mp4"
    final_out    = work_dir / f"{stem}_final.mp4"

    # 解析に必要な情報
    chat_json_path  = output_dir_path / f"{app.stream_analysis.safe_title}_chat.json"
    if not chat_json_path.exists():
        raise RuntimeError("チャットJSONがありません。先に「🛰️ チャットを取得」を実行してください。")

    # 可能ならsegment_info.jsonで絶対秒を自動特定
    abs_start = None
    abs_end   = None
    dur = get_video_duration_seconds(video_path)
    if segment_info_path.exists():
        try:
            with open(segment_info_path, "r", encoding="utf-8") as f:
                metas = json.load(f)
            hit = next((m for m in metas if m.get("file") == video_path.name), None)
            if hit:
                abs_start = float(hit["start_sec"])
                abs_end   = float(hit["end_sec"])
        except Exception:
            pass

    # 見つからなければ開始秒を聞く（空/キャンセルなら弾幕なしで進める）
    if abs_start is None:
        start_text = simpledialog.askstring(
            "開始秒を入力（任意）",
            "配信全体の中で、この動画の“開始秒”を入力してください。\n"
            "（例）12345\n\n未入力でOKすると弾幕なしで字幕だけ焼き付けます。"
        )
        if start_text and start_text.strip().isdigit():
            abs_start = float(start_text.strip())
            abs_end   = abs_start + (dur or 0.0)

    # ① Whisperで全文字幕
    print(f"📝 Whisperで文字起こし中: {video_path.name}")
    result = whisper_model.transcribe(str(video_path), language="ja", task="transcribe")
    segments = result.get("segments") or []
    if not segments:
        raise RuntimeError("Whisperのセグメントが空でした。")

    # ② セグメント微調整＆重複除去
    segments = adjust_segment_ends(str(video_path), segments)
    segments = remove_redundant_segments(segments)
    if not any(seg["text"].strip() for seg in segments):
        raise RuntimeError("有効な発話が検出できませんでした。")

    # ③ 校閲前SRT
    with open(raw_srt_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments):
            f.write(f"{i+1}\n{format_timestamp(seg['start'])} --> {format_timestamp(seg['end'])}\n{seg['text'].strip()}\n\n")

    # ④ ChatGPTで誤字脱字の軽微修正
    corrected = call_gpt_proofread_segments(segments)

    # ⑤ SRT書き出し（文が長いときは既存ロジックで分割）
    with open(srt_path, "w", encoding="utf-8") as f:
        entry_num = 1
        for corr in corrected:
            seg = segments[corr["index"]]
            text = corr["text"].strip()
            blocks = split_long_subtitle(text, 40) or [text]

            seg_start = seg["start"]
            seg_end   = seg["end"]
            total_chars = sum(len(b) for b in blocks) or 1
            t = seg_start
            for j, b in enumerate(blocks):
                block_ratio = len(b) / total_chars
                next_t = seg_end if j == len(blocks)-1 else (t + (seg_end - seg_start) * block_ratio)
                f.write(f"{entry_num}\n{format_timestamp(t)} --> {format_timestamp(next_t)}\n{b}\n\n")
                entry_num += 1
                t = next_t

    # ⑥ 弾幕（任意）→ PNG連番 → overlay
    used_base_for_subs = video_path  # デフォは元動画（弾幕なし）
    if abs_start is not None and abs_end is not None and abs_end > abs_start:
        comments = extract_comments_for_clip(chat_json_path, abs_start, abs_end)
        print(f"💬 弾幕コメント抽出: {len(comments)} 件")
        if comments:
            # 解像度とフォント
            video_resolution = get_video_resolution(video_path)
            w, h = map(int, video_resolution.split("x"))
            font_path = CUSTOM_FONT_PATHS.get(settings.get("DanmakuFont"))
            fps = 30
            generate_comment_to_png_sequence(
                comments=comments,
                video_size=(w, h),
                out_frames_dir=frames_dir,
                start_time=abs_start,
                end_time=abs_end,
                fps=fps,
                duration_per_comment=settings.get("DanmakuDuration"),
                font_path=font_path
            )
            combine_video_with_danmaku_overlay(
                clip_path=video_path,
                frames_dir=frames_dir,
                out_path=overlay_out,
                fps=fps
            )
            used_base_for_subs = overlay_out
        else:
            print("⚠️ 指定区間にコメントが見つからなかったため、弾幕はスキップします。")
    else:
        print("ℹ️ 絶対開始秒が不明のため、弾幕はスキップ（字幕のみ焼き付け）。")

    # ⑦ 字幕焼き付け（弾幕ありならoverlay後に）
    print("🔥 字幕焼き付け中・・・")
    generate_video(
        danmaku_video=used_base_for_subs,
        srt_path=srt_path,
        output_path=final_out
    )
    print(f"✅ 完了: {final_out}")

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

def calc_title_position(img, lines, font, settings):
    """
    settings: TitleAreaX, TitleAreaY, TitleAreaWidth, TitleAreaHeight, TitleAlignV, TitleAlignH
    lines: wrap_textで作成した行リスト
    """
    global app

    x0 = settings.get("TitleAreaX")
    y0 = settings.get("TitleAreaY")
    area_w = settings.get("TitleAreaWidth")
    area_h = settings.get("TitleAreaHeight")
    align_v = settings.get("TitleAlignV")
    align_h = settings.get("TitleAlignH")
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

def draw_title_on_img(img, title, font, settings):
    global app

    draw = ImageDraw.Draw(img)
    area_w = settings.get("TitleAreaWidth")
    # ラップ
    lines = wrap_title_text(title, font, area_w)
    # 位置
    x0, y, area_w, align_h, line_h = calc_title_position(img, lines, font, settings)
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

def generate_all_thumbnails_gui():
    global app
    fileMgr = app.file_manager
    output_dir_path = fileMgr.output_dir_path(app.stream_analysis.safe_title)
    
    mp4_path = filedialog.askopenfilename(
        title="サムネイル生成する元動画ファイルを選択",
        filetypes=[("MP4ファイル", "*.mp4")]
    )
    if not mp4_path:
        print("❌ 動画ファイルが選択されませんでした")
        return
    # ▼ サムネイル題名スタイル設定の取得（なければデフォルト）
    title_font_name = settings.get("TitleFont")
    title_font_size = settings.get("TitleFontSize")
    area_x = settings.get("TitleAreaX")
    area_y = settings.get("TitleAreaY")
    area_w = settings.get("TitleAreaWidth")
    area_h = settings.get("TitleAreaHeight")
    align_v = settings.get("TitleAlignV")    # "top", "center", "bottom"
    align_h = settings.get("TitleAlignH") # "left", "center", "right"
    font_path = CUSTOM_FONT_PATHS.get(title_font_name)
    video_path = Path(mp4_path)
    valleys = app.stream_analysis.valleys
    peaks = app.stream_analysis.peaks
    audio_y = app.stream_analysis.audio_y
    title = settings.get("ThumbnailTitle")
    if not valleys or not peaks or not audio_y:
        app.show_error_message("エラー", "グラフ分析データがありません（まず「分析してグラフを表示」を実行してください）")
        return
    # output/thumbnail フォルダ作成
    thumbnail_dir_path = output_dir_path / "thumbnail"
    thumbnail_dir_path.mkdir(parents=True, exist_ok=True)
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
        thumbnail_base_pattern = thumbnail_dir_path / (base_name + "_base_%d.jpg")  # ffmpeg出力パターン
        thumbnail_base_file = thumbnail_dir_path / (base_name + "_base_1.jpg")      # 実際の出力ファイル
        output_thumbnail = thumbnail_dir_path / (base_name + ".jpg")
        try:
            subprocess.run([
                str(FFMPEG_PATH), "-y",
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
                    font = ImageFont.truetype("Noto Sans JP", title_font_size)
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
            
            img = draw_title_on_img(img, title, font, settings_for_pos)
            img.save(output_thumbnail)
            thumbnail_base_file.unlink(missing_ok=True)
            print(f"✅ サムネイル生成: {output_thumbnail}")
        except Exception as e:
            print(f"❌ サムネイル生成失敗: segment{idx} {e}")
    app.show_info_message("完了", f"すべてのサムネイル画像を\noutput/thumbnail/\nに保存しました。")

def enqueue_current_url():
    global app
    url = app.entry.get().strip()
    if not url:
        app.show_warning_message("URL未入力", "YouTubeのURLを入力してください")
        return

    sa = StreamAnalysis(video_url=normalize_youtube_url(url), locked=True)

    with app.queue_lock:
        app.job_seq += 1
        # いま開いているプロジェクトの絶対パス（未選択なら None）
        proj = app.file_manager.project_file_path
        proj_abs = str(proj.resolve()) if proj else None

        job = OneClickJob(
            id=app.job_seq,
            sa=sa,
            settings_snapshot=copy.deepcopy(settings),
            project_dir=proj_abs          # ← ここで固定
        )
        app.queue_items.append(job)
        refresh_queue_ui_nolock()

    start_queue_worker_if_needed()


def refresh_queue_ui_nolock():
    global app
    if not app.queue_tree:
        return
    app.queue_tree.delete(*app.queue_tree.get_children())
    for j in app.queue_items:
        title = j.sa.safe_title or j.sa.video_url
        app.queue_tree.insert("", "end", values=(j.id, title, j.status))
    running = next((j for j in app.queue_items if j.status == "RUNNING"), None)
    if app.running_label:
        app.running_label.config(text=f"実行中: {running.sa.safe_title}" if running else "実行中: なし")


def remove_selected_queue_items():
    global app
    if not app.queue_tree:
        return
    sel = app.queue_tree.selection()
    if not sel:
        return
    ids_to_remove = {int(app.queue_tree.item(iid, "values")[0]) for iid in sel}
    with app.queue_lock:
        # 実行中は消さない
        app.queue_items = [j for j in app.queue_items if j.id not in ids_to_remove or j.status == "RUNNING"]
        refresh_queue_ui_nolock()


def clear_all_queue_items():
    global app
    with app.queue_lock:
        app.queue_items = [j for j in app.queue_items if j.status == "RUNNING"]
        refresh_queue_ui_nolock()


def start_queue_worker_if_needed():
    global app
    if app.queue_worker and app.queue_worker.is_alive():
        return
    app.queue_worker = threading.Thread(target=queue_worker_loop, daemon=True)
    app.queue_worker.start()


def queue_worker_loop():
    global app, settings
    while True:
        with app.queue_lock:
            job = next((j for j in app.queue_items if j.status == "QUEUED"), None)
            if not job:
                break
            job.status = "RUNNING"
            refresh_queue_ui_nolock()

        prev_settings = None
        prev_project_path = None
        try:
            app.current_job = job   # 実行中ジョブをアプリに登録
            app.is_oneclick_mode = True
            app.stream_analysis = job.sa

            # --- 設定を登録時スナップショットで上書き ---
            prev_settings = settings.copy()
            settings.clear()
            settings.update(job.settings_snapshot)

            # タイトル/各種パス確定（ジョブのURLで）
            if not update_paths_from_url():
                raise RuntimeError("URLからタイトル/各種パスの確定に失敗しました。")
            with app.queue_lock:
                refresh_queue_ui_nolock()

            # ①チャット → ②動画 → ③分析(join) → ④セグメント → ⑤クリップ
            if not download_chat(skip_update_paths=True):
                raise RuntimeError("チャット取得に失敗しました。")
            download_video()
            t = analyze_and_plot(show_graph=False)
            t.join()
            generate_segments(app.stream_analysis.video_file)
            
            # セグメント生成が終わるまで待機
            wait_for_segments_ready()
            
            generate_clips_from_folder()

            with app.queue_lock:
                job.status = "DONE"
                refresh_queue_ui_nolock()

        except Exception:
            import traceback; traceback.print_exc()
            with app.queue_lock:
                job.status = "ERROR"
                refresh_queue_ui_nolock()
        finally:
            # 設定を復元
            if prev_settings is not None:
                settings.clear()
                settings.update(prev_settings)
            # プロジェクトの参照を復元
            if prev_project_path is not None:
                app.file_manager._project_file_path = prev_project_path
            app.is_oneclick_mode = False
            app.current_job = None # アプリからジョブを削除

def main():
    global CUSTOM_FONT_PATHS, AVAILABLE_FONTS
    global app
    global whisper_model
    
    print(f"VigstreamClipの起動開始")
    
    # whisperの使用モデルを設定
    print(f"whisper(音声認識ライブラリ)の読み込み開始・・・")
    try:
        whisper_model = whisper.load_model("large-v3", device="cuda", download_root=str(MODEL_DIR_PATH))
    except Exception as e:
        print("CUDAでWhisper読み込みに失敗、CPUモードで再試行します:", e)
        whisper_model = whisper.load_model("large-v3", device="cpu", download_root=str(MODEL_DIR_PATH))
    print(f"whisper(音声認識ライブラリ)の読み込みが完了しました・・・")
    
    # 使用時にセット(chatgptのAPIキー)
    openai.api_key = load_api_key_from_file()

    # アプリケーション
    app = App()
    if app is None:
        print(f"アプリケーションの起動に失敗したため処理を終了します。")
        return
    app.setup("VigStreamClip")

    # ファイル管理
    fileMgr = app.file_manager
    if fileMgr is None:
        print(f"{App.FileManager.__name__}の取得に失敗しました。")
        return
    
    # 設定情報読み込み
    fileMgr.load_file_settings(app.settings)
    # 分析結果読み込み
    fileMgr.load_analysis_results(app.stream_analysis)
    
    CUSTOM_FONT_PATHS = scan_custom_fonts()
    AVAILABLE_FONTS += [f for f in CUSTOM_FONT_PATHS if f not in AVAILABLE_FONTS]
    
    print(f"アプリケーション実行開始します")
    # アプリケーションの実行処理
    app.run()

if __name__ == "__main__":
    main()
