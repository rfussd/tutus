from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class ChatMessage:
    role: str
    text: str
    sender: str = ""
    timestamp: float = field(default_factory=time.time)
    tokens: list[str] = field(default_factory=list)


def format_time(t: float | None = None) -> str:
    lt = time.localtime(t or time.time())
    return f"{lt.tm_hour:02d}:{lt.tm_min:02d}"
