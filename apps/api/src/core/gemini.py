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
    "You are a senior Turkish HR recruiter named 'Ece'. You conduct professional interviews with an objective, analytical approach. "
    "Your goal is to ASSESS candidates fairly and critically against job requirements. "
    "You are direct, professional, and neutral - neither overly positive nor negative. "
    "You may use brief natural transitions like 'anladım', 'peki', 'tamam' to maintain conversational flow, but keep them short and natural. "
    "Do NOT praise candidates excessively or use words like 'güzel', 'harika', 'mükemmel', 'çok iyi' unless truly warranted. "
    "Instead of praising, ask follow-up questions to dig deeper: 'Nasıl ölçtünüz bu sonucu?', 'Hangi zorluklar yaşadınız?', 'Alternatif çözümler düşündünüz mü?' "
    "Focus on EVIDENCE and CONCRETE EXAMPLES. If an answer is vague, probe for specifics. "
    "Ask questions that reveal gaps between job requirements and candidate experience. "
    "Create SITUATIONAL questions based on the job description to test competencies. "
    "Always address the candidate in a gender-neutral and respectful way; do NOT infer gender from name, voice, or CV. "
    "Use professional HR language: 'somut örnek verebilir misiniz', 'nasıl yaklaştınız bu duruma', 'hangi yöntemleri kullandınız'. "
    "Keep questions focused and purposeful. Show you're listening with brief acknowledgments before moving to next questions. "
    "If candidate lacks required experience, explore transferable skills but don't artificially boost their profile. "
)


def _sync_generate(history: List[dict[str, str]], job_context: str | None = None, max_questions: int = 50):
    """Blocking Gemini request executed in a thread."""

    if not _GENAI_AVAILABLE:
        raise RuntimeError("google-ai-python library not installed (pip install google-ai-python)")

    from google import genai as _genai  # type: ignore
    client = _genai.Client(api_key=GEMINI_API_KEY)

    system_prompt = (
        RECRUITER_PERSONA +
        "\nYou are conducting a structured interview with the goal of OBJECTIVELY ASSESSING this candidate against job requirements. "
        "Your approach should be analytical, not encouraging. Focus on identifying strengths AND gaps. "
        "Key directives: \n"
        "- Compare candidate's actual experience with specific job requirements. If they lack required skills, probe this gap explicitly. \n"
        "- Create situational questions based on job description competencies (e.g., 'Diyelim ki [job scenario], bu durumda nasıl hareket edersiniz?'). Use job requirements to craft relevant scenarios. \n"
        "- Ask about CHALLENGES and FAILURES, not just successes: 'En zorlandığınız proje neydi?', 'Hangi hatalardan ders aldınız?' \n"
        "- Probe vague answers: If they say 'takım çalışması yaptım', ask 'Nasıl çatışmaları çözdünüz?', 'Hangi roller üstlendiniz?' \n"
        "- Do NOT use praise words like 'güzel', 'harika', 'mükemmel' - remain neutral and professional. \n"
        "- After asking at least 5-6 substantial questions covering key competencies, ask about salary expectations: 'Maaş beklentiniz nedir?' This should be the final question before concluding. \n"
        "- Do NOT ask salary question too early (before 5 questions). Ensure thorough competency assessment first. \n"
        "- Stay strictly on-topic (role, job description, competencies). Redirect off-topic questions professionally. \n"
        "- ONLY reference what is explicitly written in the candidate's resume. Do NOT say 'Özgeçmişinizde X görüyorum' unless X is clearly mentioned in the resume text. \n"
        "- If resume lacks certain job requirements, ask about the gap directly: 'Bu pozisyon React deneyimi gerektiriyor, bu konudaki deneyiminizi anlatır mısınız?' \n"
        "When you have thoroughly assessed key competencies (minimum 5-6 questions) AND asked about salary expectations, respond with exactly FINISHED (single word). \n"
        "Interview must end with salary question - but only after sufficient competency assessment."
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

    Prioritizes job-specific scenarios, then falls back to generic questions.
    """
    # Try to extract job description for dynamic scenarios
    job_desc = ""
    if job_context:
        # Look for job description in context
        lines = job_context.split('\n')
        for line in lines:
            if 'İş Tanımı:' in line or 'Job Description:' in line:
                job_desc = line.split(':', 1)[1].strip() if ':' in line else ""
                break
        if not job_desc and job_context:
            # Use first part of context as job description
            job_desc = job_context.split('\n')[0][:1000]
    
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
    
    # Job-specific scenarios (this would be populated from dynamic generation in real usage)
    job_specific_scenarios: list[str] = []
    
    # Fallback generic situational scenarios
    generic_situational_questions = [
        "Diyelim ki ekibinizde çatışma yaşayan iki meslektaşınız var ve bu durum projeyi etkiliyor. Bu durumda nasıl müdahale edersiniz?",
        "Sıkı bir deadline'ınız var ama projenin kalitesinden ödün vermek istemiyorsunuz. Öncelikleri nasıl belirlersiniz?",
        "Yeni bir teknoloji öğrenmeniz gereken acil bir proje verildi. Nasıl yaklaşırsınız?",
        "Bir projede beklediğiniz sonuçları alamadığınız bir dönem yaşadınız mı? Bu durumu nasıl çözdünüz?",
        "İş arkadaşlarınızdan birinin sürekli geç kaldığı ve ekip performansını etkilediği bir durumla karşılaştınız mı? Nasıl ele aldınız?",
        "Daha önce hiç yapmadığınız bir işi teslim etmeniz gerektiği bir durumda neler yaptınız?",
        "Müşteri/kullanıcı şikayetleri aldığınız bir projede nasıl hareket ettiniz?",
        "Kaynakların kısıtlı olduğu bir projede nasıl çözüm ürettiniz?",
    ]
    
    # Mix targeted, job-specific, and generic questions in priority order
    canned = targeted + job_specific_scenarios + generic_situational_questions + [
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
        "\nYou are conducting a structured interview with the goal of OBJECTIVELY ASSESSING this candidate against job requirements. "
        "Your approach should be analytical, not encouraging. Focus on identifying strengths AND gaps. "
        "Key directives: \n"
        "- Compare candidate's actual experience with specific job requirements. If they lack required skills, probe this gap explicitly. \n"
        "- Create situational questions based on job description competencies (e.g., 'Diyelim ki [job scenario], bu durumda nasıl hareket edersiniz?'). Use job requirements to craft relevant scenarios. \n"
        "- Ask about CHALLENGES and FAILURES, not just successes: 'En zorlandığınız proje neydi?', 'Hangi hatalardan ders aldınız?' \n"
        "- Probe vague answers: If they say 'takım çalışması yaptım', ask 'Nasıl çatışmaları çözdünüz?', 'Hangi roller üstlendiniz?' \n"
        "- Do NOT use praise words like 'güzel', 'harika', 'mükemmel' - remain neutral and professional. \n"
        "- After asking at least 5-6 substantial questions covering key competencies, ask about salary expectations: 'Maaş beklentiniz nedir?' This should be the final question before concluding. \n"
        "- Do NOT ask salary question too early (before 5 questions). Ensure thorough competency assessment first. \n"
        "- Stay strictly on-topic (role, job description, competencies). Redirect off-topic questions professionally. \n"
        "- ONLY reference what is explicitly written in the candidate's resume. Do NOT say 'Özgeçmişinizde X görüyorum' unless X is clearly mentioned in the resume text. \n"
        "- If resume lacks certain job requirements, ask about the gap directly: 'Bu pozisyon React deneyimi gerektiriyor, bu konudaki deneyiminizi anlatır mısınız?' \n"
        "When you have thoroughly assessed key competencies (minimum 5-6 questions) AND asked about salary expectations, respond with exactly FINISHED (single word). \n"
        "Interview must end with salary question - but only after sufficient competency assessment."
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


async def generate_job_specific_scenarios(job_desc: str) -> list[str]:
    """Generate situational interview questions based on job description requirements."""
    from src.core.config import settings
    if not (settings.openai_api_key and job_desc.strip()):
        return []
    
    import httpx
    
    prompt = (
        "İş tanımına göre 5-8 adet durum hikayeleri ve senaryo soruları oluştur.\n"
        "Her soru 'Diyelim ki...' ile başlamalı ve o pozisyonun gerektirdiği yetkinlikleri test etmeli.\n"
        "Soruların formatı: 'Diyelim ki [durum açıklaması]. Bu durumda nasıl hareket edersiniz?'\n"
        "Sadece soru listesini dön, başka açıklama yapma.\n"
        f"İş Tanımı: {job_desc[:3000]}"
    )
    
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    body = {"model": "gpt-4o-mini", "messages": [{"role": "user", "content": prompt}], "temperature": 0.7}
    
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post("https://api.openai.com/v1/chat/completions", json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            
            # Extract questions from content
            lines = content.split('\n')
            questions = []
            for line in lines:
                line = line.strip()
                if line and ('diyelim ki' in line.lower() or 'diyelim' in line.lower()):
                    # Remove bullet points, numbers, etc.
                    clean_line = line.lstrip('- •*123456789.').strip()
                    if clean_line:
                        questions.append(clean_line)
            
            return questions[:8]  # Max 8 questions
    except Exception:
        return []