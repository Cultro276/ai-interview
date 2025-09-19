from __future__ import annotations

from typing import Dict, List

from src.services.memory_store import store as session_memory


_TECH_TOKENS = {
    "python", "java", "javascript", "typescript", "react", "node", "next.js", "docker", "kubernetes",
    "aws", "gcp", "azure", "postgres", "mysql", "redis", "kafka", "rabbitmq", "microservice",
    "fastapi", "django", "flask", "spring", "spring boot", ".net", "golang", "kotlin", "swift",
}


def _extract_mentioned_technologies(texts: List[str], max_items: int = 12) -> List[str]:
    seen: set[str] = set()
    found: List[str] = []
    for txt in texts:
        low = (txt or "").lower()
        for tok in _TECH_TOKENS:
            if tok in low and tok not in seen:
                seen.add(tok)
                found.append(tok)
                if len(found) >= max_items:
                    return found
    return found


def _build_rolling_summary(history: List[Dict[str, str]], max_last_pairs: int = 4, max_len: int = 400) -> str:
    """Create a compact Turkish rolling summary from recent Q/A pairs.

    Prioritizes the last N assistant questions and user answers.
    """
    # Collect last pairs assistant->user
    pairs: List[tuple[str, str]] = []
    last_role = None
    last_q = None
    for turn in history:
        role = (turn.get("role") or "").lower()
        txt = (turn.get("text") or turn.get("content") or "").strip()
        if not txt:
            continue
        if role == "assistant":
            last_q = txt
            last_role = role
        elif role == "user" and last_role == "assistant" and last_q:
            pairs.append((last_q, txt))
            last_q = None
            last_role = role
        else:
            last_role = role

    pairs = pairs[-max_last_pairs:]
    if not pairs:
        # Fallback to last messages
        last_msgs = [(turn.get("role") or "", (turn.get("text") or turn.get("content") or "").strip()) for turn in history[-4:]]
        joined = "; ".join([f"{r}: {t}" for r, t in last_msgs if t])
        return ("Son mesajlar: " + joined)[:max_len]

    bullets: List[str] = []
    for q, a in pairs:
        # Keep concise snippets
        q_snip = (q[:120] + "…") if len(q) > 120 else q
        a_snip = (a[:160] + "…") if len(a) > 160 else a
        bullets.append(f"Soru: {q_snip} | Cevap: {a_snip}")
    base = "; ".join(bullets)
    return ("Özet (son turlar): " + base)[:max_len]


async def enrich_session_memory(interview_id: int, history: List[Dict[str, str]]) -> None:
    """Update in-memory rolling summary and facts based on recent conversation.

    - Builds a compact rolling summary from last Q/A pairs
    - Extracts mentioned technologies as lightweight facts
    """
    try:
        # Build rolling summary
        summary = _build_rolling_summary(history)
        if summary:
            session_memory.update_summary(interview_id, summary)

        # Extract facts
        texts = [(t.get("text") or t.get("content") or "") for t in history[-12:]]
        techs = _extract_mentioned_technologies(texts)
        if techs:
            session_memory.upsert_fact(interview_id, "mentioned_technologies", ", ".join(techs))

        # Track last assistant question explicitly for steering
        last_assistant = next((t.get("text") or t.get("content") or "" for t in reversed(history) if (t.get("role") or "").lower() == "assistant"), "")
        if last_assistant:
            session_memory.upsert_fact(interview_id, "last_question", last_assistant[:200])
    except Exception:
        # Best-effort enrichment only
        return


