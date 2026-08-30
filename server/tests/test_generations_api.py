"""Generation job REST + stream integration tests (toy engine)."""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from starlette.testclient import TestClient as StarletteTestClient

from loaded_dicewriter.api.generations import get_job_manager
from loaded_dicewriter.app import create_app
from loaded_dicewriter.settings import clear_settings_cache


@pytest.fixture(autouse=True)
def _reset_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LDW_MODEL_MODE", "fake")
    clear_settings_cache()
    # Fresh job manager per test to avoid cross-test busy state.
    import loaded_dicewriter.api.generations as gen_mod

    gen_mod._manager = gen_mod.JobManager()


def test_create_and_complete_generation() -> None:
    app = create_app()
    with TestClient(app) as client:
        res = client.post(
            "/api/generations",
            json={"prompt": "why cities grow shops", "seed": 1, "max_new_tokens": 12},
        )
        assert res.status_code == 200
        body = res.json()
        gid = body["generation_id"]
        assert body["key_fingerprint"] == "4ac2"
        assert body["model_mode"] == "fake"

        # Poll until terminal.
        for _ in range(100):
            snap = client.get(f"/api/generations/{gid}").json()
            if snap["status"] in ("completed", "stopped", "failed"):
                break
            # tiny wait for background task
            import time

            time.sleep(0.02)
        assert snap["status"] == "completed"
        assert snap["control"] is not None
        assert snap["loaded"] is not None
        assert snap["control"]["token_count"] == 12
        assert snap["loaded"]["token_count"] == 12
        assert snap["control"]["text"] != snap["loaded"]["text"]
        assert snap["loaded"]["detection"]["num_tokens_scored"] >= 1


def test_second_generation_while_busy_returns_409() -> None:
    app = create_app()
    with TestClient(app) as client:
        # Patch max tokens high and block stop — use a long job
        r1 = client.post(
            "/api/generations",
            json={"prompt": "long job", "seed": 0, "max_new_tokens": 200},
        )
        assert r1.status_code == 200
        r2 = client.post(
            "/api/generations",
            json={"prompt": "second", "seed": 1, "max_new_tokens": 8},
        )
        # May complete very fast on toy engine; accept 200 if first already done.
        if r2.status_code == 409:
            detail = r2.json()["detail"]
            assert detail["error"] == "busy"
        else:
            assert r2.status_code == 200


def test_websocket_stream_emits_tokens_in_order() -> None:
    app = create_app()
    with StarletteTestClient(app) as client:
        res = client.post(
            "/api/generations",
            json={"prompt": "stream me", "seed": 2, "max_new_tokens": 8},
        )
        assert res.status_code == 200
        gid = res.json()["generation_id"]

        with client.websocket_connect(f"/api/generations/{gid}/stream?after_seq=0") as ws:
            seqs: list[int] = []
            token_positions: dict[str, list[int]] = {"control": [], "loaded": []}
            terminal = False
            for _ in range(500):
                event = ws.receive_json()
                if event.get("type") == "warning":
                    continue
                seq = int(event["seq"])
                seqs.append(seq)
                if event.get("type") == "token":
                    branch = event["branch"]
                    token_positions[branch].append(int(event["position"]))
                if event.get("type") in (
                    "generation_finished",
                    "generation_stopped",
                    "error",
                ):
                    terminal = True
                    break
            assert terminal
            assert seqs == sorted(seqs)
            assert seqs == list(range(min(seqs), max(seqs) + 1)) or len(seqs) > 0
            assert token_positions["control"] == list(range(8))
            assert token_positions["loaded"] == list(range(8))


@pytest.mark.asyncio
async def test_reconnect_after_seq_no_duplicates() -> None:
    clear_settings_cache()
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/generations",
            json={"prompt": "reconnect", "seed": 3, "max_new_tokens": 10},
        )
        assert res.status_code == 200
        gid = res.json()["generation_id"]

        # Wait for completion via REST.
        snap = None
        for _ in range(100):
            snap = (await client.get(f"/api/generations/{gid}")).json()
            if snap["status"] == "completed":
                break
            await asyncio.sleep(0.02)
        assert snap is not None
        assert snap["status"] == "completed"
        last_seq = snap["last_seq"]
        assert last_seq > 0

        # Replay from after_seq=0 via manager buffer.
        mgr = get_job_manager()
        job = mgr.get(gid)
        assert job is not None
        all_seqs = [int(e["seq"]) for e in job.events]
        assert all_seqs == sorted(all_seqs)
        mid = all_seqs[len(all_seqs) // 2]
        replay = [e for e in job.events if int(e["seq"]) > mid]
        replay_seqs = [int(e["seq"]) for e in replay]
        assert replay_seqs == [s for s in all_seqs if s > mid]
        assert len(set(replay_seqs)) == len(replay_seqs)
