"""Install the single craft from the supplied visual prototype once."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def seed(db_path=None):
    db_path = Path(db_path or ROOT / 'runtime' / 'kidsbook.sqlite3')
    payload = (ROOT / 'data' / 'craft_seed.json').read_text(encoding='utf-8')
    with sqlite3.connect(db_path) as db:
        if db.execute("SELECT 1 FROM craft_activities WHERE id='paper_cloud'").fetchone():
            return False
        with db:
            db.execute('INSERT INTO craft_activities VALUES (?,?,?,?,?)',
                       ('paper_cloud', 1, 'published', payload, datetime.now(timezone.utc).isoformat()))
    return True


if __name__ == '__main__':
    print('Craft installed.' if seed() else 'Craft already installed; editor changes preserved.')
