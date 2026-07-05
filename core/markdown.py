from __future__ import annotations

"""Conversión de Markdown a HTML — sin dependencias PyQt."""

import html as html_mod
import re

SUPPORTED_CSS = """
<style>
body {
    color: rgba(200, 235, 255, 230);
    font-family: 'Segoe UI', system-ui, sans-serif;
    font-size: 13px;
    margin: 0;
    line-height: 1.5;
}
b { color: rgba(0, 230, 255, 240); }
i { color: rgba(0, 200, 200, 200); }
code {
    background: rgba(0, 180, 255, 0.1);
    color: rgba(0, 255, 200, 230);
    padding: 1px 6px;
    border-radius: 4px;
    font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
    font-size: 12px;
}
pre {
    background: rgba(0, 0, 0, 0.35);
    padding: 10px 12px;
    border-radius: 8px;
    border: 1px solid rgba(0, 200, 255, 0.12);
    margin: 6px 0;
    overflow-x: auto;
}
pre code {
    background: none;
    padding: 0;
    font-size: 12px;
    color: rgba(180, 230, 255, 220);
    white-space: pre-wrap;
}
.code-block { margin: 6px 0; }
.code-lang {
    color: rgba(0, 180, 255, 120);
    font-size: 10px;
    font-family: 'Consolas', monospace;
    letter-spacing: 1px;
    padding: 2px 8px;
    text-transform: uppercase;
}
li { margin: 2px 0; color: rgba(180, 230, 255, 200); }
a { color: rgba(0, 220, 255, 200); text-decoration: none; }
</style>
"""


def markdown_to_html(text: str) -> str:
    """Convierte markdown simple a HTML."""
    text = html_mod.escape(text)
    text = re.sub(
        r"```(\w*)\n([\s\S]*?)```",
        lambda m: (
            f'<div class="code-block"><div class="code-lang">{m.group(1)}</div><pre><code>{m.group(2)}</code></pre></div>'
            if m.group(1)
            else f"<pre><code>{m.group(2)}</code></pre>"
        ),
        text,
    )
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", text)
    text = re.sub(r"^- (.+)$", r"<li>\1</li>", text, flags=re.MULTILINE)
    text = re.sub(r"^\d+\. (.+)$", r"<li>\1</li>", text, flags=re.MULTILINE)
    text = text.replace("\n", "<br>")
    return text


def wrap_html(body: str) -> str:
    """Envuelve HTML body con CSS completo."""
    return f"<!DOCTYPE html><html><head>{SUPPORTED_CSS}</head><body>{body}</body></html>"


def streaming_html(body: str) -> str:
    """HTML para streaming con cursor."""
    return f"<!DOCTYPE html><html><head>{SUPPORTED_CSS}</head><body>{body}<span style='color:rgba(0,220,255,180);font-size:14px;'>▍</span></body></html>"
