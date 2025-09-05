# uno_card_tracker.py

import cv2
import pytesseract
import numpy as np
from PIL import Image
import mss
import time
import threading
import keyboard  # 需要安装 keyboard 模块

# ========= 工具函数 =========

def get_dominant_color_bgr(cv_img):
    hsv = cv2.cvtColor(cv_img, cv2.COLOR_BGR2HSV)
    avg_h = hsv[:, :, 0].mean()
    if avg_h < 10 or avg_h > 160:
        return "Red"
    elif 10 <= avg_h < 30:
        return "Yellow"
    elif 30 <= avg_h < 85:
        return "Green"
    elif 85 <= avg_h < 130:
        return "Blue"
    else:
        return "Unknown"

def extract_center_card_info(pil_img):
    w, h = pil_img.size
    center_area = pil_img.crop((w * 0.42, h * 0.42, w * 0.58, h * 0.58))
    cv_center = cv2.cvtColor(np.array(center_area), cv2.COLOR_RGB2BGR)
    color = get_dominant_color_bgr(cv_center)

    sw, sh = center_area.size
    symbol_region = center_area.crop((sw * 0.2, sh * 0.15, sw * 0.8, sh * 0.65))
    cv_symbol = cv2.cvtColor(np.array(symbol_region), cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(cv_symbol, 120, 255, cv2.THRESH_BINARY)

    text = pytesseract.image_to_string(
        thresh, config="--psm 6 -c tessedit_char_whitelist=0123456789+SKIPREVERSEWILD"
    )
    symbol = text.strip().upper().replace(" ", "").replace("\n", "")

    if "SKIP" in symbol:
        symbol = "Skip"
    elif "REVERSE" in symbol:
        symbol = "Reverse"
    elif "+" in symbol:
        symbol = "+2" if "2" in symbol else "+4"
    elif "WILD" in symbol:
        symbol = "Wild"
    elif symbol.isdigit():
        pass
    else:
        symbol = "Unknown"

    return {"color": color, "symbol": symbol}

def capture_screen_pil():
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        sct_img = sct.grab(monitor)
        return Image.frombytes('RGB', sct_img.size, sct_img.rgb)

# ========= 主监听逻辑 =========

def track_card_changes(interval=1.5):
    last_card = None
    history = []
    print("[🟢] 正在监听 UNO 出牌区域，按下 Q 可退出...\n")

    while True:
        if keyboard.is_pressed("q"):
            print("\n[🛑] 用户中断，退出监听。")
            break

        pil_img = capture_screen_pil()
        card_info = extract_center_card_info(pil_img)

        if card_info != last_card:
            last_card = card_info
            history.append(card_info)

            print(f"[🃏] 新出牌：{card_info['color']} {card_info['symbol']}")
            print("📜 出牌历史：")
            for idx, c in enumerate(history, 1):
                print(f"  {idx}. {c['color']} {c['symbol']}")
            print("-" * 40)
        else:
            print("[…] 出牌无变化")

        time.sleep(interval)

# ========= 程序入口 =========

if __name__ == "__main__":
    track_card_changes()