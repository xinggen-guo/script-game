# V2Ray Manager

## Manager Features

The manager page supports:
- login-protected user management
- add / remove users
- path-based user rows instead of plain user names
- per-user `vmess://` links
- per-user Clash subscription URLs
- traffic totals
- last seen timestamps
- per-user device counts
- approximate active device counts across the whole service

## Runtime Behavior

- when a user is added or removed from the manager, the manager restarts `v2ray.service`
- this is required so the live V2Ray process picks up the new UUID immediately
- existing subscription paths stay unchanged for existing users
- new users get a calculated subscription path derived from the user name
- the manager relies on per-user URLs only, because direct root `clash.yaml` is blocked

If the client routes `SERVER_IP:8091` through the proxy itself, add/remove can appear to fail with a false `502` because the manager page connection is cut during the V2Ray restart.

The practical fix is:
- make the VPS IP go `DIRECT` in the base Clash rules
- refresh the client profile afterward

## Recent Fixes

If a client imported an older cached profile before the recent generator fixes, refresh or re-add the profile once.

Important fixes:
- per-user subscription file generation bug for UUIDs starting with a digit
- proxy-group target now follows the per-user proxy name
- per-user UUID replacement now stays correct while preserving the original rules
- manager/API cache-control headers were added so stale subscription URLs are less likely
- tracked subscription server now supports both `GET` and `HEAD` for remote profile clients
- a `DIRECT` rule for the VPS IP was added so the manager page and subscription endpoints stop hairpinning through V2Ray
