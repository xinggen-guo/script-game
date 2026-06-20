#!/usr/bin/env python3
import argparse
import json
import os
import uuid
from collections import Counter
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


CONFIG_PATH = Path(os.environ.get("XRAY_CONFIG_PATH", "/usr/local/etc/xray/config.json"))
ACCESS_LOG_PATH = Path(os.environ.get("XRAY_ACCESS_LOG", "/var/log/xray/access.log"))
HOST = os.environ.get("XRAY_MANAGER_HOST", "127.0.0.1")
PORT = int(os.environ.get("XRAY_MANAGER_PORT", "8091"))
SERVER_IP = os.environ.get("XRAY_SERVER_IP", "")
SUB_BASE_URL = os.environ.get("XRAY_SUB_BASE_URL", "")


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text())


def save_config(config: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(config, indent=2))


def get_reality_settings(config: dict) -> dict:
    inbound = config["inbounds"][0]
    return inbound["streamSettings"]["realitySettings"]


def get_clients(config: dict) -> list[dict]:
    return config["inbounds"][0]["settings"]["clients"]


def make_vless_link(config: dict, client: dict) -> str:
    inbound = config["inbounds"][0]
    reality = get_reality_settings(config)
    port = inbound["port"]
    server_name = reality["serverNames"][0]
    short_id = reality["shortIds"][0]
    public_key = reality.get("publicKey", "")
    name = client.get("email", client["id"])
    host = SERVER_IP or "YOUR_SERVER_IP"
    flow = client.get("flow", "xtls-rprx-vision")
    return (
        f"vless://{client['id']}@{host}:{port}"
        f"?encryption=none&security=reality&sni={server_name}&fp=chrome"
        f"&pbk={public_key}&sid={short_id}&type=tcp&flow={flow}"
        f"#{name}"
    )


def collect_hits() -> Counter:
    counts = Counter()
    if not ACCESS_LOG_PATH.exists():
        return counts
    for line in ACCESS_LOG_PATH.read_text(errors="ignore").splitlines():
        for client_id in counts.keys():
            pass
    # Xray access logs usually include "email:" when client emails are set.
    for line in ACCESS_LOG_PATH.read_text(errors="ignore").splitlines():
        marker = "email:"
        if marker not in line:
            continue
        email = line.split(marker, 1)[1].strip().split()[0].strip('"')
        if email:
            counts[email] += 1
    return counts


def list_users() -> list[dict]:
    config = load_config()
    clients = get_clients(config)
    hits = collect_hits()
    users = []
    for client in clients:
        name = client.get("email", client["id"])
        users.append(
            {
                "name": name,
                "uuid": client["id"],
                "flow": client.get("flow", ""),
                "hits": hits.get(name, 0),
                "link": make_vless_link(config, client),
            }
        )
    return users


def add_user(name: str) -> dict:
    config = load_config()
    clients = get_clients(config)
    new_uuid = str(uuid.uuid4())
    client = {
        "id": new_uuid,
        "flow": "xtls-rprx-vision",
        "email": name,
    }
    clients.append(client)
    save_config(config)
    return {
        "name": name,
        "uuid": new_uuid,
        "link": make_vless_link(config, client),
    }


def remove_user(name: str) -> bool:
    config = load_config()
    clients = get_clients(config)
    new_clients = [client for client in clients if client.get("email", client["id"]) != name]
    if len(new_clients) == len(clients):
        return False
    config["inbounds"][0]["settings"]["clients"] = new_clients
    save_config(config)
    return True


def render_html(message: str = "") -> str:
    rows = list_users()
    rows_html = "".join(
        f"<tr><td><code>{row['name']}</code></td>"
        f"<td><code>{row['uuid']}</code></td>"
        f"<td>{row['hits']}</td>"
        f"<td><textarea readonly>{row['link']}</textarea></td>"
        f"<td><form method='post' action='/remove'><input type='hidden' name='name' value='{row['name']}'><button>Remove</button></form></td></tr>"
        for row in rows
    )
    if not rows_html:
        rows_html = "<tr><td colspan='5'>No users yet.</td></tr>"
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Xray Reality User Manager</title>
  <style>
    body {{ font-family: ui-sans-serif, -apple-system, sans-serif; margin: 0; background: #0f172a; color: #e2e8f0; }}
    .wrap {{ max-width: 1100px; margin: 0 auto; padding: 24px; }}
    .card {{ background: #111827; border: 1px solid #334155; border-radius: 16px; padding: 18px; margin-bottom: 18px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ border-bottom: 1px solid #334155; text-align: left; padding: 10px; vertical-align: top; }}
    textarea {{ width: 100%; min-height: 76px; background: #0b1220; color: #cbd5e1; border: 1px solid #334155; border-radius: 8px; }}
    input, button {{ padding: 10px 12px; border-radius: 8px; border: 1px solid #334155; }}
    input {{ background: #0b1220; color: #e2e8f0; }}
    button {{ background: #2563eb; color: white; cursor: pointer; }}
    .msg {{ color: #93c5fd; margin-bottom: 12px; }}
    code {{ background: #0b1220; padding: 2px 6px; border-radius: 6px; }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <h1>Xray Reality User Manager</h1>
      <p>Updated: {now_iso()}</p>
      {f"<p class='msg'>{message}</p>" if message else ""}
      <form method="post" action="/add">
        <input name="name" placeholder="user name, for example codex-mac" required>
        <button type="submit">Add User</button>
      </form>
      <p>Config: <code>{CONFIG_PATH}</code></p>
      {f"<p>Subscription base URL: <code>{SUB_BASE_URL}</code></p>" if SUB_BASE_URL else ""}
    </div>
    <div class="card">
      <h2>Users</h2>
      <table>
        <thead><tr><th>Name</th><th>UUID</th><th>Hits</th><th>VLESS Link</th><th>Action</th></tr></thead>
        <tbody>{rows_html}</tbody>
      </table>
    </div>
  </div>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/users":
            self.respond_json({"updated_at": now_iso(), "users": list_users()})
            return
        if path == "/":
            self.respond_html(render_html())
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode()
        form = parse_qs(body)
        name = form.get("name", [""])[0].strip()
        if path == "/add" and name:
            user = add_user(name)
            self.respond_redirect(f"/?message=Added+{user['name']}")
            return
        if path == "/remove" and name:
            remove_user(name)
            self.respond_redirect(f"/?message=Removed+{name}")
            return
        self.send_response(400)
        self.end_headers()

    def respond_redirect(self, location: str):
        self.send_response(303)
        self.send_header("Location", location)
        self.end_headers()

    def respond_html(self, html: str):
        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def respond_json(self, payload: dict):
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


def cli():
    parser = argparse.ArgumentParser(description="Manage Xray Reality users.")
    sub = parser.add_subparsers(dest="cmd", required=False)
    sub.add_parser("list")
    add_parser = sub.add_parser("add")
    add_parser.add_argument("name")
    remove_parser = sub.add_parser("remove")
    remove_parser.add_argument("name")
    sub.add_parser("serve")
    args = parser.parse_args()

    if args.cmd == "add":
        user = add_user(args.name)
        print(json.dumps(user, indent=2))
        return
    if args.cmd == "remove":
        ok = remove_user(args.name)
        print("removed" if ok else "not found")
        return
    if args.cmd == "list":
        print(json.dumps({"users": list_users()}, indent=2))
        return

    server = HTTPServer((HOST, PORT), Handler)
    print(f"Listening on http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    cli()
