"""Tests for whatsapp_bot, context_monitor, and audio_stream modules."""

from __future__ import annotations

import sys
import types
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# Helpers: mock heavy modules before import
# ---------------------------------------------------------------------------


def _mock_module(name, **attrs):
    if name not in sys.modules:
        mod = types.ModuleType(name)
        for k, v in attrs.items():
            setattr(mod, k, v)
        sys.modules[name] = mod


def _mock_playwright():
    _mock_module("playwright")
    sub = types.ModuleType("playwright.sync_api")
    sub.sync_playwright = lambda: None
    sys.modules["playwright.sync_api"] = sub


def _mock_mss():
    _mock_module("mss")
    _mock_module("PIL", Image=type("Image", (), {"frombytes": lambda *a, **kw: None, "thumbnail": lambda *a: None}))


def _mock_sounddevice():
    _mock_module(
        "sounddevice",
        InputStream=lambda *a, **kw: None,
        OutputStream=lambda *a, **kw: None,
        stop=lambda: None,
        CallbackFlags=type("CallbackFlags", (), {}),
    )


def _mock_torch():
    _mock_module("torch", from_numpy=lambda x: x, tensor=lambda x: x)


def _mock_silero_vad():
    _mock_module(
        "silero_vad",
        load_silero_vad=lambda: None,
        VADIterator=type(
            "VADIterator",
            (),
            {"reset_states": lambda self: None, "__call__": lambda self, *a, **kw: None, "__init__": lambda self, *a, **kw: None},
        ),
    )


# ---------------------------------------------------------------------------
# Context Monitor
# ---------------------------------------------------------------------------


class TestClassifyWindow:
    def test_coding_editor(self):
        _mock_mss()
        from core.context_monitor import _classify_window

        result = _classify_window("main.py - VS Code", "code.exe")
        assert result["context"] == "coding"
        assert result["app"] == "editor"

    def test_browser(self):
        _mock_mss()
        from core.context_monitor import _classify_window

        for proc in ("chrome.exe", "edge.exe", "firefox.exe", "brave.exe"):
            result = _classify_window("Google", proc)
            assert result["context"] == "browsing"

    def test_terminal(self):
        _mock_mss()
        from core.context_monitor import _classify_window

        for title in ("PowerShell", "cmd.exe", "Terminal"):
            result = _classify_window(title, "WindowsTerminal.exe")
            assert result["context"] == "terminal"

    def test_email(self):
        _mock_mss()
        from core.context_monitor import _classify_window

        result = _classify_window("Inbox - Outlook", "outlook.exe")
        assert result["context"] == "email"

    def test_office(self):
        _mock_mss()
        from core.context_monitor import _classify_window

        result = _classify_window("Documento1 - Word", "winword.exe")
        assert result["context"] == "office"

    def test_music(self):
        _mock_mss()
        from core.context_monitor import _classify_window

        result = _classify_window("Spotify", "spotify.exe")
        assert result["context"] == "music"

    def test_other(self):
        _mock_mss()
        from core.context_monitor import _classify_window

        result = _classify_window("Random App", "random.exe")
        assert result["context"] == "other"


class TestShouldSuggest:
    def setup_method(self):
        _mock_mss()
        import core.context_monitor as cm

        cm._COOLDOWN_TRACKER.clear()

    def test_first_suggestion_allowed(self):
        import core.context_monitor as cm

        cm._COOLDOWN_TRACKER.clear()
        assert cm._should_suggest("test_key") is True

    def test_second_suggestion_blocked_within_cooldown(self):
        import core.context_monitor as cm

        cm._COOLDOWN_TRACKER.clear()
        cm._should_suggest("test_key")
        assert cm._should_suggest("test_key") is False

    def test_suggestion_allowed_after_cooldown(self):
        import core.context_monitor as cm

        cm._COOLDOWN_TRACKER.clear()
        cm._should_suggest("test_key")
        # Simulate past time
        cm._COOLDOWN_TRACKER["test_key"] = datetime.now() - timedelta(minutes=20)
        assert cm._should_suggest("test_key", cooldown_min=10) is True


class TestDetectOpportunities:
    def setup_method(self):
        _mock_mss()
        import core.context_monitor as cm

        cm._COOLDOWN_TRACKER.clear()
        cm.on_opportunity = None

    def test_coding_opportunity(self):
        import core.context_monitor as cm

        cm._COOLDOWN_TRACKER.clear()

        received = []
        cm.on_opportunity = lambda ctx, msg: received.append((ctx, msg))
        cm._detect_window_opportunity("main.py", "code.exe", "coding", "editor")
        assert len(received) == 1
        assert received[0][0] == "codigo"

    def test_terminal_opportunity(self):
        import core.context_monitor as cm

        cm._COOLDOWN_TRACKER.clear()

        received = []
        cm.on_opportunity = lambda ctx, msg: received.append((ctx, msg))
        cm._detect_window_opportunity("PowerShell", "cmd.exe", "terminal", "terminal")
        assert len(received) == 1
        assert received[0][0] == "terminal"

    def test_clipboard_error(self):
        import core.context_monitor as cm

        cm._COOLDOWN_TRACKER.clear()

        received = []
        cm.on_opportunity = lambda ctx, msg: received.append((ctx, msg))
        cm._detect_clipboard_opportunity("Traceback: SyntaxError: invalid syntax")
        assert len(received) == 1
        assert received[0][0] == "error"

    def test_clipboard_long_text(self):
        import core.context_monitor as cm

        cm._COOLDOWN_TRACKER.clear()

        received = []
        cm.on_opportunity = lambda ctx, msg: received.append((ctx, msg))
        cm._detect_clipboard_opportunity("x" * 300)
        assert any(r[0] == "texto_largo" for r in received)

    def test_no_callback_no_crash(self):
        import core.context_monitor as cm

        cm._COOLDOWN_TRACKER.clear()
        cm.on_opportunity = None
        cm._detect_window_opportunity("main.py", "code.exe", "coding", "editor")
        cm._detect_clipboard_opportunity("error message")


class TestMonitorLifecycle:
    def test_start_stop(self):
        _mock_mss()
        import core.context_monitor as cm

        cm._running = False
        cm.start_monitoring()
        assert cm._running is True
        cm.stop_monitoring()
        assert cm._running is False

    def test_double_start_noop(self):
        _mock_mss()
        import core.context_monitor as cm

        cm._running = True
        cm.start_monitoring()  # should not crash
        assert cm._running is True
        cm._running = False


# ---------------------------------------------------------------------------
# WhatsApp Bot
# ---------------------------------------------------------------------------


class TestWhatsAppBot:
    def test_stop_without_start(self):
        _mock_playwright()
        import skills.whatsapp_bot as wb

        wb._page = None
        wb._browser = None
        wb._playwright = None
        wb.stop_whatsapp()  # should not crash

    def test_stop_with_mock_page(self):
        _mock_playwright()
        import skills.whatsapp_bot as wb

        class MockPage:
            def is_closed(self):
                return False

            def close(self):
                pass

        class MockBrowser:
            def close(self):
                pass

        class MockPlaywright:
            def stop(self):
                pass

        wb._page = MockPage()
        wb._browser = MockBrowser()
        wb._playwright = MockPlaywright()
        wb.stop_whatsapp()
        assert wb._page is None
        assert wb._browser is None
        assert wb._playwright is None


# ---------------------------------------------------------------------------
# Audio Stream
# ---------------------------------------------------------------------------


class TestAudioPlayer:
    def test_create(self):
        _mock_sounddevice()
        _mock_torch()
        _mock_silero_vad()
        from core.audio_stream import AudioPlayer

        player = AudioPlayer()
        assert player.samplerate == 24000
        assert player.device is None

    def test_play_chunk(self):
        _mock_sounddevice()
        _mock_torch()
        _mock_silero_vad()
        from core.audio_stream import AudioPlayer

        player = AudioPlayer()
        player.play_chunk(b"\x00\x00" * 100)
        assert not player._queue.empty()

    def test_stop_playback(self):
        _mock_sounddevice()
        _mock_torch()
        _mock_silero_vad()
        from core.audio_stream import AudioPlayer

        player = AudioPlayer()
        player.play_chunk(b"\x00\x00" * 100)
        player.stop_playback()
        assert player._stop_event.is_set()

    def test_start_playback(self):
        _mock_sounddevice()
        _mock_torch()
        _mock_silero_vad()
        from core.audio_stream import AudioPlayer

        player = AudioPlayer()
        player.start_playback()
        assert player._thread is not None
        player.stop_playback()


class TestVoiceStream:
    def test_create(self):
        _mock_sounddevice()
        _mock_torch()
        _mock_silero_vad()
        from core.audio_stream import VoiceStream

        stream = VoiceStream()
        assert stream.is_running is False
        assert stream.device is None

    def test_set_interrupt(self):
        _mock_sounddevice()
        _mock_torch()
        _mock_silero_vad()
        from core.audio_stream import VoiceStream

        stream = VoiceStream()
        stream.set_interrupt_enabled(False)
        assert stream._interrupt_enabled is False
        stream.set_interrupt_enabled(True)
        assert stream._interrupt_enabled is True
