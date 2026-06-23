chcp 65001 >nul
@echo off
setlocal
set PYTHONUTF8=1
cd /d "%~dp0.."

set "VENV_PY=.venv\Scripts\python.exe"
if not exist "%VENV_PY%" (
    echo Project virtual environment not found: %VENV_PY%
    echo Please run scripts\setup_dev_windows.bat first.
    exit /b 1
)

set ENABLE_STABILITY_WATCH=1
if /I "%~1"=="--scheduled" (
    set STABILITY_WATCH_SCHEDULED_TASK=1
    set STABILITY_WATCH_TRIGGER=windows_scheduled_task
) else (
    if not defined STABILITY_WATCH_TRIGGER set STABILITY_WATCH_TRIGGER=windows_bat_manual
)

"%VENV_PY%" -X utf8 scripts\daily_stability_watch.py
set WATCH_EXIT=%ERRORLEVEL%

"%VENV_PY%" -X utf8 scripts\stability_summary.py
set SUMMARY_EXIT=%ERRORLEVEL%

if not "%WATCH_EXIT%"=="0" exit /b %WATCH_EXIT%
exit /b %SUMMARY_EXIT%
