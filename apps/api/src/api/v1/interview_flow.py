from typing import List

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.db.session import get_session
from src.db.models.interview import Interview
from src.db.models.job import Job
from src.db.models.candidate import Candidate
from src.db.models.candidate_profile import CandidateProfile
from src.db.models.conversation import ConversationMessage, MessageRole as DBMessageRole
from src.services.stt import transcribe_audio_batch
import base64

from src.core.gemini import generate_question, generate_question_robust, polish_question
from src.services.dialog import extract_keywords
from src.core.metrics import collector
import asyncio

router = APIRouter(prefix="/interview", tags=["interview"])


class Turn(BaseModel):
    role: str  # 'user' or 'assistant'
    text: str


class NextQuestionRequest(BaseModel):
    history: List[Turn]
    interview_id: int
    # Optional behavior signals from client/runtime
    signals: List[str] | None = None  # e.g., ["tab_hidden","focus_lost","very_short_answer","long_silence"]


class NextQuestionResponse(BaseModel):
    question: str | None = None
    done: bool


@router.post("/next-question", response_model=NextQuestionResponse)
async def next_question(req: NextQuestionRequest, session: AsyncSession = Depends(get_session)):
    # Generate next question (rule-based first; LLM fallback and polish)
    try:
        job_desc = ""
        req_cfg = None
        resume_text = ""
        interview = (
            await session.execute(select(Interview).where(Interview.id == req.interview_id))
        ).scalar_one_or_none()
        if interview:
            job = (
                await session.execute(select(Job).where(Job.id == interview.job_id))
            ).scalar_one_or_none()
            if job:
                if job.description:
                    job_desc = job.description
                try:
                    req_cfg = job.requirements_config  # type: ignore[attr-defined]
                except Exception:
                    req_cfg = None
            # Candidate resume text (if any)
            try:
                cand = (
                    await session.execute(select(Candidate).where(Candidate.id == interview.candidate_id))
                ).scalar_one_or_none()
                if cand:
                    profile = (
                        await session.execute(select(CandidateProfile).where(CandidateProfile.candidate_id == cand.id))
                    ).scalar_one_or_none()
                    if profile and profile.resume_text:
                        resume_text = profile.resume_text
            except Exception:
                resume_text = ""

        history = [t.dict() for t in req.history]
        # No requirements-config extraction; rely on LLM with job description and resume only

        # If this is the very first assistant turn, craft a CV+job tailored opening question
        # but NEVER disclose internal context or summaries to the candidate.
        asked = sum(1 for t in history if t.get("role") == "assistant")
        if asked == 0:
            try:
                # Build a private context only for LLM guidance
                private_ctx = (job_desc or "")
                if resume_text:
                    private_ctx += ("\n\nCV Keywords: " + ", ".join(extract_keywords(resume_text)))
                # Ask LLM for a concise opening question; we will sanitize phrasing
                result0 = await asyncio.wait_for(
                    generate_question_robust([], private_ctx, max_questions=7), timeout=8.0
                )
                q0_raw = result0.get("question")
                q0 = (q0_raw if isinstance(q0_raw, str) else "").strip()
                # Sanitize: remove any disclosure patterns
                leak_phrases = [
                    "özgeçmişinizi inceledim", "cv’nizi inceledim", "cvnizi inceledim",
                    "cv’nize göre", "cv'ye göre", "özgeçmişe göre", "ilanı okudum", "iş tanımına göre",
                ]
                low = q0.lower()
                if any(p in low for p in leak_phrases) or not q0:
                    q0 = "Kendinizi ve son iş deneyiminizi kısaca anlatır mısınız?"
                return NextQuestionResponse(question=q0, done=False)
            except Exception:
                return NextQuestionResponse(
                    question="Kendinizi ve son iş deneyiminizi kısaca anlatır mısınız?",
                    done=False,
                )

        # Blend: take dialog plan and behavior signals as hints, but let LLM drive final
        rb = None
        # Prefer LLM chain (Gemini -> OpenAI); if they fail, craft a human-like heuristic follow-up
        try:
            combined_ctx = ("Job Description:\n" + (job_desc or "")).strip()
            # Include precomputed dialog plan if exists
            # Load dialog_plan from analysis blob if present
            try:
                from sqlalchemy import select as _select
                from src.db.models.conversation import InterviewAnalysis
                ia = (
                    await session.execute(_select(InterviewAnalysis).where(InterviewAnalysis.interview_id == req.interview_id))
                ).scalar_one_or_none()
                if ia and ia.technical_assessment:
                    import json as _json
                    blob = _json.loads(ia.technical_assessment)
                    dp = blob.get("dialog_plan")
                    if dp:
                        topics = dp.get("topics") or []
                        targeted = dp.get("targeted_questions") or []
                        seed = dp.get("first_question_seed") or ""
                        if topics:
                            combined_ctx += "\n\nPlanned Job Topics: " + ", ".join(topics[:6])
                        if targeted:
                            combined_ctx += "\n\nTargeted Questions (from resume):\n- " + "\n- ".join(targeted[:3])
                        if seed and asked == 0:
                            # Strongly bias LLM to use seed for the first question
                            combined_ctx += "\n\nFirstQuestionHint: " + seed
            except Exception:
                pass
            if resume_text:
                try:
                    # Use only internal keywords to guide LLM; avoid exposing raw CV text
                    kws = extract_keywords(resume_text)
                    if kws:
                        combined_ctx += ("\n\nInternal Resume Keywords: " + ", ".join(kws[:30]))
                except Exception:
                    pass
            # Behavior signals to steer tone/speed/adaptation
            try:
                sigs = (req.signals or [])
                if sigs:
                    combined_ctx += ("\n\nBehavior Signals: " + ", ".join(set(sigs)))
            except Exception:
                pass
            # Fixed max questions; job-level manual dialog settings removed
            max_q = 7
            # Steer model when the last user message is empty/too short (likely STT artifact)
            try:
                last_user_text = next((t.get("text", "") for t in reversed(history) if t.get("role") == "user"), "")
                if (not last_user_text) or len(last_user_text.strip()) < 2 or last_user_text.strip() == "...":
                    combined_ctx += "\n\nCandidateHint: The last message seems short/possibly STT; re-ask the SAME question slowly in one sentence without frustration."
            except Exception:
                pass
            # Give LLM a bit more time to avoid falling back to canned rules
            # Enforce gender-neutral addressing in instruction context
            combined_ctx += "\n\nImportant: Address the candidate in a gender-neutral manner in Turkish (use 'siz' and avoid gendered titles)."
            result = await asyncio.wait_for(
                generate_question_robust(history, combined_ctx, max_questions=max_q), timeout=12.0
            )
        except Exception:
            # Heuristic HR-style follow-up using last user text
            try:
                last_user_text = next((t.get("text", "") for t in reversed(history) if t.get("role") == "user"), "")
                # Prefer targeting a concrete resume line when available
                q = None
                if resume_text:
                    try:
                        from src.services.nlp import extract_resume_spotlights, make_targeted_question_from_spotlight
                        spots = extract_resume_spotlights(resume_text)
                        if spots:
                            q = make_targeted_question_from_spotlight(spots[0])
                    except Exception:
                        q = None
                if not q:
                    from src.services.dialog import extract_keywords as _extract_keywords
                    kws = _extract_keywords(last_user_text) if last_user_text else []
                    if kws:
                        key = kws[0]
                        q = f"{key} ile ilgili somut bir örnek ve ölçülebilir sonucunuzu paylaşır mısınız?"
                    else:
                        q = "Bu deneyiminizde tam olarak nasıl bir rol üstlendiniz ve sonuç ne oldu?"
                result = {"question": q, "done": False}
            except Exception:
                result = {"question": "Kısa bir örnekle katkınızı ve sonucu anlatır mısınız?", "done": False}

        # Optional LLM-based polish layer for more human-like tone + sanitize leaks
        GENERIC_OPENING = "Kendinizi ve son iş deneyiminizi kısaca anlatır mısınız?"
        def _sanitize(q: str) -> str:
            import re
            s = (q or "").strip()
            low = s.lower()
            leak_words = ["cv", "özgeçmiş", "ilan", "iş tanımı", "linkedin", "github", "http://", "https://", "www.", "@"]
            if any(w in low for w in leak_words):
                return ""
            # crude phone detection or long digit runs
            if re.search(r"[+]?\d[\d\s().-]{7,}", s):
                return ""
            # avoid addressing by candidate name if accidentally produced
            for nm in ["kayra", "yıldız", "yildiz"]:
                if nm in low:
                    return ""
            return s

        q_candidate = result.get("question")
        if isinstance(q_candidate, str) and q_candidate:
            try:
                polished = await asyncio.wait_for(polish_question(q_candidate) , timeout=1.0)
                s = _sanitize(polished or q_candidate)
                if not s:
                    # Fallback neutral follow-up rather than reopening
                    last_assistant = next((t.get("text", "") for t in reversed(history) if t.get("role") == "assistant"), "")
                    if last_assistant:
                        result["question"] = "Biraz daha somutlaştırabilir misiniz? Kısa bir örnek ve elde ettiğiniz sonucu paylaşır mısınız?"
                    else:
                        result["question"] = GENERIC_OPENING
                else:
                    # Prevent regression to generic opening after first turn
                    if asked >= 1 and s.strip() == GENERIC_OPENING:
                        result["question"] = "Son rolünüzde üstlendiğiniz belirli bir görevi ve ölçülebilir sonucu kısaca paylaşır mısınız?"
                    else:
                        result["question"] = s
            except Exception:
                # As a last resort, ensure we don't regress to opening after first turn
                if asked >= 1 and isinstance(q_candidate, str) and q_candidate.strip() == GENERIC_OPENING:
                    result["question"] = "Son rolünüzde üstlendiğiniz belirli bir görevi ve ölçülebilir sonucu kısaca paylaşır mısınız?"
    except Exception as e:
        collector.record_error()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    q_any = result.get("question")
    question_out: str | None = q_any if isinstance(q_any, str) else None
    d_any = result.get("done")
    done_out: bool = True if isinstance(d_any, bool) and d_any else False
    return NextQuestionResponse(question=question_out, done=done_out) 


# --- STT -> Analysis -> Next Question pipeline ---


class NextTurnIn(BaseModel):
    interview_id: int
    token: str | None = None
    text: str | None = None
    audio_b64: str | None = None  # optional base64-encoded audio; if provided, server runs STT
    signals: List[str] | None = None


@router.post("/next-turn", response_model=NextQuestionResponse)
async def next_turn(body: NextTurnIn, session: AsyncSession = Depends(get_session)):
    # 1) Validate interview and (optional) candidate token
    interview = (
        await session.execute(select(Interview).where(Interview.id == body.interview_id))
    ).scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    if body.token:
        # Verify token belongs to the same candidate and is not expired
        cand = (
            await session.execute(select(Candidate).where(Candidate.id == interview.candidate_id))
        ).scalar_one_or_none()
        if not cand or cand.token != body.token:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")
        try:
            from datetime import datetime, timezone
            if cand.expires_at and cand.expires_at <= datetime.now(timezone.utc):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Expired token")
        except Exception:
            pass

    # 2) STT if needed
    text = (body.text or "").strip()
    if not text and body.audio_b64:
        try:
            audio_bytes = base64.b64decode(body.audio_b64)
            text, _prov = await transcribe_audio_batch(audio_bytes, "audio/webm")
            text = (text or "").strip()
        except Exception:
            text = ""

    # 3) Persist user message (skip if empty)
    last = (
        await session.execute(
            select(ConversationMessage)
            .where(ConversationMessage.interview_id == body.interview_id)
            .order_by(ConversationMessage.sequence_number.desc())
        )
    ).scalars().first()
    next_seq = (last.sequence_number if last else 0) + 1
    if text:
        msg = ConversationMessage(
            interview_id=body.interview_id,
            role=DBMessageRole.USER,
            content=text,
            sequence_number=next_seq,
        )
        session.add(msg)
        await session.commit()
    else:
        # Reserve the sequence but do not persist empty content
        pass

    # 4) Build history from DB to drive next question
    msgs = (
        await session.execute(
            select(ConversationMessage)
            .where(ConversationMessage.interview_id == body.interview_id)
            .order_by(ConversationMessage.sequence_number)
        )
    ).scalars().all()
    history: List[dict] = [
        {"role": ("assistant" if m.role.value == "assistant" else ("user" if m.role.value == "user" else "system")), "text": m.content}
        for m in msgs
        if (m.content or "").strip()
    ]
    # Include the current text if we skipped persisting (empty earlier)
    if text and (not any(t for t in history if t.get("role") == "user" and t.get("text") == text)):
        history.append({"role": "user", "text": text})

    # 5) Delegate to next_question logic
    req = NextQuestionRequest(
        history=[Turn(role=t["role"], text=t["text"]) for t in history],
        interview_id=body.interview_id,
        signals=body.signals,
    )
    result = await next_question(req, session)  # returns NextQuestionResponse

    # 6) Persist assistant question if any
    if result.question:
        last2 = (
            await session.execute(
                select(ConversationMessage)
                .where(ConversationMessage.interview_id == body.interview_id)
                .order_by(ConversationMessage.sequence_number.desc())
            )
        ).scalars().first()
        next_seq2 = (last2.sequence_number if last2 else 0) + 1
        session.add(
            ConversationMessage(
                interview_id=body.interview_id,
                role=DBMessageRole.ASSISTANT,
                content=result.question,
                sequence_number=next_seq2,
            )
        )
        await session.commit()

    return result


