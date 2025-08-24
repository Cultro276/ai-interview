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
        asked = sum(1 for t in history if t.get("role") == "assistant")
        if asked == 0:
            try:
                # Prefer overlap between resume keywords and requirement keywords
                initial_q = None
                # If resume exists, start with a short summary for the candidate
                if resume_text:
                    try:
                        from src.services.nlp import summarize_candidate_profile
                        summary = await asyncio.wait_for(summarize_candidate_profile(resume_text, job_desc), timeout=3.0)
                        if summary:
                            # Prepend a friendly summary; still ask for self-intro
                            return NextQuestionResponse(
                                question=(summary + " Kısaca kendinizi ve son deneyiminizi anlatır mısınız?").strip(),
                                done=False,
                            )
                    except Exception:
                        pass
                if req_cfg and isinstance(req_cfg, dict):
                    reqs = (req_cfg.get("requirements") or [])
                    if resume_text:
                        cv_kws = set(k.lower() for k in extract_keywords(resume_text))
                        best = None
                        best_overlap = -1
                        for r in reqs:
                            kws = [str(k).lower() for k in (r.get("keywords") or []) if k]
                            overlap = sum(1 for k in kws if k in cv_kws)
                            if overlap > best_overlap:
                                best_overlap = overlap
                                best = r
                        if best and best.get("label"):
                            label = str(best.get("label")).strip()
                            initial_q = f"Özgeçmişinizi inceledim. {label} alanındaki deneyimlerinizden kısaca bahseder misiniz?"
                if not initial_q:
                    if resume_text:
                        initial_q = "Özgeçmişinizi inceledim. Kendinizi ve son iş deneyiminizi kısaca anlatır mısınız?"
                    else:
                        initial_q = "Kendinizi ve son iş deneyiminizi kısaca anlatır mısınız?"
                return NextQuestionResponse(question=initial_q, done=False)
            except Exception:
                # Fall through to normal flow
                pass

        # Blend: take rule-based suggestion as a hint, but let LLM drive final when available
        rb = None
        # Prefer LLM chain (Gemini -> OpenAI); if they fail, craft a human-like heuristic follow-up
        try:
            combined_ctx = ("Job Description:\n" + (job_desc or "")).strip()
            if resume_text:
                combined_ctx += ("\n\nCandidate Resume (summary text):\n" + resume_text[:4000])
            # Fixed max questions; job-level manual dialog settings removed
            max_q = 7
            # Give LLM a bit more time to avoid falling back to canned rules
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
                    from src.services.dialog import extract_keywords
                    kws = extract_keywords(last_user_text) if last_user_text else []
                    if kws:
                        key = kws[0]
                        q = f"{key} ile ilgili somut bir örnek ve ölçülebilir sonucunuzu paylaşır mısınız?"
                    else:
                        q = "Bu deneyiminizde tam olarak nasıl bir rol üstlendiniz ve sonuç ne oldu?"
                result = {"question": q, "done": False}
            except Exception:
                result = {"question": "Kısa bir örnekle katkınızı ve sonucu anlatır mısınız?", "done": False}

        # Optional LLM-based polish layer for more human-like tone
        if result and result.get("question"):
            try:
                polished = await asyncio.wait_for(polish_question(result["question"]) , timeout=1.0)  # type: ignore[index]
                if polished:
                    result["question"] = polished
            except Exception:
                pass
    except Exception as e:
        collector.record_error()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    return NextQuestionResponse(question=result.get("question"), done=result.get("done", False)) 