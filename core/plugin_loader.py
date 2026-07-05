from __future__ import annotations

import importlib
import inspect
import logging
import sys
from collections.abc import Callable
from typing import Any

from core.config import PLUGINS_DIR

log = logging.getLogger("tutus.plugin_loader")


class PluginBase:
    name: str = "unnamed"
    version: str = "0.1"
    description: str = ""
    domain: str = "plugin"

    def on_load(self) -> None:
        pass

    def get_skills(self) -> dict[str, Callable[..., Any]]:
        return {}

    def get_agent_prompt(self) -> str:
        return ""


_loaded_plugins: dict[str, PluginBase] = {}


def discover_plugins() -> list[str]:
    if not PLUGINS_DIR.exists():
        PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
        (PLUGINS_DIR / "__init__.py").write_text("")
        return []

    plugins = []
    for entry in PLUGINS_DIR.iterdir():
        if entry.is_dir() and not entry.name.startswith("_"):
            init_file = entry / "__init__.py"
            if init_file.exists():
                plugins.append(entry.name)
        elif entry.suffix == ".py" and not entry.name.startswith("_"):
            plugins.append(entry.stem)

    return plugins


def load_plugin(plugin_name: str) -> bool:
    global _loaded_plugins

    try:
        if PLUGINS_DIR.exists() and str(PLUGINS_DIR) not in sys.path:
            sys.path.insert(0, str(PLUGINS_DIR))

        module = importlib.import_module(plugin_name)

        for _, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and issubclass(obj, PluginBase) and obj is not PluginBase:
                instance = obj()
                instance.on_load()
                _loaded_plugins[plugin_name] = instance
                log.info("[Plugins] Cargado: %s v%s", instance.name, instance.version)
                return True

        log.warning("[Plugins] %s: no se encontro clase Plugin", plugin_name)
        return False

    except Exception as e:
        log.error("[Plugins] Error cargando %s: %s", plugin_name, e)
        return False


def load_all_plugins() -> list[str]:
    results = []
    for name in discover_plugins():
        if load_plugin(name):
            results.append(name)
    return results


def get_plugin_skills() -> dict[str, Callable[..., Any]]:
    skills = {}
    for plugin in _loaded_plugins.values():
        skills.update(plugin.get_skills())
    return skills


def get_plugin_domains() -> dict[str, str]:
    prompts = {}
    for name, plugin in _loaded_plugins.items():
        prompt = plugin.get_agent_prompt()
        if prompt:
            prompts[plugin.domain or name] = prompt
    return prompts
