import json

from app.service import VpnService, is_admin
from vpn.settings import Settings
from vpn.store import UserStore
from tests.test_settings_render import ENV


class FakeDocker:
    def __init__(self, state="running"):
        self.restarts = []
        self.state = state

    async def container_state(self, name):
        return self.state

    async def restart(self, name):
        self.restarts.append(name)
        self.state = "running"


def _svc(tmp_path, docker=None):
    s = Settings.from_env({**ENV, "DATA_DIR": str(tmp_path)})
    return VpnService(s, UserStore(s.users_path), docker or FakeDocker()), s


def _clients(s):
    cfg = json.loads((s.data_dir / "xray" / "config.json").read_text())
    return [c["email"] for c in cfg["inbounds"][0]["settings"]["clients"]]


async def test_add_user_renders_and_restarts(tmp_path):
    svc, s = _svc(tmp_path)
    u = await svc.add_user("mom")
    assert u.name == "mom" and _clients(s) == ["mom"]
    assert svc.docker.restarts == ["vpn-xray"]


async def test_revoke_user_removes_client(tmp_path):
    svc, s = _svc(tmp_path)
    await svc.add_user("mom")
    assert await svc.revoke_user("mom") is True
    assert _clients(s) == []
    assert await svc.revoke_user("mom") is False


async def test_heal_restarts_stopped_xray_once(tmp_path):
    docker = FakeDocker(state="exited")
    svc, _ = _svc(tmp_path, docker)
    msg = await svc.heal_xray()
    assert docker.restarts == ["vpn-xray"] and "running" in msg
    assert await svc.heal_xray() is None  # healthy: nothing to do


def test_non_admin_ignored():
    assert is_admin(8550221175, frozenset({8550221175}))
    assert not is_admin(1, frozenset({8550221175}))
    assert not is_admin(None, frozenset({8550221175}))
