@echo off
REM TapeMap launcher (portable): runs from this file's own folder.
REM The desk (ui/desk.html) is served directly by the Python backend on
REM 8765 -- plain HTML, no build step. The Vite dev server on 5173 (ui-v2,
REM the abandoned React app) is NOT started here any more (2026-08-22): it
REM existed only to serve ui-v2, nothing the desk needs proxies through it,
REM and opening it left the operator staring at a dashboard with no data
REM while this window said everything was fine.
title TapeMap v2 Launcher
cd /d "%~dp0"

REM --- broker ---------------------------------------------------------
REM Dhan's Data API lapsed 2026-08-05. chain_live._broker() defaults to
REM "dhan" when this is unset, so an unset launcher starts BOTH halves --
REM the chain poller and the tape -- on a dead source, and the only symptom
REM is an empty chart. Set BEFORE the two `start` lines below, which inherit
REM this environment. A misspelling fails SAFE to Dhan (test_broker_switch),
REM so the word is spelled once, here, and nowhere else.
set TAPEMAP_BROKER=upstox

REM --- Upstox token ----------------------------------------------------
REM ASK Upstox whether the token works. Do not infer it from the file date.
REM A date says "written today"; it never says "still valid", and on
REM 2026-08-06 that difference cost a morning: the token was minted at 02:48,
REM Upstox expires tokens at 03:30, so by 09:10 it was six hours dead while
REM its file still read "today". The chart kept drawing -- the v3 candle
REM endpoint serves without auth -- and only the chain died, which looks
REM exactly like a chain bug and is not one.
REM /v2/user/profile is the cheapest authenticated call there is, and it is
REM read-only. Any failure at all -- missing file, empty file, 401 -- exits
REM non-zero and re-auths. The token is never printed.
python -c "import sys,urllib.request,upstox_feed;t=upstox_feed.read_token();r=urllib.request.Request('https://api.upstox.com/v2/user/profile',headers={'Authorization':'Bearer '+t,'Accept':'application/json','User-Agent':'Mozilla/5.0 Chrome/128.0.0.0 Safari/537.36'});urllib.request.urlopen(r,timeout=15).read();sys.exit(0)" 2>nul
if errorlevel 1 (
  echo Upstox rejected the saved token - opening the login...
  python upstox_auth.py
  if errorlevel 1 (
    echo.
    echo Upstox login did not finish. Starting anyway would put up a
    echo dashboard with no data, so stopping here instead. Fix the login
    echo above and run this launcher again.
    timeout /t 20 /nobreak >nul
    exit /b 1
  )
) else (
  echo Upstox accepted the saved token - reusing it.
)

REM --- backend (8765) ------------------------------------------------
netstat -aon | findstr ":8765" | findstr "LISTENING" >nul
if errorlevel 1 goto startbackend

REM Something already holds 8765. ASK it which broker it is on instead of
REM assuming. On 2026-08-06 this launcher assumed, and reused a Dhan server
REM that had been running since the previous afternoon -- the whole dashboard
REM was placeholder data, and the banner blamed an expired Dhan token.
REM Exit codes: 0 = a TapeMap server on Upstox, 2 = up but on another broker,
REM 1 = no /api/health to answer (older than 2026-08-06, or not ours at all).
python -c "import json,urllib.request,sys;d=json.load(urllib.request.urlopen('http://127.0.0.1:8765/api/health',timeout=4));sys.exit(0 if d.get('broker')=='upstox' else 2)" 2>nul
if not errorlevel 1 (
  echo TapeMap server already up on 8765, verified on Upstox - reusing it.
  goto frontend
)
echo.
echo Something is already on 8765 and it is NOT a TapeMap server on Upstox:
echo   - a server left running from an earlier day, or
echo   - one started without TAPEMAP_BROKER, so it is on Dhan.
echo Reusing it is exactly what filled the screen with placeholder data.
echo.
choice /C YN /N /M "Stop it and start a fresh Upstox server? [Y/N] "
if errorlevel 2 (
  echo Leaving it alone - the dashboard will show whatever that server serves.
  goto frontend
)
call "%~dp0stop.bat"
title TapeMap v2 Launcher

:startbackend
echo Starting TapeMap live server on 8765...
start "TapeMap server" cmd /k python server.py live

:frontend
REM --- wait for the backend, then open the desk directly ---------------
REM Poll instead of a fixed sleep: the tape/chain resolve on first request
REM and a cold start can take a few seconds longer than a warm one.
echo Waiting for the server to answer on 8765...
set _try=0
:wait
netstat -aon | findstr ":8765" | findstr "LISTENING" >nul
if not errorlevel 1 goto ready
set /a _try+=1
if %_try% geq 45 goto slow
timeout /t 1 /nobreak >nul
goto wait

:ready
start "" http://127.0.0.1:8765/desk.html
echo.
echo Keep the "TapeMap server" window open.
echo.
echo Running on UPSTOX. Today's token was handled above - there is nothing
echo to click. The TOKEN button in the dashboard is Dhan-only and cannot
echo refresh an Upstox token; to re-auth, run: python upstox_auth.py
timeout /t 6 /nobreak >nul
exit /b

:slow
echo.
echo 8765 never answered. Look at the "TapeMap server" window for the
echo actual error.
timeout /t 15 /nobreak >nul
