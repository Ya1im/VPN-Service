from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class User:
    name: str
    uuid: str
    sub_token: str
    created: str
    active: bool = True
