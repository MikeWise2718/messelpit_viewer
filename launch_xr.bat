@echo off
REM Launch the Messel Pit VR variant (OpenXR -> SteamVR/Oculus -> Quest 2 via Air Link).
REM
REM Prerequisites on the PC (one-time setup):
REM   1. Oculus PC app installed and running (for Air Link bridge to Quest)
REM   2. SteamVR installed (provides the OpenXR runtime that Kit talks to)
REM      -- in SteamVR settings, "Set SteamVR as OpenXR Runtime"
REM   3. Quest 2 paired with PC via Air Link: Quest Settings ->
REM      System -> Quest Link -> Air Link -> connect to this PC.
REM
REM Per-session flow:
REM   1. Put on Quest 2, connect via Air Link from inside the headset.
REM      You should land in the Oculus Link / SteamVR home environment.
REM   2. Run this script from the repo root: launch_xr.bat
REM   3. Kit will start; the headset should switch into the Messel scene
REM      rendered stereoscopically.
REM
REM USD path: same override as launch.bat. Set MESSEL_USD to point at
REM a different file. Pass --no-auto to open a blank stage.

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
    echo [launch_xr.bat] auto-loading: !MESSEL_USD!
    echo [launch_xr.bat] make sure Quest 2 Air Link is active before Kit window appears
    call .\repo.bat launch --name senckenberg.messelpit.viewer_xr.kit -- "--/app/messelpit/load_usd=!MESSEL_USD!" %*
) else (
    echo [launch_xr.bat] auto-load disabled
    call .\repo.bat launch --name senckenberg.messelpit.viewer_xr.kit -- %*
)
popd

endlocal
