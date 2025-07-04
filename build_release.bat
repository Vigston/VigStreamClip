@echo off
REM === VigStreamClip を build/release/VigStreamClip_ver0.00 にビルド ===

REM 設定
SET VER=VigStreamClip_ver0.00
SET NAME=VigStreamClip
SET DIST=build\release\%VER%
SET BUILD=build\release
SET SCRIPT=src/main.py

REM 出力先フォルダを作成
if not exist %DIST% (
    mkdir %DIST%
)

REM PyInstaller で exe をビルド
pyinstaller ^
  --name=%NAME% ^
  --onefile ^
  --noconsole ^
  --distpath %DIST% ^
  --workpath %BUILD% ^
  --clean ^
  --add-data "assets;assets" ^
  --add-data "res;res" ^
  --add-data "fonts;fonts" ^
  "%SCRIPT%"

REM リソースフォルダを出力先にコピー（上書きあり）
xcopy /E /I /Y assets %DIST%\assets
xcopy /E /I /Y res %DIST%\res
xcopy /E /I /Y fonts %DIST%\fonts

echo.
echo ✅ ビルド完了！出力: %DIST%\%NAME%.exe
pause