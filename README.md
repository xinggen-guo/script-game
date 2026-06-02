# script-game

This repository is a small collection of personal casual scripts.

Most of the files here are one-off utilities or experiments I use for:
- desktop automation
- quick computer vision tests
- simple game helpers
- local file conversion
- small learning demos
- personal network config generation

It is not structured as a single app or package. Each script is mostly standalone.

One area has become more structured over time:
- a small VPS proxy deployment workflow for V2Ray
- Clash subscription generation and serving
- lightweight service monitoring helpers

## What Is In This Repo

### Automation and game helpers

`travel_town.py`

A desktop automation script for a game workflow. It uses screenshots, template matching, and mouse control to find UI elements and repeat a sell action.

Related image assets:
- `product.png`
- `sellout_btn.png`
- `shotResult.png`

`UnoRemberCard.py`

A small UNO screen tracker. It captures the screen, tries to detect the center card color and symbol, and prints card history when the visible card changes.

`move_chats_outside_project.py`

A desktop automation helper for removing chats from a ChatGPT project list by repeating mouse actions after recording a couple of screen positions.

### Utility scripts

`convertFIleUtils.py`

Batch converts documents from a local input folder to PDF using LibreOffice in headless mode.

`generate_v2ray_subscription.py`

Generates:
- a V2Ray VMess server config JSON
- a `vmess://` share link
- a base64 subscription text file containing that link
- a small env file with the generated values

It can also:
- install V2Ray with the generated config
- uninstall V2Ray
- show whether the generated files exist
- show saved env values
- show service status when `systemd` is available

Useful commands:
- `python3 generate_v2ray_subscription.py`
- `python3 generate_v2ray_subscription.py --show-env`
- `sudo python3 generate_v2ray_subscription.py --install`
- `python3 generate_v2ray_subscription.py --status`
- `sudo python3 generate_v2ray_subscription.py --uninstall`

`deploy_v2ray_subscription.sh`

Deploys a simple VPS-based V2Ray service and a Clash subscription endpoint.

What it does:
- generates a random UUID
- installs V2Ray
- writes `/etc/v2ray/config.json`
- writes `/opt/v2ray-sub/clash.yaml`
- installs `v2ray.service`
- installs `v2ray-sub.service`
- prints the final VMess link and subscription URL

Current server shape used in this project:
- protocol: `vmess`
- transport: `ws`
- port: `443`
- path: `/v2ray`
- subscription URL: `http://SERVER_IP:8088/clash.yaml`

`check_v2ray_status.sh`

Collects common VPS debugging information for the V2Ray service:
- service state
- ports
- active connections
- recent logs
- recent accepted and rejected connections
- local subscription endpoint health

`v2ray_dashboard.py`

A lightweight dashboard app for V2Ray connection monitoring.

It shows:
- whether `v2ray.service` is active
- whether `v2ray-sub.service` is active
- active client IPs as approximate devices
- a table of active connections
- a table of seen devices over time

`deploy_v2ray_dashboard.sh`

Installs the dashboard app on a VPS as a `systemd` service.

### Learning and experiments

`testTrans.py`

A very small PyTorch transformer-style demo used for experimentation and learning.

## How To Use

There is no single entry point.

Run scripts directly with Python 3:

```bash
python3 travel_town.py
python3 UnoRemberCard.py
python3 move_chats_outside_project.py
python3 testTrans.py
python3 convertFIleUtils.py
python3 generate_v2ray_subscription.py --server-addr 1.2.3.4
```

For the VPS deploy helpers:

```bash
bash deploy_v2ray_subscription.sh
bash check_v2ray_status.sh
```

For the dashboard:

```bash
python3 v2ray_dashboard.py
bash deploy_v2ray_dashboard.sh
```

## V2Ray Project Notes

This repo now contains enough scripts to act as a small deployment base for a personal VPS proxy service.

### Current Architecture

- V2Ray runtime config lives at `/etc/v2ray/config.json`
- Clash subscription lives at `/opt/v2ray-sub/clash.yaml`
- Subscription is served by a simple Python HTTP server on port `8088`
- Main `systemd` services:
  - `v2ray.service`
  - `v2ray-sub.service`

### Current Clash Subscription Direction

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

### Main Stability Finding

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

### Recommended Future Upgrade

If this VPS tooling becomes a more serious project, the next step should likely be replacing the current transport with something stronger, for example:
- `vless + reality`
- `hysteria2`
- `tuic`

Those are better long-term directions than continuing to tune only the current `vmess + ws + no TLS` setup.

## Dependencies

Dependencies vary by script. Some scripts need extra local tools or Python packages.

Common examples in this repo:
- `pyautogui`
- `opencv-python`
- `pytesseract`
- `numpy`
- `Pillow`
- `mss`
- `keyboard`
- `torch`
- LibreOffice `soffice`

Install only what you need for the script you want to run.

## Notes

- Some scripts contain hard-coded local paths and were written for personal use.
- Some scripts are macOS or desktop-environment specific because they depend on mouse control, screen capture, or local apps.
- A few filenames and script contents are rough prototypes, which matches the casual nature of this repo.
- If I keep adding to this project, it may make sense later to split scripts into folders like `automation/`, `games/`, `utils/`, and `experiments/`.
- The V2Ray-related files are now the most cohesive part of the repo and could be split into a dedicated `vps/` or `network/` folder later.
