from __future__ import annotations

import asyncio
import io
import logging
import threading

import edge_tts
import numpy as np
import soundfile as sf

from core.audio_stream import AudioPlayer

log = logging.getLogger("tutus.streaming_tts")


VOICE: str = "es-MX-JorgeNeural"
RATE: str = "+15%"
TARGET_SR: int = 16000


class StreamingTTS:
    def __init__(self, device: int | None = None) -> None:
        self._player: AudioPlayer = AudioPlayer(samplerate=TARGET_SR, device=device)
        self._stop_event: threading.Event = threading.Event()
        self._is_speaking: bool = False

    def speak(self, text: str) -> None:
        self.stop()
        self._stop_event.clear()
        self._is_speaking = True
        thread = threading.Thread(target=self._run_tts, args=(text,), daemon=True)
        thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._player.stop_playback()
        self._is_speaking = False

    @property
    def is_speaking(self) -> bool:
        return self._is_speaking

    def _run_tts(self, text: str) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._stream_and_play(text))
        finally:
            loop.close()

    async def _stream_and_play(self, text: str) -> None:
        try:
            communicate = edge_tts.Communicate(text, VOICE, rate=RATE)
            mp3_buffer = io.BytesIO()

            async for chunk in communicate.stream():
                if self._stop_event.is_set():
                    break
                if chunk["type"] == "audio":
                    mp3_buffer.write(chunk["data"])

            if self._stop_event.is_set():
                self._is_speaking = False
                return

            mp3_buffer.seek(0)
            data, sr = sf.read(mp3_buffer)
            if sr != TARGET_SR:
                from scipy import signal

                ratio = TARGET_SR / sr
                new_len = int(len(data) * ratio)
                data = signal.resample(data, new_len)

            if data.dtype != np.int16:
                data = (data * 32767).astype(np.int16)

            self._player.start_playback()
            self._player.play_chunk(data.tobytes())

            self._is_speaking = False
        except Exception as e:
            log.error("[StreamingTTS] Error: %s", e)
            self._is_speaking = False
