"""Exercise consent, private raw storage, and retries on a disposable SQLite backup."""
from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
from contextlib import closing
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def check(response, status):
    assert response.status_code == status, (
        f"Expected HTTP {status}; got {response.status_code} from {response.request.url.path}"
    )
    return response.json() if status == 200 else None


def run():
    with tempfile.TemporaryDirectory(prefix="kidsbook-stage4-") as folder:
        temp = Path(folder)
        db = temp / "check.sqlite3"
        source = ROOT / "runtime" / "kidsbook.sqlite3"
        if source.exists():
            with closing(sqlite3.connect(source)) as old, closing(sqlite3.connect(db)) as new:
                old.backup(new)
        else:
            from scripts.init_db import initialize
            initialize(ROOT / "data" / "initial_content.json", ROOT / "db" / "schema.sql", db)
        with closing(sqlite3.connect(db)) as connection:
            connection.executescript((ROOT / "db" / "migrations" / "0002_ratings.sql").read_text(encoding="utf-8"))
            with connection:
                connection.execute("UPDATE submissions SET status='selected',published_at=NULL "
                                   "WHERE status='published' AND id IN "
                                   "(SELECT submission_id FROM published_audio)")
                connection.execute("DELETE FROM published_audio")
        os.environ["KIDSBOOK_DB"] = str(db)
        os.environ["KIDSBOOK_RAW_DIR"] = str(temp / "raw")
        os.environ["KIDSBOOK_AUTH_FILE"] = str(temp / "admin_auth.json")
        os.environ["KIDSBOOK_ASSETS"] = str(temp / "assets")
        from app.main import app
        with TestClient(app) as client:
            steps = check(client.get("/api/book/steps?language=fa"), 200)["steps"]
            page = next(p for p in steps[0]["pages"] if p["kind"] == "story")
            test_audio = b"\x1a\x45\xdf\xa3" + b"recorded audio" * 50
            request_id = str(uuid4())
            fields = dict(client_request_id=request_id, step_id=steps[0]["id"], page_id=page["id"],
                          language="fa", content_revision_id=page["revision_id"], duration_ms="1280",
                          consent_version="research-v1", consent="true")
            def submit(payload=None, audio=test_audio, mime="audio/webm"):
                return client.post("/api/book/submissions", data=payload or fields,
                                   files={"file": ("recording.webm", audio, mime)})
            count = lambda: len(list((temp / "raw").glob("*"))) if (temp / "raw").exists() else 0
            check(submit({**fields, "consent": "false"}), 422)
            check(submit({**fields, "consent_version": "unknown"}), 422)
            check(submit({**fields, "language": "azb"}), 409)
            check(submit({**fields, "content_revision_id": str(uuid4())}), 409)
            check(submit({**fields, "page_id": "fake"}), 409)
            check(submit(audio=b"not a webm"), 415)
            check(submit(audio=b"\x1a\x45\xdf\xa3" + b"x" * (15 * 1024 * 1024)), 413)
            assert count() == 0
            first = check(submit(), 200)
            assert first["status"] == "pending" and not first["reused"]
            again = check(submit(), 200)
            assert again["submission_id"] == first["submission_id"] and again["reused"]
            check(submit(audio=test_audio + b"changed"), 409)
            assert count() == 1
            with closing(sqlite3.connect(db)) as connection:
                connection.row_factory = sqlite3.Row
                row = connection.execute("SELECT * FROM submissions WHERE id=?", (first["submission_id"],)).fetchone()
                assert row and row["status"] == "pending" and row["page_id"] == page["id"]
                assert row["language"] == "fa" and row["content_revision_id"] == page["revision_id"]
                assert row["consent_version"] == "research-v1" and row["duration_ms"] == 1280
                assert row["file_size_bytes"] == len(test_audio) and Path(row["raw_file_ref"]).read_bytes() == test_audio
                assert connection.execute("SELECT count(*) FROM submissions WHERE client_request_id=?", (request_id,)).fetchone()[0] == 1
            check(client.get(f"/api/book/audio/{page['id']}/fa_1"), 404)
            assert check(client.get(f"/api/book/readings?page_id={page['id']}&language=fa"), 200)["readings"] == []
            raw_name = Path(row["raw_file_ref"]).name
            check(client.get(f"/api/raw_submissions/{raw_name}"), 404)
    print("PASS: consent, current story text, language and audio size/format validated before storage")
    print("PASS: one private pending submission has correct metadata; retry returns same receipt")
    print("PASS: raw recording is absent from public Listening and remains in disposable private folder")


if __name__ == "__main__":
    run()
