@echo off
chcp 65001 > nul

REM ========================================
REM 最新の whisper をインストール
REM ========================================
echo Whisper最新版をインストールします...
python -m pip install -U openai-whisper

REM ========================================
REM 最新の large-v3 モデルを取得・更新
REM ========================================
set MODEL_DIR=models
set MODEL_PATH=%MODEL_DIR%\large-v3.pt

REM モデル保存用ディレクトリを作成
if not exist %MODEL_DIR% (
    mkdir %MODEL_DIR%
)

REM 既存のモデルがある場合は削除（強制的に最新を再取得）
if exist %MODEL_PATH% (
    del /Q %MODEL_PATH%
)

echo Whisper large-v3 モデルをダウンロードします...
python -c "import whisper; whisper.load_model('large-v3', download_root=r'%MODEL_DIR%')"

echo ✅ large-v3 モデルを更新しました: %MODEL_PATH%

REM ========================================
REM custom_formats.json を libs/chat_downloader/formatting にコピー
REM ========================================
for /f "delims=" %%F in ('python -c "import chat_downloader.formatting, os; print(os.path.join(os.path.dirname(chat_downloader.formatting.__file__), 'custom_formats.json'))"') do set FORMATS_JSON=%%F

if not exist libs\chat_downloader\formatting (
    mkdir libs\chat_downloader\formatting
)

copy /Y "%FORMATS_JSON%" libs\chat_downloader\formatting\ > nul

echo ✅ custom_formats.json を libs\chat_downloader\formatting\ にコピーしました: %FORMATS_JSON%

pause