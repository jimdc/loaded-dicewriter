"""Generation job API — create pair jobs and stream events (toy engine first)."""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from loaded_dicewriter.core.keys import TEACHING_KEY, key_fingerprint
from loaded_dicewriter.core.profiles import get_profile
from loaded_dicewriter.generation.fake_engine import FakeEngine
from loaded_dicewriter.settings import get_settings

router = APIRouter(tags=["generations"])


class JobStatus(StrEnum):
    queued = "queued"
    running = "running"
    completed = "completed"
    stopped = "stopped"
    failed = "failed"


class CreateGenerationRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=8000)
    seed: int = 0
    max_new_tokens: int = Field(default=48, ge=1, le=256)
    profile_id: str = "teaching-kgw"
    temperature: float = Field(default=1.0, ge=0.1, le=2.0)


class CreateGenerationResponse(BaseModel):
    generation_id: str
    status: JobStatus
    model_mode: str
    profile_id: str
    key_fingerprint: str
    seed: int
    max_new_tokens: int


class BranchSnapshot(BaseModel):
    label: Literal["control", "loaded"]
    text: str
    token_count: int
    detection: dict[str, Any]
    tokens: list[dict[str, Any]]


class GenerationSnapshot(BaseModel):
    generation_id: str
    status: JobStatus
    prompt: str
    seed: int
    model_mode: str
    profile_id: str
    key_fingerprint: str
    error: str | None = None
    control: BranchSnapshot | None = None
    loaded: BranchSnapshot | None = None
    last_seq: int = 0


@dataclass
class GenerationJob:
    id: str
    prompt: str
    seed: int
    max_new_tokens: int
    profile_id: str
    temperature: float
    model_mode: str
    key: bytes
    status: JobStatus = JobStatus.queued
    error: str | None = None
    events: list[dict[str, Any]] = field(default_factory=list)
    control_text: str = ""
    loaded_text: str = ""
    control_tokens: list[dict[str, Any]] = field(default_factory=list)
    loaded_tokens: list[dict[str, Any]] = field(default_factory=list)
    control_detection: dict[str, Any] = field(default_factory=dict)
    loaded_detection: dict[str, Any] = field(default_factory=dict)
    stop_requested: bool = False
    created_at: float = field(default_factory=time.time)
    task: asyncio.Task[None] | None = None
    _seq: int = 0
    _cond: asyncio.Condition = field(default_factory=asyncio.Condition)

    def next_seq(self) -> int:
        self._seq += 1
        return self._seq

    @property
    def last_seq(self) -> int:
        return self._seq

    async def append_event(self, event: dict[str, Any]) -> dict[str, Any]:
        event = dict(event)
        event.setdefault("v", 1)
        event.setdefault("generation_id", self.id)
        event["seq"] = self.next_seq()
        self.events.append(event)
        # Bound replay buffer (keep last N events + always keep early lifecycle).
        if len(self.events) > 4000:
            self.events = self.events[-3500:]
        async with self._cond:
            self._cond.notify_all()
        return event


class JobManager:
    """Single active generation at a time (spec §9.6)."""

    def __init__(self) -> None:
        self._jobs: dict[str, GenerationJob] = {}
        self._active_id: str | None = None
        self._lock = asyncio.Lock()

    def get(self, generation_id: str) -> GenerationJob | None:
        return self._jobs.get(generation_id)

    async def create(self, req: CreateGenerationRequest) -> GenerationJob:
        settings = get_settings()
        async with self._lock:
            if self._active_id is not None:
                active = self._jobs.get(self._active_id)
                if active and active.status in (JobStatus.queued, JobStatus.running):
                    raise HTTPException(
                        status_code=409,
                        detail={
                            "error": "busy",
                            "message": "A generation is already running. Stop it or wait.",
                            "active_generation_id": self._active_id,
                        },
                    )
            profile = get_profile(req.profile_id)
            job = GenerationJob(
                id=str(uuid.uuid4()),
                prompt=req.prompt.strip(),
                seed=req.seed,
                max_new_tokens=req.max_new_tokens,
                profile_id=profile.id,
                temperature=req.temperature,
                model_mode=settings.model.mode,
                key=TEACHING_KEY,
            )
            self._jobs[job.id] = job
            self._active_id = job.id
            job.task = asyncio.create_task(self._run_job(job))
            return job

    async def stop(self, generation_id: str) -> GenerationJob:
        job = self._jobs.get(generation_id)
        if job is None:
            raise HTTPException(status_code=404, detail="generation not found")
        job.stop_requested = True
        return job

    async def _run_job(self, job: GenerationJob) -> None:
        job.status = JobStatus.running
        await job.append_event(
            {
                "type": "generation_accepted",
                "model_mode": job.model_mode,
                "profile_id": job.profile_id,
                "key_fingerprint": key_fingerprint(job.key),
                "seed": job.seed,
                "max_new_tokens": job.max_new_tokens,
            }
        )
        try:
            if job.model_mode == "transformers":
                await self._run_transformers(job)
            else:
                await self._run_fake(job)
            if job.stop_requested:
                job.status = JobStatus.stopped
                await job.append_event({"type": "generation_stopped"})
            else:
                job.status = JobStatus.completed
                await job.append_event({"type": "generation_finished"})
        except Exception as exc:  # noqa: BLE001 — surface to client event stream
            job.status = JobStatus.failed
            job.error = str(exc)
            await job.append_event({"type": "error", "message": "generation failed"})
        finally:
            async with self._lock:
                if self._active_id == job.id:
                    self._active_id = None

    async def _run_fake(self, job: GenerationJob) -> None:
        profile = get_profile(job.profile_id)
        engine = FakeEngine(
            default_length=job.max_new_tokens,
            key=job.key,
            profile=profile,
            temperature=job.temperature,
        )
        stop_flag = [False]

        for branch in ("control", "loaded"):
            await job.append_event({"type": "branch_started", "branch": branch})

        # Stream interleaved steps with tiny yields so WS clients stay responsive.
        for step in engine.iter_pair_steps(
            job.prompt,
            seed=job.seed,
            length=job.max_new_tokens,
            stop_flag=stop_flag,
        ):
            if job.stop_requested:
                stop_flag[0] = True
                break

            token = step.token
            event = {
                "type": "token",
                "branch": step.branch,
                "position": step.position,
                "token_id": token.token_id,
                "text": token.text,
                "favored": token.favored,
                "eligible": token.eligible,
                "exclusion_reason": token.exclusion_reason,
                "z_score": token.z_score_after,
                "p_value": token.p_value_after,
                "green_count": token.green_count_after,
                "scored_count": token.scored_count_after,
                "latency_ms": token.latency_ms,
                "base_probability": token.base_probability,
                "biased_probability": token.biased_probability,
                "final_sampling_probability": token.final_sampling_probability,
                "base_logit": token.base_logit,
                "biased_logit": token.biased_logit,
                "entropy": token.entropy,
                "context_ids": token.context_ids,
                "top_candidates_before": [c.as_dict() for c in token.top_candidates_before],
                "top_candidates_after": [c.as_dict() for c in token.top_candidates_after],
                "text_so_far": step.text_so_far,
                "detection": step.detection,
            }
            if step.branch == "control":
                job.control_text = step.text_so_far
                job.control_tokens.append(token.as_dict())
                job.control_detection = step.detection
            else:
                job.loaded_text = step.text_so_far
                job.loaded_tokens.append(token.as_dict())
                job.loaded_detection = step.detection
            await job.append_event(event)
            # Pace the toy stream so the UI can paint tokens + live z-scores.
            # (Still fast; without this, the job finishes before the first frame.)
            await asyncio.sleep(0.035)

        for branch in ("control", "loaded"):
            await job.append_event({"type": "branch_finished", "branch": branch})

    async def _run_transformers(self, job: GenerationJob) -> None:
        """Real-model path: load backend and stream if weights are available."""
        from loaded_dicewriter.inference.transformers_backend import (
            TransformersBackend,
            TransformersConfigError,
        )

        settings = get_settings()
        try:
            backend = TransformersBackend.from_settings(settings)
        except TransformersConfigError as exc:
            raise RuntimeError(str(exc)) from exc

        await job.append_event({"type": "model_loading", "detail": "loading local model"})
        await backend.load()
        try:
            profile = get_profile(job.profile_id)
            async for event in backend.generate_pair_events(
                prompt=job.prompt,
                seed=job.seed,
                max_new_tokens=job.max_new_tokens,
                temperature=job.temperature,
                key=job.key,
                profile=profile,
                should_stop=lambda: job.stop_requested,
            ):
                branch = event.get("branch")
                if event.get("type") == "token" and branch in ("control", "loaded"):
                    if branch == "control":
                        job.control_text = str(event.get("text_so_far", job.control_text))
                        job.control_tokens.append(event)
                        det = event.get("detection")
                        if isinstance(det, dict):
                            job.control_detection = det
                    else:
                        job.loaded_text = str(event.get("text_so_far", job.loaded_text))
                        job.loaded_tokens.append(event)
                        det = event.get("detection")
                        if isinstance(det, dict):
                            job.loaded_detection = det
                await job.append_event(event)
        finally:
            # Keep model resident for subsequent jobs; unload only on explicit settings later.
            pass


_manager = JobManager()


def get_job_manager() -> JobManager:
    return _manager


def _branch_snapshot(
    label: Literal["control", "loaded"],
    text: str,
    tokens: list[dict[str, Any]],
    detection: dict[str, Any],
) -> BranchSnapshot:
    return BranchSnapshot(
        label=label,
        text=text,
        token_count=len(tokens),
        detection=detection,
        tokens=tokens,
    )


def _snapshot(job: GenerationJob) -> GenerationSnapshot:
    return GenerationSnapshot(
        generation_id=job.id,
        status=job.status,
        prompt=job.prompt,
        seed=job.seed,
        model_mode=job.model_mode,
        profile_id=job.profile_id,
        key_fingerprint=key_fingerprint(job.key),
        error=job.error,
        control=_branch_snapshot(
            "control", job.control_text, job.control_tokens, job.control_detection
        )
        if job.control_tokens or job.control_text
        else None,
        loaded=_branch_snapshot(
            "loaded", job.loaded_text, job.loaded_tokens, job.loaded_detection
        )
        if job.loaded_tokens or job.loaded_text
        else None,
        last_seq=job.last_seq,
    )


@router.post("/api/generations", response_model=CreateGenerationResponse)
async def create_generation(req: CreateGenerationRequest) -> CreateGenerationResponse:
    job = await _manager.create(req)
    return CreateGenerationResponse(
        generation_id=job.id,
        status=job.status,
        model_mode=job.model_mode,
        profile_id=job.profile_id,
        key_fingerprint=key_fingerprint(job.key),
        seed=job.seed,
        max_new_tokens=job.max_new_tokens,
    )


@router.get("/api/generations/{generation_id}", response_model=GenerationSnapshot)
async def get_generation(generation_id: str) -> GenerationSnapshot:
    job = _manager.get(generation_id)
    if job is None:
        raise HTTPException(status_code=404, detail="generation not found")
    return _snapshot(job)


@router.post("/api/generations/{generation_id}/stop", response_model=GenerationSnapshot)
async def stop_generation(generation_id: str) -> GenerationSnapshot:
    job = await _manager.stop(generation_id)
    return _snapshot(job)


@router.websocket("/api/generations/{generation_id}/stream")
async def stream_generation(websocket: WebSocket, generation_id: str) -> None:
    await websocket.accept()
    job = _manager.get(generation_id)
    if job is None:
        await websocket.send_json(
            {"v": 1, "type": "error", "message": "generation not found", "seq": 0}
        )
        await websocket.close(code=4404)
        return

    # after_seq query param for reconnect replay
    after_seq = 0
    raw = websocket.query_params.get("after_seq")
    if raw is not None:
        try:
            after_seq = max(0, int(raw))
        except ValueError:
            after_seq = 0

    try:
        cursor = after_seq
        while True:
            # Replay buffered events after cursor.
            batch = [e for e in job.events if int(e.get("seq", 0)) > cursor]
            for event in batch:
                await websocket.send_json(event)
                cursor = int(event["seq"])

            terminal = job.status in (
                JobStatus.completed,
                JobStatus.stopped,
                JobStatus.failed,
            )
            if terminal and cursor >= job.last_seq:
                break

            async with job._cond:
                try:
                    await asyncio.wait_for(job._cond.wait(), timeout=1.0)
                except TimeoutError:
                    # keepalive: clients ignore unknown types or use as ping
                    await websocket.send_json(
                        {
                            "v": 1,
                            "type": "warning",
                            "message": "keepalive",
                            "generation_id": job.id,
                            "seq": job.last_seq,
                        }
                    )
    except WebSocketDisconnect:
        return
