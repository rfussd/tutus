from __future__ import annotations

import math
import random
from typing import Any

from PyQt6.QtCore import QPointF, Qt, QTimer
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPaintEvent,
    QPen,
)
from PyQt6.QtWidgets import QWidget

STATE_COLORS: dict[str, tuple[QColor, str]] = {
    "idle": (QColor(0, 220, 255), "TUTUS"),
    "listening": (QColor(0, 255, 150), "ESCUCHO"),
    "thinking": (QColor(255, 180, 0), "PIENSO"),
    "speaking": (QColor(255, 100, 200), "HABLO"),
}


class TutusAvatar(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(80, 80)
        self._phase: float = 0.0
        self._blink: int = 0
        self._blink_counter: int = 0
        self._state: str = "idle"
        self._audio_level: float = 0.0
        self._particles: list[dict[str, Any]] = []
        self._scan_y: float = 0.0

        for i in range(8):
            self._particles.append(
                {
                    "angle": math.radians(i * 45 + random.randint(-10, 10)),
                    "dist": 34 + random.randint(-3, 6),
                    "speed": 0.3 + random.random() * 0.6,
                    "phase": random.random() * math.tau,
                    "size": 1.2 + random.random() * 1.5,
                }
            )

        self._timer: QTimer = QTimer()
        self._timer.timeout.connect(self._animate)
        self._timer.start(30)

    def set_state(self, state: str) -> None:
        self._state = state

    def set_audio_level(self, level: float) -> None:
        self._audio_level = level

    def _animate(self) -> None:
        self._phase += 0.1
        self._blink_counter += 1
        if self._blink_counter > 100 + random.randint(0, 40):
            self._blink = 3
            self._blink_counter = 0
        if self._blink > 0:
            self._blink -= 1

        for p in self._particles:
            p["angle"] += p["speed"] * 0.02

        self._scan_y = (self._scan_y + 1.2) % 48
        self.update()

    def paintEvent(self, event: QPaintEvent | None) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = self.width() / 2
        cy = self.height() / 2 + 2

        base_color, label = STATE_COLORS.get(self._state, STATE_COLORS["idle"])
        audio_bump = self._audio_level * 15.0
        glow_alpha = int(100 + 60 * math.sin(self._phase * 0.7) + audio_bump * 8)

        # Outer glow rings (pulse with audio)
        for r in range(35, 22, -2):
            alpha = max(0, glow_alpha - (35 - r) * 5)
            gc = QColor(base_color.red(), base_color.green(), base_color.blue(), int(alpha))
            painter.setBrush(gc)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(int(cx - r), int(cy - r), r * 2, r * 2)

        # Hexagon face
        hr = 20
        hex_pts = []
        for i in range(6):
            a = math.radians(60 * i - 30)
            hex_pts.append(QPointF(cx + hr * math.cos(a), cy + hr * math.sin(a)))

        hex_path = QPainterPath()
        hex_path.moveTo(hex_pts[0])
        for p in hex_pts[1:]:
            hex_path.lineTo(p)
        hex_path.closeSubpath()

        body_color = QColor(2, 8, 20, 200)
        painter.fillPath(hex_path, body_color)

        pen_grad = QLinearGradient(cx, cy - hr, cx, cy + hr)
        pen_grad.setColorAt(0, base_color)
        pen_grad.setColorAt(1, QColor(base_color.red() // 3, base_color.green() // 3, base_color.blue() // 3, 120))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QBrush(pen_grad), 1.5))
        painter.drawPath(hex_path)

        # Inner hex line
        ihr = hr * 0.65
        inner_pts = []
        for i in range(6):
            a = math.radians(60 * i - 30)
            inner_pts.append(QPointF(cx + ihr * math.cos(a), cy + ihr * math.sin(a)))
        inner_path = QPainterPath()
        inner_path.moveTo(inner_pts[0])
        for p in inner_pts[1:]:
            inner_path.lineTo(p)
        inner_path.closeSubpath()
        painter.setPen(QPen(base_color, 1, Qt.PenStyle.DotLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(inner_path)

        # Cat ears
        ear_w = 8
        ear_h = 12
        left_base = cx - 10
        right_base = cx + 10
        ear_top_y = cy - hr - 3

        ear_left_path = QPainterPath()
        ear_left_path.moveTo(left_base - ear_w, ear_top_y)
        ear_left_path.lineTo(left_base, ear_top_y - ear_h)
        ear_left_path.lineTo(left_base + ear_w, ear_top_y)
        ear_left_path.closeSubpath()
        painter.fillPath(ear_left_path, body_color)
        painter.setPen(QPen(base_color, 1.2))
        painter.drawPath(ear_left_path)

        ear_right_path = QPainterPath()
        ear_right_path.moveTo(right_base - ear_w, ear_top_y)
        ear_right_path.lineTo(right_base, ear_top_y - ear_h)
        ear_right_path.lineTo(right_base + ear_w, ear_top_y)
        ear_right_path.closeSubpath()
        painter.fillPath(ear_right_path, body_color)
        painter.drawPath(ear_right_path)

        inner_ear_color = QColor(base_color.red(), base_color.green() // 2, base_color.blue() // 2, 80)
        painter.setBrush(inner_ear_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(left_base, ear_top_y - 4), 2, 3)
        painter.drawEllipse(QPointF(right_base, ear_top_y - 4), 2, 3)

        # Whiskers
        whisker_color = QColor(base_color.red(), base_color.green(), base_color.blue(), 100)
        painter.setPen(QPen(whisker_color, 1.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        mid_y = cy + 3
        painter.drawLine(QPointF(cx - 10, mid_y - 1), QPointF(cx - 24, mid_y - 6))
        painter.drawLine(QPointF(cx - 10, mid_y), QPointF(cx - 26, mid_y))
        painter.drawLine(QPointF(cx - 10, mid_y + 1), QPointF(cx - 24, mid_y + 6))
        painter.drawLine(QPointF(cx + 10, mid_y - 1), QPointF(cx + 24, mid_y - 6))
        painter.drawLine(QPointF(cx + 10, mid_y), QPointF(cx + 26, mid_y))
        painter.drawLine(QPointF(cx + 10, mid_y + 1), QPointF(cx + 24, mid_y + 6))

        # Cat nose
        nose_color = QColor(base_color.red(), base_color.green(), base_color.blue(), 180)
        nose_path = QPainterPath()
        nose_path.moveTo(cx, cy + 3)
        nose_path.lineTo(cx - 2, cy + 5)
        nose_path.lineTo(cx + 2, cy + 5)
        nose_path.closeSubpath()
        painter.setBrush(nose_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(nose_path)

        # Eyes
        blink = self._blink > 0
        eye_y = cy - 3
        eye_lx = cx - 8
        eye_rx = cx + 8

        shift = 2 * math.sin(self._phase * 0.6) if self._state == "thinking" else 0

        for g in range(2, 0, -1):
            ga = 40 - g * 10
            gc = QColor(base_color.red(), base_color.green(), base_color.blue(), ga)
            painter.setBrush(gc)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(eye_lx + shift, eye_y), 5 + g, 4 + g)
            painter.drawEllipse(QPointF(eye_rx + shift, eye_y), 5 + g, 4 + g)

        if blink:
            painter.setPen(QPen(base_color, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawLine(QPointF(eye_lx - 3 + shift, eye_y), QPointF(eye_lx + 3 + shift, eye_y))
            painter.drawLine(QPointF(eye_rx - 3 + shift, eye_y), QPointF(eye_rx + 3 + shift, eye_y))
        else:
            painter.setBrush(base_color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(eye_lx + shift, eye_y), 4.5, 4)
            painter.drawEllipse(QPointF(eye_rx + shift, eye_y), 4.5, 4)

            painter.setBrush(QColor(0, 0, 0, 210))
            painter.drawEllipse(QPointF(eye_lx + shift, eye_y), 1.2, 3)
            painter.drawEllipse(QPointF(eye_rx + shift, eye_y), 1.2, 3)

            painter.setBrush(QColor(255, 255, 255, 100))
            painter.drawEllipse(QPointF(eye_lx + 1.5 + shift, eye_y - 1.5), 1, 1)
            painter.drawEllipse(QPointF(eye_rx + 1.5 + shift, eye_y - 1.5), 1, 1)

        # Mouth
        mouth_y = cy + 7
        if self._state == "speaking" and self._audio_level > 0.01:
            waves = 5 + int(self._audio_level * 6)
            painter.setPen(QPen(base_color, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            for i in range(waves):
                x = cx - (waves // 2) * 2 + i * 2
                wh = max(1, 3 * abs(math.sin(self._phase * 2.5 + i * 0.7 + self._audio_level * 2)))
                painter.drawLine(QPointF(x, mouth_y - wh), QPointF(x, mouth_y + wh))
        else:
            mouth_color = QColor(base_color.red(), base_color.green(), base_color.blue(), 160)
            painter.setPen(QPen(mouth_color, 1.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            path_left = QPainterPath()
            path_left.moveTo(cx - 1, cy + 5)
            path_left.quadTo(cx - 4, mouth_y, cx - 5, mouth_y + 1)
            painter.drawPath(path_left)
            path_right = QPainterPath()
            path_right.moveTo(cx + 1, cy + 5)
            path_right.quadTo(cx + 4, mouth_y, cx + 5, mouth_y + 1)
            painter.drawPath(path_right)

        # Particles
        speed_mult = 2.0 if self._state == "thinking" else 1.0
        painter.setPen(Qt.PenStyle.NoPen)
        for part in self._particles:
            a = part["angle"] + self._phase * part["speed"] * speed_mult
            px = cx + part["dist"] * math.cos(a)
            py = cy + part["dist"] * math.sin(a)
            pa = int(50 + 70 * (0.5 + 0.5 * math.sin(self._phase * part["speed"] + part["phase"])))
            pc = QColor(base_color.red(), base_color.green(), base_color.blue(), pa)
            painter.setBrush(pc)
            painter.drawEllipse(QPointF(px, py), part["size"], part["size"])

        # Scanline
        scan_color = QColor(base_color.red(), base_color.green(), base_color.blue(), 20)
        painter.setBrush(scan_color)
        painter.setPen(Qt.PenStyle.NoPen)
        sy = cy - hr + self._scan_y
        painter.drawRect(int(cx - hr), int(sy), int(hr * 2), 1)

        # Label
        painter.setPen(base_color)
        painter.setFont(QFont("Consolas", 5, QFont.Weight.Bold))
        painter.drawText(0, self.height() - 2, self.width(), 10, Qt.AlignmentFlag.AlignCenter, label)

        painter.end()
