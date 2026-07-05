from __future__ import annotations

from pathlib import Path

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QApplication


class Color:
    PRIMARY: QColor = QColor(0, 220, 255)
    PRIMARY_DIM: QColor = QColor(0, 180, 255)
    PRIMARY_DARK: QColor = QColor(0, 150, 255)
    BG_DARK: QColor = QColor(2, 8, 20)
    BG_MEDIUM: QColor = QColor(2, 10, 25)
    BG_LIGHT: QColor = QColor(0, 30, 60, 40)
    TEXT: QColor = QColor(200, 235, 255, 230)
    TEXT_DIM: QColor = QColor(0, 180, 255, 140)
    TEXT_BRIGHT: QColor = QColor(0, 220, 255, 200)
    BORDER: QColor = QColor(0, 200, 255, 50)
    BORDER_HOVER: QColor = QColor(0, 200, 255, 120)
    BORDER_STRONG: QColor = QColor(0, 200, 255, 80)
    GLOW: QColor = QColor(0, 200, 255, 40)
    GLOW_SOFT: QColor = QColor(0, 100, 255, 25)
    SUCCESS: QColor = QColor(0, 255, 150)
    WARNING: QColor = QColor(255, 180, 0)
    SPEAKING: QColor = QColor(255, 100, 200)
    DANGER: QColor = QColor(255, 60, 60)
    DANGER_BG: QColor = QColor(255, 60, 60, 30)
    USER_BG_START: QColor = QColor(0, 60, 120, 30)
    USER_BG_END: QColor = QColor(0, 80, 160, 15)
    USER_BORDER: QColor = QColor(0, 150, 255, 60)
    ASSISTANT_BG_START: QColor = QColor(0, 30, 60, 40)
    ASSISTANT_BG_END: QColor = QColor(0, 15, 30, 20)
    ASSISTANT_BORDER: QColor = QColor(0, 200, 255, 50)
    CODE_BG: QColor = QColor(0, 0, 0, 35)
    CODE_BORDER: QColor = QColor(0, 200, 255, 12)
    CODE_TEXT: QColor = QColor(180, 230, 255, 220)
    INPUT_BG: QColor = QColor(0, 150, 255, 12)
    INPUT_FOCUS: QColor = QColor(0, 200, 255, 120)
    TRAY_BG: QColor = QColor(2, 8, 20, 240)

    @classmethod
    def rgba(cls, color: QColor, alpha: int | None = None) -> str:  # noqa: N804
        if alpha is not None:
            return f"rgba({color.red()},{color.green()},{color.blue()},{alpha})"
        return f"rgba({color.red()},{color.green()},{color.blue()},{color.alpha()})"


STYLES_DIR: Path = Path(__file__).parent


def load_stylesheet() -> str:
    qss_path: Path = STYLES_DIR / "styles.qss"
    if qss_path.exists():
        return qss_path.read_text(encoding="utf-8")
    return ""


def apply_theme(app: QApplication) -> None:
    qss: str = load_stylesheet()
    if qss:
        app.setStyleSheet(qss)
