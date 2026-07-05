from __future__ import annotations

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QLabel


class PulseLabel(QLabel):
    def __init__(self, text: str = "", parent: QLabel | None = None) -> None:
        super().__init__(text, parent)
        self._opacity: float = 1.0
        self._dir: int = -1
        self._timer: QTimer = QTimer()
        self._timer.timeout.connect(self._pulse)
        self._timer.start(80)

    def _pulse(self) -> None:
        self._opacity += self._dir * 0.025
        if self._opacity <= 0.3:
            self._dir = 1
        elif self._opacity >= 1.0:
            self._dir = -1
        a = int(self._opacity * 255)
        self.setStyleSheet(f"""
            color: rgba(0, 255, 160, {a});
            font-size: 10px;
            font-family: 'Consolas', monospace;
            letter-spacing: 2px;
            background: transparent;
        """)


class TypingIndicator(QLabel):
    def __init__(self, parent: QLabel | None = None) -> None:
        super().__init__(parent)
        self._dots: int = 0
        self._timer: QTimer = QTimer()
        self._timer.timeout.connect(self._update)
        self.setStyleSheet("""
            color: rgba(0, 200, 255, 160);
            font-size: 11px;
            font-family: 'Consolas', monospace;
            background: transparent;
            padding: 2px 14px;
        """)
        self.hide()

    def start(self) -> None:
        self._dots = 0
        self.show()
        self._timer.start(400)

    def stop(self) -> None:
        self._timer.stop()
        self.hide()

    def _update(self) -> None:
        self._dots = (self._dots + 1) % 4
        self.setText("◈ TUTUS pensando" + "." * self._dots)
