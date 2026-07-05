from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import quote_plus, urlparse

import requests
from ddgs import DDGS

from core.config import LM_STUDIO_URL, MODEL_ID

log = logging.getLogger("tutus.web_research_skill")


def _fetch_url(url: str) -> str:
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        text = resp.text
        text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:5000]
    except Exception as e:
        log.debug("fetch_url error: %s", e)
        return ""


def _google_search(query: str) -> list[dict[str, str]]:
    url = f"https://www.google.com/search?q={quote_plus(query)}&hl=es"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "es-ES,es;q=0.9",
    }
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    html = resp.text

    results = []
    for div in re.findall(r'<div[^>]*class="[^"]*g[^"]*"[^>]*>.*?</div>', html, re.DOTALL):
        title_match = re.search(r"<h3[^>]*>(.*?)</h3>", div, re.DOTALL)
        link_match = re.search(r'<a[^>]*href="(/url\?q=[^"&]+|https?://[^"]+)"', div)
        snippet_match = re.search(r'<div[^>]*class="[^"]*VwiC3b[^"]*"[^>]*>(.*?)</div>', div, re.DOTALL)

        title = re.sub(r"<[^>]+>", "", title_match.group(1)).strip() if title_match else ""
        href = link_match.group(1) if link_match else ""
        snippet = re.sub(r"<[^>]+>", "", snippet_match.group(1)).strip() if snippet_match else ""

        if href.startswith("/url?q="):
            from urllib.parse import parse_qs

            href = parse_qs(urlparse(href).query).get("q", [""])[0]
        elif not href.startswith("http"):
            href = ""

        if title and href:
            results.append({"title": title, "href": href, "body": snippet})

    return results


def _summarize_with_llm(content: str, question: str) -> str:
    prompt = f"""Información encontrada en la web para: {question}

{content[:4000]}

Con base en esto, responde de forma natural y conversacional, como si charlaras con un amigo.
Da tu análisis y opinión sobre el tema. Si te preguntan quién va a ganar, da tu pronóstico.
No te limites a enumerar datos — interpreta la información y saca conclusiones propias.
Responde en español."""

    try:
        resp = requests.post(
            LM_STUDIO_URL,
            json={
                "model": MODEL_ID,
                "messages": [
                    {
                        "role": "system",
                        "content": "Eres un analista e investigador. Lees información web y das tu análisis personal, opiniones y conclusiones de forma natural y conversacional. No eres un listador de datos.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.7,
                "max_tokens": 768,
                "stream": False,
            },
            timeout=60,
        )
        return resp.json()["choices"][0]["message"]["content"].strip()  # type: ignore[no-any-return]
    except Exception as e:
        return f"Error al resumir: {e}"


def _search(query: str) -> list[dict[str, Any]]:
    try:
        with DDGS() as ddgs:
            return list(ddgs.text(query, max_results=5))
    except Exception as e:
        log.debug("DDGS search error: %s", e)

    try:
        return _google_search(query)
    except Exception as e:
        log.debug("google search error: %s", e)

    return []


def search_and_summarize(query: str) -> str:
    try:
        results = _search(query)

        if not results:
            return f"No encontré resultados para: {query}"

        all_content = [f"Resultados de búsqueda para: {query}"]
        links_to_fetch = []

        for r in results[:3]:
            title = r.get("title", "")
            snippet = r.get("body", "")
            href = r.get("href", "")
            all_content.append(f"\n- {title}: {snippet[:300]}")
            if href:
                links_to_fetch.append(href)

        for link in links_to_fetch:
            content = _fetch_url(link)
            if content:
                all_content.append(f"\n--- {link} ---\n{content[:2000]}")

        combined = "\n".join(all_content)
        return _summarize_with_llm(combined, query)

    except Exception as e:
        return f"Error en investigación web: {e}"


def fetch_url_content(url: str) -> str:
    content = _fetch_url(url)
    if not content:
        return "No se pudo obtener el contenido."
    return _summarize_with_llm(content, f"Resume el contenido de {url}")
