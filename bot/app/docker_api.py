"""Minimal Docker Engine API client over the unix socket."""
from __future__ import annotations

import aiohttp


class DockerClient:
    def __init__(self, socket: str = "/var/run/docker.sock") -> None:
        self.socket = socket

    def _session(self) -> aiohttp.ClientSession:
        return aiohttp.ClientSession(
            connector=aiohttp.UnixConnector(path=self.socket),
            timeout=aiohttp.ClientTimeout(total=30),
        )

    async def container_state(self, name: str) -> str:
        async with self._session() as s, s.get(f"http://docker/containers/{name}/json") as r:
            if r.status == 404:
                return "missing"
            data = await r.json()
            return data["State"]["Status"]  # running | exited | restarting | ...

    async def restart(self, name: str) -> None:
        async with self._session() as s, s.post(f"http://docker/containers/{name}/restart?t=5") as r:
            if r.status >= 300:
                raise RuntimeError(f"docker restart {name}: HTTP {r.status} {await r.text()}")
