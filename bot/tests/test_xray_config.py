from vpn.xray_config import build_config


def _inb(cfg, tag):
    return next(i for i in cfg["inbounds"] if i["tag"] == tag)


def test_one_inbound_per_profile(users, reality, profiles):
    cfg = build_config(users, reality, profiles)
    assert [(i["tag"], i["port"]) for i in cfg["inbounds"]] == [
        ("vless-tcp", 443), ("vless-xhttp", 2053), ("vless-alt", 2083)]


def test_reality_self_steal_on_443(users, reality, profiles):
    inb = _inb(build_config(users, reality, profiles), "vless-tcp")
    rs = inb["streamSettings"]["realitySettings"]
    assert inb["streamSettings"]["security"] == "reality" and inb["streamSettings"]["network"] == "tcp"
    assert rs["dest"] == "127.0.0.1:8443"
    assert rs["serverNames"] == ["46-62-140-16.sslip.io"]
    assert rs["privateKey"] == "PRIV" and rs["shortIds"] == ["abcd1234"]


def test_alt_profile_steals_other_site(users, reality, profiles):
    rs = _inb(build_config(users, reality, profiles), "vless-alt")["streamSettings"]["realitySettings"]
    assert rs["dest"] == "vk.com:443" and rs["serverNames"] == ["vk.com"]


def test_xhttp_profile_has_path_and_no_flow(users, reality, profiles):
    inb = _inb(build_config(users, reality, profiles), "vless-xhttp")
    assert inb["streamSettings"]["network"] == "xhttp"
    assert inb["streamSettings"]["xhttpSettings"]["path"] == "/xh"
    assert inb["settings"]["clients"] == [{"id": users[0].uuid, "email": "mom"}]


def test_only_active_clients_with_vision_on_tcp(users, reality, profiles):
    clients = _inb(build_config(users, reality, profiles), "vless-tcp")["settings"]["clients"]
    assert clients == [{"id": users[0].uuid, "email": "mom", "flow": "xtls-rprx-vision"}]


def test_revoke_removes_client(users, reality, profiles):
    cfg = build_config([users[1]], reality, profiles)
    assert all(i["settings"]["clients"] == [] for i in cfg["inbounds"])


def test_stats_api_local_only(users, reality, profiles):
    cfg = build_config(users, reality, profiles)
    assert cfg["api"]["listen"] == "127.0.0.1:10085"
    assert "StatsService" in cfg["api"]["services"]
    assert cfg["policy"]["levels"]["0"]["statsUserDownlink"] is True


def test_blocks_torrent_and_private_ips(users, reality, profiles):
    rules = build_config(users, reality, profiles)["routing"]["rules"]
    assert {"protocol": ["bittorrent"], "outboundTag": "block"} in rules
    assert {"ip": ["geoip:private"], "outboundTag": "block"} in rules
