@echo off
rem Dinig desktop launcher: double-click to start. See docs/SYSTEM_DESIGN.md "Desktop launcher".
title Dinig launcher
cd /d "%~dp0"

rem Never let Hugging Face reach the internet; Whisper loads from models\faster-whisper-small.
set HF_HUB_OFFLINE=1

if not exist "venv\Scripts\python.exe" (
  echo Setup is not finished: venv\Scripts\python.exe was not found.
  echo Follow the setup steps in README.md first.
  pause
  exit /b 1
)

rem Start Ollama (local Qwen) if it is installed and not already running.
where ollama >nul 2>nul
if %errorlevel%==0 (
  tasklist /fi "imagename eq ollama.exe" | find /i "ollama.exe" >nul || start "Ollama" /min ollama serve
)

rem If Dinig is already running, just open the window.
curl -s -o nul http://127.0.0.1:8000/health && goto open

rem Start the server with the project's own Python (not whatever "python" is on PATH).
rem Bound to 127.0.0.1 so other devices on the network cannot reach it.
start "Dinig server" /min "venv\Scripts\python.exe" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

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
rem Edge app mode: its own window, no tabs, no address bar.
start "" msedge --app=http://localhost:8000
exit /b 0
