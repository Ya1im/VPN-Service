"""Render Xray config from the user store. CLI: python -m vpn.render"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from .settings import Settings
from .store import UserStore
from .xray_config import build_config


def render_xray_config(s: Settings) -> Path:
    cfg = build_config(UserStore(s.users_path).list(), s.reality)
    out = s.data_dir / "xray" / "config.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=out.parent, suffix=".tmp")
    with os.fdopen(fd, "w") as f:
        json.dump(cfg, f, indent=2)
    os.chmod(tmp, 0o644)
    os.replace(tmp, out)
    return out


if __name__ == "__main__":
    print(render_xray_config(Settings.from_env()))
