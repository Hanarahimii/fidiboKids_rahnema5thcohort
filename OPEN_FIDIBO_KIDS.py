"""Prepare this extracted copy, choose a free local port, and open the presentation."""
from __future__ import annotations

import hashlib
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run(*args: str) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


def prepare() -> Path:
    if sys.version_info < (3, 12):
        raise RuntimeError("Python 3.12 or newer is required.")
    if not (ROOT / "app" / "main.py").is_file():
        raise RuntimeError("Extract the entire ZIP before opening this launcher.")
    environment = ROOT / ".venv"
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.is_file():
        print("Creating a Python environment for this computer...", flush=True)
        run(sys.executable, "-m", "venv", str(environment))
    requirements = ROOT / "requirements.txt"
    fingerprint = hashlib.sha256(requirements.read_bytes()).hexdigest()
    marker = environment / "fidibo-requirements.sha256"
    if not marker.is_file() or marker.read_text().strip() != fingerprint:
        print("Installing the required packages (first run needs internet)...", flush=True)
        run(str(python), "-m", "pip", "install", "-r", str(requirements))
        marker.write_text(fingerprint + "\n", encoding="utf-8")

    if not (ROOT / "runtime" / "admin_auth.json").is_file():
        print("Set an expert password when prompted:", flush=True)
        run(str(python), str(ROOT / "scripts" / "set_admin_password.py"))
    if not (ROOT / "runtime" / "kidsbook.sqlite3").is_file():
        run(str(python), str(ROOT / "scripts" / "init_db.py"))
    for script in ("upgrade_db.py", "seed_discovery.py", "seed_your_story.py",
                   "seed_craft.py", "sync_discovery_content.py", "repair_runtime.py"):
        run(str(python), str(ROOT / "scripts" / script))
    return python


def launch(python: Path) -> None:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    url = f"http://127.0.0.1:{port}/"
    process = subprocess.Popen([str(python), "-m", "uvicorn", "app.main:app",
                                "--host", "127.0.0.1", "--port", str(port)], cwd=ROOT)
    try:
        for _ in range(120):
            if process.poll() is not None:
                raise RuntimeError("The local server exited. Read its error above.")
            try:
                with urllib.request.urlopen(url + "api/edition", timeout=1) as reply:
                    if reply.status == 200:
                        print(f"Opening {url}", flush=True)
                        webbrowser.open_new_tab(url + "?release=v4-support-links-20260926")
                        print("Keep this window open. Press Ctrl+C to stop.", flush=True)
                        returncode = process.wait()
                        if returncode:
                            raise RuntimeError(f"The server stopped with code {returncode}.")
                        return
            except (urllib.error.URLError, TimeoutError):
                pass
            time.sleep(1)
        raise RuntimeError("The local server did not become ready within two minutes.")
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == "__main__":
    try:
        launch(prepare())
    except KeyboardInterrupt:
        print("Stopped.")
    except (OSError, subprocess.CalledProcessError, RuntimeError) as error:
        print(f"Could not open Fidibo Kids: {error}", file=sys.stderr)
        raise SystemExit(1) from error
