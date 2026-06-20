# V2Ray Operations

## Subscription Tracking

The tracked subscription server is used so the service can tell which per-user URL was fetched.

Current behavior:
- `GET /clash.yaml` and `HEAD /clash.yaml` return `403 Forbidden`
- per-user URLs under `/profiles/...yaml` are allowed
- legacy `/users/<name>/clash.yaml` files can still be kept for compatibility
- each fetch is written to `/opt/v2ray-sub/access.jsonl`
- clients should refresh their per-user profile after routing-rule changes, especially after adding the VPS-IP `DIRECT` rule

## Daily Operations

Useful commands:

```bash
systemctl status v2ray --no-pager
systemctl status v2ray-sub --no-pager
systemctl status v2ray-user-manager --no-pager
python3 /opt/v2ray-user-manager/app.py list
python3 /opt/v2ray-user-manager/app.py sync
bash check_v2ray_status.sh
```

## Health Checks

Typical things to verify:
- manager page responds on `http://SERVER_IP:8091`
- per-user profile responds on `http://SERVER_IP:8088/profiles/<path>.yaml`
- root `http://SERVER_IP:8088/clash.yaml` is blocked
- `v2ray.service` stays active after user add/remove
