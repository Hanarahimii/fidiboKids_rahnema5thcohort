"""Initialize a fresh prototype database from the normalized bilingual seed."""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def validate_seed(data: dict) -> None:
    if data.get("format_version") != 1 or data.get("languages") != ["fa", "azb"]:
        raise ValueError("Unsupported seed format or languages")
    if len(data["steps"]) != 7:
        raise ValueError("Expected seven steps")
    seen_pages: set[str] = set()
    seen_questions: set[str] = set()
    for step_position, step in enumerate(data["steps"], 1):
        if step["position"] != step_position or set(step["titles"]) != {"fa", "azb"}:
            raise ValueError(f"Invalid step order or titles: {step['id']}")
        if [p["kind"] for p in step["pages"]] != ["story"] * 4 + ["lesson", "quiz"]:
            raise ValueError(f"Missing story/lesson/quiz page in {step['id']}")
        for page_position, page in enumerate(step["pages"], 1):
            if page["position"] != page_position or page["id"] in seen_pages:
                raise ValueError(f"Invalid page ID/order in {step['id']}")
            seen_pages.add(page["id"])
            if page["kind"] == "quiz":
                questions = page["questions"]
                if len(questions) != 9:
                    raise ValueError(f"Wrong question count on {page['id']}")
                for q in questions:
                    if q["id"] in seen_questions or set(q["prompts"]) != {"fa", "azb"}:
                        raise ValueError(f"Question IDs/translations invalid: {q['id']}")
                    seen_questions.add(q["id"])
                    options = q["options"]
                    if len(options) != 3 or len({o["id"] for o in options}) != 3:
                        raise ValueError(f"Invalid options: {q['id']}")
                    if q["answer_id"] not in {o["id"] for o in options}:
                        raise ValueError(f"Unknown answer: {q['id']}")
                    if not all(q["prompts"][lang] and all(o["labels"][lang] for o in options)
                               for lang in ("fa", "azb")):
                        raise ValueError(f"Missing translation: {q['id']}")
            elif set(page["locales"]) != {"fa", "azb"} or not page["art_key"]:
                raise ValueError(f"Page translations/art invalid: {page['id']}")
    if len(seen_pages) != 42 or len(seen_questions) != 63:
        raise ValueError("Seed page/question count invalid")


def locale_payload(page: dict, language: str) -> dict:
    if page["kind"] in ("story", "lesson"):
        return {"text": page["locales"][language]["text"], "art_key": page["art_key"]}
    return {"questions": [
        {"id": q["id"], "category": q["category"], "number": q["number"],
         "prompt": q["prompts"][language], "answer_id": q["answer_id"],
         "options": [{"id": o["id"], "text": o["labels"][language], "art_key": o["art_key"]}
                     for o in q["options"]]}
        for q in page["questions"]
    ]}


def initialize(seed_path: Path, schema_path: Path, db_path: Path) -> None:
    data = json.loads(seed_path.read_text(encoding="utf-8"))
    validate_seed(data)
    if db_path.exists():
        raise FileExistsError(f"Refusing to overwrite existing database: {db_path}")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    try:
        connection.executescript(schema_path.read_text(encoding="utf-8"))
        connection.execute("PRAGMA foreign_keys = ON")
        now = utc_now()
        with connection:
            for language in ("fa", "azb"):
                for ordinal in range(1, 5):
                    connection.execute(
                        "INSERT INTO readings (id, language, ordinal) VALUES (?, ?, ?)",
                        (f"{language}_{ordinal}", language, ordinal),
                    )
            for step in data["steps"]:
                connection.execute(
                    "INSERT INTO steps (id, position, status) VALUES (?, ?, 'published')",
                    (step["id"], step["position"]),
                )
                for language, title in step["titles"].items():
                    connection.execute(
                        "INSERT INTO step_locales VALUES (?, ?, ?)", (step["id"], language, title)
                    )
                for page in step["pages"]:
                    connection.execute(
                        "INSERT INTO pages VALUES (?, ?, ?, ?, 'published', ?, NULL)",
                        (page["id"], step["id"], page["kind"], page["position"], now),
                    )
                    for language in ("fa", "azb"):
                        revision_id = str(uuid4())
                        content = json.dumps(locale_payload(page, language), ensure_ascii=False)
                        connection.execute(
                            "INSERT INTO page_revisions VALUES (?, ?, ?, 1, ?, ?)",
                            (revision_id, page["id"], language, content, now),
                        )
                        connection.execute(
                            "INSERT INTO page_publications VALUES (?, ?, ?, ?)",
                            (page["id"], language, revision_id, now),
                        )
    except BaseException:
        connection.close()
        db_path.unlink(missing_ok=True)
        raise
    connection.close()


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=Path, default=root / "data" / "initial_content.json")
    parser.add_argument("--schema", type=Path, default=root / "db" / "schema.sql")
    parser.add_argument("--db", type=Path, default=root / "runtime" / "kidsbook.sqlite3")
    args = parser.parse_args()
    initialize(args.seed, args.schema, args.db)
    print(f"Initialized {args.db}")
