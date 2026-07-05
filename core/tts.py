from __future__ import annotations

"""
Text-to-Speech: usa DirectVoice (local GPU) si está disponible,
fallback a edge-tts (internet).
"""
import logging
import os
import re
import threading

log = logging.getLogger("tutus.tts")


VOICE: str = "es-MX-JorgeNeural"
RATE: str = "+15%"

_use_direct: bool = False
try:
    from core.direct_voice import has_cloned_voice

    if has_cloned_voice():
        _use_direct = True
except Exception as e:
    log.debug("direct_voice not available: %s", e)

_tts_lock: threading.Lock = threading.Lock()


def clean_text_for_tts(text: str) -> str:
    emoji_pattern = re.compile("[\U0001f600-\U0001f64f\U0001f300-\U0001f5ff\U0001f680-\U0001f9ff\U00002600-\U000027bf]+", flags=re.UNICODE)
    text = emoji_pattern.sub("", text)
    text = re.sub(r"[◈▸✓»«*#]", "", text)
    text = text.strip()
    return text


def speak(text: str) -> None:
    clean = clean_text_for_tts(text)
    if not clean:
        return

    if _use_direct:
        _speak_direct(clean)
    else:
        _speak_edge(clean)


def _speak_direct(text: str) -> None:
    import sounddevice as sd

    from core.direct_voice import text_to_speech

    def _run() -> None:
        with _tts_lock:
            audio = text_to_speech(text)
            if audio is not None:
                sd.play(audio, 16000)
                sd.wait()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()


def _speak_edge(text: str) -> None:
    import asyncio
    import tempfile

    import edge_tts
    import sounddevice as sd
    import soundfile as sf

    async def _run() -> None:
        with _tts_lock:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                temp_path = f.name
            try:
                communicate = edge_tts.Communicate(text, VOICE, rate=RATE)
                await communicate.save(temp_path)
                data, samplerate = sf.read(temp_path)
                sd.play(data, samplerate)
                sd.wait()
            finally:
                try:
                    os.unlink(temp_path)
                except Exception as e:
                    log.debug("temp file cleanup error: %s", e)

    def _launch() -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_run())
        finally:
            loop.close()

    thread = threading.Thread(target=_launch, daemon=True)
    thread.start()
