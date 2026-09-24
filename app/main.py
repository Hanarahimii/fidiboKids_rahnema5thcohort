"""Single-machine admin API and prebuilt React panel for the prototype."""

from __future__ import annotations

import io
import hashlib
import json
import os
import re
import shutil
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import Cookie, Depends, FastAPI, File, Form, Header, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, Field

from .auth import COOKIE_NAME, SESSION_SECONDS, auth_file, check_password, issue_cookie, valid_cookie


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.environ.get("KIDSBOOK_DB", ROOT / "runtime" / "kidsbook.sqlite3"))
AUTH_PATH = auth_file(ROOT)
ASSET_DIR = Path(os.environ.get("KIDSBOOK_ASSETS", ROOT / "runtime" / "assets"))
RAW_DIR = Path(os.environ.get("KIDSBOOK_RAW_DIR", ROOT / "runtime" / "raw_submissions"))
PUBLISHED_DIR = Path(os.environ.get("KIDSBOOK_PUBLISHED_DIR", ROOT / "runtime" / "published_audio"))
DIST = ROOT / "admin_dist"
app = FastAPI(title="Kidsbook Content Admin", docs_url=None, redoc_url=None)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def database():
    if not DB_PATH.is_file():
        raise HTTPException(503, "Database missing. Run scripts/init_db.py first.")
    # FastAPI may open a sync dependency on a worker thread and run an async
    # upload endpoint on the event-loop thread within the same request.
    connection = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
    finally:
        connection.close()


DB = Annotated[sqlite3.Connection, Depends(database)]


def require_action(x_admin_action: Annotated[str | None, Header()] = None):
    if x_admin_action != "1":
        raise HTTPException(403, "Invalid admin action header")


def require_admin(kidsbook_admin: Annotated[str | None, Cookie()] = None):
    if not valid_cookie(AUTH_PATH, kidsbook_admin):
        raise HTTPException(401, "Please sign in as admin")


Admin = Annotated[None, Depends(require_admin)]
Action = Annotated[None, Depends(require_action)]


class LoginInput(BaseModel):
    password: str


class CreateInput(BaseModel):
    step_id: str
    kind: Literal["story", "lesson", "quiz"]


class SaveInput(BaseModel):
    locales: dict[str, dict]
    base_revisions: dict[str, str | None]


class MoveInput(BaseModel):
    direction: Literal["up", "down"]


class RatingInput(BaseModel):
    client_id: str
    language: Literal["fa", "azb"]
    stars: int = Field(ge=1, le=5)


ResearchStatus = Literal["pending", "review", "screened_out", "shortlisted",
                         "selected", "published", "rejected"]


class ReviewInput(BaseModel):
    status: ResearchStatus
    note: str = Field(max_length=4000)


class SelectionInput(BaseModel):
    reading_id: str
    note: str = Field(default="", max_length=4000)


class BannerInput(BaseModel):
    art_key: str | None = None


def page_row(connection: sqlite3.Connection, page_id: str) -> sqlite3.Row:
    row = connection.execute("SELECT * FROM pages WHERE id=?", (page_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Page not found")
    return row


def latest(connection: sqlite3.Connection, page_id: str) -> dict[str, sqlite3.Row | None]:
    return {
        lang: connection.execute(
            "SELECT * FROM page_revisions WHERE page_id=? AND language=? "
            "ORDER BY revision_no DESC LIMIT 1", (page_id, lang)
        ).fetchone()
        for lang in ("fa", "azb")
    }


def publications(connection: sqlite3.Connection, page_id: str) -> dict[str, str | None]:
    return {
        lang: (row["revision_id"] if (row := connection.execute(
            "SELECT revision_id FROM page_publications WHERE page_id=? AND language=?",
            (page_id, lang)
        ).fetchone()) else None)
        for lang in ("fa", "azb")
    }


def detail(connection: sqlite3.Connection, page_id: str) -> dict:
    page = dict(page_row(connection, page_id))
    current = latest(connection, page_id)
    released = publications(connection, page_id)
    return {
        **page,
        "locales": {lang: json.loads(revision["payload_json"]) if revision else {}
                    for lang, revision in current.items()},
        "latest_revision_ids": {lang: revision["id"] if revision else None
                                for lang, revision in current.items()},
        "published_revision_ids": released,
        "has_unpublished_changes": any(
            current[lang] and current[lang]["id"] != released[lang]
            for lang in ("fa", "azb")
        ),
    }


def validate_payload(kind: str, payload: dict, strict: bool) -> None:
    if kind in ("story", "lesson"):
        if not isinstance(payload.get("text", ""), str) or not isinstance(payload.get("art_key", ""), str):
            raise HTTPException(422, "Text and image must be text fields")
        if strict and (not payload["text"].strip() or not payload["art_key"].strip()):
            raise HTTPException(422, "Both text and an image are required in each language")
    else:
        questions = payload.get("questions", [])
        if not isinstance(questions, list):
            raise HTTPException(422, "Questions must be a list")
        if strict and not questions:
            raise HTTPException(422, "Add at least one question")
        seen: set[str] = set()
        for question in questions:
            if not isinstance(question, dict):
                raise HTTPException(422, "Invalid question")
            qid = question.get("id")
            if not isinstance(qid, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{2,80}", qid) or qid in seen:
                raise HTTPException(422, "Each question needs a distinct stable ID")
            seen.add(qid)
            if question.get("category") not in ("recall", "infer", "think"):
                raise HTTPException(422, "Question category must be recall, infer or think")
            if not isinstance(question.get("prompt", ""), str):
                raise HTTPException(422, "Question prompt must be text")
            if strict and not question["prompt"].strip():
                raise HTTPException(422, "Question prompt is required in both languages")
            options = question.get("options", [])
            if not isinstance(options, list) or len(options) != 3:
                raise HTTPException(422, "Each question needs exactly three options")
            ids = [option.get("id") for option in options if isinstance(option, dict)]
            if len(ids) != 3 or len(set(ids)) != 3 or not all(
                isinstance(oid, str) and re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", oid) for oid in ids
            ):
                raise HTTPException(422, "Options need distinct stable IDs")
            if question.get("answer_id") not in ids:
                raise HTTPException(422, "Correct answer must match an option ID")
            for option in options:
                if not isinstance(option.get("text", ""), str) or not isinstance(option.get("art_key", ""), str):
                    raise HTTPException(422, "Option text and image key must be text")
                if strict and not option["text"].strip():
                    raise HTTPException(422, "Every option must have text in both languages")


def quiz_shape(payload: dict) -> list[tuple]:
    return [
        (q["id"], q["category"], q.get("number"), q["answer_id"], tuple(o["id"] for o in q["options"]))
        for q in payload["questions"]
    ]


@app.get("/api/health")
def health():
    return {"database_ready": DB_PATH.is_file(), "admin_ready": AUTH_PATH.is_file()}


@app.post("/api/admin/login", dependencies=[Depends(require_action)])
def login(body: LoginInput, response: Response):
    try:
        correct = check_password(AUTH_PATH, body.password)
    except RuntimeError as error:
        raise HTTPException(503, str(error)) from error
    if not correct:
        raise HTTPException(401, "Wrong password")
    response.set_cookie(COOKIE_NAME, issue_cookie(AUTH_PATH), max_age=SESSION_SECONDS,
                        httponly=True, samesite="strict", secure=False, path="/")
    return {"ok": True}


@app.get("/api/admin/me")
def me(_: Admin):
    return {"admin": True}


@app.post("/api/admin/logout")
def logout(response: Response, _: Admin, action: Action):
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@app.get("/api/admin/steps")
def steps(_: Admin, connection: DB):
    result = []
    for step in connection.execute("SELECT * FROM steps ORDER BY position"):
        titles = {row["language"]: row["title"] for row in connection.execute(
            "SELECT language,title FROM step_locales WHERE step_id=?", (step["id"],)
        )}
        pages = []
        for page in connection.execute(
            "SELECT * FROM pages WHERE step_id=? ORDER BY position", (step["id"],)
        ):
            revisions = latest(connection, page["id"])
            released = publications(connection, page["id"])
            pages.append({
                "id": page["id"], "kind": page["kind"], "position": page["position"],
                "status": page["status"],
                "has_unpublished_changes": any(revisions[l] and revisions[l]["id"] != released[l]
                                               for l in ("fa", "azb")),
            })
        result.append({"id": step["id"], "position": step["position"],
                       "status": step["status"], "titles": titles, "pages": pages})
    return {"steps": result}


@app.get("/api/admin/pages/{page_id}")
def get_page(page_id: str, _: Admin, connection: DB):
    return detail(connection, page_id)


@app.post("/api/admin/pages", dependencies=[Depends(require_action)])
def create_page(body: CreateInput, _: Admin, connection: DB):
    if not connection.execute("SELECT 1 FROM steps WHERE id=? AND status!='archived'", (body.step_id,)).fetchone():
        raise HTTPException(404, "Step not found")
    page_id = f"{body.step_id}-{uuid4().hex[:12]}"
    existing = connection.execute(
        "SELECT id,kind,position FROM pages WHERE step_id=? ORDER BY position", (body.step_id,)
    ).fetchall()
    if body.kind == "story":
        position = next((p["position"] for p in existing if p["kind"] != "story"), len(existing) + 1)
    elif body.kind == "lesson":
        position = next((p["position"] for p in existing if p["kind"] == "quiz"), len(existing) + 1)
    else:
        position = len(existing) + 1
    with connection:
        for existing_page in reversed(existing):
            if existing_page["position"] >= position:
                connection.execute("UPDATE pages SET position=? WHERE id=?",
                                   (existing_page["position"] + 1, existing_page["id"]))
        connection.execute(
            "INSERT INTO pages VALUES (?, ?, ?, ?, 'draft', ?, NULL)",
            (page_id, body.step_id, body.kind, position, now()),
        )
    return detail(connection, page_id)


@app.put("/api/admin/pages/{page_id}", dependencies=[Depends(require_action)])
def save_page(page_id: str, body: SaveInput, _: Admin, connection: DB):
    page = page_row(connection, page_id)
    if page["status"] == "archived":
        raise HTTPException(409, "Restore this page before editing")
    if set(body.locales) != {"fa", "azb"} or set(body.base_revisions) != {"fa", "azb"}:
        raise HTTPException(422, "Both fa and azb are required")
    current = latest(connection, page_id)
    if any(body.base_revisions[lang] != (current[lang]["id"] if current[lang] else None)
           for lang in ("fa", "azb")):
        raise HTTPException(409, "This page changed in another tab. Reload it before saving")
    for lang in ("fa", "azb"):
        validate_payload(page["kind"], body.locales[lang], strict=False)
    with connection:
        for lang in ("fa", "azb"):
            encoded = json.dumps(body.locales[lang], ensure_ascii=False, sort_keys=True)
            if current[lang] and json.loads(current[lang]["payload_json"]) == body.locales[lang]:
                continue
            connection.execute(
                "INSERT INTO page_revisions VALUES (?, ?, ?, ?, ?, ?)",
                (str(uuid4()), page_id, lang, 1 if current[lang] is None else current[lang]["revision_no"] + 1,
                 encoded, now()),
            )
    return detail(connection, page_id)


@app.post("/api/admin/pages/{page_id}/publish", dependencies=[Depends(require_action)])
def publish_page(page_id: str, _: Admin, connection: DB):
    page = page_row(connection, page_id)
    if page["status"] == "archived":
        raise HTTPException(409, "Restore this page before publishing")
    current = latest(connection, page_id)
    if any(current[lang] is None for lang in ("fa", "azb")):
        raise HTTPException(422, "Save both languages before publishing")
    payloads = {lang: json.loads(current[lang]["payload_json"]) for lang in ("fa", "azb")}
    for payload in payloads.values():
        validate_payload(page["kind"], payload, strict=True)
        if page["kind"] in ("story", "lesson") and payload["art_key"].startswith("upload:"):
            if not (ASSET_DIR / f"{payload['art_key'][7:]}.webp").is_file():
                raise HTTPException(422, "Uploaded image was not found")
    if page["kind"] == "quiz" and quiz_shape(payloads["fa"]) != quiz_shape(payloads["azb"]):
        raise HTTPException(422, "Question IDs, options and answers must match in both languages")
    with connection:
        for lang in ("fa", "azb"):
            connection.execute(
                "INSERT INTO page_publications VALUES (?, ?, ?, ?) "
                "ON CONFLICT(page_id,language) DO UPDATE SET revision_id=excluded.revision_id, "
                "published_at=excluded.published_at",
                (page_id, lang, current[lang]["id"], now()),
            )
        connection.execute("UPDATE pages SET status='published' WHERE id=?", (page_id,))
    return detail(connection, page_id)


@app.post("/api/admin/pages/{page_id}/archive", dependencies=[Depends(require_action)])
def archive_page(page_id: str, _: Admin, connection: DB):
    page_row(connection, page_id)
    with connection:
        connection.execute("UPDATE pages SET status='archived',archived_at=? WHERE id=?", (now(), page_id))
    return detail(connection, page_id)


@app.post("/api/admin/pages/{page_id}/restore", dependencies=[Depends(require_action)])
def restore_page(page_id: str, _: Admin, connection: DB):
    page = page_row(connection, page_id)
    if page["status"] != "archived":
        raise HTTPException(409, "Page is not archived")
    with connection:
        connection.execute("UPDATE pages SET status='draft',archived_at=NULL WHERE id=?", (page_id,))
    return detail(connection, page_id)


@app.post("/api/admin/pages/{page_id}/move", dependencies=[Depends(require_action)])
def move_page(page_id: str, body: MoveInput, _: Admin, connection: DB):
    page = page_row(connection, page_id)
    order = "DESC" if body.direction == "up" else "ASC"
    compare = "<" if body.direction == "up" else ">"
    neighbor = connection.execute(
        f"SELECT * FROM pages WHERE step_id=? AND position {compare} ? ORDER BY position {order} LIMIT 1",
        (page["step_id"], page["position"]),
    ).fetchone()
    if neighbor is None:
        return {"moved": False}
    temporary = connection.execute(
        "SELECT max(position)+1 FROM pages WHERE step_id=?", (page["step_id"],)
    ).fetchone()[0]
    with connection:
        connection.execute("UPDATE pages SET position=? WHERE id=?", (temporary, page_id))
        connection.execute("UPDATE pages SET position=? WHERE id=?", (page["position"], neighbor["id"]))
        connection.execute("UPDATE pages SET position=? WHERE id=?", (neighbor["position"], page_id))
    return {"moved": True}


@app.post("/api/admin/assets", dependencies=[Depends(require_action)])
async def upload_asset(file: Annotated[UploadFile, File()], _: Admin):
    if file.content_type not in ("image/png", "image/jpeg", "image/webp"):
        raise HTTPException(415, "Choose PNG, JPEG or WebP")
    data = await file.read(5 * 1024 * 1024 + 1)
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(413, "Image is larger than 5 MB")
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
        if image.width * image.height > 16_000_000:
            raise HTTPException(413, "Image dimensions are too large")
        image = ImageOps.exif_transpose(image).convert("RGB")
        if max(image.size) > 2400:
            image.thumbnail((2400, 2400))
        image_id = uuid4().hex
        ASSET_DIR.mkdir(parents=True, exist_ok=True)
        image.save(ASSET_DIR / f"{image_id}.webp", format="WEBP", quality=85)
    except (UnidentifiedImageError, OSError, ValueError) as error:
        raise HTTPException(422, "Image could not be read") from error
    return {"art_key": f"upload:{image_id}", "url": f"/api/assets/{image_id}"}


@app.get("/api/assets/{image_id}")
def get_asset(image_id: str, request: Request, connection: DB):
    if not re.fullmatch(r"[a-f0-9]{32}", image_id):
        raise HTTPException(404, "Image not found")
    path = ASSET_DIR / f"{image_id}.webp"
    if not path.is_file():
        raise HTTPException(404, "Image not found")
    public = connection.execute("""
        SELECT 1 FROM page_publications AS pub
        JOIN page_revisions AS rev ON rev.id=pub.revision_id
        JOIN pages AS page ON page.id=pub.page_id
        WHERE page.status='published' AND rev.payload_json LIKE ? LIMIT 1
    """, (f'%upload:{image_id}%',)).fetchone()
    if not public:
        public = connection.execute(
            "SELECT 1 FROM site_banners WHERE art_key=? LIMIT 1", (f"upload:{image_id}",)
        ).fetchone()
    if not public and not valid_cookie(AUTH_PATH, request.cookies.get(COOKIE_NAME)):
        raise HTTPException(401, "Image is still a draft")
    return FileResponse(path, media_type="image/webp")


def banner_url(art_key: str) -> str:
    return f"/api/assets/{art_key[7:]}"


@app.get("/api/book/banners")
def book_banners(connection: DB):
    rows = connection.execute("SELECT slot,art_key FROM site_banners").fetchall()
    available = {row["slot"]: row["art_key"] for row in rows
                 if (ASSET_DIR / f"{row['art_key'][7:]}.webp").is_file()}
    cover = available.get("cover")
    return {"cover": banner_url(cover) if cover else None,
            "steps": {slot[5:]: banner_url(key) for slot, key in available.items()
                      if slot.startswith("step:")}}


@app.get("/brand-font/{weight}")
def brand_font(weight: Literal["regular", "bold", "light"]):
    filenames = {"regular": "Kahroba-FD-RG.woff2", "bold": "Kahroba-FD-B.woff2",
                 "light": "Kahroba-FD-BL.woff2"}
    path = ROOT / "runtime" / "brand_fonts" / filenames[weight]
    if not path.is_file():
        raise HTTPException(404, "Install your licensed font locally first")
    return FileResponse(path, media_type="font/woff2", headers={"Cache-Control": "private, max-age=3600"})


@app.get("/api/admin/banners")
def admin_banners(_: Admin, connection: DB):
    saved = {row["slot"]: row["art_key"] for row in connection.execute(
        "SELECT slot,art_key FROM site_banners")}
    steps = [dict(row) for row in connection.execute(
        "SELECT s.id,sl.title AS title FROM steps s JOIN step_locales sl "
        "ON sl.step_id=s.id AND sl.language='fa' WHERE s.status!='archived' ORDER BY s.position")]
    return {"cover": saved.get("cover"),
            "steps": [{**step, "art_key": saved.get(f"step:{step['id']}")} for step in steps]}


@app.put("/api/admin/banners/{slot:path}", dependencies=[Depends(require_action)])
def save_banner(slot: str, body: BannerInput, _: Admin, connection: DB):
    if slot != "cover":
        if not slot.startswith("step:") or not connection.execute(
            "SELECT 1 FROM steps WHERE id=? AND status!='archived'", (slot[5:],)
        ).fetchone():
            raise HTTPException(404, "Banner slot not found")
    if body.art_key is not None:
        if not re.fullmatch(r"upload:[a-f0-9]{32}", body.art_key) or not (
            ASSET_DIR / f"{body.art_key[7:]}.webp"
        ).is_file():
            raise HTTPException(422, "Upload a valid banner image first")
    with connection:
        if body.art_key is None:
            connection.execute("DELETE FROM site_banners WHERE slot=?", (slot,))
        else:
            connection.execute("INSERT INTO site_banners(slot,art_key,updated_at) VALUES (?,?,?) "
                               "ON CONFLICT(slot) DO UPDATE SET art_key=excluded.art_key,updated_at=excluded.updated_at",
                               (slot, body.art_key, now()))
    return {"slot": slot, "art_key": body.art_key,
            "url": banner_url(body.art_key) if body.art_key else None}


@app.get("/api/book/steps")
def book_steps(language: Literal["fa", "azb"], connection: DB):
    result = []
    for step in connection.execute("SELECT id,position FROM steps WHERE status='published' ORDER BY position"):
        title = connection.execute(
            "SELECT title FROM step_locales WHERE step_id=? AND language=?", (step["id"], language)
        ).fetchone()[0]
        pages = []
        for row in connection.execute("""
            SELECT p.id,p.kind,p.position,r.id AS revision_id,r.payload_json
            FROM pages AS p JOIN page_publications AS pub ON pub.page_id=p.id AND pub.language=?
            JOIN page_revisions AS r ON r.id=pub.revision_id
            WHERE p.step_id=? AND p.status='published' ORDER BY p.position
        """, (language, step["id"])):
            pages.append({"id": row["id"], "kind": row["kind"], "position": row["position"],
                          "revision_id": row["revision_id"], "content": json.loads(row["payload_json"])})
        result.append({"id": step["id"], "title": title, "position": step["position"], "pages": pages})
    return {"language": language, "steps": result}


@app.get("/api/book/art/{art_key}")
def book_art(art_key: str):
    if not re.fullmatch(r"[a-z0-9_-]{2,40}", art_key):
        raise HTTPException(404, "Illustration not found")
    art_map = json.loads((ROOT / "data" / "art_map.json").read_text(encoding="utf-8"))
    filename = art_map.get(art_key)
    if not filename:
        raise HTTPException(404, "Illustration not found")
    path = ROOT / "book_art" / filename
    if not path.is_file():
        raise HTTPException(404, "Illustration not found")
    return FileResponse(path, media_type="image/png")


@app.get("/api/book/readings")
def book_readings(page_id: str, language: Literal["fa", "azb"], connection: DB):
    rows = connection.execute("""
        SELECT a.reading_id,r.ordinal,s.duration_ms,a.published_file_ref
        FROM published_audio AS a
        JOIN readings AS r ON r.id=a.reading_id AND r.language=a.language
        JOIN submissions AS s ON s.id=a.submission_id AND s.status='published'
        JOIN page_publications AS pub ON pub.page_id=a.page_id AND pub.language=a.language
             AND pub.revision_id=a.content_revision_id
        JOIN pages AS p ON p.id=a.page_id AND p.kind='story' AND p.status='published'
        WHERE a.page_id=? AND a.language=? ORDER BY r.ordinal
    """, (page_id, language)).fetchall()
    return {"page_id": page_id, "language": language,
            "readings": [{"id": row["reading_id"], "ordinal": row["ordinal"],
                          "duration_ms": row["duration_ms"],
                          "audio_url": f"/api/book/audio/{page_id}/{row['reading_id']}"} for row in rows
                         if Path(row["published_file_ref"]).is_file()]}


# File is private until a future researcher explicitly publishes a separate asset.
MAX_AUDIO_BYTES = 15 * 1024 * 1024
MIME_EXTENSIONS = {"audio/webm": ".webm", "audio/ogg": ".ogg",
                   "audio/mp4": ".m4a", "audio/wav": ".wav"}
CONSENT_VERSION = "research-v1"


def valid_audio_signature(data: bytes, mime: str) -> bool:
    return {"audio/webm": data.startswith(b"\x1a\x45\xdf\xa3"),
            "audio/ogg": data.startswith(b"OggS"),
            "audio/mp4": data[4:8] == b"ftyp",
            "audio/wav": data.startswith(b"RIFF") and data[8:12] == b"WAVE"}[mime]


@app.post("/api/book/submissions")
async def submit_recording(
    connection: DB,
    file: Annotated[UploadFile, File()],
    client_request_id: Annotated[str, Form()],
    step_id: Annotated[str, Form()],
    page_id: Annotated[str, Form()],
    language: Annotated[Literal["fa", "azb"], Form()],
    content_revision_id: Annotated[str, Form()],
    duration_ms: Annotated[int, Form()],
    consent: Annotated[bool, Form()],
    consent_version: Annotated[str, Form()],
):
    if not consent or consent_version != CONSENT_VERSION:
        raise HTTPException(422, "Explicit consent to research submission is required")
    if not re.fullmatch(r"[0-9a-fA-F-]{36}", client_request_id):
        raise HTTPException(422, "Invalid request ID")
    if duration_ms < 500 or duration_ms > 300_000:
        raise HTTPException(422, "Recording duration must be between 0.5 and 300 seconds")
    mime = (file.content_type or "").split(";", 1)[0].lower()
    if mime not in MIME_EXTENSIONS:
        raise HTTPException(415, "Unsupported audio format")
    current = connection.execute("""
        SELECT pub.revision_id FROM pages AS p
        JOIN steps AS s ON s.id=p.step_id AND s.status='published'
        JOIN page_publications AS pub ON pub.page_id=p.id AND pub.language=?
        WHERE p.id=? AND p.step_id=? AND p.kind='story' AND p.status='published'
    """, (language, page_id, step_id)).fetchone()
    if not current or current["revision_id"] != content_revision_id:
        raise HTTPException(409, "This page changed or is no longer published. Refresh and record it again")

    # Bounded memory and no server-side file before explicit Submit and consent.
    data = await file.read(MAX_AUDIO_BYTES + 1)
    if not data or len(data) > MAX_AUDIO_BYTES:
        raise HTTPException(413, "Audio is empty or larger than 15 MB")
    if not valid_audio_signature(data, mime):
        raise HTTPException(415, "Audio file does not match its format")
    digest = hashlib.sha256(data).hexdigest()
    existing = connection.execute(
        "SELECT * FROM submissions WHERE client_request_id=?", (client_request_id,)
    ).fetchone()
    if existing:
        if (existing["page_id"], existing["language"], existing["content_revision_id"],
            existing["duration_ms"], existing["mime_type"], existing["file_size_bytes"]) != (
                page_id, language, content_revision_id, duration_ms, mime, len(data)):
            raise HTTPException(409, "This retry ID belongs to another recording")
        if not Path(existing["raw_file_ref"]).is_file() or hashlib.sha256(
            Path(existing["raw_file_ref"]).read_bytes()
        ).hexdigest() != digest:
            raise HTTPException(409, "This retry ID belongs to another recording")
        return {"submission_id": existing["id"], "status": existing["status"], "reused": True}

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    submission_id = str(uuid4())
    stored_file = RAW_DIR / f"{submission_id}{MIME_EXTENSIONS[mime]}"
    descriptor, temporary = tempfile.mkstemp(dir=RAW_DIR, prefix="upload-", suffix=".tmp")
    try:
        with os.fdopen(descriptor, "wb") as destination:
            destination.write(data)
        os.replace(temporary, stored_file)
        timestamp = now()
        original = re.sub(r"[^a-zA-Z0-9._-]", "_", Path(file.filename or "recording").name)[:100]
        try:
            with connection:
                connection.execute("""INSERT INTO submissions
                    (id,client_request_id,submitted_at,language,step_id,page_id,content_revision_id,
                     duration_ms,mime_type,file_size_bytes,raw_file_ref,original_filename,consent_version,consent_at,status)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,'pending')""",
                    (submission_id, client_request_id, timestamp, language, step_id, page_id,
                     content_revision_id, duration_ms, mime, len(data), str(stored_file),
                     original, consent_version, timestamp))
        except sqlite3.IntegrityError as error:
            raise HTTPException(409, "This recording was already received. Retry to see its receipt") from error
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        stored_file.unlink(missing_ok=True)
        raise
    return {"submission_id": submission_id, "status": "pending", "reused": False}


@app.get("/api/book/audio/{page_id}/{reading_id}")
def book_audio(page_id: str, reading_id: str, connection: DB):
    row = connection.execute("""
        SELECT a.published_file_ref,s.mime_type
        FROM published_audio AS a
        JOIN submissions AS s ON s.id=a.submission_id AND s.status='published'
        JOIN page_publications AS pub ON pub.page_id=a.page_id AND pub.language=a.language
             AND pub.revision_id=a.content_revision_id
        JOIN pages AS p ON p.id=a.page_id AND p.kind='story' AND p.status='published'
        JOIN readings AS r ON r.id=a.reading_id AND r.language=a.language
        WHERE a.page_id=? AND a.reading_id=?
    """, (page_id, reading_id)).fetchone()
    if not row or not Path(row["published_file_ref"]).is_file():
        raise HTTPException(404, "No published audio for this page and reading")
    return FileResponse(row["published_file_ref"], media_type=row["mime_type"],
                        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "no-store"})


@app.get("/api/book/ratings")
def rating_summary(connection: DB):
    row = connection.execute("SELECT count(*) AS count,avg(stars) AS average FROM story_ratings").fetchone()
    return {"count": row["count"], "average": round(row["average"], 1) if row["average"] else None}


@app.post("/api/book/ratings")
def submit_rating(body: RatingInput, connection: DB):
    if not re.fullmatch(r"[a-f0-9-]{36}", body.client_id):
        raise HTTPException(422, "Invalid browser rating ID")
    timestamp = now()
    with connection:
        connection.execute("""
            INSERT INTO story_ratings (client_id,language,stars,created_at,updated_at)
            VALUES (?,?,?,?,?) ON CONFLICT(client_id) DO UPDATE SET
            language=excluded.language,stars=excluded.stars,updated_at=excluded.updated_at
        """, (body.client_id, body.language, body.stars, timestamp, timestamp))
    return {"saved": True, "stars": body.stars}


REVIEW_MOVES = {
    "pending": {"review", "screened_out", "rejected"},
    "review": {"shortlisted", "screened_out", "rejected"},
    "screened_out": {"review", "rejected"},
    "shortlisted": {"review", "rejected"},
    "selected": {"review", "shortlisted", "rejected"},
    "published": set(),
    "rejected": {"review"},
}


def submission_row(connection: sqlite3.Connection, submission_id: str) -> sqlite3.Row:
    row = connection.execute("SELECT * FROM submissions WHERE id=?", (submission_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Submission not found")
    return row


def current_story_revision(connection: sqlite3.Connection, row: sqlite3.Row) -> bool:
    return bool(connection.execute("""
        SELECT 1 FROM page_publications AS pub
        JOIN pages AS p ON p.id=pub.page_id AND p.status='published' AND p.kind='story'
        JOIN steps AS st ON st.id=p.step_id AND st.status='published'
        WHERE pub.page_id=? AND pub.language=? AND pub.revision_id=? AND p.step_id=?
    """, (row["page_id"], row["language"], row["content_revision_id"], row["step_id"])).fetchone())


def research_detail(connection: sqlite3.Connection, submission_id: str) -> dict:
    row = dict(submission_row(connection, submission_id))
    revision = connection.execute("SELECT payload_json FROM page_revisions WHERE id=?",
                                  (row["content_revision_id"],)).fetchone()
    events = [dict(event) for event in connection.execute(
        "SELECT occurred_at,actor,old_status,new_status,note FROM submission_events "
        "WHERE submission_id=? ORDER BY id", (submission_id,))]
    published = connection.execute(
        "SELECT reading_id FROM published_audio WHERE submission_id=?", (submission_id,)
    ).fetchone()
    occupant = connection.execute(
        "SELECT submission_id FROM published_audio WHERE page_id=? AND language=? AND reading_id=?",
        (row["page_id"], row["language"], row["target_reading_id"])
    ).fetchone() if row["target_reading_id"] else None
    title = connection.execute("SELECT title FROM step_locales WHERE step_id=? AND language='fa'",
                               (row["step_id"],)).fetchone()
    page_position = connection.execute("SELECT position FROM pages WHERE id=?", (row["page_id"],)).fetchone()
    row.pop("raw_file_ref")
    return {**row, "recorded_text": json.loads(revision["payload_json"])["text"],
            "is_current_revision": current_story_revision(connection, submission_row(connection, submission_id)),
            "raw_url": f"/api/research/submissions/{submission_id}/audio",
            "published_reading_id": published["reading_id"] if published else None,
            "replacing_submission_id": occupant["submission_id"] if occupant and occupant["submission_id"] != submission_id else None,
            "step_title": title["title"] if title else row["step_id"],
            "page_position": page_position["position"] if page_position else None,
            "events": events}


@app.get("/api/research/submissions")
def research_list(_: Admin, connection: DB, language: Literal["fa", "azb"] | None = None,
                  status: ResearchStatus | None = None, step_id: str | None = None):
    clauses, params = [], []
    for name, value in (("language", language), ("status", status), ("step_id", step_id)):
        if value:
            clauses.append(f"s.{name}=?"); params.append(value)
    where = "WHERE " + " AND ".join(clauses) if clauses else ""
    total = connection.execute(f"SELECT count(*) FROM submissions AS s {where}", params).fetchone()[0]
    items = [dict(row) for row in connection.execute(f"""
        SELECT s.id,s.submitted_at,s.step_id,s.page_id,s.language,s.status,
               s.duration_ms,s.review_note,s.target_reading_id,s.published_at,
               pub.revision_id AS current_revision_id,sl.title AS step_title,p.position AS page_position
        FROM submissions AS s LEFT JOIN page_publications AS pub
            ON pub.page_id=s.page_id AND pub.language=s.language
        LEFT JOIN step_locales AS sl ON sl.step_id=s.step_id AND sl.language='fa'
        LEFT JOIN pages AS p ON p.id=s.page_id
        {where} ORDER BY s.submitted_at DESC,s.id DESC LIMIT 500
    """, params)]
    for item in items:
        item["is_current_revision"] = item.pop("current_revision_id") == connection.execute(
            "SELECT content_revision_id FROM submissions WHERE id=?", (item["id"],)
        ).fetchone()[0]
    summary = [dict(row) for row in connection.execute(
        "SELECT language,status,count(*) AS count,round(avg(duration_ms)/1000.0,1) AS average_seconds "
        "FROM submissions GROUP BY language,status ORDER BY language,status"
    )]
    return {"total": total, "items": items, "summary": summary,
            "readings": {lang: [dict(row) for row in connection.execute(
                "SELECT id,ordinal FROM readings WHERE language=? ORDER BY ordinal", (lang,))]
                for lang in ("fa", "azb")}}


@app.get("/api/research/submissions/{submission_id}")
def research_get(submission_id: str, _: Admin, connection: DB):
    return research_detail(connection, submission_id)


@app.get("/api/research/submissions/{submission_id}/audio")
def research_raw_audio(submission_id: str, _: Admin, connection: DB):
    row = submission_row(connection, submission_id)
    path = Path(row["raw_file_ref"])
    if not path.is_file():
        raise HTTPException(404, "Raw file missing")
    return FileResponse(path, media_type=row["mime_type"],
                        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


@app.post("/api/research/submissions/{submission_id}/review", dependencies=[Depends(require_action)])
def research_review(submission_id: str, body: ReviewInput, _: Admin, connection: DB):
    row = submission_row(connection, submission_id)
    if body.status != row["status"] and body.status not in REVIEW_MOVES[row["status"]]:
        raise HTTPException(409, "Use shortlist, selection and publication in order")
    note = body.note.strip()
    if body.status == row["status"] and note == row["review_note"]:
        return research_detail(connection, submission_id)
    timestamp = now()
    with connection:
        connection.execute("UPDATE submissions SET status=?,review_note=?,target_reading_id=? WHERE id=?",
                           (body.status, note, row["target_reading_id"] if body.status == "selected" else None,
                            submission_id))
        connection.execute("INSERT INTO submission_events "
                           "(submission_id,occurred_at,actor,old_status,new_status,note) VALUES (?,?,?,?,?,?)",
                           (submission_id, timestamp, "researcher", row["status"], body.status, note))
    return research_detail(connection, submission_id)


@app.post("/api/research/submissions/{submission_id}/select", dependencies=[Depends(require_action)])
def research_select(submission_id: str, body: SelectionInput, _: Admin, connection: DB):
    row = submission_row(connection, submission_id)
    if row["status"] not in ("shortlisted", "selected"):
        raise HTTPException(409, "Shortlist this submission before selecting it")
    if not current_story_revision(connection, row):
        raise HTTPException(409, "The recorded text is no longer published")
    if not connection.execute("SELECT 1 FROM readings WHERE id=? AND language=?",
                              (body.reading_id, row["language"])).fetchone():
        raise HTTPException(422, "Choose a Reading from this submission's language")
    note = body.note.strip() or row["review_note"]
    if row["status"] == "selected" and row["target_reading_id"] == body.reading_id and note == row["review_note"]:
        return research_detail(connection, submission_id)
    with connection:
        connection.execute("UPDATE submissions SET status='selected',target_reading_id=?,review_note=? WHERE id=?",
                           (body.reading_id, note, submission_id))
        connection.execute("INSERT INTO submission_events "
                           "(submission_id,occurred_at,actor,old_status,new_status,note) VALUES (?,?,?,?,?,?)",
                           (submission_id, now(), "researcher", row["status"], "selected",
                           f"خوانش {body.reading_id[-1].translate(str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹'))}. {note}".strip()))
    return research_detail(connection, submission_id)


def safe_remove_published(path: str | None):
    if path and Path(path).resolve().is_relative_to(PUBLISHED_DIR.resolve()):
        try:
            Path(path).unlink(missing_ok=True)
        except OSError:
            # On Windows an open player can keep the old, unreferenced copy locked.
            pass


@app.post("/api/research/submissions/{submission_id}/publish", dependencies=[Depends(require_action)])
def research_publish(submission_id: str, _: Admin, connection: DB):
    row = submission_row(connection, submission_id)
    if row["status"] == "published" and connection.execute(
        "SELECT 1 FROM published_audio WHERE submission_id=?", (submission_id,)
    ).fetchone():
        return research_detail(connection, submission_id)
    if row["status"] != "selected" or not row["target_reading_id"]:
        raise HTTPException(409, "Select a Reading before publishing")
    if not current_story_revision(connection, row):
        raise HTTPException(409, "The recorded text is no longer published")
    raw = Path(row["raw_file_ref"])
    if not raw.is_file() or raw.stat().st_size != row["file_size_bytes"]:
        raise HTTPException(409, "The raw recording is missing or changed")
    if connection.execute("SELECT 1 FROM published_audio WHERE submission_id=? AND "
                          "NOT (page_id=? AND language=? AND reading_id=?)",
                          (submission_id, row["page_id"], row["language"], row["target_reading_id"])).fetchone():
        raise HTTPException(409, "This recording already belongs to another Reading")
    former = connection.execute("SELECT submission_id,published_file_ref FROM published_audio "
                                "WHERE page_id=? AND language=? AND reading_id=?",
                                (row["page_id"], row["language"], row["target_reading_id"])).fetchone()
    PUBLISHED_DIR.mkdir(parents=True, exist_ok=True)
    target = PUBLISHED_DIR / f"{uuid4().hex}{MIME_EXTENSIONS[row['mime_type']]}"
    descriptor, temporary = tempfile.mkstemp(dir=PUBLISHED_DIR, prefix="publish-", suffix=".tmp")
    try:
        with os.fdopen(descriptor, "wb") as destination, raw.open("rb") as source:
            shutil.copyfileobj(source, destination)
        os.replace(temporary, target)
        timestamp = now()
        with connection:
            if former and former["submission_id"] != submission_id:
                old = submission_row(connection, former["submission_id"])
                connection.execute("UPDATE submissions SET status='selected',published_at=NULL WHERE id=?",
                                   (old["id"],))
                connection.execute("INSERT INTO submission_events "
                                   "(submission_id,occurred_at,actor,old_status,new_status,note) "
                                   "VALUES (?,?,?,?,?,?)", (old["id"], timestamp, "researcher", old["status"],
                                                       "selected", "با صدای دیگری جایگزین شد"))
            connection.execute("""INSERT INTO published_audio
                (page_id,language,reading_id,submission_id,content_revision_id,published_file_ref,published_at)
                VALUES (?,?,?,?,?,?,?) ON CONFLICT(page_id,language,reading_id) DO UPDATE SET
                submission_id=excluded.submission_id,content_revision_id=excluded.content_revision_id,
                published_file_ref=excluded.published_file_ref,published_at=excluded.published_at""",
                (row["page_id"], row["language"], row["target_reading_id"], submission_id,
                 row["content_revision_id"], str(target), timestamp))
            connection.execute("UPDATE submissions SET status='published',published_at=? WHERE id=?",
                               (timestamp, submission_id))
            connection.execute("INSERT INTO submission_events "
                               "(submission_id,occurred_at,actor,old_status,new_status,note) VALUES (?,?,?,?,?,?)",
                               (submission_id, timestamp, "researcher", "selected", "published",
                                "در کتاب منتشر شد"))
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        target.unlink(missing_ok=True)
        raise
    if former:
        safe_remove_published(former["published_file_ref"])
    return research_detail(connection, submission_id)


@app.post("/api/research/submissions/{submission_id}/unpublish", dependencies=[Depends(require_action)])
def research_unpublish(submission_id: str, _: Admin, connection: DB):
    row = submission_row(connection, submission_id)
    publication = connection.execute("SELECT published_file_ref FROM published_audio WHERE submission_id=?",
                                     (submission_id,)).fetchone()
    if row["status"] != "published" or not publication:
        raise HTTPException(409, "This submission is not the active published Reading")
    with connection:
        connection.execute("DELETE FROM published_audio WHERE submission_id=?", (submission_id,))
        connection.execute("UPDATE submissions SET status='selected',published_at=NULL WHERE id=?",
                           (submission_id,))
        connection.execute("INSERT INTO submission_events "
                           "(submission_id,occurred_at,actor,old_status,new_status,note) VALUES (?,?,?,?,?,?)",
                           (submission_id, now(), "researcher", "published", "selected", "انتشار از کتاب برداشته شد"))
    safe_remove_published(publication["published_file_ref"])
    return research_detail(connection, submission_id)


@app.get("/{path:path}")
def admin_app(path: str):
    if path.startswith("api/"):
        raise HTTPException(404, "Not found")
    candidate = (DIST / path).resolve()
    if path and candidate.is_relative_to(DIST.resolve()) and candidate.is_file():
        return FileResponse(candidate)
    index = DIST / "index.html"
    if not index.is_file():
        raise HTTPException(503, "Admin panel build missing")
    return FileResponse(index)
