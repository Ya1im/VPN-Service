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
    server_name: str
    dest: str = "127.0.0.1:8443"


def build_config(users: list[User], reality: Reality) -> dict:
    clients = [{"id": u.uuid, "email": u.name, "flow": FLOW} for u in users if u.active]
    return {
        "log": {"loglevel": "warning"},
        "api": {"tag": "api", "listen": "127.0.0.1:10085", "services": ["StatsService", "HandlerService"]},
        "stats": {},
        "policy": {
            "levels": {"0": {"statsUserUplink": True, "statsUserDownlink": True}},
            "system": {"statsInboundUplink": True, "statsInboundDownlink": True},
        },
        "inbounds": [
            {
                "tag": "vless-reality",
                "listen": "0.0.0.0",
                "port": 443,
                "protocol": "vless",
                "settings": {"clients": clients, "decryption": "none"},
                "streamSettings": {
                    "network": "tcp",
                    "security": "reality",
                    "realitySettings": {
                        "show": False,
                        "dest": reality.dest,
                        "xver": 0,
                        "serverNames": [reality.server_name],
                        "privateKey": reality.private_key,
                        "shortIds": [reality.short_id],
                    },
                },
                "sniffing": {"enabled": True, "destOverride": ["http", "tls", "quic"], "routeOnly": True},
            }
        ],
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
