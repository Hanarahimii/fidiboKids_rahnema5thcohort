"""Check the child book and the stage-two upgrade on disposable files."""

from __future__ import annotations

import io
import os
import re
import sqlite3
import sys
import tempfile
from contextlib import closing
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def ok(response, status=200):
    assert response.status_code == status, (
        f"Expected HTTP {status}; got {response.status_code} from {response.request.url.path}"
    )
    return response.json() if "application/json" in response.headers.get("content-type", "") else response


def admin(client, method, path, **kwargs):
    return ok(client.request(method, path, headers={"X-Admin-Action": "1"}, **kwargs))


def page_ids(client, language, step_id="ask"):
    steps = ok(client.get(f"/api/book/steps?language={language}"))["steps"]
    return next(step["pages"] for step in steps if step["id"] == step_id)


def main():
    with tempfile.TemporaryDirectory(prefix="kidsbook-stage3-") as directory:
        temporary = Path(directory)
        db = temporary / "previous.sqlite3"
        if (ROOT / "runtime" / "kidsbook.sqlite3").is_file():
            # SQLite backup creates a consistent snapshot even when the local server is running.
            with closing(sqlite3.connect(ROOT / "runtime" / "kidsbook.sqlite3")) as source:
                with closing(sqlite3.connect(db)) as destination:
                    source.backup(destination)
        else:
            from scripts.init_db import initialize
            initialize(ROOT / "data" / "initial_content.json", ROOT / "db" / "schema.sql", db)
        # sqlite3.Connection's own context manager commits but DOES NOT close
        # the handle; Windows refuses to delete an open temporary database.
        with closing(sqlite3.connect(db)) as connection:
            with connection:
                connection.execute("DROP TABLE IF EXISTS story_ratings")
                old_count = connection.execute("SELECT count(*) FROM pages").fetchone()[0]
        with closing(sqlite3.connect(db)) as connection:
            connection.executescript((ROOT / "db/migrations" / "0002_ratings.sql").read_text(encoding="utf-8"))
            connection.executescript((ROOT / "db/migrations" / "0002_ratings.sql").read_text(encoding="utf-8"))
            assert connection.execute("SELECT count(*) FROM pages").fetchone()[0] == old_count
            with connection:
                connection.execute("UPDATE submissions SET status='selected',published_at=NULL "
                                   "WHERE status='published' AND id IN "
                                   "(SELECT submission_id FROM published_audio)")
                connection.execute("DELETE FROM published_audio")

        os.environ["KIDSBOOK_DB"] = str(db)
        os.environ["KIDSBOOK_ASSETS"] = str(temporary / "assets")
        os.environ["KIDSBOOK_AUTH_FILE"] = str(temporary / "auth.json")
        from app.auth import create_password_file
        create_password_file(temporary / "auth.json", "local-check-password")
        from app.main import app

        with TestClient(app) as client:
            html = ok(client.get("/book")).text
            assert "<div id=\"root\">" in html
            for expression in (r'<script[^>]+src="([^"]+)"', r'<link[^>]+href="([^"]+\.css)"'):
                url = re.search(expression, html).group(1)
                ok(client.get(url))
            fa = ok(client.get("/api/book/steps?language=fa"))["steps"]
            azb = ok(client.get("/api/book/steps?language=azb"))["steps"]
            assert len(fa) == len(azb) == 7
            assert [s["id"] for s in fa] == [s["id"] for s in azb]
            for left, right in zip(fa, azb):
                assert [p["id"] for p in left["pages"]] == [p["id"] for p in right["pages"]]
            art_keys = {p["content"]["art_key"] for s in fa for p in s["pages"] if p["kind"] != "quiz"}
            for art_key in art_keys:
                assert ok(client.get(f"/api/book/art/{art_key}")).headers["content-type"].startswith("image/")
            ok(client.get("/api/book/art/no-such-key"), 404)

            first_story = fa[0]["pages"][0]
            assert ok(client.get(f"/api/book/readings?page_id={first_story['id']}&language=fa"))["readings"] == []
            ok(client.get(f"/api/book/audio/{first_story['id']}/fa_1"), 404)
            ok(client.get("/api/admin/steps"), 401)
            admin(client, "POST", "/api/admin/login", json={"password": "local-check-password"})
            created = admin(client, "POST", "/api/admin/pages", json={"step_id": "ask", "kind": "story"})
            story_id = created["id"]
            assert story_id not in [p["id"] for p in page_ids(client, "fa")]
            image = Image.new("RGB", (24, 24), "#2f809c")
            stream = io.BytesIO(); image.save(stream, "PNG")
            asset = admin(client, "POST", "/api/admin/assets", files={"file": ("art.png", stream.getvalue(), "image/png")})
            old_asset_key = asset["art_key"]
            ok(client.get(asset["url"]))  # admin sees draft art
            content = {"fa": {"text": "صفحهٔ افزوده‌شده", "art_key": old_asset_key},
                       "azb": {"text": "یئنی صفحه", "art_key": old_asset_key}}
            admin(client, "PUT", f"/api/admin/pages/{story_id}", json={
                "locales": content, "base_revisions": created["latest_revision_ids"]})
            admin(client, "POST", f"/api/admin/pages/{story_id}/publish")
            for language in ("fa", "azb"):
                pages = page_ids(client, language)
                story_index = next(i for i, p in enumerate(pages) if p["id"] == story_id)
                assert pages[story_index]["kind"] == "story"
                assert all(p["kind"] == "story" for p in pages[:story_index])
                assert any(p["kind"] == "lesson" for p in pages[story_index + 1:])
                assert pages[story_index]["content"]["text"] == content[language]["text"]
            quiz = admin(client, "POST", "/api/admin/pages", json={"step_id": "ask", "kind": "quiz"})
            quiz_id = quiz["id"]
            question = lambda lang: {"questions": [{"id": "new-question", "category": "recall", "number": 1,
                "prompt": "ماهی کجاست؟" if lang == "fa" else "ماهی هارادادیر؟", "answer_id": "sea",
                "options": [{"id": key, "text": f"{lang}-{key}", "art_key": ""}
                            for key in ("sea", "pond", "river")]}]}
            admin(client, "PUT", f"/api/admin/pages/{quiz_id}", json={
                "locales": {"fa": question("fa"), "azb": question("azb")},
                "base_revisions": quiz["latest_revision_ids"]})
            admin(client, "POST", f"/api/admin/pages/{quiz_id}/publish")
            for language in ("fa", "azb"):
                assert page_ids(client, language)[-1]["id"] == quiz_id
                assert page_ids(client, language)[-1]["content"]["questions"][0]["answer_id"] == "sea"
            current = ok(client.get(f"/api/admin/pages/{story_id}"))
            content["fa"]["text"] = "ویرایش هنوز منتشر نشده"
            admin(client, "PUT", f"/api/admin/pages/{story_id}", json={
                "locales": content, "base_revisions": current["latest_revision_ids"]})
            assert next(p for p in page_ids(client, "fa") if p["id"] == story_id)["content"]["text"] == "صفحهٔ افزوده‌شده"
            admin(client, "POST", "/api/admin/logout")
            assert ok(client.get(asset["url"])).headers["content-type"].startswith("image/")
            ok(client.get("/api/admin/steps"), 401)

            # A raw submission, even with an existing file, must not appear in Listen.
            raw = temporary / "raw-private.webm"; raw.write_bytes(b"private recording")
            with closing(sqlite3.connect(db)) as connection:
                with connection:
                    sample = connection.execute("SELECT p.step_id,r.id FROM page_revisions AS r "
                                                "JOIN pages AS p ON p.id=r.page_id WHERE r.id=?",
                                                (first_story["revision_id"],)).fetchone()
                    connection.execute("""INSERT INTO submissions
                        (id,client_request_id,submitted_at,language,step_id,page_id,content_revision_id,
                         duration_ms,mime_type,file_size_bytes,raw_file_ref,original_filename,consent_version,consent_at)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (str(uuid4()), str(uuid4()), "2026-01-01", "fa", sample[0], first_story["id"],
                         sample[1], 1000, "audio/webm", raw.stat().st_size, str(raw), "raw.webm", "v1", "2026-01-01"))
            assert ok(client.get(f"/api/book/readings?page_id={first_story['id']}&language=fa"))["readings"] == []
            ok(client.get(f"/api/book/audio/{first_story['id']}/fa_1"), 404)

            rating_id = str(uuid4())
            assert ok(client.get("/api/book/ratings"))["count"] == 0
            ok(client.post("/api/book/ratings", json={"client_id": rating_id, "language": "fa", "stars": 5}))
            ok(client.post("/api/book/ratings", json={"client_id": rating_id, "language": "azb", "stars": 3}))
            assert ok(client.get("/api/book/ratings")) == {"count": 1, "average": 3.0}
            ok(client.post("/api/book/ratings", json={"client_id": rating_id, "language": "fa", "stars": 6}), 422)
        assert (temporary / "assets" / f"{old_asset_key.split(':')[1]}.webp").is_file()
    print("PASS: stage-two database upgrade preserves pages; book serves seven bilingual steps and illustrations")
    print("PASS: admin-created story and quiz appear in both languages in order; drafts stay private")
    print("PASS: raw audio stays private; ratings validate and update one browser vote")


if __name__ == "__main__":
    main()
