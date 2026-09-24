"""Set the first-run admin password locally. This file is not included in backups."""

from __future__ import annotations

import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.auth import auth_file, create_password_file  # noqa: E402


if __name__ == "__main__":
    path = auth_file(Path(__file__).resolve().parents[1])
    if path.exists():
        print("An admin password is already set. The existing password was not changed.")
        raise SystemExit(1)
    first = getpass.getpass("Choose an admin password (at least 8 characters): ")
    second = getpass.getpass("Repeat the password: ")
    if first != second:
        print("The passwords did not match. Please run this command again.")
        raise SystemExit(1)
    try:
        create_password_file(path, first)
    except ValueError as error:
        print(error)
        raise SystemExit(1) from error
    print("Admin password set. Keep it private; it is not shown again.")
