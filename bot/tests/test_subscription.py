import base64

from aiohttp.test_utils import TestClient, TestServer

from app.sub_server import make_sub_app
from vpn.settings import Settings
from vpn.store import UserStore
from tests.test_settings_render import ENV


async def _client(tmp_path):
    s = Settings.from_env({**ENV, "DATA_DIR": str(tmp_path)})
    store = UserStore(s.users_path)
    client = TestClient(TestServer(make_sub_app(s, store)))
    await client.start_server()
    return s, store, client


async def test_subscription_returns_links_and_happ_headers(tmp_path):
    s, store, client = await _client(tmp_path)
    u = store.add("mom")
    try:
        r = await client.get(f"/sub/{u.sub_token}")
        assert r.status == 200
        body = base64.b64decode(await r.text()).decode()
        assert body.startswith(f"vless://{u.uuid}@46.62.140.16:443")
        assert r.headers["profile-update-interval"] == "12"
        assert r.headers["profile-title"].startswith("base64:")
    finally:
        await client.close()


async def test_subscription_unknown_token_404(tmp_path):
    s, store, client = await _client(tmp_path)
    u = store.add("mom")
    store.revoke("mom")
    try:
        for tok in ["nope", u.sub_token]:
            r = await client.get(f"/sub/{tok}")
            assert r.status == 404
            assert "mom" not in await r.text()
    finally:
        await client.close()
