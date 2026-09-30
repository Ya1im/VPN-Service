from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .xray_config import Profile, Reality


@dataclass(frozen=True)
class Settings:
    tg_token: str
    admin_ids: frozenset[int]
    public_ip: str
    reality: Reality
    profiles: tuple[Profile, ...]
    data_dir: Path
    profile_title: str = "🇫🇮 TimVPN"
    latency_ms_max: float = 150
    check_interval_s: int = 60
    hcloud_token: str = ""
    xray_container: str = "vpn-xray"

    @property
    def sub_domain(self) -> str:
        return self.public_ip.replace(".", "-") + ".sslip.io"

    @property
    def users_path(self) -> Path:
        return self.data_dir / "users.json"

    def sub_url(self, token: str) -> str:
        return f"https://{self.sub_domain}/sub/{token}"

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Settings":
        e = os.environ if env is None else env
        ip = e["PUBLIC_IP"]
        domain = ip.replace(".", "-") + ".sslip.io"
        return cls(
            tg_token=e["TG_TOKEN"],
            admin_ids=frozenset(int(x) for x in e.get("ADMIN_IDS", "").replace(" ", "").split(",") if x),
            public_ip=ip,
            reality=Reality(
                private_key=e["REALITY_PRIVATE_KEY"],
                public_key=e["REALITY_PUBLIC_KEY"],
                short_id=e["REALITY_SHORT_ID"],
            ),
            profiles=_profiles(e, domain),
            data_dir=Path(e.get("DATA_DIR", "/data")),
            profile_title=e.get("PROFILE_TITLE", "🇫🇮 TimVPN"),
            latency_ms_max=float(e.get("LATENCY_MS_MAX", 150)),
            check_interval_s=int(e.get("CHECK_INTERVAL_S", 60)),
            hcloud_token=e.get("HCLOUD_TOKEN", ""),
        )


def _profiles(e: Mapping[str, str], domain: str) -> tuple[Profile, ...]:
    alt = e.get("ALT_SNI", "vk.com")
    local = "127.0.0.1:8443"  # Caddy with a real cert for `domain` (self-steal)
    available = {
        "tcp": Profile("vless-tcp", "🇫🇮 Финляндия", 443, domain, local),
        "xhttp": Profile("vless-xhttp", "🇫🇮 Финляндия XHTTP", 2053, domain, local,
                         network="xhttp", path=e.get("XHTTP_PATH", "/api/v2/stream")),
        "alt": Profile("vless-alt", "🇫🇮 Финляндия ALT", 2083, alt, f"{alt}:443"),
    }
    names = [n.strip() for n in e.get("PROFILES", "tcp,xhttp,alt").split(",") if n.strip()]
    return tuple(available[n] for n in names)
