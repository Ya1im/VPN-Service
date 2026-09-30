#!/usr/bin/env bash
# Run ON THE SERVER in /opt/vpn-service. Creates/fills .env without overwriting existing values.
set -euo pipefail
cd /opt/vpn-service
[ -f .env ] || cp .env.example .env
chmod 600 .env
get() { grep -E "^$1=" .env | cut -d= -f2- || true; }
set_kv() { if grep -qE "^$1=" .env; then sed -i "s|^$1=.*|$1=$2|" .env; else echo "$1=$2" >> .env; fi; }
if [ -z "$(get REALITY_PRIVATE_KEY)" ]; then
  out=$(docker run --rm ghcr.io/xtls/xray-core:26.3.27 x25519)
  priv=$(echo "$out" | awk -F': ' '/Private/{print $2}')
  pub=$(echo "$out"  | awk -F': ' '/Public|Password/{print $2}' | head -1)
  set_kv REALITY_PRIVATE_KEY "$priv"
  set_kv REALITY_PUBLIC_KEY "$pub"
  set_kv REALITY_SHORT_ID "$(openssl rand -hex 8)"
  echo "reality keys generated"
fi
mkdir -p data/xray
