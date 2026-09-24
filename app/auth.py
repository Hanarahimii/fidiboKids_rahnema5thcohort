"""Local admin password and signed, short-lived HTTP-only session cookie."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import os
import time
from pathlib import Path


COOKIE_NAME = "kidsbook_admin"
SESSION_SECONDS = 8 * 60 * 60


def auth_file(root: Path) -> Path:
    return Path(os.environ.get("KIDSBOOK_AUTH_FILE", root / "runtime" / "admin_auth.json"))


def create_password_file(path: Path, password: str) -> None:
    if path.exists():
        raise FileExistsError(f"Admin password already exists: {path}")
    if len(password) < 8:
        raise ValueError("Use at least eight characters for the admin password")
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 310_000)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "salt": base64.b64encode(salt).decode("ascii"),
        "hash": base64.b64encode(digest).decode("ascii"),
        "secret": base64.b64encode(os.urandom(32)).decode("ascii"),
    }), encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass  # Windows permissions are managed by the user's account.


def settings(path: Path) -> dict:
    if not path.is_file():
        raise RuntimeError("Admin password is not configured. Run scripts/set_admin_password.py first.")
    return json.loads(path.read_text(encoding="utf-8"))


def check_password(path: Path, password: str) -> bool:
    data = settings(path)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), base64.b64decode(data["salt"]), 310_000
    )
    return hmac.compare_digest(digest, base64.b64decode(data["hash"]))


def issue_cookie(path: Path) -> str:
    issued = str(int(time.time()))
    nonce = base64.urlsafe_b64encode(os.urandom(12)).decode("ascii").rstrip("=")
    payload = f"{issued}.{nonce}"
    secret = base64.b64decode(settings(path)["secret"])
    signature = hmac.new(secret, payload.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def valid_cookie(path: Path, token: str | None) -> bool:
    if not token:
        return False
    try:
        issued, nonce, signature = token.split(".")
        age = int(time.time()) - int(issued)
        if age < 0 or age > SESSION_SECONDS or len(nonce) < 12:
            return False
        secret = base64.b64decode(settings(path)["secret"])
        expected = hmac.new(secret, f"{issued}.{nonce}".encode("ascii"), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)
    except (ValueError, RuntimeError, KeyError, binascii.Error):
        return False
