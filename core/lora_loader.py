from __future__ import annotations

"""
Carga adaptadores LoRA en el modelo base de Qwen.
Se llama desde streamer.py al iniciar si LORA_ENABLED=True.
"""
import logging
from pathlib import Path
from typing import Any

import torch

from core.config import LORA_ADAPTER_PATH, LORA_ENABLED

log = logging.getLogger("tutus.lora_loader")


_model: Any = None
_tokenizer: Any = None
_lora_loaded: bool = False


def load_lora_adapter(
    adapter_path: str | None = None,
    base_model_name: str | None = None,
) -> bool:
    global _model, _tokenizer, _lora_loaded

    if not LORA_ENABLED:
        return False

    path = adapter_path or LORA_ADAPTER_PATH
    if not path or not Path(path).exists():
        log.warning("[LoRA] No se encontro adaptador en: %s", path)
        return False

    if _lora_loaded:
        log.info("[LoRA] Adaptador ya cargado")
        return True

    try:
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer

        from core.config import MODEL_ID

        model_name = base_model_name or MODEL_ID

        log.info("[LoRA] Cargando base: %s", model_name)
        tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            device_map="auto",
            torch_dtype=torch.bfloat16,
            trust_remote_code=True,
        )

        log.info("[LoRA] Cargando adaptador: %s", path)
        model = PeftModel.from_pretrained(model, path)  # type: ignore[assignment]
        model = model.merge_and_unload()  # type: ignore[operator]

        _model = model
        _tokenizer = tokenizer
        _lora_loaded = True
        log.info("[LoRA] Adaptador cargado exitosamente")
        return True

    except Exception as e:
        log.error("[LoRA] Error cargando adaptador: %s", e)
        return False


def get_lora_model() -> Any:
    return _model


def get_lora_tokenizer() -> Any:
    return _tokenizer


def is_lora_loaded() -> bool:
    return _lora_loaded


def unload_lora() -> None:
    global _model, _tokenizer, _lora_loaded
    _model = None
    _tokenizer = None
    _lora_loaded = False
