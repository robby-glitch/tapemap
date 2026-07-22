@echo off
REM TapeMap launcher (portable): runs from this file's own folder.
title TapeMap Launcher
cd /d "%~dp0"
echo Starting TapeMap live server...
start "TapeMap server" cmd /k python server.py live
echo Opening the dashboard...
timeout /t 6 /nobreak >nul
start "" http://127.0.0.1:8765
echo.
echo Keep the "TapeMap server" window open while you use TapeMap.
echo If the page asks for a token, copy your fresh Dhan token and
echo click the TOKEN button in the top-right of the dashboard.
timeout /t 5 /nobreak >nul
