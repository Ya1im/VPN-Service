# VPN-сервис — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: test-driven-development. Steps use `- [ ]`.

**Goal:** VLESS+Reality VPN на Hetzner с Happ-подпиской, Telegram-ботом (алерты/метрики/рестарт/ключи) и внешним сторожем.

**Architecture:** docker compose project `vpn-service` в `/opt/vpn-service`, `network_mode: host`.
Xray слушает :443 (Reality, *self-steal*: dest = `127.0.0.1:8443` = Caddy с настоящим сертификатом
для `46-62-140-16.sslip.io`). Не-Reality трафик на 443 уходит в Caddy → сайт-заглушка + `/sub/<token>`
(reverse_proxy на бот `127.0.0.1:8080`). Бот — единственный владелец `data/users.json`, он рендерит
`data/xray/config.json` и рестартит контейнер `vpn-xray` через docker.sock.

**Tech Stack:** Xray-core (ghcr.io/xtls/xray-core), Caddy 2, Python 3.12, aiogram 3, aiohttp, pytest, GitHub Actions.

**Spec:** `docs/specs/2026-09-30-vpn-service-design.md`

## Global Constraints
- Сервер общий с `funnel-bot` (`/opt/funnel-bot`): не трогать его файлы, контейнеры, сеть.
- Открытые порты: 22, 80 (ACME + редирект), 443. 8443/8080/10085 — только 127.0.0.1.
- Вход по паролю SSH **остаётся** (решение владельца), защита — fail2ban (maxretry 5, bantime 1h).
- Секреты только в `.env` / `.secrets/` / GitHub Secrets. В git — `.env.example`.
- Домен подписки: `46-62-140-16.sslip.io`; URL: `https://46-62-140-16.sslip.io/sub/<token>`.
- Кнопка рестарта по умолчанию = рестарт только `vpn-xray`; ребут сервера — через Hetzner API с подтверждением.
- Админ бота — только ID из `ADMIN_IDS`.

## Review Focus
1. Неверный/отозванный токен подписки → 404 без утечки информации (test_subscription_unknown_token_404).
2. Алерты не спамят: одно сообщение на переход OK→FAIL и одно «восстановлено» (test_alert_dedup).
3. Не-админ пишет боту → никаких данных и действий (test_non_admin_ignored).
4. Отзыв ключа реально удаляет клиента из конфига Xray (test_revoke_removes_client).
5. Порча/отсутствие users.json → бот стартует с пустым списком, не падает; запись атомарная (test_store_atomic_and_missing).

---

### Task 1: Bootstrap сервера
**Files:** Create `scripts/bootstrap.sh`
- [ ] Идемпотентно: apt fail2ban (jail sshd), BBR (`/etc/sysctl.d/99-vpn.conf`), ufw allow 22,80,443/tcp → enable; swap 1G если нет.
- [ ] Verify: `make bootstrap`; `ufw status` = 22/80/443; `sysctl net.ipv4.tcp_congestion_control` = bbr; `docker ps` → funnel-bot Up.
- [ ] Commit.

### Task 2: Домен — пользователи и хранилище
**Files:** `bot/vpn/models.py`, `bot/vpn/store.py`, `bot/tests/test_store.py`
**Produces:** `User(name:str, uuid:str, sub_token:str, created:str, active:bool=True)`;
`UserStore(path).list()->list[User]`, `.add(name)->User`, `.revoke(name)->bool`, `.by_token(token)->User|None`.
- [ ] Tests: add генерирует uuid4 и token ≥32 символа (secrets.token_urlsafe); дубль имени → ValueError; revoke → active=False; by_token для revoked → None; test_store_atomic_and_missing (нет файла → []; запись через tmp+os.replace).
- [ ] Implement, pass, commit.

### Task 3: Конфиг Xray, ссылки, подписка
**Files:** `bot/vpn/xray_config.py`, `bot/vpn/links.py`, `bot/tests/test_xray_config.py`, `bot/tests/test_links.py`
**Produces:** `Reality(private_key, public_key, short_id, server_name)`;
`build_config(users:list[User], reality:Reality) -> dict`; `vless_link(user, reality, host:str, label:str)->str`;
`subscription_body(users:list[User], ...)->str` (base64); `subscription_headers(title, update_hours=12)->dict`.
- [ ] Tests: inbound 443 vless, `flow=xtls-rprx-vision`, `realitySettings.dest=="127.0.0.1:8443"`, serverNames==[server_name]; только active-клиенты (test_revoke_removes_client); stats+api inbound 127.0.0.1:10085; блок bittorrent и geoip:private в routing.
  Ссылка: `vless://<uuid>@46.62.140.16:443?encryption=none&flow=xtls-rprx-vision&security=reality&sni=<sn>&fp=chrome&pbk=<pub>&sid=<sid>&type=tcp#<label>`.
  Заголовки: `profile-title` = `base64:` + b64("🇫🇮 TimVPN"), `profile-update-interval: 12`.
- [ ] Implement, pass, commit.

### Task 4: Мониторинг и алерты
**Files:** `bot/vpn/alerts.py`, `bot/vpn/metrics.py`, `bot/tests/test_alerts.py`
**Produces:** `Check(name, ok:bool, detail:str)`; `AlertState.update(checks)->list[str]` (сообщения только на смену состояния; test_alert_dedup);
`async collect_checks(cfg)->list[Check]` (xray контейнер running, TCP 443 connect, latency к 1.1.1.1/8.8.8.8 через TCP:443 < `LATENCY_MS_MAX`=150, диск <90%, RAM <90%);
`async speedtest()->dict(down_mbps, up_mbps, ping_ms)` через speed.cloudflare.com (`__down?bytes=25000000`, `__up`).
- [ ] Tests на AlertState (FAIL→одно сообщение, повтор FAIL→ничего, OK→«восстановлено»). Metrics — без сети, только форматирование.
- [ ] Implement, pass, commit.

### Task 5: Telegram-бот + HTTP подписки
**Files:** `bot/app/main.py`, `bot/app/handlers.py`, `bot/app/sub_server.py`, `bot/app/xray_ctl.py`, `bot/app/hetzner.py`, `bot/Dockerfile`, `bot/requirements.txt`, `bot/tests/test_subscription.py`, `bot/tests/test_handlers.py`
- [ ] Команды/кнопки: 📊 Статус, ⚡ Speedtest, 🔄 Рестарт VPN, ♻️ Ребут сервера (confirm), 👥 Ключи (список), ➕ `/add <имя>` → ссылка Happ + QR, ➖ `/revoke <имя>`, `/report` — дневной отчёт в 10:00 МСК.
- [ ] Фон: цикл проверок каждые 60 с → AlertState → сообщения; при FAIL xray — 1 авто-рестарт и отчёт.
- [ ] sub_server: GET `/sub/{token}` → 200 body+headers | 404 (test_subscription_unknown_token_404). test_non_admin_ignored (фильтр по ADMIN_IDS).
- [ ] Dockerfile: python:3.12-slim + `COPY --from=ghcr.io/xtls/xray-core /usr/local/bin/xray` (для `xray api statsquery`, `xray x25519`).
- [ ] Pass, commit.

### Task 6: Compose, Caddy, деплой
**Files:** `docker-compose.yml`, `server/caddy/Caddyfile`, `server/caddy/site/index.html`, `.env.example`, `scripts/init_secrets.sh`
- [ ] `init_secrets.sh` на сервере: если нет в `.env` — `xray x25519` → REALITY_PRIVATE/PUBLIC, short id `openssl rand -hex 8`.
- [ ] Caddy: `https_port 8443`, bind 127.0.0.1 для https, :80 для ACME и редиректа на `https://{host}` (443); `/sub/*` → 127.0.0.1:8080.
- [ ] Verify: `make deploy`; `curl -sI https://46-62-140-16.sslip.io/` = 200 с валидным сертификатом; `curl .../sub/<token>` = 200; `xray run -test` OK; funnel-bot всё ещё Up.
- [ ] Commit, push.

### Task 7: Внешний сторож
**Files:** `.github/workflows/watchdog.yml`
- [ ] cron `*/5 * * * *`: TCP connect 443 (+ время), HTTPS `/` → при провале 2 раза подряд (повтор через 60 с) → sendMessage в Telegram. Secrets: `TG_TOKEN`, `TG_CHAT_ID`, `VPN_HOST`.
- [ ] Verify: `workflow_dispatch` зелёный; тест-алерт с неверным портом.
- [ ] Commit, push.

### Task 8: E2E
- [ ] Happ: вставить sub URL → подключение, IP = 46.62.140.16; проверить с домашнего Wi-Fi и мобильной сети.
- [ ] `docker stop vpn-xray` → алерт + авто-рестарт + «восстановлено».
- [ ] Бот: speedtest, /add, /revoke (клиент отключается).
