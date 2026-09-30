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
    assert s.reality.server_name == "46-62-140-16.sslip.io"
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
