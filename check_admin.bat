@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo First run start_admin.bat to install the packages.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" scripts\check_stage2.py
pause
