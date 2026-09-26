"""Full Discovery authoring and recording test against a disposable database."""
from __future__ import annotations
import copy
import io
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def ok(response,status=200):
    assert response.status_code==status,(response.status_code,response.text[:400])
    return response.json() if response.headers.get('content-type','').startswith('application/json') else response


def run():
    with tempfile.TemporaryDirectory(prefix='discovery-check-') as folder:
        temp=Path(folder)
        database=temp/'content.sqlite3'
        shutil.copy2(ROOT/'runtime/kidsbook.sqlite3',database)
        os.environ.update(KIDSBOOK_DB=str(database),KIDSBOOK_AUTH_FILE=str(temp/'auth.json'),
                          KIDSBOOK_ASSETS=str(temp/'assets'),
                          KIDSBOOK_DISCOVERY_AUDIO=str(temp/'audio'),
                          KIDSBOOK_DISCOVERY_PUBLISHED=str(temp/'published'))
        from app.auth import create_password_file
        create_password_file(temp/'auth.json','discovery-check-password')
        from app.main import app
        from scripts.seed_discovery import SEED
        fixture=(ROOT/'tests/fixtures/check-tone.webm').read_bytes()
        action={'X-Admin-Action':'1'}
        with TestClient(app) as admin,TestClient(app) as child:
            for lang in ('fa','azb'):
                data=ok(child.get(f'/api/discovery/topics?language={lang}'))['topics']
                assert len(data)==3 and all(len(t['content']['branches'])==3 for t in data)
                assert sum(len(x['questions']) for t in data for x in t['content']['branches'])==18
            ok(child.get('/api/admin/discovery/topics'),401)
            ok(admin.post('/api/admin/login',json={'password':'discovery-check-password'},headers=action))
            draft=ok(admin.post('/api/admin/discovery/topics',headers=action))
            image=io.BytesIO(); Image.new('RGB',(100,80),(110,78,160)).save(image,'PNG')
            uploaded=ok(admin.post('/api/admin/assets',files={'file':('discovery.png',image.getvalue(),'image/png')},headers=action))
            key=uploaded['art_key']
            ok(child.get(uploaded['url']),401)
            locales={lang:copy.deepcopy(SEED['curiosity'][lang]) for lang in ('fa','azb')}
            for data in locales.values(): data['intro_questions'][0]['art_key']=key
            saved=ok(admin.put(f"/api/admin/discovery/topics/{draft['id']}",json={
                'locales':locales,'base_revisions':draft['latest_revision_ids']},headers=action))
            assert len(ok(child.get('/api/discovery/topics?language=fa'))['topics'])==3
            broken=copy.deepcopy(locales);broken['azb']['intro_questions'][0]['answer_id']='o1'
            ok(admin.put(f"/api/admin/discovery/topics/{draft['id']}",json={
                'locales':broken,'base_revisions':saved['latest_revision_ids']},headers=action))
            ok(admin.post(f"/api/admin/discovery/topics/{draft['id']}/publish",headers=action),422)
            current=ok(admin.get(f"/api/admin/discovery/topics/{draft['id']}"))
            saved=ok(admin.put(f"/api/admin/discovery/topics/{draft['id']}",json={
                'locales':locales,'base_revisions':current['latest_revision_ids']},headers=action))
            published=ok(admin.post(f"/api/admin/discovery/topics/{draft['id']}/publish",headers=action))
            for lang in ('fa','azb'):
                topic=next(t for t in ok(child.get(f'/api/discovery/topics?language={lang}'))['topics'] if t['id']==draft['id'])
                assert topic['content']['intro_questions'][0]['art_key']==key
            ok(child.get(uploaded['url']))
            receipt=str(uuid4())
            fields={'client_request_id':receipt,'step_id':draft['id'],'page_id':'intro','language':'fa',
                    'content_revision_id':published['published_revision_ids']['fa'],
                    'duration_ms':'1200','consent':'true','consent_version':'research-v1'}
            audio={'file':('tone.webm',fixture,'audio/webm')}
            ok(child.post('/api/discovery/submissions',data={**fields,'consent':'false'},files=audio),422)
            created=ok(child.post('/api/discovery/submissions',data=fields,files=audio))
            assert created['submission_id']==ok(child.post('/api/discovery/submissions',data=fields,files=audio))['submission_id']
            assert not ok(child.get(f"/api/discovery/readings?topic_id={draft['id']}&scene_id=intro&language=fa"))['readings']
            ok(child.get(f"/api/admin/discovery/recordings/{created['submission_id']}/audio"),401)
            assert ok(admin.get(f"/api/admin/discovery/recordings/{created['submission_id']}/audio")).content==fixture
            ok(admin.post(f"/api/admin/discovery/recordings/{created['submission_id']}/publish",headers=action))
            readings=ok(child.get(f"/api/discovery/readings?topic_id={draft['id']}&scene_id=intro&language=fa"))['readings']
            assert len(readings)==1 and ok(child.get(readings[0]['audio_url'])).content==fixture
            changed=copy.deepcopy(locales);changed['fa']['intro']['text']+=' متن تازه.'
            updated=ok(admin.put(f"/api/admin/discovery/topics/{draft['id']}",json={
                'locales':changed,'base_revisions':published['latest_revision_ids']},headers=action))
            assert ok(child.get(readings[0]['audio_url'])).content==fixture # Draft does not change public text.
            ok(admin.post(f"/api/admin/discovery/topics/{draft['id']}/publish",headers=action))
            ok(child.get(readings[0]['audio_url']),404)
            ok(admin.post(f"/api/admin/discovery/recordings/{created['submission_id']}/publish",headers=action),409)
            ok(admin.post(f"/api/admin/discovery/topics/{draft['id']}/status/archive",headers=action))
            ok(admin.delete(f"/api/admin/discovery/topics/{draft['id']}",headers=action),409)
            with sqlite3.connect(database) as db:
                assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
                assert not db.execute('PRAGMA foreign_key_check').fetchall()
                assert db.execute('SELECT count(*) FROM pages').fetchone()[0]==44
    print('PASS: three bilingual topics, nine branches, correct-answer parity and protected drafts')
    print('PASS: image privacy; consent, retry, review, current text audio and stale audio protection')
    print('PASS: isolated database keeps all original story pages and recording history')


if __name__=='__main__':run()
