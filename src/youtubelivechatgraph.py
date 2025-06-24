import os
import subprocess
import json
import re
from collections import defaultdict
import matplotlib.pyplot as plt
from datetime import timedelta

# 🎯 対象のYouTube動画URL
VIDEO_URL = "https://www.youtube.com/watch?v=CeznVFMOXBU"

# フォント設定（日本語対応）
plt.rcParams['font.family'] = 'Yu Gothic'

# 📁 出力フォルダ設定
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 🎥 動画タイトル取得
title_result = subprocess.run([
    "python", "-m", "yt_dlp", "--get-title", VIDEO_URL
], capture_output=True, text=True, shell=True, encoding="utf-8")

if title_result.returncode != 0 or not title_result.stdout.strip():
    raise RuntimeError("動画タイトルが取得できませんでした")

raw_title = title_result.stdout.strip()
safe_title = re.sub(r'[\\/*?:"<>|]', "_", raw_title)

# 出力ファイル名
CHAT_FILE = os.path.join(OUTPUT_DIR, f"{safe_title}_chat.json")
VIDEO_FILE = os.path.join(OUTPUT_DIR, f"{safe_title}.mp4")

# ✅ チャット取得
if not os.path.exists(CHAT_FILE):
    print(f"🛰️ チャット取得中... ({CHAT_FILE})")
    subprocess.run([
        "python", "-m", "chat_downloader", VIDEO_URL,
        "--output", CHAT_FILE
    ])

# ✅ 動画取得
if not os.path.exists(VIDEO_FILE):
    print(f"🎬 動画ダウンロード中... ({VIDEO_FILE})")
    subprocess.run([
        "yt-dlp",
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]",
        "--merge-output-format", "mp4",
        "-o", VIDEO_FILE,
        VIDEO_URL
    ])

# 📂 チャット読み込み
with open(CHAT_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

# ⏱️ 5分ごとにチャット集計
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

# 📊 グラフ描画
if not chat_counts:
    print("❗チャットが見つかりませんでした")
else:
    x = sorted(chat_counts.keys())
    y = [chat_counts[t] for t in x]
    x_labels = [f"{s//3600}:{(s//60)%60:02}" for s in x]

    plt.figure(figsize=(12, 5))
    plt.plot(x_labels, y, label="チャット数")

    valley_times = []
    peak_times = []

    for i in range(1, len(y) - 1):
        t = x[i]
        label = f"{int(t//3600):02}:{int((t%3600)//60):02}:{int(t%60):02}"

        if y[i - 1] > y[i] < y[i + 1]:
            plt.plot(x_labels[i], y[i], 'ro', label='谷（下→上）' if i == 1 else "")
            valley_times.append(t)

        elif y[i - 1] < y[i] > y[i + 1]:
            plt.plot(x_labels[i], y[i], 'bo', label='谷（上→下）' if i == 1 else "")
            peak_times.append(t)

    # 🎬 赤→青間を動画クリップ
    SEGMENT_DIR = os.path.join(OUTPUT_DIR, "segments")
    os.makedirs(SEGMENT_DIR, exist_ok=True)

    segment_count = 1
    BUFFER = 300  # 5分

    for v_sec in valley_times:
        next_peaks = [p for p in peak_times if p > v_sec]
        if not next_peaks:
            continue
        p_sec = next_peaks[0]

        start = max(0, v_sec - BUFFER)
        end = p_sec + BUFFER
        duration = end - start

        segment_path = os.path.join(SEGMENT_DIR, f"segment_{segment_count:02}.mp4")

        subprocess.run([
            "ffmpeg",
            "-ss", str(timedelta(seconds=start)),
            "-i", VIDEO_FILE,
            "-t", str(timedelta(seconds=duration)),
            "-c", "copy",
            segment_path
        ])

        print(f"🎬 Segment {segment_count:02} saved: {segment_path}")
        segment_count += 1
    
    plt.xlabel("動画時間（時:分）")
    plt.ylabel("チャット数（5分単位）")
    plt.title(f"{raw_title} - チャット盛り上がり可視化")
    plt.grid()
    plt.legend()
    plt.tight_layout()
    plt.show()