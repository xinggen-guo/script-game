# V2Ray Deploy Guide

This guide covers the practical deployment flow for a fresh VPS.

## Option 1: Full Stack In One Step

Use this when you want the base V2Ray service, tracked subscription server, and manager page together:

```bash
bash deploy_v2ray_full_stack.sh
```

After deploy, verify:
- `systemctl status v2ray --no-pager`
- `systemctl status v2ray-sub --no-pager`
- `systemctl status v2ray-user-manager --no-pager`

Expected endpoints:
- manager page: `http://SERVER_IP:8091`
- per-user subscriptions: `http://SERVER_IP:8088/profiles/<path>.yaml`
- root `http://SERVER_IP:8088/clash.yaml` should be blocked

## Option 2: Deploy Step By Step

1. Deploy the base V2Ray service and tracked subscription server:

```bash
bash deploy_v2ray_subscription.sh
```

This creates:
- `/etc/v2ray/config.json`
- `/opt/v2ray-sub/clash.yaml`
- `/opt/v2ray-sub/server.py`

2. Deploy the manager page:

```bash
bash deploy_v2ray_user_manager.sh
```

This creates:
- `/opt/v2ray-user-manager/app.py`
- `v2ray-user-manager.service`

3. If you already have users in `/etc/v2ray/config.json`, sync their per-user profiles:

```bash
python3 /opt/v2ray-user-manager/app.py sync
```

## Client Setup

For each device, import the per-user subscription URL instead of the shared root URL.

Use:
- `http://SERVER_IP:8088/profiles/<path>.yaml`

Do not use:
- `http://SERVER_IP:8088/clash.yaml`

## Important Routing Note

The client profile should route the VPS IP itself directly:

```yaml
- IP-CIDR,SERVER_IP/32,DIRECT,no-resolve
```

Without this rule, requests to:
- `http://SERVER_IP:8091`
- `http://SERVER_IP:8088`

can go through the proxy itself. Then manager add/remove may look like they failed with a false `502`, because restarting `v2ray.service` cuts the same proxied manager connection.

After changing the base rules, refresh or re-import the per-user subscription profile on the client.
