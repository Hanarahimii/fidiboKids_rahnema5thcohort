"""Insert the three editorial Discovery topics once; never overwrite later edits."""
import json
import sqlite3
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / 'runtime' / 'kidsbook.sqlite3'


def question(number, prompt, choices, answer):
    return {'id': f'q{number}', 'prompt': prompt, 'art_key': '',
            'answer_id': f'o{answer}', 'options': [
                {'id': f'o{i}', 'text': label, 'art_key': ''}
                for i, label in enumerate(choices, 1)]}


def branch(key, label, story, badge, questions):
    return {'id': key, 'label': label, 'text': story, 'art_key': '',
            'badge': {'title': badge, 'art_key': ''},
            'questions': [question(i, *item) for i, item in enumerate(questions, 1)]}


def topic(title, intro, prompt, intro_questions, branches, badge):
    return {'title': title, 'intro': {'text': intro, 'art_key': ''},
            'intro_questions': [question(i, *item) for i, item in enumerate(intro_questions, 1)],
            'choice_prompt': prompt,
            'branches': [branch(chr(97+i), *item) for i, item in enumerate(branches)],
            'badge': {'title': badge, 'art_key': ''}}


SEED = json.loads((ROOT / 'data' / 'discovery_seed.json').read_text(encoding='utf-8'))


def run(db=DB):
    with sqlite3.connect(db) as connection:
        connection.execute('PRAGMA foreign_keys=ON')
        for position, (slug, locales) in enumerate(SEED.items(), 1):
            if connection.execute('SELECT 1 FROM discovery_topics WHERE id=?', (slug,)).fetchone():
                continue
            with connection:
                connection.execute('INSERT INTO discovery_topics(id,position,status) VALUES (?,?,?)', (slug,position,'published'))
                for language, payload in locales.items():
                    rid=uuid4().hex
                    connection.execute('INSERT INTO discovery_revisions(id,topic_id,language,revision_no,payload_json,created_at) VALUES (?,?,?,?,?,?)',
                                       (rid,slug,language,1,json.dumps(payload,ensure_ascii=False),datetime.now(timezone.utc).isoformat()))
                    connection.execute('INSERT INTO discovery_publications(topic_id,language,revision_id) VALUES (?,?,?)', (slug,language,rid))
        assert connection.execute('PRAGMA foreign_key_check').fetchall()==[]
    print('Discovery seed ready: three bilingual topics (existing edits preserved).')


if __name__ == '__main__': run()
