"""Client links and Happ subscription payloads."""
from __future__ import annotations

import base64
from urllib.parse import quote, urlencode

from .models import User
from .xray_config import FLOW, Reality


def vless_link(user: User, reality: Reality, host: str, label: str, port: int = 443) -> str:
    query = urlencode({
        "encryption": "none",
        "flow": FLOW,
        "security": "reality",
        "sni": reality.server_name,
        "fp": "chrome",
        "pbk": reality.public_key,
        "sid": reality.short_id,
        "type": "tcp",
    })
    return f"vless://{user.uuid}@{host}:{port}?{query}#{quote(label)}"


def subscription_body(user: User, reality: Reality, host: str, label: str) -> str:
    links = [vless_link(user, reality, host, label)]
    return base64.b64encode("\n".join(links).encode()).decode()


def _b64(text: str) -> str:
    return "base64:" + base64.b64encode(text.encode()).decode()


def subscription_headers(title: str, update_hours: int = 12, support_url: str = "") -> dict[str, str]:
    headers = {
        "profile-title": _b64(title),
        "profile-update-interval": str(update_hours),
        "subscription-userinfo": "upload=0; download=0; total=0; expire=0",
        "content-disposition": 'attachment; filename="vpn"',
    }
    if support_url:
        headers["support-url"] = support_url
    return headers
