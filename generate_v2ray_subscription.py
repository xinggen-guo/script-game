#!/usr/bin/env python3
"""Generate a V2Ray VMess config, share link, and one-node subscription file.

This script does not install V2Ray for you. It prepares:
1. A server-side config.json snippet for v2ray-core
2. A vmess:// share link
3. A base64-encoded subscription file containing that one link

For a more stable and safer deployment, prefer:
- TLS enabled on the client-facing side
- a real domain name instead of a bare IP when using TLS
- a reverse proxy in front of V2Ray, with V2Ray listening on localhost

Example:
    python3 generate_v2ray_subscription.py \
        --server-addr 194.87.245.15 \
        --port 443 \
        --uuid 02def088-cd87-415c-88e8-366b59e97742 \
        --ws-path /v2ray
"""

from __future__ import annotations

import argparse
import base64
import ipaddress
import json
import os
import re
import shutil
import socket
import subprocess
import urllib.request
import uuid
from pathlib import Path


DEFAULT_CONFIG_OUT = "v2ray_config.json"
DEFAULT_SUBSCRIPTION_OUT = "subscribe.txt"
DEFAULT_ENV_OUT = "v2ray_env.env"
SYSTEM_CONFIG_PATH = "/usr/local/etc/v2ray/config.json"
SYSTEM_ENV_PATH = "/etc/v2ray-agent.env"
SYSTEMD_CANDIDATES = ("v2ray", "v2ray.service", "xray", "xray.service")


def is_ip_address(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def validate_server_addr(value: str) -> str:
    if is_ip_address(value):
        return value

    if len(value) > 253 or not re.fullmatch(r"[A-Za-z0-9.-]+", value):
        raise argparse.ArgumentTypeError("server address must be a valid IP or domain")

    return value


def validate_uuid(value: str) -> str:
    try:
        return str(uuid.UUID(value))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("uuid must be a valid UUID") from exc


def validate_ws_path(value: str) -> str:
    if not value.startswith("/"):
        raise argparse.ArgumentTypeError("ws-path must start with '/'")
    return value


def detect_public_ip() -> str:
    services = (
        "https://api.ipify.org",
        "https://ifconfig.me/ip",
        "https://ipv4.icanhazip.com",
    )
    for service in services:
        try:
            with urllib.request.urlopen(service, timeout=3) as response:
                value = response.read().decode("utf-8").strip()
            if value and is_ip_address(value):
                return value
        except Exception:
            continue
    return ""


def detect_local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except Exception:
        return ""


def resolve_server_addr(server_addr: str | None) -> tuple[str, str]:
    if server_addr:
        return server_addr, "user"

    public_ip = detect_public_ip()
    if public_ip:
        return public_ip, "detected_public_ip"

    local_ip = detect_local_ip()
    if local_ip:
        return local_ip, "detected_local_ip"

    return "127.0.0.1", "fallback_loopback"


def resolve_host(host: str, server_addr: str) -> str:
    if host:
        return host
    if not is_ip_address(server_addr):
        return server_addr
    return ""


def resolve_tls(use_tls: bool | None, server_addr: str, ws_host: str) -> bool:
    if use_tls is not None:
        return use_tls
    return bool(ws_host) and not is_ip_address(server_addr)


def resolve_listen_host(
    behind_reverse_proxy: bool | None,
    explicit_listen_host: str,
    use_tls: bool,
) -> str:
    if behind_reverse_proxy is True:
        return "127.0.0.1"
    if behind_reverse_proxy is False:
        return explicit_listen_host
    return "127.0.0.1" if use_tls else explicit_listen_host


def build_server_config(
    client_uuid: str,
    port: int,
    ws_path: str,
    listen_host: str,
    ws_host: str,
) -> dict:
    ws_settings = {"path": ws_path}
    if ws_host:
        ws_settings["headers"] = {"Host": ws_host}

    return {
        "log": {"loglevel": "warning"},
        "inbounds": [
            {
                "listen": listen_host,
                "port": port,
                "protocol": "vmess",
                "settings": {
                    "clients": [
                        {
                            "id": client_uuid,
                            "alterId": 0,
                        }
                    ]
                },
                "streamSettings": {
                    "network": "ws",
                    "wsSettings": ws_settings,
                },
            }
        ],
        "outbounds": [
            {"protocol": "freedom", "tag": "direct"},
            {"protocol": "blackhole", "tag": "block"},
        ],
    }


def build_vmess_payload(
    server_addr: str,
    port: int,
    client_uuid: str,
    ws_path: str,
    remark: str,
    ws_host: str,
    use_tls: bool,
) -> dict:
    return {
        "v": "2",
        "ps": remark,
        "add": server_addr,
        "port": str(port),
        "id": client_uuid,
        "aid": "0",
        "scy": "auto",
        "net": "ws",
        "type": "none",
        "host": ws_host,
        "path": ws_path,
        "tls": "tls" if use_tls else "",
    }


def encode_vmess_link(payload: dict) -> str:
    encoded = base64.b64encode(
        json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    return f"vmess://{encoded}"


def encode_subscription(links: list[str]) -> str:
    joined = "\n".join(links)
    return base64.b64encode(joined.encode("utf-8")).decode("ascii")


def shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def build_env_map(
    server_addr: str,
    port: int,
    client_uuid: str,
    ws_path: str,
    remark: str,
    ws_host: str,
    use_tls: bool,
    listen_host: str,
) -> dict[str, str]:
    return {
        "V2RAY_SERVER_ADDR": server_addr,
        "V2RAY_PORT": str(port),
        "V2RAY_UUID": client_uuid,
        "V2RAY_WS_PATH": ws_path,
        "V2RAY_REMARK": remark,
        "V2RAY_HOST": ws_host,
        "V2RAY_TLS": "1" if use_tls else "0",
        "V2RAY_LISTEN_HOST": listen_host,
    }


def write_env_file(path: Path, values: dict[str, str]) -> None:
    lines = [f"{key}={shell_quote(value)}" for key, value in values.items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key.strip()] = value
    return values


def require_root(action: str) -> None:
    if os.geteuid() != 0:
        raise SystemExit(f"{action} requires root. Re-run with sudo.")


def run_command(command: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=check, text=True, capture_output=True)


def detect_service_name() -> str:
    for candidate in SYSTEMD_CANDIDATES:
        result = subprocess.run(
            ["systemctl", "status", candidate],
            text=True,
            capture_output=True,
        )
        if result.returncode == 0 or "Loaded:" in result.stdout + result.stderr:
            return candidate
    return "v2ray"


def install_v2ray(
    config: dict,
    env_values: dict[str, str],
    config_out: Path,
) -> None:
    require_root("Install")
    install_cmd = (
        "bash -c \"$(curl -L https://raw.githubusercontent.com/v2fly/fhs-install-v2ray/master/install-release.sh)\""
    )
    print("Installing V2Ray from the official v2fly installer...")
    subprocess.run(install_cmd, shell=True, check=True)

    system_config = Path(SYSTEM_CONFIG_PATH)
    system_config.parent.mkdir(parents=True, exist_ok=True)
    system_config.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    write_env_file(Path(SYSTEM_ENV_PATH), env_values)

    service_name = detect_service_name()
    run_command(["systemctl", "daemon-reload"])
    run_command(["systemctl", "enable", service_name])
    run_command(["systemctl", "restart", service_name])

    print(f"Installed config: {system_config}")
    print(f"Installed env file: {SYSTEM_ENV_PATH}")
    print(f"Service restarted: {service_name}")
    print(f"Local generated config remains at: {config_out}")


def uninstall_v2ray(remove_generated_files: bool, generated_paths: list[Path]) -> None:
    require_root("Uninstall")
    service_name = detect_service_name()

    subprocess.run(["systemctl", "disable", "--now", service_name], text=True, capture_output=True)

    uninstall_script = Path("/tmp/fhs-uninstall-v2ray.sh")
    with urllib.request.urlopen(
        "https://raw.githubusercontent.com/v2fly/fhs-install-v2ray/master/install-release.sh",
        timeout=10,
    ) as response:
        uninstall_script.write_bytes(response.read())
    uninstall_script.chmod(0o755)
    subprocess.run(["bash", str(uninstall_script), "--remove"], check=True)

    Path(SYSTEM_ENV_PATH).unlink(missing_ok=True)

    if remove_generated_files:
        for path in generated_paths:
            path.unlink(missing_ok=True)

    print(f"Uninstalled service: {service_name}")
    print(f"Removed env file: {SYSTEM_ENV_PATH}")
    if remove_generated_files:
        print("Removed generated local files as requested.")


def print_status(
    env_out: Path,
    config_out: Path,
    subscription_out: Path,
) -> None:
    print("V2Ray status")
    print("------------------------------")
    print(f"Config file              : {'yes' if config_out.exists() else 'no'}")
    print(f"Env file                 : {'yes' if env_out.exists() else 'no'}")
    print(f"Config path              : {config_out}")
    print(f"Env path                 : {env_out}")

    saved_env = read_env_file(env_out)
    if saved_env:
        print()
        print("Saved config")
        print("------------------------------")
        print(f"Address                  : {saved_env.get('V2RAY_SERVER_ADDR', '')}")
        print(f"Port                     : {saved_env.get('V2RAY_PORT', '')}")
        print(f"User ID                  : {saved_env.get('V2RAY_UUID', '')}")
        print(f"Network                  : ws")
        print(f"Path                     : {saved_env.get('V2RAY_WS_PATH', '')}")
        print(f"Host                     : {saved_env.get('V2RAY_HOST', '') or 'none'}")
        print(
            f"TLS                      : {'tls' if saved_env.get('V2RAY_TLS') == '1' else 'none'}"
        )
        print(f"Listen host              : {saved_env.get('V2RAY_LISTEN_HOST', '')}")

    system_env = read_env_file(Path(SYSTEM_ENV_PATH))
    if system_env:
        print()
        print("Installed config")
        print("------------------------------")
        print(f"Address                  : {system_env.get('V2RAY_SERVER_ADDR', '')}")
        print(f"Port                     : {system_env.get('V2RAY_PORT', '')}")
        print(f"User ID                  : {system_env.get('V2RAY_UUID', '')}")
        print(f"Path                     : {system_env.get('V2RAY_WS_PATH', '')}")
        print(f"Host                     : {system_env.get('V2RAY_HOST', '') or 'none'}")
        print(
            f"TLS                      : {'tls' if system_env.get('V2RAY_TLS') == '1' else 'none'}"
        )

    system_config = Path(SYSTEM_CONFIG_PATH)
    print()
    print(f"System config            : {'yes' if system_config.exists() else 'no'}")
    print(f"System config path       : {system_config}")

    if shutil.which("systemctl") is None:
        print("Service status           : systemd unavailable on this machine")
        return

    service_name = detect_service_name()
    result = subprocess.run(
        ["systemctl", "is-active", service_name],
        text=True,
        capture_output=True,
    )
    active = result.stdout.strip() or result.stderr.strip() or "unknown"
    enabled_result = subprocess.run(
        ["systemctl", "is-enabled", service_name],
        text=True,
        capture_output=True,
    )
    enabled = enabled_result.stdout.strip() or enabled_result.stderr.strip() or "unknown"
    print(f"Service name             : {service_name}")
    print(f"Service active           : {active}")
    print(f"Service enabled          : {enabled}")


def print_generated_summary(
    server_addr: str,
    port: int,
    client_uuid: str,
    ws_path: str,
    ws_host: str,
    use_tls: bool,
    listen_host: str,
    vmess_link: str,
    config_out: Path,
    env_out: Path,
    show_env: bool,
    server_addr_source: str,
) -> None:
    network_name = "ws"
    protocol_name = "VMess-WS-TLS" if use_tls else "VMess-WS"

    print("生成配置文件...")
    print()
    print(f"使用协议: {protocol_name}")
    print("------------------------------")
    print(f"协议 (protocol)         = vmess")
    print(f"地址 (address)          = {server_addr}")
    print(f"端口 (port)             = {port}")
    print(f"用户ID (id)             = {client_uuid}")
    print(f"传输协议 (network)      = {network_name}")
    print(f"伪装类型 (type)         = none")
    print(f"路径 (path)             = {ws_path}")
    print(f"主机 (host)             = {ws_host or 'none'}")
    print(f"传输层安全 (tls)        = {'tls' if use_tls else 'none'}")
    print(f"监听地址 (listen)       = {listen_host}")
    print("------------------------------")
    print("链接 (URL)")
    print(vmess_link)
    print("------------------------------")
    print(f"配置文件                = {config_out}")
    print(f"环境文件                = {env_out}")
    if show_env:
        print("------------------------------")
        print("环境变量")
        print(f"V2RAY_SERVER_ADDR       = {server_addr}")
        print(f"V2RAY_PORT              = {port}")
        print(f"V2RAY_UUID              = {client_uuid}")
        print(f"V2RAY_WS_PATH           = {ws_path}")
        print(f"V2RAY_HOST              = {ws_host or ''}")
        print(f"V2RAY_TLS               = {'1' if use_tls else '0'}")
        print(f"V2RAY_LISTEN_HOST       = {listen_host}")
    if server_addr_source != "user":
        print("------------------------------")
        print(f"提示: 地址为自动识别结果 ({server_addr_source})，如需请手动覆盖。")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate V2Ray VMess config and subscription artifacts."
    )
    parser.add_argument(
        "--install",
        action="store_true",
        help="Install V2Ray, write the generated config into the system path, and restart the service",
    )
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="Uninstall V2Ray from the machine",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show saved config status and service running state",
    )
    parser.add_argument(
        "--show-env",
        action="store_true",
        help="Print the generated environment values after writing files",
    )
    parser.add_argument(
        "--remove-generated-files",
        action="store_true",
        help="When used with --uninstall, also remove locally generated files",
    )
    parser.add_argument(
        "--server-addr",
        type=validate_server_addr,
        help="Public server IP or domain. If omitted, the script will try to detect one.",
    )
    parser.add_argument("--port", type=int, default=443, help="Inbound port")
    parser.add_argument(
        "--uuid",
        default=str(uuid.uuid4()),
        type=validate_uuid,
        help="Client UUID (default: auto-generate)",
    )
    parser.add_argument(
        "--ws-path",
        default="/v2ray",
        type=validate_ws_path,
        help="WebSocket path",
    )
    parser.add_argument(
        "--host",
        default="",
        help="Optional Host header/domain for WebSocket and client config",
    )
    parser.add_argument(
        "--tls",
        action="store_true",
        default=None,
        help="Enable TLS in the generated VMess link",
    )
    parser.add_argument(
        "--no-tls",
        action="store_false",
        dest="tls",
        help="Disable TLS in the generated VMess link",
    )
    parser.add_argument(
        "--listen-host",
        default="0.0.0.0",
        help="Server bind address for the generated inbound config",
    )
    parser.add_argument(
        "--behind-reverse-proxy",
        action="store_true",
        default=None,
        help="Bind the inbound to 127.0.0.1 for reverse-proxy deployments",
    )
    parser.add_argument(
        "--no-behind-reverse-proxy",
        action="store_false",
        dest="behind_reverse_proxy",
        help="Keep the inbound listening on the configured listen-host",
    )
    parser.add_argument(
        "--remark",
        help="Display name in the VMess link (default: vps-v2ray-<server-addr>)",
    )
    parser.add_argument(
        "--config-out",
        default=DEFAULT_CONFIG_OUT,
        help="Where to write the generated config JSON",
    )
    parser.add_argument(
        "--subscription-out",
        default=DEFAULT_SUBSCRIPTION_OUT,
        help="Where to write the base64 subscription content",
    )
    parser.add_argument(
        "--env-out",
        default=DEFAULT_ENV_OUT,
        help="Where to write the generated environment file",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config_out = Path(args.config_out)
    subscription_out = Path(args.subscription_out)
    env_out = Path(args.env_out)

    if args.uninstall:
        uninstall_v2ray(
            remove_generated_files=args.remove_generated_files,
            generated_paths=[config_out, subscription_out, env_out],
        )
        return

    if args.status:
        print_status(env_out, config_out, subscription_out)
        return

    server_addr, server_addr_source = resolve_server_addr(args.server_addr)
    ws_host = resolve_host(args.host, server_addr)
    use_tls = resolve_tls(args.tls, server_addr, ws_host)
    listen_host = resolve_listen_host(
        args.behind_reverse_proxy,
        args.listen_host,
        use_tls,
    )
    remark = args.remark or f"vps-v2ray-{server_addr}"

    config = build_server_config(
        args.uuid,
        args.port,
        args.ws_path,
        listen_host,
        ws_host,
    )
    payload = build_vmess_payload(
        server_addr=server_addr,
        port=args.port,
        client_uuid=args.uuid,
        ws_path=args.ws_path,
        remark=remark,
        ws_host=ws_host,
        use_tls=use_tls,
    )
    vmess_link = encode_vmess_link(payload)
    subscription_content = encode_subscription([vmess_link])
    env_values = build_env_map(
        server_addr=server_addr,
        port=args.port,
        client_uuid=args.uuid,
        ws_path=args.ws_path,
        remark=remark,
        ws_host=ws_host,
        use_tls=use_tls,
        listen_host=listen_host,
    )

    config_out.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    subscription_out.write_text(subscription_content + "\n", encoding="utf-8")
    write_env_file(env_out, env_values)

    if args.install:
        install_v2ray(config, env_values, config_out)

    print_generated_summary(
        server_addr=server_addr,
        port=args.port,
        client_uuid=args.uuid,
        ws_path=args.ws_path,
        ws_host=ws_host,
        use_tls=use_tls,
        listen_host=listen_host,
        vmess_link=vmess_link,
        config_out=config_out,
        env_out=env_out,
        show_env=args.show_env,
        server_addr_source=server_addr_source,
    )
    if not use_tls:
        print("提示: 当前链接未启用 TLS，建议配合反向代理和证书使用。")
    if use_tls and is_ip_address(server_addr):
        print("提示: TLS 一般配合域名会比裸 IP 更稳定。")
    if args.server_addr is None:
        print("提示: 当前地址为自动识别结果，如与你的 VPS 地址不一致请手动指定。")
    if listen_host == "127.0.0.1":
        print("提示: 当前为反向代理模式，入站监听地址为 127.0.0.1。")


if __name__ == "__main__":
    main()
