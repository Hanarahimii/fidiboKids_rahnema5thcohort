"""Apply the small, repeatable stage-three database update without replacing data."""

from __future__ import annotations

import argparse
import sqlite3
from contextlib import closing
from pathlib import Path


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=root / "runtime" / "kidsbook.sqlite3")
    args = parser.parse_args()
    if not args.db.is_file():
        raise SystemExit(f"Database not found: {args.db}")
    with closing(sqlite3.connect(args.db)) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript((root / "db" / "migrations" / "0002_ratings.sql").read_text(encoding="utf-8"))
        connection.executescript((root / "db" / "migrations" / "0003_banners.sql").read_text(encoding="utf-8"))
        connection.executescript((root / "db" / "migrations" / "0004_discovery.sql").read_text(encoding="utf-8"))
        connection.executescript((root / "db" / "migrations" / "0005_your_story.sql").read_text(encoding="utf-8"))
        connection.executescript((root / "db" / "migrations" / "0006_unified.sql").read_text(encoding="utf-8"))
        connection.executescript((root / "db" / "migrations" / "0007_activity.sql").read_text(encoding="utf-8"))
        connection.executescript((root / "db" / "migrations" / "0008_parent_accounts.sql").read_text(encoding="utf-8"))
        if 'parent_id' not in {row[1] for row in connection.execute('PRAGMA table_info(child_profiles)')}:
            connection.execute('ALTER TABLE child_profiles ADD COLUMN parent_id TEXT REFERENCES parent_accounts(id)')
        if 'published_path' not in {row[1] for row in connection.execute('PRAGMA table_info(discovery_recordings)')}:
            connection.execute('ALTER TABLE discovery_recordings ADD COLUMN published_path TEXT')
        # Stage 4 stored absolute paths. Moving the entire runtime folder to
        # the next stage moves the files but cannot update those old strings.
        # Rebase only when the copied file is actually present next to this DB.
        rebased = 0
        with connection:
            for table, column, folder in (
                ("submissions", "raw_file_ref", "raw_submissions"),
                ("published_audio", "published_file_ref", "published_audio"),
                ("discovery_recordings", "raw_path", "discovery_audio"),
                ("discovery_recordings", "published_path", "discovery_published"),
                ("your_story_recordings", "raw_path", "your_story_audio"),
                ("your_story_recordings", "published_path", "your_story_published"),
            ):
                for rowid, previous in connection.execute(f"SELECT rowid,{column} FROM {table}").fetchall():
                    if previous is None:
                        continue
                    target = args.db.parent / folder / Path(previous).name
                    if target.is_file() and str(target) != previous:
                        connection.execute(f"UPDATE {table} SET {column}=? WHERE rowid=?",
                                           (str(target), rowid))
                        rebased += 1
        if connection.execute("PRAGMA foreign_key_check").fetchall():
            raise SystemExit("Foreign key check failed")
    print(f"Database ready; existing pages and images preserved; {rebased} audio file references updated.")
