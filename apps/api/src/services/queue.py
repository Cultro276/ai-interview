from __future__ import annotations

import asyncio
import json
from typing import Optional

import boto3  # type: ignore
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.s3 import generate_presigned_get_url
from src.db.models.interview import Interview
from src.db.models.conversation import ConversationMessage
from src.db.models.candidate import Candidate
from src.db.session import async_session_factory
from src.services.stt import transcribe_audio_batch
from src.services.analysis import (
    generate_llm_full_analysis,
    merge_enrichment_into_analysis,
    enrich_with_job_and_hr,
)
from src.services.nlp import extract_soft_skills


def _to_key(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    if url.startswith("s3://"):
        return url.split("/", 3)[-1]
    try:
        from urllib.parse import urlparse
        return urlparse(url).path.lstrip("/")
    except Exception:
        return None


async def _maybe_complete_interview(session: AsyncSession, interview: Interview) -> None:
    if interview.status == "completed":
        return
    has_media = bool(interview.audio_url or interview.video_url)
    has_transcript = bool((interview.transcript_text or "").strip())
    if has_media and has_transcript:
        from datetime import datetime, timezone
        interview.status = "completed"
        interview.completed_at = datetime.now(timezone.utc)
        # Mark candidate token used_at
        cand = (
            await session.execute(select(Candidate).where(Candidate.id == interview.candidate_id))
        ).scalar_one_or_none()
        if cand and not getattr(cand, "used_at", None):
            cand.used_at = interview.completed_at  # type: ignore[attr-defined]
        await session.commit()


async def process_interview(interview_id: int) -> None:
    """Main processing pipeline: transcribe (if needed) + analysis + enrichment.

    Safe to call multiple times (idempotent-ish)."""
    async with async_session_factory() as session:
        interview = (
            await session.execute(select(Interview).where(Interview.id == interview_id))
        ).scalar_one_or_none()
        if not interview:
            return

        # Transcribe if missing and audio exists
        needs_transcript = not bool((interview.transcript_text or "").strip())
        audio_key = _to_key(interview.audio_url)
        if needs_transcript and audio_key:
            presigned_get = generate_presigned_get_url(audio_key, expires=600)
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    resp = await client.get(presigned_get)
                    resp.raise_for_status()
                    text, provider = await transcribe_audio_batch(
                        resp.content, resp.headers.get("Content-Type") or "audio/webm"
                    )
                    if text:
                        interview.transcript_text = text
                        interview.transcript_provider = provider or "unknown"
                        await session.commit()
                        await session.refresh(interview)
                        await _maybe_complete_interview(session, interview)
            except Exception:
                # Leave to retry if using queue
                pass

        # Run LLM analysis baseline
        try:
            await generate_llm_full_analysis(session, interview.id)
        except Exception:
            pass

        # Enrichment via LLM (best-effort)
        try:
            job_desc = None
            # Lazy load job description
            from src.db.models.job import Job

            job = (
                await session.execute(select(Job).where(Job.id == interview.job_id))
            ).scalar_one_or_none()
            job_desc = getattr(job, "description", None) if job else None

            text_source = interview.transcript_text or ""
            if text_source.strip():
                soft = await extract_soft_skills(text_source, job_desc)
                enrichment = {
                    "soft_skills": soft.get("soft_skills"),
                    "llm_summary": soft.get("summary"),
                }
                await merge_enrichment_into_analysis(session, interview.id, enrichment)
        except Exception:
            pass

        # Additional enrichment: HR criteria and job-fit summary
        try:
            await enrich_with_job_and_hr(session, interview.id)
        except Exception:
            pass


def enqueue_process_interview(interview_id: int) -> None:
    """Enqueue processing via SQS when configured; otherwise fallback to in-process task."""
    queue_url = settings.sqs_queue_url
    if queue_url and settings.aws_access_key_id and settings.aws_secret_access_key:
        try:
            client = boto3.client(
                "sqs",
                region_name=settings.aws_region,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
            )
            client.send_message(QueueUrl=queue_url, MessageBody=json.dumps({"interview_id": interview_id}))
            return
        except Exception:
            # Fallback to local task
            pass
    # Local background task
    try:
        asyncio.create_task(process_interview(interview_id))
    except Exception:
        # Fallback: run in a background thread with its own event loop
        try:
            import threading
            threading.Thread(
                target=lambda: asyncio.run(process_interview(interview_id)),
                daemon=True,
            ).start()
        except Exception:
            pass


def run_sqs_worker(poll_interval_seconds: float = 2.0) -> None:
    """Blocking SQS worker loop for consuming interview processing jobs.

    Usage: call in a dedicated container/process.
    """
    queue_url = settings.sqs_queue_url
    if not (queue_url and settings.aws_access_key_id and settings.aws_secret_access_key):
        import logging, time
        logging.getLogger(__name__).warning("[worker] SQS not configured; idling")
        # Idle loop to avoid container crash/restart storms in local dev
        while True:
            time.sleep(3600)
    client = boto3.client(
        "sqs",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )
    import time
    while True:
        try:
            resp = client.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=5,
                WaitTimeSeconds=10,
                VisibilityTimeout=60,
            )
            messages = resp.get("Messages", [])
            if not messages:
                time.sleep(poll_interval_seconds)
                continue
            for m in messages:
                try:
                    body_raw = m.get("Body")
                    body = json.loads(body_raw) if isinstance(body_raw, str) else {}
                    interview_id_val = body.get("interview_id")
                    if interview_id_val is None:
                        raise ValueError("missing interview_id")
                    interview_id = int(interview_id_val)
                    # run async processor in a fresh loop per message
                    asyncio.run(process_interview(interview_id))
                    client.delete_message(QueueUrl=queue_url, ReceiptHandle=m["ReceiptHandle"])
                except Exception:
                    # leave message for retry via visibility timeout
                    pass
        except Exception:
            time.sleep(5.0)


