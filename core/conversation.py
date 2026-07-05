from __future__ import annotations

import logging

log = logging.getLogger("tutus.conversation")

_conversation_buffer: list[dict[str, str]] = []


def add_to_buffer(role: str, content: str) -> None:
    global _conversation_buffer
    _conversation_buffer.append({"role": role, "content": content})
    if len(_conversation_buffer) > 8:
        _conversation_buffer.pop(0)
    try:
        from core.memory_signals import log_conversation

        log_conversation(role, content[:1000])
    except Exception as e:
        log.debug("log_conversation error: %s", e)


def get_buffer() -> list[dict[str, str]]:
    return _conversation_buffer
