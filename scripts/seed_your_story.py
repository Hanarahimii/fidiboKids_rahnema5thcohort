"""Install the bilingual sample once, preserving later editor changes."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


def seed(db_path=None):
    db_path = Path(db_path or ROOT / 'runtime' / 'kidsbook.sqlite3')
    data = json.loads((ROOT / 'data' / 'your_story_seed.json').read_text(encoding='utf-8'))
    with sqlite3.connect(db_path) as db:
        db.execute('PRAGMA foreign_keys=ON')
        if db.execute("SELECT 1 FROM your_stories WHERE id='three_goats'").fetchone():
            return False
        position = db.execute('SELECT coalesce(max(position),0)+1 FROM your_stories').fetchone()[0]
        with db:
            db.execute("INSERT INTO your_stories VALUES ('three_goats',?,'published')", (position,))
            for lang in ('fa', 'azb'):
                revision_id = uuid4().hex
                db.execute('INSERT INTO your_story_revisions VALUES (?,?,?,?,?,?)',
                           (revision_id, 'three_goats', lang, 1,
                            json.dumps(data[lang], ensure_ascii=False), datetime.now(timezone.utc).isoformat()))
                db.execute('INSERT INTO your_story_publications VALUES (?,?,?)',
                           ('three_goats', lang, revision_id))
    return True


if __name__ == '__main__':
    print('Your Story sample installed.' if seed() else 'Your Story sample already exists; edits preserved.')
