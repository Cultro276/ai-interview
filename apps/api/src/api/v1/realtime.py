from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import asyncio
import httpx
import json
import time

from src.core.config import settings
from src.db.session import get_session
from src.db.models.interview import Interview
from src.db.models.candidate import Candidate
from src.db.models.conversation import ConversationMessage, MessageRole as DBMessageRole
from src.services.persistence import persist_user_message, persist_assistant_message
from src.services.realtime_service import (
    build_realtime_instructions,
    build_sse_system_and_messages,
)
from src.services.ephemeral_store import store as eph_store
from src.services.fanout import publish_event, subscribe_events, _channel_for_interview


router = APIRouter(prefix="/realtime", tags=["realtime"])


class EphemeralRequest(BaseModel):
    model: str | None = None  # e.g. "gpt-4o-realtime-preview-2024-12-17"
    voice: str | None = None  # e.g. "verse"
    interview_id: int | None = None
    token: str | None = None  # candidate token to authorize realtime session
    admin_secret: str | None = None  # optional admin override


@router.post("/ephemeral")
async def create_ephemeral_token(body: EphemeralRequest, session: AsyncSession = Depends(get_session)):
    if not settings.openai_api_key:
        raise HTTPException(status_code=400, detail="OPENAI_API_KEY is not configured")

    # Authorization: require either a valid candidate token tied to interview_id or a valid admin secret
    if body.admin_secret and body.admin_secret == settings.internal_admin_secret:
        pass
    else:
        if not body.interview_id or not (body.token or "").strip():
            raise HTTPException(status_code=401, detail="Authorization required")
        # Validate interview and candidate token
        interview = (
            await session.execute(select(Interview).where(Interview.id == body.interview_id))
        ).scalar_one_or_none()
        if not interview:
            raise HTTPException(status_code=404, detail="Interview not found")
        cand = (
            await session.execute(select(Candidate).where(Candidate.id == interview.candidate_id))
        ).scalar_one_or_none()
        if not cand or cand.token != (body.token or "").strip():
            raise HTTPException(status_code=400, detail="Geçersiz token")
        # Expiry check (best-effort)
        try:
            from datetime import datetime, timezone
            cand_expires = getattr(cand, "expires_at", None)
            if cand_expires is not None and cand_expires <= datetime.now(timezone.utc):
                raise HTTPException(status_code=400, detail="Token süresi dolmuş")
        except Exception:
            pass

    model = (body.model or "gpt-4o-realtime-preview")
    voice = (body.voice or "verse")
    url = "https://api.openai.com/v1/realtime/sessions"
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
        "OpenAI-Beta": "realtime=v1",
    }
    payload: dict = {
        "model": model,
        "voice": voice,
    }

    # Add interview-specific brief instructions to steer tone and context
    if body.interview_id:
        interview = (
            await session.execute(select(Interview).where(Interview.id == body.interview_id))
        ).scalar_one_or_none()
        if interview:
            try:
                payload["instructions"] = await build_realtime_instructions(session, interview)  # type: ignore[arg-type]
            except Exception:
                pass

    timeout = httpx.Timeout(15.0, read=15.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, headers=headers, json=payload)
        if resp.status_code != 200:
            try:
                detail = resp.json()
            except Exception:
                detail = {"error": resp.text}
            raise HTTPException(status_code=resp.status_code, detail=detail)
        data = resp.json()
        try:
            eph_id = eph_store.new_id()
            await eph_store.put(
                f"eph:{eph_id}",
                {"openai": data, "model": model, "voice": voice, "interview_id": body.interview_id},
                ttl_seconds=120,
            )
            data["_ephemeral_id"] = eph_id
        except Exception:
            pass
        return data


def _sse_format(event: str | None, data: dict | str) -> bytes:
    buf = []
    if event:
        buf.append(f"event: {event}")
    if isinstance(data, (dict, list)):
        buf.append("data: " + json.dumps(data, ensure_ascii=False))
    else:
        for line in str(data).splitlines() or [""]:
            buf.append("data: " + line)
    buf.append("")  # end of message
    return ("\n".join(buf) + "\n").encode("utf-8")


@router.get("/interview/stream")
async def stream_next_question(
    interview_id: int = Query(...),
    token: str = Query(...),
    text: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
):
    # Validate interview and optional candidate token
    interview = (
        await session.execute(select(Interview).where(Interview.id == interview_id))
    ).scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    # Require candidate token and validate expiry
    cand = (
        await session.execute(select(Candidate).where(Candidate.id == interview.candidate_id))
    ).scalar_one_or_none()
    if not cand or cand.token != token:
        raise HTTPException(status_code=400, detail="Geçersiz token")
    try:
        from datetime import datetime, timezone
        cand_expires = getattr(cand, "expires_at", None)
        if cand_expires is not None and cand_expires <= datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="Token süresi dolmuş")
    except Exception:
        pass

    # Build history from DB
    msgs = (
        await session.execute(
            select(ConversationMessage)
            .where(ConversationMessage.interview_id == interview_id)
            .order_by(ConversationMessage.sequence_number)
        )
    ).scalars().all()
    history: list[dict[str, str]] = []
    for m in msgs:
        role = "assistant" if m.role.value == "assistant" else ("user" if m.role.value == "user" else "system")
        content = m.content or ""
        if content.strip():
            history.append({"role": role, "content": content})

    # Optionally persist incoming user text before streaming
    user_text = (text or "").strip()
    if user_text:
        try:
            saved = await persist_user_message(session, interview_id, user_text)
        except Exception:
            saved = None
        history.append({"role": "user", "content": user_text})

    if not settings.openai_api_key:
        raise HTTPException(status_code=400, detail="OPENAI_API_KEY is not configured")

    async def event_gen():
        started = time.time()
        first_token_sent = False
        model = "gpt-4o-mini"
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        url = "https://api.openai.com/v1/chat/completions"
        # Build a strong system persona and role guidance for SSE chat
        system_content, messages = await build_sse_system_and_messages(session, interview, history)

        body = {
            "model": model,
            "messages": messages,
            "stream": True,
            "temperature": 0.7,
        }
        accumulated = []
        # Send a ready event and publish to fanout
        ready_payload = {"ts": started}
        yield _sse_format("ready", ready_payload)
        try:
            await publish_event(_channel_for_interview(interview_id), "ready", ready_payload)
        except Exception:
            pass
        timeout = httpx.Timeout(30.0, read=60.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                async with client.stream("POST", url, headers=headers, json=body) as resp:
                    if resp.status_code != 200:
                        err_text = await resp.aread()
                        yield _sse_format("error", {"status": resp.status_code, "detail": err_text.decode("utf-8", "ignore")})
                        return
                    async for line in resp.aiter_lines():
                        if not line:
                            continue
                        if line.startswith("data: "):
                            data = line[len("data: ") :].strip()
                            if data == "[DONE]":
                                break
                            try:
                                obj = json.loads(data)
                                delta = (
                                    obj.get("choices", [{}])[0]
                                    .get("delta", {})
                                    .get("content")
                                )
                                if delta:
                                    accumulated.append(delta)
                                    chunk = {"token": delta}
                                    yield _sse_format("delta", chunk)
                                    try:
                                        await publish_event(_channel_for_interview(interview_id), "delta", chunk)
                                    except Exception:
                                        pass
                                    if not first_token_sent:
                                        first_token_sent = True
                                        try:
                                            from src.core.metrics import collector
                                            collector.record_histogram("sse_first_token_latency_ms", (time.time() - started) * 1000.0)
                                        except Exception:
                                            pass
                            except Exception:
                                # pass through non-json heartbeat lines safely
                                continue
            except Exception as e:
                yield _sse_format("error", {"detail": str(e)})

        full_text = ("".join(accumulated)).strip()
        if full_text:
            # Persist assistant message with idempotency
            try:
                await persist_assistant_message(session, interview_id, full_text)
            except Exception:
                pass
        done_payload = {"length": len(full_text)}
        yield _sse_format("done", done_payload)
        try:
            await publish_event(_channel_for_interview(interview_id), "done", done_payload)
        except Exception:
            pass

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@router.get("/interview/subscribe")
async def subscribe_stream(
    interview_id: int = Query(...),
    token: str | None = Query(None),
    admin_secret: str | None = Query(None),
):
    # Authorization: candidate token matches interview, or admin secret
    authorized = False
    if admin_secret and admin_secret == settings.internal_admin_secret:
        authorized = True
    else:
        if token:
            # Lazy import of DB deps to avoid unnecessary session in simple fanout
            try:
                from sqlalchemy import select as _select
                from src.db.session import async_session_factory as _session_factory  # type: ignore
                from src.db.models.interview import Interview as _I  # type: ignore
                from src.db.models.candidate import Candidate as _C  # type: ignore
                async def _validate() -> bool:
                    async with _session_factory() as s:  # type: ignore
                        iv = (await s.execute(_select(_I).where(_I.id == interview_id))).scalar_one_or_none()
                        if not iv:
                            return False
                        cd = (await s.execute(_select(_C).where(_C.id == iv.candidate_id))).scalar_one_or_none()
                        if not cd or cd.token != token:
                            return False
                        try:
                            from datetime import datetime, timezone
                            cd_expires = getattr(cd, "expires_at", None)
                            if cd_expires is not None and cd_expires <= datetime.now(timezone.utc):
                                return False
                        except Exception:
                            pass
                        return True
                authorized = await _validate()
            except Exception:
                authorized = False
    if not authorized:
        raise HTTPException(status_code=401, detail="Authorization required")

    channel = _channel_for_interview(interview_id)

    async def sub_gen():
        try:
            async for evt in subscribe_events(channel):
                event = str(evt.get("event") or "message")
                data = evt.get("data") or {}
                yield _sse_format(event, data)
        except Exception as e:
            yield _sse_format("error", {"detail": str(e)})

    return StreamingResponse(sub_gen(), media_type="text/event-stream")


