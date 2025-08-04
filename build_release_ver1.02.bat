@echo off
chcp 65001 > nul

REM === ビルド前にdist/build/__pycache__完全削除 ===
rmdir /S /Q dist
rmdir /S /Q build
rmdir /S /Q __pycache__

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

REM custom_formats.json の絶対パスをPythonで取得
for /f "delims=" %%F in ('python -c "import chat_downloader.formatting, os; print(os.path.join(os.path.dirname(chat_downloader.formatting.__file__), 'custom_formats.json'))"') do set FORMATS_JSON=%%F

REM PyInstaller で exe をビルド（--onedir）
pyinstaller ^
  --name=%NAME% ^
  --onedir ^
  --distpath %DIST% ^
  --workpath %BUILD% ^
  --clean ^
  --collect-data whisper ^
  --add-binary "libs/ffmpeg.exe;libs" ^
  --add-binary "libs/ffprobe.exe;libs" ^
  --add-data "%FORMATS_JSON%;chat_downloader/formatting" ^
  "%SCRIPT%"

REM リソースフォルダを出力先にコピー（上書きあり）
xcopy /E /I /Y fonts %DIST%\fonts
xcopy /E /I /Y models %DIST%\models
xcopy /E /I /Y libs %DIST%\libs
xcopy /E /I /Y res %DIST%\res

REM openai_key.txt を空で出力先に作成
echo. > %DIST%\res\openai_key.txt

echo.
echo ✅ ビルド完了！出力: %DIST%\%NAME%\%NAME%.exe
pause