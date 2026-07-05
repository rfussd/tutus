from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeyEvent, QResizeEvent
from PyQt6.QtWidgets import QTextEdit, QWidget

INPUT_STYLE: str = """
    QTextEdit {
        background: rgba(0, 150, 255, 12);
        color: rgba(200, 240, 255, 230);
        border: 1px solid rgba(0, 200, 255, 50);
        border-radius: 10px;
        padding: 8px 14px;
        font-family: 'Segoe UI', system-ui, sans-serif;
        font-size: 13px;
        selection-background-color: rgba(0, 200, 255, 80);
    }
    QTextEdit:focus {
        border: 1px solid rgba(0, 200, 255, 120);
        background: rgba(0, 150, 255, 18);
    }
"""


class ExpandingInput(QTextEdit):
    send_requested: pyqtSignal = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setPlaceholderText("Escribe un mensaje...")
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFixedHeight(38)
        self.setMaximumHeight(120)
        self.setAcceptRichText(False)
        doc = self.document()
        if doc is not None:
            doc.contentsChanged.connect(self._adjust_height)
        self.setStyleSheet(INPUT_STYLE)

    def _adjust_height(self) -> None:
        doc = self.document()
        vp = self.viewport()
        if doc is None or vp is None:
            return
        doc.setTextWidth(vp.width())
        h = int(doc.size().height()) + 14
        self.setFixedHeight(max(38, min(h, self.maximumHeight())))

    def keyPressEvent(self, event: QKeyEvent | None) -> None:
        if event is None:
            return
        if event.key() == Qt.Key.Key_Return and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            text = self.toPlainText().strip()
            if text:
                self.send_requested.emit(text)
                self.clear()
                self._adjust_height()
            return
        super().keyPressEvent(event)

    def resizeEvent(self, event: QResizeEvent | None) -> None:
        super().resizeEvent(event)
        self._adjust_height()
