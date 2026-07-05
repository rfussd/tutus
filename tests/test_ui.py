from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestTutusAvatar:
    def test_create(self, qapp):
        from ui.avatar import TutusAvatar

        w = TutusAvatar()
        assert w.parent() is None
        w.close()

    def test_set_state(self, qapp):
        from ui.avatar import TutusAvatar

        w = TutusAvatar()
        w.set_state("idle")
        w.set_state("listening")
        w.set_state("speaking")
        w.set_state("thinking")
        w.close()

    def test_set_audio_level(self, qapp):
        from ui.avatar import TutusAvatar

        w = TutusAvatar()
        w.set_audio_level(0.5)
        w.set_audio_level(1.0)
        w.set_audio_level(0.0)
        w.close()


class TestChatData:
    def test_chat_message(self):
        from ui.chat_data import ChatMessage

        msg = ChatMessage(role="user", text="hola", sender="test")
        assert msg.role == "user"
        assert msg.text == "hola"
        assert isinstance(msg.timestamp, float)

    def test_format_time(self):
        from ui.chat_data import format_time

        t = format_time()
        assert isinstance(t, str)
        assert len(t) > 0

    def test_format_time_with_arg(self):
        import time

        from ui.chat_data import format_time

        t = format_time(time.time())
        assert isinstance(t, str)


class TestMarkdownBrowser:
    def test_create(self, qapp):
        from ui.markdown_browser import MarkdownBrowser

        w = MarkdownBrowser()
        assert w.parent() is None
        w.close()

    def test_set_streaming(self, qapp):
        from ui.markdown_browser import MarkdownBrowser

        w = MarkdownBrowser()
        w.set_streaming("test **bold**")
        w.close()

    def test_set_markdown(self, qapp):
        from ui.markdown_browser import MarkdownBrowser

        w = MarkdownBrowser()
        w.set_markdown("# Title\n\nParagraph")
        w.close()


class TestChatBubble:
    def test_create(self, qapp):
        from ui.chat_bubble import ChatBubble
        from ui.chat_data import ChatMessage

        msg = ChatMessage(role="user", text="hola", sender="user")
        w = ChatBubble(msg)
        assert w.parent() is None
        w.close()

    def test_message_property(self, qapp):
        from ui.chat_bubble import ChatBubble
        from ui.chat_data import ChatMessage

        msg = ChatMessage(role="assistant", text="respuesta", sender="tutus")
        w = ChatBubble(msg)
        assert w.message().text == "respuesta"
        assert w.message().role == "assistant"
        w.close()

    def test_double_click_copies(self, qapp):
        from ui.chat_bubble import ChatBubble
        from ui.chat_data import ChatMessage

        msg = ChatMessage(role="assistant", text="test copy", sender="tutus")
        w = ChatBubble(msg)
        received = []

        def on_copy(text):
            received.append(text)

        w.copy_requested.connect(on_copy)

        from PyQt6.QtCore import QEvent, QPointF
        from PyQt6.QtGui import QMouseEvent

        center = QPointF(w.rect().center())
        event = QMouseEvent(
            QEvent.Type.MouseButtonDblClick,
            center,
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        w.mouseDoubleClickEvent(event)
        w.close()


class TestChatScrollArea:
    def test_create(self, qapp):
        from ui.chat_area import ChatScrollArea

        w = ChatScrollArea()
        assert w.parent() is None
        w.close()

    def test_add_bubble(self, qapp):
        from ui.chat_area import ChatScrollArea
        from ui.chat_bubble import ChatBubble
        from ui.chat_data import ChatMessage

        area = ChatScrollArea()
        msg = ChatMessage(role="user", text="hola", sender="user")
        bubble = ChatBubble(msg)
        area.add_bubble(bubble)
        area.close()

    def test_clear_all(self, qapp):
        from ui.chat_area import ChatScrollArea
        from ui.chat_bubble import ChatBubble
        from ui.chat_data import ChatMessage

        area = ChatScrollArea()
        msg = ChatMessage(role="user", text="hola", sender="user")
        for _ in range(3):
            area.add_bubble(ChatBubble(msg))
        area.clear_all()
        area.close()

    def test_scroll_to_bottom(self, qapp):
        from ui.chat_area import ChatScrollArea
        from ui.chat_bubble import ChatBubble
        from ui.chat_data import ChatMessage

        area = ChatScrollArea()
        msg = ChatMessage(role="user", text="hola", sender="user")
        for _ in range(5):
            area.add_bubble(ChatBubble(msg))
        area.scroll_to_bottom_now()
        area.close()


class TestPulseLabel:
    def test_create(self, qapp):
        from ui.indicators import PulseLabel

        w = PulseLabel("test")
        assert w.text() == "test"
        assert w._opacity == 1.0
        assert w._dir == -1
        w.close()

    def test_pulse_changes_opacity(self, qapp):
        from ui.indicators import PulseLabel

        w = PulseLabel("pulse")
        old = w._opacity
        w._pulse()
        assert w._opacity < old
        w.close()


class TestTypingIndicator:
    def test_create(self, qapp):
        from ui.indicators import TypingIndicator

        w = TypingIndicator()
        assert w.parent() is None
        assert w.isHidden()
        w.close()

    def test_start_shows_widget(self, qapp):
        from ui.indicators import TypingIndicator

        w = TypingIndicator()
        w.start()
        assert w.isVisible()
        assert w._timer.isActive()
        w.stop()

    def test_stop_hides_widget(self, qapp):
        from ui.indicators import TypingIndicator

        w = TypingIndicator()
        w.start()
        assert w.isVisible()
        w.stop()
        assert w.isHidden()
        assert not w._timer.isActive()
        w.close()

    def test_update_changes_text(self, qapp):
        from ui.indicators import TypingIndicator

        w = TypingIndicator()
        w._dots = 0
        w._update()
        assert "◈ TUTUS pensando" in w.text()
        assert w.text().endswith(".")

        w._dots = 2
        w._update()
        assert w.text().endswith("...")
        w.close()

    def test_update_cycles_correctly(self, qapp):
        from ui.indicators import TypingIndicator

        w = TypingIndicator()
        w._dots = 3
        w._update()
        assert w._dots == 0
        w.close()


class TestExpandingInput:
    def test_create(self, qapp):
        from ui.input_bar import ExpandingInput

        w = ExpandingInput()
        assert w.parent() is None
        assert w.toPlainText() == ""
        w.close()

    def test_placeholder(self, qapp):
        from ui.input_bar import ExpandingInput

        w = ExpandingInput()
        assert w.placeholderText() == "Escribe un mensaje..."
        w.close()

    def test_text_input(self, qapp):
        from ui.input_bar import ExpandingInput

        w = ExpandingInput()
        w.setPlainText("hola mundo")
        assert w.toPlainText() == "hola mundo"
        w.close()

    def test_clear(self, qapp):
        from ui.input_bar import ExpandingInput

        w = ExpandingInput()
        w.setPlainText("some text")
        assert w.toPlainText() == "some text"
        w.clear()
        assert w.toPlainText() == ""
        w.close()

    def test_send_signal_emitted_on_enter(self, qapp):
        from PyQt6.QtCore import QEvent, Qt
        from PyQt6.QtGui import QKeyEvent

        from ui.input_bar import ExpandingInput

        w = ExpandingInput()
        w.setPlainText("hello")

        received = []

        def on_send(text):
            received.append(text)

        w.send_requested.connect(on_send)

        event = QKeyEvent(
            QEvent.Type.KeyPress,
            Qt.Key.Key_Return,
            Qt.KeyboardModifier.NoModifier,
            "hello",
        )
        w.keyPressEvent(event)

        assert len(received) == 1
        assert received[0] == "hello"
        w.close()

    def test_send_clears_input(self, qapp):
        from PyQt6.QtCore import QEvent, Qt
        from PyQt6.QtGui import QKeyEvent

        from ui.input_bar import ExpandingInput

        w = ExpandingInput()
        w.setPlainText("clear me")

        w.send_requested.connect(lambda _: None)

        event = QKeyEvent(
            QEvent.Type.KeyPress,
            Qt.Key.Key_Return,
            Qt.KeyboardModifier.NoModifier,
            "clear me",
        )
        w.keyPressEvent(event)

        assert w.toPlainText() == ""
        w.close()

    def test_shift_enter_does_not_send(self, qapp):
        from PyQt6.QtCore import QEvent, Qt
        from PyQt6.QtGui import QKeyEvent

        from ui.input_bar import ExpandingInput

        w = ExpandingInput()
        w.setPlainText("no send")

        received = []

        def on_send(text):
            received.append(text)

        w.send_requested.connect(on_send)

        event = QKeyEvent(
            QEvent.Type.KeyPress,
            Qt.Key.Key_Return,
            Qt.KeyboardModifier.ShiftModifier,
            "no send",
        )
        w.keyPressEvent(event)

        assert len(received) == 0
        w.close()

    def test_empty_enter_does_not_send(self, qapp):
        from PyQt6.QtCore import QEvent, Qt
        from PyQt6.QtGui import QKeyEvent

        from ui.input_bar import ExpandingInput

        w = ExpandingInput()
        w.setPlainText("  ")

        received = []

        def on_send(text):
            received.append(text)

        w.send_requested.connect(on_send)

        event = QKeyEvent(
            QEvent.Type.KeyPress,
            Qt.Key.Key_Return,
            Qt.KeyboardModifier.NoModifier,
            "  ",
        )
        w.keyPressEvent(event)

        assert len(received) == 0
        w.close()

    def test_disable_enable(self, qapp):
        from ui.input_bar import ExpandingInput

        w = ExpandingInput()
        assert w.isEnabled()
        w.setEnabled(False)
        assert not w.isEnabled()
        w.setEnabled(True)
        assert w.isEnabled()
        w.close()


class TestTheme:
    def test_color_constants_exist(self):
        from ui.theme import Color

        assert hasattr(Color, "PRIMARY")
        assert hasattr(Color, "PRIMARY_DIM")
        assert hasattr(Color, "PRIMARY_DARK")
        assert hasattr(Color, "BG_DARK")
        assert hasattr(Color, "BG_MEDIUM")
        assert hasattr(Color, "BG_LIGHT")
        assert hasattr(Color, "TEXT")
        assert hasattr(Color, "TEXT_DIM")
        assert hasattr(Color, "TEXT_BRIGHT")
        assert hasattr(Color, "BORDER")
        assert hasattr(Color, "SUCCESS")
        assert hasattr(Color, "DANGER")
        assert hasattr(Color, "DANGER_BG")
        assert hasattr(Color, "SPEAKING")
        assert hasattr(Color, "WARNING")
        assert hasattr(Color, "CODE_BG")
        assert hasattr(Color, "CODE_BORDER")
        assert hasattr(Color, "CODE_TEXT")
        assert hasattr(Color, "INPUT_BG")
        assert hasattr(Color, "INPUT_FOCUS")
        assert hasattr(Color, "TRAY_BG")

    def test_rgba_returns_correct_format(self):
        from ui.theme import Color

        result = Color.rgba(Color.PRIMARY)
        assert result.startswith("rgba(")
        assert result.endswith(")")
        assert "0,220,255" in result

    def test_rgba_custom_alpha(self):
        from ui.theme import Color

        result = Color.rgba(Color.PRIMARY, alpha=100)
        assert result == "rgba(0,220,255,100)"

    def test_load_stylesheet_returns_string(self):
        from ui.theme import load_stylesheet

        result = load_stylesheet()
        assert isinstance(result, str)

    def test_apply_theme(self, qapp):
        from ui.theme import apply_theme

        apply_theme(qapp)
        ss = qapp.styleSheet()
        assert isinstance(ss, str)


class TestTutusWindow:
    def test_create_without_engine(self, qapp, monkeypatch):
        monkeypatch.setattr("ui.window.TutusWindow._init_ui", lambda self: None)
        monkeypatch.setattr("ui.window.TutusWindow._load_settings", lambda self: {})
        from ui.window import TutusWindow

        w = TutusWindow()
        assert w is not None
        w.close()

    def test_create_with_mock_engine(self, qapp, monkeypatch):
        monkeypatch.setattr("ui.window.TutusWindow._init_ui", lambda self: None)
        monkeypatch.setattr("ui.window.TutusWindow._load_settings", lambda self: {})

        class MockEngine:
            proactive_suggestion = None

        from ui.window import TutusWindow

        w = TutusWindow(MockEngine())
        assert w is not None
        w.close()
