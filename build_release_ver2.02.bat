@echo off
chcp 65001 > nul

REM === ビルド前にdist/build/__pycache__完全削除 ===
rmdir /S /Q dist
rmdir /S /Q build
rmdir /S /Q __pycache__

REM === VigStreamClip を build/release/VigStreamClip_ver2.02 にビルド ===

echo pyinstaller最新版をインストールします...
pip install --upgrade pyinstaller

REM 設定
SET VER=ver2.02
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

REM リソースフォルダを出力先にコピー（上書きあり、cookies.txtは除外）
REM 注意: robocopy の終了コード 0～7 は成功扱い
REM /E: サブフォルダ含む（空も）
REM /MT:16: 並列コピー（CPU/ディスクに合わせて調整可）
REM /NFL /NDL /NJH /NJS /NP: ログ簡略化（お好みで
echo フォントをコピー中...
robocopy "fonts" "%DIST%\fonts" /E /MT:16 /NFL /NDL /NJH /NJS /NP
if %ERRORLEVEL% GEQ 8 exit /b %ERRORLEVEL%

echo モデルをコピー中...
robocopy "models" "%DIST%\models" /E /MT:16 /NFL /NDL /NJH /NJS /NP
if %ERRORLEVEL% GEQ 8 exit /b %ERRORLEVEL%

echo ライブラリをコピー中...
robocopy "libs" "%DIST%\libs" /E /MT:16 /NFL /NDL /NJH /NJS /NP
if %ERRORLEVEL% GEQ 8 exit /b %ERRORLEVEL%

echo リソースをコピー中（cookies.txt は除外）...
robocopy "res" "%DIST%\res" /E /MT:16 /XF cookies.txt /NFL /NDL /NJH /NJS /NP
if %ERRORLEVEL% GEQ 8 exit /b %ERRORLEVEL%

echo.
echo ✅ ビルド完了！出力: %DIST%\%NAME%\%NAME%.exe
pause