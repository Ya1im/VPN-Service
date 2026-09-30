"""Hetzner Cloud API: hard reboot of this server (works even if the OS is hung)."""
from __future__ import annotations

import aiohttp

API = "https://api.hetzner.cloud/v1"


def find_server_id(data: dict, ip: str) -> int | None:
    for srv in data.get("servers", []):
        if (srv.get("public_net", {}).get("ipv4") or {}).get("ip") == ip:
            return srv["id"]
    return None


async def reboot(token: str, ip: str) -> str:
    headers = {"Authorization": f"Bearer {token}"}
    async with aiohttp.ClientSession(headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as s:
        async with s.get(f"{API}/servers", params={"per_page": "50"}) as r:
            r.raise_for_status()
            sid = find_server_id(await r.json(), ip)
        if sid is None:
            raise RuntimeError(f"сервер с IP {ip} не найден в проекте Hetzner")
        async with s.post(f"{API}/servers/{sid}/actions/reboot") as r:
            r.raise_for_status()
            return (await r.json())["action"]["status"]
