from app.hetzner import find_server_id


def test_find_server_id_by_ip():
    data = {"servers": [
        {"id": 1, "public_net": {"ipv4": {"ip": "1.2.3.4"}}},
        {"id": 42, "public_net": {"ipv4": {"ip": "46.62.140.16"}}},
    ]}
    assert find_server_id(data, "46.62.140.16") == 42
    assert find_server_id(data, "9.9.9.9") is None
    assert find_server_id({}, "9.9.9.9") is None
