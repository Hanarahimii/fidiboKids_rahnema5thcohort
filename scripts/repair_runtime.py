"""Repair audio file references after moving this project to another computer.

Only file-path metadata is updated. Story text, questions, images and audio bytes
are left untouched.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path, PurePosixPath, PureWindowsPath


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "runtime" / "kidsbook.sqlite3"


def filename(value: str) -> str:
    # Databases created on Windows contain backslash paths. PureWindowsPath is
    # used explicitly so this also works when the repair is checked on Linux.
    return PureWindowsPath(value).name or PurePosixPath(value).name


if not DB.is_file():
    raise SystemExit(f"Database not found: {DB}")

changed = 0
with sqlite3.connect(DB) as connection:
    for table, column, folder in (
        ("submissions", "raw_file_ref", "raw_submissions"),
        ("published_audio", "published_file_ref", "published_audio"),
    ):
        for rowid, old_ref in connection.execute(f"SELECT rowid,{column} FROM {table}"):
            local = ROOT / "runtime" / folder / filename(old_ref)
            portable = Path("runtime") / folder / filename(old_ref)
            if local.is_file() and old_ref != str(portable):
                connection.execute(f"UPDATE {table} SET {column}=? WHERE rowid=?",
                                   (str(portable), rowid))
                changed += 1
print(f"Runtime paths ready; {changed} audio references repaired.")
