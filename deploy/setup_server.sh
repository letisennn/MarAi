#!/usr/bin/env bash
# Körs PÅ SERVERN som root (av deploy.sh). Idempotent — går att köra om.
# Användning: setup_server.sh <domän, t.ex. 1-2-3-4.sslip.io>
set -euo pipefail

DOMAIN="${1:?usage: setup_server.sh <domän>}"
APP=/opt/noel
export DEBIAN_FRONTEND=noninteractive

timedatectl set-timezone Europe/Stockholm      # 17:00 ska vara 17:00 svensk tid

apt-get update -y
apt-get install -y curl ca-certificates rsync ufw gpg debian-keyring debian-archive-keyring apt-transport-https

# --- Caddy (HTTPS med automatiskt certifikat) ---------------------------------
if ! command -v caddy >/dev/null; then
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor --yes -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' > /etc/apt/sources.list.d/caddy-stable.list
  apt-get update -y
  apt-get install -y caddy
fi

# --- användare + mappar ---------------------------------------------------------
id noel >/dev/null 2>&1 || useradd --system --create-home --shell /bin/bash noel
mkdir -p "$APP/data" /var/log
touch /var/log/noel-refresh.log
chown -R noel:noel "$APP"

# --- 4 GB swap (panelbygget är minnestungt; skyddar mot OOM på små servrar) ----
if ! swapon --show | grep -q .; then
  fallocate -l 4G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

# --- Python-miljö (uv) ---------------------------------------------------------
runuser -u noel -- bash -lc 'command -v uv >/dev/null 2>&1 || [ -x "$HOME/.local/bin/uv" ] || (curl -LsSf https://astral.sh/uv/install.sh | sh)'
runuser -u noel -- bash -lc "cd $APP && \$HOME/.local/bin/uv sync --frozen"

# --- systemd: appen + daglig uppdatering 17:00 och 18:00 ----------------------
chmod +x "$APP/deploy/refresh.sh"
install -m 644 "$APP/deploy/noel-app.service" /etc/systemd/system/noel-app.service
install -m 644 "$APP/deploy/noel-refresh.service" /etc/systemd/system/noel-refresh.service
install -m 644 "$APP/deploy/noel-refresh.timer" /etc/systemd/system/noel-refresh.timer
systemctl daemon-reload
systemctl enable noel-app.service noel-refresh.timer
systemctl restart noel-app.service
systemctl start noel-refresh.timer

# --- Caddy: publik adress -> appen ---------------------------------------------
sed "s/{{DOMAIN}}/$DOMAIN/g" "$APP/deploy/Caddyfile.template" > /etc/caddy/Caddyfile
systemctl enable caddy
systemctl reload caddy 2>/dev/null || systemctl restart caddy

# --- brandvägg: bara SSH + webb --------------------------------------------------
ufw allow OpenSSH >/dev/null
ufw allow 80/tcp >/dev/null
ufw allow 443/tcp >/dev/null
ufw --force enable >/dev/null

# --- är appen uppe? --------------------------------------------------------------
for i in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:8501/_stcore/health >/dev/null 2>&1; then
    echo "OK: appen svarar lokalt på servern"
    exit 0
  fi
  sleep 2
done
echo "VARNING: appen svarar inte än — kolla: journalctl -u noel-app -n 50" >&2
exit 1
