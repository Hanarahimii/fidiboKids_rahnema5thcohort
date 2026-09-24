@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo First run start_admin.bat.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" scripts\check_fidibo.py
if errorlevel 1 (
  echo The banner check failed. Keep this window open and share the output.
)
pause
