# V2Ray Architecture

## Current Architecture

- V2Ray runtime config lives at `/etc/v2ray/config.json`
- Clash subscription lives at `/opt/v2ray-sub/clash.yaml`
- Subscription serving logic lives at `/opt/v2ray-sub/server.py`
- Port `8088` is served by the tracked subscription server, not plain `python -m http.server`
- Direct root `/clash.yaml` access is blocked on purpose
- Existing legacy per-user files can still live under `/opt/v2ray-sub/users/<name>/clash.yaml`
- Active per-user subscription files live under `/opt/v2ray-sub/profiles/*.yaml`
- Subscription access log lives at `/opt/v2ray-sub/access.jsonl`
- The base Clash rules should include a `DIRECT` rule for the VPS IP itself, for example `IP-CIDR,SERVER_IP/32,DIRECT,no-resolve`
- V2Ray stats API listens on `127.0.0.1:10085`
- Admin page listens on `http://SERVER_IP:8091`

Main `systemd` services:
- `v2ray.service`
- `v2ray-sub.service`
- `v2ray-user-manager.service`

## Current Clash Subscription Direction

The generated subscription is designed to support:
- Google services
- OpenAI / ChatGPT / Codex
- Claude / Anthropic
- Gemini / Google AI
- Telegram
- LinkedIn

The rule structure is intentionally simple:
- local/private direct
- explicit Google rules
- explicit AI service rules
- Telegram rules
- LinkedIn rules
- China mainland direct
- final fallback to the single VPS proxy group

Per-user generated YAML files keep the original base rules and only replace:
- the first proxy `name`
- the first proxy `uuid`
- references to the original first proxy name inside proxy groups

That keeps rule behavior aligned with the base `clash.yaml`.

## Main Stability Finding

The most important conclusion from debugging this setup:

- the Clash rules are mostly fine
- DNS was improved with a fallback block
- the main instability is the current server transport itself

Current transport:
- `vmess + ws + no TLS` on port `443`

Observed server log problems included:
- `unexpected EOF`
- `failed to read request header`
- `i/o timeout`
- `connection reset by peer`

So this repo is useful for deploying the current service, but the next real upgrade should be protocol-level rather than only rule-level.
