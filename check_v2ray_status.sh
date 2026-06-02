#!/usr/bin/env bash

set -u

SERVICE_NAME="v2ray"
LOG_LINES=500

echo "=================================================="
echo " V2Ray Status Check"
echo " Time: $(date)"
echo " Host: $(hostname)"
echo "=================================================="
echo

echo "========== 1. System Basic Status =========="
echo "[Uptime]"
uptime
echo

echo "[Memory]"
free -h
echo

echo "[Disk]"
df -h /
echo

echo "========== 2. Service Status =========="
if systemctl list-unit-files | grep -q "^${SERVICE_NAME}.service"; then
    systemctl status "$SERVICE_NAME" --no-pager
else
    echo "Service ${SERVICE_NAME}.service not found."
fi
echo

echo "========== 3. Failed Systemd Units =========="
systemctl --failed --no-pager
echo

echo "========== 4. V2Ray Process =========="
ps aux | grep -E '[v]2ray|[x]ray' || echo "No v2ray/xray process found."
echo

echo "========== 5. Listening Ports =========="
echo "All listening TCP/UDP ports related to v2ray/xray or common ports:"
ss -lntup | grep -Ei 'v2ray|xray|:80|:443|:8088|:8443' || echo "No matching listening ports found."
echo

echo "========== 6. Current Established Connections =========="
echo "Current established TCP connections related to common service ports:"
ss -ntp state established | grep -Ei 'v2ray|xray|:80|:443|:8088|:8443' || echo "No matching established connections found."
echo

echo "========== 7. Unique Remote IPs From Current Connections =========="
ss -ntp state established \
  | grep -Ei 'v2ray|xray|:80|:443|:8088|:8443' \
  | awk '{print $5}' \
  | sed 's/^\[//; s/\]//' \
  | sed 's/:[0-9]*$//' \
  | sort \
  | uniq -c \
  | sort -nr || true
echo

echo "========== 8. Recent V2Ray Logs =========="
journalctl -u "$SERVICE_NAME" -n "$LOG_LINES" --no-pager
echo

echo "========== 9. Recent Accepted Connections From Logs =========="
journalctl -u "$SERVICE_NAME" -n "$LOG_LINES" --no-pager \
  | grep -i "accepted" || echo "No accepted records found in recent logs."
echo

echo "========== 10. Unique Client IPs From Accepted Logs =========="
journalctl -u "$SERVICE_NAME" -n "$LOG_LINES" --no-pager \
  | grep -i "accepted" \
  | grep -Eo '([0-9]{1,3}\.){3}[0-9]{1,3}:[0-9]+' \
  | cut -d: -f1 \
  | sort \
  | uniq -c \
  | sort -nr || true
echo

echo "========== 11. Recent Rejected / Error Logs =========="
journalctl -u "$SERVICE_NAME" -n "$LOG_LINES" --no-pager \
  | grep -Ei "rejected|failed|error|timeout|invalid|warning" || echo "No obvious rejected/error/warning records found."
echo

echo "========== 12. YAML Endpoint Check =========="
if command -v curl >/dev/null 2>&1; then
    curl -I --connect-timeout 5 http://127.0.0.1:8088/clash.yaml || echo "Local YAML endpoint check failed."
else
    echo "curl not installed."
fi
echo

echo "=================================================="
echo " Check complete."
echo "=================================================="