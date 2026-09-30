"""Client links and Happ subscription payloads."""
from __future__ import annotations

import base64
from urllib.parse import quote, urlencode

from .models import User
from .xray_config import Profile, Reality


def vless_link(user: User, reality: Reality, profile: Profile, host: str) -> str:
    params = {"encryption": "none"}
    if profile.flow:
        params["flow"] = profile.flow
    params.update({
        "security": "reality",
        "sni": profile.server_name,
        "fp": "chrome",
        "pbk": reality.public_key,
        "sid": reality.short_id,
        "type": profile.network,
    })
    if profile.network == "xhttp":
        params.update({"path": profile.path, "mode": "auto"})
    return f"vless://{user.uuid}@{host}:{profile.port}?{urlencode(params)}#{quote(profile.label)}"


def subscription_body(user: User, reality: Reality, profiles: list[Profile], host: str) -> str:
    links = [vless_link(user, reality, p, host) for p in profiles]
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
