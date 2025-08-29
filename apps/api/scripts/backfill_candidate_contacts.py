# pyright: reportMissingImports=false, reportMissingModuleSource=false
import asyncio
import json
import re
from typing import Any

from sqlalchemy import select

from src.db.session import async_session_factory
from src.db.models.candidate import Candidate
from src.db.models.candidate_profile import CandidateProfile


EMAIL_RE = re.compile(r"(?<![A-Za-z0-9._%+-])[A-Za-z][A-Za-z0-9._%+-]*@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?:\.[A-Za-z]{2,})?(?![A-Za-z0-9._%+-])")
TR_MOBILE_RE = re.compile(r"(?:\+?90)?\s*0?\s*5\d{2}\s*\d{3}\s*\d{2}\s*\d{2}")

GENERIC_NAME_TOKENS = {
    "cv", "özgeçmiş", "ozgecmis", "resume", "kişisel", "kisisel", "bilgiler",
    "devam", "ik", "adres", "document", "dokuman", "doküman", "güncel", "guncel",
    "basvuru", "başvuru", "kullanici", "user"
}


def normalize_phone(value: str | None) -> str | None:
    if not value:
        return None
    digits = re.sub(r"[^\d+]", "", value)
    if digits.startswith("+90") and len(digits) >= 12:
        return digits
    if digits.startswith("90") and len(digits) >= 11:
        return "+" + digits
    if digits.startswith("0") and len(digits) >= 11:
        return "+90" + digits[1:]
    if digits.startswith("5") and len(digits) >= 10:
        return "+90" + digits
    return digits[:20] if digits else None


def normalize_linkedin(u: str | None) -> str | None:
    if not u:
        return None
    u = u.strip()
    low = u.lower()
    if low.startswith("http://") or low.startswith("https://"):
        return u
    if low.startswith("in/") or low.startswith("company/"):
        return "https://www.linkedin.com/" + u
    if "linkedin.com" in low:
        return u
    return "https://www.linkedin.com/in/" + u


def pick_email(text: str, fallback: str | None) -> str | None:
    # prefer valid email in text; else fallback
    m = EMAIL_RE.search(text or "")
    if m:
        return m.group(0).strip()
    return fallback


def guess_name(text: str, fallback_file: str | None, existing: str | None) -> str | None:
    if existing and len(existing.split()) >= 2:
        return existing
    # try header-like lines
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    for ln in lines[:120]:
        low = ln.lower()
        if any(tok in low for tok in GENERIC_NAME_TOKENS):
            continue
        toks = [t for t in re.split(r"\s+", ln) if t]
        if 2 <= len(toks) <= 5 and not re.search(r"\d", ln):
            return " ".join(w.capitalize() for w in toks)
    # fallback: filename
    if fallback_file:
        base = fallback_file.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").strip()
        low = base.lower()
        if not any(tok in low for tok in GENERIC_NAME_TOKENS) and 2 <= len(base.split()) <= 5:
            return base.title()[:255]
    return existing


async def main() -> None:
    updated = 0
    async with async_session_factory() as session:
        rows = (await session.execute(select(Candidate, CandidateProfile).join(CandidateProfile, CandidateProfile.candidate_id == Candidate.id, isouter=True))).all()
        for cand, prof in rows:
            try:
                resume_text = getattr(prof, "resume_text", None) or ""
                parsed_json: dict[str, Any] | None = None
                if getattr(prof, "parsed_json", None):
                    try:
                        parsed_json = json.loads(prof.parsed_json)
                    except Exception:
                        parsed_json = None
                # derive fields
                email_in_parsed = None
                phone_in_parsed = None
                linkedin_in_parsed = None
                if isinstance(parsed_json, dict):
                    email_in_parsed = parsed_json.get("email")
                    phone_in_parsed = parsed_json.get("phone")
                    links = parsed_json.get("links") or {}
                    if isinstance(links, dict):
                        linkedin_in_parsed = links.get("linkedin")
                best_email = pick_email(resume_text, email_in_parsed)
                phone_match = TR_MOBILE_RE.search(resume_text or "")
                best_phone = normalize_phone(phone_in_parsed or (phone_match.group(0) if phone_match else None))
                best_linkedin = normalize_linkedin(linkedin_in_parsed)
                best_name = guess_name(resume_text, getattr(prof, "file_name", None), cand.name)
                changed = False
                if best_name and best_name != cand.name:
                    cand.name = best_name
                    changed = True
                if best_email and best_email != cand.email and "@example.com" in (cand.email or ""):
                    cand.email = best_email
                    changed = True
                if best_phone and best_phone != getattr(cand, "phone", None):
                    cand.phone = best_phone
                    changed = True
                if best_linkedin and best_linkedin != getattr(cand, "linkedin_url", None):
                    cand.linkedin_url = best_linkedin
                    changed = True
                if changed:
                    updated += 1
            except Exception:
                continue
        try:
            await session.commit()
        except Exception as e:
            await session.rollback()
            print(f"Commit error (some candidates may have conflicting emails): {e}")
    print(f"Backfill completed. Updated {updated} candidates.")


if __name__ == "__main__":
    asyncio.run(main())
