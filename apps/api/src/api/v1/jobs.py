# pyright: reportMissingImports=false, reportMissingModuleSource=false
from typing import List
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.job import Job
from src.db.session import get_session, async_session_factory
from src.auth import current_active_user, get_effective_owner_id, ensure_permission
from src.db.models.user import User
from src.api.v1.schemas import JobCreate, JobRead, JobUpdate, CandidateCreate, CandidateRead
from src.db.models.candidate import Candidate
from src.db.models.interview import Interview
from src.db.models.candidate_profile import CandidateProfile
from src.db.models.conversation import InterviewAnalysis
from src.core.s3 import put_object_bytes, generate_presigned_put_url_at_key, generate_presigned_get_url
from fastapi import Body
from datetime import datetime, timedelta
from uuid import uuid4
import re
from src.services.nlp import parse_resume_bytes, extract_candidate_fields, extract_candidate_fields_smart
import json
from src.core.config import settings
from typing import Optional
from src.core.audit import AuditLogger, AuditEventType, AuditContext

# Hint pyright that 3rd-party imports are available at runtime
if TYPE_CHECKING:
    import fastapi  # noqa: F401
    import sqlalchemy  # noqa: F401
    import pydantic  # noqa: F401

router = APIRouter(prefix="/jobs", tags=["jobs"])


def create_name_slug(name: str, candidate_id: int) -> str:
    """Create URL-safe slug from candidate name for S3 paths."""
    name_for_path = (name or "unknown").lower()
    
    # Replace Turkish characters
    char_map = {'ç': 'c', 'ğ': 'g', 'ı': 'i', 'ö': 'o', 'ş': 's', 'ü': 'u'}
    for tr_char, en_char in char_map.items():
        name_for_path = name_for_path.replace(tr_char, en_char)
    
    # Clean up: keep only alphanumeric, spaces, and dashes
    name_for_path = re.sub(r'[^a-z0-9\s-]', '', name_for_path)
    # Replace spaces with dashes
    name_for_path = re.sub(r'\s+', '-', name_for_path.strip())
    # Remove multiple consecutive dashes
    name_for_path = re.sub(r'-+', '-', name_for_path)
    
    # Limit length and clean edges
    if len(name_for_path) > 30:
        name_for_path = name_for_path[:30]
    name_for_path = name_for_path.strip('-')
    
    # Ensure we have something and add ID for uniqueness
    if not name_for_path:
        name_for_path = "candidate"
    
    return f"{name_for_path}-{candidate_id}"


def _sanitize_phone(raw: Optional[str]) -> Optional[str]:
    """Return phone in E.164 (+xxxxxxxxxxxx) if possible; otherwise None.

    Avoids DB validation errors from EncryptedPhone when LLM extracts free-form phones.
    """
    if not raw:
        return None
    s = str(raw).strip()
    if not s:
        return None
    import re as _re
    # Allow already valid E.164
    if _re.match(r"^\+[1-9]\d{1,14}$", s):
        return s
    # Strip all non-digits
    digits = "".join(ch for ch in s if ch.isdigit())
    if not digits:
        return None
    # Drop leading zeros
    digits = digits.lstrip("0")
    # Heuristic: common TR mobile numbers (10 digits starting with 5) -> +90
    if len(digits) == 10 and digits.startswith("5"):
        cand = "+90" + digits
        if _re.match(r"^\+[1-9]\d{1,14}$", cand):
            return cand
    # If looks like an international number (11-15 digits), prefix '+'
    if 11 <= len(digits) <= 15:
        cand = "+" + digits
        if _re.match(r"^\+[1-9]\d{1,14}$", cand):
            return cand
    return None


@router.get("/", response_model=List[JobRead])
async def list_jobs(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user)
):
    owner_id = get_effective_owner_id(current_user)
    result = await session.execute(select(Job).where(Job.user_id == owner_id))
    return result.scalars().all()


## Removed requirements-config, rubric-weights, and extract-requirements endpoints


@router.post("/", response_model=JobRead, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_in: JobCreate, 
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user)
):
    ensure_permission(current_user, manage_jobs=True)
    expiry = job_in.expires_in_days if (job_in.expires_in_days and job_in.expires_in_days > 0) else 7
    job = Job(
        title=job_in.title,
        description=job_in.description,
        extra_questions=(job_in.extra_questions or None),
        user_id=get_effective_owner_id(current_user),
        default_invite_expiry_days=expiry,
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    # Audit
    try:
        audit = AuditLogger()
        await audit.log(
            AuditEventType.DATA_CREATE,
            message="Job created",
            context=AuditContext(user_id=get_effective_owner_id(current_user), tenant_id=get_effective_owner_id(current_user), resource_type="job", resource_id=job.id),
            details={"title": job.title}
        )
    except Exception:
        pass
    return job


@router.put("/{job_id}", response_model=JobRead)
async def update_job(
    job_id: int, 
    job_in: JobUpdate, 
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user)
):
    ensure_permission(current_user, manage_jobs=True)
    owner_id = get_effective_owner_id(current_user)
    result = await session.execute(select(Job).where(Job.id == job_id, Job.user_id == owner_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    for field, value in job_in.dict(exclude_unset=True).items():
        if field == "expires_in_days" and value is not None:
            job.default_invite_expiry_days = value
        elif field in {"title", "description", "extra_questions"}:
            setattr(job, field, value)
    await session.commit()
    await session.refresh(job)
    # Audit
    try:
        audit = AuditLogger()
        await audit.log(
            AuditEventType.DATA_UPDATE,
            message="Job updated",
            context=AuditContext(user_id=get_effective_owner_id(current_user), tenant_id=get_effective_owner_id(current_user), resource_type="job", resource_id=job.id),
            details={"fields": list(job_in.dict(exclude_unset=True).keys())}
        )
    except Exception:
        pass
    # Precompute dialog plan for all interviews under this job? Not at job create.
    return job


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: int, 
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user)
):
    ensure_permission(current_user, manage_jobs=True)
    owner_id = get_effective_owner_id(current_user)
    result = await session.execute(select(Job).where(Job.id == job_id, Job.user_id == owner_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    await session.delete(job)
    await session.commit()
    # Audit
    try:
        audit = AuditLogger()
        await audit.log(
            AuditEventType.DATA_DELETE,
            message="Job deleted",
            context=AuditContext(user_id=get_effective_owner_id(current_user), tenant_id=get_effective_owner_id(current_user), resource_type="job", resource_id=job_id)
        )
    except Exception:
        pass


# --- Bulk CV upload --

class BulkUploadResponse(BaseModel):
    created: int
    candidates: List[int]


_EMAIL_RE = re.compile(r"(?<![A-Za-z0-9._%+-])[A-Za-z][A-Za-z0-9._%+-]*@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?:\.[A-Za-z]{2,})*(?![A-Za-z0-9._%+-])")


def _extract_email(text: str) -> str | None:
    m = _EMAIL_RE.search(text or "")
    return (m.group(0).strip().lower() if m else None)


@router.post("/{job_id}/candidates/bulk-upload", response_model=BulkUploadResponse)
async def bulk_upload_candidates(
    job_id: int,
    files: List[UploadFile] = File(...),
    expires_in_days: int = Form(7),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user),
):
    ensure_permission(current_user, manage_candidates=True)
    owner_id = get_effective_owner_id(current_user)
    job = (await session.execute(select(Job).where(Job.id == job_id, Job.user_id == owner_id))).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    created_ids: List[int] = []
    # Collect but don't fail whole request on single-file errors
    errors: List[str] = []

    for f in files:
        try:
            content = await f.read()
            # Parse bytes into normalized text for ALL file types (pdf, docx, txt)
            try:
                text = parse_resume_bytes(content, f.content_type, f.filename)
            except Exception:
                text = ""

            # Extract fields with LLM for accuracy (fallback to heuristics on failure)
            try:
                fields_quick = await extract_candidate_fields_smart(text, f.filename)
            except Exception:
                try:
                    fields_quick = extract_candidate_fields(text, f.filename)
                except Exception:
                    fields_quick = {}
            # Get email from extraction results (already validated by LLM/heuristics)
            email = None
            if isinstance(fields_quick, dict):
                extracted_email = fields_quick.get("email")
                if isinstance(extracted_email, str) and extracted_email.strip() and "@" in extracted_email:
                    email = extracted_email.strip().lower()
            
            # Fallback: search in text if no email extracted
            if not email:
                m = _EMAIL_RE.search(text or "")
                if m:
                    email = m.group(0).strip().lower()
            base = (f.filename or "candidate").rsplit(".", 1)[0].replace("_", " ").replace("-", " ").strip()
            # prefer name from text; reject generic filename-derived labels
            generic = {"cv","özgeçmiş","ozgecmis","resume","kişisel","kisisel","bilgiler","devam","ik","adres","document","dokuman","doküman","güncel","guncel","basvuru","başvuru","kullanici","user","curriculum","vitae","eğitim","egitim","deneyim","portfolio","profil","profile","son","yeni","final","latest","updated","new","version","ver","v","copy","kopya"}
            name_from_text = (fields_quick.get("name") if isinstance(fields_quick, dict) else None)
            name = None
            if isinstance(name_from_text, str) and 2 <= len(name_from_text.split()) <= 5:
                name = name_from_text.strip()[:255]
            else:
                low = base.lower()
                if (not any(k in low for k in generic)) and 2 <= len(base.split()) <= 5:
                    name = base.title()[:255]
                else:
                    name = "Candidate"

            # Clean S3 path structure: resumes/job-{job_id}/candidate-{candidate_id}.{ext}
            safe_name = (f.filename or "resume").split("/")[-1]
            # Extract file extension
            file_ext = safe_name.split('.')[-1] if '.' in safe_name else 'bin'
            # In production use S3. In dev (no S3), skip and store raw bytes in DB profile.
            temp_key = f"temp/job-{job.id}/{safe_name}"
            resume_url = None
            s3_available = bool(settings.s3_bucket)
            if s3_available:
                try:
                    resume_url = put_object_bytes(temp_key, content, f.content_type or "application/octet-stream")
                except Exception:
                    # Treat as dev fallback if S3 write fails
                    resume_url = None
                    s3_available = False

            # Ensure a unique, valid email (fallback if missing or already exists)
            from uuid import uuid4 as _uuid4
            use_email = email or f"candidate-{_uuid4().hex[:8]}@placeholder.local"
            try:
                exists = (
                    await session.execute(select(Candidate.id).where(Candidate.email == use_email))
                ).scalar_one_or_none()
                if exists is not None:
                    # Tweak alias slightly to ensure uniqueness
                    use_email = f"candidate-{_uuid4().hex[:8]}@placeholder.local"
            except Exception:
                pass

            # Create candidate or reuse existing (email unique) by catching IntegrityError
            create_new = True
            cand: Candidate
            try:
                cand = Candidate(
                    user_id=owner_id,
                    name=(name or "Candidate").strip() or "Candidate",
                    email=use_email,
                    phone=None,
                    linkedin_url=((fields_quick.get("links") or {}).get("linkedin") if isinstance(fields_quick, dict) else None),
                    resume_url=resume_url,  # Temporary URL, will be updated below
                    status="pending",
                    token=uuid4().hex,
                    expires_at=datetime.utcnow() + timedelta(days=expires_in_days),
                )
                session.add(cand)
                await session.flush()  # Get candidate.id
            except Exception as _e:
                # Likely duplicate email; find existing candidate under same tenant
                await session.rollback()
                create_new = False
                try:
                    all_cands = (
                        await session.execute(select(Candidate).where(Candidate.user_id == owner_id))
                    ).scalars().all()
                    cand = next((c for c in all_cands if (c.email or "").strip().lower() == (use_email or "").strip().lower()), None)  # type: ignore[attr-defined]
                except Exception:
                    cand = None  # type: ignore[assignment]
                if not cand:
                    raise
            
            # Move file to clean path if S3 is available: resumes/job-{job_id}/{name-slug}.{ext}
            if s3_available and resume_url:
                name_slug = create_name_slug(cand.name, cand.id)
                final_key = f"resumes/job-{job.id}/{name_slug}.{file_ext}"
                temp_s3_key = temp_key
                try:
                    from src.core.s3 import move_object
                    final_url = move_object(temp_s3_key, final_key)
                    cand.resume_url = final_url  # Update with final clean URL
                except Exception as e:
                    print(f"Failed to move resume to clean path: {e}")
                    # Keep original URL if move fails

            # Link to job via Interview
            interview = Interview(job_id=job.id, candidate_id=cand.id, status="pending")
            session.add(interview)

            # Save profile metadata only (no raw file in DB when using S3)
            profile = CandidateProfile(
                candidate_id=cand.id,
                resume_text=text or None,
                resume_file=(None if s3_available else content),
                file_name=f.filename,
                content_type=f.content_type,
                file_size=len(content),
                parsed_json=(json.dumps(fields_quick, ensure_ascii=False) if fields_quick else None),
            )
            session.add(profile)

            await session.commit()
            created_ids.append(cand.id)
            # Audit
            try:
                audit = AuditLogger()
                if create_new:
                    await audit.log(
                        AuditEventType.DATA_CREATE,
                        message="Candidate created via bulk upload",
                        context=AuditContext(user_id=owner_id, tenant_id=owner_id, resource_type="candidate", resource_id=cand.id),
                        details={"job_id": job.id}
                    )
                await audit.log(
                    AuditEventType.INTERVIEW_CREATE,
                    message="Interview linked (bulk upload)",
                    context=AuditContext(user_id=owner_id, tenant_id=owner_id, resource_type="interview", resource_id=interview.id),
                    details={"job_id": job.id, "candidate_id": cand.id}
                )
            except Exception:
                pass

            # Background: improve parsed_json using a fresh DB session (avoid await_only issues)
            async def _bg_improve(cid: int, resume_txt: str | None, file_name: str | None):
                if not resume_txt:
                    return
                try:
                    from sqlalchemy import select as _sel
                    async with async_session_factory() as bg:
                        try:
                            fields_full = await extract_candidate_fields_smart(resume_txt, file_name)
                        except Exception:
                            return
                        if not fields_full:
                            return
                        prof_obj = (
                            await bg.execute(_sel(CandidateProfile).where(CandidateProfile.candidate_id == cid))
                        ).scalar_one_or_none()
                        if prof_obj:
                            import json as _json
                            prof_obj.parsed_json = _json.dumps(fields_full, ensure_ascii=False)
                            await bg.commit()
                except Exception:
                    return
            try:
                import asyncio as _aio
                _aio.create_task(_bg_improve(cand.id, text, f.filename))
            except Exception:
                pass

        except Exception as e:
            try:
                await session.rollback()
            except Exception:
                pass
            errors.append(str(e))

    # If nothing created, return error with captured reasons
    if len(created_ids) == 0:
        from fastapi import HTTPException as _HTTPException
        raise _HTTPException(status_code=400, detail={
            "message": "No candidates created",
            "errors": errors[:10],
        })
    return BulkUploadResponse(created=len(created_ids), candidates=created_ids) 


# --- Single candidate creation bound to a job ---


@router.post("/{job_id}/candidates", response_model=CandidateRead, status_code=status.HTTP_201_CREATED)
async def create_candidate_for_job(
    job_id: int,
    cand_in: CandidateCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user),
):
    # Ensure job belongs to current user
    ensure_permission(current_user, manage_candidates=True)
    owner_id = get_effective_owner_id(current_user)
    job = (
        await session.execute(select(Job).where(Job.id == job_id, Job.user_id == owner_id))
    ).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Create candidate (mimic candidates.create flow)
    from uuid import uuid4
    from src.core.mail import send_email_resend
    expires_days = cand_in.expires_in_days or job.default_invite_expiry_days or 7
    # Create or reuse candidate by email (catch duplicate)
    from sqlalchemy.exc import IntegrityError
    candidate: Candidate
    created_new = True
    try:
        candidate = Candidate(
            user_id=owner_id,
            name=cand_in.name,
            email=cand_in.email,
            resume_url=cand_in.resume_url,
            status="pending",
            token=uuid4().hex,
            expires_at=datetime.utcnow() + timedelta(days=expires_days),
        )
        session.add(candidate)
        await session.flush()
    except IntegrityError:
        await session.rollback()
        created_new = False
        # Scan this tenant's candidates to find by decrypted email
        existing = (
            await session.execute(select(Candidate).where(Candidate.user_id == owner_id))
        ).scalars().all()
        found = next((c for c in existing if (c.email or "").strip().lower() == cand_in.email.strip().lower()), None)  # type: ignore[attr-defined]
        if not found:
            raise
        candidate = found

    # Link to job via Interview
    interview = Interview(job_id=job.id, candidate_id=candidate.id, status="pending")
    session.add(interview)
    await session.flush()

    # Trigger dialog plan precompute in background so first questions are personalized
    try:
        from src.services.analysis import precompute_dialog_plan_bg
        import asyncio as _aio
        _aio.create_task(precompute_dialog_plan_bg(interview.id))
    except Exception:
        pass

    # If candidate has an uploaded resume URL, parse it now so LLM has context immediately
    try:
        if candidate.resume_url and candidate.resume_url.strip():
            def _to_key(url: str) -> str | None:
                if url.startswith("s3://"):
                    from urllib.parse import urlparse as _up
                    p = _up(url)
                    return p.path.lstrip("/")
                try:
                    from urllib.parse import urlparse as _up
                    p = _up(url)
                    return p.path.lstrip("/")
                except Exception:
                    return None
            key = _to_key(candidate.resume_url)
            if key:
                url = generate_presigned_get_url(key, expires=120)
                import httpx
                async with httpx.AsyncClient(timeout=20.0) as client:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    data = resp.content
                    from src.services.nlp import parse_resume_bytes, extract_candidate_fields_smart
                    parsed = parse_resume_bytes(data, resp.headers.get("Content-Type"), candidate.resume_url)
                    if parsed:
                        prof = (
                            await session.execute(
                                select(CandidateProfile).where(CandidateProfile.candidate_id == candidate.id)
                            )
                        ).scalar_one_or_none()
                        if prof:
                            prof.resume_text = parsed[:100000]
                            try:
                                import json as _json
                                fields = await extract_candidate_fields_smart(parsed, candidate.resume_url)
                                prof.parsed_json = _json.dumps(fields, ensure_ascii=False)
                            except Exception:
                                pass
                        else:
                            try:
                                import json as _json
                                fields = await extract_candidate_fields_smart(parsed, candidate.resume_url)
                                session.add(CandidateProfile(candidate_id=candidate.id, resume_text=parsed[:100000], parsed_json=_json.dumps(fields, ensure_ascii=False)))
                            except Exception:
                                session.add(CandidateProfile(candidate_id=candidate.id, resume_text=parsed[:100000]))
                        await session.flush()
    except Exception:
        pass

    await session.commit()
    await session.refresh(candidate)
    # Audit
    try:
        audit = AuditLogger()
        if created_new:
            await audit.log(
                AuditEventType.DATA_CREATE,
                message="Candidate created",
                context=AuditContext(user_id=owner_id, tenant_id=owner_id, resource_type="candidate", resource_id=candidate.id),
                details={"job_id": job.id}
            )
        await audit.log(
            AuditEventType.INTERVIEW_CREATE,
            message="Interview created for job",
            context=AuditContext(user_id=owner_id, tenant_id=owner_id, resource_type="interview", resource_id=interview.id),
            details={"job_id": job.id, "candidate_id": candidate.id}
        )
    except Exception:
        pass

    # Best-effort invite email
    try:
        await send_email_resend(
            candidate.email,
            "Interview Invitation",
            (
                f"Merhaba {candidate.name},\n\n"
                f"Mülakatınızı başlatmak için bağlantı:\nhttp://localhost:3000/interview/{candidate.token}\n\n"
                f"Bağlantı {expires_days} gün geçerlidir."
            ),
        )
    except Exception:
        pass
    import logging
    logging.getLogger(__name__).info("[INVITE LINK] /interview/%s", candidate.token)
    return candidate


# --- Single candidate with CV presign ---


class SingleCandidatePresignRequest(BaseModel):
    file_name: str
    content_type: str


@router.post("/{job_id}/candidates/presign-cv")
async def presign_single_candidate_cv(
    job_id: int,
    payload: SingleCandidatePresignRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user),
):
    # Verify job ownership
    owner_id = get_effective_owner_id(current_user)
    job = (
        await session.execute(select(Job).where(Job.id == job_id, Job.user_id == owner_id))
    ).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    safe_name = (payload.file_name or "resume").split("/")[-1]
    # Use temp path for presign, will be moved to clean path after candidate creation
    key = f"temp/job-{job.id}/{safe_name}"
    try:
        presigned = generate_presigned_put_url_at_key(key, payload.content_type)
        return {"url": presigned["url"], "key": presigned["key"]}
    except Exception:
        # Dev fallback – when S3 not configured
        url = f"http://localhost:8000/dev-upload/{key}"
        return {"url": url, "key": key}


# --- Leaderboard for a job ---


class LeaderboardItem(BaseModel):
    candidate_id: int
    candidate_name: str | None
    interview_id: int
    overall_score: float | None = None
    communication_score: float | None = None
    technical_score: float | None = None
    cultural_fit_score: float | None = None


@router.get("/{job_id}/leaderboard", response_model=List[LeaderboardItem])
async def job_leaderboard(
    job_id: int,
    limit: int = 100,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user),
):
    # Verify ownership
    ensure_permission(current_user, view_interviews=True)
    owner_id = get_effective_owner_id(current_user)
    job = (
        await session.execute(select(Job).where(Job.id == job_id, Job.user_id == owner_id))
    ).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    result = await session.execute(
        select(
            Interview.id.label("interview_id"),
            Candidate.id.label("candidate_id"),
            Candidate.name.label("candidate_name"),
            InterviewAnalysis.overall_score,
            InterviewAnalysis.communication_score,
            InterviewAnalysis.technical_score,
            InterviewAnalysis.cultural_fit_score,
        )
        .join(Candidate, Interview.candidate_id == Candidate.id)
        .outerjoin(InterviewAnalysis, InterviewAnalysis.interview_id == Interview.id)
        .where(Interview.job_id == job.id)
        .order_by(InterviewAnalysis.overall_score.desc().nullslast(), Interview.id.desc())
        .limit(limit)
    )
    rows = result.all()
    return [
        LeaderboardItem(
            interview_id=r.interview_id,
            candidate_id=r.candidate_id,
            candidate_name=r.candidate_name,
            overall_score=r.overall_score,
            communication_score=r.communication_score,
            technical_score=r.technical_score,
            cultural_fit_score=r.cultural_fit_score,
        )
        for r in rows
    ]