"""In-process WebSocket fan-out for register customer displays."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any

from fastapi import WebSocket


class DisplayHub:
    """Subscribe WebSockets by cash_register_uuid; broadcast JSON dicts."""

    def __init__(self) -> None:
        self._subs: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, cash_register_uuid: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._subs[cash_register_uuid].add(websocket)

    async def disconnect(self, cash_register_uuid: str, websocket: WebSocket) -> None:
        async with self._lock:
            room = self._subs.get(cash_register_uuid)
            if not room:
                return
            room.discard(websocket)
            if not room:
                self._subs.pop(cash_register_uuid, None)

    async def broadcast(self, cash_register_uuid: str, message: dict[str, Any]) -> None:
        async with self._lock:
            sockets = list(self._subs.get(cash_register_uuid) or ())
        dead: list[WebSocket] = []
        for ws in sockets:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.disconnect(cash_register_uuid, ws)


display_hub = DisplayHub()
