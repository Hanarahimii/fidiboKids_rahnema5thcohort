"""Test a complete upload → review → publication → second reader journey."""
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
SAMPLE = (ROOT / "tests" / "fixtures" / "check-tone.webm").read_bytes()
SAMPLE_2 = (ROOT / "tests" / "fixtures" / "check-tone-2.webm").read_bytes()


def expect(response, code=200):
    assert response.status_code == code, (
        f"Expected HTTP {code}; got {response.status_code} from {response.request.url.path}"
    )
    return response.json() if "application/json" in response.headers.get("content-type", "") else response


def main():
    with tempfile.TemporaryDirectory(prefix="kidsbook-stage6-") as folder:
        temporary = Path(folder)
        db = temporary / "check.sqlite3"
        source = ROOT / "runtime" / "kidsbook.sqlite3"
        if source.is_file():
            with closing(sqlite3.connect(source)) as old, closing(sqlite3.connect(db)) as new:
                old.backup(new)
        else:
            from scripts.init_db import initialize
            initialize(ROOT / "data" / "initial_content.json", ROOT / "db" / "schema.sql", db)
        with closing(sqlite3.connect(db)) as connection:
            connection.executescript((ROOT / "db" / "migrations" / "0002_ratings.sql").read_text(encoding="utf-8"))
            # Existing user publications stay untouched. The test starts with
            # clear slots in its own copy to exercise the full publication flow.
            with connection:
                connection.execute("UPDATE submissions SET status='selected',published_at=NULL "
                                   "WHERE status='published' AND id IN (SELECT submission_id FROM published_audio)")
                connection.execute("DELETE FROM published_audio")
        os.environ.update(KIDSBOOK_DB=str(db), KIDSBOOK_AUTH_FILE=str(temporary / "auth.json"),
                          KIDSBOOK_RAW_DIR=str(temporary / "raw"),
                          KIDSBOOK_PUBLISHED_DIR=str(temporary / "published"),
                          KIDSBOOK_ASSETS=str(temporary / "assets"))
        from app.auth import create_password_file
        create_password_file(temporary / "auth.json", "temporary-stage-six-password")
        from app.main import app
        with TestClient(app) as recording_child, TestClient(app) as researcher, TestClient(app) as next_reader:
            fa = expect(recording_child.get("/api/book/steps?language=fa"))["steps"]
            azb = expect(next_reader.get("/api/book/steps?language=azb"))["steps"]
            assert len(fa) == len(azb) == 7
            step = fa[0]
            stories = [p for p in step["pages"] if p["kind"] == "story"]
            assert len(stories) >= 3
            first, second, empty = stories[:3]
            azb_first = next(p for p in azb[0]["pages"] if p["id"] == first["id"])
            assert first["id"] == azb_first["id"] and first["revision_id"] != azb_first["revision_id"]
            def send(page, language, recording, agree=True):
                fields = {"client_request_id": str(uuid4()), "step_id": step["id"], "page_id": page["id"],
                          "language": language, "content_revision_id": page["revision_id"],
                          "duration_ms": "1200", "consent_version": "research-v1", "consent": str(agree).lower()}
                response = recording_child.post("/api/book/submissions", data=fields,
                    files={"file": ("reading.webm", recording, "audio/webm")})
                return response
            expect(send(first, "fa", SAMPLE, False), 422)
            assert not (temporary / "raw").exists()
            first_id = expect(send(first, "fa", SAMPLE))["submission_id"]
            second_id = expect(send(second, "fa", SAMPLE_2))["submission_id"]
            azb_id = expect(send(azb_first, "azb", SAMPLE_2))["submission_id"]
            assert expect(next_reader.get(f"/api/book/readings?page_id={first['id']}&language=fa"))["readings"] == []
            expect(next_reader.get(f"/api/book/audio/{first['id']}/fa_1"), 404)
            expect(next_reader.get(f"/api/research/submissions/{first_id}/audio"), 401)
            expect(researcher.post("/api/admin/login", json={"password": "temporary-stage-six-password"},
                headers={"X-Admin-Action": "1"}))
            def decide(submission, reading):
                route = f"/api/research/submissions/{submission}"
                for status in ("review", "shortlisted"):
                    assert expect(researcher.post(f"{route}/review", json={"status": status, "note": "Checked"},
                        headers={"X-Admin-Action": "1"}))["status"] == status
                chosen = expect(researcher.post(f"{route}/select", json={"reading_id": reading, "note": "Ready"},
                    headers={"X-Admin-Action": "1"}))
                assert chosen["target_reading_id"] == reading
                assert expect(researcher.post(f"{route}/publish", headers={"X-Admin-Action": "1"}))["status"] == "published"
            decide(first_id, "fa_1")
            decide(second_id, "fa_1")
            decide(azb_id, "azb_1")
            for page, language, reading, sample in (
                (first, "fa", "fa_1", SAMPLE), (second, "fa", "fa_1", SAMPLE_2),
                (first, "azb", "azb_1", SAMPLE_2),
            ):
                choices = expect(next_reader.get(f"/api/book/readings?page_id={page['id']}&language={language}"))["readings"]
                assert [item["id"] for item in choices] == [reading]
                response = expect(next_reader.get(choices[0]["audio_url"]))
                assert response.content == sample and response.headers["content-type"].startswith("audio/webm")
                partial = expect(next_reader.get(choices[0]["audio_url"], headers={"Range": "bytes=0-31"}), 206)
                assert partial.content == sample[:32]
            assert expect(next_reader.get(f"/api/book/readings?page_id={empty['id']}&language=fa"))["readings"] == []
            expect(next_reader.get(f"/api/book/audio/{empty['id']}/fa_1"), 404)
            assert expect(next_reader.get(f"/api/book/readings?page_id={second['id']}&language=azb"))["readings"] == []
            expect(next_reader.get(f"/api/research/submissions/{second_id}/audio"), 401)
            with closing(sqlite3.connect(db)) as connection:
                assert connection.execute("SELECT count(*) FROM published_audio WHERE submission_id IN (?,?,?)",
                                          (first_id, second_id, azb_id)).fetchone()[0] == 3
                raw_ref = Path(connection.execute("SELECT raw_file_ref FROM submissions WHERE id=?", (first_id,)).fetchone()[0])
                public_ref = Path(connection.execute("SELECT published_file_ref FROM published_audio WHERE submission_id=?", (first_id,)).fetchone()[0])
                assert raw_ref != public_ref and raw_ref.read_bytes() == public_ref.read_bytes() == SAMPLE
            public_ref.unlink()
            assert expect(next_reader.get(f"/api/book/readings?page_id={first['id']}&language=fa"))["readings"] == []
            expect(next_reader.get(f"/api/book/audio/{first['id']}/fa_1"), 404)
            assert raw_ref.read_bytes() == SAMPLE
    print("PASS: child records with consent; researcher reviews and publishes FA/AZB Reading 1")
    print("PASS: separate reader sees only published slots, playable audio and seekable byte ranges")
    print("PASS: same Reading spans two story pages; missing slots and raw audio stay private")


if __name__ == "__main__":
    main()
