@echo off
REM Launch the Messel Pit Viewer in streaming mode (WebRTC).
REM
REM This runs senckenberg.messelpit.viewer_streaming.kit which is the base
REM Viewer kit + omni.kit.livestream.app for WebRTC streaming. Kit serves
REM the rendered viewport over WebRTC; a separate browser-side client
REM (NVIDIA-Omniverse/web-viewer-sample) connects to it.
REM
REM Pass --no-window to Kit so it doesn't open its own window competing
REM with the streamed client (per upstream USD Viewer streaming docs).
REM
REM Browser client setup (one-time):
REM   git clone https://github.com/NVIDIA-Omniverse/web-viewer-sample.git
REM   cd web-viewer-sample
REM   npm install
REM Then per-session:
REM   1. Run this script (launch_stream.bat) in one terminal
REM   2. cd web-viewer-sample && npm run dev   (in another terminal)
REM   3. Open http://localhost:5173 in Chrome/Edge on this machine
REM From a Meta Quest browser on the same Wi-Fi, replace localhost
REM with this PC's LAN IP (find with `ipconfig`).
REM
REM Same USD-path override as launch.bat: set MESSEL_USD to a different file.
REM Pass --no-auto to skip auto-loading and open a blank stage.

setlocal EnableDelayedExpansion

if "%MESSEL_USD%"=="" (
    set "MESSEL_CAND=%~dp0..\messelpit\out\messel_med.usd"
    if exist "!MESSEL_CAND!" (
        set "MESSEL_USD=!MESSEL_CAND!"
    ) else (
        set "MESSEL_USD=%~dp0..\messelpit\out\messel.usd"
    )
)

set "AUTO=1"
if /i "%~1"=="--no-auto" (
    set "AUTO=0"
    shift
)

pushd "%~dp0kit-app-template"
if "!AUTO!"=="1" (
    echo [launch_stream.bat] auto-loading: !MESSEL_USD!
    echo [launch_stream.bat] start web-viewer-sample with 'npm run dev' then open http://localhost:5173
    call .\repo.bat launch --name senckenberg.messelpit.viewer_streaming.kit -- --no-window "--/app/messelpit/load_usd=!MESSEL_USD!" %*
) else (
    echo [launch_stream.bat] auto-load disabled
    call .\repo.bat launch --name senckenberg.messelpit.viewer_streaming.kit -- --no-window %*
)
popd

endlocal
