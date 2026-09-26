@echo off
setlocal
cd /d "%~dp0"
if not exist "app\main.py" (
  echo Please extract the entire ZIP first, then run this file from the extracted folder.
  pause
  exit /b 1
)

where py >nul 2>&1
if not errorlevel 1 (
  py -3.12 -c "import sys" >nul 2>&1
  if not errorlevel 1 goto PY_LAUNCHER
)
python -c "import sys;sys.exit(sys.version_info < (3,12))" >nul 2>&1
if errorlevel 1 (
  echo Python 3.12 is required. Install it, then open this file again.
  echo https://www.python.org/downloads/
  pause
  exit /b 1
)
python "%~dp0OPEN_FIDIBO_KIDS.py"
goto END

:PY_LAUNCHER
py -3.12 "%~dp0OPEN_FIDIBO_KIDS.py"

:END
if errorlevel 1 (
  echo Startup did not complete. The error is shown above.
  pause
)
endlocal
