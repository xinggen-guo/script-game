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

Deploys a VPS-based V2Ray service and a tracked Clash subscription endpoint.

What it does:
- generates a random UUID
- installs V2Ray
- writes `/etc/v2ray/config.json`
- writes `/opt/v2ray-sub/clash.yaml`
- writes `/opt/v2ray-sub/server.py`
- installs `v2ray.service`
- installs `v2ray-sub.service`
- prints the final VMess link and subscription URL

Current server shape used in this project:
- protocol: `vmess`
- transport: `ws`
- port: `443`
- path: `/v2ray`
- direct root `http://SERVER_IP:8088/clash.yaml` is blocked
- per-user subscriptions are served from `http://SERVER_IP:8088/profiles/<path>.yaml`

`deploy_v2ray_user_manager.sh`

Deploys the web admin page for user management.

What it does:
- installs the manager app under `/opt/v2ray-user-manager`
- installs `v2ray-user-manager.service`
- exposes the manager page on port `8091`
- manages per-user Clash subscriptions under `/opt/v2ray-sub/profiles/*.yaml`
- preserves existing user paths and only generates calculated new paths for new users
- restarts `v2ray.service` automatically after add/remove so new users work immediately

`deploy_v2ray_full_stack.sh`

Deploys the whole current V2Ray stack in one step.

What it does:
- deploys the base V2Ray service and main subscription
- enables the local V2Ray stats API on `127.0.0.1:10085`
- deploys the admin page
- syncs per-user subscription files
- prints the final subscription URL and manager login

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
bash deploy_v2ray_user_manager.sh
bash deploy_v2ray_full_stack.sh
bash check_v2ray_status.sh
```

For the dashboard:

```bash
python3 v2ray_dashboard.py
bash deploy_v2ray_dashboard.sh
```

## V2Ray Docs

The VPS proxy workflow is now split by function:

- [Deploy Guide](docs/v2ray-deploy-guide.md)
- [Architecture](docs/v2ray-architecture.md)
- [Manager](docs/v2ray-manager.md)
- [Operations](docs/v2ray-operations.md)

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
