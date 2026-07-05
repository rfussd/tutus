from __future__ import annotations

import os
import threading
import time
from collections.abc import Callable
from typing import Any

from core.log import setup_logger

log = setup_logger("tutus.engine")


# ── Service: Startup ─────────────────────────────────────────────────────────


class StartupService:
    """Arranque asíncrono de LM Studio, modelo, plugins, RAG y LoRA."""

    def __init__(self) -> None:
        self._ready: threading.Event = threading.Event()

    @property
    def is_ready(self) -> bool:
        return self._ready.is_set()

    def wait_ready(self, timeout: float | None = None) -> bool:
        return self._ready.wait(timeout)

    def run(self, on_progress: Callable[[str], None] | None = None) -> None:
        """Ejecuta todo el bootstrap en el hilo actual."""

        def _progress(msg: str) -> None:
            log.info(msg)
            if on_progress:
                on_progress(msg)

        try:
            from core.config import LM_STUDIO_BASE, LORA_ENABLED, MODEL_ID
        except Exception as e:
            _progress(f"Error cargando config: {e}")
            return

        _progress("Iniciando LM Studio...")
        self._start_lmstudio()

        _progress("Cargando modelo...")
        self._load_model(MODEL_ID)

        _progress("Esperando servidor LM Studio...")
        lmstudio_ok = self._wait_for_lmstudio(LM_STUDIO_BASE)
        if not lmstudio_ok:
            _progress("LM Studio no disponible — modo offline parcial")

        _progress("Inicializando plugins...")
        self._init_plugins()

        _progress("Indexando documentos (RAG)...")
        self._init_rag()

        if LORA_ENABLED:
            _progress("Cargando adaptador LoRA...")
            self._init_lora()

        self._ready.set()
        _progress("TUTUS v2.0 activo")

    @staticmethod
    def _start_lmstudio() -> None:
        try:
            from core.startup import start_lmstudio

            start_lmstudio()
        except Exception as e:
            log.warning("Error iniciando LM Studio: %s", e)

    @staticmethod
    def _load_model(model_id: str) -> None:
        lms = os.path.expanduser(r"~\.lmstudio\bin\lms.exe")
        if os.path.exists(lms):
            import subprocess

            subprocess.Popen([lms, "load", model_id, "--gpu", "max"], creationflags=subprocess.CREATE_NO_WINDOW)

    @staticmethod
    def _wait_for_lmstudio(base_url: str, max_attempts: int = 40) -> bool:
        try:
            import requests
        except ImportError:
            log.warning("requests no instalado — saltando espera LM Studio")
            return False
        models_url = f"{base_url}/v1/models"
        for i in range(max_attempts):
            try:
                r = requests.get(models_url, timeout=3)
                if r.status_code == 200:
                    models = r.json().get("data", [])
                    if models:
                        log.info("LM Studio listo → %s", models[0]["id"])
                        return True
                    log.info("Modelos disponibles, esperando carga... (%d/%d)", i + 1, max_attempts)
                    continue
            except (requests.ConnectionError, requests.Timeout) as e:
                log.debug("LM Studio connection error: %s", e)
            except Exception as e:
                log.debug("LM Studio wait error: %s", e)
            log.info("Esperando LM Studio... (%d/%d)", i + 1, max_attempts)
            time.sleep(3)
        log.error("LM Studio no respondió")
        return False

    @staticmethod
    def _init_plugins() -> None:
        try:
            from core.plugin_loader import load_all_plugins

            loaded = load_all_plugins()
            if loaded:
                log.info("Plugins cargados: %s", ", ".join(loaded))
        except Exception as e:
            log.warning("Error cargando plugins: %s", e)

    @staticmethod
    def _init_rag() -> None:
        try:
            from core.rag import index_documents_folder

            result = index_documents_folder()
            if result and "No" not in result:
                log.info("%s", result)
        except Exception as e:
            log.debug("RAG index opcional: %s", e)

    @staticmethod
    def _init_lora() -> None:
        try:
            from core.lora_loader import load_lora_adapter

            if load_lora_adapter():
                log.info("LoRA adaptador cargado")
            else:
                log.info("LoRA: skip (sin adaptador)")
        except Exception as e:
            log.warning("Error cargando LoRA: %s", e)


# ── Service: Voice ───────────────────────────────────────────────────────────


class VoiceService:
    """Grabación, transcripción y modo continuo."""

    def __init__(self) -> None:
        self._continuous_voice: dict[str, Any] | None = None

    @property
    def is_continuous_active(self) -> bool:
        return self._continuous_voice is not None

    def process_voice(
        self,
        duration: int = 5,
        *,
        on_text: Callable[[str], None] | None = None,
        on_token: Callable[[str], None] | None = None,
        on_done: Callable[[dict[str, Any]], None] | None = None,
    ) -> threading.Thread:
        def _run() -> None:
            try:
                from core.listener import record_audio
            except ImportError as e:
                log.error("voice deps not available: %s", e)
                if on_text:
                    on_text("")
                return
            try:
                text = record_audio(duration)
                if on_text:
                    on_text(text)
                if text and text.strip():
                    self._route_text(text, on_token=on_token, on_done=on_done)
            except Exception as e:
                log.error("process_voice error: %s", e)

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        return t

    @staticmethod
    def _route_text(
        text: str, *, on_token: Callable[[str], None] | None = None, on_done: Callable[[dict[str, Any]], None] | None = None
    ) -> None:
        from core.agent_router import route

        try:
            result = route(text, on_token=on_token)
            if on_done:
                on_done(result)
        except Exception as e:
            log.error("route error: %s", e)
            if on_done:
                on_done({"domain": "chat", "message": f"Error: {e}"})

    def start_continuous(
        self,
        *,
        on_speech: Callable[[str], None] | None = None,
        on_token: Callable[[str], None] | None = None,
        on_response: Callable[[dict[str, Any]], None] | None = None,
        on_level: Callable[[float], None] | None = None,
        on_listening: Callable[[bool], None] | None = None,
        on_speaking: Callable[[bool], None] | None = None,
    ) -> None:
        if self._continuous_voice:
            return

        try:
            from core.audio_stream import VoiceStream
            from core.streaming_tts import StreamingTTS
        except ImportError as e:
            log.error("continuous voice deps not available: %s", e)
            return

        vs = VoiceStream()
        tts = StreamingTTS()

        data = {"stream": vs, "tts": tts, "processing": False}
        self._continuous_voice = data

        vs.on_audio_level = lambda v: on_level(v) if on_level else None
        vs.on_speech_start = lambda: self._on_cont_speech_start(tts, on_listening, on_speaking)
        vs.on_speech_end = lambda audio: self._on_cont_speech_end(
            audio, tts, on_speech, on_token, on_response, on_listening, on_speaking, data
        )
        vs.start()

    def stop_continuous(self) -> None:
        if not self._continuous_voice:
            return
        data = self._continuous_voice
        try:
            data["stream"].stop()
        except Exception as e:
            log.debug("stream stop error: %s", e)
        try:
            data["tts"].stop()
        except Exception as e:
            log.debug("tts stop error: %s", e)
        self._continuous_voice = None

    @staticmethod
    def _on_cont_speech_start(tts: Any, on_listening: Callable[[bool], None] | None, on_speaking: Callable[[bool], None] | None) -> None:
        try:
            if tts.is_speaking:
                tts.stop()
                if on_speaking:
                    on_speaking(False)
        except Exception as e:
            log.debug("speech start error: %s", e)
        if on_listening:
            on_listening(True)

    def _on_cont_speech_end(
        self,
        audio_bytes: bytes,
        tts: Any,
        on_speech: Callable[[str], None] | None,
        on_token: Callable[[str], None] | None,
        on_response: Callable[[dict[str, Any]], None] | None,
        on_listening: Callable[[bool], None] | None,
        on_speaking: Callable[[bool], None] | None,
        data: dict[str, Any],
    ) -> None:
        if on_listening:
            on_listening(False)
        if data.get("processing"):
            return
        data["processing"] = True

        def transcribe() -> None:
            try:
                import numpy as np

                from core.listener import model as whisper_model

                audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
                result = whisper_model.transcribe(audio_np, language="es")
                text = result["text"].strip()

                if not text:
                    data["processing"] = False
                    return

                log.info("STT: %s", text)
                if on_speech:
                    on_speech(text)

                self._route_text(text, on_token=on_token, on_done=lambda r: self._on_cont_result(r, tts, on_response, on_speaking, data))
            except Exception as e:
                log.error("STT error: %s", e)
                data["processing"] = False

        threading.Thread(target=transcribe, daemon=True).start()

    @staticmethod
    def _on_cont_result(
        result: dict[str, Any],
        tts: Any,
        on_response: Callable[[dict[str, Any]], None] | None,
        on_speaking: Callable[[bool], None] | None,
        data: dict[str, Any],
    ) -> None:
        try:
            message = result.get("message", "")
            if on_response:
                on_response(result)
            if message and tts:
                if on_speaking:
                    on_speaking(True)
                tts.speak(message)
        except Exception as e:
            log.error("cont result error: %s", e)
        finally:
            data["processing"] = False


# ── Service: Background ──────────────────────────────────────────────────────


class BackgroundService:
    """Servicios de fondo: proactivo, recordatorios, monitor, telegram, web."""

    @staticmethod
    def start_proactive(on_suggestion: Callable[[str, dict[str, Any]], None]) -> None:
        try:
            from core.proactive import start_proactive_engine

            start_proactive_engine(on_suggestion)
        except Exception as e:
            log.warning("proactive engine: %s", e)

    @staticmethod
    def start_reminders(on_notify: Callable[[str], None]) -> None:
        try:
            from core.reminder import start_reminder_engine

            start_reminder_engine(on_notify)
        except Exception as e:
            log.warning("reminder engine: %s", e)

    @staticmethod
    def start_context_monitor(on_opportunity: Callable[[str, str], None]) -> None:
        try:
            import core.context_monitor as cm

            cm.on_opportunity = on_opportunity
            cm.start_monitoring()
        except Exception as e:
            log.warning("context monitor: %s", e)

    @staticmethod
    def start_telegram_bot() -> None:
        try:
            from core.telegram_bot import start_bot

            start_bot()
        except Exception as e:
            log.warning("telegram bot: %s", e)

    @staticmethod
    def start_web_server(host: str = "0.0.0.0", port: int = 8080) -> threading.Thread | None:
        try:
            import asyncio

            import uvicorn

            from web.server import app
        except ImportError as e:
            log.warning("web server deps not available: %s", e)
            return None

        def _run() -> None:
            config = uvicorn.Config(app, host=host, port=port, log_level="warning")
            config.install_signal_handlers = False  # type: ignore[attr-defined]
            server = uvicorn.Server(config)
            try:
                asyncio.run(server.serve())
            except Exception as e:
                log.warning("Web server stopped: %s", e)

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        return t

    @staticmethod
    def get_web_ip() -> str:
        try:
            from web.server import get_local_ip

            return get_local_ip()
        except Exception as e:
            log.debug("get_web_ip error: %s", e)
            return "127.0.0.1"


# ── Facade ───────────────────────────────────────────────────────────────────


class TutusEngine:
    """Orquestador principal — fachada sobre servicios especializados."""

    def __init__(self) -> None:
        self.startup: StartupService = StartupService()
        self.voice: VoiceService = VoiceService()
        self.background: BackgroundService = BackgroundService()

    # ── Lifecycle ───────────────────────────────────────────────────────────

    def bootstrap(self, on_progress: Callable[[str], None] | None = None) -> None:
        """Arranque completo en el hilo actual."""
        self.startup.run(on_progress=on_progress)

    def bootstrap_async(self, on_progress: Callable[[str], None] | None = None) -> threading.Thread:
        """Arranque en hilo separado (no bloquea UI)."""
        t = threading.Thread(target=self.bootstrap, args=(on_progress,), daemon=True)
        t.start()
        return t

    @property
    def is_ready(self) -> bool:
        return self.startup.is_ready

    # ── Conversation Buffer ─────────────────────────────────────────────────

    @staticmethod
    def add_to_buffer(role: str, text: str) -> None:
        try:
            from core.conversation import add_to_buffer as _add

            _add(role, text)
        except Exception as e:
            log.warning("add_to_buffer: %s", e)

    @staticmethod
    def detect_multi_intent(text: str) -> list[str]:
        try:
            from core.orchestrator import detect_multi_intent

            return detect_multi_intent(text)
        except Exception as e:
            log.debug("detect_multi_intent error: %s", e)
            return []

    @staticmethod
    def route_parallel(messages: list[str]) -> list[dict[str, Any]]:
        try:
            from core.orchestrator import route_parallel

            return route_parallel(messages)
        except Exception as e:
            log.debug("route_parallel error: %s", e)
            return []

    # ── Text ────────────────────────────────────────────────────────────────

    def process_text(
        self, text: str, *, on_token: Callable[[str], None] | None = None, on_done: Callable[[dict[str, Any]], None] | None = None
    ) -> threading.Thread:
        def _run() -> None:
            from core.agent_router import route

            try:
                result = route(text, on_token=on_token)
                if on_done:
                    on_done(result)
            except Exception as e:
                log.error("process_text error: %s", e)
                if on_done:
                    on_done({"domain": "chat", "message": f"Error: {e}"})

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        return t

    # ── Voice (delegado a VoiceService) ─────────────────────────────────────

    @property
    def is_continuous_active(self) -> bool:
        return self.voice.is_continuous_active

    def process_voice(self, **kwargs: Any) -> threading.Thread:
        return self.voice.process_voice(**kwargs)

    def start_continuous(self, **kwargs: Any) -> None:
        self.voice.start_continuous(**kwargs)

    def stop_continuous(self) -> None:
        self.voice.stop_continuous()

    # ── Background (delegado a BackgroundService) ───────────────────────────

    def start_proactive(self, on_suggestion: Callable[[str, dict[str, Any]], None]) -> None:
        self.background.start_proactive(on_suggestion)

    def start_reminders(self, on_notify: Callable[[str], None]) -> None:
        self.background.start_reminders(on_notify)

    def start_context_monitor(self, on_opportunity: Callable[[str, str], None]) -> None:
        self.background.start_context_monitor(on_opportunity)

    def start_telegram_bot(self) -> None:
        self.background.start_telegram_bot()

    def start_web_server(self, host: str = "0.0.0.0", port: int = 8080) -> threading.Thread | None:
        return self.background.start_web_server(host, port)

    @staticmethod
    def get_web_ip() -> str:
        return BackgroundService.get_web_ip()
