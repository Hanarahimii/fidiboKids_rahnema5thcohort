@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo First run start_admin.bat to install Python packages.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" scripts\install_brand_font.py
if errorlevel 1 (
  echo Place the licensed 3-Kahroba-V1.0-Eco.zip next to this file, then try again.
)
pause
