"""Exercise private review, Reading selection, replacement, revocation and stale scripts."""
from __future__ import annotations

import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from contextlib import closing
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SAMPLE = (ROOT / "tests" / "fixtures" / "check-tone.webm").read_bytes()
SAMPLE_2 = (ROOT / "tests" / "fixtures" / "check-tone-2.webm").read_bytes()


def check(response, code=200):
    assert response.status_code == code, (
        f"Expected HTTP {code}; got {response.status_code} from {response.request.url.path}"
    )
    return response.json() if "application/json" in response.headers.get("content-type", "") else response


def mutation(client, path, data=None):
    return check(client.post(path, json=data, headers={"X-Admin-Action": "1"}))


def run():
    with tempfile.TemporaryDirectory(prefix="kidsbook-stage5-") as folder:
        temporary = Path(folder)
        db = temporary / "check.sqlite3"
        source = ROOT / "runtime" / "kidsbook.sqlite3"
        if source.exists():
            with closing(sqlite3.connect(source)) as old, closing(sqlite3.connect(db)) as new:
                old.backup(new)
        else:
            from scripts.init_db import initialize
            initialize(ROOT / "data" / "initial_content.json", ROOT / "db" / "schema.sql", db)
        with closing(sqlite3.connect(db)) as connection:
            connection.executescript((ROOT / "db" / "migrations" / "0002_ratings.sql").read_text(encoding="utf-8"))
            # The test needs empty Reading slots even if the real book has
            # already published audio. Change only the disposable DB copy.
            with connection:
                connection.execute("UPDATE submissions SET status='selected',published_at=NULL "
                                   "WHERE status='published' AND id IN "
                                   "(SELECT submission_id FROM published_audio)")
                connection.execute("DELETE FROM published_audio")
        # Simulate a real stage-four runtime that moved to another folder.
        previous_raw = temporary / "old-stage-four" / "raw_submissions" / "existing.webm"
        previous_raw.parent.mkdir(parents=True)
        previous_raw.write_bytes(SAMPLE)
        copied_raw = temporary / "raw_submissions" / previous_raw.name
        copied_raw.parent.mkdir()
        shutil.copy2(previous_raw, copied_raw)
        migrated_id = str(uuid4())
        with closing(sqlite3.connect(db)) as connection:
            page_before, step_before, revision_before = connection.execute(
                "SELECT p.id,p.step_id,pub.revision_id FROM pages AS p "
                "JOIN page_publications AS pub ON pub.page_id=p.id AND pub.language='fa' "
                "WHERE p.kind='story' LIMIT 1").fetchone()
            with connection:
                connection.execute("""INSERT INTO submissions
                    (id,client_request_id,submitted_at,language,step_id,page_id,content_revision_id,
                     duration_ms,mime_type,file_size_bytes,raw_file_ref,original_filename,consent_version,consent_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (migrated_id, str(uuid4()), "2026-01-01", "fa", step_before, page_before,
                     revision_before, 1200, "audio/webm", len(SAMPLE), str(previous_raw),
                     "existing.webm", "research-v1", "2026-01-01"))
        result = subprocess.run([sys.executable, str(ROOT / "scripts" / "upgrade_db.py"), "--db", str(db)],
                                capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        with closing(sqlite3.connect(db)) as connection:
            assert connection.execute("SELECT raw_file_ref FROM submissions WHERE id=?", (migrated_id,)).fetchone()[0] == str(copied_raw)
        shutil.rmtree(previous_raw.parent.parent)
        os.environ.update(KIDSBOOK_DB=str(db), KIDSBOOK_RAW_DIR=str(temporary / "raw"),
                          KIDSBOOK_PUBLISHED_DIR=str(temporary / "published"),
                          KIDSBOOK_AUTH_FILE=str(temporary / "auth.json"),
                          KIDSBOOK_ASSETS=str(temporary / "assets"))
        from app.auth import create_password_file
        create_password_file(temporary / "auth.json", "temporary-review-password")
        from app.main import app
        with TestClient(app) as client, TestClient(app) as outsider:
            fa_step = check(client.get("/api/book/steps?language=fa"))["steps"][0]
            azb_step = check(client.get("/api/book/steps?language=azb"))["steps"][0]
            page = fa_step["pages"][0]
            assert page["id"] == azb_step["pages"][0]["id"]
            def submit(language, revision, audio):
                form = dict(client_request_id=str(uuid4()), step_id=fa_step["id"], page_id=page["id"],
                            language=language, content_revision_id=revision, duration_ms="1200",
                            consent="true", consent_version="research-v1")
                return check(client.post("/api/book/submissions", data=form,
                                         files={"file": ("sample.webm", audio, "audio/webm")}))["submission_id"]
            first = submit("fa", page["revision_id"], SAMPLE)
            second = submit("fa", page["revision_id"], SAMPLE_2)
            azb = submit("azb", azb_step["pages"][0]["revision_id"], SAMPLE)
            screened = submit("fa", page["revision_id"], SAMPLE)
            raw_first = temporary / "raw" / f"{first}.webm"
            assert raw_first.read_bytes() == SAMPLE
            check(outsider.get(f"/api/research/submissions/{first}"), 401)
            check(outsider.get(f"/api/research/submissions/{first}/audio"), 401)
            check(outsider.get("/api/research/submissions"), 401)
            check(outsider.post(f"/api/research/submissions/{first}/publish", headers={"X-Admin-Action": "1"}), 401)
            check(client.get(f"/api/book/audio/{page['id']}/fa_1"), 404)
            check(client.post("/api/admin/login", headers={"X-Admin-Action": "1",
                              }, json={"password": "temporary-review-password"}))
            result = check(client.get("/api/research/submissions?language=fa&status=pending"))
            assert result["total"] >= 3 and all(item["language"] == "fa" for item in result["items"])
            assert sum(i["count"] for i in result["summary"] if i["language"] == "fa") >= 2
            assert check(client.get(f"/api/research/submissions/{first}/audio")).content == SAMPLE
            assert check(client.get(f"/api/research/submissions/{migrated_id}/audio")).content == SAMPLE
            assert check(client.get(f"/api/research/submissions/{first}/audio")).headers["cache-control"] == "no-store"
            check(client.post(f"/api/research/submissions/{first}/review",
                              json={"status": "review", "note": "listen"}), 403)
            check(client.post(f"/api/research/submissions/{first}/publish",
                              headers={"X-Admin-Action": "1"}), 409)
            check(client.post(f"/api/research/submissions/{first}/select",
                              headers={"X-Admin-Action": "1"}, json={"reading_id": "fa_1"}), 409)
            mutation(client, f"/api/research/submissions/{screened}/review",
                     {"status": "screened_out", "note": "Needs further review"})
            mutation(client, f"/api/research/submissions/{screened}/review",
                     {"status": "review", "note": "Reviewed again"})
            mutation(client, f"/api/research/submissions/{screened}/review",
                     {"status": "rejected", "note": "Not selected"})
            check(client.post(f"/api/research/submissions/{screened}/publish",
                              headers={"X-Admin-Action": "1"}), 409)
            def prepare(submission, lang, reading):
                detail = mutation(client, f"/api/research/submissions/{submission}/review",
                                  {"status": "review", "note": "Reviewed by researcher"})
                assert detail["status"] == "review"
                mutation(client, f"/api/research/submissions/{submission}/review",
                         {"status": "shortlisted", "note": "Suitable"})
                detail = mutation(client, f"/api/research/submissions/{submission}/select",
                                  {"reading_id": reading, "note": "Selected"})
                assert detail["status"] == "selected" and detail["language"] == lang
                return detail
            prepare(first, "fa", "fa_1")
            check(client.post(f"/api/research/submissions/{first}/select",
                              headers={"X-Admin-Action": "1"}, json={"reading_id": "azb_1"}), 422)
            published = mutation(client, f"/api/research/submissions/{first}/publish")
            assert published["published_reading_id"] == "fa_1" and published["status"] == "published"
            first_public_path = next((temporary / "published").iterdir())
            assert first_public_path.read_bytes() == raw_first.read_bytes()
            assert first_public_path != raw_first
            assert SAMPLE not in outsider.get(f"/runtime/published_audio/{first_public_path.name}").content
            assert SAMPLE not in outsider.get(f"/runtime/raw_submissions/{raw_first.name}").content
            check(outsider.get(f"/api/book/audio/{page['id']}/fa_1"))
            assert check(outsider.get(f"/api/book/audio/{page['id']}/fa_1")).content == SAMPLE
            assert check(outsider.get(f"/api/book/audio/{page['id']}/fa_1")).headers["content-type"].startswith("audio/webm")
            assert [r["id"] for r in check(outsider.get(f"/api/book/readings?page_id={page['id']}&language=fa"))["readings"]] == ["fa_1"]
            assert check(outsider.get(f"/api/book/readings?page_id={page['id']}&language=azb"))["readings"] == []
            assert mutation(client, f"/api/research/submissions/{first}/publish")["id"] == first
            prepare(second, "fa", "fa_1")
            mutation(client, f"/api/research/submissions/{second}/publish")
            assert check(outsider.get(f"/api/book/audio/{page['id']}/fa_1")).content == SAMPLE_2
            assert check(client.get(f"/api/research/submissions/{first}"))["status"] == "selected"
            assert raw_first.read_bytes() == SAMPLE and not first_public_path.exists()
            mutation(client, f"/api/research/submissions/{second}/unpublish")
            check(outsider.get(f"/api/book/audio/{page['id']}/fa_1"), 404)
            assert len(list((temporary / "published").iterdir())) == 0
            mutation(client, f"/api/research/submissions/{second}/publish")
            prepare(azb, "azb", "azb_1")
            mutation(client, f"/api/research/submissions/{azb}/publish")
            assert check(outsider.get(f"/api/book/audio/{page['id']}/azb_1")).content == SAMPLE
            assert check(outsider.get(f"/api/book/readings?page_id={page['id']}&language=azb"))["readings"][0]["id"] == "azb_1"
            # New published script hides audio tied to the previous revision.
            original = check(client.get(f"/api/admin/pages/{page['id']}"))
            locales = original["locales"]
            locales["fa"]["text"] += " (revised)"
            check(client.put(f"/api/admin/pages/{page['id']}", headers={"X-Admin-Action": "1"}, json={
                "locales": locales, "base_revisions": original["latest_revision_ids"]}))
            check(client.post(f"/api/admin/pages/{page['id']}/publish", headers={"X-Admin-Action": "1"}))
            assert check(outsider.get(f"/api/book/readings?page_id={page['id']}&language=fa"))["readings"] == []
            check(outsider.get(f"/api/book/audio/{page['id']}/fa_1"), 404)
            mutation(client, f"/api/research/submissions/{second}/unpublish")
            check(client.post(f"/api/research/submissions/{second}/publish", headers={"X-Admin-Action": "1"}), 409)
            assert check(outsider.get(f"/api/book/audio/{page['id']}/azb_1")).content == SAMPLE
            events = check(client.get(f"/api/research/submissions/{second}"))["events"]
            assert [e["new_status"] for e in events].count("published") == 2
            assert [e["new_status"] for e in events].count("selected") >= 2
    print("PASS: private researcher playback, notes, filters and status transitions require admin session")
    print("PASS: selected Reading publishes separate playable WebM; replacement and unpublish keep raw files")
    print("PASS: moved raw files survive upgrade; language and text revision hide obsolete audio")


if __name__ == "__main__":
    run()
