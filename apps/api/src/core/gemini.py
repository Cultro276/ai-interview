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
    "Mirror common Turkish HR phrasing so it feels like a human interviewer: prefer cues like 'kısaca', 'somut örnek', 'ölçülebilir sonuç', 'hangi rolü üstlendiniz', 'ne yaptınız ve sonuç ne oldu?'. "
    "Avoid starting with filler like 'Anladım'/'Görünüyor'; ask direct, polite, natural questions; keep follow-ups short and STAR-oriented. "
    "Proactively personalize questions using the candidate's resume and the job description. "
    "When helpful, explicitly reference resume items in Turkish (e.g., 'Özgeçmişinizde ... gördüm') without exposing sensitive personal data or links. "
)


def _sync_generate(history: List[dict[str, str]], job_context: str | None = None, max_questions: int = 50):
    """Blocking Gemini request executed in a thread."""

    if not _GENAI_AVAILABLE:
        raise RuntimeError("google-ai-python library not installed (pip install google-ai-python)")

    from google import genai as _genai  # type: ignore
    client = _genai.Client(api_key=GEMINI_API_KEY)

    system_prompt = (
        RECRUITER_PERSONA +
        "\nYou are conducting a structured interview. "
        "Given the conversation and context, ask the next concise, natural question in Turkish. "
        "Constraints: \n"
        "- Do NOT echo or paraphrase the candidate's words. \n"
        "- Avoid filler like 'Anladım', 'Görünüyor', 'Teşekkürler' at the start. \n"
        "- Prefer 1–2 sentences; ask a primary question and at most one short follow-up when necessary. \n"
        "- Vary intonation implicitly via word choice: sometimes energetic, sometimes calm; keep it professional. \n"
        "- Use micro-empathy where appropriate (kısa ve doğal), but keep it brief. \n"
        "- Prefer resume- and job-specific questions; it is OK to explicitly reference a resume item (e.g., 'Özgeçmişinizde ... gördüm'). Avoid sharing personal data or links. \n"
        "- Stay strictly on-topic (role, job description, resume). If the candidate asks unrelated things (genel kültür, matematik soruları, vb.), NAZİKÇE konuyu mülakata geri yönlendir. \n"
        "- You may have the full resume text in context; DO NOT say you cannot see the resume. Use it to ask specific, grounded questions. \n"
        "- Do not repeat the same question twice; if already asked, either rephrase concisely or move to the next concrete area. \n"
        "When you judge that you have collected sufficient, concrete evidence (e.g., key requirements confirmed or clearly not met) and the interview has naturally concluded, respond with exactly FINISHED (single word). Do not mention counts. Prefer to finish after at least a few meaningful exchanges. \n"
        "Adaptive behavior: If the last candidate message is extremely short (e.g., '...' or under ~10 characters) or likely STT failure, RE-ASK the SAME question more slowly and in simpler words; keep it 1 sentence. Offer a gentle STAR hint (Durum, Görev, Eylem, Sonuç) only once early in the interview."
    )
    if job_context:
        # Accept larger context to include full resume and extras (no truncation here; upstream controls size)
        system_prompt += (
            "\n\nContext (job description, full resume, and extra questions):\n" + job_context
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
    if text.upper().strip() == "FINISHED":
        return {"question": "", "done": True}
    return {"question": text, "done": False}


def _fallback_generate(history: List[dict[str, str]], job_context: str | None = None, max_questions: int = 50) -> dict[str, str | bool]:
    """Deterministic local fallback when Gemini is not configured.

    Asks up to 5 generic Turkish interview questions based on history length.
    """
    # Prefer resume-keyword targeted canned questions if available in job_context
    def _extract_keywords_from_ctx(ctx: str) -> list[str]:
        import re as _re
        # Expect a line like: Internal Resume Keywords: kw1, kw2, kw3
        m = _re.search(r"Internal Resume Keywords:\s*(.+)", ctx or "", flags=_re.IGNORECASE)
        if not m:
            return []
        part = m.group(1)
        kws = [t.strip() for t in part.split(",") if t.strip()]
        return kws[:6]

    targeted: list[str] = []
    kws = _extract_keywords_from_ctx(job_context or "") if job_context else []
    for k in kws:
        targeted.append(f"Özgeçmişinizde '{k}' geçmiş. Bu konuda hangi problemi nasıl çözdünüz ve ölçülebilir sonuç neydi?")
    # Fallback generics only if no targeted left
    canned = targeted + [
        "Özgeçmişinizde öne çıkan bir proje/başarıyı STAR çerçevesinde kısaca anlatır mısınız?",
        "Son rolünüzde somut bir katkınızı ve sonucunu paylaşır mısınız?",
    ]
    asked = sum(1 for t in history if t.get("role") == "assistant")
    # Respect hard question limit first
    if asked < len(canned):
        return {"question": canned[asked], "done": False}
    # Keep going without finishing: vary phrasing slightly
    return {"question": "Özgeçmişinizden başka bir proje veya başarıyı kısaca STAR çerçevesinde paylaşır mısınız?", "done": False}


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

def _openai_sync_generate(history: List[dict[str, str]], job_context: str | None = None, max_questions: int = 50) -> dict[str, str | bool]:
    """Blocking OpenAI request executed in a thread (chat.completions)."""
    api_key = settings.openai_api_key
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not configured")
    import httpx  # local import to avoid import when unused

    system_prompt = (
        RECRUITER_PERSONA +
        "\nYou are conducting a structured interview. "
        "Given the conversation so far and the provided context, ask the next concise, natural, and human-sounding question in Turkish. "
        "Do NOT echo or paraphrase the candidate's words back to them. Avoid filler like 'Anladım', 'Görünüyor', 'Teşekkürler' at the start. "
        "Prefer 1–2 sentences; ask a primary question and at most one short follow-up when necessary. "
        "Prefer asking about the intersection of the Job Description and the Candidate Resume; explicitly reference resume items in Turkish (e.g., 'Özgeçmişinizde ... gördüm'). Avoid exposing personal data or links. "
        "Stay strictly on-topic (role, job description, resume). If the candidate asks unrelated things (genel kültür, matematik soruları, vb.), NAZİKÇE konuyu mülakata geri yönlendir. "
        "You may have the full resume text in context; DO NOT say you cannot see the resume. Use it to ask specific, grounded questions. "
        "Do not repeat the same question twice; if already asked, rephrase or proceed. "
        "When you judge that you have collected sufficient evidence and the interview has reached a natural conclusion, respond with exactly FINISHED (single word). Do not mention counts."
    )
    if job_context:
        system_prompt += ("\n\nContext (job description and full resume text may be included):\n" + job_context[:8000])

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
    if text.upper().strip() == "FINISHED":
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