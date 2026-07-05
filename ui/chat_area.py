from __future__ import annotations

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer
from PyQt6.QtGui import QResizeEvent
from PyQt6.QtWidgets import QLabel, QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget

from .chat_bubble import ChatBubble
from .constants import ANIM_DURATION


class _ScrollToBottomButton(QPushButton):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("⬇", parent)
        self.setFixedSize(28, 28)
        self.setStyleSheet("""
            QPushButton {
                background: rgba(0, 180, 255, 40);
                color: rgba(0, 220, 255, 200);
                border: 1px solid rgba(0, 200, 255, 60);
                border-radius: 14px;
                font-size: 13px;
            }
            QPushButton:hover {
                background: rgba(0, 180, 255, 80);
                border: 1px solid rgba(0, 200, 255, 120);
            }
        """)
        self.hide()


class ChatScrollArea(QScrollArea):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._container: QWidget = QWidget()
        self._container.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._container.setStyleSheet("background: transparent;")
        self._layout: QVBoxLayout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(6, 6, 6, 6)
        self._layout.setSpacing(6)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._stretch: QLabel = QLabel()
        self._stretch.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._layout.addWidget(self._stretch)

        self.setWidget(self._container)
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollArea > QWidget > QWidget { background: transparent; }
            QScrollBar:vertical {
                background: transparent; width: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(0,200,255,60); border-radius: 2px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover { background: rgba(0,200,255,120); }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
        """)
        if vp := self.viewport():
            vp.setStyleSheet("background: transparent;")

        vp = self.viewport()
        self._scroll_btn: _ScrollToBottomButton = _ScrollToBottomButton(vp)
        self._scroll_btn.clicked.connect(self.scroll_to_bottom_now)
        if sb := self.verticalScrollBar():
            sb.valueChanged.connect(self._on_scroll)
        QTimer.singleShot(0, self._position_btn)

    def _position_btn(self) -> None:
        vp = self.viewport()
        if vp is None:
            return
        self._scroll_btn.move(vp.width() - 36, vp.height() - 36)

    def _on_scroll(self, value: int) -> None:
        sb = self.verticalScrollBar()
        if sb is None or sb.maximum() - value > 40:
            self._scroll_btn.show()
        else:
            self._scroll_btn.hide()

    def resizeEvent(self, event: QResizeEvent | None) -> None:
        super().resizeEvent(event)
        self._position_btn()

    def add_bubble(self, bubble: ChatBubble) -> None:
        self._layout.insertWidget(self._layout.count() - 1, bubble)
        self._layout.activate()
        QTimer.singleShot(30, self._animate_scroll)

    def clear_all(self) -> None:
        while self._layout.count() > 1:
            item = self._layout.takeAt(0)
            if item is None:
                break
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self._layout.update()

    def _animate_scroll(self) -> None:
        sb = self.verticalScrollBar()
        if sb is None:
            return
        target = sb.maximum()
        current = sb.value()
        if target - current < 20:
            sb.setValue(target)
            return

        self._anim: QPropertyAnimation = QPropertyAnimation(sb, b"value")
        self._anim.setDuration(ANIM_DURATION)
        self._anim.setStartValue(current)
        self._anim.setEndValue(target)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.start()

    def scroll_to_bottom_now(self) -> None:
        sb = self.verticalScrollBar()
        if sb is not None:
            sb.setValue(sb.maximum())
