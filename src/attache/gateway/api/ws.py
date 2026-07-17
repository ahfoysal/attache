"""WebSocket /v1/events — the live task-event stream for the dashboard/app."""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


@router.websocket("/v1/events")
async def events_ws(ws: WebSocket) -> None:
    await ws.accept()
    ctx = ws.app.state.ctx
    agen = ctx.bus.subscribe()
    try:
        async for event in agen:
            await ws.send_json(event)
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        await agen.aclose()
