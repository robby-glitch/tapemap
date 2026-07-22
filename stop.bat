@echo off
REM Stop TapeMap: kill only the process listening on the dashboard port (8765),
REM not every python on the machine.
title Stop TapeMap
set _found=
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8765" ^| findstr "LISTENING"') do (
  taskkill /F /PID %%a >nul 2>&1
  set _found=1
)
if defined _found (echo TapeMap stopped.) else (echo TapeMap was not running.)
timeout /t 3 /nobreak >nul
