@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
  echo Run install_windows.bat first, or double-click "Launch Head Focus.bat".
  pause
  exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" head_focus.py
