"""Check the bilingual graph and published/draft boundary on a disposable database."""
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def check():
    with tempfile.TemporaryDirectory(prefix='your-story-check-') as folder:
        db_path = Path(folder) / 'content.sqlite3'
        shutil.copy2(ROOT / 'runtime' / 'kidsbook.sqlite3', db_path)
        os.environ['KIDSBOOK_DB'] = str(db_path)
        from app import main
        from app.your_story import validate, structure

        for language in ('fa', 'azb'):
            seed = json.loads((ROOT / 'data' / 'your_story_seed.json').read_text(encoding='utf-8'))[language]
            validate(seed, strict=True)
        main.app.dependency_overrides[main.require_admin] = lambda: None
        client = TestClient(main.app)
        views = {lang: client.get('/api/your-story/stories', params={'language':lang}).json()['stories']
                 for lang in ('fa','azb')}
        assert all(any(s['id']=='three_goats' for s in stories) for stories in views.values())
        fa = next(s for s in views['fa'] if s['id']=='three_goats')
        az = next(s for s in views['azb'] if s['id']=='three_goats')
        assert structure(fa['content']) == structure(az['content'])
        nodes = fa['content']['nodes']
        assert {key for key,node in nodes.items() if not node.get('choices')} == {'HAPPY','OPEN','SAD','EXIT'}
        assert [nodes['S4']['choices'][i]['to'] for i in range(3)] == ['HAPPY','OPEN','SAD']
        assert all(node['choices'][2]['to']=='EXIT' for key,node in nodes.items() if key!='S4' and node.get('choices'))
        detail = client.get('/api/admin/your-story/stories/three_goats').json()
        body = {'locales':detail['locales'],'base_revisions':detail['latest_revision_ids']}
        body['locales']['fa']['nodes']['S1']['text'] += ' آزمون موقت'
        response = client.put('/api/admin/your-story/stories/three_goats',
                              headers={'X-Admin-Action':'1'},json=body)
        assert response.status_code == 200, response.text
        current = client.get('/api/your-story/stories',params={'language':'fa'}).json()['stories'][0]
        assert 'آزمون موقت' not in current['content']['nodes']['S1']['text']
        response = client.post('/api/admin/your-story/stories/three_goats/publish',headers={'X-Admin-Action':'1'})
        assert response.status_code == 200, response.text
        current = client.get('/api/your-story/stories',params={'language':'fa'}).json()['stories'][0]
        assert 'آزمون موقت' in current['content']['nodes']['S1']['text']
        with sqlite3.connect(db_path) as db:
            assert db.execute('PRAGMA foreign_key_check').fetchall() == []
    print('Your Story graph, two languages, draft isolation, publication and foreign keys: OK')


if __name__ == '__main__':
    check()
