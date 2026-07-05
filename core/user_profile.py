from __future__ import annotations

from datetime import datetime
from typing import Any

from core.memory_signals import get_domain_signals, get_signal, set_signal

DOMAIN: str = "profile"


def update_preference(key: str, value: Any) -> None:
    set_signal(DOMAIN, key, value)
    set_signal(DOMAIN, "last_updated", datetime.now().isoformat())


def get_preference(key: str, default: Any = None) -> Any:
    return get_signal(DOMAIN, key, default)


def get_user_profile_summary() -> str:
    from core.memory_signals import search_memories

    parts = []

    profile_data = get_domain_signals(DOMAIN)
    if profile_data:
        lines = [f"  - {k}: {v}" for k, v in profile_data.items() if k != "last_updated"]
        if lines:
            parts.append("Preferencias:\n" + "\n".join(lines))

    memories = search_memories("", limit=10)
    if memories:
        mem_lines = [f"  - {m['content']}" for m in memories]
        parts.append("Información personal:\n" + "\n".join(mem_lines))

    music_signals = get_domain_signals("music")
    if music_signals:
        recent = music_signals.get("recent_artists", [])
        platform = music_signals.get("preferred_platform", "spotify")
        music_info = f"  - Plataforma favorita: {platform}"
        if recent:
            music_info += f"\n  - Artistas recientes: {', '.join(recent[:3])}"
        parts.append("Música:\n" + music_info)

    files_signals = get_domain_signals("files")
    if files_signals:
        folders = files_signals.get("frequent_folders", [])
        if folders:
            parts.append("Carpetas frecuentes:\n" + "\n".join(f"  - {f}" for f in folders))

    return "\n\n".join(parts) if parts else ""
