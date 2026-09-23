#!/usr/bin/env bash
# Daglig uppdatering på servern (körs av systemd-timern som root).
#
# Bygger den nya databasen på en KOPIA och byter in den först när allt gått bra:
# en misslyckad körning (t.ex. Yahoo som strular) kan aldrig skada den databas
# som appen visar. Appen körs hela tiden — den startas bara om (några sekunder)
# när den nya databasen läggs på plats. Portföljerna (paper_trades.duckdb) är en
# separat fil som aldrig rörs här.
set -euo pipefail

APP="${NOEL_DIR:-/opt/noel}"
DATA="$APP/data"
LOG="${NOEL_LOG:-/var/log/noel-refresh.log}"
RESTART="${NOEL_RESTART_CMD:-systemctl restart noel-app}"
AS_APP_USER="${NOEL_RUN_AS:-runuser -u noel --}"

exec 9>"/tmp/noel-refresh.lock"
flock -n 9 || { echo "$(date '+%Y-%m-%dT%H:%M:%S%z') en uppdatering pågår redan — hoppar över" >>"$LOG"; exit 0; }
exec >>"$LOG" 2>&1

echo "=== $(date '+%Y-%m-%dT%H:%M:%S%z') uppdatering startar ==="
NEW="$DATA/marc.refresh.duckdb"
cleanup() { rm -f "$NEW" "$NEW.wal"; }
trap cleanup EXIT
cleanup
cp "$DATA/marc.duckdb" "$NEW"

if $AS_APP_USER env MARC_DB_PATH="$NEW" "$APP/.venv/bin/marc" refresh; then
  mv -f "$NEW" "$DATA/marc.duckdb"
  rm -f "$DATA/marc.duckdb.wal"
  $RESTART
  echo "=== $(date '+%Y-%m-%dT%H:%M:%S%z') klart — ny databas på plats ==="
else
  echo "=== $(date '+%Y-%m-%dT%H:%M:%S%z') UPPDATERINGEN MISSLYCKADES — behåller gårdagens databas ==="
  exit 1
fi
