@echo off
rem Dinig desktop launcher: double-click to start. See docs/SYSTEM_DESIGN.md "Desktop launcher".
title Dinig launcher
cd /d "%~dp0"

rem Never let Hugging Face reach the internet; Whisper loads from models\faster-whisper-small.
set HF_HUB_OFFLINE=1

rem Teacher installer ships Python inside python\. A developer laptop uses venv\ instead.
set "PY=%~dp0python\python.exe"
if not exist "%PY%" set "PY=%~dp0venv\Scripts\python.exe"
if not exist "%PY%" (
  echo Setup is not finished: python\python.exe and venv\Scripts\python.exe were not found.
  echo Teacher laptop: run DinigSetup.exe. Developer laptop: follow README.md.
  pause
  exit /b 1
)

rem Bundled Qwen lives next to the app. A developer laptop keeps using Ollama's own folder.
if exist "%~dp0models\ollama\" set "OLLAMA_MODELS=%~dp0models\ollama"

rem Start Ollama (local Qwen) if it is installed and not already running.
set "OLLAMA_EXE="
if exist "%LocalAppData%\Programs\Ollama\ollama.exe" set "OLLAMA_EXE=%LocalAppData%\Programs\Ollama\ollama.exe"
if not defined OLLAMA_EXE (
  where ollama >nul 2>nul
  if not errorlevel 1 set "OLLAMA_EXE=ollama"
)
if defined OLLAMA_EXE (
  tasklist /fi "imagename eq ollama.exe" | find /i "ollama.exe" >nul || start "Ollama" /min "%OLLAMA_EXE%" serve
)

rem If Dinig is already running, just open the window.
curl -s -o nul http://127.0.0.1:8000/health && goto open

rem Start the server with the project's own Python (not whatever "python" is on PATH).
rem Bound to 127.0.0.1 so other devices on the network cannot reach it.
start "Dinig server" /min "%PY%" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

echo Starting Dinig (loading Whisper, this can take a little while)...
set /a tries=0
:wait
curl -s -o nul http://127.0.0.1:8000/health && goto open
set /a tries+=1
if %tries% geq 90 (
  echo Dinig did not start. Look at the "Dinig server" window for the error.
  pause
  exit /b 1
)
timeout /t 1 /nobreak >nul
goto wait

:open
rem Own window, no tabs, no address bar. localhost keeps the microphone allowed.
call :find_browser
if defined BROWSER (
  start "" "%BROWSER%" --app=http://localhost:8000
) else (
  echo No Edge or Chrome found. Opening the usual browser.
  start "" http://localhost:8000
)
exit /b 0

:find_browser
set "BROWSER="
set "EDGE=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
if exist "%EDGE%" (
  set "BROWSER=%EDGE%"
  goto :eof
)
set "EDGE=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
if exist "%EDGE%" (
  set "BROWSER=%EDGE%"
  goto :eof
)
set "EDGE=%LocalAppData%\Microsoft\Edge\Application\msedge.exe"
if exist "%EDGE%" (
  set "BROWSER=%EDGE%"
  goto :eof
)
set "CHROME=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if exist "%CHROME%" (
  set "BROWSER=%CHROME%"
  goto :eof
)
set "CHROME=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
if exist "%CHROME%" (
  set "BROWSER=%CHROME%"
  goto :eof
)
set "CHROME=%LocalAppData%\Google\Chrome\Application\chrome.exe"
if exist "%CHROME%" (
  set "BROWSER=%CHROME%"
  goto :eof
)
goto :eof
