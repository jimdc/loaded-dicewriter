"""FastAPI application — loopback by default, static frontend in production."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from loaded_dicewriter import __version__
from loaded_dicewriter.api import generations, health, status
from loaded_dicewriter.base_path import AppBasePathMiddleware
from loaded_dicewriter.settings import REPO_ROOT, get_settings

STATIC_DIR = REPO_ROOT / "web" / "dist"


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    settings.server.data_dir.mkdir(parents=True, exist_ok=True)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="loaded-dicewriter",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    app.include_router(health.router)
    app.include_router(status.router)
    app.include_router(generations.router)

    @app.get("/api/version")
    def version() -> dict[str, str]:
        return {"version": __version__, "name": "loaded-dicewriter"}

    # Production: serve compiled frontend from the same origin (web root).
    # With APP_BASE_PATH=/loaded-dicewriter/, the hub gateway strips the slug
    # (default) so /loaded-dicewriter/x arrives as /x. Middleware also accepts
    # unstripped prefixed paths when strip_prefix:false or for local checks.
    if STATIC_DIR.is_dir() and (STATIC_DIR / "index.html").is_file():
        assets = STATIC_DIR / "assets"
        if assets.is_dir():
            app.mount("/assets", StaticFiles(directory=assets), name="assets")

        @app.get("/{full_path:path}")
        def spa_fallback(full_path: str) -> FileResponse:
            # Never let the SPA swallow API routes (already registered above).
            candidate = STATIC_DIR / full_path
            if full_path and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(STATIC_DIR / "index.html")

    # Last added = outermost on request: strip hub prefix before routing.
    app.add_middleware(AppBasePathMiddleware, base_path=settings.app_base_path)

    return app


app = create_app()
