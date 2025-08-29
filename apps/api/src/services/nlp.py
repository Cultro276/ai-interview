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



# --- Job requirements extraction (normalize spec from Turkish job description) ---

async def extract_requirements_spec(job_desc: str) -> Dict[str, Any]:
    """Normalize job requirements from a Turkish job description into a structured spec.

    Shape:
    {
      "items": [
        {
          "id": str,
          "label": str,
          "must": bool,
          "level": "junior|mid|senior|lead",
          "weight": float (0..1),
          "keywords": [str],
          "success_rubric": str,
          "question_templates": [str]
        }
      ]
    }

    Falls back to a simple keyword-based list if LLM is unavailable.
    """
    if not (job_desc or "").strip():
        return {"items": []}

    # Fallback when no OpenAI key: build a lightweight spec from tokens
    if not settings.openai_api_key:
        import re as _re
        toks = [t for t in _re.split(r"[^a-zA-ZçğıöşüÇĞİÖŞÜ0-9\+\.#]+", job_desc.lower()) if len(t) >= 3]
        seen: set[str] = set()
        uniq: list[str] = []
        for t in toks:
            if t in seen:
                continue
            seen.add(t)
            uniq.append(t)
            if len(uniq) >= 12:
                break
        items = []
        for i, k in enumerate(uniq):
            items.append({
                "id": f"kw_{i}",
                "label": k,
                "must": False,
                "level": "mid",
                "weight": 0.5,
                "keywords": [k],
                "success_rubric": "Somut örnek, rolünüz, yaptığınız eylemler ve ölçülebilir sonuç.",
                "question_templates": [f"{k} ile ilgili somut bir örnek ve sonucu paylaşır mısınız?"],
            })
        return {"items": items}

    # LLM path
    import httpx  # local import in function scope
    import json as _json
    prompt = (
        "Aşağıdaki iş ilanından gereksinimleri çıkar ve normalize et. JSON dön.\n"
        "Şema: {\"items\":[{\"id\":str,\"label\":str,\"must\":bool,\"level\":\"junior|mid|senior|lead\","
        "\"weight\":0-1,\"keywords\":[str],\"success_rubric\":str,\"question_templates\":[str]}]}\n"
        f"İlan Metni:\n{job_desc[:5000]}"
    )
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    body = {"model": "gpt-4o-mini", "messages": [{"role": "user", "content": prompt}], "temperature": 0.1}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post("https://api.openai.com/v1/chat/completions", json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            spec = _json.loads(data["choices"][0]["message"]["content"])
            # Defensive normalization
            items = spec.get("items") if isinstance(spec, dict) else None
            if not isinstance(items, list):
                return {"items": []}
            for i, it in enumerate(items):
                if not isinstance(it, dict):
                    continue
                it.setdefault("id", f"req_{i}")
                it["weight"] = float(it.get("weight", 0.5) or 0.5)
                kws = it.get("keywords") or []
                if not isinstance(kws, list) or not kws:
                    it["keywords"] = [it.get("label", "")]
                qts = it.get("question_templates") or []
                if not isinstance(qts, list) or not qts:
                    it["question_templates"] = [f"{it.get('label','')} ile ilgili somut bir örnek anlatır mısınız?"]
            return {"items": items}
    except Exception:
        return {"items": []}
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


# --- Project title and technology extraction for safer explicit references ---

def extract_resume_project_titles(resume_text: str, max_items: int = 6) -> list[str]:
    titles: list[str] = []
    seen: set[str] = set()
    if not resume_text:
        return titles
    lines = [ln.strip() for ln in resume_text.splitlines() if ln.strip()]
    import re as _re
    in_projects = False
    for ln in lines:
        low = ln.lower()
        if low.startswith("projects") or "projects" in low or low.startswith("projects"):
            in_projects = True
            continue
        cand = _re.sub(r"\s*\([^)]+\)\s*$", "", ln).strip()
        if cand.startswith(("•", "-", "*")):
            continue
        if 6 <= len(cand) <= 120:
            if in_projects or _re.search(r"[A-Za-z][A-Za-z0-9\- ]+", cand):
                key = cand.lower()
                if key not in seen:
                    seen.add(key)
                    titles.append(cand)
                    if len(titles) >= max_items:
                        break
        if in_projects and len(cand) == 0:
            in_projects = False
    if len(titles) < 1:
        for ln in lines:
            if ":" in ln and len(ln.split(":", 1)[0]) <= 80:
                t = ln.split(":", 1)[0].strip()
                if 3 <= len(t) <= 80 and t.lower() not in seen:
                    seen.add(t.lower())
                    titles.append(t)
                    if len(titles) >= max_items:
                        break
    return titles


def extract_known_technologies_from_resume(resume_text: str, max_items: int = 24) -> list[str]:
    out: list[str] = []
    if not resume_text:
        return out
    low = resume_text.lower()
    for tok in sorted(_TECH_TOKENS):
        if tok in low:
            label = tok
            if tok == "next.js":
                label = "Next.js"
            elif tok == "spring boot":
                label = "Spring Boot"
            out.append(label)
            if len(out) >= max_items:
                break
    return out

