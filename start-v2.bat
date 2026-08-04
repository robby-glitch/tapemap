@echo off
REM TapeMap v2 launcher (portable): runs from this file's own folder.
REM v2 needs BOTH halves — the Python backend on 8765 and the Vite dev
REM server on 5173, which proxies /api to it. Each gets its own window,
REM so closing this launcher does not kill them.
title TapeMap v2 Launcher
cd /d "%~dp0"

REM --- backend (8765) ------------------------------------------------
netstat -aon | findstr ":8765" | findstr "LISTENING" >nul
if errorlevel 1 (
  echo Starting TapeMap live server on 8765...
  start "TapeMap server" cmd /k python server.py live
) else (
  echo TapeMap server already up on 8765 - reusing it.
)

REM --- v2 frontend (Vite, 5173) ---------------------------------------
netstat -aon | findstr ":5173" | findstr "LISTENING" >nul
if errorlevel 1 (
  echo Starting the v2 dashboard ^(Vite^)...
  start "TapeMap v2 UI" cmd /k corepack pnpm --dir ui-v2 dev
) else (
  echo v2 UI already up on 5173 - reusing it.
)

REM --- wait for Vite, then open the browser ----------------------------
REM Poll instead of a fixed sleep: a cold start pays for dependency
REM optimisation and can take far longer than the backend does.
echo Waiting for the UI to answer on 5173...
set _try=0
:wait
netstat -aon | findstr ":5173" | findstr "LISTENING" >nul
if not errorlevel 1 goto ready
set /a _try+=1
if %_try% geq 45 goto slow
timeout /t 1 /nobreak >nul
goto wait

:ready
start "" http://localhost:5173
echo.
echo Keep BOTH windows open: "TapeMap server" and "TapeMap v2 UI".
echo The Dhan token expires daily - first click of the day is TOKEN,
echo top-right of the dashboard.
timeout /t 6 /nobreak >nul
exit /b

:slow
echo.
echo 5173 never answered. Look at the "TapeMap v2 UI" window - a first
echo run may still be installing packages, or corepack/pnpm may have
echo failed there. The backend on 8765 is unaffected.
timeout /t 15 /nobreak >nul
