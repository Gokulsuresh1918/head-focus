@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\pythonw.exe" (
  echo Head Focus is not set up yet. Running install ...
  call "%~dp0install_windows.bat"
  if errorlevel 1 exit /b 1
)

start "" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0head_focus.py"
