chcp 65001 >nul
@echo off
setlocal
set PYTHONUTF8=1
cd /d "%~dp0.."

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$name = -join [char[]](0x41,0x80A1,0x884C,0x60C5,0x6E90,0x8DEF,0x7531,0x5668,0x5F,0x7A33,0x5B9A,0x6027,0x89C2,0x5BDF);" ^
  "$root = (Resolve-Path -LiteralPath '.').Path;" ^
  "$script = Join-Path $root 'scripts\run_stability_watch_windows.bat';" ^
  "if (-not (Test-Path -LiteralPath $script)) { Write-Host ('SKIP: stability watch script not found: ' + $script); exit 0 }" ^
  "& schtasks.exe /Query /TN $name *> $null;" ^
  "if ($LASTEXITCODE -eq 0) { Write-Host ('Existing task will be overwritten: ' + $name) }" ^
  "$target = '\"' + $script + '\" --scheduled';" ^
  "& schtasks.exe /Create /TN $name /SC DAILY /ST '15:40' /TR $target /F;" ^
  "if ($LASTEXITCODE -ne 0) { Write-Host 'SKIP: unable to create scheduled task. Run this script from an elevated terminal if Windows policy requires it.'; exit 0 }" ^
  "Write-Host ('Installed scheduled task: ' + $name);" ^
  "Write-Host 'Time: 15:40';" ^
  "Write-Host ('Target: ' + $script);" ^
  "exit 0"

exit /b %ERRORLEVEL%
