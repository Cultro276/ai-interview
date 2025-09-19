from __future__ import annotations

"""
Lightweight content safety utilities for PII masking and prompt-safety guardrails.

Functions:
- mask_pii(text): Replace email/phone/URL with tokens to reduce leakage risk.
- analyze_input(text): Detect simple prompt-injection and unsafe patterns.
- validate_assistant_question(text): Final guard for assistant questions.

Notes:
- Designed to be fast, regex-based, and dependency-free.
- Not a replacement for full-blown safety services.
"""

import re
from typing import Dict, List, Tuple


EMAIL_RE = re.compile(r"(?i)\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}(?:\.[a-z]{2,})?\b")
PHONE_RE = re.compile(r"(?:(?:\+?\d{1,3}[\s.-]?)?(?:\(\d{2,4}\)|\d{2,4})[\s.-]?)?\d{3,4}[\s.-]?\d{2,4}[\s.-]?\d{2,4}")
URL_RE = re.compile(r"(?i)\b(?:https?://|www\.)\S+\b")

INJECTION_PHRASES = (
    "ignore previous instructions",
    "override system",
    "disregard above",
    "role: system",
    "begin system prompt",
    "jailbreak",
    "as chatgpt",
    "you are now",
)

DISALLOWED_LINK_HOSTS = (
    "linkedin.com",
    "github.com",
)


def mask_pii(text: str) -> Tuple[str, List[str]]:
    issues: List[str] = []
    s = text or ""
    if not s:
        return s, issues
    if EMAIL_RE.search(s):
        s = EMAIL_RE.sub("[email]", s)
        issues.append("email")
    # Mask long digit sequences as phone numbers conservatively
    if PHONE_RE.search(s):
        s = PHONE_RE.sub(lambda m: "[phone]" if len((m.group(0) or "").strip()) >= 7 else m.group(0), s)
        issues.append("phone")
    if URL_RE.search(s):
        s = URL_RE.sub("[url]", s)
        issues.append("url")
    return s.strip(), issues


def analyze_input(text: str) -> Dict:
    low = (text or "").lower()
    flags: List[str] = []
    for p in INJECTION_PHRASES:
        if p in low:
            flags.append("injection:" + p)
    return {"flags": flags}


def validate_assistant_question(text: str) -> Tuple[bool, str]:
    """Return (ok, safe_text). Remove links/PII and enforce it's a question.

    If the text is empty or looks like a system disclosure, return a neutral fallback.
    """
    s = (text or "").strip()
    if not s:
        return False, "Önceki cevabınızı bir cümleyle somutlaştırır mısınız?"

    # Remove link mentions
    s2, _ = mask_pii(s)
    # Guard system disclosure
    low = s2.lower()
    if any(ph in low for ph in INJECTION_PHRASES):
        return False, "Lütfen son cevabınızı biraz daha somutlaştırır mısınız? Kısa bir örnek paylaşabilirsiniz."

    # Ensure it's a question
    s2 = s2.rstrip()
    if not s2.endswith("?"):
        s2 = s2 + "?"
    return True, s2


