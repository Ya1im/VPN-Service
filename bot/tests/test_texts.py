from app.texts import format_speed, format_users
from vpn.models import User


def test_format_users_with_traffic():
    users = [User("mom", "u1", "t1", "2026-10-01"), User("old", "u2", "t2", "2026-10-01", active=False)]
    text = format_users(users, {"mom": (1024, 3 * 1024**3)})
    assert "🟢 mom" in text and "↓3.0 GB" in text and "↑1.0 KB" in text
    assert "⚪️ old" in text


def test_format_users_empty():
    assert "нет" in format_users([], {}).lower()


def test_format_speed():
    t = format_speed({"down_mbps": 812.3, "up_mbps": 640.0, "ping_ms": 2.1})
    assert "812.3" in t and "640.0" in t and "2.1" in t
