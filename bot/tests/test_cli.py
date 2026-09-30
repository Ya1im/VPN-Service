import json

from vpn.cli import main
from tests.test_settings_render import ENV


def test_cli_add_prints_sub_url_and_renders(tmp_path, capsys, monkeypatch):
    for k, v in {**ENV, "DATA_DIR": str(tmp_path)}.items():
        monkeypatch.setenv(k, v)
    assert main(["add", "tim"]) == 0
    out = capsys.readouterr().out
    assert "https://46-62-140-16.sslip.io/sub/" in out and "vless://" in out
    cfg = json.loads((tmp_path / "xray" / "config.json").read_text())
    assert cfg["inbounds"][0]["settings"]["clients"][0]["email"] == "tim"
    assert main(["revoke", "tim"]) == 0
    cfg = json.loads((tmp_path / "xray" / "config.json").read_text())
    assert cfg["inbounds"][0]["settings"]["clients"] == []
    assert main(["revoke", "tim"]) == 1
