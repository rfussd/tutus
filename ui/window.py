from __future__ import annotations

import json
import logging
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QPoint, QPointF, QRect, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QContextMenuEvent,
    QFont,
    QIcon,
    QKeySequence,
    QLinearGradient,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
    QPixmap,
    QRadialGradient,
    QResizeEvent,
    QShortcut,
    QShowEvent,
)
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from .avatar import TutusAvatar
from .chat_area import ChatScrollArea
from .chat_bubble import ChatBubble
from .chat_data import ChatMessage
from .constants import WINDOW_MIN_SIZE, WINDOW_SIZE
from .indicators import PulseLabel, TypingIndicator
from .input_bar import ExpandingInput
from .settings_panel import SettingsPanel

DATA_DIR: Path = Path(__file__).resolve().parent.parent / "data"
CHAT_HISTORY_FILE: Path = DATA_DIR / "chat_history.json"
SETTINGS_FILE: Path = DATA_DIR / "settings.json"
MAX_MESSAGES_MEMORY: int = 200
log: logging.Logger = logging.getLogger("tutus.ui")


def _make_tray_icon() -> QIcon:
    pixmap = QPixmap(32, 32)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(0, 200, 255))
    painter.setPen(QPen(QColor(0, 220, 255, 120), 1))
    painter.drawEllipse(2, 2, 28, 28)

    gradient = QRadialGradient(16, 16, 14, 10, 10)
    gradient.setColorAt(0, QColor(0, 255, 200, 80))
    gradient.setColorAt(1, QColor(0, 200, 255, 0))
    painter.setBrush(QBrush(gradient))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(2, 2, 28, 28)

    painter.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
    painter.setPen(QColor(0, 10, 20))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "T")
    painter.end()
    return QIcon(pixmap)


class TutusWindow(QWidget):
    hotword_detected: pyqtSignal = pyqtSignal()
    response_ready: pyqtSignal = pyqtSignal(object)
    token_ready: pyqtSignal = pyqtSignal(str)
    voice_text_ready: pyqtSignal = pyqtSignal(str)
    cont_speech_ready: pyqtSignal = pyqtSignal(str)
    cont_level_ready: pyqtSignal = pyqtSignal(float)
    cont_listening_ready: pyqtSignal = pyqtSignal(bool)
    cont_speaking_ready: pyqtSignal = pyqtSignal(bool)

    def __init__(self, engine: Any = None) -> None:
        super().__init__()
        self._engine: Any = engine
        self.drag_pos: QPoint = QPoint()
        self._messages: list[ChatMessage] = []
        self._streaming_text: str = ""
        self._streaming_bubble: ChatBubble | None = None
        self._continuous_mode: bool = False
        self._settings: dict[str, Any] = self._load_settings()
        self._init_ui()
        self._init_tray()
        self._init_shortcuts()
        self._start_hotword()
        self.response_ready.connect(self._handle_response)
        self.token_ready.connect(self._append_token)
        self.voice_text_ready.connect(self._on_voice_text)
        self.cont_speech_ready.connect(self._on_cont_speech)
        self.cont_level_ready.connect(self._on_cont_level)
        self.cont_listening_ready.connect(self._on_cont_listening)
        self.cont_speaking_ready.connect(self._on_cont_speaking)
        self._load_history()
        self._auto_save_timer: QTimer = QTimer()
        self._auto_save_timer.timeout.connect(self._save_history)
        self._auto_save_timer.start(30000)

    # ── UI Setup ───────────────────────────────────────────────────────────

    def _init_ui(self) -> None:
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(*WINDOW_MIN_SIZE)
        self.resize(*WINDOW_SIZE)

        self._shadow_margin: int = 28
        root = QVBoxLayout(self)
        root.setContentsMargins(self._shadow_margin, self._shadow_margin, self._shadow_margin, self._shadow_margin)
        root.setSpacing(0)

        # ── Title Bar ────────────────────────────────────────────────
        title_bar = QWidget()
        title_bar.setFixedHeight(38)
        title_bar.setCursor(Qt.CursorShape.OpenHandCursor)
        tbar = QHBoxLayout(title_bar)
        tbar.setContentsMargins(12, 0, 12, 0)
        tbar.setSpacing(4)

        def _title_btn(text: str, color: str, _hover_color: str, click_target: Callable[[], None], tooltip: str) -> QPushButton:
            btn = QPushButton(text)
            btn.setFixedSize(26, 26)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: rgba({color},40);
                    color: rgba({color},200);
                    border: 1px solid rgba({color},70);
                    border-radius: 6px;
                    font-size: 13px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background: rgba({color},100);
                    color: rgba({color},255);
                    border: 1px solid rgba({color},150);
                }}
            """)
            btn.clicked.connect(click_target)
            btn.setToolTip(tooltip)
            return btn

        btn_close = _title_btn("✕", "255,80,80", "255,120,120", self._close_app, "Cerrar")
        btn_min = _title_btn("−", "0,200,255", "0,220,255", self.hide, "Minimizar")
        self._btn_settings = _title_btn("⚙", "0,200,255", "0,220,255", self._toggle_settings, "Configuración")

        logo = QLabel("◈  TUTUS")
        logo.setStyleSheet("""
            color: rgba(0, 220, 255, 240);
            font-size: 13px;
            font-weight: bold;
            font-family: 'Consolas', monospace;
            letter-spacing: 5px;
            background: transparent;
            padding-left: 6px;
        """)

        self._status_label = PulseLabel("● EN LÍNEA")

        tbar.addWidget(logo)
        tbar.addSpacing(8)
        tbar.addStretch()
        tbar.addWidget(self._status_label)
        tbar.addSpacing(8)
        tbar.addWidget(btn_min)
        tbar.addSpacing(2)
        tbar.addWidget(self._btn_settings)
        tbar.addSpacing(2)
        tbar.addWidget(btn_close)

        # ── Avatar ───────────────────────────────────────────────────
        self._avatar = TutusAvatar()
        avatar_row = QWidget()
        avatar_row.setFixedHeight(88)
        av = QHBoxLayout(avatar_row)
        av.setContentsMargins(0, 6, 0, 6)
        av.addStretch()
        av.addWidget(self._avatar)
        av.addStretch()

        # ── Separator ────────────────────────────────────────────────
        sep = QLabel()
        sep.setFixedHeight(1)
        sep.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 rgba(0,200,255,0),
                stop:0.5 rgba(0,200,255,50),
                stop:1 rgba(0,200,255,0));
            margin: 0 20px;
        """)

        # ── Chat ─────────────────────────────────────────────────────
        self._chat = ChatScrollArea()
        self._typing = TypingIndicator()

        # ── Input ────────────────────────────────────────────────────
        inp = QWidget()
        inp_layout = QHBoxLayout(inp)
        inp_layout.setContentsMargins(14, 6, 14, 10)
        inp_layout.setSpacing(8)

        self._input = ExpandingInput()
        self._input.send_requested.connect(self._on_input_send)

        self._btn_mic = QPushButton("🎤")
        self._btn_mic.setFixedSize(36, 36)
        self._mic_normal_style()
        self._btn_mic.clicked.connect(self._start_listening)

        self._btn_cont = QPushButton("◉")
        self._btn_cont.setFixedSize(36, 36)
        self._cont_off_style()
        self._btn_cont.clicked.connect(self._toggle_continuous)
        self._btn_cont.setToolTip("Modo conversación continua")

        btn_send = QPushButton("▶")
        btn_send.setFixedSize(36, 36)
        btn_send.setStyleSheet("""
            QPushButton {
                background: rgba(0,180,255,40);
                color: rgba(0,220,255,210);
                border: 1px solid rgba(0,200,255,80);
                border-radius: 8px; font-size: 13px;
            }
            QPushButton:hover { background: rgba(0,180,255,80); }
        """)
        btn_send.clicked.connect(lambda: self._on_input_send(self._input.toPlainText().strip()))

        inp_layout.addWidget(self._input)
        inp_layout.addWidget(self._btn_mic)
        inp_layout.addWidget(self._btn_cont)
        inp_layout.addWidget(btn_send)

        # ── Footer ───────────────────────────────────────────────────
        model_id = ""
        try:
            from core.config import MODEL_ID

            model_id = MODEL_ID
        except Exception:
            model_id = ""
        footer_text = f"Model: {model_id}" if model_id else "Multi-Agent System"
        footer = QLabel(footer_text)
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("""
            color: rgba(0,180,255,40);
            font-size: 8px;
            font-family: 'Consolas', monospace;
            letter-spacing: 1px;
            padding: 2px;
        """)

        root.addWidget(title_bar)
        root.addWidget(avatar_row)
        root.addWidget(sep)
        root.addWidget(self._chat, stretch=1)
        root.addWidget(self._typing)
        root.addWidget(inp)
        root.addWidget(footer)

        # ── Settings overlay ─────────────────────────────────────────
        self._settings_panel = SettingsPanel(self, shadow_margin=self._shadow_margin)
        self._settings_panel.setGeometry(0, 0, self.width(), self.height())
        self._settings_panel.settings_changed.connect(self._on_settings_changed)

        self.add_message("TUTUS", "Sistema multi-agente activo. ¿En qué te ayudo?", role="assistant")

    def _mic_normal_style(self) -> None:
        self._btn_mic.setStyleSheet("""
            QPushButton {
                background: rgba(0,180,255,25);
                border: 1px solid rgba(0,200,255,60);
                border-radius: 8px; font-size: 16px;
            }
            QPushButton:hover { background: rgba(0,180,255,50); }
        """)

    def _mic_recording_style(self) -> None:
        self._btn_mic.setStyleSheet("""
            QPushButton {
                background: rgba(255,50,50,70);
                border: 2px solid rgba(255,80,80,180);
                border-radius: 8px; font-size: 16px;
            }
        """)

    def _cont_off_style(self) -> None:
        self._btn_cont.setStyleSheet("""
            QPushButton {
                background: rgba(80,80,80,30);
                color: rgba(150,150,150,180);
                border: 1px solid rgba(100,100,100,60);
                border-radius: 8px; font-size: 16px;
            }
            QPushButton:hover { background: rgba(0,200,100,50); }
        """)

    def _cont_on_style(self) -> None:
        self._btn_cont.setStyleSheet("""
            QPushButton {
                background: rgba(0,255,100,50);
                color: rgba(0,255,120,210);
                border: 2px solid rgba(0,255,120,160);
                border-radius: 8px; font-size: 16px;
            }
            QPushButton:hover { background: rgba(0,255,100,80); }
        """)

    # ── Shortcuts ──────────────────────────────────────────────────────────

    def _init_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+W"), self, self.hide)
        QShortcut(QKeySequence("Alt+F4"), self, self._close_app)
        QShortcut(QKeySequence("Ctrl+L"), self, self._clear_chat)
        QShortcut(QKeySequence("Ctrl+,"), self, self._toggle_settings)
        QShortcut(QKeySequence("Escape"), self, self._handle_escape)

    def _handle_escape(self) -> None:
        if self._settings_panel.is_open:
            self._settings_panel.toggle()
        else:
            self.hide()

    def _clear_chat(self) -> None:
        self._chat.clear_all()
        self._messages.clear()
        self.add_message("TUTUS", "Chat limpiado.", role="assistant")

    # ── Settings ───────────────────────────────────────────────────────────

    def _toggle_settings(self) -> None:
        self._settings_panel.raise_()
        self._settings_panel.toggle()

    def resizeEvent(self, event: QResizeEvent | None) -> None:
        super().resizeEvent(event)
        if self._settings_panel:
            self._settings_panel.setGeometry(0, 0, self.width(), self.height())

    # ── Tray ───────────────────────────────────────────────────────────────

    def _init_tray(self) -> None:
        self._tray: QSystemTrayIcon = QSystemTrayIcon(self)
        self._tray.setIcon(_make_tray_icon())
        self._tray.setToolTip("TUTUS v2.0 — Multi-Agent")

        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: rgba(2,8,20,240);
                color: rgba(0,220,255,210);
                border: 1px solid rgba(0,200,255,60);
                font-family: 'Consolas', monospace;
                font-size: 11px; padding: 4px;
            }
            QMenu::item { padding: 6px 20px; }
            QMenu::item:selected { background: rgba(0,180,255,50); }
            QMenu::separator { background: rgba(0,200,255,30); height: 1px; margin: 4px 10px; }
        """)

        show_action = menu.addAction("◈ Mostrar TUTUS")
        if show_action is not None:
            show_action.triggered.connect(self._show_window)
        menu.addSeparator()
        self._action_continuous: QAction | None = menu.addAction("🎤 Modo continuo")
        if self._action_continuous is not None:
            self._action_continuous.triggered.connect(self._toggle_continuous)
        menu.addSeparator()

        from core.startup import is_startup_enabled

        label = "✓ Arranque automático" if is_startup_enabled() else "○ Arranque automático"
        self._action_startup: QAction | None = menu.addAction(label)
        if self._action_startup is not None:
            self._action_startup.triggered.connect(self._toggle_startup)
        menu.addSeparator()
        close_action = menu.addAction("× Cerrar")
        if close_action is not None:
            close_action.triggered.connect(self._close_app)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._tray_clicked)
        self._tray.show()

    def _tray_clicked(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            if self.isVisible():
                self.hide()
            else:
                self._show_window()

    def _show_window(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def showEvent(self, event: QShowEvent | None) -> None:
        super().showEvent(event)

    def _toggle_startup(self) -> None:
        from core.startup import disable_startup, enable_startup, is_startup_enabled

        if is_startup_enabled():
            disable_startup()
            if self._action_startup is not None:
                self._action_startup.setText("○ Arranque automático")
        else:
            enable_startup()
            if self._action_startup is not None:
                self._action_startup.setText("✓ Arranque automático")

    # ── Hotword ────────────────────────────────────────────────────────────

    def _start_hotword(self) -> None:
        from core.hotword import start_hotword_detection

        self.hotword_detected.connect(self._on_hotword)
        start_hotword_detection(lambda: self.hotword_detected.emit())

    def _on_hotword(self) -> None:
        self._show_window()
        QTimer.singleShot(300, self._start_listening)

    # ── Messages ───────────────────────────────────────────────────────────

    def add_message(self, sender: str, text: str, role: str = "assistant", is_tutus: bool | None = None) -> None:
        if is_tutus is not None:
            role = "assistant" if is_tutus else "user"
        if role not in ("user", "assistant"):
            role = "assistant"
        msg = ChatMessage(role=role, text=text, sender=sender)
        self._messages.append(msg)
        self._trim_messages()
        bubble = ChatBubble(msg, self._chat)
        bubble.copy_requested.connect(self._copy_text)
        self._chat.add_bubble(bubble)

    def _copy_text(self, text: str) -> None:
        cb = QApplication.clipboard()
        if cb is not None:
            cb.setText(text)
        self._show_toast("Copiado al portapapeles")

    def _show_toast(self, message: str) -> None:
        self._typing.setText(f"✓ {message}")
        self._typing.show()
        self._typing.setStyleSheet("""
            color: rgba(0, 255, 150, 180);
            font-size: 10px;
            font-family: 'Consolas', monospace;
            background: transparent;
            padding: 2px 14px;
        """)
        QTimer.singleShot(1500, lambda: self._typing.hide())

    # ── Streaming ──────────────────────────────────────────────────────────

    def _start_streaming(self) -> None:
        self._streaming_text = ""
        msg = ChatMessage(role="assistant", text="")
        self._streaming_bubble = ChatBubble(msg, self._chat)
        self._streaming_bubble.copy_requested.connect(self._copy_text)
        self._chat.add_bubble(self._streaming_bubble)

    def _append_token(self, token: str) -> None:
        if not self._streaming_bubble:
            self._start_streaming()
        self._streaming_text += token
        if self._streaming_bubble is not None:
            self._streaming_bubble.text_browser.set_streaming(self._streaming_text)
        self._chat._animate_scroll()

    # ── Send / Process ─────────────────────────────────────────────────────

    def _on_input_send(self, text: str) -> None:
        if not text:
            return
        self._input.clear()
        self.add_message("TÚ", text, role="user")
        self._process_message(text)

    def show_window(self) -> None:
        self._show_window()

    def process_message(self, text: str) -> None:
        self._process_message(text)

    def _process_message(self, text: str) -> None:
        if self._engine:
            self._engine.add_to_buffer("user", text)

        self._finalize_streaming()
        self._avatar.set_state("thinking")
        self._typing.start()
        self._streaming_bubble = None
        self._streaming_text = ""

        multi: list[str] = self._engine.detect_multi_intent(text) if self._engine else []
        if len(multi) >= 2:
            self._process_multi(multi)
            return

        if self._engine:
            self._engine.process_text(text, on_token=lambda t: self.token_ready.emit(t), on_done=lambda r: self.response_ready.emit(r))

    def _process_multi(self, messages: list[str]) -> None:
        def _run() -> None:
            if not self._engine:
                return
            results = self._engine.route_parallel(messages)
            domains: set[str] = set()
            texts: list[str] = []
            for msg, res in zip(messages, results):
                r: str = res.get("message", "") if isinstance(res, dict) else str(res)
                d: str = res.get("domain", "") if isinstance(res, dict) else ""
                domains.add(d)
                texts.append(r)

            combined: str = "\n\n".join(texts)
            self._engine.add_to_buffer("assistant", combined)
            self.response_ready.emit({"domain": "multi", "message": combined.strip()})

        threading.Thread(target=_run, daemon=True).start()

    def _handle_response(self, result: dict[str, Any]) -> None:
        try:
            self._typing.stop()
            self._avatar.set_state("idle")

            message = result.get("message", "") or "¿En qué te ayudo?"

            if self._streaming_bubble:
                self._finalize_streaming(message)
                final = self._streaming_text or message
            else:
                self.add_message("TUTUS", message, role="assistant")
                final = message

            if self._engine:
                self._engine.add_to_buffer("assistant", final)

            if self._settings.get("auto_tts", True):
                try:
                    from core.tts import speak

                    speak(final)
                except Exception as e:
                    log.warning("TTS error: %s", e)

            self._streaming_bubble = None
            self._streaming_text = ""
        except Exception as e:
            log.error("handle_response error: %s", e)
            self._streaming_bubble = None
            self._streaming_text = ""
            self._avatar.set_state("idle")
            self._typing.stop()

    # ── Voice ──────────────────────────────────────────────────────────────

    def _start_listening(self) -> None:
        self._mic_recording_style()
        self._avatar.set_state("listening")
        self._show_toast("🎙 Escuchando...")

        if self._engine:
            self._engine.process_voice(
                duration=5,
                on_text=lambda t: self.voice_text_ready.emit(t),
                on_token=lambda t: self.token_ready.emit(t),
                on_done=lambda r: self.response_ready.emit(r),
            )

    def _on_voice_text(self, text: str) -> None:
        self._mic_normal_style()
        self._avatar.set_state("idle")

        if not text.strip():
            self._show_toast("No escuché nada")
            return

        self.add_message("TÚ", f"🎙 {text}", role="user")

    def _toggle_continuous(self) -> None:
        if self._continuous_mode:
            self._stop_continuous()
        else:
            self._start_continuous()

    def _start_continuous(self) -> None:
        self._continuous_mode = True
        self._cont_on_style()
        self._btn_cont.setToolTip("Desactivar modo continuo")

        if self._engine:
            self._engine.start_continuous(
                on_speech=lambda t: self.cont_speech_ready.emit(t),
                on_token=lambda t: self.token_ready.emit(t),
                on_response=lambda r: self.response_ready.emit(r),
                on_level=lambda v: self.cont_level_ready.emit(v),
                on_listening=lambda v: self.cont_listening_ready.emit(v),
                on_speaking=lambda v: self.cont_speaking_ready.emit(v),
            )

        self.add_message("TUTUS", "🎤 Modo continuo activado. Habla cuando quieras.", role="assistant")

    def _stop_continuous(self) -> None:
        if self._engine:
            self._engine.stop_continuous()
        self._continuous_mode = False
        self._cont_off_style()
        self._btn_cont.setToolTip("Modo conversación continua")
        self._avatar.set_state("idle")
        self.add_message("TUTUS", "⏹ Modo continuo desactivado.", role="assistant")

    def _finalize_streaming(self, fallback_text: str = "") -> None:
        if self._streaming_bubble:
            text = self._streaming_text or fallback_text or " "
            self._streaming_bubble.text_browser.set_markdown(text)
            if hasattr(self._streaming_bubble, "_msg"):
                self._streaming_bubble._msg.text = text
            self._messages.append(ChatMessage(role="assistant", text=text))
            self._streaming_bubble = None
            self._streaming_text = ""

    def _on_cont_speech(self, text: str) -> None:
        self._finalize_streaming()
        self.add_message("TÚ", f"🎙 {text}", role="user")

    def _on_cont_level(self, level: float) -> None:
        self._avatar.set_audio_level(level)

    def _on_cont_listening(self, listening: bool) -> None:
        if listening:
            self._avatar.set_state("listening")
        else:
            self._mic_normal_style()

    def _on_cont_speaking(self, speaking: bool) -> None:
        if speaking:
            self._avatar.set_state("speaking")
        else:
            self._avatar.set_state("idle")

    # ── Persistencia ───────────────────────────────────────────────────────

    @staticmethod
    def _load_settings() -> dict[str, Any]:
        defaults: dict[str, Any] = {
            "tts_rate": 115,
            "auto_tts": True,
            "proactive": False,
            "temperature": 70,
            "max_tokens": 2048,
        }
        try:
            if SETTINGS_FILE.exists():
                saved: dict[str, Any] = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
                defaults.update(saved)
        except Exception as e:
            log.warning("settings load error: %s", e)
        return defaults

    def _save_settings(self) -> None:
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            SETTINGS_FILE.write_text(
                json.dumps(self._settings, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            log.warning("settings save error: %s", e)

    def _on_settings_changed(self, changes: dict[str, Any]) -> None:
        self._settings.update(changes)
        self._save_settings()
        log.info("settings updated: %s", changes)

    def _save_history(self) -> None:
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            data: list[dict[str, Any]] = [
                {"role": m.role, "text": m.text, "sender": m.sender, "timestamp": m.timestamp} for m in self._messages[-100:]
            ]
            CHAT_HISTORY_FILE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            log.warning("history save error: %s", e)

    def _load_history(self) -> None:
        try:
            if not CHAT_HISTORY_FILE.exists():
                return
            data: list[dict[str, Any]] = json.loads(CHAT_HISTORY_FILE.read_text(encoding="utf-8"))
            for item in data[-20:]:
                self.add_message(item.get("sender", ""), item["text"], role=item["role"])
        except Exception as e:
            log.warning("history load error: %s", e)

    def _trim_messages(self) -> None:
        if len(self._messages) > MAX_MESSAGES_MEMORY:
            excess = len(self._messages) - MAX_MESSAGES_MEMORY
            self._messages = self._messages[-MAX_MESSAGES_MEMORY:]
            log.info("trimmed %d old messages", excess)

    # ── Close ──────────────────────────────────────────────────────────────

    def _close_app(self) -> None:
        if self._continuous_mode:
            self._stop_continuous()
        self._auto_save_timer.stop()
        self._save_history()
        self._save_settings()
        try:
            from core.hotword import stop_hotword

            stop_hotword()
        except Exception:
            pass
        log.info("shutdown complete")
        app = QApplication.instance()
        if app is not None:
            app.quit()

    def _on_startup_progress(self, msg: str) -> None:
        self._status_label.setText(f"⏳ {msg}")
        if "activo" in msg.lower() or "ready" in msg.lower():
            self._status_label.setText("● EN LÍNEA")
            self._avatar.set_state("idle")

    def show_suggestion(self, context: str, message: str) -> None:
        self.add_message("TUTUS", f"[{context}] {message}", role="assistant")
        if not self.isVisible():
            self._show_window()

    # ── Drag ───────────────────────────────────────────────────────────────

    def mousePressEvent(self, event: QMouseEvent | None) -> None:
        if event is None or event.button() != Qt.MouseButton.LeftButton:
            return
        self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event: QMouseEvent | None) -> None:
        if event is None or event.buttons() != Qt.MouseButton.LeftButton:
            return
        if not self.drag_pos.isNull():
            self.move(event.globalPosition().toPoint() - self.drag_pos)

    # ── Context Menu (right-click to close) ──────────────────────────────

    def contextMenuEvent(self, event: QContextMenuEvent | None) -> None:
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: rgba(2,8,20,240);
                color: rgba(0,220,255,210);
                border: 1px solid rgba(0,200,255,60);
                font-family: 'Consolas', monospace;
                font-size: 11px; padding: 4px;
            }
            QMenu::item { padding: 6px 20px; }
            QMenu::item:selected { background: rgba(0,180,255,50); }
        """)

        def _safe_connect(action_text: str, slot: Callable[[], None]) -> None:
            act = menu.addAction(action_text)
            if act is not None:
                act.triggered.connect(slot)

        _safe_connect("✕ Cerrar TUTUS", self._close_app)
        _safe_connect("− Minimizar", self.hide)
        menu.addSeparator()
        _safe_connect("◈ Mostrar ventana", self._show_window)
        if event is not None:
            menu.exec(event.globalPos())

    # ── Paint ──────────────────────────────────────────────────────────────

    def paintEvent(self, event: QPaintEvent | None) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        m = self._shadow_margin
        r = self.rect().adjusted(m, m, -m, -m)

        # Drop shadow (drawn outside the body, inside the widget)
        for i in range(12, 0, -1):
            alpha = max(0, 35 - i * 3)
            spread = i * 1.8
            shadow = r.adjusted(int(-spread), int(-spread + 2), int(-spread), int(-spread + 2))
            painter.setBrush(QColor(0, 0, 0, alpha))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(shadow, 18 + i, 18 + i)

        # Deep glass background
        painter.setBrush(QColor(2, 8, 20, 215))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(r, 16, 16)

        # Glow border
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(0, 200, 255, 80), 1))
        painter.drawRoundedRect(r, 16, 16)

        # Top accent light bar
        accent = QRect(r.x() + 50, r.y(), r.width() - 100, 2)
        grad = QLinearGradient(QPointF(accent.topLeft()), QPointF(accent.topRight()))
        grad.setColorAt(0, QColor(0, 200, 255, 0))
        grad.setColorAt(0.5, QColor(0, 220, 255, 90))
        grad.setColorAt(1, QColor(0, 200, 255, 0))
        painter.setBrush(QBrush(grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(accent, 1, 1)


if __name__ == "__main__":
    app = QApplication([])
    app.setQuitOnLastWindowClosed(False)
    w = TutusWindow()
    w.show()
    app.exec()
