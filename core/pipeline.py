from __future__ import annotations

import logging
import threading
from typing import Any

from PyQt6.QtCore import QObject, pyqtSignal

log = logging.getLogger("tutus.pipeline")


class PipelineStage(QObject):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)


class SttStage(PipelineStage):
    done = pyqtSignal(str)

    def run(self, duration: int = 5) -> None:
        def _run() -> None:
            try:
                from core.listener import record_audio

                text = record_audio(duration)
                self.done.emit(text)
            except Exception as e:
                self.error.emit(str(e))

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()


class TtsStage(PipelineStage):
    done = pyqtSignal()

    def run(self, text: str) -> None:
        from core.tts import speak

        def _run() -> None:
            try:
                speak(text)
                self.done.emit()
            except Exception as e:
                self.error.emit(str(e))

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()


class RouterStage(PipelineStage):
    response_ready = pyqtSignal(dict)
    token_ready = pyqtSignal(str)

    def run(self, message: str, stream: bool = True) -> None:
        from core.agent_router import route

        def _run() -> None:
            try:
                result = route(message, on_token=self._on_token if stream else None)
                self.response_ready.emit(result)
            except Exception as e:
                self.error.emit(str(e))

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()

    def _on_token(self, token: str) -> None:
        self.token_ready.emit(token)


class AsyncPipeline(QObject):
    voice_input_ready = pyqtSignal(str)
    response_ready = pyqtSignal(dict)
    token_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self._stt: SttStage = SttStage()
        self._router: RouterStage = RouterStage()
        self._tts: TtsStage = TtsStage()

        self._stt.done.connect(self._on_stt_done)
        self._router.response_ready.connect(self._on_router_done)
        self._router.token_ready.connect(self._on_token)

    def process_voice(self, duration: int = 5) -> None:
        self._stt.run(duration)

    def process_text(self, text: str) -> None:
        self._router.run(text)

    def speak(self, text: str) -> None:
        self._tts.run(text)

    def _on_stt_done(self, text: str) -> None:
        self.voice_input_ready.emit(text)

    def _on_router_done(self, result: dict[str, Any]) -> None:
        self.response_ready.emit(result)

    def _on_token(self, token: str) -> None:
        self.token_ready.emit(token)

    def _on_error(self, msg: str) -> None:
        self.error_occurred.emit(msg)


class ContinuousVoiceEngine(QObject):
    speech_ready = pyqtSignal(str)
    response_ready = pyqtSignal(dict)
    token_ready = pyqtSignal(str)
    audio_level = pyqtSignal(float)
    listening_state = pyqtSignal(bool)
    speaking_state = pyqtSignal(bool)
    error_occurred = pyqtSignal(str)

    def __init__(self, mic_device: int | None = None, speaker_device: int | None = None) -> None:
        super().__init__()
        self._mic_device: int | None = mic_device
        self._speaker_device: int | None = speaker_device
        self._voice_stream: Any = None
        self._streaming_tts: Any = None
        self._running: bool = False
        self._processing: bool = False

    def start(self) -> None:
        if self._running:
            return

        from core.audio_stream import VoiceStream
        from core.streaming_tts import StreamingTTS

        self._voice_stream = VoiceStream(device=self._mic_device)
        self._voice_stream.on_audio_level = self._on_audio_level
        self._voice_stream.on_speech_start = self._on_speech_start
        self._voice_stream.on_speech_end = self._on_speech_end
        self._voice_stream.on_interrupt = self._on_interrupt

        self._streaming_tts = StreamingTTS(device=self._speaker_device)

        self._running = True
        self._voice_stream.start()

    def stop(self) -> None:
        self._running = False
        if self._streaming_tts:
            self._streaming_tts.stop()
        if self._voice_stream:
            self._voice_stream.stop()

    @property
    def is_running(self) -> bool:
        return self._running

    def _on_audio_level(self, level: float) -> None:
        self.audio_level.emit(level)

    def _on_speech_start(self) -> None:
        log.debug("Speech start")
        if self._streaming_tts and self._streaming_tts.is_speaking:
            self._streaming_tts.stop()
            self.speaking_state.emit(False)
        self.listening_state.emit(True)

    def _on_speech_end(self, audio_bytes: bytes) -> None:
        self.listening_state.emit(False)
        self._voice_stream.set_interrupt_enabled(True)
        if self._processing:
            return
        self._processing = True

        def transcribe_and_route() -> None:
            try:
                import numpy as np

                from core.listener import model as whisper_model

                audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
                result = whisper_model.transcribe(audio_np, language="es")
                text = result["text"].strip()

                if not text:
                    self._processing = False
                    return

                log.info("STT: %s", text)
                self.speech_ready.emit(text)
                self._route(text)
            except Exception as e:
                log.error("STT error: %s", e)
                self._processing = False
                self.error_occurred.emit(str(e))

        thread = threading.Thread(target=transcribe_and_route, daemon=True)
        thread.start()

    def _route(self, text: str) -> None:
        from core.agent_router import route

        def on_tok(tok: str) -> None:
            self.token_ready.emit(tok)

        try:
            result = route(text, on_token=on_tok)
            self.response_ready.emit(result)
            self._speak_result(result)
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            self._processing = False

    def _speak_result(self, result: dict[str, Any]) -> None:
        message = result.get("message", "")
        if not message:
            return
        self.speaking_state.emit(True)
        self._streaming_tts.speak(message)

    def _on_interrupt(self) -> None:
        if self._streaming_tts and self._streaming_tts.is_speaking:
            log.debug("Interruption!")
            self._streaming_tts.stop()
            self.speaking_state.emit(False)
