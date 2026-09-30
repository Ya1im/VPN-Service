"""System / network metrics. Pure helpers are unit-tested; I/O functions are thin."""
from __future__ import annotations

import asyncio
import os
import shutil
import statistics
import time
from pathlib import Path

import aiohttp

from .alerts import Check


# ---------- pure helpers ----------
def parse_user_traffic(raw: dict) -> dict[str, tuple[int, int]]:
    """xray `statsquery` JSON -> {user: (uplink, downlink)}."""
    out: dict[str, list[int]] = {}
    for s in raw.get("stat", []) or []:
        parts = s.get("name", "").split(">>>")
        if len(parts) != 4 or parts[0] != "user":
            continue
        cur = out.setdefault(parts[1], [0, 0])
        cur[0 if parts[3] == "uplink" else 1] += int(s.get("value", 0) or 0)
    return {k: (v[0], v[1]) for k, v in out.items()}


def human_bytes(n: float) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while n >= 1024 and i < len(units) - 1:
        n /= 1024
        i += 1
    return f"{int(n)} B" if i == 0 else f"{n:.1f} {units[i]}"


def mem_used_percent(meminfo: str) -> float:
    vals = {}
    for line in meminfo.splitlines():
        k, _, rest = line.partition(":")
        if rest:
            vals[k.strip()] = int(rest.split()[0])
    return round(100 * (1 - vals["MemAvailable"] / vals["MemTotal"]), 1)


# ---------- I/O ----------
async def tcp_ms(host: str, port: int, timeout: float = 3.0) -> float | None:
    t0 = time.perf_counter()
    try:
        _, w = await asyncio.wait_for(asyncio.open_connection(host, port), timeout)
        w.close()
        return round((time.perf_counter() - t0) * 1000, 1)
    except (OSError, asyncio.TimeoutError):
        return None


async def latency_check(targets: list[tuple[str, int]], max_ms: float) -> Check:
    results = await asyncio.gather(*(tcp_ms(h, p) for h, p in targets))
    ok_vals = [r for r in results if r is not None]
    if not ok_vals:
        return Check("задержка", False, "все цели недоступны")
    med = statistics.median(ok_vals)
    lost = len(results) - len(ok_vals)
    detail = f"{med:.0f} мс" + (f", потеряно {lost}/{len(results)}" if lost else "")
    return Check("задержка", med <= max_ms and lost == 0, detail)


def disk_check(path: str = "/", max_pct: float = 90) -> Check:
    du = shutil.disk_usage(path)
    pct = round(100 * du.used / du.total, 1)
    return Check("диск", pct < max_pct, f"{pct}% из {human_bytes(du.total)}")


def mem_check(max_pct: float = 90) -> Check:
    pct = mem_used_percent(Path("/proc/meminfo").read_text())
    return Check("память", pct < max_pct, f"{pct}%")


def load_str() -> str:
    one, five, _ = os.getloadavg()
    return f"{one:.2f} / {five:.2f} (ядер: {os.cpu_count()})"


async def https_check(url: str, timeout: float = 8.0) -> Check:
    t0 = time.perf_counter()
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as s:
            async with s.get(url) as r:
                ms = (time.perf_counter() - t0) * 1000
                return Check("https/подписка", r.status == 200, f"HTTP {r.status}, {ms:.0f} мс")
    except Exception as e:  # noqa: BLE001 — any failure is a failed check
        return Check("https/подписка", False, type(e).__name__)


async def speedtest(down_bytes: int = 25_000_000, up_bytes: int = 5_000_000) -> dict:
    base = "https://speed.cloudflare.com"
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as s:
        ping = await tcp_ms("speed.cloudflare.com", 443)
        t0 = time.perf_counter()
        async with s.get(f"{base}/__down", params={"bytes": str(down_bytes)}) as r:
            size = 0
            async for chunk in r.content.iter_chunked(1 << 16):
                size += len(chunk)
        down = size * 8 / (time.perf_counter() - t0) / 1e6
        t0 = time.perf_counter()
        async with s.post(f"{base}/__up", data=os.urandom(up_bytes)) as r:
            await r.read()
        up = up_bytes * 8 / (time.perf_counter() - t0) / 1e6
    return {"down_mbps": round(down, 1), "up_mbps": round(up, 1), "ping_ms": ping}
