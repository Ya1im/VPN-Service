#!/usr/bin/env bash
# One-time, idempotent server setup. Run: make bootstrap
# Does NOT touch /opt/funnel-bot or its containers.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

echo "== packages"
apt-get update -qq
apt-get install -y -qq fail2ban ufw curl jq >/dev/null

echo "== fail2ban (sshd: 5 attempts -> 1h ban)"
cat >/etc/fail2ban/jail.d/sshd.local <<'JAIL'
[sshd]
enabled  = true
backend  = systemd
maxretry = 5
findtime = 10m
bantime  = 1h
JAIL
systemctl enable --now fail2ban >/dev/null
systemctl restart fail2ban

echo "== BBR + network tuning"
cat >/etc/sysctl.d/99-vpn.conf <<'SYS'
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr
net.ipv4.tcp_fastopen = 3
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
SYS
sysctl --system >/dev/null

echo "== swap 1G"
if ! swapon --show | grep -q .; then
  fallocate -l 1G /swapfile && chmod 600 /swapfile && mkswap /swapfile >/dev/null && swapon /swapfile
  grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

echo "== firewall (22, 80, 443)"
ufw allow 22/tcp  >/dev/null
ufw allow 80/tcp  >/dev/null
ufw allow 443/tcp >/dev/null
ufw default deny incoming  >/dev/null
ufw default allow outgoing >/dev/null
ufw --force enable >/dev/null

echo "== result"
ufw status | sed -n '1,12p'
sysctl -n net.ipv4.tcp_congestion_control
fail2ban-client status sshd | grep -E 'Currently|Total' || true
swapon --show
docker ps --format '{{.Names}}: {{.Status}}'
