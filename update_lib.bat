@echo off
chcp 65001 > nul

REM ========================================
REM Update openai-whisper
REM ========================================
echo Installing latest openai-whisper...
python -m pip install -U openai-whisper
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to install openai-whisper.
    pause
    exit /b 1
)

REM ========================================
REM Refresh large-v3 model
REM ========================================
set MODEL_DIR=models
set MODEL_PATH=%MODEL_DIR%\large-v3.pt

if not exist %MODEL_DIR% (
    mkdir %MODEL_DIR%
)

if exist %MODEL_PATH% (
    del /Q %MODEL_PATH%
)

echo Downloading Whisper large-v3 model...
python -c "import whisper; whisper.load_model('large-v3', download_root=r'%MODEL_DIR%')"
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to download large-v3 model.
    pause
    exit /b 1
)

echo [DONE] Model refreshed: %MODEL_PATH%
pause
