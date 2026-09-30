from vpn.xray_config import build_config


def _vless(cfg):
    return next(i for i in cfg["inbounds"] if i["protocol"] == "vless")


def test_reality_inbound_on_443_self_steal(users, reality):
    inb = _vless(build_config(users, reality))
    assert inb["port"] == 443
    rs = inb["streamSettings"]["realitySettings"]
    assert inb["streamSettings"]["security"] == "reality"
    assert rs["dest"] == "127.0.0.1:8443"
    assert rs["serverNames"] == ["46-62-140-16.sslip.io"]
    assert rs["privateKey"] == "PRIV"
    assert rs["shortIds"] == ["abcd1234"]


def test_only_active_clients_with_vision(users, reality):
    clients = _vless(build_config(users, reality))["settings"]["clients"]
    assert clients == [{"id": users[0].uuid, "email": "mom", "flow": "xtls-rprx-vision"}]


def test_revoke_removes_client(users, reality):
    cfg = build_config([users[1]], reality)
    assert _vless(cfg)["settings"]["clients"] == []


def test_stats_api_local_only(users, reality):
    cfg = build_config(users, reality)
    assert cfg["api"]["listen"] == "127.0.0.1:10085"
    assert "StatsService" in cfg["api"]["services"]
    assert cfg["policy"]["levels"]["0"]["statsUserDownlink"] is True


def test_blocks_torrent_and_private_ips(users, reality):
    rules = build_config(users, reality)["routing"]["rules"]
    assert {"protocol": ["bittorrent"], "outboundTag": "block"} in rules
    assert {"ip": ["geoip:private"], "outboundTag": "block"} in rules
