from __future__ import annotations

import re


FINISHED_RE = re.compile(r"\bFINISHED\b", re.IGNORECASE)
PHONE_RE = re.compile(r"[+]?\d[\d\s().-]{7,}")
URL_BITS = ("http://", "https://", "www.", "linkedin.com", "github.com")


def strip_finished_flag(text: str) -> tuple[str, bool]:
    s = (text or "").strip()
    if not s:
        return "", False
    cleaned = FINISHED_RE.sub("", s).strip()
    finished = (not cleaned) and ("finished" in s.lower())
    return cleaned, finished


def sanitize_question_text(text: str) -> str:
    s = (text or "").strip()
    low = s.lower()
    # filter obvious PII and links
    if any(bit in low for bit in URL_BITS):
        return ""
    if PHONE_RE.search(s):
        return ""
    # ensure ends with a question mark for consistency
    if s and not s.endswith("?"):
        s = s + "?"
    # collapse spaces
    s = re.sub(r"\s+", " ", s)
    return s


