"""Pure builder for the Xray server config (VLESS + Reality self-steal)."""
from __future__ import annotations

from dataclasses import dataclass

from .models import User

FLOW = "xtls-rprx-vision"


@dataclass(frozen=True)
class Reality:
    private_key: str
    public_key: str
    short_id: str


@dataclass(frozen=True)
class Profile:
    """One public entry point (inbound) = one line in the Happ subscription."""
    tag: str
    label: str
    port: int
    server_name: str
    dest: str
    network: str = "tcp"  # tcp | xhttp
    path: str = ""        # xhttp only

    @property
    def flow(self) -> str:
        return FLOW if self.network == "tcp" else ""


def _inbound(p: Profile, users: list[User], reality: Reality) -> dict:
    clients = []
    for u in users:
        if u.active:
            c = {"id": u.uuid, "email": u.name}
            if p.flow:
                c["flow"] = p.flow
            clients.append(c)
    stream = {
        "network": p.network,
        "security": "reality",
        "realitySettings": {
            "show": False,
            "dest": p.dest,
            "xver": 0,
            "serverNames": [p.server_name],
            "privateKey": reality.private_key,
            "shortIds": [reality.short_id],
        },
    }
    if p.network == "xhttp":
        stream["xhttpSettings"] = {"path": p.path, "mode": "auto"}
    return {
        "tag": p.tag,
        "listen": "0.0.0.0",
        "port": p.port,
        "protocol": "vless",
        "settings": {"clients": clients, "decryption": "none"},
        "streamSettings": stream,
        "sniffing": {"enabled": True, "destOverride": ["http", "tls", "quic"], "routeOnly": True},
    }


def build_config(users: list[User], reality: Reality, profiles: list[Profile]) -> dict:
    return {
        "log": {"loglevel": "warning"},
        "api": {"tag": "api", "listen": "127.0.0.1:10085", "services": ["StatsService", "HandlerService"]},
        "stats": {},
        "policy": {
            "levels": {"0": {"statsUserUplink": True, "statsUserDownlink": True}},
            "system": {"statsInboundUplink": True, "statsInboundDownlink": True},
        },
        "inbounds": [_inbound(p, users, reality) for p in profiles],
        "outbounds": [
            {"protocol": "freedom", "tag": "direct"},
            {"protocol": "blackhole", "tag": "block"},
        ],
        "routing": {
            "domainStrategy": "IPIfNonMatch",
            "rules": [
                {"protocol": ["bittorrent"], "outboundTag": "block"},
                {"ip": ["geoip:private"], "outboundTag": "block"},
            ],
        },
    }
