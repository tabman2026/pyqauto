@echo off
chcp 65001 >nul
set PYTHONUTF8=1

python -X utf8 -m pytest -q
if errorlevel 1 exit /b 1

python -X utf8 scripts\check_release.py
if errorlevel 1 exit /b 1

python -X utf8 scripts\smoke_test.py
if errorlevel 1 exit /b 1

python -X utf8 -m build
if errorlevel 1 exit /b 1

exit /b 0
