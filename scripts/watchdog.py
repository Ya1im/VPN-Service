#!/usr/bin/env python3
"""External watchdog (GitHub Actions). Stdlib only.

Checks the VPN server from outside, keeps state in a JSON file (persisted via actions/cache)
and notifies Telegram only on state changes. Optional hard reboot via Hetzner API when the
whole server (443 and 22) has been unreachable for REBOOT_AFTER consecutive runs.
"""
from __future__ import annotations

import json
import os
import socket
import ssl
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

REBOOT_AFTER = 3


def tcp_ms(host: str, port: int, timeout: float = 5.0) -> float | None:
    t0 = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return round((time.perf_counter() - t0) * 1000, 1)
    except OSError:
        return None


def https_ok(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=10, context=ssl.create_default_context()) as r:
            return r.status == 200
    except Exception:  # noqa: BLE001
        return False


def probe(host: str, domain: str) -> dict:
    return {"vpn_ms": tcp_ms(host, 443), "ssh_ms": tcp_ms(host, 22), "https": https_ok(f"https://{domain}/")}


def is_up(p: dict) -> bool:
    return p["vpn_ms"] is not None and p["https"]


def decide(prev: dict, up: bool, server_dead: bool, can_reboot: bool) -> tuple[dict, list[str], bool]:
    """Pure state machine -> (new_state, messages, do_reboot)."""
    fails = 0 if up else prev.get("fails", 0) + 1
    msgs: list[str] = []
    reboot = False
    was_down = prev.get("down", False)
    if not up and not was_down:
        msgs.append("🚨 [watchdog] VPN недоступен снаружи")
    if up and was_down:
        msgs.append("✅ [watchdog] VPN снова доступен снаружи")
    rebooted = prev.get("rebooted", False) and not up
    if not up and server_dead and can_reboot and fails >= REBOOT_AFTER and not rebooted:
        reboot, rebooted = True, True
        msgs.append(f"♻️ [watchdog] сервер недоступен {fails} проверки подряд — hard reboot через Hetzner API")
    return {"down": not up, "fails": fails, "rebooted": rebooted}, msgs, reboot


def tg(token: str, chat: str, text: str) -> None:
    data = urllib.parse.urlencode({"chat_id": chat, "text": text}).encode()
    urllib.request.urlopen(f"https://api.telegram.org/bot{token}/sendMessage", data=data, timeout=15)


def hetzner_reboot(token: str, ip: str) -> None:
    h = {"Authorization": f"Bearer {token}"}
    req = urllib.request.Request("https://api.hetzner.cloud/v1/servers?per_page=50", headers=h)
    servers = json.load(urllib.request.urlopen(req, timeout=15))["servers"]
    sid = next(s["id"] for s in servers if s["public_net"]["ipv4"]["ip"] == ip)
    urllib.request.urlopen(urllib.request.Request(
        f"https://api.hetzner.cloud/v1/servers/{sid}/actions/reboot", method="POST", headers=h), timeout=15)


def main() -> int:
    host = os.environ["VPN_HOST"]
    domain = host.replace(".", "-") + ".sslip.io"
    state_file = Path(os.environ.get("STATE_FILE", ".watchdog/state.json"))
    prev = json.loads(state_file.read_text()) if state_file.exists() else {}

    p = probe(host, domain)
    if not is_up(p):  # confirm to avoid false alarms from runner network blips
        time.sleep(30)
        p = probe(host, domain)
    up = is_up(p)
    print(json.dumps(p))

    hc = os.environ.get("HCLOUD_TOKEN", "")
    state, msgs, reboot = decide(prev, up, server_dead=p["ssh_ms"] is None and p["vpn_ms"] is None, can_reboot=bool(hc))
    if reboot:
        try:
            hetzner_reboot(hc, host)
        except Exception as e:  # noqa: BLE001
            msgs.append(f"ребут не удался: {e}")
    for m in msgs:
        tg(os.environ["TG_TOKEN"], os.environ["TG_CHAT_ID"], f"{m}\n{json.dumps(p)}")
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(state))
    return 0


if __name__ == "__main__":
    sys.exit(main())
