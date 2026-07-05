from __future__ import annotations

import asyncio
import json
import logging
import socket
import sys
import traceback
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

log: logging.Logger = logging.getLogger("tutus.web_server")


ROOT: Path = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

app: FastAPI = FastAPI(title="TUTUS Web")


@app.get("/")
async def get_index() -> HTMLResponse:
    index_path: Path = ROOT / "web" / "static" / "index.html"
    return HTMLResponse(index_path.read_text(encoding="utf-8"))


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/info")
async def info() -> dict[str, Any]:
    from core.config import MODEL_ID
    from core.knowledge_graph import get_knowledge_graph

    kg = get_knowledge_graph()
    stats = kg.get_stats()
    return {
        "model": MODEL_ID,
        "kg_triples": stats["triples"],
        "kg_entities": stats["entities"],
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    log.info("[Web] Cliente conectado")

    loop = asyncio.get_event_loop()

    try:
        while True:
            data: str = await websocket.receive_text()
            msg: dict[str, Any] = json.loads(data)
            text: str = msg.get("text", "").strip()

            if not text:
                await websocket.send_json({"type": "error", "message": "Mensaje vacío"})
                continue

            if text == "!info":
                from core.knowledge_graph import get_knowledge_graph

                kg = get_knowledge_graph()
                await websocket.send_json({"type": "info", "data": kg.get_graph_insights()})
                continue

            from core.conversation import add_to_buffer

            add_to_buffer("user", text)

            await websocket.send_json({"type": "user", "text": text})
            await websocket.send_json({"type": "status", "state": "thinking"})

            def send_token(tok: str) -> None:
                try:
                    asyncio.run_coroutine_threadsafe(websocket.send_json({"type": "token", "text": tok}), loop)
                except Exception as e:
                    log.debug("send_token error: %s", e)

            try:
                from core.agent_router import route

                result: dict[str, Any] = await asyncio.to_thread(route, text, on_token=send_token)
                message: str = result.get("message", "") or "Listo."

                from core.conversation import add_to_buffer

                add_to_buffer("assistant", message)

                await websocket.send_json({"type": "done", "text": message, "domain": result.get("domain", "chat")})
            except Exception as e:
                await websocket.send_json({"type": "error", "message": str(e)})

            await websocket.send_json({"type": "status", "state": "idle"})

    except WebSocketDisconnect:
        log.info("[Web] Cliente desconectado")
    except Exception as e:
        log.error("[Web] Error: %s", e)
        traceback.print_exc()
    finally:
        try:
            await websocket.close()
        except Exception as e:
            log.debug("websocket close error: %s", e)


def get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]  # type: ignore[no-any-return]
    except Exception as e:
        log.debug("get_local_ip error: %s", e)
        return "127.0.0.1"
    finally:
        s.close()


def start_server(port: int = 8080) -> None:
    ip: str = get_local_ip()
    log.info("[Web] Servidor: http://%s:%s", ip, port)
    log.info("[Web] Desde tu celular: http://%s:%s", ip, port)
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="warning")
    server = uvicorn.Server(config)
    try:
        server.run()
    except Exception as e:
        log.error("[Web] Error en servidor: %s", e)
        traceback.print_exc()


if __name__ == "__main__":
    start_server()
