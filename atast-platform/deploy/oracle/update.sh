#!/usr/bin/env bash
# Deploys a new version: git pull in your checkout, then `sudo bash atast-platform/deploy/oracle/update.sh`.
# The database and the photos are never touched; a backup is taken first.
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Run as root: sudo bash $0"; exit 1; }
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
/usr/local/bin/atast-backup || echo "(no backup taken)"
rsync -a --delete --exclude node_modules --exclude '.env' --exclude 'database/*.sqlite*' --exclude 'database/backups' \
  --exclude uploads --exclude deploy --exclude .git "$SRC"/ /opt/atast/app/
chown -R atast:atast /opt/atast/app
sudo -u atast bash -c "cd /opt/atast/app && npm ci --omit=dev --no-audit --no-fund"
systemctl restart atast
for _ in $(seq 1 20); do curl -fsS http://127.0.0.1:3000/healthz >/dev/null 2>&1 && { echo "Updated and running."; exit 0; }; sleep 1; done
echo "The application did not start. See: journalctl -u atast -n 50"; exit 1
