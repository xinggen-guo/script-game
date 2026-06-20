#!/usr/bin/env bash
set -euo pipefail

APP_SRC="${1:-./v2ray_user_manager.py}"
APP_DST="/opt/v2ray-user-manager/app.py"
SERVICE_FILE="/etc/systemd/system/v2ray-user-manager.service"
STATE_PATH="${V2RAY_MANAGER_STATE_PATH:-/opt/v2ray-user-manager/state.json}"
MANAGER_HOST="${V2RAY_MANAGER_HOST:-0.0.0.0}"
MANAGER_PORT="${V2RAY_MANAGER_PORT:-8091}"
CONFIG_PATH="${V2RAY_CONFIG_PATH:-/etc/v2ray/config.json}"
BASE_CLASH_PATH="${V2RAY_BASE_CLASH_PATH:-/opt/v2ray-sub/clash.yaml}"
USERS_DIR="${V2RAY_USERS_DIR:-/opt/v2ray-sub/users}"
SERVER_ADDR="${V2RAY_SERVER_ADDR:-}"
SUB_BASE_URL="${V2RAY_SUB_BASE_URL:-http://194.87.245.15:8088/clash.yaml}"
VMESS_PORT="${V2RAY_PORT:-443}"
WS_PATH="${V2RAY_WS_PATH:-/v2ray}"
V2RAY_API_SERVER="${V2RAY_API_SERVER:-127.0.0.1:10085}"
MANAGER_USERNAME="${V2RAY_MANAGER_USERNAME:-admin}"
MANAGER_PASSWORD="${V2RAY_MANAGER_PASSWORD:-$(openssl rand -hex 16)}"
MANAGER_SESSION_SECRET="${V2RAY_MANAGER_SESSION_SECRET:-$(openssl rand -hex 24)}"

if [ ! -f "$APP_SRC" ]; then
  echo "User manager source not found: $APP_SRC" >&2
  exit 1
fi

mkdir -p /opt/v2ray-user-manager
mkdir -p "$USERS_DIR"

install -m 755 "$APP_SRC" "$APP_DST"

cat >"$SERVICE_FILE" <<EOF
[Unit]
Description=V2Ray User Manager
After=network.target v2ray.service v2ray-sub.service

[Service]
User=root
WorkingDirectory=/opt/v2ray-user-manager
Environment=V2RAY_MANAGER_HOST=${MANAGER_HOST}
Environment=V2RAY_MANAGER_PORT=${MANAGER_PORT}
Environment=V2RAY_MANAGER_STATE_PATH=${STATE_PATH}
Environment=V2RAY_CONFIG_PATH=${CONFIG_PATH}
Environment=V2RAY_BASE_CLASH_PATH=${BASE_CLASH_PATH}
Environment=V2RAY_USERS_DIR=${USERS_DIR}
Environment=V2RAY_SERVER_ADDR=${SERVER_ADDR}
Environment=V2RAY_SUB_BASE_URL=${SUB_BASE_URL}
Environment=V2RAY_PORT=${VMESS_PORT}
Environment=V2RAY_WS_PATH=${WS_PATH}
Environment=V2RAY_API_SERVER=${V2RAY_API_SERVER}
Environment=V2RAY_MANAGER_USERNAME=${MANAGER_USERNAME}
Environment=V2RAY_MANAGER_PASSWORD=${MANAGER_PASSWORD}
Environment=V2RAY_MANAGER_SESSION_SECRET=${MANAGER_SESSION_SECRET}
ExecStart=/usr/bin/python3 /opt/v2ray-user-manager/app.py serve
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now v2ray-user-manager.service

echo "V2Ray user manager deployed."
echo "Bind: ${MANAGER_HOST}:${MANAGER_PORT}"
echo "Login: ${MANAGER_USERNAME}"
echo "Password: ${MANAGER_PASSWORD}"
systemctl --no-pager --full status v2ray-user-manager.service | sed -n '1,8p'
