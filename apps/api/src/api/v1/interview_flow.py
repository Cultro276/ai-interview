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
    # Optional live insights for recruiter-side UX (not shown to candidate)
    live: dict | None = None


@router.post("/next-question", response_model=NextQuestionResponse)
async def next_question(req: NextQuestionRequest, session: AsyncSession = Depends(get_session)):
    # Generate next question (rule-based first; LLM fallback and polish)
    try:
        import re as _re
        job_desc = ""
        req_cfg = None
        resume_text = ""
        extra_list = []
        job = None
        cand = None
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
                # Parse extra recruiter-provided questions (one per line)
                extra_list = []
                try:
                    extra_raw = getattr(job, "extra_questions", None)
                    if isinstance(extra_raw, str) and extra_raw.strip():
                        extra_list = [q.strip() for q in extra_raw.splitlines() if q.strip()]
                except Exception:
                    pass
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
                    
                    # First try to get resume_text from profile
                    if profile and profile.resume_text:
                        resume_text = profile.resume_text
                    # If no resume_text but resume_url exists, try to parse on-demand
                    elif cand.resume_url and cand.resume_url.strip():
                        try:
                            from src.core.s3 import generate_presigned_get_url
                            from src.services.nlp import parse_resume_bytes
                            from urllib.parse import urlparse
                            import httpx
                            
                            def _to_key(url: str) -> str | None:
                                if url.startswith("s3://"):
                                    p = urlparse(url)
                                    return p.path.lstrip("/")
                                try:
                                    p = urlparse(url)
                                    return p.path.lstrip("/")
                                except Exception:
                                    return None
                            
                            key = _to_key(cand.resume_url)
                            if key:
                                presigned = generate_presigned_get_url(key, expires=180)
                                async with httpx.AsyncClient(timeout=20.0) as client:
                                    resp = await client.get(presigned)
                                    if resp.status_code == 200:
                                        parsed_text = parse_resume_bytes(resp.content, resp.headers.get("Content-Type"), cand.resume_url)
                                        if parsed_text:
                                            resume_text = parsed_text
                                            # Cache for future use
                                            if not profile:
                                                profile = CandidateProfile(candidate_id=cand.id)
                                                session.add(profile)
                                                await session.flush()
                                            profile.resume_text = parsed_text[:100000]
                                            await session.commit()
                        except Exception:
                            pass
            except Exception:
                resume_text = ""

        history = [t.dict() for t in req.history]
        # Sliding window: keep last 20 turns to control token usage
        if len(history) > 20:
            history = history[-20:]
        # No requirements-config extraction; rely on LLM with job description and resume only

        # If this is the very first assistant turn, craft a CV+job tailored opening question
        # but NEVER disclose internal context or summaries to the candidate.
        asked = sum(1 for t in history if t.get("role") == "assistant")
        if asked == 0:
            try:
                # Build a private context only for LLM guidance
                private_ctx = (job_desc or "")
                
                # Add CV-Job relevance checking
                try:
                    from src.services.cv_job_matcher import generate_cv_aware_context
                    cv_relevance_context = generate_cv_aware_context(resume_text or "", job_desc or "")
                    if cv_relevance_context:
                        private_ctx += "\n\n" + cv_relevance_context
                except Exception:
                    pass
                
                if resume_text:
                    # Provide full resume text to the LLM as hidden context
                    private_ctx += ("\n\nResume (full text):\n" + resume_text)
                
                # Add company context if available
                try:
                    from src.db.models.user import User
                    if job:
                        user = (await session.execute(select(User).where(User.id == job.user_id))).scalar_one_or_none()
                        if user and user.company_name:
                            private_ctx += f"\n\nCompany: {user.company_name}"
                except Exception:
                    pass
                # Include recruiter-provided extra questions without truncation
                try:
                    if extra_list:
                        private_ctx += "\n\nRecruiter Extra Questions (verbatim):\n- " + "\n- ".join(extra_list)
                except Exception:
                    pass
                # Generate job-specific situational questions
                try:
                    from src.core.gemini import generate_job_specific_scenarios
                    job_scenarios = await generate_job_specific_scenarios(job_desc)
                    if job_scenarios:
                        private_ctx += "\n\nJob-Specific Scenarios:\n- " + "\n- ".join(job_scenarios)
                except Exception:
                    pass
                # Debug: log initial context sizes
                try:
                    import logging as _log
                    _log.getLogger(__name__).info(
                        "[CTX FIRST] interview=%s job_len=%s resume_len=%s extra_count=%s",
                        getattr(interview, "id", None), len(job_desc or ""), len(resume_text or ""), len(extra_list or [])
                    )
                except Exception:
                    pass
                # Ask LLM for a concise opening question (allowed to reference resume items)
                result0 = await asyncio.wait_for(
                    generate_question_robust([], private_ctx, max_questions=7), timeout=8.0
                )
                q0_raw = result0.get("question")
                q0 = (q0_raw if isinstance(q0_raw, str) else "").strip()
                # If recruiter provided extra questions, prefer the first one as opener
                try:
                    if (not q0) and extra_list:
                        q0 = extra_list[0]
                except Exception:
                    pass
                if not q0:
                    q0 = "Özgeçmişinizde öne çıkan bir proje/başarıyı STAR çerçevesinde kısaca anlatır mısınız?"
                # Friendly intro with candidate name and job title
                intro = None
                try:
                    _first = None
                    if cand and getattr(cand, "name", None):
                        _first = str(cand.name).strip().split()[0]
                    jt = (job.title if job and getattr(job, "title", None) else None)
                    if _first and jt:
                        intro = f"Merhaba {_first}, ben şirketimizin yapay zekâ insan kaynakları asistanıyım. {jt} pozisyonu için görüşmemize hoş geldiniz."
                    elif _first:
                        intro = f"Merhaba {_first}, ben şirketimizin yapay zekâ insan kaynakları asistanıyım. Görüşmemize hoş geldiniz."
                    elif jt:
                        intro = f"Merhaba, ben şirketimizin yapay zekâ insan kaynakları asistanıyım. {jt} pozisyonu için görüşmemize hoş geldiniz."
                except Exception:
                    intro = None
                # Avoid duplicate greetings by removing common Turkish greetings from AI question
                if intro and q0:
                    # Remove common greeting patterns from the start of AI question
                    q0_clean = q0
                    greeting_patterns = [
                        "merhaba", "merhaba,", "hoş geldiniz", "hoş geldiniz.",
                        "hoşgeldiniz", "hoşgeldiniz.", "selamlar", "selamlar,",
                        "iyi günler", "iyi günler,"
                    ]
                    q0_lower = q0.lower().strip()
                    for pattern in greeting_patterns:
                        if q0_lower.startswith(pattern):
                            # Remove the greeting and clean up whitespace/punctuation
                            q0_clean = q0[len(pattern):].lstrip(" ,.").strip()
                            # Capitalize first letter if needed
                            if q0_clean and q0_clean[0].islower():
                                q0_clean = q0_clean[0].upper() + q0_clean[1:]
                            break
                    final_q0 = f"{intro} {q0_clean}".strip()
                else:
                    final_q0 = intro or q0
                return NextQuestionResponse(question=final_q0, done=False, live=None)
            except Exception:
                return NextQuestionResponse(
                    question="Özgeçmişinizde öne çıkan bir proje/başarıyı STAR çerçevesinde kısaca anlatır mısınız?",
                    done=False,
                    live=None,
                )

        # Blend: take dialog plan and behavior signals as hints, but let LLM drive final
        rb = None
        # Prefer LLM chain (Gemini -> OpenAI); if they fail, craft a human-like heuristic follow-up
        try:
            combined_ctx = ("Job Description:\n" + (job_desc or "")).strip()
            # Include recruiter-provided extra questions in hidden context to bias LLM
            try:
                if extra_list:
                    combined_ctx += "\n\nRecruiter Extra Questions (ask these if not covered):\n- " + "\n- ".join(extra_list[:6])
            except Exception:
                pass
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
                    req_spec = blob.get("requirements_spec") or {"items": []}
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
                    # Add requirements coverage steering if we have job_fit and req_spec
                    try:
                        from src.services.dialog import build_requirements_ctx, pick_next_requirement_target
                        job_fit = blob.get("job_fit") or {}
                        # asked_counts by simple label matching in prior assistant questions
                        asked_counts: dict[str, int] = {}
                        for t in history:
                            if t.get("role") != "assistant":
                                continue
                            txt = (t.get("text") or "").lower()
                            for it in (req_spec.get("items") or [])[:12]:
                                lab = str(it.get("label", "")).lower()
                                if lab and lab in txt:
                                    asked_counts[lab] = asked_counts.get(lab, 0) + 1
                        target = pick_next_requirement_target(req_spec, (job_fit.get("requirements_matrix") or []), asked_counts)
                        combined_ctx += "\n\n" + build_requirements_ctx(req_spec, job_fit, target)
                    except Exception:
                        pass
            except Exception:
                pass
            # After the first assistant turn, avoid re-sending the full resume to reduce cost
            # Behavior signals to steer tone/speed/adaptation
            try:
                sigs = (req.signals or [])
                if sigs:
                    combined_ctx += ("\n\nBehavior Signals: " + ", ".join(set(sigs)))
            except Exception:
                pass
            # Tunable max questions
            from src.core.config import settings as _settings
            max_q = 50
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
            # If there are pending extra questions not yet asked, surface them before LLM
            def _pending_extra() -> str | None:
                try:
                    if not extra_list:
                        return None
                    asked_texts = [t.get("text", "").strip() for t in history if t.get("role") == "assistant"]
                    for q in extra_list:
                        if q and all(q not in (a or "") for a in asked_texts):
                            return q
                except Exception:
                    return None
                return None

            pend = _pending_extra()
            if pend:
                result = {"question": pend, "done": False}
            else:
                result = await asyncio.wait_for(
                    generate_question_robust(history, combined_ctx, max_questions=50), timeout=12.0
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
        def _strip_finished(s: str) -> str:
            try:
                return _re.sub(r"\bFINISHED\b", "", s, flags=_re.IGNORECASE).strip()
            except Exception:
                return (s or "").strip()
        def _is_generic(s: str) -> bool:
            low = (s or "").lower()
            generic_bits = [
                "ne yaparsınız", "ne yapardınız", "nasıl yaklaşırsınız", "senaryo", "varsayalım",
                "rol üstlendiniz", "takım çalışmalarında", "takım projelerinde", "zorlayıcı bir durum",
            ]
            return any(bit in low for bit in generic_bits)
        def _sanitize(q: str) -> str:
            import re
            s = (q or "").strip()
            low = s.lower()
            # Allow referencing resume/job; only filter links and obvious PII
            banned = ["http://", "https://", "www.", "@", "linkedin.com", "github.com"]
            if any(w in low for w in banned):
                return ""
            # crude phone detection or long digit runs
            if re.search(r"[+]?\d[\d\s().-]{7,}", s):
                return ""
            return s

        q_candidate = result.get("question")
        # Sanitize FINISHED from any question text and mark done if nothing remains
        if isinstance(q_candidate, str):
            cleaned = _strip_finished(q_candidate)
            if (not cleaned) and ("finished" in q_candidate.lower()):
                result["question"] = ""
                result["done"] = True
            else:
                result["question"] = cleaned
        # If we still have a question string, optionally polish and de-genericize
        q_candidate = result.get("question")
        if isinstance(q_candidate, str) and q_candidate:
            try:
                polished = await asyncio.wait_for(polish_question(q_candidate) , timeout=1.0)
                s = _sanitize(polished or q_candidate)
                # If polished was filtered out, fallback to neutral follow-up
                if not s:
                    last_assistant = next((t.get("text", "") for t in reversed(history) if t.get("role") == "assistant"), "")
                    if last_assistant:
                        s = "Biraz daha somutlaştırabilir misiniz? Kısa bir örnek ve elde ettiğiniz sonucu paylaşır mısınız?"
                    else:
                        s = GENERIC_OPENING
                # Avoid regression to opening after first turn
                if asked >= 1 and s.strip() == GENERIC_OPENING:
                    s = "Son rolünüzde üstlendiğiniz belirli bir görevi ve ölçülebilir sonucu kısaca paylaşır mısınız?"
                # Avoid overly generic hypotheticals; prefer resume- or answer-anchored
                if _is_generic(s) or "[proje adı]" in s.lower():
                    try:
                        # Prefer resume spotlight if available
                        if resume_text:
                            from src.services.nlp import extract_resume_spotlights, make_targeted_question_from_spotlight, extract_resume_project_titles
                            spots = extract_resume_spotlights(resume_text)
                            if spots:
                                s = make_targeted_question_from_spotlight(spots[0])
                            else:
                                # Try to reference a concrete project title if available (safe to mention)
                                titles = extract_resume_project_titles(resume_text)
                                if titles:
                                    title = titles[0]
                                    s = f"Özgeçmişinizde '{title}' projesinden bahsetmişsiniz. Bu projede hangi sorunu çözdünüz, nasıl bir rol üstlendiniz ve ölçülebilir sonuç ne oldu?"
                        if _is_generic(s):
                            # Fall back to last user keywords
                            from src.services.dialog import extract_keywords as _ek2
                            last_user_text = next((t.get("text", "") for t in reversed(history) if t.get("role") == "user"), "")
                            kws = _ek2(last_user_text) if last_user_text else []
                            if kws:
                                key = kws[0]
                                s = f"Cevabınızda '{key}' dediniz; bunu hangi teknolojilerle nasıl yaptınız ve ölçülebilir sonucu kısaca paylaşır mısınız?"
                    except Exception:
                        pass
                # If there are still recruiter-provided extra questions pending, prefer them
                try:
                    asked_texts2 = [t.get("text", "").strip() for t in history if t.get("role") == "assistant"]
                    remaining = [q for q in (extra_list or []) if q and all(q not in (a or "") for a in asked_texts2)]
                    if remaining:
                        s = remaining[0]
                except Exception:
                    pass
                result["question"] = s
            except Exception:
                if asked >= 1 and isinstance(q_candidate, str) and q_candidate.strip() == GENERIC_OPENING:
                    result["question"] = "Son rolünüzde üstlendiğiniz belirli bir görevi ve ölçülebilir sonucu kısaca paylaşır mısınız?"
    except Exception as e:
        collector.record_error()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    # Check if salary question has been asked and answered (auto-complete logic)
    try:
        asked_count = sum(1 for t in req.history if t.role == "assistant")
        if asked_count >= 5:  # Only check after sufficient questions
            salary_asked = False
            salary_answered = False
            
            # Look for salary-related questions in conversation history
            for i, turn in enumerate(req.history):
                if turn.role == "assistant" and turn.text:
                    question_text = turn.text.lower()
                    if any(keyword in question_text for keyword in ["maaş", "ücret", "salary", "beklenti"]):
                        salary_asked = True
                        # Check if there's a user response after this question
                        if i + 1 < len(req.history) and req.history[i + 1].role == "user" and req.history[i + 1].text.strip():
                            salary_answered = True
                        break
            
            # If salary question was asked and answered, finish the interview
            if salary_asked and salary_answered:
                return NextQuestionResponse(question=None, done=True, live=None)
    except Exception:
        pass

    q_any = result.get("question")
    question_out: str | None = q_any if isinstance(q_any, str) else None
    d_any = result.get("done")
    done_out: bool = True if isinstance(d_any, bool) and d_any else False
    return NextQuestionResponse(question=question_out, done=done_out, live=None)


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
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Geçersiz token")
        try:
            from datetime import datetime, timezone
            if cand.expires_at and cand.expires_at <= datetime.now(timezone.utc):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token süresi dolmuş")
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
        # Check for existing message with same sequence number to avoid duplicates
        existing_msg = (
            await session.execute(
                select(ConversationMessage)
                .where(
                    ConversationMessage.interview_id == body.interview_id,
                    ConversationMessage.sequence_number == next_seq
                )
            )
        ).scalars().first()
        
        if not existing_msg:
            msg = ConversationMessage(
                interview_id=body.interview_id,
                role=DBMessageRole.USER,
                content=text,
                sequence_number=next_seq,
            )
            session.add(msg)
            try:
                await session.commit()
            except Exception:
                # If conflict occurs, rollback and continue
                await session.rollback()
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

    # 5) Check if salary question has been asked and answered (but only after sufficient questions)
    salary_asked = False
    salary_answered = False
    asked_count = sum(1 for t in history if t.get("role") == "assistant")
    try:
        # Look for salary-related questions in conversation history
        for i, turn in enumerate(history):
            if turn.get("role") == "assistant" and turn.get("text"):
                question_text = turn["text"].lower()
                if any(keyword in question_text for keyword in ["maaş", "ücret", "salary", "beklenti"]):
                    salary_asked = True
                    # Check if there's a user response after this question
                    if i + 1 < len(history) and history[i + 1].get("role") == "user" and history[i + 1].get("text", "").strip():
                        salary_answered = True
                    break
        
        # If salary question was asked and answered AND we've asked enough questions, finish the interview
        if salary_asked and salary_answered and asked_count >= 5:
            return NextQuestionResponse(question=None, done=True, live=None)
    except Exception:
        pass

    # 5.1) Delegate to next_question logic
    req = NextQuestionRequest(
        history=[Turn(role=t["role"], text=t["text"]) for t in history],
        interview_id=body.interview_id,
        signals=body.signals,
    )
    # 5.1) Per-turn LLM-backed quick analysis for early-stop and live insights
    from src.services.analysis import generate_llm_full_analysis, merge_enrichment_into_analysis
    from src.core.metrics import Timer
    live: dict | None = None
    try:
        with Timer() as t:
            analysis = await generate_llm_full_analysis(session, body.interview_id)
        # Build turn evidence snippet from the last user message
        last_user_text = next((t.get("text", "") for t in reversed(history) if t.get("role") == "user"), "")
        turn_ev = {
            "seq": next_seq,
            "text": last_user_text[:500],
            "ts_ms": t.ms,
            "comm": analysis.communication_score,
            "tech": analysis.technical_score,
            "culture": analysis.cultural_fit_score,
            "overall": analysis.overall_score,
        }
        await merge_enrichment_into_analysis(session, body.interview_id, {"turn_evidence": turn_ev})
        # Prepare live insights for recruiter dashboard (not exposed to candidate UI)
        live = {
            "overall": analysis.overall_score,
            "communication": analysis.communication_score,
            "technical": analysis.technical_score,
            "cultural_fit": analysis.cultural_fit_score,
            "analysis_ms": t.ms,
        }
    except Exception:
        live = None

    # 5.2) Dynamic max question bound and evidence-based early-stop
    from src.core.config import settings as _settings2
    dynamic_max_q = 10**6
    try:
        if live and isinstance(live.get("overall"), (int, float)):
            ov = float(live["overall"])
            # If very strong candidate early, stop sooner to save time/cost
            if ov >= _settings2.interview_overall_score_strong_threshold:
                dynamic_max_q = min(dynamic_max_q, 5)
            elif ov >= _settings2.interview_overall_score_good_threshold:
                dynamic_max_q = min(dynamic_max_q, 6)
    except Exception:
        dynamic_max_q = _settings2.interview_max_questions_default

    # If we've already asked enough, stop here
    asked_count = sum(1 for t in history if t.get("role") == "assistant")
    # No hard cap; the interviewer will not auto-finish based on count

    # Evidence-based early finish: if requirements coverage is clearly sufficient (positive or negative), end
    try:
        from sqlalchemy import select as _select
        from src.db.models.conversation import InterviewAnalysis
        ia = (
            await session.execute(_select(InterviewAnalysis).where(InterviewAnalysis.interview_id == body.interview_id))
        ).scalar_one_or_none()
        if ia and ia.technical_assessment:
            import json as _json
            blob = _json.loads(ia.technical_assessment)
            req_spec = (blob.get("requirements_spec") or {}).get("items") or []
            job_fit = blob.get("job_fit") or {}
            matrix = job_fit.get("requirements_matrix") or []
            if isinstance(matrix, list) and matrix:
                cover = {str(m.get("label", "")): str(m.get("meets", "")).lower() for m in matrix if isinstance(m, dict)}
                must_labels = [str(it.get("label", "")) for it in req_spec if isinstance(it, dict) and bool(it.get("must", False))]
                # If no explicit must, pick top-3 by weight as critical
                if not must_labels:
                    tmp = sorted([it for it in req_spec if isinstance(it, dict)], key=lambda it: float(it.get("weight", 0.5) or 0.5), reverse=True)
                    must_labels = [str(it.get("label", "")) for it in tmp[:3]]
                must_labels = [l for l in must_labels if l]
                must_yes = all(cover.get(l) == "yes" for l in must_labels) if must_labels else False
                must_no = any(cover.get(l) == "no" for l in must_labels) if must_labels else False
                must_partial_count = sum(1 for l in must_labels if cover.get(l) == "partial") if must_labels else 0
                ov = float(live["overall"]) if live and isinstance(live.get("overall"), (int, float)) else None
                # Positive: all critical requirements met → finish if minimum interaction achieved
                if asked_count >= _settings2.interview_min_questions_positive and must_yes:
                    return NextQuestionResponse(question=None, done=True, live=live)
                # Negative: any critical requirement explicitly not met and enough exchange → finish
                if asked_count >= _settings2.interview_min_questions_negative and must_no:
                    return NextQuestionResponse(question=None, done=True, live=live)
                # Mixed: many partials and low overall → finish to avoid dragging
                if asked_count >= _settings2.interview_min_questions_mixed and must_partial_count >= 2 and (ov is not None and ov <= _settings2.interview_low_score_threshold):
                    return NextQuestionResponse(question=None, done=True, live=live)
    except Exception:
        pass

    # 5.2) Check if adaptive questioning should be used
    should_adapt = False
    try:
        from src.services.adaptive_questions import should_adapt_interview, analyze_response_weaknesses, generate_targeted_question
        should_adapt = await should_adapt_interview(history, asked_count)
        
        if should_adapt and asked_count >= 3:
            # Get job context for adaptive analysis
            interview = (
                await session.execute(select(Interview).where(Interview.id == body.interview_id))
            ).scalar_one_or_none()
            
            job_context = ""
            if interview:
                from src.db.models.job import Job
                job = (await session.execute(select(Job).where(Job.id == interview.job_id))).scalar_one_or_none()
                if job and job.description:
                    job_context = job.description[:2000]
            
            # Analyze weaknesses and generate targeted question
            weakness_analysis = await analyze_response_weaknesses(history, job_context)
            
            if weakness_analysis.get("weak_areas"):
                priority_area = weakness_analysis["weak_areas"][0]  # Get highest priority weakness
                targeted_question = await generate_targeted_question(priority_area, job_context)
                
                if targeted_question:
                    # Return adaptive question directly
                    next_seq2 = (last.sequence_number if last else 0) + 1
                    session.add(
                        ConversationMessage(
                            interview_id=body.interview_id,
                            role=DBMessageRole.ASSISTANT,
                            content=targeted_question,
                            sequence_number=next_seq2,
                        )
                    )
                    await session.commit()
                    return NextQuestionResponse(question=targeted_question, done=False, live=live)
    except Exception as e:
        # Fall back to standard question generation
        import logging
        logging.warning(f"Adaptive questioning failed: {e}")
        pass

    # 5.3) Delegate to next_question logic to craft next prompt
    result = await next_question(req, session)  # returns NextQuestionResponse
    # Attach live insights to the response
    try:
        result.live = live  # type: ignore[attr-defined]
    except Exception:
        pass

    # 6) Persist assistant question if any
    if result.question:
        last2 = (
            await session.execute(
                select(ConversationMessage)
                .where(ConversationMessage.interview_id == body.interview_id)
                .order_by(ConversationMessage.sequence_number.desc())
            )
        ).scalars().first()
        # Skip insert if identical assistant question was just saved
        try:
            if last2 and getattr(last2.role, "value", str(last2.role)) == "assistant" and (last2.content or "").strip() == (result.question or "").strip():
                pass
            else:
                # Check for existing message with same content (due to unique constraint)
                existing_msg = (
                    await session.execute(
                        select(ConversationMessage)
                        .where(
                            ConversationMessage.interview_id == body.interview_id,
                            ConversationMessage.role == DBMessageRole.ASSISTANT,
                            ConversationMessage.content == result.question
                        )
                    )
                ).scalars().first()
                
                if not existing_msg:
                    next_seq2 = (last2.sequence_number if last2 else 0) + 1
                    
                    # Double-check for sequence conflicts before inserting
                    seq_conflict = (
                        await session.execute(
                            select(ConversationMessage)
                            .where(
                                ConversationMessage.interview_id == body.interview_id,
                                ConversationMessage.sequence_number == next_seq2
                            )
                        )
                    ).scalars().first()
                    
                    if not seq_conflict:
                        session.add(
                            ConversationMessage(
                                interview_id=body.interview_id,
                                role=DBMessageRole.ASSISTANT,
                                content=result.question,
                                sequence_number=next_seq2,
                            )
                        )
                        try:
                            await session.commit()
                        except Exception:
                            # If there's still a conflict, rollback and continue
                            await session.rollback()
        except Exception:
            # Best-effort: do not fail the turn if persistence has a conflict
            try:
                await session.rollback()
            except Exception:
                pass

    return result


