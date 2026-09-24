"""Exercise banner upload, public visibility and reset using disposable data."""
from __future__ import annotations

import io
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def check(response, status=200):
    assert response.status_code == status, (response.status_code, response.text[:300])
    return response.json() if "application/json" in response.headers.get("content-type", "") else response


def run():
    with tempfile.TemporaryDirectory(prefix="kidsbook-fidibo-") as folder:
        temp = Path(folder)
        db = temp / "books.sqlite3"
        from scripts.init_db import initialize
        initialize(ROOT / "data" / "initial_content.json", ROOT / "db" / "schema.sql", db)
        # Simulate a copied stage-six database created before banner settings existed.
        with sqlite3.connect(db) as connection:
            connection.execute("DROP TABLE site_banners")
        upgraded = subprocess.run([sys.executable, str(ROOT / "scripts" / "upgrade_db.py"),
                                   "--db", str(db)], capture_output=True, text=True)
        assert upgraded.returncode == 0, upgraded.stderr
        os.environ.update(KIDSBOOK_DB=str(db), KIDSBOOK_AUTH_FILE=str(temp / "auth.json"),
                          KIDSBOOK_ASSETS=str(temp / "assets"), KIDSBOOK_RAW_DIR=str(temp / "raw"),
                          KIDSBOOK_PUBLISHED_DIR=str(temp / "published"))
        from app.auth import create_password_file
        create_password_file(temp / "auth.json", "disposable-check-password")
        from app.main import app
        image = io.BytesIO()
        Image.new("RGB", (400, 240), (108, 65, 160)).save(image, format="PNG")
        payload = image.getvalue()
        with TestClient(app) as admin, TestClient(app) as reader:
            assert check(reader.get("/api/book/banners")) == {"cover": None, "steps": {}}
            check(reader.get("/api/admin/banners"), 401)
            check(reader.post("/api/admin/assets", files={"file": ("banner.png", payload, "image/png")},
                              headers={"X-Admin-Action": "1"}), 401)
            check(admin.post("/api/admin/login", json={"password": "disposable-check-password"},
                             headers={"X-Admin-Action": "1"}))
            current = check(admin.get("/api/admin/banners"))
            assert current["cover"] is None and len(current["steps"]) == 7
            art_key = check(admin.post("/api/admin/assets", files={"file": ("banner.png", payload, "image/png")},
                                       headers={"X-Admin-Action": "1"}))["art_key"]
            image_url = "/api/assets/" + art_key[7:]
            check(reader.get(image_url), 401)
            check(admin.put("/api/admin/banners/cover", json={"art_key": art_key}), 403)
            action = {"X-Admin-Action": "1"}
            check(admin.put("/api/admin/banners/cover", json={"art_key": art_key}, headers=action))
            assert check(reader.get("/api/book/banners"))["cover"] == image_url
            assert check(reader.get(image_url)).headers["content-type"] == "image/webp"
            step_id = current["steps"][0]["id"]
            check(admin.put(f"/api/admin/banners/step:{step_id}", json={"art_key": art_key}, headers=action))
            assert check(reader.get("/api/book/banners"))["steps"][step_id] == image_url
            check(admin.put("/api/admin/banners/step:missing", json={"art_key": art_key}, headers=action), 404)
            check(admin.put("/api/admin/banners/cover", json={"art_key": "upload:missing"}, headers=action), 422)
            check(admin.put("/api/admin/banners/cover", json={"art_key": None}, headers=action))
            assert check(reader.get("/api/book/banners"))["cover"] is None
            assert check(reader.get(image_url)).status_code == 200  # Still used by a published step banner.
            check(admin.put(f"/api/admin/banners/step:{step_id}", json={"art_key": None}, headers=action))
            check(reader.get(image_url), 401)
            with sqlite3.connect(db) as conn:
                assert conn.execute("SELECT count(*) FROM site_banners").fetchone()[0] == 0
        print("PASS: banner editor controls cover and step images; reset restores fallbacks")
        print("PASS: drafts remain private; only active banners are public, with auth on all edits")
        print("PASS: a copied stage-six database receives banner settings without losing content")


if __name__ == "__main__":
    run()
