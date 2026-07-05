"""Tests for core TTS, streaming TTS, telegram bot and listener modules."""

import asyncio
import os
import sys
import threading
import types
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest


class _SyncThread:
    def __init__(self, target=None, args=(), kwargs=None, daemon=None):
        self._target = target
        self._args = args
        self._kwargs = kwargs or {}

    def start(self):
        if self._target is not None:
            self._target(*self._args, **self._kwargs)

    def join(self, timeout=None):
        pass

    def is_alive(self):
        return False


class _NoRunThread:
    def __init__(self, *args, **kwargs):
        pass

    def start(self):
        pass

    def join(self, timeout=None):
        pass

    def is_alive(self):
        return False


def _fake_threading(thread_cls):
    fake = types.ModuleType("threading_fake")
    fake.Thread = thread_cls
    fake.Lock = threading.Lock
    fake.Event = threading.Event
    return fake


class TestTTS:
    def test_clean_text_removes_emojis(self):
        from core.tts import clean_text_for_tts

        result = clean_text_for_tts("hola 😀 mundo 🎉")
        assert "😀" not in result
        assert "🎉" not in result
        assert "hola" in result
        assert "mundo" in result

    def test_clean_text_removes_special_symbols(self):
        from core.tts import clean_text_for_tts

        result = clean_text_for_tts("»hola« *check✓ #tag*")
        for ch in ("»", "«", "*", "#", "✓"):
            assert ch not in result

    def test_clean_text_strips_whitespace(self):
        from core.tts import clean_text_for_tts

        assert clean_text_for_tts("   hola   ") == "hola"

    def test_clean_text_all_emojis_returns_empty(self):
        from core.tts import clean_text_for_tts

        assert clean_text_for_tts("😀🎉👏") == ""

    def test_speak_empty_text_does_not_start_thread(self, monkeypatch):
        started = {"v": False}

        class _Spy(_NoRunThread):
            def __init__(self, *a, **k):
                started["v"] = True
                super().__init__(*a, **k)

        monkeypatch.setattr("core.tts.threading", _fake_threading(_Spy))
        from core.tts import speak

        speak("")
        assert started["v"] is False

    def test_speak_only_emojis_returns_early(self, monkeypatch):
        started = {"v": False}

        class _Spy(_NoRunThread):
            def __init__(self, *a, **k):
                started["v"] = True
                super().__init__(*a, **k)

        monkeypatch.setattr("core.tts.threading", _fake_threading(_Spy))
        from core.tts import speak

        speak("😀🎉")
        assert started["v"] is False

    def test_speak_with_mocked_edge_runs_without_crash(self, monkeypatch):
        monkeypatch.setattr("core.tts._use_direct", False)
        monkeypatch.setattr("core.tts.threading", _fake_threading(_SyncThread))

        mock_edge = types.ModuleType("edge_tts")
        communicate = MagicMock()
        communicate.save = AsyncMock()
        mock_edge.Communicate = MagicMock(return_value=communicate)

        mock_sd = types.ModuleType("sounddevice")
        mock_sd.play = MagicMock()
        mock_sd.wait = MagicMock()

        mock_sf = types.ModuleType("soundfile")
        mock_sf.read = MagicMock(return_value=(np.zeros(100, dtype=np.float32), 24000))

        monkeypatch.setitem(sys.modules, "edge_tts", mock_edge)
        monkeypatch.setitem(sys.modules, "sounddevice", mock_sd)
        monkeypatch.setitem(sys.modules, "soundfile", mock_sf)

        from core.tts import speak

        speak("hola mundo")

        communicate.save.assert_awaited_once()
        mock_sd.play.assert_called_once()
        mock_sd.wait.assert_called_once()

    def test_speak_edge_cleans_temp_file_on_error(self, monkeypatch):
        monkeypatch.setattr("core.tts._use_direct", False)
        monkeypatch.setattr("core.tts.threading", _fake_threading(_SyncThread))

        mock_edge = types.ModuleType("edge_tts")
        communicate = MagicMock()
        communicate.save = AsyncMock(side_effect=RuntimeError("tts network fail"))
        mock_edge.Communicate = MagicMock(return_value=communicate)

        mock_sd = types.ModuleType("sounddevice")
        mock_sd.play = MagicMock()
        mock_sd.wait = MagicMock()

        mock_sf = types.ModuleType("soundfile")
        mock_sf.read = MagicMock(return_value=(np.zeros(10, dtype=np.float32), 24000))

        monkeypatch.setitem(sys.modules, "edge_tts", mock_edge)
        monkeypatch.setitem(sys.modules, "sounddevice", mock_sd)
        monkeypatch.setitem(sys.modules, "soundfile", mock_sf)

        unlinked = []
        real_unlink = os.unlink

        def _track_unlink(path, *a, **k):
            unlinked.append(path)
            return real_unlink(path, *a, **k)

        monkeypatch.setattr("core.tts.os", types.SimpleNamespace(unlink=_track_unlink))

        from core.tts import speak

        with pytest.raises(RuntimeError):
            speak("hola")
        assert len(unlinked) == 1
        assert not os.path.exists(unlinked[0])


class TestStreamingTTS:
    def _player_cls(self):
        class _Player:
            def __init__(self, *a, **k):
                self.chunks = []
                self.started = False
                self.stopped = False

            def start_playback(self):
                self.started = True

            def play_chunk(self, data):
                self.chunks.append(data)

            def stop_playback(self):
                self.stopped = True

        return _Player

    def test_init_defaults(self, monkeypatch):
        monkeypatch.setattr("core.streaming_tts.AudioPlayer", self._player_cls())
        from core.streaming_tts import StreamingTTS

        s = StreamingTTS()
        assert s.is_speaking is False
        assert s._player is not None
        assert s._stop_event is not None

    def test_speak_sets_speaking_state(self, monkeypatch):
        monkeypatch.setattr("core.streaming_tts.AudioPlayer", self._player_cls())
        monkeypatch.setattr("core.streaming_tts.threading", _fake_threading(_NoRunThread))
        from core.streaming_tts import StreamingTTS

        s = StreamingTTS()
        assert s.is_speaking is False
        s.speak("hola")
        assert s.is_speaking is True

    def test_stop_clears_state_and_stops_player(self, monkeypatch):
        monkeypatch.setattr("core.streaming_tts.AudioPlayer", self._player_cls())
        monkeypatch.setattr("core.streaming_tts.threading", _fake_threading(_NoRunThread))
        from core.streaming_tts import StreamingTTS

        s = StreamingTTS()
        s.speak("hola")
        player = s._player
        s.stop()
        assert s.is_speaking is False
        assert s._stop_event.is_set() is True
        assert player.stopped is True

    def test_stream_and_play_success(self, monkeypatch):
        monkeypatch.setattr("core.streaming_tts.AudioPlayer", self._player_cls())

        class _Communicate:
            def __init__(self, text, voice, rate):
                pass

            async def stream(self):
                yield {"type": "audio", "data": b"chunk1"}
                yield {"type": "text", "data": b"ignore"}
                yield {"type": "audio", "data": b"chunk2"}

        mock_edge = types.ModuleType("edge_tts")
        mock_edge.Communicate = _Communicate
        monkeypatch.setattr("core.streaming_tts.edge_tts", mock_edge)

        mock_sf = MagicMock()
        mock_sf.read.return_value = (np.zeros(100, dtype=np.float32), 16000)
        monkeypatch.setattr("core.streaming_tts.sf", mock_sf)

        from core.streaming_tts import StreamingTTS

        s = StreamingTTS()
        asyncio.run(s._stream_and_play("hola"))
        assert s.is_speaking is False
        assert s._player.started is True
        assert len(s._player.chunks) == 1

    def test_stream_and_play_handles_error(self, monkeypatch):
        monkeypatch.setattr("core.streaming_tts.AudioPlayer", self._player_cls())

        class _Communicate:
            def __init__(self, text, voice, rate):
                pass

            async def stream(self):
                raise RuntimeError("stream fail")
                yield {"type": "audio", "data": b""}  # pragma: no cover

        mock_edge = types.ModuleType("edge_tts")
        mock_edge.Communicate = _Communicate
        monkeypatch.setattr("core.streaming_tts.edge_tts", mock_edge)
        monkeypatch.setattr("core.streaming_tts.sf", MagicMock())

        from core.streaming_tts import StreamingTTS

        s = StreamingTTS()
        s._is_speaking = True
        asyncio.run(s._stream_and_play("hola"))
        assert s.is_speaking is False


class TestTelegramBot:
    def test_get_token_from_env(self, monkeypatch):
        monkeypatch.setenv("TUTUS_BOT_TOKEN", "env_token_123")
        from core.telegram_bot import _get_token

        assert _get_token() == "env_token_123"

    def test_get_token_missing_returns_empty(self, monkeypatch):
        monkeypatch.delenv("TUTUS_BOT_TOKEN", raising=False)

        class _FakePath:
            def __init__(self, *a, **k):
                pass

            @property
            def parent(self):
                return self

            def __truediv__(self, other):
                return self

            def exists(self):
                return False

            def read_text(self):
                return ""

        monkeypatch.setattr("core.telegram_bot.Path", _FakePath)
        from core.telegram_bot import _get_token

        assert _get_token() == ""

    def test_start_bot_no_token_returns_early(self, monkeypatch):
        monkeypatch.setattr("core.telegram_bot._get_token", lambda: "")
        monkeypatch.setattr("core.telegram_bot._bot_thread", None)
        from core.telegram_bot import start_bot

        start_bot()
        import core.telegram_bot as tb

        assert tb._bot_thread is None

    def test_start_bot_no_telegram_lib(self, monkeypatch):
        monkeypatch.setattr("core.telegram_bot._get_token", lambda: "fake_token")
        monkeypatch.setattr("core.telegram_bot._bot_thread", None)
        monkeypatch.setitem(sys.modules, "telegram.ext", None)
        from core.telegram_bot import start_bot

        start_bot()
        import core.telegram_bot as tb

        assert tb._bot_thread is None

    def test_start_bot_with_mocked_telegram(self, monkeypatch):
        monkeypatch.setattr("core.telegram_bot._get_token", lambda: "fake_token")
        monkeypatch.setattr("core.telegram_bot._bot_thread", None)
        monkeypatch.setattr("core.telegram_bot._application", None)
        monkeypatch.setattr("core.telegram_bot.threading", _fake_threading(_SyncThread))

        fake_tg = types.ModuleType("telegram.ext")

        class _BuiltApp:
            def __init__(self):
                self.handlers = []
                self.polling = False

            def add_handler(self, h):
                self.handlers.append(h)

            def run_polling(self):
                self.polling = True

            def stop(self):
                pass

        class _Builder:
            def token(self, t):
                return self

            def build(self):
                return _BuiltApp()

        class _Application:
            @classmethod
            def builder(cls):
                return _Builder()

        fake_tg.Application = _Application
        fake_tg.MessageHandler = MagicMock()
        fake_tg.filters = MagicMock()
        monkeypatch.setitem(sys.modules, "telegram.ext", fake_tg)

        from core.telegram_bot import start_bot

        start_bot()
        import core.telegram_bot as tb

        assert tb._application is not None
        assert tb._application.polling is True
        assert len(tb._application.handlers) == 1
        assert tb._bot_thread is not None

    def test_stop_bot_calls_stop_when_application_set(self, monkeypatch):
        app = MagicMock()
        monkeypatch.setattr("core.telegram_bot._application", app)
        from core.telegram_bot import stop_bot

        stop_bot()
        app.stop.assert_called_once()

    def test_stop_bot_noop_when_none(self, monkeypatch):
        monkeypatch.setattr("core.telegram_bot._application", None)
        from core.telegram_bot import stop_bot

        stop_bot()

    def test_stop_bot_handles_exception(self, monkeypatch):
        app = MagicMock()
        app.stop.side_effect = RuntimeError("stop fail")
        monkeypatch.setattr("core.telegram_bot._application", app)
        from core.telegram_bot import stop_bot

        stop_bot()

    def test_handle_message_replies_with_route_result(self, monkeypatch):
        monkeypatch.setattr("core.agent_router.route", lambda msg: {"message": "Hola Alice"})

        class _User:
            first_name = "Alice"

        class _Msg:
            def __init__(self):
                self.text = "hola"
                self.replied = None
                self.from_user = _User()

            async def reply_text(self, text):
                self.replied = text

        class _Update:
            def __init__(self):
                self.message = _Msg()

        from core.telegram_bot import _handle_message

        update = _Update()
        asyncio.run(_handle_message(update, None))
        assert update.message.replied == "Hola Alice"

    def test_handle_message_empty_text_no_reply(self, monkeypatch):
        monkeypatch.setattr("core.agent_router.route", lambda msg: {"message": "x"})

        class _User:
            first_name = "A"

        class _Msg:
            def __init__(self):
                self.text = "   "
                self.replied = None
                self.from_user = _User()

            async def reply_text(self, text):
                self.replied = text

        class _Update:
            message = _Msg()

        from core.telegram_bot import _handle_message

        update = _Update()
        asyncio.run(_handle_message(update, None))
        assert update.message.replied is None

    def test_handle_message_route_error_replies_error(self, monkeypatch):
        def _boom(msg):
            raise RuntimeError("route fail")

        monkeypatch.setattr("core.agent_router.route", _boom)

        class _User:
            first_name = "Bob"

        class _Msg:
            def __init__(self):
                self.text = "hola"
                self.replied = None
                self.from_user = _User()

            async def reply_text(self, text):
                self.replied = text

        class _Update:
            def __init__(self):
                self.message = _Msg()

        from core.telegram_bot import _handle_message

        update = _Update()
        asyncio.run(_handle_message(update, None))
        assert update.message.replied is not None
        assert "Error" in update.message.replied or "route fail" in update.message.replied


class TestListener:
    @pytest.fixture
    def listener_env(self, monkeypatch):
        mock_whisper = types.ModuleType("whisper")
        mock_model = MagicMock()
        mock_model.transcribe = MagicMock(return_value={"text": "hola mundo"})
        mock_whisper.load_model = MagicMock(return_value=mock_model)
        monkeypatch.setitem(sys.modules, "whisper", mock_whisper)

        import core.listener as mod

        mock_sd = MagicMock()
        mock_sf = MagicMock()
        monkeypatch.setattr(mod, "sd", mock_sd)
        monkeypatch.setattr(mod, "sf", mock_sf)
        monkeypatch.setattr(mod, "model", mock_model)
        return mod, mock_sd, mock_sf, mock_model

    def test_record_audio_returns_transcription(self, listener_env, monkeypatch):
        mod, sd, sf, model = listener_env
        unlinked = []
        real_unlink = os.unlink

        def _track(path, *a, **k):
            unlinked.append(path)
            return real_unlink(path, *a, **k)

        monkeypatch.setattr(mod, "os", types.SimpleNamespace(unlink=_track))

        text = mod.record_audio(duration=1)
        assert text == "hola mundo"
        model.transcribe.assert_called_once()
        sd.wait.assert_called()
        assert len(unlinked) == 1
        assert not os.path.exists(unlinked[0])

    def test_record_audio_raw_returns_int16(self, listener_env):
        mod, sd, sf, model = listener_env
        sd.rec.return_value = np.zeros((16000, 1), dtype=np.float32)

        audio = mod.record_audio_raw(duration=1)
        assert audio.dtype == np.int16
        assert len(audio) == 16000

    def test_listen_once_invokes_callback(self, listener_env, monkeypatch):
        mod, sd, sf, model = listener_env
        monkeypatch.setattr(mod, "record_audio", lambda duration=5: "hola")
        monkeypatch.setattr(mod, "threading", _fake_threading(_SyncThread))

        called = []
        mod.listen_once(duration=1, callback=lambda t: called.append(t))
        assert called == ["hola"]

    def test_record_audio_transcribe_error_cleans_temp(self, listener_env, monkeypatch):
        mod, sd, sf, model = listener_env
        model.transcribe.side_effect = RuntimeError("whisper fail")
        unlinked = []
        real_unlink = os.unlink

        def _track(path, *a, **k):
            unlinked.append(path)
            return real_unlink(path, *a, **k)

        monkeypatch.setattr(mod, "os", types.SimpleNamespace(unlink=_track))

        with pytest.raises(RuntimeError):
            mod.record_audio(duration=1)
        assert len(unlinked) == 1
        assert not os.path.exists(unlinked[0])
