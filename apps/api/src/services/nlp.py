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
        "{\"job_fit_summary\": str, \"key_matches\": [str], \"gaps\": [str], \"recommendations\": [str]}\n"
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



