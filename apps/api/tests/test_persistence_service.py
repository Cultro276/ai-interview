import asyncio
import pytest
from typing import Any

from fastapi.testclient import TestClient

from src.main import app
from src.db.session import async_session_factory, engine
from src.db.base import Base
from src.db.models.job import Job
from src.db.models.candidate import Candidate
from src.db.models.interview import Interview
from src.db.models.conversation import ConversationMessage, MessageRole
from src.services.persistence import (
    persist_user_message,
    persist_assistant_message,
    fetch_messages,
)


@pytest.fixture(scope="session", autouse=True)
def ensure_schema() -> None:
    async def _create() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    asyncio.get_event_loop().run_until_complete(_create())


@pytest.mark.asyncio
async def test_persist_user_idempotent_on_same_last_message() -> None:
    async with async_session_factory() as session:
        # Arrange: create interview
        job = Job(user_id=1, title="Dev", description="desc")
        session.add(job)
        await session.flush()
        cand = Candidate(user_id=1, name="Ca", email="c@example.com", status="pending", token="t", expires_at=None)
        session.add(cand)
        await session.flush()
        iv = Interview(job_id=job.id, candidate_id=cand.id, status="pending")
        session.add(iv)
        await session.commit()

        # Act: persist the same user message twice
        m1 = await persist_user_message(session, iv.id, "hello")
        m2 = await persist_user_message(session, iv.id, "hello")

        # Assert: only one user message exists and ids are same (idempotent)
        msgs = await fetch_messages(session, iv.id)
        user_msgs = [m for m in msgs if m.role == MessageRole.USER]
        assert len(user_msgs) == 1
        assert m1 is not None and m2 is not None
        assert m1.id == m2.id
        assert user_msgs[0].sequence_number == 1


@pytest.mark.asyncio
async def test_persist_assistant_deduplicates_by_content() -> None:
    async with async_session_factory() as session:
        # Arrange interview
        job = Job(user_id=1, title="QA", description="desc")
        session.add(job)
        await session.flush()
        cand = Candidate(user_id=1, name="Cee", email="c2@example.com", status="pending", token="t2", expires_at=None)
        session.add(cand)
        await session.flush()
        iv = Interview(job_id=job.id, candidate_id=cand.id, status="pending")
        session.add(iv)
        await session.commit()

        # Act: persist identical assistant content twice
        a1 = await persist_assistant_message(session, iv.id, "Question?")
        a2 = await persist_assistant_message(session, iv.id, "Question?")

        # Assert: only one assistant message stored
        msgs = await fetch_messages(session, iv.id)
        assistant_msgs = [m for m in msgs if m.role == MessageRole.ASSISTANT]
        assert len(assistant_msgs) == 1
        assert a1 is not None and a2 is not None
        assert a1.id == a2.id
        assert assistant_msgs[0].sequence_number == 1


@pytest.mark.asyncio
async def test_sequence_increments_user_then_assistant() -> None:
    async with async_session_factory() as session:
        # Arrange interview
        job = Job(user_id=1, title="Mgr", description="desc")
        session.add(job)
        await session.flush()
        cand = Candidate(user_id=1, name="Cee3", email="c3@example.com", status="pending", token="t3", expires_at=None)
        session.add(cand)
        await session.flush()
        iv = Interview(job_id=job.id, candidate_id=cand.id, status="pending")
        session.add(iv)
        await session.commit()

        # Act
        u = await persist_user_message(session, iv.id, "one")
        a = await persist_assistant_message(session, iv.id, "two")

        # Assert sequence ordering
        assert u is not None and a is not None
        assert u.sequence_number == 1
        assert a.sequence_number == 2


def test_realtime_stream_persists_user_and_assistant(monkeypatch: pytest.MonkeyPatch) -> None:
    # Patch httpx.AsyncClient to yield a short token stream and DONE
    class _FakeResp:
        status_code = 200

        async def aiter_lines(self):  # type: ignore[override]
            yield "data: {\"choices\":[{\"delta\":{\"content\":\"Mer\"}}]}"
            yield "data: {\"choices\":[{\"delta\":{\"content\":\"haba\"}}]}"
            yield "data: [DONE]"

    class _StreamCtx:
        async def __aenter__(self):  # type: ignore[override]
            return _FakeResp()

        async def __aexit__(self, exc_type, exc, tb):  # type: ignore[override]
            return False

    class _FakeAsyncClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def __aenter__(self):  # type: ignore[override]
            return self

        async def __aexit__(self, exc_type, exc, tb):  # type: ignore[override]
            return False

        def stream(self, *args: Any, **kwargs: Any):  # type: ignore[override]
            return _StreamCtx()

    import httpx  # type: ignore
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient, raising=True)

    # Prepare interview
    tc = TestClient(app)
    # Create minimal DB entities via async session
    async def _setup() -> int:
        async with async_session_factory() as session:
            job = Job(user_id=1, title="Role", description="desc")
            session.add(job)
            await session.flush()
            cand = Candidate(user_id=1, name="Name", email="name@example.com", status="pending", token="tok", expires_at=None)
            session.add(cand)
            await session.flush()
            iv = Interview(job_id=job.id, candidate_id=cand.id, status="pending")
            session.add(iv)
            await session.commit()
            return iv.id

    int_id = asyncio.get_event_loop().run_until_complete(_setup())

    # Call SSE endpoint with user text
    with tc.stream("GET", "/api/v1/realtime/interview/stream", params={"interview_id": int_id, "text": "hello"}) as r:
        # Drain the stream
        for _ in r.iter_lines():
            pass

    # Verify messages persisted
    async def _verify() -> tuple[int, int, list[str]]:
        async with async_session_factory() as session:
            msgs = await fetch_messages(session, int_id)
            return (
                len([m for m in msgs if m.role == MessageRole.USER]),
                len([m for m in msgs if m.role == MessageRole.ASSISTANT]),
                [m.content for m in msgs],
            )

    u_count, a_count, contents = asyncio.get_event_loop().run_until_complete(_verify())
    assert u_count == 1
    assert a_count == 1
    # Assistant content should be the concatenation: "Merhaba"
    assert any("Merhaba" in c for c in contents)


