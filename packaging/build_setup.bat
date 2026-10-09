@echo off
rem Build DinigSetup.exe on a Windows laptop that has internet.
rem Install Inno Setup 6 first: https://jrsoftware.org/isdl.php
rem The finished file is packaging\output\DinigSetup.exe (about 4GB). Copy it to a USB.
title Build Dinig setup
cd /d "%~dp0"
setlocal

set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (
  echo Inno Setup 6 was not found. Install it from https://jrsoftware.org/isdl.php and run this again.
  pause
  exit /b 1
)

echo Preparing a clean staging folder...
if exist staging rmdir /s /q staging
mkdir staging
mkdir staging\models
mkdir redist 2>nul
mkdir output 2>nul

robocopy ..\backend staging\backend /E /XD __pycache__ /NFL /NDL /NJH /NJS
if errorlevel 8 goto failed
robocopy ..\frontend staging\frontend /E /NFL /NDL /NJH /NJS
if errorlevel 8 goto failed
copy /y ..\start_dinig.bat staging\start_dinig.bat >nul
if errorlevel 1 goto failed

call :embed_python || goto failed
call :whisper || goto failed
call :ollama_setup || goto failed
call :qwen || goto failed
call :seed || goto failed

echo Compiling DinigSetup.exe (this takes a while)...
"%ISCC%" dinig.iss
if errorlevel 1 goto failed

echo.
echo Done: %CD%\output\DinigSetup.exe
echo Copy that file to a USB. On the teacher laptop, double-click it.
echo If Windows says it protected your PC, choose More info, then Run anyway.
pause
exit /b 0

:failed
echo Build stopped. See the message above.
pause
exit /b 1

:embed_python
echo Downloading Python 3.12 (embeddable)...
set "PYVER=3.12.10"
set "PYZIP=python-%PYVER%-embed-amd64.zip"
if not exist "%PYZIP%" (
  powershell -NoProfile -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/%PYVER%/%PYZIP%' -OutFile '%PYZIP%'"
  if errorlevel 1 exit /b 1
)
mkdir staging\python
tar -xf "%PYZIP%" -C staging\python
if errorlevel 1 exit /b 1
powershell -NoProfile -Command "Get-ChildItem 'staging\python\python*._pth' | ForEach-Object { (Get-Content $_.FullName) -replace '#\s*import site','import site' | Set-Content $_.FullName }"
if not exist staging\python\get-pip.py (
  powershell -NoProfile -Command "Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile 'staging\python\get-pip.py'"
  if errorlevel 1 exit /b 1
)
staging\python\python.exe staging\python\get-pip.py
if errorlevel 1 exit /b 1
staging\python\python.exe -m pip install -r ..\requirements.txt
if errorlevel 1 exit /b 1
exit /b 0

:whisper
if not exist "..\models\faster-whisper-small\model.bin" (
  echo Downloading Whisper small...
  staging\python\python.exe ..\backend\download_models.py
  if errorlevel 1 exit /b 1
)
robocopy ..\models\faster-whisper-small staging\models\faster-whisper-small /E /NFL /NDL /NJH /NJS
if errorlevel 8 exit /b 1
exit /b 0

:ollama_setup
if exist "redist\OllamaSetup.exe" exit /b 0
echo Downloading the Ollama installer...
powershell -NoProfile -Command "Invoke-WebRequest -Uri 'https://ollama.com/download/OllamaSetup.exe' -OutFile 'redist\OllamaSetup.exe'"
if errorlevel 1 exit /b 1
exit /b 0

:qwen
set "OLLAMA_EXE="
if exist "%LocalAppData%\Programs\Ollama\ollama.exe" set "OLLAMA_EXE=%LocalAppData%\Programs\Ollama\ollama.exe"
if not defined OLLAMA_EXE (
  where ollama >nul 2>nul
  if not errorlevel 1 set "OLLAMA_EXE=ollama"
)
if not defined OLLAMA_EXE (
  echo Installing Ollama on this build laptop so the models can be downloaded...
  start /wait redist\OllamaSetup.exe /VERYSILENT /NORESTART /SUPPRESSMSGBOXES
  if exist "%LocalAppData%\Programs\Ollama\ollama.exe" set "OLLAMA_EXE=%LocalAppData%\Programs\Ollama\ollama.exe"
)
if not defined OLLAMA_EXE (
  echo Ollama was not found after install. Open Ollama from the Start menu and run this again.
  exit /b 1
)
echo Downloading Qwen 3B and 1.5B into models\ollama (about 3GB)...
set "OLLAMA_MODELS=%CD%\..\models\ollama"
"%OLLAMA_EXE%" pull qwen2.5:3b
if errorlevel 1 exit /b 1
"%OLLAMA_EXE%" pull qwen2.5:1.5b
if errorlevel 1 exit /b 1
robocopy ..\models\ollama staging\models\ollama /E /NFL /NDL /NJH /NJS
if errorlevel 8 exit /b 1
exit /b 0

:seed
echo Loading the sample class into the installer database...
pushd staging
python\python.exe backend\seed.py
set "SEED_ERR=%ERRORLEVEL%"
popd
if not "%SEED_ERR%"=="0" exit /b 1
exit /b 0
