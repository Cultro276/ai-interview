from __future__ import annotations

from typing import Dict, List


def build_memory_section(
    memory_snapshot: Dict | None,
    asked_count: int,
    signals: List[str] | None = None,
    max_last: int = 6,
) -> str:
    """Return a short context block derived from session memory.

    This block is appended to LLM hidden context to reduce repetition and contradictions
    without leaking PII. It is not shown to the candidate.
    """
    if not memory_snapshot:
        return ""
    try:
        parts: List[str] = []
        rs = (memory_snapshot.get("rolling_summary") or "").strip()
        if rs:
            parts.append("PriorSummary: " + rs[:800])
        lastN = list(memory_snapshot.get("lastN") or [])
        if lastN:
            # Keep only assistant questions to steer variety
            prev_qs = [txt for (role, txt) in lastN if role == "assistant" and txt]
            if prev_qs:
                joined = "; ".join([q.strip() for q in prev_qs[-max_last:]])
                parts.append("PreviousQuestions: " + joined[:800])
        if signals:
            parts.append("RecentSignals: " + ", ".join(sorted(set(signals)))[:200])
        if not parts:
            return ""
        return "\n\nSessionMemory Guidance:\n" + "\n".join(parts)
    except Exception:
        return ""


