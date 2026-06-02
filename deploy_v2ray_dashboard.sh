#!/usr/bin/env bash
set -euo pipefail

APP_SRC="${1:-./v2ray_dashboard.py}"
APP_DST="/opt/v2ray-dashboard/app.py"
STATE_DIR="/var/lib/v2ray-dashboard"
SERVICE_FILE="/etc/systemd/system/v2ray-dashboard.service"
DASHBOARD_PORT="${V2RAY_DASHBOARD_PORT:-8090}"
V2RAY_PORT="${V2RAY_PORT:-443}"
SUB_URL="${V2RAY_SUB_URL:-http://127.0.0.1:8088/clash.yaml}"

if [ ! -f "$APP_SRC" ]; then
  echo "Dashboard source not found: $APP_SRC" >&2
  exit 1
fi

mkdir -p /opt/v2ray-dashboard
mkdir -p "$STATE_DIR"

install -m 755 "$APP_SRC" "$APP_DST"

cat >"$SERVICE_FILE" <<EOF
[Unit]
Description=V2Ray Connection Dashboard
After=network.target v2ray.service v2ray-sub.service

[Service]
User=root
WorkingDirectory=/opt/v2ray-dashboard
Environment=V2RAY_DASHBOARD_PORT=${DASHBOARD_PORT}
Environment=V2RAY_PORT=${V2RAY_PORT}
Environment=V2RAY_DASHBOARD_STATE=${STATE_DIR}/state.json
Environment=V2RAY_SUB_URL=${SUB_URL}
ExecStart=/usr/bin/python3 /opt/v2ray-dashboard/app.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now v2ray-dashboard.service

echo "Dashboard deployed."
echo "Dashboard port: ${DASHBOARD_PORT}"
echo "Dashboard service: v2ray-dashboard.service"
systemctl --no-pager --full status v2ray-dashboard.service | sed -n '1,8p'
