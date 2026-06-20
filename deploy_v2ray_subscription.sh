#!/usr/bin/env bash
set -euo pipefail

WS_PATH="/v2ray"
V2RAY_PORT="443"
SUB_PORT="8088"

if command -v uuidgen >/dev/null 2>&1; then
  UUID="$(uuidgen | tr 'A-Z' 'a-z')"
else
  UUID="$(cat /proc/sys/kernel/random/uuid)"
fi

PUBLIC_IP="$(curl -4 -fsSL ifconfig.me || hostname -I | awk '{print $1}')"

apt-get update
apt-get install -y curl unzip python3

mkdir -p /usr/local/v2ray
mkdir -p /etc/v2ray
mkdir -p /opt/v2ray-sub
touch /opt/v2ray-sub/.healthz

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT
cd "$TMP_DIR"

curl -L -o v2ray.zip https://github.com/v2fly/v2ray-core/releases/latest/download/v2ray-linux-64.zip
unzip -o v2ray.zip
install -m 755 v2ray /usr/local/v2ray/v2ray
if [ -f v2ctl ]; then
  install -m 755 v2ctl /usr/local/v2ray/v2ctl
fi

cat >/etc/v2ray/config.json <<EOF
{
  "log": { "loglevel": "warning" },
  "inbounds": [
    {
      "listen": "0.0.0.0",
      "port": ${V2RAY_PORT},
      "protocol": "vmess",
      "settings": {
        "clients": [
          {
            "id": "${UUID}",
            "alterId": 0
          }
        ]
      },
      "streamSettings": {
        "network": "ws",
        "wsSettings": {
          "path": "${WS_PATH}"
        }
      }
    }
  ],
  "outbounds": [
    { "protocol": "freedom" },
    { "protocol": "blackhole", "tag": "blocked" }
  ]
}
EOF

cat >/etc/systemd/system/v2ray.service <<'EOF'
[Unit]
Description=V2Ray Service
After=network.target nss-lookup.target

[Service]
User=root
ExecStart=/usr/local/v2ray/v2ray run -config /etc/v2ray/config.json
Restart=on-failure
RestartSec=3
LimitNOFILE=1048576

[Install]
WantedBy=multi-user.target
EOF

cat >/opt/v2ray-sub/clash.yaml <<EOF
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
  - name: AntLink-VPS
    type: vmess
    server: ${PUBLIC_IP}
    port: ${V2RAY_PORT}
    uuid: ${UUID}
    alterId: 0
    cipher: auto
    tls: false
    network: ws
    udp: true
    ws-opts:
      path: ${WS_PATH}

proxy-groups:
  - name: AntLink
    type: select
    proxies:
      - AntLink-VPS
      - DIRECT

rules:
  - DOMAIN,injections.adguard.org,DIRECT
  - DOMAIN,local.adguard.org,DIRECT
  - DOMAIN-SUFFIX,local,DIRECT
  - IP-CIDR,${PUBLIC_IP}/32,DIRECT,no-resolve
  - IP-CIDR,127.0.0.0/8,DIRECT
  - IP-CIDR,10.0.0.0/8,DIRECT
  - IP-CIDR,172.16.0.0/12,DIRECT
  - IP-CIDR,192.168.0.0/16,DIRECT
  - IP-CIDR,100.64.0.0/10,DIRECT
  - IP-CIDR,224.0.0.0/4,DIRECT
  - IP-CIDR6,fe80::/10,DIRECT
  - DOMAIN-SUFFIX,accounts.google.com,AntLink
  - DOMAIN-SUFFIX,docs.google.com,AntLink
  - DOMAIN-SUFFIX,drive.google.com,AntLink
  - DOMAIN-SUFFIX,meet.google.com,AntLink
  - DOMAIN-SUFFIX,mail.google.com,AntLink
  - DOMAIN-SUFFIX,calendar.google.com,AntLink
  - DOMAIN-SUFFIX,photos.google.com,AntLink
  - DOMAIN-SUFFIX,play.google.com,AntLink
  - DOMAIN-SUFFIX,one.google.com,AntLink
  - DOMAIN,dns.google,AntLink
  - DOMAIN,dns.google.com,AntLink
  - DOMAIN,mtalk.google.com,AntLink
  - DOMAIN-SUFFIX,services.googleapis.cn,AntLink
  - DOMAIN-SUFFIX,xn--ngstr-lra8j.com,AntLink
  - DOMAIN-SUFFIX,1e100.net,AntLink
  - DOMAIN-SUFFIX,g.co,AntLink
  - DOMAIN-SUFFIX,ggpht.com,AntLink
  - DOMAIN-SUFFIX,google.com,AntLink
  - DOMAIN-SUFFIX,googleapis.com,AntLink
  - DOMAIN-SUFFIX,googleapis.cn,AntLink
  - DOMAIN-SUFFIX,gstatic.com,AntLink
  - DOMAIN-SUFFIX,gstatic.cn,AntLink
  - DOMAIN-SUFFIX,gvt0.com,AntLink
  - DOMAIN-SUFFIX,gvt1.com,AntLink
  - DOMAIN-SUFFIX,gvt2.com,AntLink
  - DOMAIN-SUFFIX,gvt3.com,AntLink
  - DOMAIN-SUFFIX,youtu.be,AntLink
  - DOMAIN-SUFFIX,youtube.com,AntLink
  - DOMAIN-SUFFIX,ytimg.com,AntLink
  - DOMAIN-SUFFIX,googlevideo.com,AntLink
  - DOMAIN-KEYWORD,gmail,AntLink
  - DOMAIN-KEYWORD,google,AntLink
  - DOMAIN-KEYWORD,youtube,AntLink
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
  - DOMAIN,ai.google.dev,AntLink
  - DOMAIN-SUFFIX,aistudio.google.com,AntLink
  - DOMAIN-SUFFIX,bard.google.com,AntLink
  - DOMAIN-SUFFIX,gemini.google.com,AntLink
  - DOMAIN-SUFFIX,notebooklm.google,AntLink
  - DOMAIN-SUFFIX,deepmind.com,AntLink
  - DOMAIN-SUFFIX,deepmind.google,AntLink
  - DOMAIN-KEYWORD,generativelanguage,AntLink
  - DOMAIN-SUFFIX,perplexity.ai,AntLink
  - DOMAIN-SUFFIX,perplexity.com,AntLink
  - DOMAIN-SUFFIX,pplx.ai,AntLink
  - DOMAIN-SUFFIX,x.ai,AntLink
  - DOMAIN-SUFFIX,grok.com,AntLink
  - DOMAIN-SUFFIX,poe.com,AntLink
  - DOMAIN-SUFFIX,huggingface.co,AntLink
  - DOMAIN-SUFFIX,replicate.com,AntLink
  - DOMAIN-SUFFIX,openrouter.ai,AntLink
  - DOMAIN-SUFFIX,together.ai,AntLink
  - DOMAIN-SUFFIX,groq.com,AntLink
  - DOMAIN-SUFFIX,cohere.com,AntLink
  - DOMAIN-SUFFIX,mistral.ai,AntLink
  - DOMAIN-SUFFIX,githubcopilot.com,AntLink
  - DOMAIN-SUFFIX,copilot.microsoft.com,AntLink
  - DOMAIN-SUFFIX,cursor.com,AntLink
  - DOMAIN-SUFFIX,cursor.sh,AntLink
  - DOMAIN-SUFFIX,windsurf.com,AntLink
  - DOMAIN-SUFFIX,codeium.com,AntLink
  - DOMAIN-SUFFIX,midjourney.com,AntLink
  - DOMAIN-SUFFIX,discord.com,AntLink
  - DOMAIN-SUFFIX,discord.gg,AntLink
  - DOMAIN-SUFFIX,discordapp.com,AntLink
  - DOMAIN-SUFFIX,linkedin.com,AntLink
  - DOMAIN-SUFFIX,licdn.com,AntLink
  - DOMAIN-SUFFIX,telegram.org,AntLink
  - DOMAIN-SUFFIX,telegram.me,AntLink
  - DOMAIN-SUFFIX,t.me,AntLink
  - DOMAIN-SUFFIX,telegra.ph,AntLink
  - DOMAIN-SUFFIX,telesco.pe,AntLink
  - DOMAIN-SUFFIX,tdesktop.com,AntLink
  - DOMAIN-SUFFIX,telegram-cdn.org,AntLink
  - DOMAIN-SUFFIX,telegram.dog,AntLink
  - DOMAIN-SUFFIX,tx.me,AntLink
  - DOMAIN-KEYWORD,telegram,AntLink
  - IP-CIDR,91.105.192.0/23,AntLink,no-resolve
  - IP-CIDR,91.108.4.0/22,AntLink,no-resolve
  - IP-CIDR,91.108.8.0/21,AntLink,no-resolve
  - IP-CIDR,91.108.16.0/21,AntLink,no-resolve
  - IP-CIDR,91.108.56.0/22,AntLink,no-resolve
  - IP-CIDR,95.161.64.0/20,AntLink,no-resolve
  - IP-CIDR,149.154.160.0/20,AntLink,no-resolve
  - IP-CIDR,185.76.151.0/24,AntLink,no-resolve
  - IP-CIDR6,2001:b28:f23c::/47,AntLink,no-resolve
  - IP-CIDR6,2001:b28:f23f::/48,AntLink,no-resolve
  - IP-CIDR6,2001:67c:4e8::/48,AntLink,no-resolve
  - IP-CIDR6,2a0a:f280::/32,AntLink,no-resolve
  - DOMAIN-SUFFIX,appsflyer.com,REJECT
  - DOMAIN-SUFFIX,doubleclick.net,REJECT
  - DOMAIN-SUFFIX,mmstat.com,REJECT
  - DOMAIN-SUFFIX,vungle.com,REJECT
  - DOMAIN-KEYWORD,adservice,REJECT
  - DOMAIN-KEYWORD,adwords,REJECT
  - DOMAIN-KEYWORD,adsage,REJECT
  - DOMAIN-KEYWORD,admaster,REJECT
  - DOMAIN-KEYWORD,umeng,REJECT
  - DOMAIN-SUFFIX,cn,DIRECT
  - GEOIP,CN,DIRECT
  - MATCH,AntLink
EOF

cat >/opt/v2ray-sub/server.py <<'EOF'
#!/usr/bin/env python3
import json
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT_DIR = Path(os.environ.get("V2RAY_SUB_ROOT", "/opt/v2ray-sub"))
HOST = os.environ.get("V2RAY_SUB_HOST", "0.0.0.0")
PORT = int(os.environ.get("V2RAY_SUB_PORT", "8088"))
ACCESS_LOG_PATH = Path(os.environ.get("V2RAY_SUB_ACCESS_LOG", str(ROOT_DIR / "access.jsonl")))
DENY_ROOT_CLASH = os.environ.get("V2RAY_SUB_DENY_ROOT_CLASH", "true").lower() not in {"0", "false", "no"}

def now_iso():
  return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def client_ip(handler):
  forwarded = handler.headers.get("X-Forwarded-For", "").strip()
  if forwarded:
    return forwarded.split(",", 1)[0].strip()
  return handler.client_address[0]

def write_access(handler, status, path):
  ACCESS_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
  entry = {
    "time": now_iso(),
    "ip": client_ip(handler),
    "status": status,
    "path": path,
    "user_agent": handler.headers.get("User-Agent", ""),
  }
  with ACCESS_LOG_PATH.open("a", encoding="utf-8") as handle:
    handle.write(json.dumps(entry, ensure_ascii=True) + "\n")

def resolve_path(request_path):
  cleaned = unquote(urlparse(request_path).path)
  if cleaned in {"", "/"}:
    return None
  if DENY_ROOT_CLASH and cleaned == "/clash.yaml":
    return None
  if cleaned == "/healthz":
    return ROOT_DIR / ".healthz"
  relative = cleaned.lstrip("/")
  candidate = (ROOT_DIR / relative).resolve()
  try:
    candidate.relative_to(ROOT_DIR.resolve())
  except ValueError:
    return None
  if not candidate.is_file():
    return None
  return candidate

class Handler(BaseHTTPRequestHandler):
  def handle_request(self, send_body):
    path = urlparse(self.path).path
    if path == "/healthz":
      body = b"ok\n"
      self.send_response(200)
      self.send_header("Content-Type", "text/plain; charset=utf-8")
      self.send_header("Content-Length", str(len(body)))
      self.send_header("Cache-Control", "no-store")
      self.end_headers()
      if send_body:
        self.wfile.write(body)
      write_access(self, 200, path)
      return
    if DENY_ROOT_CLASH and path == "/clash.yaml":
      body = b"Direct /clash.yaml is disabled. Use a per-user subscription URL.\n"
      self.send_response(403)
      self.send_header("Content-Type", "text/plain; charset=utf-8")
      self.send_header("Content-Length", str(len(body)))
      self.send_header("Cache-Control", "no-store")
      self.end_headers()
      if send_body:
        self.wfile.write(body)
      write_access(self, 403, path)
      return
    file_path = resolve_path(self.path)
    if file_path is None:
      body = b"Not found\n"
      self.send_response(404)
      self.send_header("Content-Type", "text/plain; charset=utf-8")
      self.send_header("Content-Length", str(len(body)))
      self.send_header("Cache-Control", "no-store")
      self.end_headers()
      if send_body:
        self.wfile.write(body)
      write_access(self, 404, path)
      return
    body = file_path.read_bytes()
    self.send_response(200)
    self.send_header("Content-Type", "application/octet-stream")
    self.send_header("Content-Length", str(len(body)))
    self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
    self.send_header("Pragma", "no-cache")
    self.send_header("Expires", "0")
    self.end_headers()
    if send_body:
      self.wfile.write(body)
    write_access(self, 200, path)

  def do_GET(self):
    self.handle_request(True)

  def do_HEAD(self):
    self.handle_request(False)

  def log_message(self, format, *args):
    return

ROOT_DIR.mkdir(parents=True, exist_ok=True)
HTTPServer((HOST, PORT), Handler).serve_forever()
EOF
chmod +x /opt/v2ray-sub/server.py

cat >/etc/systemd/system/v2ray-sub.service <<EOF
[Unit]
Description=Tracked HTTP server for Clash subscription
After=network.target

[Service]
WorkingDirectory=/opt/v2ray-sub
Environment=V2RAY_SUB_ROOT=/opt/v2ray-sub
Environment=V2RAY_SUB_HOST=0.0.0.0
Environment=V2RAY_SUB_PORT=${SUB_PORT}
Environment=V2RAY_SUB_DENY_ROOT_CLASH=true
ExecStart=/usr/bin/python3 /opt/v2ray-sub/server.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now v2ray.service
systemctl enable --now v2ray-sub.service

VMESS_JSON="$(printf '{"v":"2","ps":"AntLink-VPS","add":"%s","port":"%s","id":"%s","aid":"0","scy":"auto","net":"ws","type":"none","host":"","path":"%s","tls":""}' "$PUBLIC_IP" "$V2RAY_PORT" "$UUID" "$WS_PATH")"
VMESS_LINK="vmess://$(printf '%s' "$VMESS_JSON" | base64 | tr -d '\n')"

echo
echo "========== DEPLOY SUCCESS =========="
echo "Server IP: ${PUBLIC_IP}"
echo "Port: ${V2RAY_PORT}"
echo "UUID: ${UUID}"
echo "Network: ws"
echo "Path: ${WS_PATH}"
echo "TLS: false"
echo "Subscription URL: http://${PUBLIC_IP}:${SUB_PORT}/clash.yaml"
echo "Config file: /etc/v2ray/config.json"
echo "Subscription file: /opt/v2ray-sub/clash.yaml"
echo
echo "Service status:"
systemctl --no-pager --full status v2ray.service | sed -n '1,8p'
systemctl --no-pager --full status v2ray-sub.service | sed -n '1,8p'
echo
echo "VMess Link:"
echo "${VMESS_LINK}"
echo "===================================="
