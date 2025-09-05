import sys
import pyautogui
import time
import os

import cv2 as cv

import tty
import termios
import select



def printScreenInfo() -> None:
    screen_w, screen_h = pyautogui.size()
    print(f'screen_width:%d ; screen_height:%d' % (screen_w, screen_h))


def getImageMachPosition(imgOriginalPath, imgMatchPath):
    imgOriginal = cv.imread(imgOriginalPath)
    imgMatch = cv.imread(imgMatchPath)
    imagMatchResult = cv.matchTemplate(imgOriginal, imgMatch, 3)
    min, max, minlocation, maxlocation = cv.minMaxLoc(imagMatchResult)
    h, w = imgMatch.shape[:2]
    imgOriginalH, imgOriginalW = imgOriginal.shape[:2]

    centerPosX = w / 2 + maxlocation[0]
    centerPosY = h / 2 + maxlocation[1]
    return centerPosX / imgOriginalW, centerPosY / imgOriginalH

def getKeyBoardInput():
    settings = termios.tcgetattr(sys.stdin)
    tty.setraw(sys.stdin.fileno())
    rlist, _, _ = select.select([sys.stdin], [], [], 0.3)
    if rlist:
        key = sys.stdin.read(1)
    else:
        key = ''
    print('key:',key)
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
    return key



def sellProductByCount(product_x, product_y, selloutBtn_x, selloutBtn_y,sellCount = 1):
    loopNum = sellCount
    counter = 1
    print(f'count:%d----loopNum:%d' % (counter,loopNum))
    if loopNum <= counter:
        return

    sellout_x = product_x
    sellout_y = product_y

    pyautogui.moveRel(sellout_x, sellout_y, 0.3)
    pyautogui.click(sellout_x, sellout_y)
    time.sleep(0.3)

    sellout_but_x = selloutBtn_x
    sellout_but_y = selloutBtn_y

    while counter <= loopNum:

        pyautogui.click(sellout_x, sellout_y)
        pyautogui.moveRel(sellout_but_x, sellout_but_y,0)
        sellout_but_loop_num = 0
        while sellout_but_loop_num < 2:
            pyautogui.click(sellout_but_x, sellout_but_y)
            input = getKeyBoardInput()
            if input == '':
                print('continue')
            else:
                counter == loopNum
            pyautogui.click(sellout_but_x, sellout_but_y)
            sellout_but_loop_num += 1

        print(f'count:%d' % counter)
        counter += 1


def refreshMoneyMeathod():
    screenshotResult = pyautogui.screenshot()
    currentDir = os.getcwd()
    screenshotPath = currentDir + ('/shotResult.png')
    if os.path.exists(screenshotPath):
        os.remove(screenshotPath)

    screenshotResult.save(screenshotPath)

    imgSelloutBtnMatch = '/Users/xinggenguo/develop/script-game/sellout_btn.png'

    relativeSelloutBtnPos = getImageMachPosition(screenshotPath, imgSelloutBtnMatch)

    screen_w, screen_h = pyautogui.size()

    selloutX = relativeSelloutBtnPos[0] * screen_w
    selloutY = relativeSelloutBtnPos[1] * screen_h

    imgProductBtn = '/Users/xinggenguo/develop/script-game/product.png'
    relativeProductBtnPos = getImageMachPosition(screenshotPath, imgProductBtn)

    productX = relativeProductBtnPos[0] * screen_w
    productY = relativeProductBtnPos[1] * screen_h

    sellProductByCount(productX, productY, selloutX, selloutY, 1000)



# result = getKeyBoardInput()
# if result == '':
#     print("    empty")
# else:
#     print("no empty")
# print('result:',result)

refreshMoneyMeathod()

