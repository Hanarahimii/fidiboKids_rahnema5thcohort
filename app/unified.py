"""Local family profiles and editable craft content for the unified experience."""
from __future__ import annotations

import base64
import hmac
import hashlib
import json
import os
import re
import secrets
import time
from urllib.parse import urlsplit
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator

from .auth import COOKIE_NAME, settings
from .edition import MODE, DONATION_URL, SECURE_COOKIES
from .main import Action, Admin, AUTH_PATH, DB, ASSET_DIR

router = APIRouter()
CHILD_COOKIE = 'kidsbook_child'
PARENT_COOKIE = 'kidsbook_parent'
CHILD_AGE = 30 * 24 * 60 * 60
PARENT_AGE = 8 * 60 * 60
_attempts: dict[str, list[float]] = {}


def _now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def _secret():
    return base64.b64decode(settings(AUTH_PATH)['secret'])


def _child_cookie(child_id: str):
    value = f'{child_id}.{int(time.time())}.{secrets.token_hex(12)}'
    signature = hmac.new(_secret(), value.encode(), hashlib.sha256).hexdigest()
    return f'{value}.{signature}'


def _child_id(token: str | None):
    try:
        child_id, issued, nonce, sig = (token or '').split('.')
        value = f'{child_id}.{issued}.{nonce}'
        age = time.time() - int(issued)
        if not (0 <= age <= CHILD_AGE) or len(nonce) < 20:
            return None
        expected = hmac.new(_secret(), value.encode(), hashlib.sha256).hexdigest()
        return child_id if hmac.compare_digest(sig, expected) else None
    except (ValueError, RuntimeError, KeyError):
        return None


def _public_child(row):
    return {key: row[key] for key in ('id', 'name', 'birth_date', 'avatar', 'daily_limit_min')}


def _parent_cookie(parent_id: str):
    value = f'parent.{parent_id}.{int(time.time())}.{secrets.token_hex(12)}'
    signature = hmac.new(_secret(), value.encode(), hashlib.sha256).hexdigest()
    return f'{value}.{signature}'


def _parent_id(token: str | None):
    try:
        role, parent_id, issued, nonce, sig = (token or '').split('.')
        value = f'{role}.{parent_id}.{issued}.{nonce}'
        age = time.time() - int(issued)
        if role != 'parent' or not (0 <= age <= PARENT_AGE) or len(nonce) < 20:
            return None
        expected = hmac.new(_secret(), value.encode(), hashlib.sha256).hexdigest()
        return parent_id if hmac.compare_digest(sig, expected) else None
    except (ValueError, RuntimeError, KeyError):
        return None


def require_parent(db: DB, kidsbook_parent: Annotated[str | None, Cookie()] = None):
    if MODE == 'child-test':
        raise HTTPException(404, 'Parent accounts are unavailable in this edition')
    parent_id = _parent_id(kidsbook_parent)
    if not parent_id or not db.execute('SELECT 1 FROM parent_accounts WHERE id=?', (parent_id,)).fetchone():
        raise HTTPException(401, 'Parent sign-in required')
    return parent_id


Parent = Annotated[str, Depends(require_parent)]


def _birth_date(value: str):
    if not value:
        return value
    match = re.fullmatch(r'(1[34]\d{2})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])', value)
    if not match:
        raise HTTPException(422, 'Choose a Solar Hijri date')
    year, month, day = map(int, match.groups())
    if day > (31 if month <= 6 else 30 if month <= 11 else _esfand_days(year)):
        raise HTTPException(422, 'Invalid Solar Hijri day')
    return value


def _esfand_days(jy):
    # Borkowski/Jalaali break-year algorithm, valid for supported 1300–1499.
    breaks = [-61,9,38,199,426,686,756,818,1111,1181,1210,1635,2060,2097,2192,2262,2324,2394,2456,3178]
    jp = breaks[0]
    for jm in breaks[1:]:
        jump = jm - jp
        if jy < jm:
            break
        jp = jm
    n = jy - jp
    if jump - n < 6:
        n = n - jump + ((jump + 4) // 33) * 33
    leap = ((n + 1) % 33 - 1) % 4
    return 30 if leap == 0 else 29


class ParentCredentials(BaseModel):
    phone: str = Field(pattern=r'^09\d{9}$')
    password: str = Field(min_length=8, max_length=128)


def _password_hash(password: str, salt: bytes):
    return hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 310_000)


def _set_parent_session(response: Response, parent_id: str):
    response.delete_cookie(COOKIE_NAME, path='/')
    response.delete_cookie(CHILD_COOKIE, path='/')
    response.set_cookie(PARENT_COOKIE, _parent_cookie(parent_id), max_age=PARENT_AGE,
                        httponly=True, secure=SECURE_COOKIES, samesite='strict', path='/')


@router.post('/api/parent/register')
def parent_register(body: ParentCredentials, response: Response, action: Action, db: DB):
    if MODE == 'child-test':
        raise HTTPException(404, 'Parent accounts are unavailable in this edition')
    if db.execute('SELECT 1 FROM parent_accounts WHERE phone=?', (body.phone,)).fetchone():
        raise HTTPException(409, 'This phone number already has an account')
    parent_id = uuid4().hex
    salt = secrets.token_bytes(16)
    with db:
        db.execute('INSERT INTO parent_accounts VALUES (?,?,?,?,?)',
                   (parent_id, body.phone, base64.b64encode(salt).decode(),
                    base64.b64encode(_password_hash(body.password, salt)).decode(), _now()))
    _set_parent_session(response, parent_id)
    return {'parent': {'id': parent_id, 'phone': body.phone}}


@router.post('/api/parent/login')
def parent_login(body: ParentCredentials, response: Response, action: Action, db: DB):
    if MODE == 'child-test':
        raise HTTPException(404, 'Parent accounts are unavailable in this edition')
    row = db.execute('SELECT * FROM parent_accounts WHERE phone=?', (body.phone,)).fetchone()
    if not row:
        raise HTTPException(401, 'Wrong phone or password')
    salt = base64.b64decode(row['password_salt'])
    expected = base64.b64decode(row['password_hash'])
    if not hmac.compare_digest(_password_hash(body.password, salt), expected):
        raise HTTPException(401, 'Wrong phone or password')
    _set_parent_session(response, row['id'])
    return {'parent': {'id': row['id'], 'phone': row['phone']}}


@router.get('/api/parent/me')
def parent_me(parent_id: Parent, db: DB):
    row = db.execute('SELECT id,phone FROM parent_accounts WHERE id=?', (parent_id,)).fetchone()
    return {'parent': dict(row)}


@router.post('/api/parent/logout')
def parent_logout(response: Response, parent_id: Parent, action: Action):
    response.delete_cookie(PARENT_COOKIE, path='/')
    return {'ok': True}


class ChildInput(BaseModel):
    name: str = Field(min_length=1, max_length=60, pattern=r'.*\S.*')
    birth_date: str = Field(default='', max_length=30)
    avatar: Literal['', 'girl', 'boy', 'phile'] = ''
    daily_limit_min: int = Field(default=30, ge=5, le=240)


class CodeInput(BaseModel):
    code: str = Field(pattern=r'^\d{4}$')


class SwitchInput(BaseModel):
    child_id: str


class AvatarInput(BaseModel):
    avatar: Literal['girl', 'boy', 'phile']


class ActivityInput(BaseModel):
    lane: Literal['story', 'discovery', 'craft']
    item_id: str = Field(min_length=1, max_length=100, pattern=r'^[a-zA-Z0-9:_-]+$')


@router.get('/api/parent/children')
def children(parent_id: Parent, db: DB):
    return {'children': [dict(row) for row in db.execute(
        'SELECT * FROM child_profiles WHERE parent_id=? ORDER BY created_at', (parent_id,))]}


@router.post('/api/parent/children')
def create_child(body: ChildInput, parent_id: Parent, action: Action, db: DB):
    for _ in range(100):
        code = f'{secrets.randbelow(10000):04d}'
        if not db.execute('SELECT 1 FROM child_profiles WHERE entry_code=?', (code,)).fetchone():
            break
    else:
        raise HTTPException(503, 'No child codes available')
    child_id = uuid4().hex
    with db:
        db.execute('INSERT INTO child_profiles '
                   '(id,name,birth_date,avatar,daily_limit_min,entry_code,created_at,parent_id) '
                   'VALUES (?,?,?,?,?,?,?,?)',
                   (child_id, body.name.strip(), _birth_date(body.birth_date), body.avatar,
                    body.daily_limit_min, code, _now(), parent_id))
    return {'child': dict(db.execute('SELECT * FROM child_profiles WHERE id=?', (child_id,)).fetchone())}


@router.put('/api/parent/children/{child_id}')
def update_child(child_id: str, body: ChildInput, parent_id: Parent, action: Action, db: DB):
    if not db.execute('SELECT 1 FROM child_profiles WHERE id=? AND parent_id=?', (child_id, parent_id)).fetchone():
        raise HTTPException(404, 'Child not found')
    with db:
        db.execute('UPDATE child_profiles SET name=?,birth_date=?,avatar=?,daily_limit_min=? '
                   'WHERE id=? AND parent_id=?',
                   (body.name.strip(), _birth_date(body.birth_date), body.avatar,
                    body.daily_limit_min, child_id, parent_id))
    return {'child': dict(db.execute('SELECT * FROM child_profiles WHERE id=?', (child_id,)).fetchone())}


@router.delete('/api/parent/children/{child_id}')
def delete_child(child_id: str, parent_id: Parent, action: Action, db: DB):
    with db:
        changed = db.execute('DELETE FROM child_profiles WHERE id=? AND parent_id=?',
                             (child_id, parent_id)).rowcount
    if not changed:
        raise HTTPException(404, 'Child not found')
    return {'ok': True}


@router.post('/api/child/login')
def child_login(body: CodeInput, response: Response, request: Request, db: DB):
    if MODE == 'child-test':
        raise HTTPException(404, 'Use quick entry')
    if body.code == '1234':
        _demo_family(db)
    ip = request.client.host if request.client else 'local'
    recent = [t for t in _attempts.get(ip, []) if time.monotonic() - t < 600]
    if len(recent) >= 5:
        raise HTTPException(429, 'Try again later')
    row = db.execute('SELECT * FROM child_profiles WHERE entry_code=?', (body.code,)).fetchone()
    if not row:
        _attempts[ip] = recent + [time.monotonic()]
        raise HTTPException(401, 'Invalid child code')
    _attempts.pop(ip, None)
    response.delete_cookie(COOKIE_NAME, path='/')
    response.delete_cookie(PARENT_COOKIE, path='/')
    response.set_cookie(CHILD_COOKIE, _child_cookie(row['id']), max_age=CHILD_AGE,
                        httponly=True, secure=SECURE_COOKIES, samesite='strict', path='/')
    return {'child': _public_child(row)}


@router.get('/api/child/me')
def child_me(db: DB, kidsbook_child: Annotated[str | None, Cookie()] = None):
    child_id = _child_id(kidsbook_child)
    row = db.execute('SELECT * FROM child_profiles WHERE id=?', (child_id,)).fetchone() if child_id else None
    if not row:
        raise HTTPException(401, 'Child entry required')
    return {'child': _public_child(row)}


@router.put('/api/child/avatar')
def choose_avatar(body: AvatarInput, action: Action, db: DB,
                  kidsbook_child: Annotated[str | None, Cookie()] = None):
    child_id = _child_id(kidsbook_child)
    if not child_id or not db.execute('SELECT 1 FROM child_profiles WHERE id=?', (child_id,)).fetchone():
        raise HTTPException(401, 'Child entry required')
    with db:
        db.execute('UPDATE child_profiles SET avatar=? WHERE id=?', (body.avatar, child_id))
    return {'child': _public_child(db.execute('SELECT * FROM child_profiles WHERE id=?', (child_id,)).fetchone())}


@router.post('/api/child/logout')
def child_logout(response: Response):
    response.delete_cookie(CHILD_COOKIE, path='/')
    return {'ok': True}


@router.post('/api/child/activity')
def complete_activity(body: ActivityInput, action: Action, db: DB,
                      kidsbook_child: Annotated[str | None, Cookie()] = None):
    child_id = _child_id(kidsbook_child)
    if not child_id or not db.execute('SELECT 1 FROM child_profiles WHERE id=?', (child_id,)).fetchone():
        raise HTTPException(401, 'Child entry required')
    with db:
        db.execute('INSERT OR IGNORE INTO child_activity VALUES (?,?,?,?)',
                   (child_id, body.lane, body.item_id, _now()))
    return {'ok': True}


@router.get('/api/parent/progress')
def parent_progress(parent_id: Parent, db: DB):
    return {'items': [dict(row) for row in db.execute(
        'SELECT a.child_id,a.lane,a.item_id,a.completed_at FROM child_activity a '
        'JOIN child_profiles c ON c.id=a.child_id WHERE c.parent_id=? ORDER BY a.completed_at DESC',
        (parent_id,))]}


@router.post('/api/parent/enter-child')
def enter_child(body: SwitchInput, response: Response, parent_id: Parent, action: Action, db: DB):
    row = db.execute('SELECT * FROM child_profiles WHERE id=? AND parent_id=?',
                     (body.child_id, parent_id)).fetchone()
    if not row:
        raise HTTPException(404, 'Child not found')
    response.delete_cookie(PARENT_COOKIE, path='/')
    response.set_cookie(CHILD_COOKIE, _child_cookie(row['id']), max_age=CHILD_AGE,
                        httponly=True, secure=SECURE_COOKIES, samesite='strict', path='/')
    return {'child': _public_child(row)}


class CraftInput(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    duration: str = Field(min_length=1, max_length=40)
    icon: str = Field(default='✂️', max_length=8)
    art_key: str = ''
    steps: list[dict] = Field(min_length=1, max_length=20)


def _validate_art(value):
    return not value or (bool(re.fullmatch(r'upload:[a-f0-9]{32}', value))
                         and (ASSET_DIR / (value[7:] + '.webp')).is_file())


def _craft_payload(body: CraftInput):
    data = body.model_dump()
    if not _validate_art(data['art_key']):
        raise HTTPException(422, 'Invalid craft image')
    for step in data['steps']:
        if not isinstance(step, dict) or not all(isinstance(step.get(k), str) and step[k].strip()
                                                  for k in ('title', 'text', 'icon')):
            raise HTTPException(422, 'Craft steps need a title, description and icon')
        if not _validate_art(step.get('art_key', '')):
            raise HTTPException(422, 'Invalid step image')
    return data


@router.get('/api/crafts')
def public_crafts(db: DB):
    return {'crafts': [{'id': row['id'], 'content': json.loads(row['payload_json'])}
                       for row in db.execute("SELECT * FROM craft_activities WHERE status='published' ORDER BY position")]}


@router.get('/api/admin/crafts')
def admin_crafts(_: Admin, db: DB):
    return {'crafts': [dict(row) | {'content': json.loads(row['payload_json'])}
                       for row in db.execute('SELECT * FROM craft_activities ORDER BY position')]}


@router.put('/api/admin/crafts/{craft_id}')
def edit_craft(craft_id: str, body: CraftInput, _: Admin, action: Action, db: DB):
    if not db.execute('SELECT 1 FROM craft_activities WHERE id=?', (craft_id,)).fetchone():
        raise HTTPException(404, 'Craft not found')
    data = _craft_payload(body)
    with db:
        db.execute('UPDATE craft_activities SET payload_json=?,updated_at=? WHERE id=?',
                   (json.dumps(data, ensure_ascii=False), _now(), craft_id))
    return {'id': craft_id, 'content': data}


@router.post('/api/admin/crafts/{craft_id}/status/{status}')
def craft_status(craft_id: str, status: Literal['published','draft','archived'],
                 _: Admin, action: Action, db: DB):
    with db:
        changed = db.execute('UPDATE craft_activities SET status=?,updated_at=? WHERE id=?',
                             (status, _now(), craft_id)).rowcount
    if not changed:
        raise HTTPException(404, 'Craft not found')
    return {'id': craft_id, 'status': status}


@router.delete('/api/admin/crafts/{craft_id}')
def delete_craft(craft_id: str, _: Admin, action: Action, db: DB):
    with db:
        changed = db.execute("DELETE FROM craft_activities WHERE id=? AND status='archived'", (craft_id,)).rowcount
    if not changed:
        raise HTTPException(409, 'Archive the craft before deleting')
    return {'ok': True}


@router.get('/api/edition')
def edition():
    return {'mode': MODE, 'donation_url': DONATION_URL, 'feedback_enabled': MODE == 'child-test'}


class SupportLinksInput(BaseModel):
    version: int = Field(ge=0)
    gateway_url: str = Field(default='', max_length=2048)
    direct_url: str = Field(default='', max_length=2048)
    card_number: str = Field(default='', max_length=32)

    @field_validator('gateway_url', 'direct_url')
    @classmethod
    def payment_link(cls, value: str) -> str:
        value = value.strip()
        if not value:
            return value
        parsed = urlsplit(value)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or any(ord(char) < 33 for char in value):
            raise ValueError('Enter a complete HTTPS payment link')
        return value

    @field_validator('card_number')
    @classmethod
    def valid_card(cls, value: str) -> str:
        number = re.sub(r'[\s-]', '', value).translate(str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789'))
        if number and not re.fullmatch(r'\d{16}', number):
            raise ValueError('Enter a 16-digit card number')
        return number


def _support_links(db: DB) -> dict:
    with db:
        db.execute('CREATE TABLE IF NOT EXISTS support_links (id INTEGER PRIMARY KEY CHECK(id=1), gateway_url TEXT NOT NULL, direct_url TEXT NOT NULL, card_number TEXT NOT NULL, version INTEGER NOT NULL)')
    row = db.execute('SELECT gateway_url,direct_url,card_number,version FROM support_links WHERE id=1').fetchone()
    return dict(row) if row else {'gateway_url':'', 'direct_url':'', 'card_number':'', 'version':0}


@router.get('/api/support-links')
def public_support_links(response: Response, db: DB):
    response.headers['Cache-Control'] = 'no-store'
    data = _support_links(db)
    return {key:data[key] for key in ('gateway_url','direct_url','card_number')}


@router.get('/api/admin/support-links')
def admin_support_links(_: Admin, db: DB):
    return _support_links(db)


@router.put('/api/admin/support-links')
def update_support_links(body: SupportLinksInput, _: Admin, action: Action, db: DB):
    _support_links(db)
    with db:
        db.execute('BEGIN IMMEDIATE')
        current = db.execute('SELECT version FROM support_links WHERE id=1').fetchone()
        if (current['version'] if current else 0) != body.version:
            raise HTTPException(409, 'Support links changed in another tab')
        db.execute('INSERT INTO support_links (id,gateway_url,direct_url,card_number,version) VALUES (1,?,?,?,?) ON CONFLICT(id) DO UPDATE SET gateway_url=excluded.gateway_url,direct_url=excluded.direct_url,card_number=excluded.card_number,version=excluded.version',
                   (body.gateway_url, body.direct_url, body.card_number, body.version+1))
    return _support_links(db)


def _demo_family(db):
    # Demo data is restricted to the presentation edition, never seeded in child-test.
    if MODE != 'presentation':
        raise HTTPException(404, 'Not found')
    with db:
        db.execute('INSERT OR IGNORE INTO parent_accounts VALUES (?,?,?,?,?)',
                   ('presentation-family', 'demo-presentation', '', '', _now()))
        for child_id, name, avatar, code, birth in [
            ('presentation-baran', 'باران', 'girl', '1234', '1398-04-12'),
            ('presentation-kian', 'کیان', 'boy', '1235', '1397-07-20')]:
            db.execute('INSERT OR IGNORE INTO child_profiles '
                       '(id,name,birth_date,avatar,daily_limit_min,entry_code,created_at,parent_id) VALUES (?,?,?,?,?,?,?,?)',
                       (child_id, name, birth, avatar, 30, code, _now(), 'presentation-family'))


class DemoInput(BaseModel):
    code: str = Field(max_length=4)


@router.post('/api/parent/demo-entry')
def demo_entry(body: DemoInput, response: Response, action: Action, db: DB):
    if MODE != 'presentation':
        raise HTTPException(404, 'Not found')
    if body.code != '1234':
        raise HTTPException(401, 'Wrong demo code')
    _demo_family(db)
    _set_parent_session(response, 'presentation-family')
    return {'ok': True}


@router.post('/api/child/quick-entry')
def quick_entry(response: Response, action: Action, db: DB,
                kidsbook_child: Annotated[str | None, Cookie()] = None):
    if MODE != 'child-test':
        raise HTTPException(404, 'Not found')
    child_id = _child_id(kidsbook_child)
    row = db.execute("SELECT * FROM child_profiles WHERE id=? AND id LIKE 'testing-%'", (child_id,)).fetchone() if child_id else None
    if not row:
        child_id = 'testing-' + uuid4().hex
        with db:
            db.execute('INSERT INTO child_profiles '
                       '(id,name,birth_date,avatar,daily_limit_min,entry_code,created_at,parent_id) VALUES (?,?,?,?,?,?,?,NULL)',
                       (child_id, 'دوست من', '', '', 30, 'test-' + uuid4().hex, _now()))
        row = db.execute('SELECT * FROM child_profiles WHERE id=?', (child_id,)).fetchone()
    response.delete_cookie(PARENT_COOKIE, path='/')
    response.delete_cookie(COOKIE_NAME, path='/')
    response.set_cookie(CHILD_COOKIE, _child_cookie(child_id), max_age=CHILD_AGE,
                        httponly=True, secure=SECURE_COOKIES, samesite='strict', path='/')
    return {'child': _public_child(row)}


class FeedbackInput(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str = Field(default='', max_length=2000)


def _feedback_table(db):
    db.execute('CREATE TABLE IF NOT EXISTS test_feedback '
               '(child_id TEXT PRIMARY KEY REFERENCES child_profiles(id) ON DELETE CASCADE, '
               'rating INTEGER NOT NULL, comment TEXT NOT NULL, created_at TEXT NOT NULL)')


@router.post('/api/test/feedback')
def test_feedback(body: FeedbackInput, action: Action, db: DB,
                  kidsbook_child: Annotated[str | None, Cookie()] = None):
    if MODE != 'child-test':
        raise HTTPException(404, 'Not found')
    child_id = _child_id(kidsbook_child)
    if not child_id or not child_id.startswith('testing-') or not db.execute('SELECT 1 FROM child_profiles WHERE id=?', (child_id,)).fetchone():
        raise HTTPException(401, 'Child entry required')
    with db:
        _feedback_table(db)
        db.execute('INSERT OR REPLACE INTO test_feedback VALUES (?,?,?,?)',
                   (child_id, body.rating, body.comment.strip(), _now()))
    return {'ok': True}


@router.delete('/api/test/session')
def forget_test(response: Response, action: Action, db: DB,
                kidsbook_child: Annotated[str | None, Cookie()] = None):
    if MODE != 'child-test':
        raise HTTPException(404, 'Not found')
    child_id = _child_id(kidsbook_child)
    if child_id and child_id.startswith('testing-'):
        with db:
            _feedback_table(db)
            db.execute('DELETE FROM child_profiles WHERE id=?', (child_id,))
    response.delete_cookie(CHILD_COOKIE, path='/')
    return {'ok': True}


@router.get('/api/admin/test-feedback')
def feedback_export(_: Admin, db: DB):
    with db:
        _feedback_table(db)
    return {'items': [dict(r) for r in db.execute('SELECT * FROM test_feedback ORDER BY created_at DESC')]}
