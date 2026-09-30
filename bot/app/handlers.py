"""Telegram UI. Only ADMIN_IDS can use the bot; everyone else is silently ignored."""
from __future__ import annotations

import io
import logging
from html import escape

import qrcode
from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import (BufferedInputFile, CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, KeyboardButton, Message, ReplyKeyboardMarkup)

from vpn import metrics
from vpn.alerts import format_status

from . import hetzner
from .service import VpnService
from .texts import format_speed, format_users

log = logging.getLogger(__name__)

BTN_STATUS, BTN_SPEED, BTN_KEYS = "📊 Статус", "⚡ Скорость", "👥 Ключи"
BTN_RESTART, BTN_REBOOT = "🔄 Рестарт VPN", "♻️ Ребут сервера"

MENU = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
    [KeyboardButton(text=BTN_STATUS), KeyboardButton(text=BTN_SPEED)],
    [KeyboardButton(text=BTN_KEYS), KeyboardButton(text=BTN_RESTART)],
    [KeyboardButton(text=BTN_REBOOT)],
])

HELP = (
    "<b>VPN-бот</b>\n"
    "/add <i>имя</i> — выдать ключ (ссылка для Happ + QR)\n"
    "/link <i>имя</i> — прислать ссылку ещё раз\n"
    "/revoke <i>имя</i> — отозвать ключ\n"
    "/report — полный отчёт\n\n"
    "В Happ: «+» → «Вставить из буфера» → ссылка https://…/sub/…"
)


def qr_png(text: str) -> bytes:
    buf = io.BytesIO()
    qrcode.make(text, box_size=8, border=2).save(buf, format="PNG")
    return buf.getvalue()


def build_router(svc: VpnService) -> Router:
    s = svc.s
    r = Router(name="admin")
    r.message.filter(F.from_user.id.in_(s.admin_ids))
    r.callback_query.filter(F.from_user.id.in_(s.admin_ids))

    async def send_key(m: Message, name: str) -> None:
        user = next((u for u in svc.store.active() if u.name == name), None)
        if user is None:
            await m.answer(f"Активного ключа «{escape(name)}» нет.")
            return
        url = s.sub_url(user.sub_token)
        await m.answer_photo(
            BufferedInputFile(qr_png(url), "happ.png"),
            caption=(f"🔑 <b>{escape(name)}</b>\n\nСсылка для Happ (подписка):\n<code>{url}</code>\n\n"
                     "Happ → «+» → «Вставить из буфера обмена»."),
        )

    @r.message(CommandStart())
    @r.message(Command("help"))
    async def start(m: Message) -> None:
        await m.answer(HELP, reply_markup=MENU)

    @r.message(F.text == BTN_STATUS)
    async def status(m: Message) -> None:
        checks = await svc.checks()
        await m.answer(f"<b>Статус</b>\n{format_status(checks)}\nнагрузка: {metrics.load_str()}")

    @r.message(F.text == BTN_SPEED)
    async def speed(m: Message) -> None:
        await m.answer("⏳ Меряю скорость (~15 с)…")
        try:
            await m.answer(format_speed(await metrics.speedtest()))
        except Exception as e:  # noqa: BLE001
            await m.answer(f"Не удалось: {type(e).__name__}")

    @r.message(F.text == BTN_KEYS)
    async def keys(m: Message) -> None:
        try:
            traffic = await svc.traffic()
        except Exception as e:  # noqa: BLE001
            log.warning("traffic: %s", e)
            traffic = {}
        await m.answer("<b>Ключи</b> (трафик с последнего рестарта Xray)\n" + format_users(svc.store.list(), traffic))

    @r.message(F.text == BTN_RESTART)
    async def restart(m: Message) -> None:
        await m.answer("🔄 Перезапускаю Xray…")
        await m.answer(f"Xray: {await svc.restart_xray()}")

    @r.message(F.text == BTN_REBOOT)
    async def reboot_ask(m: Message) -> None:
        if not s.hcloud_token:
            await m.answer("Ребут сервера не настроен: нет HCLOUD_TOKEN в .env.")
            return
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="Да, ребут", callback_data="reboot:yes"),
            InlineKeyboardButton(text="Отмена", callback_data="reboot:no"),
        ]])
        await m.answer("⚠️ Перезагрузить весь сервер? Упадут VPN и funnel-bot на ~1 мин.", reply_markup=kb)

    @r.callback_query(F.data.startswith("reboot:"))
    async def reboot_do(c: CallbackQuery) -> None:
        await c.answer()
        if c.data != "reboot:yes":
            await c.message.edit_text("Отменено.")
            return
        try:
            st = await hetzner.reboot(s.hcloud_token, s.public_ip)
            await c.message.edit_text(f"♻️ Ребут отправлен ({st}). Бот вернётся через ~1 мин.")
        except Exception as e:  # noqa: BLE001
            await c.message.edit_text(f"Ребут не удался: {escape(str(e))}")

    @r.message(Command("add"))
    async def add(m: Message, command: CommandObject) -> None:
        name = (command.args or "").strip()
        try:
            await svc.add_user(name)
        except ValueError as e:
            await m.answer(f"❌ {escape(str(e))}\nПример: /add mama")
            return
        await send_key(m, name)

    @r.message(Command("link"))
    async def link(m: Message, command: CommandObject) -> None:
        await send_key(m, (command.args or "").strip())

    @r.message(Command("revoke"))
    async def revoke(m: Message, command: CommandObject) -> None:
        name = (command.args or "").strip()
        ok = await svc.revoke_user(name)
        await m.answer(f"➖ Ключ «{escape(name)}» отозван." if ok else "Такого активного ключа нет.")

    @r.message(Command("report"))
    async def report(m: Message) -> None:
        await m.answer(await build_report(svc))

    return r


async def build_report(svc: VpnService, with_speed: bool = False) -> str:
    checks = await svc.checks()
    try:
        traffic = await svc.traffic()
    except Exception:  # noqa: BLE001
        traffic = {}
    parts = ["<b>📋 Отчёт VPN</b>", format_status(checks), f"нагрузка: {metrics.load_str()}", "",
             format_users(svc.store.list(), traffic)]
    if with_speed:
        try:
            parts += ["", format_speed(await metrics.speedtest())]
        except Exception as e:  # noqa: BLE001
            parts += ["", f"speedtest: {type(e).__name__}"]
    return "\n".join(parts)
