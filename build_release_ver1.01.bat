@echo off
chcp 65001 > nul
REM === VigStreamClip を build/release/VigStreamClip_ver1.01 にビルド ===

echo pyinstaller最新版をインストールします...
pip install --upgrade pyinstaller

REM 設定
SET VER=ver1.01
SET NAME=VigStreamClip
SET DIST=build\release\%NAME%_%VER%
SET BUILD=build\release
SET SCRIPT=src\main.py

REM 出力先フォルダを作成
if not exist %DIST% (
    mkdir %DIST%
)

REM PyInstaller で exe をビルド
pyinstaller ^
  --name=%NAME% ^
  --onefile ^
  --distpath %DIST% ^
  --workpath %BUILD% ^
  --clean ^
  --add-data "assets;assets" ^
  --add-data "fonts;fonts" ^
  --add-binary "libs/ffmpeg-7.1.1-full_build/bin/ffmpeg.exe;libs/ffmpeg-7.1.1-full_build/bin" ^
  --add-binary "libs/ffmpeg-7.1.1-full_build/bin/ffprobe.exe;libs/ffmpeg-7.1.1-full_build/bin" ^
  "%SCRIPT%"

REM リソースフォルダを出力先にコピー（上書きあり）
xcopy /E /I /Y assets %DIST%\assets
xcopy /E /I /Y fonts %DIST%\fonts
xcopy /E /I /Y models %DIST%\models
xcopy /E /I /Y libs %DIST%\libs

echo.
echo ✅ ビルド完了！出力: %DIST%\%NAME%.exe
pause