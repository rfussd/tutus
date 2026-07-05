from __future__ import annotations

from typing import Any

from PyQt6.QtCore import (  # type: ignore[attr-defined]
    QAbstractAnimation,
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    QRectF,
    Qt,
    QVariantAnimation,
    pyqtProperty,
    pyqtSignal,
)
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPaintEvent, QPen, QResizeEvent
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)


class SettingsPanel(QFrame):
    settings_changed: pyqtSignal = pyqtSignal(dict)

    def __init__(self, parent: QWidget | None = None, shadow_margin: int = 0) -> None:
        super().__init__(parent)
        self._sm: int = shadow_margin
        self._visible: bool = False
        self._panel_w: int = 280
        self._backdrop_alpha: int = 0
        self._slide_offset: float = 0.0

        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._build_content()
        self.hide()

    def _build_content(self) -> None:
        self.setStyleSheet("""
            SettingsPanel {
                background: transparent;
                border: none;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._content = QFrame(self)
        self._content.setFixedWidth(self._panel_w)
        self._content.setStyleSheet("""
            QFrame {
                background: rgba(2, 10, 25, 248);
                border: 1px solid rgba(0, 200, 255, 80);
                border-radius: 14px 0 0 14px;
            }
        """)

        cl = QVBoxLayout(self._content)
        cl.setContentsMargins(18, 18, 18, 18)
        cl.setSpacing(12)

        title = QLabel("⚙ CONFIGURACIÓN")
        title.setStyleSheet("""
            color: rgba(0, 220, 255, 200);
            font-size: 11px;
            font-family: 'Consolas', monospace;
            letter-spacing: 3px;
            background: transparent;
        """)
        cl.addWidget(title)
        cl.addWidget(self._separator())

        self._add_slider(cl, "VELOCIDAD TTS", "tts_rate", 50, 150, 115)
        self._add_checkbox(cl, "AUTO-TTS", "auto_tts", True)
        self._add_checkbox(cl, "MODO PROACTIVO", "proactive", False)
        self._add_slider(cl, "TEMP. MODELO", "temperature", 1, 100, 70)
        self._add_slider(cl, "MAX TOKENS", "max_tokens", 128, 4096, 2048)

        cl.addWidget(self._separator())

        voice_label = QLabel("VOZ TTS")
        voice_label.setStyleSheet(
            "color: rgba(0,180,255,140); font-size: 10px; font-family: Consolas, monospace; letter-spacing: 2px; background: transparent;"
        )
        cl.addWidget(voice_label)

        self._voice_combo = QComboBox()
        self._voice_combo.addItems(
            [
                "Jorge (es-MX)",
                "Dalia (es-MX)",
                "Francisco (es-ES)",
                "Karina (es-MX)",
                "Lupe (es-US)",
            ]
        )
        self._voice_combo.setCurrentIndex(0)
        self._voice_combo.setStyleSheet("""
            QComboBox {
                background: rgba(0,150,255,20);
                color: rgba(200,235,255,210);
                border: 1px solid rgba(0,200,255,50);
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 11px;
                font-family: 'Segoe UI', sans-serif;
            }
            QComboBox:hover { border: 1px solid rgba(0,200,255,100); }
            QComboBox::drop-down { border: none; width: 22px; }
            QComboBox QAbstractItemView {
                background: rgba(2,10,25,240);
                color: rgba(200,235,255,210);
                border: 1px solid rgba(0,200,255,50);
                selection-background-color: rgba(0,150,255,60);
                font-size: 11px;
            }
        """)
        cl.addWidget(self._voice_combo)

        cl.addStretch()

        close_btn = QPushButton("CERRAR ✕")
        close_btn.clicked.connect(self.toggle)
        close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(0,180,255,25);
                color: rgba(0,200,255,160);
                border: 1px solid rgba(0,200,255,50);
                border-radius: 8px;
                padding: 8px;
                font-size: 10px;
                font-family: Consolas, monospace;
                letter-spacing: 2px;
            }
            QPushButton:hover { background: rgba(0,180,255,50); }
        """)
        cl.addWidget(close_btn)

        self._content.hide()

    @staticmethod
    @staticmethod
    def _separator() -> QLabel:
        s = QLabel()
        s.setFixedHeight(1)
        s.setStyleSheet("background: rgba(0,200,255,35);")
        return s

    def _add_slider(self, layout: QVBoxLayout, label_text: str, key: str, min_v: int, max_v: int, default: int) -> None:
        lbl = QLabel(label_text)
        lbl.setStyleSheet(
            "color: rgba(0,180,255,140); font-size: 9px; font-family: Consolas, monospace; letter-spacing: 2px; background: transparent;"
        )
        layout.addWidget(lbl)

        val_lbl = QLabel(str(default))
        val_lbl.setStyleSheet("color: rgba(0,220,255,200); font-size: 10px; font-family: Consolas, monospace; background: transparent;")

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(min_v, max_v)
        slider.setValue(default)
        slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: rgba(0,150,255,25); height: 2px;
                border-radius: 1px;
            }
            QSlider::handle:horizontal {
                background: rgba(0,220,255,200); width: 12px; height: 12px;
                margin: -5px 0; border-radius: 6px;
            }
            QSlider::handle:horizontal:hover {
                background: rgba(0,255,200,230); width: 14px; height: 14px;
                margin: -6px 0; border-radius: 7px;
            }
            QSlider::sub-page:horizontal {
                background: rgba(0,200,255,70); border-radius: 1px;
            }
        """)
        slider.valueChanged.connect(lambda v, k=key, vl=val_lbl: self._on_value_changed(k, v, vl))
        layout.addWidget(slider)
        layout.addWidget(val_lbl)

    def _add_checkbox(self, layout: QVBoxLayout, label_text: str, key: str, default: bool) -> None:
        cb = QCheckBox(label_text)
        cb.setChecked(default)
        cb.setStyleSheet("""
            QCheckBox {
                color: rgba(0,180,255,140);
                font-size: 9px;
                font-family: Consolas, monospace;
                letter-spacing: 2px;
                spacing: 6px;
            }
            QCheckBox::indicator {
                width: 13px; height: 13px;
                border: 1px solid rgba(0,200,255,60);
                border-radius: 3px;
                background: rgba(0,150,255,15);
            }
            QCheckBox::indicator:checked {
                background: rgba(0,220,255,120);
                border: 1px solid rgba(0,220,255,180);
            }
            QCheckBox::indicator:hover {
                border: 1px solid rgba(0,200,255,120);
            }
        """)
        cb.toggled.connect(lambda v, k=key: self._on_value_changed(k, v, None))
        layout.addWidget(cb)

    def _on_value_changed(self, key: str, value: Any, label: QLabel | None) -> None:
        if label:
            label.setText(str(value))
        self.settings_changed.emit({key: value})

    @property
    def is_open(self) -> bool:
        return self._visible

    # ── animated backdrop alpha ──────────────────────────────────────────

    def _get_backdrop_alpha(self) -> int:
        return self._backdrop_alpha

    def _set_backdrop_alpha(self, a: int) -> None:
        self._backdrop_alpha = int(a)
        self.update()

    backdrop_alpha = pyqtProperty(int, _get_backdrop_alpha, _set_backdrop_alpha)

    def toggle(self) -> None:
        for attr in ("_slide_anim", "_fade_anim"):
            anim = getattr(self, attr, None)
            if anim:
                try:
                    anim.finished.disconnect()
                except TypeError:
                    pass
                if anim.state() == QAbstractAnimation.State.Running:
                    anim.stop()

        self._visible = not self._visible

        if self._visible:
            p = self.parent()
            pw = p.width() if isinstance(p, QWidget) else 0
            ph = p.height() if isinstance(p, QWidget) else 0
            self.setGeometry(0, 0, pw, ph)
            self.show()
            self.raise_()
            self._backdrop_alpha = 0

            body_h = self.height() - 2 * self._sm
            self._content.setFixedHeight(max(0, body_h))
            self._content.show()
            self._content.raise_()
            self._content.move(self.width(), self._sm)

            fade = QVariantAnimation(self)
            fade.setDuration(200)
            fade.setStartValue(0)
            fade.setEndValue(80)
            fade.valueChanged.connect(lambda v: self._set_backdrop_alpha(int(v)))
            fade.start()

            end_x = self.width() - self._sm - self._panel_w
            slide = QPropertyAnimation(self._content, b"pos")
            slide.setDuration(280)
            slide.setStartValue(QPoint(self.width(), self._sm))
            slide.setEndValue(QPoint(end_x, self._sm))
            slide.setEasingCurve(QEasingCurve.Type.OutBack)
            slide.start()

            self._fade_anim = fade
            self._slide_anim = slide
        else:
            self._backdrop_alpha = 80
            end_x = self.width() - self._sm - self._panel_w
            slide = QPropertyAnimation(self._content, b"pos")
            slide.setDuration(200)
            slide.setStartValue(QPoint(end_x, self._sm))
            slide.setEndValue(QPoint(self.width(), self._sm))
            slide.setEasingCurve(QEasingCurve.Type.InCubic)
            slide.finished.connect(self._on_closed)
            slide.start()

            fade = QVariantAnimation(self)
            fade.setDuration(180)
            fade.setStartValue(80)
            fade.setEndValue(0)
            fade.valueChanged.connect(lambda v: self._set_backdrop_alpha(int(v)))
            fade.start()

            self._fade_anim = fade
            self._slide_anim = slide

    def _on_closed(self) -> None:
        self._content.hide()
        self.hide()

    # ── Paint ────────────────────────────────────────────────────────────

    def resizeEvent(self, event: QResizeEvent | None) -> None:
        super().resizeEvent(event)
        if hasattr(self, "_content"):
            body_h = self.height() - 2 * self._sm
            self._content.setFixedHeight(max(0, body_h))

    def paintEvent(self, event: QPaintEvent | None) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        sm = self._sm
        body = self.rect().adjusted(sm, sm, -sm, -sm)

        # Clip backdrop to rounded body
        path = QPainterPath()
        path.addRoundedRect(QRectF(body), 16, 16)
        painter.setClipPath(path)

        # Semi-transparent backdrop
        painter.fillRect(self.rect(), QColor(0, 0, 0, self._backdrop_alpha))

        painter.setClipping(False)

        # Divider line where the panel sits
        px = body.right() - self._panel_w
        painter.setPen(QPen(QColor(0, 200, 255, 50), 1))
        painter.drawLine(px, body.top() + 10, px, body.bottom() - 10)

        painter.end()
