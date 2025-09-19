from __future__ import annotations

from typing import Dict, List

from src.core.config import settings
from src.core.gemini import RECRUITER_PERSONA
from src.services.llm_client import get_llm_client, LLMRequest, LLMProvider


def _local_fallback(history: List[Dict[str, str]], job_context: str | None, max_questions: int) -> Dict[str, str | bool]:
    from src.core.gemini import _fallback_generate
    return _fallback_generate(history, job_context, max_questions)


async def generate_next_question(
    history: List[Dict[str, str]],
    combined_ctx: str | None,
    *,
    max_questions: int = 7,
) -> Dict[str, str | bool]:
    """Provider-agnostic question generation using unified LLM client with retry/fallback."""

    # Respect hard limit by assistant-turn count
    asked = 0
    try:
        asked = sum(1 for t in history if t.get("role") == "assistant")
    except Exception:
        asked = 0
    if asked >= max_questions:
        return {"question": "", "done": True}

    # Build messages with recruiter persona as system and include private context
    try:
        messages: List[Dict[str, str]] = []
        system_content = RECRUITER_PERSONA
        if combined_ctx:
            system_content += "\n\nContext (job description, full resume, extras):\n" + combined_ctx
        messages.append({"role": "system", "content": system_content})
        for turn in history[-20:]:
            role = "user" if (turn.get("role") == "user") else "assistant"
            messages.append({"role": role, "content": turn.get("text") or ""})

        client = get_llm_client()
        request = LLMRequest(
            prompt="",  # Using messages mode
            messages=messages,
            model="gpt-4o-mini",
            temperature=0.3,
            max_tokens=220,
        )

        preferred = None
        if settings.openai_api_key and (settings.environment or "development").lower() == "production":
            preferred = LLMProvider.OPENAI

        response = await client.generate(request, preferred_provider=preferred)
        text = (response.content or "").strip()
        if text.upper().strip() == "FINISHED":
            return {"question": "", "done": True}
        return {"question": text, "done": False}
    except Exception:
        # Local fallback if all providers fail
        return _local_fallback(history, combined_ctx, max_questions)

