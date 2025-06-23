import os
import cv2
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import SpanSelector
import yt_dlp

plt.rcParams['font.family'] = 'Noto Sans JP'

VIDEO_FILENAME = "video.mp4"
YOUTUBE_URL = "https://www.youtube.com/watch?v=HH7ptfUnPSY"

def download_youtube_video(url: str, output_path: str = VIDEO_FILENAME):
    ydl_opts = {
        'outtmpl': output_path,
        'format': 'bestvideo+bestaudio/best',
        'merge_output_format': 'mp4'
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

def get_frame_count_and_fps(cap):
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    return frame_count, fps

def frame_to_time(frame_idx, fps):
    seconds = frame_idx / fps
    return f"{int(seconds // 60):02}:{int(seconds % 60):02}"

def show_video_with_graph(video_path):
    cap = cv2.VideoCapture(video_path)
    frame_count, fps = get_frame_count_and_fps(cap)

    # ダミーデータ
    x = np.linspace(0, frame_count, 100)
    popularity = np.random.rand(100) * 100
    comments = np.random.rand(100) * 50

    # 最初のフレームを読み込む
    ret, frame = cap.read()
    if not ret:
        print("⚠️ フレームが読み込めませんでした")
        cap.release()
        return

    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # 元動画の縦横比
    height, width, _ = frame_rgb.shape
    aspect_ratio = width / height

    # figsizeを横長の比率に合わせる
    fig_width = 12
    fig_height = fig_width / aspect_ratio + 2  # +2 はグラフ表示スペース

    fig, ax = plt.subplots(2, 1, figsize=(fig_width, fig_height), gridspec_kw={'height_ratios': [1, aspect_ratio]})
    fig.subplots_adjust(hspace=0.4)

    # 上のグラフ
    ax[0].plot(x, popularity, label="人気度", color="blue")
    ax[0].plot(x, comments, label="チャット数", color="green")
    ax[0].set_title("再生位置ごとの人気度・チャット数")
    ax[0].legend()

    # 再生位置インジケーター
    current_frame_line = ax[0].axvline(x=0, color='red', linestyle='--', linewidth=2)

    # 下の動画表示用Axes
    img_ax = ax[1]
    img_ax.axis("off")
    img = img_ax.imshow(frame_rgb, aspect='equal')  # アスペクト比固定

    def update_frame(target_frame):
        cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        ret, frame = cap.read()
        if ret:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img.set_data(frame_rgb)
            current_frame_line.set_xdata([target_frame])
            fig.suptitle(f"フレーム: {target_frame} / 時間: {frame_to_time(target_frame, fps)}")
            fig.canvas.draw_idle()

    # スパン選択でフレーム更新
    def onselect(xmin, xmax):
        target_frame = int((xmin + xmax) / 2)
        update_frame(target_frame)

    # クリックでフレーム更新
    def onclick(event):
        if event.inaxes != ax[0] or event.xdata is None:
            return
        target_frame = int(event.xdata)
        update_frame(target_frame)

    # イベント接続
    fig.canvas.mpl_connect("button_press_event", onclick)

    # スパンセレクター接続
    span = SpanSelector(
        ax[0], onselect, 'horizontal', useblit=True,
        props=dict(facecolor="red", alpha=0.3),
        interactive=True
    )

    plt.show()
    cap.release()

if __name__ == "__main__":
    if not os.path.exists(VIDEO_FILENAME):
        print("📥 動画をダウンロード中…")
        download_youtube_video(YOUTUBE_URL)
        print("✅ ダウンロード完了！")

    print("🎞️ ビューアを起動中…")
    show_video_with_graph(VIDEO_FILENAME)