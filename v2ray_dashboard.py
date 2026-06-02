#!/usr/bin/env python3
import json
import os
import socket
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse


PORT = int(os.environ.get("V2RAY_DASHBOARD_PORT", "8090"))
V2RAY_PORT = int(os.environ.get("V2RAY_PORT", "443"))
STATE_PATH = Path(os.environ.get("V2RAY_DASHBOARD_STATE", "/var/lib/v2ray-dashboard/state.json"))
HOST = os.environ.get("V2RAY_DASHBOARD_HOST", "0.0.0.0")
SUB_URL = os.environ.get("V2RAY_SUB_URL", "")


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run_command(cmd: list[str]) -> str:
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
    except Exception:
        return ""


def systemd_active(service_name: str) -> str:
    out = run_command(["systemctl", "is-active", service_name]).strip()
    return out or "unknown"


def parse_host_port(value: str) -> tuple[str, str]:
    value = value.strip()
    if value.startswith("[") and "]:" in value:
        host, port = value[1:].rsplit("]:", 1)
        return host, port
    if ":" in value:
        host, port = value.rsplit(":", 1)
        return host, port
    return value, ""


def get_active_connections() -> list[dict]:
    output = run_command(["ss", "-nt", "state", "established"])
    rows = []
    for line in output.splitlines():
        if f":{V2RAY_PORT}" not in line:
            continue
        parts = line.split()
        if len(parts) < 5:
            continue
        local_addr = parts[3]
        remote_addr = parts[4]
        local_host, local_port = parse_host_port(local_addr)
        if local_port != str(V2RAY_PORT):
            continue
        remote_host, remote_port = parse_host_port(remote_addr)
        if not remote_host:
            continue
        family = "ipv6" if ":" in remote_host else "ipv4"
        rows.append(
            {
                "ip": remote_host,
                "port": remote_port,
                "family": family,
            }
        )
    return rows


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {"devices": {}}
    try:
        return json.loads(STATE_PATH.read_text())
    except Exception:
        return {"devices": {}}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True))


def update_seen_devices(active_rows: list[dict]) -> dict:
    state = load_state()
    devices = state.setdefault("devices", {})
    current_time = now_iso()
    for row in active_rows:
        device = devices.setdefault(
            row["ip"],
            {
                "first_seen": current_time,
                "last_seen": current_time,
                "hits": 0,
                "family": row["family"],
            },
        )
        device["last_seen"] = current_time
        device["hits"] = int(device.get("hits", 0)) + 1
        device["family"] = row["family"]
    save_state(state)
    return state


def build_snapshot() -> dict:
    active_rows = get_active_connections()
    state = update_seen_devices(active_rows)
    counts = Counter(row["ip"] for row in active_rows)
    ports = defaultdict(set)
    families = {}
    for row in active_rows:
        ports[row["ip"]].add(row["port"])
        families[row["ip"]] = row["family"]

    active_devices = [
        {
            "ip": ip,
            "connections": counts[ip],
            "ports": sorted(ports[ip]),
            "family": families.get(ip, ""),
        }
        for ip in sorted(counts)
    ]

    seen_devices = []
    for ip, item in state.get("devices", {}).items():
        seen_devices.append(
            {
                "ip": ip,
                "first_seen": item.get("first_seen", ""),
                "last_seen": item.get("last_seen", ""),
                "hits": int(item.get("hits", 0)),
                "family": item.get("family", ""),
            }
        )
    seen_devices.sort(key=lambda item: item["last_seen"], reverse=True)

    return {
        "updated_at": now_iso(),
        "host": socket.gethostname(),
        "v2ray_service": systemd_active("v2ray.service"),
        "subscription_service": systemd_active("v2ray-sub.service"),
        "subscription_url": SUB_URL,
        "v2ray_port": V2RAY_PORT,
        "active_count": len(active_devices),
        "seen_count": len(seen_devices),
        "active_devices": active_devices,
        "seen_devices": seen_devices,
    }


HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>V2Ray Dashboard</title>
  <style>
    :root {
      --bg: #0b1020;
      --panel: #131a2d;
      --muted: #8da2c0;
      --text: #eef4ff;
      --accent: #57b2ff;
      --ok: #42c37d;
      --warn: #f3b63f;
      --bad: #ff6b6b;
      --line: rgba(255,255,255,0.08);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(87,178,255,0.18), transparent 28%),
        radial-gradient(circle at top right, rgba(66,195,125,0.12), transparent 24%),
        var(--bg);
    }
    .wrap { max-width: 1180px; margin: 0 auto; padding: 28px 20px 40px; }
    h1 { margin: 0 0 8px; font-size: 32px; }
    .sub { color: var(--muted); margin-bottom: 20px; }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 14px;
      margin-bottom: 18px;
    }
    .card, .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 16px;
      box-shadow: 0 16px 40px rgba(0,0,0,0.22);
    }
    .card { padding: 18px; }
    .label { color: var(--muted); font-size: 13px; margin-bottom: 8px; }
    .value { font-size: 28px; font-weight: 700; }
    .status.ok { color: var(--ok); }
    .status.bad { color: var(--bad); }
    .panel { overflow: hidden; margin-top: 16px; }
    .panel h2 {
      margin: 0;
      padding: 16px 18px;
      border-bottom: 1px solid var(--line);
      font-size: 18px;
    }
    table { width: 100%; border-collapse: collapse; }
    th, td {
      padding: 12px 18px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      font-size: 14px;
    }
    th { color: var(--muted); font-weight: 600; }
    tr:last-child td { border-bottom: none; }
    code {
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      background: rgba(255,255,255,0.05);
      padding: 2px 6px;
      border-radius: 6px;
    }
    .toolbar {
      display: flex;
      gap: 10px;
      align-items: center;
      flex-wrap: wrap;
      margin: 10px 0 4px;
      color: var(--muted);
      font-size: 13px;
    }
    .badge {
      display: inline-block;
      padding: 4px 8px;
      border-radius: 999px;
      background: rgba(255,255,255,0.06);
      border: 1px solid var(--line);
    }
    .empty { padding: 18px; color: var(--muted); }
  </style>
</head>
<body>
  <div class="wrap">
    <h1>V2Ray Dashboard</h1>
    <div class="sub">This dashboard treats unique client IPs as approximate devices. One IP can represent more than one real device.</div>
    <div class="grid" id="cards"></div>
    <div class="toolbar" id="toolbar"></div>
    <div class="panel">
      <h2>Active Devices</h2>
      <div id="activeTable"></div>
    </div>
    <div class="panel">
      <h2>Seen Devices</h2>
      <div id="seenTable"></div>
    </div>
  </div>
  <script>
    function statusClass(value) {
      return value === "active" ? "ok" : "bad";
    }

    function renderTable(rows, columns) {
      if (!rows.length) return '<div class="empty">No data yet.</div>';
      const head = columns.map(c => `<th>${c.label}</th>`).join('');
      const body = rows.map(row => {
        return '<tr>' + columns.map(c => `<td>${c.render(row)}</td>`).join('') + '</tr>';
      }).join('');
      return `<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
    }

    async function loadData() {
      const res = await fetch('/api/status');
      const data = await res.json();

      document.getElementById('cards').innerHTML = `
        <div class="card"><div class="label">Host</div><div class="value" style="font-size:20px">${data.host}</div></div>
        <div class="card"><div class="label">V2Ray</div><div class="value status ${statusClass(data.v2ray_service)}">${data.v2ray_service}</div></div>
        <div class="card"><div class="label">Subscription</div><div class="value status ${statusClass(data.subscription_service)}">${data.subscription_service}</div></div>
        <div class="card"><div class="label">Active Devices</div><div class="value">${data.active_count}</div></div>
        <div class="card"><div class="label">Seen Devices</div><div class="value">${data.seen_count}</div></div>
        <div class="card"><div class="label">V2Ray Port</div><div class="value">${data.v2ray_port}</div></div>
      `;

      document.getElementById('toolbar').innerHTML = `
        <span class="badge">Updated: ${data.updated_at}</span>
        ${data.subscription_url ? `<span class="badge">Subscription: <code>${data.subscription_url}</code></span>` : ''}
      `;

      document.getElementById('activeTable').innerHTML = renderTable(data.active_devices, [
        { label: 'IP', render: row => `<code>${row.ip}</code>` },
        { label: 'Family', render: row => row.family },
        { label: 'Connections', render: row => row.connections },
        { label: 'Remote Ports', render: row => row.ports.map(p => `<code>${p}</code>`).join(' ') }
      ]);

      document.getElementById('seenTable').innerHTML = renderTable(data.seen_devices, [
        { label: 'IP', render: row => `<code>${row.ip}</code>` },
        { label: 'Family', render: row => row.family },
        { label: 'First Seen', render: row => row.first_seen || '-' },
        { label: 'Last Seen', render: row => row.last_seen || '-' },
        { label: 'Hits', render: row => row.hits }
      ]);
    }

    loadData();
    setInterval(loadData, 10000);
  </script>
</body>
</html>
"""


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/status":
            self.respond_json(build_snapshot())
            return
        if path == "/":
            self.respond_html(HTML)
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, format, *args):
        return

    def respond_html(self, body: str):
        content = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def respond_json(self, payload: dict):
        content = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


if __name__ == "__main__":
    server = HTTPServer((HOST, PORT), DashboardHandler)
    print(f"Listening on http://{HOST}:{PORT}")
    server.serve_forever()
