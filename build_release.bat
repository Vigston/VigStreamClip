@echo off
REM === PyInstaller を使って src/main.py をビルドする ===

REM 設定
SET NAME=MyApp
SET DIST=release
SET BUILD=pybuild
SET SCRIPT=src/main.py

REM 出力先フォルダがなければ作成
if not exist %DIST% (
    mkdir %DIST%
)

REM 実行ファイルのビルド
pyinstaller ^
  --name=%NAME% ^
  --onefile ^
  --noconsole ^
  --distpath %DIST% ^
  --workpath %BUILD% ^
  --clean ^
  --add-data "assets/sec/openai_key.txt;assets/sec" ^
  --add-data "res/subtitle_style_help.txt;res" ^
  --add-data "lib/ffmpeg-master-latest-win64-gpl-shared/bin/ffmpeg.exe;." ^
  --add-data "lib/ffmpeg-master-latest-win64-gpl-shared/bin/ffprobe.exe;." ^
  --add-data "fonts;fonts" ^
  "%SCRIPT%"

echo.
echo ✅ ビルド完了！出力: %DIST%\%NAME%.exe
pause