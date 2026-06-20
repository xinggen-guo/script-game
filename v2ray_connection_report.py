#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


IP_PORT_RE = re.compile(r"((?:\d{1,3}\.){3}\d{1,3}|\[[0-9a-fA-F:]+\]):(\d+)")


def run_command(cmd: list[str]) -> str:
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
    except Exception:
        return ""


def collect_from_journal(service: str, lines: int) -> list[dict]:
    output = run_command(["journalctl", "-u", service, "-n", str(lines), "--no-pager"])
    records = []
    for line in output.splitlines():
        if " accepted " not in line:
            continue
        matches = IP_PORT_RE.findall(line)
        if not matches:
          continue
        ip = matches[0][0].strip("[]")
        records.append({"ip": ip, "raw": line})
    return records


def collect_from_access_log(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records = []
    for line in path.read_text(errors="ignore").splitlines():
        if " accepted " not in line and "email:" not in line and "tcp:" not in line:
            continue
        matches = IP_PORT_RE.findall(line)
        if not matches:
            continue
        ip = matches[0][0].strip("[]")
        records.append({"ip": ip, "raw": line})
    return records


def build_report(records: list[dict]) -> dict:
    counts = Counter(item["ip"] for item in records)
    items = [{"ip": ip, "hits": counts[ip]} for ip in sorted(counts, key=lambda value: (-counts[value], value))]
    return {
        "updated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "unique_clients": len(items),
        "total_records": len(records),
        "clients": items,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize V2Ray/Xray connected client IPs.")
    parser.add_argument("--service", default="v2ray.service", help="systemd service name to inspect")
    parser.add_argument("--lines", type=int, default=500, help="journal lines to inspect")
    parser.add_argument("--access-log", default="", help="optional access log file to parse instead of journal")
    parser.add_argument("--json-output", default="", help="optional path to write JSON report")
    args = parser.parse_args()

    if args.access_log:
        records = collect_from_access_log(Path(args.access_log))
    else:
        records = collect_from_journal(args.service, args.lines)

    report = build_report(records)

    if args.json_output:
        out_path = Path(args.json_output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2))

    print(f"Updated: {report['updated_at']}")
    print(f"Unique clients: {report['unique_clients']}")
    print(f"Total records: {report['total_records']}")
    print()
    for item in report["clients"]:
        print(f"{item['hits']:>5}  {item['ip']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
