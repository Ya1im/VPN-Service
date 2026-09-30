import json

import pytest

from vpn.settings import Settings
from vpn.render import render_xray_config
from vpn.store import UserStore

ENV = {
    "TG_TOKEN": "1:x", "ADMIN_IDS": "111, 222", "PUBLIC_IP": "46.62.140.16",
    "REALITY_PRIVATE_KEY": "PRIV", "REALITY_PUBLIC_KEY": "PUB", "REALITY_SHORT_ID": "ab12",
}


def test_settings_from_env_defaults():
    s = Settings.from_env(ENV)
    assert s.admin_ids == {111, 222}
    assert s.sub_domain == "46-62-140-16.sslip.io"
    assert s.sub_url("tok") == "https://46-62-140-16.sslip.io/sub/tok"
    assert [(p.tag, p.port, p.server_name) for p in s.profiles] == [
        ("vless-tcp", 443, "46-62-140-16.sslip.io"),
        ("vless-xhttp", 2053, "46-62-140-16.sslip.io"),
    ]  # "alt" (foreign IP + vk.com SNI) is opt-in: it failed on mobile networks
    assert s.latency_ms_max == 150


def test_settings_missing_required():
    with pytest.raises(KeyError):
        Settings.from_env({k: v for k, v in ENV.items() if k != "TG_TOKEN"})


def test_render_writes_config(tmp_path):
    s = Settings.from_env({**ENV, "DATA_DIR": str(tmp_path)})
    UserStore(s.users_path).add("mom")
    path = render_xray_config(s)
    cfg = json.loads(path.read_text())
    assert path == tmp_path / "xray" / "config.json"
    assert cfg["inbounds"][0]["settings"]["clients"][0]["email"] == "mom"


def test_profiles_selectable_via_env():
    s = Settings.from_env({**ENV, "PROFILES": "tcp", "ALT_SNI": "ya.ru"})
    assert [p.tag for p in s.profiles] == ["vless-tcp"]
    s = Settings.from_env({**ENV, "PROFILES": "alt", "ALT_SNI": "ya.ru"})
    assert s.profiles[0].server_name == "ya.ru" and s.profiles[0].dest == "ya.ru:443"
