# vpn-service

Личный VPN (VLESS + Reality на Xray-core) на Hetzner (Хельсинки) с подпиской для Happ
и Telegram-ботом мониторинга/управления.

## Структура
| Путь | Что там |
|---|---|
| `server/xray/` | шаблон конфига Xray (VLESS + Reality + Vision) |
| `server/caddy/` | Caddy: HTTPS-подписки для Happ (`https://<IP>.sslip.io:8443/sub/<token>`) |
| `bot/` | Telegram-бот: алерты, метрики, speedtest, рестарт, выдача ключей |
| `scripts/` | bootstrap/хардeнинг сервера, деплой |
| `.github/workflows/` | внешний сторож (проверка сервера снаружи каждые 5 минут) |
| `docs/specs/` | дизайн и решения |
| `.secrets/` | SSH-ключи проекта (**в git не попадает**) |

## Деплой
```bash
make deploy      # rsync + docker compose up на сервер, без пароля (ключ из .secrets/)
make ssh         # зайти на сервер
make test        # тесты бота и генерации конфигов
```
