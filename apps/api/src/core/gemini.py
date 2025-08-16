import os
from typing import List

from anyio import to_thread

from src.core.config import settings


# --- Dynamic import for new client API ---
try:
    from google import genai  # type: ignore

    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False


GEMINI_API_KEY = settings.gemini_api_key
MODEL_NAME = "gemini-2.5-flash"


def _sync_generate(history: List[dict[str, str]]):
    """Blocking Gemini request executed in a thread."""

    if not _GENAI_AVAILABLE:
        raise RuntimeError("google-ai-python library not installed (pip install google-ai-python)")

    client = genai.Client(api_key=GEMINI_API_KEY)

    system_prompt = (
        "You are an HR interviewer conducting a Turkish job interview. "
        "Given the conversation so far, ask the next appropriate question. "
        "If the candidate has answered sufficiently AND you have asked at least 5 questions, respond with the single word FINISHED. "
        "Otherwise respond with only the next question sentence."
    )

    convo_text = system_prompt + "\n\n"
    for turn in history:
        prefix = "Candidate:" if turn["role"] == "user" else "Interviewer:"
        convo_text += f"{prefix} {turn['text']}\n"
    convo_text += "Interviewer:"

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=convo_text,
        # Note: current google-genai client does not support generation_config param
    )

    text = response.text.strip()
    if text.upper() == "FINISHED":
        return {"question": "", "done": True}
    return {"question": text, "done": False}


def _fallback_generate(history: List[dict[str, str]]) -> dict[str, str]:
    """Deterministic local fallback when Gemini is not configured.

    Asks up to 5 generic Turkish interview questions based on history length.
    """
    canned = [
        "Kendinizi ve son iş deneyiminizi kısaca anlatır mısınız?",
        "Bu pozisyonda başarılı olmak için hangi teknik becerilerin kritik olduğunu düşünüyorsunuz?",
        "Zorlayıcı bir problemi nasıl çözdüğünüze dair somut bir örnek verebilir misiniz?",
        "Takım çalışmasında rolünüz ve iletişim tarzınız nasıldır?",
        "Önümüzdeki 1 yıl için kariyer hedefleriniz nelerdir?",
    ]
    asked = sum(1 for t in history if t.get("role") == "assistant")
    if asked >= len(canned):
        return {"question": "", "done": True}
    return {"question": canned[asked], "done": False}


async def generate_question(history: List[dict[str, str]]) -> dict[str, str]:
    # If API key or library missing, use fallback for smooth local dev
    if not GEMINI_API_KEY or not _GENAI_AVAILABLE:
        return _fallback_generate(history)

    try:
        return await to_thread.run_sync(_sync_generate, history)
    except Exception:
        # Last-resort fallback
        return _fallback_generate(history)