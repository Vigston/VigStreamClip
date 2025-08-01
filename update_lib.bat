@echo off
chcp 65001 > nul

REM ========================================
REM 最新の yt-dlp と whisper をインストール
REM ========================================
echo yt-dlp最新版をインストールします...
python -m pip install -U yt-dlp

echo Whisper最新版をインストールします...
python -m pip install -U openai-whisper

REM ========================================
REM yt-dlp.exe を環境変数 PATH から探して libs にコピー
REM ========================================
echo yt-dlp.exe を検索して libs にコピーします...

REM libs フォルダがなければ作成
if not exist libs (
    mkdir libs
)

REM Python から yt-dlp.exe のパスを取得して環境変数に格納
for /f "delims=" %%i in ('python -c "import shutil; print(shutil.which('yt-dlp'))"') do set YTDLP_PATH=%%i

REM 見つからなかった場合のエラーハンドリング
if not defined YTDLP_PATH (
    echo [エラー] yt-dlp.exe が見つかりませんでした。PATH を確認してください。
    pause
    exit /b
)

REM コピーを実行
copy /Y "%YTDLP_PATH%" libs\yt-dlp.exe > nul

echo ✅ yt-dlp.exe を libs\ にコピーしました: %YTDLP_PATH%

REM ========================================
REM custom_formats.json を libs/chat_downloader/formatting にコピー
REM ========================================

REM Python から custom_formats.json の絶対パスを取得
for /f "delims=" %%F in ('python -c "import chat_downloader.formatting, os; print(os.path.join(os.path.dirname(chat_downloader.formatting.__file__), 'custom_formats.json'))"') do set FORMATS_JSON=%%F

REM コピー先ディレクトリを作成
if not exist libs\chat_downloader\formatting (
    mkdir libs\chat_downloader\formatting
)

REM ファイルをコピー
copy /Y "%FORMATS_JSON%" libs\chat_downloader\formatting\ > nul

echo ✅ custom_formats.json を libs\chat_downloader\formatting\ にコピーしました: %FORMATS_JSON%

pause