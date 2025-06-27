@echo off
setlocal enabledelayedexpansion

for %%D in (%*) do (
    if exist "%%~fD" (
        echo 🔍 処理中のフォルダ: %%~nxD

        pushd "%%~fD"

        for %%F in (clip_*.mp4) do (
            set "mp4=%%~fF"
            set "name=%%~nF"
            set "srt=%%~dpF!name!.srt"
            set "out=%%~dpF!name!_subtitled.mp4"

            if exist "!srt!" (
                echo 🔧 字幕焼き込み中: !name!.mp4 + !name!.srt

                rem パスをffmpeg用にエスケープ（コロンとバックスラッシュをエスケープ）
                set "srt_fixed=!srt:\=\\!"
                set "srt_fixed=!srt_fixed::=\:!"

                ffmpeg -y -i "!mp4!" -vf "subtitles='!srt_fixed!'" -c:v h264_nvenc -c:a copy "!out!"
                echo ✅ 完了: !name!_subtitled.mp4
            ) else (
                echo ⚠️ 字幕ファイルが見つかりません: !srt!
            )
        )

        popd
    ) else (
        echo ❌ 無効なフォルダ: %%~fD
    )
)

pause