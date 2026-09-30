from vpn.metrics import human_bytes, mem_used_percent, parse_user_traffic


def test_parse_user_traffic():
    raw = {"stat": [
        {"name": "user>>>mom>>>traffic>>>downlink", "value": 2048},
        {"name": "user>>>mom>>>traffic>>>uplink", "value": "1024"},
        {"name": "inbound>>>vless-reality>>>traffic>>>downlink", "value": 5},
        {"name": "user>>>dad>>>traffic>>>uplink"},
    ]}
    assert parse_user_traffic(raw) == {"mom": (1024, 2048), "dad": (0, 0)}


def test_parse_user_traffic_empty():
    assert parse_user_traffic({}) == {}


def test_human_bytes():
    assert human_bytes(0) == "0 B"
    assert human_bytes(1536) == "1.5 KB"
    assert human_bytes(3 * 1024**3) == "3.0 GB"


def test_mem_used_percent():
    meminfo = "MemTotal:       4000 kB\nMemFree:  100 kB\nMemAvailable:   1000 kB\n"
    assert mem_used_percent(meminfo) == 75.0
