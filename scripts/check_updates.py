"""Verify illustrated bilingual quiz and archive deletion against a disposable copy."""
from __future__ import annotations

import io
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def expect(response, status=200):
    assert response.status_code == status, (response.status_code, response.text[:350])
    return response.json() if "application/json" in response.headers.get("content-type", "") else response


def run():
    with tempfile.TemporaryDirectory(prefix="kidsbook-updates-") as folder:
        temp = Path(folder)
        db = temp / "content.sqlite3"
        shutil.copyfile(ROOT / "runtime" / "kidsbook.sqlite3", db)
        os.environ.update(KIDSBOOK_DB=str(db), KIDSBOOK_AUTH_FILE=str(temp / "auth.json"),
                          KIDSBOOK_ASSETS=str(temp / "assets"), KIDSBOOK_RAW_DIR=str(temp / "raw"),
                          KIDSBOOK_PUBLISHED_DIR=str(temp / "published"))
        from app.auth import create_password_file
        create_password_file(temp / "auth.json", "temporary-update-check")
        from app.main import app

        action = {"X-Admin-Action": "1"}
        image = io.BytesIO()
        Image.new("RGB", (340, 200), (80, 52, 125)).save(image, format="PNG")
        with TestClient(app) as admin, TestClient(app) as reader:
            expect(admin.post("/api/admin/login", json={"password": "temporary-update-check"}, headers=action))
            new = expect(admin.post("/api/admin/pages", json={"step_id": "ask", "kind": "quiz"}, headers=action))
            image_key = expect(admin.post("/api/admin/assets", files={
                "file": ("question.png", image.getvalue(), "image/png")}, headers=action))["art_key"]
            image_url = f"/api/assets/{image_key[7:]}"
            expect(reader.get(image_url), 401)

            def localized(language):
                return {"questions": [{"id": "test-picture-question", "category": "recall", "number": 1,
                    "prompt": "ماهی کجاست؟" if language == "fa" else "ماهی هارادادیر؟",
                    "art_key": image_key, "answer_id": "water", "options": [
                        {"id": option, "text": f"{language}-{option}", "art_key": ""}
                        for option in ("water", "sky", "tree")]}]}

            saved = expect(admin.put(f"/api/admin/pages/{new['id']}", json={
                "locales": {lang: localized(lang) for lang in ("fa", "azb")},
                "base_revisions": new["latest_revision_ids"]}, headers=action))
            expect(admin.post(f"/api/admin/pages/{new['id']}/publish", headers=action))
            for language in ("fa", "azb"):
                steps = expect(reader.get(f"/api/book/steps?language={language}"))["steps"]
                page = next(p for step in steps for p in step["pages"] if p["id"] == new["id"])
                assert page["content"]["questions"][0]["art_key"] == image_key
            expect(reader.get(image_url))
            expect(admin.delete(f"/api/admin/pages/{new['id']}"), 403)
            expect(admin.delete(f"/api/admin/pages/{new['id']}", headers=action), 409)
            expect(admin.post(f"/api/admin/pages/{new['id']}/archive", headers=action))
            expect(admin.delete(f"/api/admin/pages/{new['id']}", headers=action))
            expect(reader.get(image_url), 401)
            expect(admin.get(f"/api/admin/pages/{new['id']}"), 404)
            with sqlite3.connect(db) as connection:
                recorded_page = connection.execute("SELECT page_id FROM submissions LIMIT 1").fetchone()[0]
            expect(admin.post(f"/api/admin/pages/{recorded_page}/archive", headers=action))
            expect(admin.delete(f"/api/admin/pages/{recorded_page}", headers=action), 409)
        with sqlite3.connect(db) as connection:
            assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert not connection.execute("PRAGMA foreign_key_check").fetchall()
    print("PASS: question image publishes in both languages; draft images stay private")
    print("PASS: only archived pages without recordings can be permanently deleted")
    print("PASS: copied database retains referential integrity after deletion")


if __name__ == "__main__":
    run()
