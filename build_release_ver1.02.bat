@echo off
chcp 65001 > nul
REM === VigStreamClip を build/release/VigStreamClip_ver1.02 にビルド ===

echo pyinstaller最新版をインストールします...
pip install --upgrade pyinstaller

REM 設定
SET VER=ver1.02
SET NAME=VigStreamClip
SET DIST=build\release\%NAME%_%VER%
SET BUILD=build\release
SET SCRIPT=src\main.py

REM 出力先フォルダを作成
if not exist %DIST% (
    mkdir %DIST%
)

REM === yt-dlp.exe を Pythonの環境変数PATHから探してlibsにコピー ===
for /f "delims=" %%i in ('python -c "import shutil; print(shutil.which(''yt-dlp''))"') do set YTDLP_PATH=%%i

if not defined YTDLP_PATH (
    echo [エラー] yt-dlp.exe が環境変数PATHから見つかりません
    pause
    exit /b
)

copy /Y "%YTDLP_PATH%" libs\

REM PyInstaller で exe をビルド（--onedir）
pyinstaller ^
  --name=%NAME% ^
  --onedir ^
  --distpath %DIST% ^
  --workpath %BUILD% ^
  --clean ^
  --collect-data whisper ^
  --add-binary "libs/ffmpeg-7.1.1-full_build/bin/ffmpeg.exe;libs/ffmpeg-7.1.1-full_build/bin" ^
  --add-binary "libs/ffmpeg-7.1.1-full_build/bin/ffprobe.exe;libs/ffmpeg-7.1.1-full_build/bin" ^
  "%SCRIPT%"

REM リソースフォルダを出力先にコピー（上書きあり）
xcopy /E /I /Y assets %DIST%\assets
xcopy /E /I /Y fonts %DIST%\fonts
xcopy /E /I /Y models %DIST%\models
xcopy /E /I /Y libs %DIST%\libs

REM openai_key.txt を空で出力先に作成
echo. > %DIST%\assets\sec\openai_key.txt

echo.
echo ✅ ビルド完了！出力: %DIST%\%NAME%\%NAME%.exe
pause