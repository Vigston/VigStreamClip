@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 > nul

if /I not "%~1"=="__RUNNING__" (
    echo(!CMDCMDLINE!| findstr /I " /c " > nul
    if %ERRORLEVEL% EQU 0 (
        cmd /k ""%~f0" __RUNNING__"
        exit /b
    )
)

cd /d "%~dp0"

set "VENV_DIR=.venv"
set "VENV_PY=%CD%\%VENV_DIR%\Scripts\python.exe"
set "PY_CMD="

py -3 -c "import sys" > nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PY_CMD=py -3"
) else (
    python -c "import sys" > nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        set "PY_CMD=python"
    )
)

if not defined PY_CMD (
    echo [ERROR] Python 3 is not installed or not available on PATH.
    echo [INFO] Install Python 3 first, then re-run setup_venv.bat.
    pause
    exit /b 1
)

if exist "%VENV_PY%" (
    echo [INFO] Existing virtual environment found: %VENV_DIR%
) else (
    echo [INFO] Creating virtual environment in %CD%\%VENV_DIR%
    %PY_CMD% -m venv "%VENV_DIR%"

    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

if not exist "%VENV_PY%" (
    echo [ERROR] Virtual environment python not found: %VENV_PY%
    pause
    exit /b 1
)

echo [INFO] Upgrading pip/setuptools/wheel...
"%VENV_PY%" -m pip install --upgrade pip setuptools wheel
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to upgrade pip tooling.
    pause
    exit /b 1
)

set "TORCH_CUDA_INDEX_1=https://download.pytorch.org/whl/cu130"
set "TORCH_CUDA_INDEX_2=https://download.pytorch.org/whl/cu128"
set "TORCH_CPU_INDEX=https://download.pytorch.org/whl/cpu"
set "TORCH_INSTALLED="

echo [INFO] Installing PyTorch...
where nvidia-smi > nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [INFO] NVIDIA GPU detected. Trying CUDA PyTorch wheel cu130...
    "%VENV_PY%" -m pip install --upgrade torch torchvision torchaudio --index-url %TORCH_CUDA_INDEX_1%
    if %ERRORLEVEL% EQU 0 (
        set "TORCH_INSTALLED=1"
    ) else (
        echo [WARN] cu130 install failed. Trying cu128...
        "%VENV_PY%" -m pip install --upgrade torch torchvision torchaudio --index-url %TORCH_CUDA_INDEX_2%
        if %ERRORLEVEL% EQU 0 (
            set "TORCH_INSTALLED=1"
        ) else (
            echo [WARN] CUDA PyTorch install failed. Falling back to CPU wheel...
        )
    )
) else (
    echo [INFO] NVIDIA GPU not detected. Installing CPU PyTorch wheel...
)

if not defined TORCH_INSTALLED (
    "%VENV_PY%" -m pip install --upgrade torch torchvision torchaudio --index-url %TORCH_CPU_INDEX%
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to install PyTorch.
        pause
        exit /b 1
    )
)

echo [INFO] Verifying torch runtime...
"%VENV_PY%" -c "import torch; print('[INFO] torch', torch.__version__, 'cuda', torch.version.cuda, 'cuda_available', torch.cuda.is_available()); print('[INFO] gpu', torch.cuda.get_device_name(0)) if torch.cuda.is_available() else None; print('[INFO] arch_list', torch.cuda.get_arch_list()) if torch.cuda.is_available() else None"

echo [INFO] Installing project dependencies...
"%VENV_PY%" -m pip install ^
    openai-whisper ^
    matplotlib ^
    openai ^
    fonttools ^
    numpy ^
    soundfile ^
    pillow ^
    yt-chat-downloader ^
    pydub ^
    pyopengltk ^
    PyOpenGL

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo [DONE] Environment setup complete.
echo [INFO] Activate with: call %VENV_DIR%\Scripts\activate
pause
exit /b 0
