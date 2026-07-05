from __future__ import annotations

import logging
import os
import tempfile
import threading
from collections.abc import Callable

import numpy as np
import sounddevice as sd
import soundfile as sf
import whisper

log = logging.getLogger("tutus.listener")

# Cargar modelo Whisper (se baja la primera vez ~150MB)
log.info("Cargando Whisper...")
model: whisper.Whisper = whisper.load_model("base")
log.info("Whisper listo.")

SAMPLE_RATE: int = 16000
CHANNELS: int = 1


def record_audio(duration: int = 5) -> str:
    """
    Graba audio por `duration` segundos y retorna la transcripción.
    """
    log.info("Grabando %s segundos...", duration)
    audio = sd.rec(int(duration * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=CHANNELS, dtype=np.float32)
    sd.wait()  # Esperar a que termine la grabación
    log.info("Grabacion terminada, transcribiendo...")

    # Guardar en archivo temporal
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        temp_path = f.name
        sf.write(temp_path, audio, SAMPLE_RATE)

    # Transcribir con Whisper
    try:
        result = model.transcribe(temp_path, language="es")
        text = result["text"].strip()
        log.info("Transcripcion: %s", text)
        return text  # type: ignore[no-any-return]
    finally:
        os.unlink(temp_path)


def listen_once(duration: int = 5, callback: Callable[[str], None] | None = None) -> None:
    """
    Graba y transcribe en un hilo separado para no bloquear la UI.
    """

    def _run() -> None:
        text = record_audio(duration)
        if callback and text:
            callback(text)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()


def record_audio_raw(duration: int = 5) -> np.ndarray:
    """
    Graba audio y devuelve el array numpy (int16, 16kHz).
    """
    audio = sd.rec(int(duration * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=CHANNELS, dtype=np.float32)
    sd.wait()
    audio_int16 = (audio.flatten() * 32767).astype(np.int16)
    return audio_int16  # type: ignore[no-any-return]
