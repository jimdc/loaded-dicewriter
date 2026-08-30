"""Lightweight status for the application shell."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from loaded_dicewriter.generation.fake_engine import FakeEngine
from loaded_dicewriter.settings import get_settings

router = APIRouter(tags=["status"])


class StatusResponse(BaseModel):
    name: str
    version: str
    model_mode: str
    model_ready: bool
    app_ready: bool
    telemetry: bool
    host: str
    port: int
    fake_sample: str | None = None


@router.get("/api/status", response_model=StatusResponse)
def status() -> StatusResponse:
    settings = get_settings()
    sample: str | None = None
    if settings.model.mode == "fake":
        result = FakeEngine().generate_pair("status probe", seed=0, length=6)
        sample = result.loaded.text
    return StatusResponse(
        name="loaded-dicewriter",
        version=settings.version,
        model_mode=settings.model.mode,
        model_ready=settings.model_ready,
        app_ready=settings.app_ready,
        telemetry=settings.privacy.telemetry,
        host=settings.server.host,
        port=settings.server.port,
        fake_sample=sample,
    )
