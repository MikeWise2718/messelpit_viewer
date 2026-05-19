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

if "%MESSEL_USD%"=="" set "MESSEL_USD=D:\senckenberg\messelpit\out\messel.usd"

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
