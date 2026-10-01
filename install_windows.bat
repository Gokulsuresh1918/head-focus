@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
title Head Focus - Install

echo.
echo   Head Focus - one-time setup
echo   ===========================
echo.

set "PY="
where py >nul 2>&1
if %ERRORLEVEL%==0 set "PY=py -3"

if not defined PY (
  where python >nul 2>&1
  if !ERRORLEVEL!==0 set "PY=python"
)

if not defined PY (
  echo Python was not found.
  echo.
  echo Install Python 3.10 or newer from https://www.python.org/downloads/
  echo During install, turn ON "Add python.exe to PATH".
  echo.
  pause
  exit /b 1
)

echo Using: %PY%
%PY% --version
if errorlevel 1 (
  echo Could not run Python. Fix your PATH and run this file again.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo.
  echo Creating virtual environment in .venv ...
  %PY% -m venv .venv
  if errorlevel 1 (
    echo Failed to create .venv
    pause
    exit /b 1
  )
)

echo.
echo Installing packages ^(first time can take several minutes^) ...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\pip.exe" install -r requirements.txt
if errorlevel 1 (
  echo.
  echo pip install failed. Check your internet connection and try again.
  pause
  exit /b 1
)

echo.
echo   Setup complete.
echo.
echo   Next: double-click "Launch Head Focus.bat"
echo   Or run:  .venv\Scripts\python.exe head_focus.py
echo.
echo   Allow Camera access for python.exe when Windows asks.
echo   On first run the face model downloads automatically ^(~10 MB^).
echo.
pause
exit /b 0
