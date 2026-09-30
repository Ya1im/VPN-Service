"""Server-side admin CLI: docker compose run --rm bot python -m vpn.cli add NAME"""
from __future__ import annotations

import sys

from .links import vless_link
from .render import render_xray_config
from .settings import Settings
from .store import UserStore


def main(argv: list[str]) -> int:
    s = Settings.from_env()
    store = UserStore(s.users_path)
    cmd, *args = argv or ["list"]
    if cmd == "render":
        print(render_xray_config(s))
    elif cmd == "add" and args:
        u = store.add(args[0])
        render_xray_config(s)
        print(f"sub:   {s.sub_url(u.sub_token)}")
        print(f"vless: {vless_link(u, s.reality, s.public_ip, s.profile_title)}")
    elif cmd == "revoke" and args:
        if not store.revoke(args[0]):
            print("not found")
            return 1
        render_xray_config(s)
        print("revoked")
    elif cmd == "list":
        for u in store.list():
            print(f"{'+' if u.active else '-'} {u.name}  {s.sub_url(u.sub_token)}")
    else:
        print("usage: render | add NAME | revoke NAME | list")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
