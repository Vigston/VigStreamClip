import torch
print(torch.cuda.is_available())  # TrueならGPUが使える状態

"""
import yt_dlp

url = 'https://www.youtube.com/watch?v=HH7ptfUnPSY'

# 出力形式や画質を指定
ydl_opts = {
    'format': 'bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]/best[ext=mp4]',
    'outtmpl': 'C:/Vigston/StreamClips/VigslibStreamClip/res/sample_video.%(ext)s'
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.download([url])

print("ダウンロード完了！")
"""