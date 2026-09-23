#!/usr/bin/env bash
# Läg upp / uppdatera Noel AI på servern. Körs från din Mac (repots rot eller deploy/).
#
#   deploy/deploy.sh <server-ip>                 # kod + inställningar (rör aldrig portföljerna)
#   deploy/deploy.sh <server-ip> --with-data     # + första gången: databaserna (marc.duckdb, och
#                                                #   paper_trades.duckdb OM den inte redan finns på servern)
#   deploy/deploy.sh <server-ip> --domain noel.example.com   # egen domän i stället för <ip>.sslip.io
#
# Servern är sanningen för portföljerna: när den väl har en paper_trades.duckdb
# skrivs den ALDRIG över härifrån.
set -euo pipefail

HOST="${1:?usage: deploy.sh <server-ip> [--with-data] [--domain d]}"
shift || true
WITH_DATA=0
DOMAIN="${HOST//./-}.sslip.io"
while [ $# -gt 0 ]; do
  case "$1" in
    --with-data) WITH_DATA=1 ;;
    --domain) DOMAIN="${2:?--domain kräver ett värde}"; shift ;;
    *) echo "okänt argument: $1" >&2; exit 2 ;;
  esac
  shift
done

cd "$(dirname "$0")/.."
KEY="${NOEL_SSH_KEY:-$HOME/.ssh/noel_deploy_ed25519}"
SSH_OPTS="-i $KEY -o StrictHostKeyChecking=accept-new -o ServerAliveInterval=30"
REMOTE="root@$HOST"
ssh_run() { ssh $SSH_OPTS "$REMOTE" "$@"; }

echo "→ 1/5 kontrollerar SSH mot $HOST"
ssh_run 'mkdir -p /opt/noel/data && echo ok' >/dev/null

echo "→ 2/5 kopierar koden"
rsync -az --delete -e "ssh $SSH_OPTS" \
  --include='data/' --include='data/seed/' --include='data/seed/***' --exclude='data/**' \
  --exclude='.git' --exclude='.venv' --exclude='.env' --exclude='__pycache__' --exclude='*.pyc' \
  --exclude='.pytest_cache' --exclude='.ruff_cache' --exclude='.mypy_cache' --exclude='.DS_Store' \
  ./ "$REMOTE:/opt/noel/"

echo "→ 3/5 lösenord (bara MARC_USER_* ur din lokala .env, filen på servern blir 600)"
grep -E '^MARC_USER_(JONAS|HUGO)_PASSWORD=.+' .env | ssh_run 'umask 077; cat > /etc/noel.env'

if [ "$WITH_DATA" = 1 ]; then
  echo "→ 4/5 kopierar databaserna (kan ta några minuter)"
  rsync -az --partial --info=progress2 -e "ssh $SSH_OPTS" data/marc.duckdb "$REMOTE:/opt/noel/data/marc.duckdb"
  if ssh_run 'test -f /opt/noel/data/paper_trades.duckdb'; then
    echo "   paper_trades.duckdb finns redan på servern — rör den inte."
  else
    rsync -az -e "ssh $SSH_OPTS" data/paper_trades.duckdb "$REMOTE:/opt/noel/data/paper_trades.duckdb"
  fi
else
  echo "→ 4/5 hoppar över databaserna (använd --with-data första gången)"
fi

echo "→ 5/5 installerar och startar på servern"
ssh_run "bash /opt/noel/deploy/setup_server.sh $DOMAIN"

echo
echo "Klart. Adress:  https://$DOMAIN"
echo "(certifikatet kan ta upp till en minut första gången)"
