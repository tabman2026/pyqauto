chcp 65001 >nul
@echo off
setlocal
set PYTHONUTF8=1

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$name = -join [char[]](0x41,0x80A1,0x884C,0x60C5,0x6E90,0x8DEF,0x7531,0x5668,0x5F,0x7A33,0x5B9A,0x6027,0x89C2,0x5BDF);" ^
  "& schtasks.exe /Query /TN $name *> $null;" ^
  "if ($LASTEXITCODE -ne 0) { Write-Host ('SKIP: scheduled task not found: ' + $name); exit 0 }" ^
  "& schtasks.exe /Delete /TN $name /F;" ^
  "if ($LASTEXITCODE -ne 0) { Write-Host 'SKIP: unable to delete scheduled task. No logs or reports were removed.'; exit 0 }" ^
  "Write-Host ('Deleted scheduled task: ' + $name);" ^
  "Write-Host 'Logs and reports were not removed.';" ^
  "exit 0"

exit /b %ERRORLEVEL%
