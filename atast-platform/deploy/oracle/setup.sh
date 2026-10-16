#!/usr/bin/env bash
# One-time installation of the ATAST platform on an Ubuntu/Debian VM (Oracle Cloud Always Free or any other VPS).
#
#   git clone <repo> && cd <repo>
#   sudo bash atast-platform/deploy/oracle/setup.sh                  # site on https://<ip>.sslip.io
#   sudo DOMAIN=membres.exemple.tn bash atast-platform/deploy/oracle/setup.sh   # your own domain (DNS A record first)
#
# Safe to run again: it keeps the database, the uploads and /etc/atast/atast.env.
set -euo pipefail

[ "$(id -u)" -eq 0 ] || { echo "Run as root: sudo bash $0"; exit 1; }
command -v apt-get >/dev/null || { echo "This script supports Ubuntu/Debian (apt) only."; exit 1; }

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"   # the atast-platform folder of the checkout
APP=/opt/atast/app
DATA=/var/lib/atast
ENV_FILE=/etc/atast/atast.env
export DEBIAN_FRONTEND=noninteractive

[ -f "$SRC/backend/server.js" ] || { echo "Cannot find backend/server.js next to this script ($SRC)."; exit 1; }

echo "==> Packages"
apt-get update -y
apt-get install -y curl ca-certificates gnupg rsync debian-keyring debian-archive-keyring apt-transport-https cron iptables

echo "==> Node.js 22"
need_node=1
if command -v node >/dev/null; then
  node -e 'const [a,b]=process.versions.node.split(".").map(Number); process.exit(a>22||(a===22&&b>=13)?0:1)' && need_node=0
fi
if [ "$need_node" = 1 ]; then
  curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
  apt-get install -y nodejs
fi
node -v

echo "==> Caddy (automatic HTTPS)"
if ! command -v caddy >/dev/null; then
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor --yes -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' > /etc/apt/sources.list.d/caddy-stable.list
  apt-get update -y
  apt-get install -y caddy
fi

echo "==> Service user and folders"
id atast >/dev/null 2>&1 || useradd --system --home /opt/atast --shell /usr/sbin/nologin atast
mkdir -p "$APP" "$DATA/uploads" "$DATA/backups" /etc/atast
chown -R atast:atast /opt/atast "$DATA"

echo "==> Application code"
rsync -a --delete --exclude node_modules --exclude '.env' --exclude 'database/*.sqlite*' --exclude 'database/backups' \
  --exclude uploads --exclude deploy --exclude .git "$SRC"/ "$APP"/
mkdir -p "$APP/uploads"
chown -R atast:atast "$APP"
sudo -u atast bash -c "cd '$APP' && npm ci --omit=dev --no-audit --no-fund"

echo "==> Address of the site"
if [ -n "${DOMAIN:-}" ]; then
  HOST="$DOMAIN"
else
  IP="$(curl -4fsS https://api.ipify.org || curl -4fsS https://ifconfig.me)"
  HOST="${IP//./-}.sslip.io"   # free wildcard DNS: 1-2-3-4.sslip.io -> 1.2.3.4
fi
echo "    https://$HOST"

echo "==> Configuration ($ENV_FILE)"
if [ ! -f "$ENV_FILE" ]; then
  cat > "$ENV_FILE" <<EOF
NODE_ENV=production
PORT=3000
APP_URL=https://$HOST
DATABASE_URL=$DATA/atast.sqlite
UPLOAD_DIR=$DATA/uploads
BACKUP_DIR=$DATA/backups
BACKUP_KEEP=30
CLUB_TIMEZONE=Africa/Tunis
AUTO_ACCEPT_REQUIRE_PHONE=true
EOF
else
  # keep every setting but follow a changed address
  sed -i "s#^APP_URL=.*#APP_URL=https://$HOST#" "$ENV_FILE"
fi
chown root:atast "$ENV_FILE"
chmod 640 "$ENV_FILE"

echo "==> Helper commands"
cat > /usr/local/bin/atast-run <<'EOF'
#!/usr/bin/env bash
# Runs a project script with the production settings, as the service user: atast-run database/seeds/create-admin.js
set -euo pipefail
[ "$#" -ge 1 ] || { echo "usage: atast-run <script.js>"; exit 1; }
exec sudo -u atast bash -c 'set -a; . /etc/atast/atast.env; set +a; cd /opt/atast/app; exec node "$@"' _ "$@"
EOF
cat > /usr/local/bin/atast-admin <<'EOF'
#!/usr/bin/env bash
# Creates (or reactivates) an administrator: sudo atast-admin "Nom" email phone   (the password is asked, not echoed)
set -euo pipefail
[ "$#" -eq 3 ] || { echo 'usage: sudo atast-admin "Nom complet" email@exemple.tn +21620000000'; exit 1; }
read -r -s -p "Mot de passe (8+ caractères, lettres et chiffres) : " ADMIN_PASSWORD; echo
export ADMIN_NAME="$1" ADMIN_EMAIL="$2" ADMIN_PHONE="$3" ADMIN_PASSWORD
exec sudo -u atast --preserve-env=ADMIN_NAME,ADMIN_EMAIL,ADMIN_PHONE,ADMIN_PASSWORD \
  bash -c 'set -a; . /etc/atast/atast.env; set +a; cd /opt/atast/app; exec node database/seeds/create-admin.js'
EOF
cat > /usr/local/bin/atast-backup <<'EOF'
#!/usr/bin/env bash
exec /usr/local/bin/atast-run database/backup.js
EOF
chmod 755 /usr/local/bin/atast-run /usr/local/bin/atast-admin /usr/local/bin/atast-backup

echo "==> Service"
cp "$SRC/deploy/oracle/atast.service" /etc/systemd/system/atast.service
sed "s#__HOST__#$HOST#" "$SRC/deploy/oracle/Caddyfile" > /etc/caddy/Caddyfile
echo '17 3 * * * root /usr/local/bin/atast-backup >> /var/log/atast-backup.log 2>&1' > /etc/cron.d/atast-backup
chmod 644 /etc/cron.d/atast-backup
systemctl daemon-reload
systemctl enable --now atast
systemctl restart atast
systemctl enable caddy
systemctl reload caddy 2>/dev/null || systemctl restart caddy

echo "==> Firewall (ports 80 and 443)"
if command -v ufw >/dev/null && ufw status | grep -q "Status: active"; then
  ufw allow 80/tcp; ufw allow 443/tcp
else
  for port in 80 443; do
    iptables -C INPUT -p tcp --dport "$port" -j ACCEPT 2>/dev/null || iptables -I INPUT 1 -p tcp --dport "$port" -j ACCEPT
  done
  DEBIAN_FRONTEND=noninteractive apt-get install -y iptables-persistent >/dev/null 2>&1 || true
  command -v netfilter-persistent >/dev/null && netfilter-persistent save >/dev/null 2>&1 || true
fi

echo "==> Health check"
for _ in $(seq 1 20); do
  if curl -fsS http://127.0.0.1:3000/healthz >/dev/null 2>&1; then ok=1; break; fi
  sleep 1
done
[ "${ok:-0}" = 1 ] || { echo "The application did not start. See: journalctl -u atast -n 50"; exit 1; }

cat <<EOF

Done. The platform runs at: https://$HOST
(the HTTPS certificate is issued on first visit; if the page does not open, check that ports 80 and 443 are open in the Oracle console)

Next step: create the first administrator
    sudo atast-admin "Bureau ATAST" bureau@atast.tn +21673000000
EOF
