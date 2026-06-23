@echo off
chcp 65001 >nul
setlocal
set PYTHONUTF8=1
set "VENV_PY=.venv\Scripts\python.exe"

if not exist "%VENV_PY%" (
    echo Project virtual environment not found: %VENV_PY%
    echo Please run scripts\setup_dev_windows.bat first.
    exit /b 1
)

"%VENV_PY%" -X utf8 -m pytest -q
if errorlevel 1 exit /b 1

"%VENV_PY%" -X utf8 -m compileall -q astock_source_router tests examples
if errorlevel 1 exit /b 1

"%VENV_PY%" -X utf8 scripts\smoke_test_offline.py
if errorlevel 1 exit /b 1

"%VENV_PY%" -X utf8 scripts\doctor_env.py
if errorlevel 1 exit /b 1

"%VENV_PY%" -X utf8 -m ruff --version >nul 2>nul
if errorlevel 1 (
    echo ruff: SKIP，原因：未安装
) else (
    "%VENV_PY%" -X utf8 -m ruff check .
    if errorlevel 1 exit /b 1
)
