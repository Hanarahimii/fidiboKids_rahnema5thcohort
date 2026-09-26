"""Independent bilingual branching stories and editor."""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .main import Admin, Action, DB, ASSET_DIR, now

router = APIRouter()
LANGS = ('fa', 'azb')
TERMINALS = {'HAPPY', 'OPEN', 'SAD', 'EXIT'}


class Save(BaseModel):
    locales: dict[str, dict]
    base_revisions: dict[str, str | None]


def row(db, story_id):
    found = db.execute('SELECT * FROM your_stories WHERE id=?', (story_id,)).fetchone()
    if not found:
        raise HTTPException(404, 'Story not found')
    return found


def latest(db, story_id, language):
    return db.execute('SELECT * FROM your_story_revisions WHERE story_id=? AND language=? '
                      'ORDER BY revision_no DESC LIMIT 1', (story_id, language)).fetchone()


def revision(db, story_id, language):
    return db.execute('SELECT r.* FROM your_story_publications p JOIN your_story_revisions r '
                      'ON r.id=p.revision_id WHERE p.story_id=? AND p.language=?',
                      (story_id, language)).fetchone()


def detail(db, story_id):
    item = row(db, story_id)
    drafts = {language: latest(db, story_id, language) for language in LANGS}
    live = {language: revision(db, story_id, language) for language in LANGS}
    return {**dict(item), 'locales': {language: json.loads(drafts[language]['payload_json'])
                                    if drafts[language] else {} for language in LANGS},
            'latest_revision_ids': {language: drafts[language]['id'] if drafts[language] else None for language in LANGS},
            'published_revision_ids': {language: live[language]['id'] if live[language] else None for language in LANGS},
            'has_unpublished_changes': any(drafts[l] and (not live[l] or drafts[l]['id'] != live[l]['id']) for l in LANGS)}


def validate(payload, strict=False):
    if not isinstance(payload, dict) or not isinstance(payload.get('nodes'), dict):
        raise HTTPException(422, 'Story needs a node map')
    for field in ('title', 'description'):
        if not isinstance(payload.get(field), str) or (strict and not payload[field].strip()):
            raise HTTPException(422, f'Missing {field}')
    nodes = payload['nodes']
    if 'S1' not in nodes or not TERMINALS.issubset(nodes):
        raise HTTPException(422, 'Story needs S1 and four terminal nodes')
    for key, node in nodes.items():
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}', key) or not isinstance(node, dict):
            raise HTTPException(422, 'Invalid node')
        for field in ('title', 'text', 'art_key'):
            if not isinstance(node.get(field), str) or (strict and field != 'art_key' and not node[field].strip()):
                raise HTTPException(422, f'Missing {field} on {key}')
        art = node['art_key']
        if strict and art and (not re.fullmatch(r'upload:[0-9a-f]{32}', art)
                               or not (ASSET_DIR / (art[7:] + '.webp')).is_file()):
            raise HTTPException(422, f'Missing image on {key}')
        if key in TERMINALS:
            if node.get('choices'):
                raise HTTPException(422, f'Terminal node {key} cannot have choices')
            if key != 'EXIT' and (not isinstance(node.get('badge'), str) or (strict and not node['badge'].strip())):
                raise HTTPException(422, f'Missing badge on {key}')
            continue
        choices = node.get('choices')
        if not isinstance(choices, list) or len(choices) != 3:
            raise HTTPException(422, f'{key} needs three choices')
        if [c.get('kind') for c in choices if isinstance(c, dict)] != (
                ['ending'] * 3 if key == 'S4' else ['main', 'side', 'exit']):
            raise HTTPException(422, f'Invalid choice roles on {key}')
        if key == 'S4' and [c.get('to') for c in choices] != ['HAPPY', 'OPEN', 'SAD']:
            raise HTTPException(422, 'Final scene needs three distinct endings')
        for choice in choices:
            if (not re.fullmatch(r'[a-z0-9_-]{2,80}', str(choice.get('id', '')))
                    or not isinstance(choice.get('text'), str)
                    or (strict and not choice['text'].strip()) or choice.get('to') not in nodes):
                raise HTTPException(422, f'Invalid choice on {key}')
            if choice['kind'] == 'exit' and choice['to'] != 'EXIT':
                raise HTTPException(422, 'Exit must end this run')
    # All authored nodes must be reachable; no loop may trap a child indefinitely.
    seen, visiting = set(), set()
    def visit(key):
        if key in visiting:
            raise HTTPException(422, 'Story graph contains a cycle')
        if key in seen:
            return
        visiting.add(key)
        for choice in nodes[key].get('choices', []):
            visit(choice['to'])
        visiting.remove(key)
        seen.add(key)
    visit('S1')
    if seen != set(nodes):
        raise HTTPException(422, 'Story contains unreachable scenes')


def structure(payload):
    return {key: (node['art_key'], [(c['id'], c['kind'], c['to']) for c in node.get('choices', [])])
            for key, node in payload['nodes'].items()}


@router.get('/api/admin/your-story/stories')
def admin_stories(_: Admin, db: DB):
    return {'stories': [dict(item) | {'title': (json.loads(rev['payload_json'])['title'] if
                           (rev := latest(db, item['id'], 'fa')) else 'داستان تازه')}
                        for item in db.execute('SELECT * FROM your_stories ORDER BY position')]}


@router.post('/api/admin/your-story/stories')
def create(_: Admin, action: Action, db: DB):
    story_id = uuid4().hex
    template = json.loads((Path(__file__).resolve().parents[1] / 'data' / 'your_story_seed.json').read_text(encoding='utf-8'))
    with db:
        position = db.execute('SELECT coalesce(max(position),0)+1 FROM your_stories').fetchone()[0]
        db.execute('INSERT INTO your_stories VALUES (?,?,?)', (story_id, position, 'draft'))
        for language in LANGS:
            template[language]['title'] = 'داستان تازه' if language == 'fa' else 'یئنی قصه'
            db.execute('INSERT INTO your_story_revisions VALUES (?,?,?,?,?,?)',
                       (uuid4().hex, story_id, language, 1,
                        json.dumps(template[language], ensure_ascii=False), now()))
    return detail(db, story_id)


@router.get('/api/admin/your-story/stories/{story_id}')
def admin_story(story_id: str, _: Admin, db: DB):
    return detail(db, story_id)


@router.put('/api/admin/your-story/stories/{story_id}')
def save(story_id: str, body: Save, _: Admin, action: Action, db: DB):
    if row(db, story_id)['status'] == 'archived':
        raise HTTPException(409, 'Restore story before editing')
    if set(body.locales) != set(LANGS) or set(body.base_revisions) != set(LANGS):
        raise HTTPException(422, 'Save both languages')
    for payload in body.locales.values():
        validate(payload)
    with db:
        for language in LANGS:
            current = latest(db, story_id, language)
            if (current['id'] if current else None) != body.base_revisions[language]:
                raise HTTPException(409, 'Story changed in another tab')
            db.execute('INSERT INTO your_story_revisions VALUES (?,?,?,?,?,?)',
                       (uuid4().hex, story_id, language, 1 + (current['revision_no'] if current else 0),
                        json.dumps(body.locales[language], ensure_ascii=False), now()))
    return detail(db, story_id)


@router.post('/api/admin/your-story/stories/{story_id}/publish')
def publish(story_id: str, _: Admin, action: Action, db: DB):
    if row(db, story_id)['status'] == 'archived':
        raise HTTPException(409, 'Restore story first')
    drafts = {language: latest(db, story_id, language) for language in LANGS}
    if not all(drafts.values()):
        raise HTTPException(422, 'Both languages need content')
    data = {language: json.loads(drafts[language]['payload_json']) for language in LANGS}
    for payload in data.values():
        validate(payload, True)
    if structure(data['fa']) != structure(data['azb']):
        raise HTTPException(422, 'Both languages need the same scenes, choices, routes and images')
    with db:
        for language in LANGS:
            db.execute('INSERT INTO your_story_publications VALUES (?,?,?) ON CONFLICT(story_id,language) '
                       'DO UPDATE SET revision_id=excluded.revision_id', (story_id, language, drafts[language]['id']))
        db.execute("UPDATE your_stories SET status='published' WHERE id=?", (story_id,))
    return detail(db, story_id)


@router.post('/api/admin/your-story/stories/{story_id}/status/{operation}')
def lifecycle(story_id: str, operation: Literal['archive', 'restore'], _: Admin, action: Action, db: DB):
    current = row(db, story_id)
    if (operation == 'archive' and current['status'] == 'archived') or (operation == 'restore' and current['status'] != 'archived'):
        raise HTTPException(409, 'Invalid status transition')
    with db:
        db.execute('UPDATE your_stories SET status=? WHERE id=?',
                   ('archived' if operation == 'archive' else 'draft', story_id))
    return detail(db, story_id)


@router.get('/api/your-story/stories')
def public_stories(language: Literal['fa', 'azb'], db: DB):
    stories = []
    for item in db.execute("SELECT * FROM your_stories WHERE status='published' ORDER BY position"):
        published = revision(db, item['id'], language)
        if published:
            stories.append({'id': item['id'], 'position': item['position'], 'revision_id': published['id'],
                            'content': json.loads(published['payload_json'])})
    return {'stories': stories}

import hashlib
import os
import shutil
import tempfile
from pathlib import Path
from typing import Annotated
from fastapi import File, Form, UploadFile
from fastapi.responses import FileResponse
from .main import DB_PATH, MIME_EXTENSIONS, MAX_AUDIO_BYTES, CONSENT_VERSION, valid_audio_signature
RAW = Path(os.environ.get('KIDSBOOK_YOUR_STORY_AUDIO', DB_PATH.parent / 'your_story_audio'))
PUBLIC = Path(os.environ.get('KIDSBOOK_YOUR_STORY_PUBLISHED', DB_PATH.parent / 'your_story_published'))

@router.post('/api/your-story/submissions')
async def submission(db: DB, file: Annotated[UploadFile,File()],
                     client_request_id: Annotated[str,Form()], step_id: Annotated[str,Form()],
                     page_id: Annotated[str,Form()], language: Annotated[Literal['fa','azb'],Form()],
                     content_revision_id: Annotated[str,Form()], duration_ms: Annotated[int,Form()],
                     consent: Annotated[bool,Form()], consent_version: Annotated[str,Form()]):
    if not consent or consent_version!=CONSENT_VERSION: raise HTTPException(422,'Consent required')
    if not re.fullmatch(r'[0-9a-fA-F-]{36}',client_request_id): raise HTTPException(422,'Invalid request ID')
    if not 500<=duration_ms<=300000: raise HTTPException(422,'Invalid duration')
    mime=(file.content_type or '').split(';',1)[0].lower()
    if mime not in MIME_EXTENSIONS: raise HTTPException(415,'Unsupported audio format')
    topic=row(db,step_id)
    rev=revision(db,step_id,language)
    if topic['status']!='published' or not rev or rev['id']!=content_revision_id:
        raise HTTPException(409,'Text changed; record again')
    payload=json.loads(rev['payload_json'])
    if page_id not in payload['nodes']:
        raise HTTPException(422,'Invalid scene')
    data=await file.read(MAX_AUDIO_BYTES+1)
    if not data or len(data)>MAX_AUDIO_BYTES: raise HTTPException(413,'Audio too large')
    if not valid_audio_signature(data,mime): raise HTTPException(415,'Audio format mismatch')
    digest=hashlib.sha256(data).hexdigest()
    existing=db.execute('SELECT * FROM your_story_recordings WHERE request_id=?',(client_request_id,)).fetchone()
    if existing:
        if (existing['story_id'],existing['scene_id'],existing['language'],existing['revision_id'],existing['file_hash'],existing['duration_ms']) != (step_id,page_id,language,content_revision_id,digest,duration_ms):
            raise HTTPException(409,'Retry ID belongs to another recording')
        return {'submission_id':existing['id'],'status':existing['status'],'reused':True}
    RAW.mkdir(parents=True,exist_ok=True)
    key=uuid4().hex
    target=RAW/(key+MIME_EXTENSIONS[mime])
    fd,temp=tempfile.mkstemp(dir=RAW,prefix='upload-',suffix='.tmp')
    try:
        with os.fdopen(fd,'wb') as output: output.write(data)
        os.replace(temp,target)
        with db:
            db.execute('INSERT INTO your_story_recordings(id,request_id,story_id,scene_id,language,revision_id,duration_ms,mime,raw_path,file_hash,status,submitted_at) '
                       'VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                       (key,client_request_id,step_id,page_id,language,content_revision_id,duration_ms,mime,str(target),digest,'pending',now()))
    except BaseException:
        Path(temp).unlink(missing_ok=True);target.unlink(missing_ok=True);raise
    return {'submission_id':key,'status':'pending','reused':False}


@router.get('/api/admin/your-story/recordings')
def recordings(_: Admin, db: DB):
    return {'recordings':[dict(item) | {'raw_path':None,'published_path':None} for item in
            db.execute('SELECT * FROM your_story_recordings ORDER BY submitted_at DESC')]}


@router.get('/api/admin/your-story/recordings/{key}/audio')
def admin_audio(key: str, _: Admin, db: DB):
    item=db.execute('SELECT * FROM your_story_recordings WHERE id=?',(key,)).fetchone()
    if not item or not Path(item['raw_path']).is_file(): raise HTTPException(404,'Recording missing')
    return FileResponse(item['raw_path'],media_type=item['mime'])


@router.post('/api/admin/your-story/recordings/{key}/{operation}')
def review(key: str, operation: Literal['publish','reject','unpublish'], _: Admin, action: Action, db: DB):
    item=db.execute('SELECT * FROM your_story_recordings WHERE id=?',(key,)).fetchone()
    if not item: raise HTTPException(404,'Recording missing')
    if operation=='publish':
        topic=row(db,item['story_id'])
        live=revision(db,item['story_id'],item['language'])
        if topic['status']!='published' or not live or live['id']!=item['revision_id']:
            raise HTTPException(409,'Recording belongs to an older text revision')
        if not Path(item['raw_path']).is_file(): raise HTTPException(404,'Raw recording missing')
        PUBLIC.mkdir(parents=True,exist_ok=True)
        copied=PUBLIC/Path(item['raw_path']).name
        shutil.copy2(item['raw_path'],copied)
        with db:
            previous=db.execute("SELECT * FROM your_story_recordings WHERE story_id=? AND scene_id=? AND language=? AND status='published'",
                                (item['story_id'],item['scene_id'],item['language'])).fetchall()
            db.execute("UPDATE your_story_recordings SET status='pending',published_path=NULL,published_at=NULL WHERE story_id=? AND scene_id=? AND language=? AND status='published'",
                       (item['story_id'],item['scene_id'],item['language']))
            db.execute("UPDATE your_story_recordings SET status='published',published_path=?,published_at=? WHERE id=?",
                       (str(copied),now(),key))
        for old in previous:
            if old['published_path'] and old['id']!=key: Path(old['published_path']).unlink(missing_ok=True)
    else:
        if item['published_path']: Path(item['published_path']).unlink(missing_ok=True)
        with db:
            db.execute('UPDATE your_story_recordings SET status=?,published_path=NULL,published_at=NULL WHERE id=?',
                       ('rejected' if operation=='reject' else 'pending',key))
    return {'id':key,'status':'published' if operation=='publish' else 'rejected' if operation=='reject' else 'pending'}


@router.get('/api/your-story/readings')
def readings(story_id: str, scene_id: str, language: Literal['fa','azb'], db: DB):
    topic=row(db,story_id)
    rev=revision(db,story_id,language)
    if topic['status']!='published' or not rev: return {'readings':[]}
    records=db.execute("SELECT id,published_path FROM your_story_recordings WHERE story_id=? AND scene_id=? AND language=? AND revision_id=? AND status='published'",
                       (story_id,scene_id,language,rev['id'])).fetchall()
    return {'readings':[{'id':x['id'],'audio_url':f"/api/your-story/audio/{x['id']}"}
                        for x in records if x['published_path'] and Path(x['published_path']).is_file()]}


@router.get('/api/your-story/audio/{key}')
def public_audio(key: str, db: DB):
    item=db.execute("SELECT * FROM your_story_recordings WHERE id=? AND status='published'",(key,)).fetchone()
    if not item or not item['published_path'] or not Path(item['published_path']).is_file():
        raise HTTPException(404,'No published reading')
    live=revision(db,item['story_id'],item['language'])
    if row(db,item['story_id'])['status']!='published' or not live or live['id']!=item['revision_id']:
        raise HTTPException(404,'Reading belongs to older text')
    return FileResponse(item['published_path'],media_type=item['mime'])
