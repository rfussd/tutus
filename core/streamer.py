from __future__ import annotations

import json
import re
from collections.abc import Callable

import requests

from core.config import LM_STUDIO_URL, MODEL_ID


def stream_chat(
    messages: list[dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 1024,
    on_token: Callable[[str], None] | None = None,
) -> str:
    full_content = ""
    accumulated = ""
    try:
        response = requests.post(
            LM_STUDIO_URL,
            json={
                "model": MODEL_ID,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True,
            },
            stream=True,
            timeout=120,
        )

        for raw_line in response.iter_lines():
            if not raw_line:
                continue
            line = raw_line.decode("utf-8", errors="ignore")
            if line.startswith("data: "):
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        full_content += content
                        accumulated += content
                        if on_token and (content in (" ", "\n", ".", "!", "?", ",") or len(accumulated) >= 5):
                            on_token(accumulated)
                            accumulated = ""
                except json.JSONDecodeError:
                    continue

        if on_token and accumulated:
            on_token(accumulated)

    except requests.exceptions.ConnectionError:
        full_content = "No puedo conectarme a LM Studio."
        if on_token:
            on_token(full_content)
    except Exception as e:
        full_content = f"Error: {str(e)}"
        if on_token:
            on_token(full_content)

    full_content = re.sub(r"<think>.*?</think>", "", full_content, flags=re.DOTALL).strip()
    return full_content


def stream_think(
    system_prompt: str,
    user_content: str,
    temperature: float = 0.1,
    max_tokens: int = 512,
    on_token: Callable[[str], None] | None = None,
) -> str:
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]
    return stream_chat(messages, temperature, max_tokens, on_token=on_token)
