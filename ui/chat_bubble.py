from __future__ import annotations

from PyQt6.QtCore import QEvent, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QEnterEvent,
    QLinearGradient,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPaintEvent,
    QPen,
)
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from .chat_data import ChatMessage, format_time
from .markdown_browser import MarkdownBrowser

BUBBLE_COLORS: dict[str, dict[str, QColor]] = {
    "user": {
        "bg_start": QColor(0, 60, 120, 30),
        "bg_end": QColor(0, 80, 160, 15),
        "border": QColor(0, 150, 255, 60),
        "border_hover": QColor(0, 180, 255, 140),
        "glow": QColor(0, 100, 255, 25),
        "accent": QColor(0, 170, 255),
    },
    "assistant": {
        "bg_start": QColor(0, 30, 60, 40),
        "bg_end": QColor(0, 15, 30, 20),
        "border": QColor(0, 200, 255, 50),
        "border_hover": QColor(0, 220, 255, 100),
        "glow": QColor(0, 200, 255, 20),
        "accent": QColor(0, 220, 255),
    },
}

BUBBLE_MAX_WIDTHS: dict[str, int] = {
    "user": 280,
    "assistant": 380,
}


class ChatBubble(QWidget):
    copy_requested: pyqtSignal = pyqtSignal(str)

    def __init__(self, message: ChatMessage, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._msg: ChatMessage = message
        self._hovered: bool = False
        is_user: bool = message.role == "user"
        self._colors: dict[str, QColor] = BUBBLE_COLORS.get(message.role, BUBBLE_COLORS["assistant"])
        self._max_w: int = BUBBLE_MAX_WIDTHS.get(message.role, BUBBLE_MAX_WIDTHS["assistant"])
        self._is_user: bool = is_user
        self._init_ui()

    def _init_ui(self) -> None:
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setMaximumWidth(self._max_w)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(3)

        sender: str = self._msg.sender or {
            "user": "▸ TÚ",
            "assistant": "◈ TUTUS",
        }.get(self._msg.role, "◈ TUTUS")
        self.sender_label: QLabel = QLabel(sender)
        self.sender_label.setStyleSheet(f"""
            color: rgba({self._colors["accent"].red()},{self._colors["accent"].green()},{self._colors["accent"].blue()},180);
            font-size: 10px;
            font-family: Consolas, monospace;
            letter-spacing: 2px;
            background: transparent;
        """)

        self.text_browser: MarkdownBrowser = MarkdownBrowser(self)
        self.text_browser.set_markdown(self._msg.text)

        self.time_label: QLabel = QLabel(format_time(self._msg.timestamp))
        self.time_label.setStyleSheet("""
            color: rgba(0, 180, 255, 80);
            font-size: 9px;
            font-family: Consolas, monospace;
            background: transparent;
        """)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        if self._is_user:
            row.addStretch()
            row.addWidget(self.time_label)
        else:
            row.addWidget(self.time_label)
            row.addStretch()

        layout.addWidget(self.sender_label)
        layout.addWidget(self.text_browser)
        layout.addLayout(row)

        if self._is_user:
            layout.setAlignment(Qt.AlignmentFlag.AlignRight)
            self.sender_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        QTimer.singleShot(0, self._fit_bubble)

    def _fit_bubble(self) -> None:
        if self.text_browser and self._msg.text:
            self.text_browser.set_markdown(self._msg.text)

    def message(self) -> ChatMessage:
        return self._msg

    def enterEvent(self, event: QEnterEvent | None) -> None:
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent | None) -> None:
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event: QPaintEvent | None) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width() if not self._is_user else min(self.width(), self._max_w)
        x_offset = self.width() - w if self._is_user else 0
        rect = QRectF(self.rect().adjusted(x_offset + 1, 1, -1 if not self._is_user else -(self.width() - w + 1), -1))

        path = QPainterPath()
        path.addRoundedRect(rect, 12, 12)

        bg = QLinearGradient(0, 0, 0, rect.height())
        bg.setColorAt(0, self._colors["bg_start"])
        bg.setColorAt(1, self._colors["bg_end"])
        painter.fillPath(path, QBrush(bg))

        border_color = self._colors["border_hover"] if self._hovered else self._colors["border"]
        painter.setPen(QPen(border_color, 1))
        painter.drawPath(path)

        glow_path = QPainterPath()
        glow_path.addRoundedRect(rect.adjusted(-2, -2, 2, 2), 14, 14)
        painter.setPen(QPen(self._colors["glow"], 3))
        painter.drawPath(glow_path)

        painter.end()
        super().paintEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent | None) -> None:
        self.copy_requested.emit(self._msg.text)
        super().mouseDoubleClickEvent(event)
