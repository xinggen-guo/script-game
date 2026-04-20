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
