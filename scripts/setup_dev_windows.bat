@echo off
chcp 65001 >nul
setlocal
set PYTHONUTF8=1
set "VENV_PY=.venv\Scripts\python.exe"

if not exist "%VENV_PY%" (
    echo Creating project virtual environment: .venv
    py -3.10 -X utf8 -m venv .venv
    if errorlevel 1 (
        echo py -3.10 is unavailable or failed. Trying C:\python\python.exe ...
        C:\python\python.exe -X utf8 -m venv .venv
    )
)

if not exist "%VENV_PY%" (
    echo Failed to create .venv.
    echo Please install Python 3.10+ and rerun scripts\setup_dev_windows.bat.
    exit /b 1
)

"%VENV_PY%" -X utf8 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
if errorlevel 1 (
    echo The project virtual environment must use Python 3.10+.
    echo Please remove .venv, install Python 3.10+, and rerun scripts\setup_dev_windows.bat.
    exit /b 1
)

"%VENV_PY%" -X utf8 -m pip install --upgrade pip setuptools wheel
if errorlevel 1 exit /b 1

"%VENV_PY%" -X utf8 -m pip install -e ".[dev]"
if errorlevel 1 exit /b 1

echo Development environment is ready: %VENV_PY%
