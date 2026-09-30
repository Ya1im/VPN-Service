"""JSON-backed user store. The bot is the single writer."""
from __future__ import annotations

import json
import logging
import os
import re
import secrets
import tempfile
import uuid
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path

from .models import User

log = logging.getLogger(__name__)
NAME_RE = re.compile(r"^[\w-]{1,32}$")


class UserStore:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def list(self) -> list[User]:
        try:
            raw = json.loads(self.path.read_text())
            return [User(**item) for item in raw]
        except FileNotFoundError:
            return []
        except (ValueError, TypeError) as e:
            log.error("users file %s unreadable: %s", self.path, e)
            return []

    def active(self) -> list[User]:
        return [u for u in self.list() if u.active]

    def add(self, name: str) -> User:
        if not NAME_RE.fullmatch(name or ""):
            raise ValueError("имя: 1–32 символа, буквы/цифры/_/-")
        users = self.list()
        if any(u.name == name for u in users):
            raise ValueError(f"пользователь {name} уже есть")
        user = User(
            name=name,
            uuid=str(uuid.uuid4()),
            sub_token=secrets.token_urlsafe(32),
            created=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )
        self._save(users + [user])
        return user

    def revoke(self, name: str) -> bool:
        users = self.list()
        if not any(u.name == name and u.active for u in users):
            return False
        self._save([replace(u, active=False) if u.name == name else u for u in users])
        return True

    def by_token(self, token: str) -> User | None:
        for u in self.list():
            if u.active and secrets.compare_digest(u.sub_token.encode(), token.encode()):
                return u
        return None

    def _save(self, users: list[User]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
        with os.fdopen(fd, "w") as f:
            json.dump([asdict(u) for u in users], f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)
