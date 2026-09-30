import base64
from urllib.parse import parse_qs, urlsplit, unquote

from vpn.links import subscription_body, subscription_headers, vless_link


def test_vless_link_format(users, reality):
    link = vless_link(users[0], reality, host="46.62.140.16", label="🇫🇮 TimVPN")
    u = urlsplit(link)
    assert u.scheme == "vless"
    assert u.username == users[0].uuid and u.hostname == "46.62.140.16" and u.port == 443
    q = {k: v[0] for k, v in parse_qs(u.query).items()}
    assert q == {
        "encryption": "none", "flow": "xtls-rprx-vision", "security": "reality",
        "sni": "46-62-140-16.sslip.io", "fp": "chrome", "pbk": "PUBKEY",
        "sid": "abcd1234", "type": "tcp",
    }
    assert unquote(u.fragment) == "🇫🇮 TimVPN"


def test_subscription_body_is_base64_of_links(users, reality):
    body = subscription_body(users[0], reality, host="46.62.140.16", label="X")
    assert base64.b64decode(body).decode().startswith("vless://")


def test_subscription_headers_for_happ():
    h = subscription_headers("🇫🇮 TimVPN", update_hours=12)
    assert h["profile-title"] == "base64:" + base64.b64encode("🇫🇮 TimVPN".encode()).decode()
    assert h["profile-update-interval"] == "12"
    assert "subscription-userinfo" in h
    # header values must be latin-1 encodable for HTTP
    for v in h.values():
        v.encode("latin-1")
