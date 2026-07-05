from __future__ import annotations

import logging
import threading
from collections.abc import Callable

import numpy as np
import sounddevice as sd
from openwakeword.model import Model

from core.config import HOTWORD

log = logging.getLogger("tutus.hotword")

log.info("Cargando detector de hotword ('%s')...", HOTWORD)
# Usar modelo pre-entrenado de openwakeword como fallback
_HOTWORD_MODELS: dict[str, str] = {"tutus": "hey_jarvis", "jarvis": "hey_jarvis", "tutis": "alexa"}
_oww_model_name: str = _HOTWORD_MODELS.get(HOTWORD.lower(), HOTWORD)
oww_model: Model = Model(wakeword_models=[_oww_model_name], inference_framework="onnx")
log.info("Hotword listo (usando '%s').", _oww_model_name)

SAMPLE_RATE: int = 16000
CHUNK_SIZE: int = 1280
_running: bool = False


def stop_hotword() -> None:
    global _running
    _running = False


def start_hotword_detection(callback: Callable[[], None]) -> None:
    global _running
    _running = True

    def _listen() -> None:
        global _running
        log.info("Escuchando hotword... di '%s'", _oww_model_name.replace("_", " ").title())

        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype=np.int16,
            blocksize=CHUNK_SIZE,
        ) as stream:
            while _running:
                try:
                    audio_chunk, _ = stream.read(CHUNK_SIZE)
                    audio_flat = audio_chunk.flatten()
                    oww_model.predict(audio_flat)

                    for model_name, scores in oww_model.prediction_buffer.items():
                        if scores[-1] > 0.3:
                            log.info("Hotword detectado: %s", model_name)
                            oww_model.reset()
                            callback()
                            break
                except Exception as e:
                    log.debug("hotword stream error: %s", e)
                    break

    thread = threading.Thread(target=_listen, daemon=True)
    thread.start()
