"""Entrypoint: Telegram bot + monitoring loop + subscription HTTP server."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiohttp import web

from vpn.alerts import AlertState
from vpn.render import render_xray_config
from vpn.settings import Settings
from vpn.store import UserStore

from .docker_api import DockerClient
from .handlers import build_report, build_router
from .service import VpnService
from .sub_server import make_sub_app

log = logging.getLogger("vpn-bot")
REPORT_HOUR_UTC = 7  # 10:00 Moscow


async def notify(bot: Bot, s: Settings, text: str) -> None:
    for uid in s.admin_ids:
        try:
            await bot.send_message(uid, text)
        except Exception as e:  # noqa: BLE001
            log.error("notify %s: %s", uid, e)


async def monitor(bot: Bot, svc: VpnService) -> None:
    state = AlertState(fail_threshold=2)
    while True:
        try:
            healed = await svc.heal_xray()
            if healed:
                await notify(bot, svc.s, healed)
            for msg in state.update(await svc.checks()):
                await notify(bot, svc.s, msg)
        except Exception:  # noqa: BLE001
            log.exception("monitor iteration failed")
        await asyncio.sleep(svc.s.check_interval_s)


def seconds_until(hour_utc: int, now: datetime | None = None) -> float:
    now = now or datetime.now(timezone.utc)
    nxt = now.replace(hour=hour_utc, minute=0, second=0, microsecond=0)
    if nxt <= now:
        nxt += timedelta(days=1)
    return (nxt - now).total_seconds()


async def daily_report(bot: Bot, svc: VpnService) -> None:
    while True:
        await asyncio.sleep(seconds_until(REPORT_HOUR_UTC))
        try:
            await notify(bot, svc.s, await build_report(svc, with_speed=True))
        except Exception:  # noqa: BLE001
            log.exception("daily report failed")


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    s = Settings.from_env()
    store = UserStore(s.users_path)
    render_xray_config(s)  # config always matches the store
    svc = VpnService(s, store, DockerClient())

    runner = web.AppRunner(make_sub_app(s, store))
    await runner.setup()
    await web.TCPSite(runner, "127.0.0.1", 8080).start()

    bot = Bot(s.tg_token, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()
    dp.include_router(build_router(svc))

    await notify(bot, s, "🟢 VPN-бот запущен. /help — команды")
    tasks = [asyncio.create_task(monitor(bot, svc)), asyncio.create_task(daily_report(bot, svc))]
    try:
        await dp.start_polling(bot)
    finally:
        for t in tasks:
            t.cancel()
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
