@echo off
cd /d "%~dp0"
echo === Kidsbook Admin: first run may take a few minutes ===
if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
    if errorlevel 1 (
        echo Python could not create the local environment.
        pause
        exit /b 1
    )
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo Installing Python packages failed. Keep this window open and share the error.
    pause
    exit /b 1
)
if not exist "runtime\admin_auth.json" (
    ".venv\Scripts\python.exe" scripts\set_admin_password.py
    if errorlevel 1 (
        pause
        exit /b 1
    )
)
if not exist "runtime\kidsbook.sqlite3" (
    ".venv\Scripts\python.exe" scripts\init_db.py
    if errorlevel 1 (
        pause
        exit /b 1
    )
)
".venv\Scripts\python.exe" scripts\upgrade_db.py
if errorlevel 1 (
    echo Database update failed. The server was not started.
    pause
    exit /b 1
)
echo.
echo Open http://127.0.0.1:8000/book for the child book.
echo Open http://127.0.0.1:8000 for the admin panel.
echo Open http://127.0.0.1:8000/research to review recordings.
echo Keep this window open while you use the book. Press Ctrl+C to stop.
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
