from __future__ import annotations

import json
import httpx
from typing import Any, Dict

from src.core.config import settings


async def extract_soft_skills(text: str, job_desc: str | None = None) -> Dict[str, Any]:
    """Extract soft skills and short summary using OpenAI (if configured).

    Returns a dict shape suitable to embed inside InterviewAnalysis.technical_assessment.
    Falls back to empty dict if API key missing or call fails.
    """
    if not settings.openai_api_key:
        return {}
    prompt = (
        "Aşağıdaki yanıttan soft-skills çıkar ve kısa özet ver. "
        "Yanıt Türkçe olabilir. JSON dön: {\"soft_skills\":[{\"label\":str,\"confidence\":0-1,\"evidence\":str}],\"summary\":str}.\n"
        f"İş tanımı: {job_desc or '-'}\n"
        f"Yanıt: {text[:4000]}"
    )
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    body = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post("https://api.openai.com/v1/chat/completions", json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            try:
                return json.loads(content)
            except Exception:
                return {"summary": content}
    except Exception:
        return {}


async def summarize_candidate_profile(resume_text: str, job_desc: str | None = None) -> str:
    """Return 1-2 sentence summary tailored to the job. Empty string if unavailable."""
    if not (settings.openai_api_key and resume_text.strip()):
        return ""
    prompt = (
        "Aşağıdaki özgeçmiş metnini iş ilanına göre 1-2 cümlede özetle. Basit, doğal Türkçe kullan.\n"
        f"İlan: {job_desc or '-'}\n"
        f"Özgeçmiş: {resume_text[:3500]}"
    )
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    body = {"model": "gpt-4o-mini", "messages": [{"role": "user", "content": prompt}], "temperature": 0.2}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post("https://api.openai.com/v1/chat/completions", json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return str(data["choices"][0]["message"]["content"]).strip()
    except Exception:
        return ""


async def assess_hr_criteria(transcript_text: str) -> Dict[str, Any]:
    """Score broad HR criteria using LLM: communication clarity, problem-solving, teamwork, leadership, growth mindset.

    Returns: { criteria: [{label, score_0_100, evidence}], summary }
    """
    if not (settings.openai_api_key and transcript_text.strip()):
        return {}
    prompt = (
        "Metne göre HR kriterlerini puanla (0-100) ve kısa kanıt ver. JSON dön.\n"
        "Kriterler: iletişim netliği, problem çözme, takım çalışması, liderlik, büyüme zihniyeti.\n"
        "Format: {\"criteria\":[{\"label\":str,\"score_0_100\":number,\"evidence\":str}],\"summary\":str} \n"
        f"Metin: {transcript_text[:5000]}"
    )
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    body = {"model": "gpt-4o-mini", "messages": [{"role": "user", "content": prompt}], "temperature": 0.1}
    try:
        async with httpx.AsyncClient(timeout=25) as client:
            resp = await client.post("https://api.openai.com/v1/chat/completions", json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            import json as _json
            return _json.loads(data["choices"][0]["message"]["content"])
    except Exception:
        return {}


async def assess_job_fit(job_desc: str, transcript_text: str, resume_text: str | None = None) -> Dict[str, Any]:
    """Produce job-fit summary and requirement coverage in natural language (LLM-level)."""
    if not (settings.openai_api_key and (job_desc.strip() and transcript_text.strip())):
        return {}
    prompt = (
        "İş tanımı ile adayın cevabını (ve varsa özgeçmişini) karşılaştır.\n"
        "Özet + güçlü/zayıf eşleşmeler + eksik alanlar + öneriler ver. JSON dön.\n"
        "{\"job_fit_summary\": str, \"key_matches\": [str], \"gaps\": [str], \"recommendations\": [str], \"requirements_matrix\": [{\"label\": str, \"meets\": \"yes\"|\"partial\"|\"no\", \"evidence\": str}]}\n"
        f"İş Tanımı: {job_desc[:4000]}\n"
        f"Cevap/Transkript: {transcript_text[:4000]}\n"
        f"Özgeçmiş: { (resume_text or '')[:2000] }"
    )
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    body = {"model": "gpt-4o-mini", "messages": [{"role": "user", "content": prompt}], "temperature": 0.2}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post("https://api.openai.com/v1/chat/completions", json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            import json as _json
            return _json.loads(data["choices"][0]["message"]["content"])
    except Exception:
        return {}


async def opinion_on_candidate(job_desc: str, transcript_text: str, resume_text: str | None = None) -> Dict[str, Any]:
    """Return a concise AI opinion for the candidate: label + 2-3 sentence rationale.

    Returns JSON: {"opinion_label": str, "opinion_text": str, "confidence_0_1": number}
    """
    if not (settings.openai_api_key and (job_desc.strip() and transcript_text.strip())):
        return {}
    prompt = (
        "Aşağıdaki iş tanımı ve aday transkriptine göre kısa bir işe alım görüşü ver.\n"
        "Türkçe ve doğal ol. 2-3 cümlelik gerekçe yaz.\n"
        "JSON dön: {\"opinion_label\": \"Strong Hire|Hire|Hold|No Hire\", \"opinion_text\": str, \"confidence_0_1\": number}.\n"
        f"İş Tanımı: {job_desc[:3500]}\n"
        f"Transkript: {transcript_text[:3500]}\n"
        f"Özgeçmiş: {(resume_text or '')[:1500]}"
    )
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    body = {"model": "gpt-4o-mini", "messages": [{"role": "user", "content": prompt}], "temperature": 0.1}
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post("https://api.openai.com/v1/chat/completions", json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            import json as _json
            return _json.loads(data["choices"][0]["message"]["content"])
    except Exception:
        return {}



# --- CV parsing helpers (bytes -> text) and spotlights ---

def _read_pdf_bytes(data: bytes) -> str:
    try:
        from pdfminer.high_level import extract_text_to_fp  # type: ignore
        from io import BytesIO, StringIO
        input_fp = BytesIO(data)
        output = StringIO()
        extract_text_to_fp(input_fp, output)
        return output.getvalue()
    except Exception:
        return ""


def _read_docx_bytes(data: bytes) -> str:
    try:
        from io import BytesIO
        import docx  # type: ignore
        doc = docx.Document(BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs if p.text)
    except Exception:
        return ""


def parse_resume_bytes(data: bytes, content_type: str | None, file_name: str | None = None) -> str:
    ct = (content_type or "").lower().strip()
    name = (file_name or "").lower()
    text = ""
    if "/pdf" in ct or name.endswith(".pdf"):
        text = _read_pdf_bytes(data)
    elif name.endswith(".docx") or "officedocument" in ct:
        text = _read_docx_bytes(data)
    else:
        try:
            text = data.decode("utf-8", errors="ignore")
        except Exception:
            text = ""
    # Normalize whitespace
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


_TECH_TOKENS = {
    "python", "java", "javascript", "typescript", "react", "node", "next.js", "docker", "kubernetes",
    "aws", "gcp", "azure", "postgres", "mysql", "redis", "kafka", "rabbitmq", "microservice",
    "fastapi", "django", "flask", "spring", "spring boot", ".net", "golang", "kotlin", "swift",
}


def extract_resume_spotlights(resume_text: str, max_items: int = 3) -> list[str]:
    """Pick a few concrete lines from the resume that likely contain project/tech context.

    Heuristics: choose lines between 40-220 chars containing any tech token, keep first N unique.
    """
    if not resume_text:
        return []
    lines = [ln.strip() for ln in resume_text.splitlines() if ln.strip()]
    chosen: list[str] = []
    seen: set[str] = set()
    for ln in lines:
        low = ln.lower()
        if 40 <= len(ln) <= 220 and any(tok in low for tok in _TECH_TOKENS):
            key = low[:120]
            if key not in seen:
                seen.add(key)
                chosen.append(ln)
                if len(chosen) >= max_items:
                    break
    # fallback: if nothing matched, take the longest informative line
    if not chosen and lines:
        chosen = sorted(lines, key=lambda s: len(s), reverse=True)[:1]
    return chosen


def make_targeted_question_from_spotlight(line: str) -> str:
    frag = line.strip()
    if len(frag) > 120:
        frag = frag[:117] + "…"
    return (
        f"Özgeçmişinizde '{frag}' üzerinde çalıştığınızı görüyorum. "
        "Bu çalışmada hangi sorunu çözdünüz, hangi teknolojileri nasıl kullandınız ve ölçülebilir sonuç ne oldu?"
    )


# --- CV parsing helpers (bytes -> text) ---

def _read_pdf_bytes(data: bytes) -> str:
    try:
        from pdfminer.high_level import extract_text_to_fp  # type: ignore
        from io import BytesIO, StringIO
        input_fp = BytesIO(data)
        output = StringIO()
        extract_text_to_fp(input_fp, output)
        return output.getvalue()
    except Exception:
        return ""


def _read_docx_bytes(data: bytes) -> str:
    try:
        from io import BytesIO
        import docx  # type: ignore
        doc = docx.Document(BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs if p.text)
    except Exception:
        return ""


def parse_resume_bytes(data: bytes, content_type: str | None, file_name: str | None = None) -> str:
    ct = (content_type or "").lower().strip()
    name = (file_name or "").lower()
    text = ""
    if "/pdf" in ct or name.endswith(".pdf"):
        text = _read_pdf_bytes(data)
    elif name.endswith(".docx") or "officedocument" in ct:
        text = _read_docx_bytes(data)
    else:
        try:
            text = data.decode("utf-8", errors="ignore")
        except Exception:
            text = ""
    # Normalize whitespace
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())
