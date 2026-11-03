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
REM The Jarvis page (8787): the static file server start-v2.bat starts.
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8787" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
REM Option order flow: the Dext bridge (its lock port 9230) and the Option Battlefield (8790). Dext itself stays open.
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":9230" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8790" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
timeout /t 3 /nobreak >nul
