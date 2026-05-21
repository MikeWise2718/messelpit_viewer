@echo off
REM Launch the Messel Pit Viewer in streaming mode (WebRTC).
REM
REM This runs senckenberg.messelpit.viewer_streaming.kit which is the base
REM Viewer kit + omni.kit.livestream.app for WebRTC streaming. Kit serves
REM a WebRTC endpoint locally; connect from a browser to view.
REM
REM Default test client (Chrome/Edge on this machine):
REM   open kit-app-template/_build/windows-x86_64/release/extscache/omni.kit.livestream.webrtc-*/web/index.html
REM (the exact path depends on the cached version)
REM
REM From a Meta Quest browser on the same Wi-Fi:
REM   http://<this-PC-LAN-IP>:8011
REM (find IP with `ipconfig` -> IPv4 Address of the active adapter)
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
    echo [launch_stream.bat] WebRTC endpoint will be on port 8011 once Kit is up
    call .\repo.bat launch --name senckenberg.messelpit.viewer_streaming.kit -- "--/app/messelpit/load_usd=!MESSEL_USD!" %*
) else (
    echo [launch_stream.bat] auto-load disabled
    call .\repo.bat launch --name senckenberg.messelpit.viewer_streaming.kit -- %*
)
popd

endlocal
