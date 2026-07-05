from __future__ import annotations

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QResizeEvent
from PyQt6.QtWidgets import QTextBrowser, QWidget

from core.markdown import markdown_to_html, streaming_html, wrap_html


class MarkdownBrowser(QTextBrowser):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setOpenExternalLinks(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet("""
            QTextBrowser {
                background: transparent;
                border: none;
                color: rgba(200, 235, 255, 230);
                font-family: 'Segoe UI', system-ui, sans-serif;
                font-size: 13px;
            }
        """)
        doc = self.document()
        if doc is not None:
            doc.setDocumentMargin(0)
            doc.contentsChanged.connect(self._auto_height)

    def _auto_height(self) -> None:
        doc = self.document()
        vp = self.viewport()
        if doc is None or vp is None:
            return
        doc.setTextWidth(vp.width())
        h = int(doc.size().height())
        self.setFixedHeight(max(20, h + 4))
        self.updateGeometry()

    def set_markdown(self, md_text: str) -> None:
        self.setHtml(wrap_html(markdown_to_html(md_text)))

    def set_streaming(self, md_text: str) -> None:
        self.setHtml(streaming_html(markdown_to_html(md_text)))

    def sizeHint(self) -> QSize:
        doc = self.document()
        if doc is not None:
            return doc.size().toSize()
        return QSize(0, 0)

    def resizeEvent(self, event: QResizeEvent | None) -> None:
        super().resizeEvent(event)
        self._auto_height()
