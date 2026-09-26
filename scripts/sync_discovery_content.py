"""Update the bundled first Discovery draft without touching later editorial work."""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / 'runtime' / 'kidsbook.sqlite3'


def digest(payload):
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def run(db_path=DEFAULT_DB):
    updated = []
    current = json.loads((ROOT / 'data/discovery_seed.json').read_text(encoding='utf-8'))
    hashes = json.loads((ROOT / 'data/discovery_seed_v1_hashes.json').read_text(encoding='utf-8'))
    with sqlite3.connect(db_path) as db:
        db.execute('PRAGMA foreign_keys=ON')
        for topic, locales in current.items():
            # Both languages must be the untouched bundled first revision. A
            # later draft in either language means the editor owns this topic.
            stock = True
            for language in ('fa', 'azb'):
                pub = db.execute('SELECT r.id,r.revision_no,r.payload_json FROM discovery_publications p '
                                 'JOIN discovery_revisions r ON r.id=p.revision_id '
                                 'WHERE p.topic_id=? AND p.language=?', (topic, language)).fetchone()
                latest = db.execute('SELECT id FROM discovery_revisions WHERE topic_id=? AND language=? '
                                    'ORDER BY revision_no DESC LIMIT 1', (topic, language)).fetchone()
                if (not pub or not latest or pub[0] != latest[0] or pub[1] != 1
                        or digest(json.loads(pub[2])) != hashes[topic][language]):
                    stock = False
                    break
            if not stock:
                continue
            with db:
                for language in ('fa', 'azb'):
                    revision_id = uuid4().hex
                    db.execute('INSERT INTO discovery_revisions '
                               '(id,topic_id,language,revision_no,payload_json,created_at) '
                               'VALUES (?,?,?,?,?,?)',
                               (revision_id, topic, language, 2,
                                json.dumps(locales[language], ensure_ascii=False),
                                datetime.now(timezone.utc).isoformat()))
                    db.execute('UPDATE discovery_publications SET revision_id=? '
                               'WHERE topic_id=? AND language=?', (revision_id, topic, language))
            updated.append(topic)
        assert not db.execute('PRAGMA foreign_key_check').fetchall()
    print('Discovery editorial sync:', ', '.join(updated) if updated else 'nothing to update')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path, default=DEFAULT_DB)
    run(parser.parse_args().db)
