"""
Skill de clonación de voz y Speech-to-Speech directo.
"""

from __future__ import annotations

from core.direct_voice import (
    get_device,
    has_cloned_voice,
    record_and_clone,
    text_to_speech,
)


def clonar_voz(duracion: int = 30) -> str:
    return record_and_clone(duracion)


def hablar(texto: str) -> str:
    import os
    import tempfile

    import numpy as np
    from scipy.io.wavfile import write as wav_write

    audio = text_to_speech(texto)
    if audio is None:
        return "No se pudo generar audio."

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    wav_write(tmp.name, 16000, (audio * 32767).astype(np.int16))

    import sounddevice as sd

    sd.play(audio, 16000)
    sd.wait()

    os.unlink(tmp.name)
    return "Audio reproducido."


def estado_voz() -> str:
    device = get_device()
    cloned = has_cloned_voice()
    return f"Device: {device} | Voz clonada: {'Si' if cloned else 'No'}"
