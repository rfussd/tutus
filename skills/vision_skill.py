from __future__ import annotations

import base64
import os
import tempfile
from typing import Any

import mss
import requests
from PIL import Image

from core.config import LM_STUDIO_BASE, MODEL_ID


def _lm_url() -> str:
    return LM_STUDIO_BASE


def capture_screen(monitor: int = 1) -> str:
    with mss.MSS() as sct:
        screenshot = sct.grab(sct.monitors[monitor])
        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        img.thumbnail((1280, 720))

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            temp_path = f.name
            img.save(temp_path, "JPEG", quality=85)

    with open(temp_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")

    os.unlink(temp_path)
    return b64


def analyze_screen(question: str = "¿Qué hay en esta pantalla?") -> str:
    b64_image = capture_screen()

    payload: dict[str, Any] = {
        "model": MODEL_ID,
        "messages": [
            {"role": "system", "content": "Eres TUTUS. Analiza la pantalla y responde en español de forma clara y concisa."},
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"}},
                    {"type": "text", "text": question},
                ],
            },
        ],
        "max_tokens": 1024,
        "stream": False,
    }

    try:
        response = requests.post(f"{_lm_url()}/v1/chat/completions", json=payload, timeout=120)
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()  # type: ignore[no-any-return]
    except Exception as e:
        return f"Error analizando pantalla: {str(e)}"


def take_screenshot(filename: str = "screenshot") -> str:
    import datetime
    from pathlib import Path

    output_dir = Path(__file__).parent.parent / "data" / "screenshots"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = output_dir / f"{filename}_{timestamp}.jpg"

    with mss.MSS() as sct:
        screenshot = sct.grab(sct.monitors[1])
        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        img.save(str(path), "JPEG", quality=90)

    os.startfile(str(path))
    return f"Captura guardada: {path.name}"
