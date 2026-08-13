@echo off
REM TapeMap EOD capture (portable): runs from this file's own folder.
REM Launched by the "TapeMap EOD capture" scheduled task, weekdays after the
REM close. Preserves the session tape so trigger_log rows stay scoreable --
REM see eod_capture.py's docstring for why that stopped being true.
cd /d "%~dp0"

echo.>> data\eod_capture.log
echo ===== %DATE% %TIME% =====>> data\eod_capture.log

REM Absolute interpreter, unlike start.bat's plain `python`: a scheduled task
REM runs with a different PATH than an interactive shell, and the WindowsApps
REM python stub can win there and fail without ever reaching this script.
"C:\Python313\python.exe" eod_capture.py >> data\eod_capture.log 2>&1

REM Propagate the exit code so Task Scheduler's "Last Run Result" shows a
REM refusal as a failure. A capture that quietly did nothing is the whole
REM problem this was built to end.
exit /b %ERRORLEVEL%
