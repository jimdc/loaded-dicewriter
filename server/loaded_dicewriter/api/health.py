"""Health and readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from loaded_dicewriter import __version__
from loaded_dicewriter.settings import get_settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    version: str


class ReadyResponse(BaseModel):
    ready: bool
    app_ready: bool
    model_ready: bool
    model_mode: str
    version: str
    detail: str


@router.get("/api/healthz", response_model=HealthResponse)
def healthz() -> HealthResponse:
    """Process liveness — the server is up."""
    return HealthResponse(status="ok", version=__version__)


@router.get("/api/readyz", response_model=ReadyResponse)
def readyz() -> ReadyResponse:
    """Readiness distinguishes app config readiness from model readiness."""
    settings = get_settings()
    app_ready = settings.app_ready
    model_ready = settings.model_ready
    ready = app_ready and model_ready
    if not app_ready:
        detail = "application configuration is not ready"
    elif not model_ready:
        detail = "engine is not loaded; app is up in degraded mode"
    else:
        # Keep internal mode for API consumers; user-facing detail avoids "fake".
        engine = (
            "built-in engine"
            if settings.model.mode == "fake"
            else "local model"
            if settings.model.mode == "transformers"
            else settings.model.mode
        )
        detail = f"ready ({engine})"
    return ReadyResponse(
        ready=ready,
        app_ready=app_ready,
        model_ready=model_ready,
        model_mode=settings.model.mode,
        version=settings.version,
        detail=detail,
    )
