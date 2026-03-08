@echo off
chcp 65001 > nul

REM === 繝薙Ν繝牙燕縺ｫdist/build/__pycache__螳悟・蜑企勁 ===
rmdir /S /Q dist
rmdir /S /Q build
rmdir /S /Q __pycache__

REM === VigStreamClip 繧・build/release/VigStreamClip_ver2.02 縺ｫ繝薙Ν繝・===

echo pyinstaller譛譁ｰ迚医ｒ繧､繝ｳ繧ｹ繝医・繝ｫ縺励∪縺・..
pip install --upgrade pyinstaller

REM 險ｭ螳・
SET VER=ver2.02
SET NAME=VigStreamClip
SET DIST=build\release\%NAME%_%VER%
SET BUILD=build\release
SET SCRIPT=src\main.py

REM 蜃ｺ蜉帛・繝輔か繝ｫ繝繧剃ｽ懈・
if not exist %DIST% (
    mkdir %DIST%
)


REM PyInstaller 縺ｧ exe 繧偵ン繝ｫ繝会ｼ・-onedir・・
pyinstaller ^
  --name=%NAME% ^
  --onedir ^
  --distpath %DIST% ^
  --workpath %BUILD% ^
  --clean ^
  --collect-data whisper ^
  --add-binary "libs/ffmpeg.exe;libs" ^
  --add-binary "libs/ffprobe.exe;libs" ^
  "%SCRIPT%"

REM 繝ｪ繧ｽ繝ｼ繧ｹ繝輔か繝ｫ繝繧貞・蜉帛・縺ｫ繧ｳ繝斐・・井ｸ頑嶌縺阪≠繧翫…ookies.txt縺ｯ髯､螟厄ｼ・
REM 豕ｨ諢・ robocopy 縺ｮ邨ゆｺ・さ繝ｼ繝・0・・ 縺ｯ謌仙粥謇ｱ縺・
REM /E: 繧ｵ繝悶ヵ繧ｩ繝ｫ繝蜷ｫ繧・育ｩｺ繧ゑｼ・
REM /MT:16: 荳ｦ蛻励さ繝斐・・・PU/繝・ぅ繧ｹ繧ｯ縺ｫ蜷医ｏ縺帙※隱ｿ謨ｴ蜿ｯ・・
REM /NFL /NDL /NJH /NJS /NP: 繝ｭ繧ｰ邁｡逡･蛹厄ｼ医♀螂ｽ縺ｿ縺ｧ
echo 繝輔か繝ｳ繝医ｒ繧ｳ繝斐・荳ｭ...
robocopy "fonts" "%DIST%\fonts" /E /MT:16 /NFL /NDL /NJH /NJS /NP
if %ERRORLEVEL% GEQ 8 exit /b %ERRORLEVEL%

echo 繝｢繝・Ν繧偵さ繝斐・荳ｭ...
robocopy "models" "%DIST%\models" /E /MT:16 /NFL /NDL /NJH /NJS /NP
if %ERRORLEVEL% GEQ 8 exit /b %ERRORLEVEL%

echo 繝ｩ繧､繝悶Λ繝ｪ繧偵さ繝斐・荳ｭ...
robocopy "libs" "%DIST%\libs" /E /MT:16 /NFL /NDL /NJH /NJS /NP
if %ERRORLEVEL% GEQ 8 exit /b %ERRORLEVEL%

echo 繝ｪ繧ｽ繝ｼ繧ｹ繧偵さ繝斐・荳ｭ・・ookies.txt 縺ｯ髯､螟厄ｼ・..
robocopy "res" "%DIST%\res" /E /MT:16 /XF cookies.txt /NFL /NDL /NJH /NJS /NP
if %ERRORLEVEL% GEQ 8 exit /b %ERRORLEVEL%

echo.
echo 笨・繝薙Ν繝牙ｮ御ｺ・ｼ∝・蜉・ %DIST%\%NAME%\%NAME%.exe
pause
