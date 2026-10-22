@echo off
rem Encode the Movie Render Queue frames of SEQ_Fly (tools/ue_12_fly.py) into an MP4 for sharing.
rem usage: encode_fly.cmd [frame folder under export\renders, default fly_final]
setlocal
set FF=C:\Users\user\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe
set DIR=G:\Claude\mongha-ue\export\renders\%~1
if "%~1"=="" set DIR=G:\Claude\mongha-ue\export\renders\fly_final
"%FF%" -y -loglevel error -framerate 24 -i "%DIR%\fly_%%04d.png" -c:v libx264 -preset slow -crf 17 -pix_fmt yuv420p -movflags +faststart "G:\Claude\mongha-ue\export\MongHa_2010_UE_flythrough.mp4"
echo written G:\Claude\mongha-ue\export\MongHa_2010_UE_flythrough.mp4
