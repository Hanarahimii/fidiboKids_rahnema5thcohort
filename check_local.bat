@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo First run start_admin.bat to create the local Python environment.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" scripts\repair_runtime.py
if errorlevel 1 (
  echo Runtime repair failed.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -c "from pathlib import Path; from app.main import app; print('PASS: local app imports; build and runtime are present')"
pause
