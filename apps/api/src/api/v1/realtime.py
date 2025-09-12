from fastapi import APIRouter, Depends, HTTPException, Query, status
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


router = APIRouter(prefix="/realtime", tags=["realtime"])


class EphemeralRequest(BaseModel):
    model: str | None = None  # e.g. "gpt-4o-realtime-preview-2024-12-17"
    voice: str | None = None  # e.g. "verse"
    interview_id: int | None = None


@router.post("/ephemeral")
async def create_ephemeral_token(body: EphemeralRequest, session: AsyncSession = Depends(get_session)):
    if not settings.openai_api_key:
        raise HTTPException(status_code=400, detail="OPENAI_API_KEY is not configured")

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
        job_title = None
        company_name = None
        if interview:
            try:
                from src.db.models.job import Job
                job = (
                    await session.execute(select(Job).where(Job.id == interview.job_id))
                ).scalar_one_or_none()
                job_title = getattr(job, "title", None)
                from src.db.models.user import User
                if job:
                    user = (await session.execute(select(User).where(User.id == job.user_id))).scalar_one_or_none()
                    company_name = getattr(user, "company_name", None)
            except Exception:
                pass
        instructions = (
            "You are a professional HR interviewer conducting a natural Turkish voice conversation. "
            "Speak concisely, one question at a time; do not narrate system states. "
            "Be warm and neutral, avoid gendered language, use 'siz'. "
        )
        if company_name:
            instructions += f"Company: {company_name}. "
        if job_title:
            instructions += f"Role: {job_title}. "
        payload["instructions"] = instructions

    timeout = httpx.Timeout(15.0, read=15.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, headers=headers, json=payload)
        if resp.status_code != 200:
            try:
                detail = resp.json()
            except Exception:
                detail = {"error": resp.text}
            raise HTTPException(status_code=resp.status_code, detail=detail)
        return resp.json()


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
    token: str | None = Query(None),
    text: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
):
    # Validate interview and optional candidate token
    interview = (
        await session.execute(select(Interview).where(Interview.id == interview_id))
    ).scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    if token:
        cand = (
            await session.execute(select(Candidate).where(Candidate.id == interview.candidate_id))
        ).scalar_one_or_none()
        if not cand or cand.token != token:
            raise HTTPException(status_code=400, detail="Geçersiz token")

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
        # Persist with fresh sequence number
        last_msg = (
            await session.execute(
                select(ConversationMessage)
                .where(ConversationMessage.interview_id == interview_id)
                .order_by(ConversationMessage.sequence_number.desc())
            )
        ).scalars().first()
        next_seq = (last_msg.sequence_number if last_msg else 0) + 1
        session.add(
            ConversationMessage(
                interview_id=interview_id,
                role=DBMessageRole.USER,
                content=user_text,
                sequence_number=next_seq,
            )
        )
        try:
            await session.commit()
        except Exception:
            try:
                await session.rollback()
            except Exception:
                pass
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
        body = {
            "model": model,
            "messages": [
                {"role": h["role"], "content": h["content"]} for h in history
            ],
            "stream": True,
            "temperature": 0.7,
        }
        accumulated = []
        # Send a ready event
        yield _sse_format("ready", {"ts": started})
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
                                    yield _sse_format("delta", {"token": delta})
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
            # Persist assistant message
            last_msg2 = (
                await session.execute(
                    select(ConversationMessage)
                    .where(ConversationMessage.interview_id == interview_id)
                    .order_by(ConversationMessage.sequence_number.desc())
                )
            ).scalars().first()
            next_seq2 = (last_msg2.sequence_number if last_msg2 else 0) + 1
            session.add(
                ConversationMessage(
                    interview_id=interview_id,
                    role=DBMessageRole.ASSISTANT,
                    content=full_text,
                    sequence_number=next_seq2,
                )
            )
            try:
                await session.commit()
            except Exception:
                try:
                    await session.rollback()
                except Exception:
                    pass
        yield _sse_format("done", {"length": len(full_text)})

    return StreamingResponse(event_gen(), media_type="text/event-stream")


