import os
import subprocess
import json
import re
from collections import defaultdict
import threading
import urllib.parse
import tkinter as tk
from tkinter import messagebox

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from datetime import timedelta

plt.rcParams["font.family"] = "Yu Gothic"


def normalize_youtube_url(url: str) -> str:
    """URLの?t=xxx や &t=xxx を除去する"""
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query)
    query.pop("t", None)
    new_query = urllib.parse.urlencode(query, doseq=True)
    return urllib.parse.urlunparse(parsed._replace(query=new_query))


def main():
    OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "output"))
    SEGMENT_DIR = os.path.join(OUTPUT_DIR, "segments")
    os.makedirs(SEGMENT_DIR, exist_ok=True)

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
        state["chat_file"] = os.path.join(OUTPUT_DIR, f"{state['safe_title']}_chat.json")
        state["video_file"] = os.path.join(OUTPUT_DIR, f"{state['safe_title']}.mp4")
        return True

    def download_chat():
        if not update_paths_from_url():
            return
        if os.path.exists(state["chat_file"]):
            messagebox.showinfo("情報", "チャットファイルは既に存在します。")
            return
        try:
            subprocess.run([
                "python", "-m", "chat_downloader", state["video_url"],
                "--output", state["chat_file"]
            ])
            messagebox.showinfo("完了", "チャットダウンロード完了！")
        except Exception as e:
            messagebox.showerror("エラー", str(e))

    def download_video():
        if not update_paths_from_url():
            return
        if os.path.exists(state["video_file"]):
            messagebox.showinfo("情報", "動画ファイルは既に存在します。")
            return
        try:
            subprocess.run([
                "yt-dlp",
                "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]",
                "--merge-output-format", "mp4",
                "-o", state["video_file"],
                state["video_url"]
            ])
            messagebox.showinfo("完了", "動画ダウンロード完了！")
        except Exception as e:
            messagebox.showerror("エラー", str(e))

    def analyze_and_plot():
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

        if not chat_counts:
            messagebox.showinfo("情報", "チャットが見つかりませんでした")
            return

        x = sorted(chat_counts.keys())
        y = [chat_counts[t] for t in x]
        x_labels = [f"{s//3600}:{(s//60)%60:02}" for s in x]
        valleys, peaks = [], []

        plt.figure(figsize=(12, 5))
        plt.plot(x_labels, y, label="チャット数")

        for i in range(1, len(y) - 1):
            t = x[i]
            if y[i - 1] > y[i] < y[i + 1]:
                plt.plot(x_labels[i], y[i], 'ro', label='谷（下→上）' if i == 1 else "")
                valleys.append(t)
            elif y[i - 1] < y[i] > y[i + 1]:
                plt.plot(x_labels[i], y[i], 'bo', label='谷（上→下）' if i == 1 else "")
                peaks.append(t)

        state.update({
            "x": x,
            "y": y,
            "x_labels": x_labels,
            "valleys": valleys,
            "peaks": peaks
        })

        plt.xlabel("動画時間（時:分）")
        plt.ylabel("チャット数（5分単位）")
        plt.title(f"{state['raw_title']} - チャット盛り上がり可視化")
        plt.grid()
        plt.legend()
        plt.tight_layout()
        plt.show()

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
            segment_path = os.path.join(SEGMENT_DIR, f"segment_{segment_count:02}.mp4")

            subprocess.run([
                "ffmpeg",
                "-ss", str(timedelta(seconds=start)),
                "-i", state["video_file"],
                "-t", str(timedelta(seconds=duration)),
                "-c", "copy",
                segment_path
            ])
            print(f"🎬 Segment {segment_count:02} saved: {segment_path}")
            segment_count += 1

        messagebox.showinfo("完了", "セグメント生成が完了しました！")

    # === GUI構築 ===
    global root
    root = tk.Tk()
    root.title("YouTubeチャット＆動画処理ツール")

    frame = tk.Frame(root, padx=20, pady=20)
    frame.pack()

    label = tk.Label(frame, text="YouTube動画URLを入力:")
    label.pack()

    entry = tk.Entry(frame, width=70)
    entry.pack(pady=5)

    tk.Button(frame, text="🛰️ チャットを取得", command=lambda: threading.Thread(target=download_chat).start()).pack(pady=5)
    tk.Button(frame, text="🎬 動画を取得", command=lambda: threading.Thread(target=download_video).start()).pack(pady=5)
    tk.Button(frame, text="📊 分析してグラフを表示", command=lambda: threading.Thread(target=analyze_and_plot).start()).pack(pady=10)
    tk.Button(frame, text="✂️ セグメント動画生成", command=lambda: threading.Thread(target=generate_segments).start()).pack(pady=5)

    root.mainloop()


if __name__ == "__main__":
    main()