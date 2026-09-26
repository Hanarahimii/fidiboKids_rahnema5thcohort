"""Check source completeness and prove that new story/quiz pages fit the model."""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import tempfile
from pathlib import Path
from uuid import uuid4


def count(connection: sqlite3.Connection, sql: str) -> int:
    return connection.execute(sql).fetchone()[0]


def check(db_path: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="kidsbook-check-") as folder:
        trial = Path(folder) / "trial.sqlite3"
        shutil.copy2(db_path, trial)
        connection = sqlite3.connect(trial)
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
            assert count(connection, "SELECT count(*) FROM steps") == 7
            assert count(connection, "SELECT count(*) FROM pages WHERE kind='story'") == 28
            assert count(connection, "SELECT count(*) FROM pages WHERE kind='lesson'") == 7
            assert count(connection, "SELECT count(*) FROM pages WHERE kind='quiz'") == 7
            assert count(connection, "SELECT count(*) FROM page_publications") == 84
            assert count(connection, "SELECT count(*) FROM readings") == 8
            assert count(connection, "SELECT count(*) FROM submissions") == 0

            quizzes = connection.execute("""
                SELECT p.id, pub.language, r.payload_json
                FROM pages AS p JOIN page_publications AS pub ON pub.page_id=p.id
                JOIN page_revisions AS r ON r.id=pub.revision_id
                WHERE p.kind='quiz'
            """).fetchall()
            assert len(quizzes) == 14
            for page_id, language, encoded in quizzes:
                questions = json.loads(encoded)["questions"]
                assert len(questions) == 9, (page_id, language)
                assert [(q["category"], q["number"]) for q in questions] == [
                    (category, number) for category in ("recall", "infer", "think")
                    for number in (1, 2, 3)
                ]
                for q in questions:
                    assert len(q["options"]) == 3
                    assert q["answer_id"] in {o["id"] for o in q["options"]}
            for page_id, encoded_fa, encoded_azb in connection.execute("""
                SELECT p.id, rf.payload_json, ra.payload_json
                FROM pages AS p
                JOIN page_publications AS pf ON pf.page_id=p.id AND pf.language='fa'
                JOIN page_revisions AS rf ON rf.id=pf.revision_id
                JOIN page_publications AS pa ON pa.page_id=p.id AND pa.language='azb'
                JOIN page_revisions AS ra ON ra.id=pa.revision_id
                WHERE p.kind='quiz'
            """):
                fa = json.loads(encoded_fa)["questions"]
                azb = json.loads(encoded_azb)["questions"]
                assert [(q["id"], q["answer_id"], [o["id"] for o in q["options"]]) for q in fa] == [
                    (q["id"], q["answer_id"], [o["id"] for o in q["options"]]) for q in azb
                ], page_id

            # A draft added from the future admin panel can be published in both
            # languages without modifying a single line of frontend content.
            for kind, position in (("story", 7), ("quiz", 8)):
                page_id = f"check-{kind}-{uuid4().hex[:8]}"
                with connection:
                    connection.execute(
                        "INSERT INTO pages VALUES (?, 'ask', ?, ?, 'draft', 'test', NULL)",
                        (page_id, kind, position),
                    )
                    for language in ("fa", "azb"):
                        revision_id = str(uuid4())
                        if kind == "story":
                            payload = {"text": f"Test {language}", "art_key": "test-art"}
                        else:
                            payload = {"questions": [{
                                "id": "check-q1", "category": "recall", "number": 1,
                                "prompt": f"Test {language}?", "answer_id": "yes",
                                "options": [{"id": "yes", "text": "Yes", "art_key": "yes"},
                                            {"id": "no", "text": "No", "art_key": "no"}],
                            }]}
                        connection.execute(
                            "INSERT INTO page_revisions VALUES (?, ?, ?, 1, ?, 'test')",
                            (revision_id, page_id, language, json.dumps(payload)),
                        )
                        connection.execute(
                            "INSERT INTO page_publications VALUES (?, ?, ?, 'test')",
                            (page_id, language, revision_id),
                        )
                    connection.execute("UPDATE pages SET status='published' WHERE id=?", (page_id,))
                assert count(connection, f"SELECT count(*) FROM page_publications WHERE page_id='{page_id}'") == 2

            # Publishing a new text revision retains the old revision for the
            # submission research trail. Audio visibility will require equality
            # with the current publication revision in the future reader API.
            old_revision = connection.execute(
                "SELECT revision_id FROM page_publications WHERE page_id='ask-1' AND language='fa'"
            ).fetchone()[0]
            new_revision = str(uuid4())
            with connection:
                connection.execute(
                    "INSERT INTO page_revisions VALUES (?, 'ask-1', 'fa', 2, ?, 'test')",
                    (new_revision, json.dumps({"text": "Updated", "art_key": "story"})),
                )
                connection.execute(
                    "UPDATE page_publications SET revision_id=?, published_at='test' "
                    "WHERE page_id='ask-1' AND language='fa'", (new_revision,),
                )
            assert old_revision != new_revision
            assert count(connection, f"SELECT count(*) FROM page_revisions WHERE id='{old_revision}'") == 1
            assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        finally:
            connection.close()
    print("PASS: 7 steps, 28 story pages, 7 lessons, 7 quizzes, 63 bilingual questions")
    print("PASS: stable IDs, answer parity, 84 published locale revisions, 8 Reading slots")
    print("PASS: adding story/quiz pages and replacing text revisions in an isolated database copy")


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=root / "runtime" / "kidsbook.sqlite3")
    args = parser.parse_args()
    check(args.db)
