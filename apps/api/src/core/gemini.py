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

# Consistent recruiter persona (single voice across all interviews)
RECRUITER_PERSONA = (
    "You are a senior Turkish HR recruiter named 'Ece'. You speak with a calm, professional, and warm tone. "
    "You are concise, human, and natural. You avoid robotic phrasing and avoid repeating candidate words. "
    "Use micro-empathy briefly when appropriate (e.g., 'güzel', 'anlıyorum' INLINE not at the start), but keep it short. "
    "Vary rhythm naturally with word choice (energetic for achievements, calmer for sensitive topics). "
    "Prefer questions that are neither too long nor too short: typically 1–2 sentences, 12–35 words total. "
    "Always address the candidate in a gender-neutral and respectful way; do NOT infer gender from name, voice, or CV. "
)


def _sync_generate(history: List[dict[str, str]], job_context: str | None = None, max_questions: int = 7):
    """Blocking Gemini request executed in a thread."""

    if not _GENAI_AVAILABLE:
        raise RuntimeError("google-ai-python library not installed (pip install google-ai-python)")

    from google import genai as _genai  # type: ignore
    client = _genai.Client(api_key=GEMINI_API_KEY)

    system_prompt = (
        RECRUITER_PERSONA +
        f"\nYou are conducting a structured interview with a hard limit of {max_questions} questions. "
        "Given the conversation and context, ask the next concise, natural question in Turkish. "
        "Constraints: \n"
        "- Do NOT echo or paraphrase the candidate's words. \n"
        "- Avoid filler like 'Anladım', 'Görünüyor', 'Teşekkürler' at the start. \n"
        "- Prefer 1–2 sentences; ask a primary question and at most one short follow-up when necessary. \n"
        "- Vary intonation implicitly via word choice: sometimes energetic, sometimes calm; keep it professional. \n"
        "- Use micro-empathy where appropriate (kısa ve doğal), but keep it brief. \n"
        "- You MAY use job description and CV internally to select a topic, but do NOT reveal, summarize, or reference them explicitly. Never quote names, emails, phone numbers, links, or specific lines from the CV. Keep questions neutral from the candidate's perspective. \n"
        f"- If the candidate has answered sufficiently AND you have already asked {max_questions} questions, respond with exactly FINISHED.\n"
        "Adaptive behavior: If the last candidate message is extremely short (e.g., '...' or under ~10 characters) or likely STT failure, RE-ASK the SAME question more slowly and in simpler words; keep it 1 sentence. Offer a gentle STAR hint (Durum, Görev, Eylem, Sonuç) only once early in the interview."
    )
    if job_context:
        system_prompt += (
            "\n\nJob description (context for tailoring questions):\n" + job_context[:1500]
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

    text = (response.text or "").strip()
    if text.upper() == "FINISHED":
        return {"question": "", "done": True}
    return {"question": text, "done": False}


def _fallback_generate(history: List[dict[str, str]], job_context: str | None = None, max_questions: int = 7) -> dict[str, str | bool]:
    """Deterministic local fallback when Gemini is not configured.

    Asks up to 5 generic Turkish interview questions based on history length.
    """
    # Optionally bias a couple of context-aware questions if job_context exists
    context_biased = []
    if job_context:
        context_biased = [
            "İlanın gereksinimlerine göre en güçlü olduğunuz alanlar nelerdir?",
            "İş tanımındaki sorumluluklara benzer bir projede deneyiminizden bahseder misiniz?",
        ]
    canned = context_biased + [
        "Kendinizi ve son iş deneyiminizi kısaca anlatır mısınız?",
        "Bu pozisyonda başarılı olmak için hangi teknik becerilerin kritik olduğunu düşünüyorsunuz?",
        "Zorlayıcı bir problemi nasıl çözdüğünüze dair somut bir örnek verebilir misiniz?",
        "Takım çalışmasında rolünüz ve iletişim tarzınız nasıldır?",
        "Önümüzdeki 1 yıl için kariyer hedefleriniz nelerdir?",
    ]
    asked = sum(1 for t in history if t.get("role") == "assistant")
    # Respect hard question limit first
    if asked >= max_questions:
        return {"question": "", "done": True}
    if asked >= len(canned):
        return {"question": "", "done": True}
    return {"question": canned[asked], "done": False}


async def generate_question(history: List[dict[str, str]], job_context: str | None = None, max_questions: int = 7) -> dict[str, str | bool]:
    # If API key or library missing, use fallback for smooth local dev
    if not GEMINI_API_KEY or not _GENAI_AVAILABLE:
        return _fallback_generate(history, job_context, max_questions)

    try:
        return await to_thread.run_sync(_sync_generate, history, job_context, max_questions)
    except Exception:
        # Last-resort fallback
        return _fallback_generate(history, job_context, max_questions)


async def polish_question(text: str) -> str:
    """Optionally send the generated question to the LLM to smooth tone.

    Kept optional with strict fallback to original text.
    """
    if not GEMINI_API_KEY or not _GENAI_AVAILABLE:
        return text
    try:
        def _sync(t: str):
            from google import genai as _genai  # type: ignore
            client = _genai.Client(api_key=GEMINI_API_KEY)
            prompt = (
                "Aşağıdaki soruyu Türkçe, kısa ve doğal bir üslupla nazikçe yeniden yaz.\n"
                "Tek cümle ve soru işaretiyle bitir. Yapay ve mekanik duygudan kaçın, hafif insansı ton kat:\n\n" + t
            )
            resp = client.models.generate_content(model=MODEL_NAME, contents=prompt)
            cleaned = (resp.text or t).strip()
            return cleaned or t
        return await to_thread.run_sync(_sync, text)
    except Exception:
        return text


# --- OpenAI fallback (HTTP) ---

def _openai_sync_generate(history: List[dict[str, str]], job_context: str | None = None, max_questions: int = 7) -> dict[str, str | bool]:
    """Blocking OpenAI request executed in a thread (chat.completions)."""
    api_key = settings.openai_api_key
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not configured")
    import httpx  # local import to avoid import when unused

    system_prompt = (
        RECRUITER_PERSONA +
        f"\nYou are conducting a structured interview with a hard limit of {max_questions} questions. "
        "Given the conversation so far and the provided context, ask the next concise, natural, and human-sounding question in Turkish. "
        "Do NOT echo or paraphrase the candidate's words back to them. Avoid filler like 'Anladım', 'Görünüyor', 'Teşekkürler' at the start. "
        "Prefer 1–2 sentences; ask a primary question and at most one short follow-up when necessary. "
        "If both a Job Description and a Candidate Resume section are present in the context, prefer asking about their intersection first; "
        "if Resume is present and this is the first question, it's acceptable to say 'Özgeçmişinizi inceledim' (but never say 'ilanı okudum'). "
        f"If the candidate has answered sufficiently AND you have already asked {max_questions} questions, respond with the single word FINISHED."
    )
    if job_context:
        system_prompt += ("\n\nJob description (context for tailoring questions):\n" + job_context[:1500])

    messages = [{"role": "system", "content": system_prompt}]
    for turn in history:
        role = "user" if turn["role"] == "user" else "assistant"
        messages.append({"role": role, "content": turn["text"]})

    payload = {
        "model": "gpt-4o-mini",
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 120,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    with httpx.Client(timeout=5.0) as client:
        resp = client.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    text = (data.get("choices", [{}])[0].get("message", {}).get("content", "").strip())
    if text.upper() == "FINISHED":
        return {"question": "", "done": True}
    return {"question": text, "done": False}


async def generate_question_robust(history: List[dict[str, str]], job_context: str | None = None, max_questions: int = 7, total_timeout_s: float = 5.0) -> dict[str, str | bool]:
    """Two-tier LLM strategy: OpenAI first, then Gemini; last resort local canned.

    OpenAI (gpt-4o-mini) is preferred for lower latency and Turkish fluency; Gemini remains as backup.
    """
    # 1) OpenAI (preferred)
    try:
        return await to_thread.run_sync(_openai_sync_generate, history, job_context, max_questions)
    except Exception:
        pass

    # 2) Gemini (backup)
    try:
        return await to_thread.run_sync(_sync_generate, history, job_context, max_questions)
    except Exception:
        pass

    # 3) Local canned
    return _fallback_generate(history, job_context, max_questions)


def _fallback_requirements(text: str) -> dict:
    # Deprecated: manual requirements/rubric extraction removed
    return {}


async def extract_requirements_from_text(text: str) -> dict:
    """Deprecated helper kept for compatibility; returns empty config."""
    return {}