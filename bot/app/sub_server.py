"""HTTP endpoint for Happ subscriptions (behind Caddy): GET /sub/{token}."""
from __future__ import annotations

from aiohttp import web

from vpn.links import subscription_body, subscription_headers
from vpn.settings import Settings
from vpn.store import UserStore


def make_sub_app(s: Settings, store: UserStore) -> web.Application:
    async def sub(request: web.Request) -> web.Response:
        user = store.by_token(request.match_info["token"])
        if user is None:
            raise web.HTTPNotFound(text="not found")
        body = subscription_body(user, s.reality, s.public_ip, s.profile_title)
        headers = subscription_headers(s.profile_title, update_hours=12)
        return web.Response(text=body, headers=headers, content_type="text/plain")

    app = web.Application()
    app.router.add_get("/sub/{token}", sub)
    return app
