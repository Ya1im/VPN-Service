"""Application service: orchestrates store, config rendering and docker."""
from __future__ import annotations

import asyncio
import json
import logging

from vpn import metrics
from vpn.alerts import Check
from vpn.models import User
from vpn.render import render_xray_config
from vpn.settings import Settings
from vpn.store import UserStore

log = logging.getLogger(__name__)


def is_admin(user_id: int | None, admin_ids: frozenset[int]) -> bool:
    return user_id is not None and user_id in admin_ids


class VpnService:
    def __init__(self, s: Settings, store: UserStore, docker) -> None:
        self.s, self.store, self.docker = s, store, docker
        self._lock = asyncio.Lock()

    async def _apply(self) -> None:
        render_xray_config(self.s)
        await self.docker.restart(self.s.xray_container)

    async def add_user(self, name: str) -> User:
        async with self._lock:
            u = self.store.add(name)
            await self._apply()
            return u

    async def revoke_user(self, name: str) -> bool:
        async with self._lock:
            if not self.store.revoke(name):
                return False
            await self._apply()
            return True

    async def restart_xray(self) -> str:
        async with self._lock:
            await self.docker.restart(self.s.xray_container)
            await asyncio.sleep(2)
            return await self.docker.container_state(self.s.xray_container)

    async def heal_xray(self) -> str | None:
        """If Xray is not running, restart it once. Returns a report or None if healthy."""
        state = await self.docker.container_state(self.s.xray_container)
        if state == "running":
            return None
        log.warning("xray state=%s, restarting", state)
        try:
            new = await self.restart_xray()
        except Exception as e:  # noqa: BLE001
            return f"🛠 Авто-рестарт Xray не удался: {e}"
        return f"🛠 Xray был {state}, авто-рестарт → {new}"

    async def checks(self) -> list[Check]:
        state = await self.docker.container_state(self.s.xray_container)
        ports = []
        for p in self.s.profiles:
            ms = await metrics.tcp_ms("127.0.0.1", p.port)
            ports.append(Check(f"порт {p.port}", ms is not None, f"{ms} мс" if ms is not None else "не отвечает"))
        return [
            Check("xray", state == "running", state),
            *ports,
            await metrics.https_check(f"https://{self.s.sub_domain}/"),
            await metrics.latency_check([("1.1.1.1", 443), ("8.8.8.8", 443), ("ya.ru", 443)], self.s.latency_ms_max),
            metrics.disk_check("/"),
            metrics.mem_check(),
        ]

    async def traffic(self) -> dict[str, tuple[int, int]]:
        proc = await asyncio.create_subprocess_exec(
            "xray", "api", "statsquery", "--server=127.0.0.1:10085",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        out, err = await asyncio.wait_for(proc.communicate(), 10)
        if proc.returncode != 0:
            raise RuntimeError(err.decode()[:200])
        return metrics.parse_user_traffic(json.loads(out or b"{}"))
