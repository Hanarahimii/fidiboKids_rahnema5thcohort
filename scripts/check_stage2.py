"""Exercise the admin journey on a disposable copy of the packaged database."""

from __future__ import annotations

import io
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def expect(response, status: int = 200):
    assert response.status_code == status, (response.status_code, response.text)
    return response.json() if response.headers.get("content-type", "").startswith("application/json") else response


def mutation(client: TestClient, method: str, path: str, **kwargs):
    headers = kwargs.pop("headers", {})
    return client.request(method, path, headers={"X-Admin-Action": "1", **headers}, **kwargs)


def run():
    with tempfile.TemporaryDirectory(prefix="kidsbook-stage2-") as directory:
        folder = Path(directory)
        db_path = folder / "check.sqlite3"
        shutil.copy2(ROOT / "runtime" / "kidsbook.sqlite3", db_path)
        os.environ["KIDSBOOK_DB"] = str(db_path)
        os.environ["KIDSBOOK_AUTH_FILE"] = str(folder / "auth.json")
        os.environ["KIDSBOOK_ASSETS"] = str(folder / "assets")
        from app.auth import create_password_file
        create_password_file(folder / "auth.json", "temporary-check-password")
        from app.main import app

        with TestClient(app) as client:
            html = expect(client.get("/"))
            assert "ماهی سیاه کوچولو | فیدیبو کیدز" in html.text
            assert expect(client.get("/black-fish.svg")).headers["content-type"].startswith("image/svg+xml")
            script_path = re.search(r'<script[^>]+src="([^"]+)"', html.text).group(1)
            style_path = re.search(r'<link[^>]+href="([^"]+\.css)"', html.text).group(1)
            assert expect(client.get(script_path)).status_code == 200
            assert expect(client.get(style_path)).status_code == 200
            expect(client.get("/api/admin/steps"), 401)
            expect(mutation(client, "POST", "/api/admin/login", json={"password": "wrong"}), 401)
            expect(mutation(client, "POST", "/api/admin/login", json={"password": "temporary-check-password"}))
            assert len(expect(client.get("/api/admin/steps"))["steps"]) == 7
            story = expect(mutation(client, "POST", "/api/admin/pages", json={"step_id": "ask", "kind": "story"}))
            story_id = story["id"]
            assert story["status"] == "draft"
            assert story_id not in [p["id"] for p in expect(client.get("/api/book/steps?language=fa"))["steps"][0]["pages"]]

            image = Image.new("RGB", (32, 32), (37, 116, 147))
            stream = io.BytesIO(); image.save(stream, "PNG")
            asset = expect(mutation(client, "POST", "/api/admin/assets",
                                    files={"file": ("test.png", stream.getvalue(), "image/png")}))
            art_key = asset["art_key"]
            outside = TestClient(app)
            expect(outside.get(asset["url"]), 401)
            content = {"fa": {"text": "صفحهٔ تازهٔ فارسی", "art_key": art_key},
                       "azb": {"text": "یئنی صفحه", "art_key": art_key}}
            saved = expect(mutation(client, "PUT", f"/api/admin/pages/{story_id}", json={
                "locales": content, "base_revisions": story["latest_revision_ids"],
            }))
            assert saved["has_unpublished_changes"]
            expect(mutation(client, "PUT", f"/api/admin/pages/{story_id}", json={
                "locales": content, "base_revisions": story["latest_revision_ids"],
            }), 409)
            story = expect(mutation(client, "POST", f"/api/admin/pages/{story_id}/publish"))
            assert story["status"] == "published"
            assert expect(outside.get(asset["url"])).status_code == 200
            for language in ("fa", "azb"):
                book = expect(client.get(f"/api/book/steps?language={language}"))
                assert any(p["id"] == story_id for p in book["steps"][0]["pages"])

            # Editing a published script creates an unpublished revision while
            # the previous text stays visible until explicitly published.
            original_revision = story["published_revision_ids"]["fa"]
            content["fa"]["text"] = "نسخهٔ دوم متن فارسی"
            edited = expect(mutation(client, "PUT", f"/api/admin/pages/{story_id}", json={
                "locales": content, "base_revisions": story["latest_revision_ids"],
            }))
            assert edited["published_revision_ids"]["fa"] == original_revision
            public_story = next(p for p in expect(client.get("/api/book/steps?language=fa"))["steps"][0]["pages"]
                                if p["id"] == story_id)
            assert public_story["content"]["text"] == "صفحهٔ تازهٔ فارسی"
            expect(mutation(client, "POST", f"/api/admin/pages/{story_id}/publish"))
            updated = next(p for p in expect(client.get("/api/book/steps?language=fa"))["steps"][0]["pages"]
                           if p["id"] == story_id)
            assert updated["revision_id"] != original_revision

            quiz = expect(mutation(client, "POST", "/api/admin/pages", json={"step_id": "ask", "kind": "quiz"}))
            quiz_id = quiz["id"]
            def question(lang, answer):
                return {"questions": [{"id": "new-q1", "category": "recall", "number": 1,
                    "prompt": "کجاست؟" if lang == "fa" else "هارادا؟", "answer_id": answer,
                    "options": [{"id": key, "text": f"{lang}-{key}", "art_key": ""}
                                for key in ("river", "sea", "pond")]}]}
            expect(mutation(client, "PUT", f"/api/admin/pages/{quiz_id}", json={
                "locales": {"fa": question("fa", "river"), "azb": question("azb", "sea")},
                "base_revisions": quiz["latest_revision_ids"],
            }))
            expect(mutation(client, "POST", f"/api/admin/pages/{quiz_id}/publish"), 422)
            quiz = expect(client.get(f"/api/admin/pages/{quiz_id}"))
            expect(mutation(client, "PUT", f"/api/admin/pages/{quiz_id}", json={
                "locales": {"fa": question("fa", "river"), "azb": question("azb", "river")},
                "base_revisions": quiz["latest_revision_ids"],
            }))
            expect(mutation(client, "POST", f"/api/admin/pages/{quiz_id}/publish"))
            expect(mutation(client, "POST", f"/api/admin/pages/{quiz_id}/move", json={"direction": "up"}))
            expect(mutation(client, "POST", f"/api/admin/pages/{story_id}/archive"))
            assert all(p["id"] != story_id for p in expect(client.get("/api/book/steps?language=fa"))["steps"][0]["pages"])
            expect(mutation(client, "POST", f"/api/admin/pages/{story_id}/restore"))
            assert all(p["id"] != story_id for p in expect(client.get("/api/book/steps?language=fa"))["steps"][0]["pages"])
            expect(mutation(client, "POST", f"/api/admin/pages/{story_id}/publish"))
            assert any(p["id"] == story_id for p in expect(client.get("/api/book/steps?language=fa"))["steps"][0]["pages"])
            expect(mutation(client, "POST", "/api/admin/logout"))
            expect(client.get("/api/admin/steps"), 401)
    print("PASS: sign in, add/edit/reorder/archive/restore bilingual pages, publish and preview")
    print("PASS: upload image, reject inconsistent quiz answers, retain old text revision")
    print("PASS: draft stays private; published content appears for both languages")


if __name__ == "__main__":
    run()
