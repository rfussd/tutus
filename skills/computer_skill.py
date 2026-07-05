from __future__ import annotations

import base64
import time
from io import BytesIO

import mss
import pyautogui
from PIL import Image

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.3


def capture_screen_base64() -> str:
    with mss.MSS() as sct:
        screenshot = sct.grab(sct.monitors[1])
        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        img.thumbnail((1280, 720))
        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return b64


def click(x: int, y: int) -> str:
    pyautogui.click(x, y)
    return f"Click en ({x}, {y})"


def double_click(x: int, y: int) -> str:
    pyautogui.doubleClick(x, y)
    return f"Doble click en ({x}, {y})"


def right_click(x: int, y: int) -> str:
    pyautogui.rightClick(x, y)
    return f"Click derecho en ({x}, {y})"


def type_text(text: str) -> str:
    pyautogui.write(text, interval=0.05)
    return f"Texto escrito: {text[:50]}"


def press_key(key: str) -> str:
    pyautogui.press(key.lower())
    return f"Tecla: {key}"


def hotkey(*keys: str) -> str:
    pyautogui.hotkey(*keys)
    return f"Combinación: {'+'.join(keys)}"


def scroll(clicks: int) -> str:
    pyautogui.scroll(clicks)
    return f"Scroll: {clicks}"


def wait(seconds: float = 1.0) -> str:
    time.sleep(seconds)
    return f"Esperé {seconds}s"


def get_screen_size() -> str:
    w: int
    h: int
    w, h = pyautogui.size()
    return f"Pantalla: {w}x{h}"
