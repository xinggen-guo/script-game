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


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def client_ip(handler: BaseHTTPRequestHandler) -> str:
    forwarded = handler.headers.get("X-Forwarded-For", "").strip()
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return handler.client_address[0]


def write_access(handler: BaseHTTPRequestHandler, status: int, path: str) -> None:
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


def resolve_path(request_path: str) -> Path | None:
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
    def handle_request(self, send_body: bool):
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
        self.handle_request(send_body=True)

    def do_HEAD(self):
        self.handle_request(send_body=False)

    def log_message(self, format, *args):
        return


def main():
    ROOT_DIR.mkdir(parents=True, exist_ok=True)
    HTTPServer((HOST, PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
