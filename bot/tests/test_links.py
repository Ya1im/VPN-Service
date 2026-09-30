import base64
from urllib.parse import parse_qs, unquote, urlsplit

from vpn.links import subscription_body, subscription_headers, vless_link


def _q(link):
    return {k: v[0] for k, v in parse_qs(urlsplit(link).query).items()}


def test_vless_tcp_link_format(users, reality, profiles):
    link = vless_link(users[0], reality, profiles[0], host="46.62.140.16")
    u = urlsplit(link)
    assert u.scheme == "vless" and u.username == users[0].uuid
    assert u.hostname == "46.62.140.16" and u.port == 443
    assert _q(link) == {
        "encryption": "none", "flow": "xtls-rprx-vision", "security": "reality",
        "sni": "46-62-140-16.sslip.io", "fp": "chrome", "pbk": "PUBKEY",
        "sid": "abcd1234", "type": "tcp",
    }
    assert unquote(u.fragment) == "🇫🇮 TCP"


def test_vless_xhttp_link(users, reality, profiles):
    link = vless_link(users[0], reality, profiles[1], host="46.62.140.16")
    q = _q(link)
    assert urlsplit(link).port == 2053
    assert q["type"] == "xhttp" and q["path"] == "/xh" and q["mode"] == "auto"
    assert "flow" not in q


def test_subscription_body_has_all_profiles(users, reality, profiles):
    body = base64.b64decode(subscription_body(users[0], reality, profiles, host="46.62.140.16")).decode()
    lines = body.splitlines()
    assert len(lines) == 3 and all(l.startswith("vless://") for l in lines)
    assert "sni=vk.com" in lines[2]


def test_subscription_headers_for_happ():
    h = subscription_headers("🇫🇮 TimVPN", update_hours=12)
    assert h["profile-title"] == "base64:" + base64.b64encode("🇫🇮 TimVPN".encode()).decode()
    assert h["profile-update-interval"] == "12"
    assert "subscription-userinfo" in h
    for v in h.values():
        v.encode("latin-1")
