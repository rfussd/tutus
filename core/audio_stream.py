from __future__ import annotations

import queue
import threading
from collections.abc import Callable

import numpy as np
import sounddevice as sd
import torch
from silero_vad import VADIterator, load_silero_vad

SAMPLE_RATE: int = 16000
CHANNELS: int = 1
DTYPE: str = "int16"
FRAME_SIZE: int = 512


class VoiceStream:
    def __init__(self, device: int | None = None):
        self.device: int | None = device
        self._running: bool = False
        self._stream: sd.InputStream | None = None
        self._buffered_audio: list[np.ndarray] = []
        self._speech_start_time: float = 0.0
        self._is_speaking: bool = False
        self._interrupt_enabled: bool = True

        self._vad_model = load_silero_vad()
        self._vad_iterator = VADIterator(
            self._vad_model,
            threshold=0.5,
            sampling_rate=SAMPLE_RATE,
            min_silence_duration_ms=600,
            speech_pad_ms=50,
        )

        self.on_speech_start: Callable[[], None] | None = None
        self.on_speech_end: Callable[[bytes], None] | None = None
        self.on_interrupt: Callable[[], None] | None = None
        self.on_audio_level: Callable[[float], None] | None = None

    def start(self) -> None:
        self._running = True
        self._buffered_audio = []
        self._is_speaking = False
        self._vad_iterator.reset_states()

        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            blocksize=FRAME_SIZE,
            device=self.device,
            callback=self._audio_callback,
        )
        self._stream.start()

    def stop(self) -> None:
        self._running = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    @property
    def is_running(self) -> bool:
        return self._running

    def set_interrupt_enabled(self, enabled: bool) -> None:
        self._interrupt_enabled = enabled

    def reset_vad(self) -> None:
        self._vad_iterator.reset_states()
        self._buffered_audio = []
        self._is_speaking = False

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info: object, status: sd.CallbackFlags) -> None:
        if not self._running:
            return

        audio_int16 = indata.flatten()
        audio_float32 = audio_int16.astype(np.float32) / 32768.0

        level = float(np.sqrt(np.mean(audio_float32**2)))
        if self.on_audio_level:
            self.on_audio_level(level)

        tensor = torch.from_numpy(audio_float32.copy())
        speech_dict = self._vad_iterator(tensor, return_seconds=False)

        if self._is_speaking:
            self._buffered_audio.append(audio_int16.copy())

        if speech_dict is not None:
            if "start" in speech_dict:
                self._is_speaking = True
                self._buffered_audio = [audio_int16.copy()]
                if self.on_speech_start:
                    self.on_speech_start()

            elif "end" in speech_dict:
                self._is_speaking = False
                if self._buffered_audio:
                    full_audio = np.concatenate(self._buffered_audio)
                    audio_bytes = full_audio.tobytes()
                    self._buffered_audio = []

                    if self._interrupt_enabled and self.on_interrupt:
                        self.on_interrupt()

                    if self.on_speech_end:
                        self.on_speech_end(audio_bytes)


class AudioPlayer:
    def __init__(self, samplerate: int = 24000, device: int | None = None):
        self.samplerate: int = samplerate
        self.device: int | None = device
        self._queue: queue.Queue[bytes] = queue.Queue()
        self._stop_event: threading.Event = threading.Event()
        self._thread: threading.Thread | None = None
        self._stream: sd.OutputStream | None = None

    def play_chunk(self, audio_data: bytes) -> None:
        self._queue.put(audio_data)

    def start_playback(self) -> None:
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._playback_loop, daemon=True)
        self._thread.start()

    def stop_playback(self) -> None:
        self._stop_event.set()
        sd.stop()
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

    def _playback_loop(self) -> None:
        empty_cycles = 0
        while not self._stop_event.is_set():
            try:
                data = self._queue.get(timeout=0.1)
                empty_cycles = 0
                if self._stop_event.is_set():
                    break
            except queue.Empty:
                empty_cycles += 1
                if empty_cycles > 10:
                    break
                continue

            audio_np = np.frombuffer(data, dtype=np.int16)

            if self._stream is None:
                self._stream = sd.OutputStream(
                    samplerate=self.samplerate,
                    channels=1,
                    dtype="int16",
                    device=self.device,
                )
                self._stream.start()

            self._stream.write(audio_np)

        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
