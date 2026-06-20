#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

MANAGER_USERNAME="${V2RAY_MANAGER_USERNAME:-admin}"
MANAGER_PASSWORD="${V2RAY_MANAGER_PASSWORD:-}"
MANAGER_SESSION_SECRET="${V2RAY_MANAGER_SESSION_SECRET:-}"
MANAGER_HOST="${V2RAY_MANAGER_HOST:-0.0.0.0}"
MANAGER_PORT="${V2RAY_MANAGER_PORT:-8091}"
MANAGER_STATE_PATH="${V2RAY_MANAGER_STATE_PATH:-/opt/v2ray-user-manager/state.json}"
V2RAY_API_SERVER="${V2RAY_API_SERVER:-127.0.0.1:10085}"
SERVER_ADDR="${V2RAY_SERVER_ADDR:-}"
SUB_BASE_URL="${V2RAY_SUB_BASE_URL:-}"

if [ -z "$MANAGER_PASSWORD" ]; then
  MANAGER_PASSWORD="$(openssl rand -hex 16)"
fi

if [ -z "$MANAGER_SESSION_SECRET" ]; then
  MANAGER_SESSION_SECRET="$(openssl rand -hex 24)"
fi

echo "==> Deploying base V2Ray service and subscription"
bash "$SCRIPT_DIR/deploy_v2ray_subscription.sh"

if [ -z "$SERVER_ADDR" ]; then
  SERVER_ADDR="$(python3 - <<'PY'
import json
from pathlib import Path
cfg = json.loads(Path('/opt/v2ray-sub/clash.yaml').read_text())
print(cfg['proxies'][0]['server'])
PY
)"
fi

if [ -z "$SUB_BASE_URL" ]; then
  SUB_BASE_URL="http://${SERVER_ADDR}:8088/clash.yaml"
fi

echo "==> Enabling V2Ray stats API"
python3 - <<'PY'
import json
from pathlib import Path

path = Path("/etc/v2ray/config.json")
config = json.loads(path.read_text())
config.setdefault("stats", {})
api = config.setdefault("api", {})
api["tag"] = "api"
api["services"] = list(dict.fromkeys(api.get("services", []) + ["StatsService"]))
policy = config.setdefault("policy", {})
levels = policy.setdefault("levels", {})
level0 = levels.setdefault("0", {})
level0["statsUserUplink"] = True
level0["statsUserDownlink"] = True
system = policy.setdefault("system", {})
system["statsInboundUplink"] = True
system["statsInboundDownlink"] = True
system["statsOutboundUplink"] = True
system["statsOutboundDownlink"] = True

inbounds = config.setdefault("inbounds", [])
for inbound in inbounds:
    if inbound.get("protocol") == "vmess":
        for client in inbound.get("settings", {}).get("clients", []):
            if not client.get("email"):
                client["email"] = client.get("id", "")

if not any(item.get("tag") == "api-in" for item in inbounds):
    inbounds.append(
        {
            "tag": "api-in",
            "listen": "127.0.0.1",
            "port": 10085,
            "protocol": "dokodemo-door",
            "settings": {"address": "127.0.0.1"},
        }
    )

routing = config.setdefault("routing", {})
rules = routing.setdefault("rules", [])
if not any(rule.get("outboundTag") == "api" and "api-in" in rule.get("inboundTag", []) for rule in rules):
    rules.insert(0, {"type": "field", "inboundTag": ["api-in"], "outboundTag": "api"})

path.write_text(json.dumps(config, indent=2))
PY

/usr/local/v2ray/v2ray test -c /etc/v2ray/config.json
systemctl restart v2ray.service

echo "==> Deploying manager"
V2RAY_MANAGER_USERNAME="$MANAGER_USERNAME" \
V2RAY_MANAGER_PASSWORD="$MANAGER_PASSWORD" \
V2RAY_MANAGER_SESSION_SECRET="$MANAGER_SESSION_SECRET" \
V2RAY_MANAGER_HOST="$MANAGER_HOST" \
V2RAY_MANAGER_PORT="$MANAGER_PORT" \
V2RAY_MANAGER_STATE_PATH="$MANAGER_STATE_PATH" \
V2RAY_SERVER_ADDR="$SERVER_ADDR" \
V2RAY_SUB_BASE_URL="$SUB_BASE_URL" \
V2RAY_API_SERVER="$V2RAY_API_SERVER" \
bash "$SCRIPT_DIR/deploy_v2ray_user_manager.sh" "$SCRIPT_DIR/v2ray_user_manager.py"

echo "==> Syncing manager-generated per-user subscriptions"
V2RAY_MANAGER_STATE_PATH="$MANAGER_STATE_PATH" \
V2RAY_CONFIG_PATH="/etc/v2ray/config.json" \
V2RAY_BASE_CLASH_PATH="/opt/v2ray-sub/clash.yaml" \
V2RAY_USERS_DIR="/opt/v2ray-sub/users" \
V2RAY_SERVER_ADDR="$SERVER_ADDR" \
V2RAY_SUB_BASE_URL="$SUB_BASE_URL" \
V2RAY_PORT="443" \
V2RAY_WS_PATH="/v2ray" \
python3 /opt/v2ray-user-manager/app.py sync

echo
echo "Full V2Ray stack deployed."
echo "Subscription URL: $SUB_BASE_URL"
echo "Manager URL: http://${SERVER_ADDR}:${MANAGER_PORT}"
echo "Manager login: $MANAGER_USERNAME"
echo "Manager password: $MANAGER_PASSWORD"
