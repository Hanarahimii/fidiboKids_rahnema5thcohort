"""Independent Discovery content, child reader, and private recording workflow."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import tempfile
from pathlib import Path
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .main import (ROOT, ASSET_DIR, DB, Admin, Action, DB_PATH, MIME_EXTENSIONS,
                   MAX_AUDIO_BYTES, CONSENT_VERSION, now, valid_audio_signature)

router = APIRouter()
LANGS = ('fa', 'azb')
RAW = Path(os.environ.get('KIDSBOOK_DISCOVERY_AUDIO', DB_PATH.parent / 'discovery_audio'))
PUBLIC = Path(os.environ.get('KIDSBOOK_DISCOVERY_PUBLISHED', DB_PATH.parent / 'discovery_published'))


class Save(BaseModel):
    locales: dict[str, dict]
    base_revisions: dict[str, str | None]


class Direction(BaseModel):
    direction: Literal['up', 'down']


def row(db, slug):
    item = db.execute('SELECT * FROM discovery_topics WHERE id=?', (slug,)).fetchone()
    if not item:
        raise HTTPException(404, 'Discovery topic not found')
    return item


def latest(db, slug, lang):
    return db.execute('SELECT * FROM discovery_revisions WHERE topic_id=? AND language=? ORDER BY revision_no DESC LIMIT 1',
                      (slug, lang)).fetchone()


def revision(db, slug, lang):
    return db.execute('SELECT r.* FROM discovery_publications p JOIN discovery_revisions r ON r.id=p.revision_id '
                      'WHERE p.topic_id=? AND p.language=?', (slug, lang)).fetchone()


def detail(db, slug):
    item = row(db, slug)
    draft = {lang: latest(db, slug, lang) for lang in LANGS}
    published = {lang: revision(db, slug, lang) for lang in LANGS}
    return {**dict(item), 'locales': {lang: json.loads(draft[lang]['payload_json']) if draft[lang] else {}
                                     for lang in LANGS},
            'latest_revision_ids': {lang: draft[lang]['id'] if draft[lang] else None for lang in LANGS},
            'published_revision_ids': {lang: published[lang]['id'] if published[lang] else None for lang in LANGS},
            'has_unpublished_changes': any(draft[l] and (not published[l] or draft[l]['id'] != published[l]['id'])
                                           for l in LANGS)}


def require_text(value, strict):
    if not isinstance(value, str) or (strict and not value.strip()):
        raise HTTPException(422, 'Required localized text is missing')


def image_key(value, strict):
    if not isinstance(value, str):
        raise HTTPException(422, 'Image reference must be text')
    if strict and value and (not re.fullmatch(r'upload:[0-9a-f]{32}', value)
                             or not (ASSET_DIR / (value[7:] + '.webp')).is_file()):
        raise HTTPException(422, 'Upload the missing image before publishing')


def questions(value, strict):
    if not isinstance(value, list) or (strict and not value):
        raise HTTPException(422, 'Add at least one question')
    seen = set()
    for q in value:
        if not isinstance(q, dict) or not re.fullmatch(r'[\w-]{2,80}', str(q.get('id', ''))) or q['id'] in seen:
            raise HTTPException(422, 'Questions need distinct stable IDs')
        seen.add(q['id'])
        require_text(q.get('prompt', ''), strict)
        image_key(q.get('art_key', ''), strict)
        options = q.get('options', [])
        if not isinstance(options, list) or len(options) != 3:
            raise HTTPException(422, 'Every question needs three options')
        ids = [o.get('id') for o in options if isinstance(o, dict)]
        if len(ids) != 3 or len(set(ids)) != 3 or any(not re.fullmatch(r'[\w-]{2,80}', str(x)) for x in ids):
            raise HTTPException(422, 'Options need distinct stable IDs')
        if q.get('answer_id') not in ids:
            raise HTTPException(422, 'Select a correct answer')
        for option in options:
            require_text(option.get('text', ''), strict)
            image_key(option.get('art_key', ''), strict)


def validate(data, strict=False):
    if not isinstance(data, dict):
        raise HTTPException(422, 'Content must be an object')
    require_text(data.get('title', ''), strict)
    intro = data.get('intro', {})
    if not isinstance(intro, dict):
        raise HTTPException(422, 'Intro must be an object')
    require_text(intro.get('text', ''), strict)
    image_key(intro.get('art_key', ''), strict)
    questions(data.get('intro_questions', []), strict)
    require_text(data.get('choice_prompt', ''), strict)
    branches = data.get('branches', [])
    if not isinstance(branches, list) or (strict and not branches):
        raise HTTPException(422, 'Add a branch')
    seen = set()
    for branch in branches:
        if not isinstance(branch, dict) or not re.fullmatch(r'[\w-]{1,80}', str(branch.get('id', ''))) or branch['id'] in seen:
            raise HTTPException(422, 'Branches need distinct stable IDs')
        seen.add(branch['id'])
        require_text(branch.get('label', ''), strict)
        require_text(branch.get('text', ''), strict)
        image_key(branch.get('art_key', ''), strict)
        questions(branch.get('questions', []), strict)
        badge = branch.get('badge', {})
        if not isinstance(badge, dict):
            raise HTTPException(422, 'Badge must be an object')
        require_text(badge.get('title', ''), strict)
        image_key(badge.get('art_key', ''), strict)
    badge = data.get('badge', {})
    if not isinstance(badge, dict):
        raise HTTPException(422, 'Topic badge must be an object')
    require_text(badge.get('title', ''), strict)
    image_key(badge.get('art_key', ''), strict)


def shape(data):
    def qs(value):
        return [(q['id'], q['answer_id'], q.get('art_key', ''),
                 [(o['id'], o.get('art_key', '')) for o in q['options']]) for q in value]
    return [data['intro'].get('art_key', ''), qs(data['intro_questions']),
            [(b['id'], b.get('art_key', ''), b['badge'].get('art_key', ''), qs(b['questions']))
             for b in data['branches']], data['badge'].get('art_key', '')]


@router.get('/api/admin/discovery/topics')
def admin_topics(_: Admin, db: DB):
    return {'topics': [dict(topic) | {'title': (json.loads(r['payload_json'])['title'] if
                                  (r := latest(db, topic['id'], 'fa')) else 'موضوع تازه')}
                       for topic in db.execute('SELECT * FROM discovery_topics ORDER BY position')]}


@router.post('/api/admin/discovery/topics')
def create(_: Admin, action: Action, db: DB):
    slug = uuid4().hex
    with db:
        position = db.execute('SELECT coalesce(max(position),0)+1 FROM discovery_topics').fetchone()[0]
        db.execute('INSERT INTO discovery_topics(id,position,status) VALUES (?,?,?)', (slug,position,'draft'))
    return detail(db,slug)


@router.get('/api/admin/discovery/topics/{slug}')
def admin_topic(slug: str, _: Admin, db: DB):
    return detail(db,slug)


@router.put('/api/admin/discovery/topics/{slug}')
def save(slug: str, body: Save, _: Admin, action: Action, db: DB):
    topic = row(db,slug)
    if topic['status']=='archived':
        raise HTTPException(409,'Restore the topic before editing')
    if set(body.locales) != set(LANGS) or set(body.base_revisions) != set(LANGS):
        raise HTTPException(422,'Save both languages')
    for data in body.locales.values(): validate(data)
    with db:
        for lang in LANGS:
            current = latest(db,slug,lang)
            if (current['id'] if current else None)!=body.base_revisions[lang]:
                raise HTTPException(409,'This topic changed in another tab')
            db.execute('INSERT INTO discovery_revisions(id,topic_id,language,revision_no,payload_json,created_at) '
                       'VALUES (?,?,?,?,?,?)', (uuid4().hex,slug,lang,1+(current['revision_no'] if current else 0),
                        json.dumps(body.locales[lang],ensure_ascii=False),now()))
    return detail(db,slug)


@router.post('/api/admin/discovery/topics/{slug}/publish')
def publish(slug: str, _: Admin, action: Action, db: DB):
    topic=row(db,slug)
    if topic['status']=='archived': raise HTTPException(409,'Restore topic first')
    drafts={lang:latest(db,slug,lang) for lang in LANGS}
    if not all(drafts.values()): raise HTTPException(422,'Both languages need content')
    data={lang:json.loads(drafts[lang]['payload_json']) for lang in LANGS}
    for payload in data.values(): validate(payload,True)
    if shape(data['fa'])!=shape(data['azb']):
        raise HTTPException(422,'Branches, questions, answers and images must match across languages')
    with db:
        for lang in LANGS:
            db.execute('INSERT INTO discovery_publications(topic_id,language,revision_id) VALUES (?,?,?) '
                       'ON CONFLICT(topic_id,language) DO UPDATE SET revision_id=excluded.revision_id',
                       (slug,lang,drafts[lang]['id']))
        db.execute("UPDATE discovery_topics SET status='published' WHERE id=?", (slug,))
    return detail(db,slug)


@router.post('/api/admin/discovery/topics/{slug}/status/{operation}')
def lifecycle(slug: str, operation: Literal['archive','restore'], _: Admin, action: Action, db: DB):
    topic=row(db,slug)
    if operation=='restore' and topic['status']!='archived': raise HTTPException(409,'Not archived')
    with db:
        db.execute('UPDATE discovery_topics SET status=? WHERE id=?',
                   ('archived' if operation=='archive' else 'draft',slug))
    return detail(db,slug)


@router.post('/api/admin/discovery/topics/{slug}/move')
def move(slug: str, body: Direction, _: Admin, action: Action, db: DB):
    topic=row(db,slug)
    neighbor=db.execute('SELECT * FROM discovery_topics WHERE position {} ? ORDER BY position {} LIMIT 1'.format(
        '<' if body.direction=='up' else '>', 'DESC' if body.direction=='up' else 'ASC'),
        (topic['position'],)).fetchone()
    if neighbor:
        with db:
            # Negative temporary position respects uniqueness while swapping.
            db.execute('UPDATE discovery_topics SET position=-1 WHERE id=?',(slug,))
            db.execute('UPDATE discovery_topics SET position=? WHERE id=?',(topic['position'],neighbor['id']))
            db.execute('UPDATE discovery_topics SET position=? WHERE id=?',(neighbor['position'],slug))
    return detail(db,slug)


@router.delete('/api/admin/discovery/topics/{slug}')
def delete(slug: str, _: Admin, action: Action, db: DB):
    topic=row(db,slug)
    if topic['status']!='archived': raise HTTPException(409,'Archive before deleting')
    if db.execute('SELECT 1 FROM discovery_recordings WHERE topic_id=? LIMIT 1',(slug,)).fetchone():
        raise HTTPException(409,'This topic has recordings')
    with db:
        db.execute('DELETE FROM discovery_publications WHERE topic_id=?',(slug,))
        db.execute('DELETE FROM discovery_revisions WHERE topic_id=?',(slug,))
        db.execute('DELETE FROM discovery_topics WHERE id=?',(slug,))
        db.execute('UPDATE discovery_topics SET position=position-1 WHERE position>?',(topic['position'],))
    return {'deleted':True}


@router.get('/api/discovery/topics')
def public_topics(language: Literal['fa','azb'], db: DB):
    topics=[]
    for item in db.execute("SELECT * FROM discovery_topics WHERE status='published' ORDER BY position"):
        rev=revision(db,item['id'],language)
        if rev:
            topics.append({'id':item['id'],'position':item['position'],'revision_id':rev['id'],
                           'content':json.loads(rev['payload_json'])})
    return {'topics':topics}


@router.post('/api/discovery/submissions')
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
    if page_id not in ['intro', *(b['id'] for b in payload['branches'])]:
        raise HTTPException(422,'Invalid scene')
    data=await file.read(MAX_AUDIO_BYTES+1)
    if not data or len(data)>MAX_AUDIO_BYTES: raise HTTPException(413,'Audio too large')
    if not valid_audio_signature(data,mime): raise HTTPException(415,'Audio format mismatch')
    digest=hashlib.sha256(data).hexdigest()
    existing=db.execute('SELECT * FROM discovery_recordings WHERE request_id=?',(client_request_id,)).fetchone()
    if existing:
        if (existing['topic_id'],existing['scene_id'],existing['language'],existing['revision_id'],existing['file_hash'],existing['duration_ms']) != (step_id,page_id,language,content_revision_id,digest,duration_ms):
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
            db.execute('INSERT INTO discovery_recordings(id,request_id,topic_id,scene_id,language,revision_id,duration_ms,mime,raw_path,file_hash,status,submitted_at) '
                       'VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                       (key,client_request_id,step_id,page_id,language,content_revision_id,duration_ms,mime,str(target),digest,'pending',now()))
    except BaseException:
        Path(temp).unlink(missing_ok=True);target.unlink(missing_ok=True);raise
    return {'submission_id':key,'status':'pending','reused':False}


@router.get('/api/admin/discovery/recordings')
def recordings(_: Admin, db: DB):
    return {'recordings':[dict(item) | {'raw_path':None,'published_path':None} for item in
            db.execute('SELECT * FROM discovery_recordings ORDER BY submitted_at DESC')]}


@router.get('/api/admin/discovery/recordings/{key}/audio')
def admin_audio(key: str, _: Admin, db: DB):
    item=db.execute('SELECT * FROM discovery_recordings WHERE id=?',(key,)).fetchone()
    if not item or not Path(item['raw_path']).is_file(): raise HTTPException(404,'Recording missing')
    return FileResponse(item['raw_path'],media_type=item['mime'])


@router.post('/api/admin/discovery/recordings/{key}/{operation}')
def review(key: str, operation: Literal['publish','reject','unpublish'], _: Admin, action: Action, db: DB):
    item=db.execute('SELECT * FROM discovery_recordings WHERE id=?',(key,)).fetchone()
    if not item: raise HTTPException(404,'Recording missing')
    if operation=='publish':
        topic=row(db,item['topic_id'])
        live=revision(db,item['topic_id'],item['language'])
        if topic['status']!='published' or not live or live['id']!=item['revision_id']:
            raise HTTPException(409,'Recording belongs to an older text revision')
        if not Path(item['raw_path']).is_file(): raise HTTPException(404,'Raw recording missing')
        PUBLIC.mkdir(parents=True,exist_ok=True)
        copied=PUBLIC/Path(item['raw_path']).name
        shutil.copy2(item['raw_path'],copied)
        with db:
            previous=db.execute("SELECT * FROM discovery_recordings WHERE topic_id=? AND scene_id=? AND language=? AND status='published'",
                                (item['topic_id'],item['scene_id'],item['language'])).fetchall()
            db.execute("UPDATE discovery_recordings SET status='pending',published_path=NULL,published_at=NULL WHERE topic_id=? AND scene_id=? AND language=? AND status='published'",
                       (item['topic_id'],item['scene_id'],item['language']))
            db.execute("UPDATE discovery_recordings SET status='published',published_path=?,published_at=? WHERE id=?",
                       (str(copied),now(),key))
        for old in previous:
            if old['published_path'] and old['id']!=key: Path(old['published_path']).unlink(missing_ok=True)
    else:
        if item['published_path']: Path(item['published_path']).unlink(missing_ok=True)
        with db:
            db.execute('UPDATE discovery_recordings SET status=?,published_path=NULL,published_at=NULL WHERE id=?',
                       ('rejected' if operation=='reject' else 'pending',key))
    return {'id':key,'status':'published' if operation=='publish' else 'rejected' if operation=='reject' else 'pending'}


@router.get('/api/discovery/readings')
def readings(topic_id: str, scene_id: str, language: Literal['fa','azb'], db: DB):
    topic=row(db,topic_id)
    rev=revision(db,topic_id,language)
    if topic['status']!='published' or not rev: return {'readings':[]}
    records=db.execute("SELECT id,published_path FROM discovery_recordings WHERE topic_id=? AND scene_id=? AND language=? AND revision_id=? AND status='published'",
                       (topic_id,scene_id,language,rev['id'])).fetchall()
    return {'readings':[{'id':x['id'],'audio_url':f"/api/discovery/audio/{x['id']}"}
                        for x in records if x['published_path'] and Path(x['published_path']).is_file()]}


@router.get('/api/discovery/audio/{key}')
def public_audio(key: str, db: DB):
    item=db.execute("SELECT * FROM discovery_recordings WHERE id=? AND status='published'",(key,)).fetchone()
    if not item or not item['published_path'] or not Path(item['published_path']).is_file():
        raise HTTPException(404,'No published reading')
    live=revision(db,item['topic_id'],item['language'])
    if row(db,item['topic_id'])['status']!='published' or not live or live['id']!=item['revision_id']:
        raise HTTPException(404,'Reading belongs to older text')
    return FileResponse(item['published_path'],media_type=item['mime'])
