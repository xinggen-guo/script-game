#!/usr/bin/env python3
import argparse
import base64
import copy
import hashlib
import hmac
import html
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import threading
import time
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse


CONFIG_PATH = Path(os.environ.get("V2RAY_CONFIG_PATH", "/etc/v2ray/config.json"))
BASE_CLASH_PATH = Path(os.environ.get("V2RAY_BASE_CLASH_PATH", "/opt/v2ray-sub/clash.yaml"))
USERS_DIR = Path(os.environ.get("V2RAY_USERS_DIR", "/opt/v2ray-sub/users"))
PROFILE_FILES_DIR = Path(os.environ.get("V2RAY_PROFILE_FILES_DIR", "/opt/v2ray-sub/profiles"))
STATE_PATH = Path(os.environ.get("V2RAY_MANAGER_STATE_PATH", "/opt/v2ray-user-manager/state.json"))
HOST = os.environ.get("V2RAY_MANAGER_HOST", "0.0.0.0")
PORT = int(os.environ.get("V2RAY_MANAGER_PORT", "8091"))
SERVER_ADDR = os.environ.get("V2RAY_SERVER_ADDR", "")
SUB_BASE_URL = os.environ.get("V2RAY_SUB_BASE_URL", "")
VMESS_PORT = int(os.environ.get("V2RAY_PORT", "443"))
WS_PATH = os.environ.get("V2RAY_WS_PATH", "/v2ray")
V2RAY_API_SERVER = os.environ.get("V2RAY_API_SERVER", "127.0.0.1:10085")
MANAGER_USERNAME = os.environ.get("V2RAY_MANAGER_USERNAME", "admin")
MANAGER_PASSWORD = os.environ.get("V2RAY_MANAGER_PASSWORD", "")
SESSION_SECRET = os.environ.get("V2RAY_MANAGER_SESSION_SECRET", MANAGER_PASSWORD or secrets.token_hex(24))
SESSION_COOKIE = "v2ray_manager_session"
SESSION_TTL = int(os.environ.get("V2RAY_MANAGER_SESSION_TTL", "43200"))
V2RAY_SERVICE_NAME = os.environ.get("V2RAY_SERVICE_NAME", "v2ray.service")
RECENT_ACTIVITY_MINUTES = int(os.environ.get("V2RAY_RECENT_ACTIVITY_MINUTES", "5"))
ASYNC_RESTART_DELAY_SECONDS = float(os.environ.get("V2RAY_ASYNC_RESTART_DELAY_SECONDS", "1.0"))


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text())


def save_config(config: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(config, indent=2))


def get_clients(config: dict) -> list[dict]:
    return config["inbounds"][0]["settings"]["clients"]


def sanitize_name(name: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", name.strip())
    safe = safe.strip("-")
    if not safe:
        raise ValueError("name cannot be empty")
    return safe


def detect_server_addr() -> str:
    if SERVER_ADDR:
        return SERVER_ADDR
    config = load_config()
    return config["inbounds"][0].get("listen", "") or "YOUR_SERVER_IP"


def build_vmess_link(server_addr: str, client_uuid: str, name: str) -> str:
    payload = {
        "v": "2",
        "ps": name,
        "add": server_addr,
        "port": str(VMESS_PORT),
        "id": client_uuid,
        "aid": "0",
        "scy": "auto",
        "net": "ws",
        "type": "none",
        "host": "",
        "path": WS_PATH,
        "tls": "",
    }
    encoded = base64.b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode()
    return f"vmess://{encoded}"


def render_user_clash(name: str, client_uuid: str) -> str:
    lines = BASE_CLASH_PATH.read_text().splitlines()
    rendered = []
    in_proxies = False
    first_proxy_name = ""
    first_proxy_rewritten = False
    first_uuid_rewritten = False

    for line in lines:
        stripped = line.strip()

        if stripped == "proxies:":
            in_proxies = True
            rendered.append(line)
            continue

        if in_proxies and re.match(r"^[A-Za-z0-9_-]+:\s*$", line):
            in_proxies = False

        if in_proxies and not first_proxy_rewritten:
            match = re.match(r"^(\s*-\s*name:\s*)(.+?)\s*$", line)
            if match:
                first_proxy_name = match.group(2)
                rendered.append(f"{match.group(1)}{name}")
                first_proxy_rewritten = True
                continue

        if in_proxies and first_proxy_rewritten and not first_uuid_rewritten:
            match = re.match(r"^(\s*uuid:\s*)(.+?)\s*$", line)
            if match:
                rendered.append(f"{match.group(1)}{client_uuid}")
                first_uuid_rewritten = True
                continue

        if first_proxy_name:
            match = re.match(r"^(\s*-\s*)(.+?)\s*$", line)
            if match and match.group(2) == first_proxy_name:
                rendered.append(f"{match.group(1)}{name}")
                continue

        rendered.append(line)

    return "\n".join(rendered) + "\n"


def ensure_user_subscription(name: str, client_uuid: str) -> Path:
    safe_name = sanitize_name(name)
    state = load_state()
    user_dir = USERS_DIR / safe_name
    user_dir.mkdir(parents=True, exist_ok=True)
    clash_path = user_dir / "clash.yaml"
    clash_path.write_text(render_user_clash(name, client_uuid))
    flat_profile_path = get_profile_fs_path(safe_name, state)
    flat_profile_path.parent.mkdir(parents=True, exist_ok=True)
    flat_profile_path.write_text(render_user_clash(name, client_uuid))
    save_state(state)
    return clash_path


def remove_user_subscription(name: str) -> None:
    safe_name = sanitize_name(name)
    state = load_state()
    user_dir = USERS_DIR / safe_name
    if user_dir.exists():
        shutil.rmtree(user_dir)
    flat_profile_path = get_profile_fs_path(safe_name, state)
    if flat_profile_path.exists():
        flat_profile_path.unlink()
    state.setdefault("profiles", {}).pop(safe_name, None)
    save_state(state)


def subscribe_url(name: str, state: dict | None = None) -> str:
    if not SUB_BASE_URL:
        return ""
    base = SUB_BASE_URL.rstrip("/")
    if base.endswith("/clash.yaml"):
        base = base[: -len("/clash.yaml")]
    return f"{base}{get_profile_url_path(name, state)}"


def profile_path(name: str, state: dict | None = None) -> str:
    return get_profile_url_path(name, state)


def list_users() -> list[dict]:
    config = load_config()
    state = load_state()
    server_addr = detect_server_addr()
    users = []
    for client in get_clients(config):
        name = client.get("email") or client["id"]
        users.append(
            {
                "name": name,
                "uuid": client["id"],
                "profile_path": profile_path(name, state),
                "vmess_link": build_vmess_link(server_addr, client["id"], name),
                "subscription_url": subscribe_url(name, state),
            }
        )
    save_state(state)
    return users


def restart_v2ray_service() -> None:
    result = subprocess.run(
        ["systemctl", "restart", V2RAY_SERVICE_NAME],
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or f"failed to restart {V2RAY_SERVICE_NAME}"
        raise RuntimeError(message)

    active = run_command(["systemctl", "is-active", V2RAY_SERVICE_NAME]).strip()
    if active != "active":
        raise RuntimeError(f"{V2RAY_SERVICE_NAME} is not active after restart")


def restart_v2ray_service_async(delay_seconds: float = ASYNC_RESTART_DELAY_SECONDS) -> None:
    def worker():
        if delay_seconds > 0:
            time.sleep(delay_seconds)
        try:
            restart_v2ray_service()
        except Exception:
            return

    threading.Thread(target=worker, daemon=True).start()


def add_user(name: str, restart: bool = True) -> dict:
    safe_name = sanitize_name(name)
    config = load_config()
    clients = get_clients(config)
    for client in clients:
        if (client.get("email") or client["id"]) == safe_name:
            raise ValueError("user already exists")
    client_uuid = str(uuid.uuid4())
    clients.append({"id": client_uuid, "alterId": 0, "email": safe_name})
    save_config(config)
    if restart:
        restart_v2ray_service()
    ensure_user_subscription(safe_name, client_uuid)
    server_addr = detect_server_addr()
    return {
        "name": safe_name,
        "uuid": client_uuid,
        "profile_path": profile_path(safe_name),
        "vmess_link": build_vmess_link(server_addr, client_uuid, safe_name),
        "subscription_url": subscribe_url(safe_name),
    }


def remove_user(name: str, restart: bool = True) -> bool:
    safe_name = sanitize_name(name)
    config = load_config()
    clients = get_clients(config)
    new_clients = [client for client in clients if (client.get("email") or client["id"]) != safe_name]
    if len(new_clients) == len(clients):
        return False
    config["inbounds"][0]["settings"]["clients"] = new_clients
    save_config(config)
    if restart:
        restart_v2ray_service()
    remove_user_subscription(safe_name)
    return True


def sync_users() -> None:
    state = load_state()
    USERS_DIR.mkdir(parents=True, exist_ok=True)
    PROFILE_FILES_DIR.mkdir(parents=True, exist_ok=True)
    config = load_config()
    active_names = set()
    active_profile_paths = set()
    for client in get_clients(config):
        name = client.get("email") or client["id"]
        active_names.add(sanitize_name(name))
        active_profile_paths.add(get_profile_fs_path(name, state).resolve())
        ensure_user_subscription(name, client["id"])
    for path in USERS_DIR.iterdir():
        if path.is_dir() and path.name not in active_names:
            shutil.rmtree(path)
    for path in PROFILE_FILES_DIR.rglob("*.yaml"):
        if path.resolve() not in active_profile_paths:
            path.unlink()
    for stale_name in list(state.setdefault("profiles", {})):
        if stale_name not in active_names:
            del state["profiles"][stale_name]
    save_state(state)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run_command(cmd: list[str]) -> str:
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
    except Exception:
        return ""


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {"traffic": {}, "devices": {}, "profiles": {}}
    try:
        data = json.loads(STATE_PATH.read_text())
    except Exception:
        return {"traffic": {}, "devices": {}, "profiles": {}}
    data.setdefault("traffic", {})
    data.setdefault("devices", {})
    data.setdefault("profiles", {})
    return data


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True))


def build_new_profile_filename(name: str) -> str:
    safe_name = sanitize_name(name)
    digest = hashlib.sha256(safe_name.encode()).hexdigest()[:12]
    return f"{safe_name}-{digest}.yaml"


def get_profile_relative_path(name: str, state: dict | None = None) -> str:
    safe_name = sanitize_name(name)
    working_state = state if state is not None else load_state()
    profiles = working_state.setdefault("profiles", {})
    existing = profiles.get(safe_name, "").strip()
    if existing:
        return existing

    legacy_filename = f"{safe_name}.yaml"
    legacy_path = PROFILE_FILES_DIR / legacy_filename
    if legacy_path.exists():
        relative_path = f"profiles/{legacy_filename}"
    else:
        relative_path = f"profiles/{build_new_profile_filename(safe_name)}"
    profiles[safe_name] = relative_path
    if state is None:
        save_state(working_state)
    return relative_path


def get_profile_fs_path(name: str, state: dict | None = None) -> Path:
    relative_path = get_profile_relative_path(name, state)
    return BASE_CLASH_PATH.parent / relative_path


def get_profile_url_path(name: str, state: dict | None = None) -> str:
    relative_path = get_profile_relative_path(name, state)
    return "/" + "/".join(quote(part) for part in relative_path.split("/"))


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
        parts = line.split()
        if len(parts) < 5:
            continue
        local_host, local_port = parse_host_port(parts[3])
        remote_host, remote_port = parse_host_port(parts[4])
        if local_port != str(VMESS_PORT):
            continue
        if not remote_host or remote_host == SERVER_ADDR:
            continue
        if remote_host.startswith("::ffff:"):
            remote_host = remote_host.replace("::ffff:", "", 1)
        family = "ipv6" if ":" in remote_host else "ipv4"
        rows.append(
            {
                "ip": remote_host,
                "port": remote_port,
                "family": family,
                "send_q": parts[2],
                "recv_q": parts[1],
            }
        )
    return rows


def query_user_traffic() -> dict[str, dict]:
    output = run_command(
        [
            "/usr/local/v2ray/v2ray",
            "api",
            "stats",
            "-server",
            V2RAY_API_SERVER,
            "-json",
            "-regexp",
            r"user>>>.*>>>traffic>>>.*",
        ]
    ).strip()
    if not output:
        return {}
    try:
        payload = json.loads(output)
    except json.JSONDecodeError:
        return {}
    stats = {}
    for item in payload.get("stat", []):
        name = item.get("name", "")
        value = int(item.get("value", 0))
        match = re.match(r"user>>>(.+?)>>>traffic>>>(uplink|downlink)$", name)
        if not match:
            continue
        user_name, direction = match.groups()
        entry = stats.setdefault(user_name, {"uplink": 0, "downlink": 0, "total": 0})
        entry[direction] = value
        entry["total"] = entry.get("uplink", 0) + entry.get("downlink", 0)
    return stats


def get_recent_activity(minutes: int = RECENT_ACTIVITY_MINUTES) -> dict:
    output = run_command(
        [
            "journalctl",
            "-u",
            V2RAY_SERVICE_NAME,
            "--since",
            f"{minutes} minutes ago",
            "--no-pager",
        ]
    )
    entries = []
    user_connections = Counter()
    user_devices = defaultdict(set)
    device_connections = Counter()
    for line in output.splitlines():
        if " accepted " not in line:
            continue
        matches = re.findall(r"((?:\d{1,3}\.){3}\d{1,3}|\[[0-9a-fA-F:]+\]):(\d+)", line)
        email_match = re.search(r"email:\s+(.+?)\s*$", line)
        if not matches or not email_match:
            continue
        ip = matches[0][0].strip("[]")
        if ip.startswith("::ffff:"):
            ip = ip.replace("::ffff:", "", 1)
        user = email_match.group(1).strip()
        user_connections[user] += 1
        user_devices[user].add(ip)
        device_connections[ip] += 1
        entries.append({"user": user, "ip": ip, "raw": line})
    return {
        "minutes": minutes,
        "request_count": len(entries),
        "user_count": len(user_connections),
        "device_count": len(device_connections),
        "user_connections": dict(user_connections),
        "user_devices": {user: sorted(values) for user, values in user_devices.items()},
        "device_connections": dict(device_connections),
    }


def format_bytes(value: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(value)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{value} B"


def build_snapshot() -> dict:
    state = load_state()
    active_rows = get_active_connections()
    recent = get_recent_activity()
    counts = Counter(row["ip"] for row in active_rows)
    ports = defaultdict(set)
    send_q = defaultdict(int)
    recv_q = defaultdict(int)
    family = {}
    for row in active_rows:
        ports[row["ip"]].add(row["port"])
        send_q[row["ip"]] += int(row["send_q"])
        recv_q[row["ip"]] += int(row["recv_q"])
        family[row["ip"]] = row["family"]
        device = state["devices"].setdefault(
            row["ip"],
            {
                "first_seen": now_iso(),
                "last_seen": now_iso(),
                "family": row["family"],
                "hits": 0,
            },
        )
        device["last_seen"] = now_iso()
        device["family"] = row["family"]
        device["hits"] = int(device.get("hits", 0)) + 1

    active_devices = [
        {
            "ip": ip,
            "connections": counts[ip],
            "ports": sorted(ports[ip]),
            "send_q": send_q[ip],
            "recv_q": recv_q[ip],
            "family": family.get(ip, ""),
        }
        for ip in sorted(counts)
    ]
    runtime_traffic = query_user_traffic()
    traffic = {}
    user_presence = {}
    current_time = now_iso()
    for row in list_users():
        name = row["name"]
        runtime = runtime_traffic.get(name, {})
        current_up = int(runtime.get("uplink", 0))
        current_down = int(runtime.get("downlink", 0))
        entry = state["traffic"].setdefault(
            name,
            {
                "uplink_total": 0,
                "downlink_total": 0,
                "last_runtime_uplink": 0,
                "last_runtime_downlink": 0,
                "first_seen": current_time,
                "last_seen": "",
            },
        )
        prev_up = int(entry.get("last_runtime_uplink", 0))
        prev_down = int(entry.get("last_runtime_downlink", 0))
        delta_up = current_up - prev_up if current_up >= prev_up else current_up
        delta_down = current_down - prev_down if current_down >= prev_down else current_down
        if delta_up < 0:
            delta_up = 0
        if delta_down < 0:
            delta_down = 0
        entry["uplink_total"] = int(entry.get("uplink_total", 0)) + delta_up
        entry["downlink_total"] = int(entry.get("downlink_total", 0)) + delta_down
        entry["last_runtime_uplink"] = current_up
        entry["last_runtime_downlink"] = current_down
        if delta_up > 0 or delta_down > 0:
            entry["last_seen"] = current_time
        traffic[name] = {
            "uplink": int(entry["uplink_total"]),
            "downlink": int(entry["downlink_total"]),
            "total": int(entry["uplink_total"]) + int(entry["downlink_total"]),
            "last_seen": entry.get("last_seen", ""),
            "first_seen": entry.get("first_seen", ""),
            "runtime_uplink": current_up,
            "runtime_downlink": current_down,
        }
        recent_ips = recent.get("user_devices", {}).get(name, [])
        active_ip_set = {item["ip"] for item in active_devices}
        user_presence[name] = {
            "device_count": len(recent_ips),
            "active_device_count": sum(1 for ip in recent_ips if ip in active_ip_set),
            "request_count": int(recent.get("user_connections", {}).get(name, 0)),
            "ips": recent_ips,
        }
    for stale_name in list(state["traffic"]):
        if stale_name not in {row["name"] for row in list_users()}:
            del state["traffic"][stale_name]
    save_state(state)
    return {
        "updated_at": current_time,
        "host": socket.gethostname(),
        "active_count": len(active_devices),
        "active_connections": len(active_rows),
        "active_devices": active_devices,
        "recent_activity": recent,
        "user_presence": user_presence,
        "traffic_by_user": traffic,
        "traffic_enabled": bool(traffic),
    }


def build_rows(users: list[dict], traffic: dict[str, dict], user_presence: dict[str, dict]) -> str:
    return "".join(
        "<tr>"
        f"<td><code>{row['profile_path']}</code></td>"
        f"<td><code>{row['uuid']}</code></td>"
        f"<td>{user_presence.get(row['name'], {}).get('device_count', 0)}</td>"
        f"<td>{format_bytes(traffic.get(row['name'], {}).get('uplink', 0))}</td>"
        f"<td>{format_bytes(traffic.get(row['name'], {}).get('downlink', 0))}</td>"
        f"<td>{format_bytes(traffic.get(row['name'], {}).get('total', 0))}</td>"
        f"<td>{traffic.get(row['name'], {}).get('last_seen', '') or '-'}</td>"
        f"<td><textarea readonly>{row['vmess_link']}</textarea></td>"
        f"<td><textarea readonly>{row['subscription_url']}</textarea></td>"
        f"<td><form method='post' action='/remove'><input type='hidden' name='name' value='{row['name']}'><button>Remove</button></form></td>"
        "</tr>"
        for row in users
    ) or "<tr><td colspan='10'>No users yet.</td></tr>"


def build_active_summary(active_ip_rows: list[dict]) -> str:
    return (
        "".join(
            "<tr>"
            f"<td><code>{item['ip']}</code></td>"
            f"<td>{item['connections']}</td>"
            f"<td>{', '.join(item['ports']) or '-'}</td>"
            f"<td>{item['recv_q']}</td>"
            f"<td>{item['send_q']}</td>"
            "</tr>"
            for item in active_ip_rows
        )
        or "<tr><td colspan='5'>No active client connections right now.</td></tr>"
    )


def build_session_value() -> str:
    issued_at = str(int(time.time()))
    payload = f"{MANAGER_USERNAME}:{issued_at}"
    signature = hmac.new(SESSION_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{issued_at}.{signature}"


def is_authorized(headers) -> bool:
    cookie_header = headers.get("Cookie", "")
    cookies = {}
    for part in cookie_header.split(";"):
        if "=" not in part:
            continue
        key, value = part.strip().split("=", 1)
        cookies[key] = value
    cookie_value = cookies.get(SESSION_COOKIE, "")
    if "." not in cookie_value:
        return False
    issued_at, signature = cookie_value.split(".", 1)
    if not issued_at.isdigit():
        return False
    if time.time() - int(issued_at) > SESSION_TTL:
        return False
    payload = f"{MANAGER_USERNAME}:{issued_at}"
    expected = hmac.new(SESSION_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)


def login_page(message: str = "") -> str:
    safe_message = html.escape(message)
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>V2Ray Manager Login</title>
  <style>
    body {{ font-family: ui-sans-serif, -apple-system, sans-serif; margin: 0; min-height: 100vh; display: grid; place-items: center; background: linear-gradient(135deg, #020617, #0f172a 45%, #1e293b); color: #e2e8f0; }}
    .card {{ width: min(420px, calc(100vw - 32px)); background: rgba(15, 23, 42, 0.92); border: 1px solid #334155; border-radius: 18px; padding: 24px; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.35); }}
    h1 {{ margin-top: 0; font-size: 28px; }}
    p {{ color: #94a3b8; }}
    label {{ display: block; margin: 14px 0 6px; color: #cbd5e1; }}
    input {{ width: 100%; box-sizing: border-box; padding: 12px; border-radius: 10px; border: 1px solid #334155; background: #020617; color: #e2e8f0; }}
    button {{ width: 100%; margin-top: 18px; padding: 12px; border: 0; border-radius: 10px; background: #2563eb; color: #fff; font-weight: 600; cursor: pointer; }}
    .msg {{ min-height: 24px; color: #fca5a5; }}
  </style>
</head>
<body>
  <form class="card" method="post" action="/login">
    <h1>Manager Login</h1>
    <p>Sign in to manage V2Ray users and subscriptions.</p>
    <div class="msg">{safe_message}</div>
    <label>Username</label>
    <input name="username" autocomplete="username" required>
    <label>Password</label>
    <input type="password" name="password" autocomplete="current-password" required>
    <button type="submit">Login</button>
  </form>
</body>
</html>"""


def action_result_page(title: str, message: str, refresh_seconds: int = 6) -> str:
    safe_title = html.escape(title)
    safe_message = html.escape(message)
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="{refresh_seconds};url=/">
  <title>{safe_title}</title>
  <style>
    body {{ font-family: ui-sans-serif, -apple-system, sans-serif; margin: 0; min-height: 100vh; display: grid; place-items: center; background: linear-gradient(135deg, #020617, #0f172a 45%, #1e293b); color: #e2e8f0; }}
    .card {{ width: min(520px, calc(100vw - 32px)); background: rgba(15, 23, 42, 0.94); border: 1px solid #334155; border-radius: 18px; padding: 24px; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.35); }}
    h1 {{ margin: 0 0 10px; font-size: 28px; }}
    p {{ color: #cbd5e1; line-height: 1.5; }}
    .muted {{ color: #94a3b8; }}
    a {{ color: #93c5fd; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>{safe_title}</h1>
    <p>{safe_message}</p>
    <p class="muted">The proxy service is restarting in the background. This page will return to the manager automatically in {refresh_seconds} seconds.</p>
    <p><a href="/">Return now</a></p>
  </div>
</body>
</html>"""


def page(message: str = "") -> str:
    snapshot = build_snapshot()
    traffic = snapshot["traffic_by_user"]
    user_presence = snapshot.get("user_presence", {})
    active_ip_rows = snapshot["active_devices"]
    rows = list_users()
    recent = snapshot["recent_activity"]
    active_summary = build_active_summary(active_ip_rows)
    rows_html = build_rows(rows, traffic, user_presence)
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="3600">
  <title>V2Ray User Manager</title>
  <style>
    body {{ font-family: ui-sans-serif, -apple-system, sans-serif; margin: 0; background: #0f172a; color: #e2e8f0; }}
    .wrap {{ max-width: 1200px; margin: 0 auto; padding: 24px; }}
    .card {{ background: #111827; border: 1px solid #334155; border-radius: 16px; padding: 18px; margin-bottom: 18px; }}
    .stats {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-top: 16px; }}
    .stat {{ background: #0b1220; border: 1px solid #334155; border-radius: 12px; padding: 14px; }}
    .stat-label {{ color: #94a3b8; font-size: 13px; margin-bottom: 6px; }}
    .stat-value {{ font-size: 26px; font-weight: 700; }}
    .stat-note {{ color: #94a3b8; font-size: 12px; margin-top: 4px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ border-bottom: 1px solid #334155; text-align: left; padding: 10px; vertical-align: top; }}
    textarea {{ width: 100%; min-height: 88px; background: #0b1220; color: #cbd5e1; border: 1px solid #334155; border-radius: 8px; }}
    input, button {{ padding: 10px 12px; border-radius: 8px; border: 1px solid #334155; }}
    input {{ background: #0b1220; color: #e2e8f0; }}
    button {{ background: #2563eb; color: white; cursor: pointer; }}
    code {{ background: #0b1220; padding: 2px 6px; border-radius: 6px; }}
    .msg {{ color: #93c5fd; margin-bottom: 12px; }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <div style="display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap;">
        <h1 style="margin:0;">V2Ray User Manager</h1>
        <form method="post" action="/logout" style="margin:0;">
          <button type="submit" style="background:#475569;">Logout</button>
        </form>
      </div>
      {f"<p class='msg'>{message}</p>" if message else ""}
      <form method="post" action="/add">
        <input name="name" placeholder="user name, for example codex-mac" required>
        <button type="submit">Add User</button>
      </form>
      <div class="stats" id="statsGrid">
        <div class="stat"><div class="stat-label">Current Active Devices</div><div class="stat-value">{snapshot['active_count']}</div><div class="stat-note">Live socket snapshot</div></div>
        <div class="stat"><div class="stat-label">Current Active Connections</div><div class="stat-value">{snapshot['active_connections']}</div><div class="stat-note">Live socket snapshot</div></div>
        <div class="stat"><div class="stat-label">Recent Active Users</div><div class="stat-value">{recent['user_count']}</div><div class="stat-note">Last {recent['minutes']} minutes</div></div>
        <div class="stat"><div class="stat-label">Recent Requests</div><div class="stat-value">{recent['request_count']}</div><div class="stat-note">Last {recent['minutes']} minutes</div></div>
        <div class="stat"><div class="stat-label">Traffic Stats</div><div class="stat-value">{"On" if snapshot['traffic_enabled'] else "Off"}</div><div class="stat-note">Per-user totals</div></div>
        <div class="stat"><div class="stat-label">Updated</div><div class="stat-value" style="font-size:15px;">{snapshot['updated_at']}</div><div class="stat-note">Live panel refreshes every 15s</div></div>
      </div>
      <p>Direct root subscription is blocked: <code>{SUB_BASE_URL or 'N/A'}</code></p>
      <p>Per-user subscriptions are generated under <code>/opt/v2ray-sub/profiles/&lt;calculated-path&gt;.yaml</code>. Existing user paths stay unchanged.</p>
      <p>Current active numbers come from the live port `443` socket table. Recent active numbers come from accepted V2Ray requests in the last {recent['minutes']} minutes.</p>
      <p>{"Per-user traffic totals come from the built-in V2Ray stats API." if snapshot['traffic_enabled'] else "Per-user traffic totals are not available yet until the V2Ray stats API is enabled."}</p>
      <p>This page auto-refreshes every hour.</p>
    </div>
    <div class="card">
      <h2>Active Client IPs</h2>
      <table id="activeTable">
        <thead><tr><th>IP</th><th>Connections</th><th>Remote Ports</th><th>Recv-Q</th><th>Send-Q</th></tr></thead>
        <tbody>{active_summary}</tbody>
      </table>
    </div>
    <div class="card">
      <h2>Users</h2>
      <table id="usersTable">
        <thead><tr><th>Path</th><th>UUID</th><th>Devices</th><th>Upload</th><th>Download</th><th>Total</th><th>Last Seen</th><th>VMess Link</th><th>Subscription URL</th><th>Action</th></tr></thead>
        <tbody>{rows_html}</tbody>
      </table>
    </div>
  </div>
  <script>
    function formatBytes(bytes) {{
      const units = ['B', 'KB', 'MB', 'GB', 'TB'];
      let value = Number(bytes || 0);
      let index = 0;
      while (value >= 1024 && index < units.length - 1) {{
        value /= 1024;
        index += 1;
      }}
      return index === 0 ? `${{Math.round(value)}} B` : `${{value.toFixed(1)}} ${{units[index]}}`;
    }}

    function renderStats(snapshot) {{
      const recent = snapshot.recent_activity;
      document.getElementById('statsGrid').innerHTML = `
        <div class="stat"><div class="stat-label">Current Active Devices</div><div class="stat-value">${{snapshot.active_count}}</div><div class="stat-note">Live socket snapshot</div></div>
        <div class="stat"><div class="stat-label">Current Active Connections</div><div class="stat-value">${{snapshot.active_connections}}</div><div class="stat-note">Live socket snapshot</div></div>
        <div class="stat"><div class="stat-label">Recent Active Users</div><div class="stat-value">${{recent.user_count}}</div><div class="stat-note">Last ${{recent.minutes}} minutes</div></div>
        <div class="stat"><div class="stat-label">Recent Requests</div><div class="stat-value">${{recent.request_count}}</div><div class="stat-note">Last ${{recent.minutes}} minutes</div></div>
        <div class="stat"><div class="stat-label">Traffic Stats</div><div class="stat-value">${{snapshot.traffic_enabled ? 'On' : 'Off'}}</div><div class="stat-note">Per-user totals</div></div>
        <div class="stat"><div class="stat-label">Updated</div><div class="stat-value" style="font-size:15px;">${{snapshot.updated_at}}</div><div class="stat-note">Live panel refreshes every 15s</div></div>
      `;
    }}

    function renderActiveTable(snapshot) {{
      const rows = snapshot.active_devices || [];
      const body = rows.length ? rows.map((item) => `
        <tr>
          <td><code>${{item.ip}}</code></td>
          <td>${{item.connections}}</td>
          <td>${{(item.ports || []).join(', ') || '-'}}</td>
          <td>${{item.recv_q}}</td>
          <td>${{item.send_q}}</td>
        </tr>
      `).join('') : `<tr><td colspan="5">No active client connections right now.</td></tr>`;
      document.querySelector('#activeTable tbody').innerHTML = body;
    }}

    function renderUsers(data) {{
      const traffic = data.snapshot.traffic_by_user || {{}};
      const presence = data.snapshot.user_presence || {{}};
      const rows = data.users || [];
      const body = rows.length ? rows.map((row) => `
        <tr>
          <td><code>${{row.profile_path}}</code></td>
          <td><code>${{row.uuid}}</code></td>
          <td>${{presence[row.name]?.device_count || 0}}</td>
          <td>${{formatBytes(traffic[row.name]?.uplink || 0)}}</td>
          <td>${{formatBytes(traffic[row.name]?.downlink || 0)}}</td>
          <td>${{formatBytes(traffic[row.name]?.total || 0)}}</td>
          <td>${{traffic[row.name]?.last_seen || '-'}}</td>
          <td><textarea readonly>${{row.vmess_link}}</textarea></td>
          <td><textarea readonly>${{row.subscription_url}}</textarea></td>
          <td><form method="post" action="/remove"><input type="hidden" name="name" value="${{row.name}}"><button>Remove</button></form></td>
        </tr>
      `).join('') : `<tr><td colspan="10">No users yet.</td></tr>`;
      document.querySelector('#usersTable tbody').innerHTML = body;
    }}

    async function refreshLivePanel() {{
      try {{
        const response = await fetch('/api/users', {{ credentials: 'same-origin' }});
        if (!response.ok) return;
        const data = await response.json();
        renderStats(data.snapshot);
        renderActiveTable(data.snapshot);
        renderUsers(data);
      }} catch (_err) {{
      }}
    }}

    setInterval(refreshLivePanel, 15000);
  </script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/login":
            if is_authorized(self.headers):
                self.redirect("/")
                return
            message = parse_qs(parsed.query).get("message", [""])[0]
            self.respond_html(login_page(message))
            return
        if not is_authorized(self.headers):
            self.redirect("/login?message=Please+login")
            return
        if parsed.path == "/api/users":
            self.respond_json({"users": list_users(), "snapshot": build_snapshot()})
            return
        message = parse_qs(parsed.query).get("message", [""])[0]
        self.respond_html(page(message))

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode()
        form = parse_qs(body)
        if self.path == "/login":
            username = form.get("username", [""])[0]
            password = form.get("password", [""])[0]
            if username == MANAGER_USERNAME and password == MANAGER_PASSWORD:
                self.send_response(303)
                self.send_header("Location", "/")
                self.send_header("Set-Cookie", f"{SESSION_COOKIE}={build_session_value()}; HttpOnly; Path=/; Max-Age={SESSION_TTL}; SameSite=Lax")
                self.end_headers()
                return
            self.redirect("/login?message=Invalid+username+or+password")
            return
        if self.path == "/logout":
            self.send_response(303)
            self.send_header("Location", "/login?message=Logged+out")
            self.send_header("Set-Cookie", f"{SESSION_COOKIE}=deleted; HttpOnly; Path=/; Max-Age=0; SameSite=Lax")
            self.end_headers()
            return
        if not is_authorized(self.headers):
            self.redirect("/login?message=Please+login")
            return
        name = form.get("name", [""])[0]
        try:
            if self.path == "/add":
                user = add_user(name, restart=False)
                restart_v2ray_service_async(delay_seconds=2.5)
                self.respond_html(action_result_page("User Added", f"Added {user['name']} successfully."))
                return
            if self.path == "/remove":
                remove_user(name, restart=False)
                restart_v2ray_service_async(delay_seconds=2.5)
                self.respond_html(action_result_page("User Removed", f"Removed {name} successfully."))
                return
        except Exception as exc:
            self.respond_html(action_result_page("Action Failed", str(exc), refresh_seconds=8))
            return
        self.send_response(400)
        self.end_headers()

    def redirect(self, location: str):
        self.send_response(303)
        self.send_header("Location", location)
        self.end_headers()

    def respond_html(self, html: str):
        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.end_headers()
        self.wfile.write(body)

    def respond_json(self, payload: dict):
        body = json.dumps(payload, indent=2).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


def main():
    parser = argparse.ArgumentParser(description="Manage users for the existing V2Ray VMess service.")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("list")
    add_parser = sub.add_parser("add")
    add_parser.add_argument("name")
    remove_parser = sub.add_parser("remove")
    remove_parser.add_argument("name")
    sub.add_parser("sync")
    sub.add_parser("serve")
    args = parser.parse_args()

    if args.cmd == "list":
        sync_users()
        print(json.dumps({"users": list_users()}, indent=2))
        return
    if args.cmd == "add":
        user = add_user(args.name)
        print(json.dumps(user, indent=2))
        return
    if args.cmd == "remove":
        print("removed" if remove_user(args.name) else "not found")
        return
    if args.cmd == "sync":
        sync_users()
        print("synced")
        return

    if not MANAGER_PASSWORD:
        raise SystemExit("V2RAY_MANAGER_PASSWORD must be set before starting the web manager.")

    sync_users()
    server = HTTPServer((HOST, PORT), Handler)
    print(f"Listening on http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
