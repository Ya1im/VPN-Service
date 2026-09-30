from __future__ import annotations

from html import escape

from vpn.metrics import human_bytes
from vpn.models import User


def format_users(users: list[User], traffic: dict[str, tuple[int, int]]) -> str:
    if not users:
        return "Ключей пока нет. Добавить: /add имя"
    lines = []
    for u in users:
        up, down = traffic.get(u.name, (0, 0))
        mark = "🟢" if u.active else "⚪️"
        lines.append(f"{mark} {escape(u.name)} — ↓{human_bytes(down)} ↑{human_bytes(up)}")
    return "\n".join(lines)


def format_speed(r: dict) -> str:
    return (f"⚡ Скорость сервера (Cloudflare)\n"
            f"↓ {r['down_mbps']} Мбит/с\n↑ {r['up_mbps']} Мбит/с\n"
            f"пинг {r['ping_ms']} мс")
