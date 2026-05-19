@echo off
REM Launch the Messel Pit Explorer (USD Explorer template) and auto-open messel.usd.
REM
REM The USD path is passed via a custom setting /app/messelpit/load_usd, which the
REM senckenberg.messelpit.explorer.setup extension reads on startup and calls
REM omni.usd.get_context().open_stage_async() with.
REM
REM Override the USD by setting MESSEL_USD before invoking:
REM   set "MESSEL_USD=D:\path\to\other.usd" && launch.bat
REM Pass --no-auto to skip auto-loading and open a blank stage:
REM   launch.bat --no-auto

setlocal EnableDelayedExpansion

REM Default to the --decimate 4 build (~6.75M tris) which loads stably on a
REM 4090. The full-res messel.usd (~108M tris) triggers a GPU device-lost
REM after ~30s in Kit (it works fine in usdview). Use messel.usd directly via
REM   set "MESSEL_USD=D:\senckenberg\messelpit\out\messel.usd" && launch.bat
REM for offline-quality renders if you accept the crash risk.
if "%MESSEL_USD%"=="" set "MESSEL_USD=D:\senckenberg\messelpit\out\messel_med.usd"

set "AUTO=1"
if /i "%~1"=="--no-auto" (
    set "AUTO=0"
    shift
)

pushd "%~dp0kit-app-template"
if "!AUTO!"=="1" (
    echo [launch.bat] auto-loading: !MESSEL_USD!
    call .\repo.bat launch --name senckenberg.messelpit.explorer.kit -- "--/app/messelpit/load_usd=!MESSEL_USD!" %*
) else (
    echo [launch.bat] auto-load disabled
    call .\repo.bat launch --name senckenberg.messelpit.explorer.kit -- %*
)
popd

endlocal
