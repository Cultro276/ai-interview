import os
import asyncio
import pytest
from typing import Any

from httpx import Response as _HttpxResponse  # type: ignore
from fastapi.testclient import TestClient

from src.main import app
from src.db.session import async_session_factory, engine
from src.db.base import Base
from src.db.models.job import Job
from src.db.models.candidate import Candidate
from src.db.models.interview import Interview


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def ensure_schema() -> None:
    # Create tables if they don't exist (idempotent)
    async def _create() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    asyncio.get_event_loop().run_until_complete(_create())


@pytest.mark.anyio
async def test_tts_elevenlabs_returns_audio_when_env_present_and_http_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    os.environ["ELEVENLABS_API_KEY"] = "test-key"
    os.environ["ELEVENLABS_VOICE_ID"] = "test-voice"

    class _FakeResp:
        def __init__(self) -> None:
            self.status_code = 200
            self.content = b"ID3\x00fake-mp3"
            self.text = ""

        def raise_for_status(self) -> None:
            return None

    class _FakeAsyncClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: D401
            pass

        async def __aenter__(self) -> "_FakeAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
            return None

        async def post(self, *args: Any, **kwargs: Any) -> _HttpxResponse:  # type: ignore[override]
            return _FakeResp()  # type: ignore[return-value]

    import httpx  # type: ignore

    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient, raising=True)

    # Call API
    from fastapi.testclient import TestClient
    tc = TestClient(app)
    resp = tc.post("/api/v1/tts/speak", json={"text": "merhaba", "lang": "tr", "provider": "elevenlabs"})
    assert resp.status_code == 200
    assert resp.headers.get("content-type", "").startswith("audio/")


@pytest.mark.anyio
async def test_upload_transcript_marks_completed() -> None:
    # Arrange: create job, candidate, interview with audio_url set
    async with async_session_factory() as session:
        job = Job(user_id=1, title="QA Engineer", description="test job")
        session.add(job)
        await session.flush()
        cand = Candidate(user_id=1, name="Test", email="test@example.com", status="pending", token="tok", expires_at=None)
        session.add(cand)
        await session.flush()
        intv = Interview(job_id=job.id, candidate_id=cand.id, status="pending", audio_url="s3://bucket/media/test.webm")
        session.add(intv)
        await session.commit()
        int_id = intv.id

    # Act: post transcript
    from fastapi.testclient import TestClient
    tc = TestClient(app)
    r = tc.post(f"/api/v1/interviews/{int_id}/transcript", json={"text": "deneme transcript", "provider": "manual"})
    assert r.status_code == 200

    # Assert: interview is completed
    async with async_session_factory() as session:
        refreshed = await session.get(Interview, int_id)
        assert refreshed is not None
        assert refreshed.status == "completed"


