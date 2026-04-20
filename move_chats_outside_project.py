import time
import pyautogui

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.25

# ----------------------------
# Config
# ----------------------------
TOTAL = 100
FIRST_RECORD_DELAY = 5
SECOND_RECORD_DELAY = 5
MENU_DELAY = 1.2
MENU_DELAY_START = 0.3
AFTER_REMOVE_DELAY = 2.8


def countdown(label: str, seconds: int):
    print(f"\n{label}")
    for i in range(seconds, 0, -1):
        print(f"{i}...")
        time.sleep(1)


print("Open the ChatGPT project chat list first.")
print("Flow:")
print("1. Move mouse to FIRST visible row")
print("2. Script records and right-clicks automatically")
print("3. Move mouse to 'Remove from work'")
print("4. Script records and left-clicks automatically")
print("5. Then it starts looping\n")
print("Move mouse to top-left corner any time to stop.\n")

# Step 1: record first row automatically
countdown("Move mouse to the FIRST visible chat row. Recording soon", FIRST_RECORD_DELAY)
chat_row = pyautogui.position()
print(f"First row recorded at: {chat_row}")

# Step 2: automatic right click on first row
pyautogui.moveTo(chat_row.x, chat_row.y, duration=0.2)
time.sleep(0.15)
pyautogui.rightClick()
print("Right-clicked first row to open menu.")

# Wait a moment for menu to appear
time.sleep(MENU_DELAY)

# Step 3: record remove item automatically
countdown("Now move mouse to 'Remove from work'. Recording soon", SECOND_RECORD_DELAY)
remove_item = pyautogui.position()
print(f"Remove item recorded at: {remove_item}")

# Step 4: automatic left click on remove item
pyautogui.moveTo(remove_item.x, remove_item.y, duration=0.2)
time.sleep(0.15)
pyautogui.click()
print("Clicked 'Remove from work'.")

# Wait after first removal
time.sleep(AFTER_REMOVE_DELAY)

# Step 5: automatic loop
for i in range(TOTAL - 1):
    print(f"Round {i + 2}/{TOTAL}")

    pyautogui.moveTo(chat_row.x, chat_row.y, duration=0.2)
    time.sleep(0.15)
    pyautogui.rightClick()
    time.sleep(MENU_DELAY_START)

    pyautogui.moveTo(remove_item.x, remove_item.y, duration=0.2)
    time.sleep(0.15)
    pyautogui.click()
    time.sleep(AFTER_REMOVE_DELAY)

print("Done.")