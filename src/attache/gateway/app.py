"""FastAPI app — the gateway process."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from ..config import settings
from .api import tasks, turns, ws
from .context import AppContext

STATIC = Path(__file__).parent / "static"


def _configure(app: FastAPI) -> FastAPI:
    app.include_router(turns.router)
    app.include_router(tasks.router)
    app.include_router(ws.router)

    @app.get("/healthz")
    async def healthz() -> dict:
        return {"ok": True, "agent": settings.agent, "router": settings.router}

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(STATIC / "index.html")

    return app


@asynccontextmanager
async def lifespan(app: FastAPI):
    ctx = AppContext(settings)
    await ctx.startup()
    app.state.ctx = ctx
    try:
        yield
    finally:
        await ctx.shutdown()


def create_app() -> FastAPI:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s"
    )
    return _configure(FastAPI(title="Attaché", version="0.0.1", lifespan=lifespan))


def app_from_context(ctx: AppContext) -> FastAPI:
    """Mount the routes against an already-started context (used by tests)."""
    app = FastAPI(title="Attaché (test)")
    app.state.ctx = ctx
    return _configure(app)


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run("attache.gateway.app:app", host="127.0.0.1", port=8787, reload=False)


if __name__ == "__main__":
    main()
