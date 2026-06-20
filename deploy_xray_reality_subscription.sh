#!/usr/bin/env bash
set -euo pipefail

XRAY_PORT="${XRAY_PORT:-443}"
SUB_PORT="${SUB_PORT:-8088}"
SERVER_NAME="${SERVER_NAME:-www.cloudflare.com}"
DEST_ADDR="${DEST_ADDR:-www.cloudflare.com:443}"
SHORT_ID_LENGTH="${SHORT_ID_LENGTH:-8}"
XRAY_BIN_DIR="/usr/local/xray"
XRAY_ETC_DIR="/usr/local/etc/xray"
SUB_DIR="/opt/v2ray-sub"
SERVICE_FILE="/etc/systemd/system/xray.service"
SUB_SERVICE_FILE="/etc/systemd/system/xray-sub.service"
ACCESS_LOG="/var/log/xray/access.log"
ERROR_LOG="/var/log/xray/error.log"

if command -v uuidgen >/dev/null 2>&1; then
  UUID="$(uuidgen | tr 'A-Z' 'a-z')"
else
  UUID="$(cat /proc/sys/kernel/random/uuid)"
fi

SHORT_ID="$(openssl rand -hex "$((SHORT_ID_LENGTH / 2))")"
PUBLIC_IP="$(curl -4 -fsSL ifconfig.me || hostname -I | awk '{print $1}')"

apt-get update
apt-get install -y curl unzip python3 openssl

mkdir -p "$XRAY_BIN_DIR" "$XRAY_ETC_DIR" "$SUB_DIR" /var/log/xray

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT
cd "$TMP_DIR"

curl -L -o xray.zip https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip
unzip -o xray.zip
install -m 755 xray "${XRAY_BIN_DIR}/xray"
if [ -f geosite.dat ]; then
  install -m 644 geosite.dat "${XRAY_ETC_DIR}/geosite.dat"
fi
if [ -f geoip.dat ]; then
  install -m 644 geoip.dat "${XRAY_ETC_DIR}/geoip.dat"
fi

KEYPAIR="$(${XRAY_BIN_DIR}/xray x25519)"
PRIVATE_KEY="$(printf '%s\n' "$KEYPAIR" | awk '/Private key/ {print $3}')"
PUBLIC_KEY="$(printf '%s\n' "$KEYPAIR" | awk '/Public key/ {print $3}')"

cat >"${XRAY_ETC_DIR}/config.json" <<EOF
{
  "log": {
    "loglevel": "warning",
    "access": "${ACCESS_LOG}",
    "error": "${ERROR_LOG}"
  },
  "inbounds": [
    {
      "listen": "0.0.0.0",
      "port": ${XRAY_PORT},
      "protocol": "vless",
      "settings": {
        "clients": [
          {
            "id": "${UUID}",
            "flow": "xtls-rprx-vision"
          }
        ],
        "decryption": "none"
      },
      "streamSettings": {
        "network": "tcp",
        "security": "reality",
        "realitySettings": {
          "show": false,
          "dest": "${DEST_ADDR}",
          "xver": 0,
          "serverNames": ["${SERVER_NAME}"],
          "privateKey": "${PRIVATE_KEY}",
          "shortIds": ["${SHORT_ID}"]
        }
      },
      "sniffing": {
        "enabled": true,
        "destOverride": ["http", "tls", "quic"]
      }
    }
  ],
  "outbounds": [
    {
      "protocol": "freedom",
      "tag": "direct"
    },
    {
      "protocol": "blackhole",
      "tag": "blocked"
    }
  ]
}
EOF

cat >"${SERVICE_FILE}" <<EOF
[Unit]
Description=Xray Service
After=network.target nss-lookup.target

[Service]
User=root
ExecStart=${XRAY_BIN_DIR}/xray run -config ${XRAY_ETC_DIR}/config.json
Restart=on-failure
RestartSec=3
LimitNOFILE=1048576

[Install]
WantedBy=multi-user.target
EOF

cat >"${SUB_DIR}/clash.yaml" <<EOF
mode: rule
mixed-port: 7890
allow-lan: true
log-level: info
ipv6: false
unified-delay: true

dns:
  enable: true
  ipv6: false
  enhanced-mode: fake-ip
  use-hosts: true
  default-nameserver:
    - 223.5.5.5
    - 119.29.29.29
  nameserver:
    - 223.5.5.5
    - 119.29.29.29
  fallback:
    - https://dns.cloudflare.com/dns-query
    - https://dns.google/dns-query
    - tls://1.1.1.1:853
    - tls://8.8.8.8:853
  fallback-filter:
    geoip: true
    geoip-code: CN
    ipcidr:
      - 240.0.0.0/4
      - 0.0.0.0/32

proxies:
  - name: AntLink-Reality
    type: vless
    server: ${PUBLIC_IP}
    port: ${XRAY_PORT}
    uuid: ${UUID}
    network: tcp
    udp: true
    tls: true
    servername: ${SERVER_NAME}
    reality-opts:
      public-key: ${PUBLIC_KEY}
      short-id: ${SHORT_ID}
    flow: xtls-rprx-vision
    client-fingerprint: chrome

proxy-groups:
  - name: AntLink
    type: select
    proxies:
      - AntLink-Reality
      - DIRECT

rules:
  - DOMAIN-SUFFIX,chatgpt.com,AntLink
  - DOMAIN-SUFFIX,openai.com,AntLink
  - DOMAIN-SUFFIX,auth.openai.com,AntLink
  - DOMAIN-SUFFIX,platform.openai.com,AntLink
  - DOMAIN-SUFFIX,cdn.openai.com,AntLink
  - DOMAIN-SUFFIX,oaistatic.com,AntLink
  - DOMAIN-SUFFIX,oaiusercontent.com,AntLink
  - DOMAIN-SUFFIX,cdn.oaistatic.com,AntLink
  - DOMAIN-SUFFIX,files.oaiusercontent.com,AntLink
  - DOMAIN-SUFFIX,anthropic.com,AntLink
  - DOMAIN-SUFFIX,claude.ai,AntLink
  - DOMAIN-SUFFIX,claudeusercontent.com,AntLink
  - DOMAIN-SUFFIX,gemini.google.com,AntLink
  - DOMAIN-SUFFIX,google.com,AntLink
  - DOMAIN-SUFFIX,googleapis.com,AntLink
  - DOMAIN-SUFFIX,gstatic.com,AntLink
  - DOMAIN-SUFFIX,telegram.org,AntLink
  - DOMAIN-SUFFIX,t.me,AntLink
  - DOMAIN-SUFFIX,telegra.ph,AntLink
  - DOMAIN-SUFFIX,linkedin.com,AntLink
  - DOMAIN-SUFFIX,licdn.com,AntLink
  - DOMAIN-SUFFIX,cn,DIRECT
  - GEOIP,CN,DIRECT
  - MATCH,AntLink
EOF

cat >"${SUB_SERVICE_FILE}" <<EOF
[Unit]
Description=Simple HTTP server for Clash subscription
After=network.target

[Service]
WorkingDirectory=${SUB_DIR}
ExecStart=/usr/bin/python3 -m http.server ${SUB_PORT} --bind 0.0.0.0
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now xray.service
systemctl enable --now xray-sub.service

VLESS_LINK="vless://${UUID}@${PUBLIC_IP}:${XRAY_PORT}?encryption=none&security=reality&sni=${SERVER_NAME}&fp=chrome&pbk=${PUBLIC_KEY}&sid=${SHORT_ID}&type=tcp&flow=xtls-rprx-vision#AntLink-Reality"

echo
echo "========== DEPLOY SUCCESS =========="
echo "Server IP: ${PUBLIC_IP}"
echo "Port: ${XRAY_PORT}"
echo "Protocol: vless"
echo "Security: reality"
echo "UUID: ${UUID}"
echo "ServerName: ${SERVER_NAME}"
echo "Dest: ${DEST_ADDR}"
echo "Public Key: ${PUBLIC_KEY}"
echo "Short ID: ${SHORT_ID}"
echo "Subscription URL: http://${PUBLIC_IP}:${SUB_PORT}/clash.yaml"
echo "Config file: ${XRAY_ETC_DIR}/config.json"
echo "Access log: ${ACCESS_LOG}"
echo "Error log: ${ERROR_LOG}"
echo
echo "Services:"
systemctl --no-pager --full status xray.service | sed -n '1,8p'
systemctl --no-pager --full status xray-sub.service | sed -n '1,8p'
echo
echo "VLESS Link:"
echo "${VLESS_LINK}"
echo "===================================="
