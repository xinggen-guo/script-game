#!/usr/bin/env bash
set -euo pipefail

APP_SRC="${1:-./xray_reality_user_manager.py}"
APP_DST="/opt/xray-user-manager/app.py"
SERVICE_FILE="/etc/systemd/system/xray-user-manager.service"
MANAGER_HOST="${XRAY_MANAGER_HOST:-127.0.0.1}"
MANAGER_PORT="${XRAY_MANAGER_PORT:-8091}"
CONFIG_PATH="${XRAY_CONFIG_PATH:-/usr/local/etc/xray/config.json}"
ACCESS_LOG="${XRAY_ACCESS_LOG:-/var/log/xray/access.log}"
SERVER_IP="${XRAY_SERVER_IP:-}"
SUB_BASE_URL="${XRAY_SUB_BASE_URL:-http://127.0.0.1:8088/clash.yaml}"

if [ ! -f "$APP_SRC" ]; then
  echo "Manager source not found: $APP_SRC" >&2
  exit 1
fi

mkdir -p /opt/xray-user-manager

install -m 755 "$APP_SRC" "$APP_DST"

cat >"$SERVICE_FILE" <<EOF
[Unit]
Description=Xray Reality User Manager
After=network.target xray.service xray-sub.service

[Service]
User=root
WorkingDirectory=/opt/xray-user-manager
Environment=XRAY_MANAGER_HOST=${MANAGER_HOST}
Environment=XRAY_MANAGER_PORT=${MANAGER_PORT}
Environment=XRAY_CONFIG_PATH=${CONFIG_PATH}
Environment=XRAY_ACCESS_LOG=${ACCESS_LOG}
Environment=XRAY_SERVER_IP=${SERVER_IP}
Environment=XRAY_SUB_BASE_URL=${SUB_BASE_URL}
ExecStart=/usr/bin/python3 /opt/xray-user-manager/app.py serve
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now xray-user-manager.service

echo "User manager deployed."
echo "Bind: ${MANAGER_HOST}:${MANAGER_PORT}"
systemctl --no-pager --full status xray-user-manager.service | sed -n '1,8p'
