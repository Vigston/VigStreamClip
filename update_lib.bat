@echo off
chcp 65001 > nul

REM ========================================
REM 最新の whisper をインストール
REM ========================================
echo Whisper最新版をインストールします...
python -m pip install -U openai-whisper

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