from __future__ import annotations

import json
import httpx
from typing import Any, Dict
import re
def _best_phone_tr(text_in: str) -> str | None:
    try:
        digits_only = re.findall(r"(?:\+?90)?\s*0?\s*5\d{2}\s*\d{3}\s*\d{2}\s*\d{2}", text_in)
        generic = re.findall(r"\+?\d[\d\s\-\(\)]{8,}\d", text_in)
        cands = digits_only + generic
        if not cands:
            return None
        def normalize(p: str) -> str:
            return re.sub(r"[^\d+]", "", p)
        def score(p: str) -> tuple[int, int]:
            n = normalize(p)
            mobile = int(bool(re.match(r"^(?:\+?90)?0?5\d{9}$", n)))
            len_score = -abs(len(n) - 12)
            return (mobile, len_score)
        cands = sorted(set(cands), key=score, reverse=True)
        return cands[0].strip()
    except Exception:
        return None


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
    """Return a concise CV summary (max ~600 chars) tailored to the job.

    Keeps it short for modal display. Returns empty string if unavailable.
    """
    if not (settings.openai_api_key and resume_text.strip()):
        return ""
    
    prompt = (
        "Aşağıdaki özgeçmişi detaylı analiz et ve iş ilanına göre değerlendir. "
        "3-4 paragraf halinde şu bilgileri ver:\n"
        "1. Genel profil özeti (deneyim, eğitim, ana yetkinlikler)\n"
        "2. İş ilanına uygunluk analizi (eşleşen beceriler, eksik alanlar)\n"
        "3. Öne çıkan projeler ve başarılar\n"
        "4. Genel değerlendirme ve öneriler\n\n"
        f"İş İlanı: {job_desc or 'Belirtilmemiş'}\n\n"
        f"Özgeçmiş:\n{resume_text[:4000]}"
    )
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    body = {
        "model": "gpt-4o-mini", 
        "messages": [{"role": "user", "content": prompt}], 
        "temperature": 0.3,
        "max_tokens": 800
    }
    try:
        async with httpx.AsyncClient(timeout=25) as client:
            resp = await client.post("https://api.openai.com/v1/chat/completions", json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            text = str(data["choices"][0]["message"]["content"]).strip()
            # Compress to a concise summary suitable for modal display
            text = re.sub(r"\n{3,}", "\n\n", text)  # collapse excessive blank lines
            text = text.strip()
            if len(text) > 600:
                text = text[:600].rstrip() + "…"
            return text
    except Exception as e:
        # Better error handling for debugging
        import logging
        logging.error(f"CV summary generation failed: {e}")
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
        "İş tanımı, adayın özgeçmişi ve mülakat cevaplarını karşılaştır.\n"
        "ÖNEMLI: Özgeçmişte ZATEN bulunan yetenekleri 'cv_exists' olarak işaretle, mülakat sırasında test edilenleri 'interview_tested' olarak değerlendir.\n"
        "Adayın özgeçmişinde yok ama iş ilanında istenen yetenikleri açıkça 'missing' olarak belirt.\n"
        "JSON formatında döndür:\n"
        "{\n"
        "  \"job_fit_summary\": \"Genel değerlendirme özeti\",\n"
        "  \"cv_existing_skills\": [\"Özgeçmişte zaten bulunan yetenekler\"],\n"
        "  \"interview_demonstrated\": [\"Mülakatta kanıtlanan yetenekler\"],\n"
        "  \"clear_gaps\": [\"Hem özgeçmişte hem mülakattta eksik yetenekler\"],\n"
        "  \"recommendations\": [\"İşe alım önerileri\"],\n"
        "  \"requirements_matrix\": [\n"
        "    {\n"
        "      \"label\": \"Yetenek adı\",\n"
        "      \"meets\": \"yes|partial|no\",\n"
        "      \"source\": \"cv|interview|both|neither\",\n"
        "      \"evidence\": \"Kanıt açıklaması\"\n"
        "    }\n"
        "  ]\n"
        "}\n\n"
        f"İş Tanımı: {job_desc[:4000]}\n"
        f"Özgeçmiş: {(resume_text or '')[:3000]}\n"
        f"Mülakat Cevapları: {transcript_text[:4000]}"
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
    """Return a detailed AI opinion for the candidate including salary analysis.

    Returns JSON with detailed breakdown including salary expectations.
    """
    if not (settings.openai_api_key and (job_desc.strip() and transcript_text.strip())):
        return {}
    prompt = (
        "İş tanımı, özgeçmiş ve mülakat transkriptine göre detaylı işe alım değerlendirmesi yap.\n"
        "Maaş beklentisi sorusu ve cevabını özellikle analiz et.\n"
        "Objektif ve profesyonel ol. Hem güçlü hem zayıf yönleri belirt.\n"
        "JSON formatında döndür:\n"
        "{\n"
        "  \"hire_recommendation\": \"Strong Hire|Hire|Hold|No Hire\",\n"
        "  \"overall_assessment\": \"3-4 cümlelik genel değerlendirme\",\n"
        "  \"key_strengths\": [\"Güçlü yönler listesi\"],\n"
        "  \"key_concerns\": [\"Endişe alanları listesi\"],\n"
        "  \"salary_analysis\": {\n"
        "    \"candidate_expectation\": \"Adayın belirttiği maaş beklentisi\",\n"
        "    \"market_alignment\": \"market_appropriate|too_high|too_low|not_specified\",\n"
        "    \"negotiation_notes\": \"Maaş müzakeresi notları\"\n"
        "  },\n"
        "  \"confidence_score\": 0.8,\n"
        "  \"next_steps\": \"Önerilen sonraki adımlar\"\n"
        "}\n\n"
        f"İş Tanımı: {job_desc[:3500]}\n"
        f"Özgeçmiş: {(resume_text or '')[:2000]}\n"
        f"Mülakat Transkripti: {transcript_text[:4000]}"
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


def _ocr_pdf_bytes_textract(data: bytes) -> str:
    """Best-effort OCR using AWS Textract if credentials exist.

    Returns empty string on any failure.
    """
    try:
        import boto3  # type: ignore
        client = boto3.client("textract")
        resp = client.analyze_document(Document={"Bytes": data}, FeatureTypes=["FORMS"])  # type: ignore
        lines: list[str] = []
        for b in resp.get("Blocks", []):
            if b.get("BlockType") == "LINE" and b.get("Text"):
                lines.append(str(b["Text"]))
        return "\n".join(lines)
    except Exception:
        return ""


def _ocr_image_bytes_textract(data: bytes) -> str:
    """OCR for image files using AWS Textract.
    
    Supports JPG, PNG and other image formats.
    Returns empty string on any failure.
    """
    try:
        import boto3  # type: ignore
        client = boto3.client("textract")
        
        # Use detect_document_text for basic text extraction from images
        resp = client.detect_document_text(Document={"Bytes": data})  # type: ignore
        lines: list[str] = []
        
        for block in resp.get("Blocks", []):
            if block.get("BlockType") == "LINE" and block.get("Text"):
                lines.append(str(block["Text"]))
        
        return "\n".join(lines)
    except Exception as e:
        # Log the error for debugging but don't fail the upload
        print(f"OCR failed for image: {e}")
        return ""


def _parse_json_loose(raw: str) -> dict | None:
    try:
        import json as _json
        return _json.loads(raw)
    except Exception:
        pass
    if not raw:
        return None
    # Strip code fences if present
    try:
        if "```" in raw:
            inner = raw.split("```", 2)
            if len(inner) >= 3:
                content = inner[1]
                # remove optional language tag
                if "\n" in content:
                    content = content.split("\n", 1)[1]
                raw = content
    except Exception:
        pass
    # Find a JSON object by braces balance
    try:
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            snippet = raw[start:end+1]
            import json as _json
            return _json.loads(snippet)
    except Exception:
        return None
    return None


def parse_resume_bytes(data: bytes, content_type: str | None, file_name: str | None = None) -> str:
    ct = (content_type or "").lower().strip()
    name = (file_name or "").lower()
    text = ""
    
    # PDF processing
    if "/pdf" in ct or name.endswith(".pdf"):
        text = _read_pdf_bytes(data)
        if not text or len(text) < 60:
            ocr = _ocr_pdf_bytes_textract(data)
            if ocr and len(ocr) > len(text):
                text = ocr
    
    # DOCX processing
    elif name.endswith(".docx") or "officedocument" in ct:
        text = _read_docx_bytes(data)
    
    # Image processing (JPG, PNG, etc.) - OCR directly
    elif (any(img_type in ct for img_type in ["image/", "/jpeg", "/jpg", "/png", "/tiff", "/bmp"]) or 
          any(name.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp"])):
        print(f"Detected image file: {name} ({ct}), attempting OCR...")
        text = _ocr_image_bytes_textract(data)
        if not text:
            print(f"OCR failed for image, no text extracted")
    
    # Text files and unknown types
    else:
        try:
            text = data.decode("utf-8", errors="ignore")
        except Exception:
            text = ""
    # Normalize whitespace
    normalized = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    # Remove PostgreSQL-incompatible nulls and control chars (except tab/newline handled above)
    try:
        normalized = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", normalized)
    except Exception:
        # As a last resort, drop all null bytes
        normalized = normalized.replace("\x00", "")
    return normalized


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


# --- Candidate field extraction (heuristics; no network) ---

def _extract_first_reasonable_name_line(lines: list[str]) -> str | None:
    """Pick a plausible name line from the first lines of a resume.

    Heuristics: 2-5 tokens, each token starts with uppercase (Turkish supported),
    avoid lines containing email/phone/URL.
    """
    head = lines[:12]
    for ln in head:
        low = ln.lower()
        if any(k in low for k in ("@", "http://", "https://", "linkedin.com", "github.com")):
            continue
        if re.search(r"\d", ln):
            continue
        toks = [t for t in re.split(r"\s+", ln.strip()) if t]
        if 2 <= len(toks) <= 5:
            ok = 0
            for t in toks:
                if re.match(r"^[A-ZÇĞİÖŞÜ][a-zçğıöşü'\-]+$", t):
                    ok += 1
            if ok >= max(2, len(toks) - 1):
                return ln.strip()
    return None


def extract_candidate_fields(resume_text: str, file_name: str | None = None) -> Dict[str, Any]:
    """Extract key candidate fields from plain text resume.

    Returns a JSON-serializable dict, e.g.:
    {
      "name": str|None,
      "email": str|None,
      "phone": str|None,
      "links": {"linkedin": str|None, "github": str|None, "website": str|None},
      "skills": [str],
    }
    """
    text = resume_text or ""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    # Email – prefer best guess (avoid labels like e-posta, trailing tokens)
    def _best_email_local(text_in: str) -> str | None:
        try:
            # Normalize obfuscated styles: "name (at) domain (dot) com", spaces around @ and .
            cleaned = text_in
            # Remove email labels but keep the content
            cleaned = re.sub(r"(?i)\b(e[-\s]?posta|eposta|e[-\s]?mail|email|mail|iletişim|iletişim bilgileri|e[-\s]?mail adresi|mail adresi)\s*[:：]\s*", " ", cleaned)
            # Replace (at)/[at]/ at → @ (but not random "et" in Turkish names!)
            cleaned = re.sub(r"(?i)\s*(\(|\[)\s*(?:at|et)\s*(\)|\])\s*", "@", cleaned)  # Only bracketed
            cleaned = re.sub(r"(?i)\b\s+at\s+\b", "@", cleaned)  # Only standalone " at "
            # Replace dot/nokta → .
            cleaned = re.sub(r"(?i)\s*(?:dot|nokta)\s*", ".", cleaned)
            # Collapse spaces around @ and .
            cleaned = re.sub(r"\s*@\s*", "@", cleaned)
            cleaned = re.sub(r"\s*\.\s*", ".", cleaned)
            # Remove zero-width and control
            cleaned = re.sub(r"[\u200B\x00-\x1F]", "", cleaned)

            # Collect candidates (allow leading letter for user)
            raw_cands = re.findall(r"(?<![A-Za-z0-9._%+-])[A-Za-z][A-Za-z0-9._%+-]*@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?:\.[A-Za-z]{2,})?(?![A-Za-z0-9._%+-])", cleaned)
            if not raw_cands:
                return None

            def normalize_domain(dom: str) -> str:
                low = dom.lower()
                # If contains known tlds inside (e.g., gmail.comdo), cut after the last known tld
                known = [".com.tr", ".net.tr", ".org.tr", ".com", ".net", ".org", ".edu", ".gov", ".io", ".co", ".tr"]
                for t in known:
                    if t in low:
                        idx = low.rfind(t)
                        return dom[: idx + len(t)]
                return dom

            cands: list[str] = []
            for e in raw_cands:
                try:
                    user, dom = e.split("@", 1)
                    dom = normalize_domain(dom)
                    e2 = f"{user}@{dom}"
                    cands.append(e2)
                except Exception:
                    continue

            if not cands:
                return None

            # Score
            def score(e: str) -> tuple[int, int, int, int]:
                user, dom = e.split("@", 1)
                bad = int(any(k in user.lower() for k in ["posta", "eposta", "mail", "noreply", "no-reply"]))
                tld_known = int(any(dom.lower().endswith(t) for t in [
                    ".com", ".com.tr", ".net", ".org", ".io", ".co", ".edu", ".gov", ".tr"
                ]))
                common = int(any(dom.lower().endswith(d) for d in ["gmail.com", "outlook.com", "hotmail.com", "yahoo.com", "yandex.com"]))
                # Prefer shorter, simpler usernames
                simple_user = int(user.count(".") <= 1 and user.count("_") <= 1 and not re.search(r"\d{3,}", user))
                return (tld_known + common, simple_user, 1 - bad, -len(user))

            cands = sorted(set(cands), key=score, reverse=True)
            return cands[0]
        except Exception:
            return None
    # Email extraction via heuristics (fallback when LLM unavailable)
    email = _best_email_local(text)

    # Phone heuristic baseline; LLM result will override in smart path
    phone = _best_phone_tr(text) if '_best_phone_tr' in globals() else None

    # Links - improved LinkedIn detection
    linkedin_patterns = [
        r"https?://(?:www\.)?linkedin\.com/[A-Za-z0-9_\-/]+",  # Full URL
        r"linkedin\.com/[A-Za-z0-9_\-/]+",  # Domain with path
        r"(?i)linkedin\s*[:;]\s*([A-Za-z0-9_\-/]+)",  # "LinkedIn: username" format
        r"(?i)(?:linkedin|li)\s*[-:]\s*([A-Za-z0-9_\-]+)",  # "LinkedIn - username" or "LI: username"
    ]
    
    linkedin_url = None
    for pattern in linkedin_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            found = match.group(0)
            # Normalize to full URL
            if not found.startswith("http"):
                if "linkedin.com" in found:
                    linkedin_url = "https://" + found
                else:
                    # Extract just the username/handle
                    username = match.group(1) if match.lastindex else found.split()[-1]
                    linkedin_url = f"https://www.linkedin.com/in/{username}"
            else:
                linkedin_url = found
            break
    
    m_github = re.search(r"https?://(?:www\.)?github\.com/[A-Za-z0-9_\-/]+", text, re.IGNORECASE)
    # A generic site (skip linkedin/github duplicates)
    site = None
    urls = re.findall(r"https?://[^\s)]+", text)
    for u in urls:
        if ("linkedin.com" in u.lower()) or ("github.com" in u.lower()):
            continue
        site = u
        break

    # Skills (known tech tokens)
    skills = extract_known_technologies_from_resume(text, max_items=24)

    # Name guess helpers
    def _guess_name_from_email(em: str | None) -> str | None:
        if not em or "@" not in em:
            return None
        user = em.split("@", 1)[0]
        user = re.sub(r"\d+", " ", user)
        parts = [p for p in re.split(r"[._-]+", user) if len(p) >= 2]
        parts = [p for p in parts if p.lower() not in {"mail", "eposta", "email"}]
        if 1 <= len(parts) <= 4:
            return " ".join(w.capitalize() for w in parts)
        return None

    def _guess_name_from_header(all_lines: list[str]) -> str | None:
        # Look for 2–4 token lines likely to be a name; accept ALL CAPS
        ban = {
            "cv", "özgeçmiş", "ozgecmis", "resume", "iletişim", "egitim", "eğitim", "deneyim",
            "is", "iş", "yetenek", "diller", "referans", "kişisel", "kisisel", "bilgiler",
            "hakkımda", "hakkinda", "özet", "ozet", "projeler", "sertifika", "sertifikalar",
            "kariyer", "tecrübe", "tecrube", "iletişim bilgileri", "contact", "summary"
        }
        best: tuple[int, str] | None = None
        for idx, ln in enumerate(all_lines[:120]):
            ln_stripped = ln.strip()
            if not (3 <= len(ln_stripped) <= 60):
                continue
            toks = [t for t in re.split(r"\s+", ln_stripped) if t]
            if not (2 <= len(toks) <= 4):
                continue
            low = ln_stripped.lower()
            if any(b in low for b in ban):
                continue
            # accept ALL CAPS tokens as well
            good = 0
            for t in toks:
                if re.match(r"^[A-ZÇĞİÖŞÜ][a-zçğıöşü'\-]+$", t):
                    good += 1
                elif re.match(r"^[A-ZÇĞİÖŞÜ]{2,}$", t):
                    good += 1
            if good >= max(2, len(toks) - 1):
                # score earlier lines higher
                score = max(0, 120 - idx)
                cand = " ".join(w.capitalize() for w in toks)
                if not best or score > best[0]:
                    best = (score, cand)
        return best[1] if best else None

    # Name guess: prefer explicit label lines first (scan whole doc)
    name_guess = None
    try:
        for ln in lines:
            m = re.search(r"(?i)^(ad[ıi] soyad[ıi]|ad[ıi]\s*[-:]\s*|name\s*[-:]\s*|full\s*name\s*[-:]\s*|i?sim\s*[-:]\s*)(.+)$", ln)
            if m:
                cand = m.group(2).strip()
                # Strip trailing non-letters and leading colon/dash
                cand = re.sub(r"^[-:\s]+", "", cand)
                cand = re.sub(r"[^A-Za-zÇĞİÖŞÜçğıöşü'\- ]+$", "", cand)
                if 3 <= len(cand) <= 80:
                    name_guess = cand
                    break
    except Exception:
        name_guess = None
    if not name_guess:
        # Try header-like lines (ALL CAPS allowed)
        name_guess = _guess_name_from_header(lines)
    if not name_guess:
        # Try email user part
        name_guess = _guess_name_from_email(email)
    if not name_guess:
        name_guess = _extract_first_reasonable_name_line(lines)
    if not name_guess and file_name:
        base = (file_name or "").rsplit(".", 1)[0]
        base = base.replace("_", " ").replace("-", " ").strip()
        # Avoid generic names like "cv", "özgeçmiş", numeric-only
        low = base.lower()
        generic_tokens = {
            "cv", "özgeçmiş", "ozgecmis", "resume", "kişisel", "kisisel", "bilgiler",
            "devam", "ik", "adres", "document", "dokuman", "doküman", "güncel", "guncel",
            "basvuru", "başvuru", "kullanici", "user", "curriculum", "vitae", "eğitim",
            "egitim", "deneyim", "portfolio", "profil", "profile", "son", "yeni", "final",
            "latest", "updated", "new", "version", "ver", "v", "copy", "kopya"
        }
        # Also avoid filenames with too many numbers or special characters
        has_numbers = bool(re.search(r"\d{2,}", base))  # 2+ consecutive digits
        has_special = bool(re.search(r"[()[\]{}@#$%^&*+=|\\/<>]", base))
        too_generic = any(k in low for k in generic_tokens)
        
        if not too_generic and not has_numbers and not has_special and 2 <= len(base.split()) <= 5:
            name_guess = base.title()[:255]

    return {
        "name": name_guess,
        "email": email,
        "phone": phone,
        "links": {
            "linkedin": linkedin_url,
            "github": m_github.group(0) if m_github else None,
            "website": site,
        },
        "skills": skills,
    }


# --- Smart extractor (LLM if available; fallback to heuristics) ---

def _pick_best_email(*candidates: str | None, from_text: str | None = None) -> str | None:
    vals: list[str] = []
    for c in candidates:
        if isinstance(c, str) and c:
            vals.append(c.strip())
    # Also collect from text via regex
    if from_text:
        found = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", from_text)
        vals.extend(found)
    if not vals:
        return None
    # Prefer known TLDs and domains
    preferred_tlds = {"com", "net", "org", "io", "co", "edu", "gov", "tr", "com.tr", "net.tr", "org.tr"}
    def score(email: str) -> tuple[int, int]:
        try:
            domain = email.split("@", 1)[1].lower()
            # handle two-level tld
            parts = domain.rsplit(".", 2)
            tld = ".".join(parts[1:]) if len(parts) >= 2 else ""
            second = parts[-1] if parts else ""
            known = int(tld in preferred_tlds or second in preferred_tlds)
            has_common = int(any(x in domain for x in ["gmail.com", "outlook.com", "yahoo.com"]))
            return (known, has_common)
        except Exception:
            return (0, 0)
    vals_sorted = sorted(set(vals), key=lambda e: score(e), reverse=True)
    # Basic sanity: ensure only ascii control-free
    for v in vals_sorted:
        if re.search(r"[\x00-\x1F\x7F]", v):
            continue
        return v
    return vals_sorted[0] if vals_sorted else None


async def extract_candidate_fields_smart(resume_text: str, file_name: str | None = None) -> Dict[str, Any]:
    text = (resume_text or "").strip()
    if not text:
        return extract_candidate_fields(resume_text, file_name)
    # If OpenAI key exists, attempt LLM extraction
    if settings.openai_api_key:
        headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
        schema = (
            "Sadece JSON döndür. {\n"
            "  \"name\": str|null, \"email\": str|null, \"phone\": str|null,\n"
            "  \"links\": {\"linkedin\": str|null, \"github\": str|null, \"website\": str|null},\n"
            "  \"skills\": [str]\n"
            "}"
        )
        def _make_prompt(snippet: str) -> str:
            return (
                "Aşağıdaki özgeçmiş metninden SADECE ADAYIN kendi iletişim bilgilerini çıkar. "
                + schema +
                "\nKURALLAR: Tahmin etme, emin değilsen null yaz. E-posta ve LinkedIn tam adres olsun. Türkçe karakterleri koru. "
                "Referanslar/şirket/okul kişilerine ait e-posta/telefonları ASLA alma. 'Referans', 'Refere', 'Hoca', 'Müdür', 'Danışman' bölümlerini yok say.\n"
                f"METİN:\n{snippet}"
            )
        # Chunk the text - smaller chunks for better stability
        max_chunk = 8000  # Reduced from 20000 for better rate limiting
        chunks: list[str] = []
        if len(text) <= max_chunk:
            chunks = [text]
        else:
            lines = text.splitlines()
            cur = ""
            for ln in lines:
                if len(cur) + len(ln) + 1 > max_chunk:
                    chunks.append(cur)
                    cur = ln
                else:
                    cur = (cur + "\n" + ln) if cur else ln
            if cur:
                chunks.append(cur)
            # limit to first 2 chunks to reduce API calls
            chunks = chunks[:2]
        results: list[Dict[str, Any]] = []
        try:
            import logging as _log
            async with httpx.AsyncClient(timeout=30) as client:  # Reduced timeout
                for ck in chunks:
                    body = {
                        "model": "gpt-4o-mini",  # More stable, faster, less rate limiting
                        "messages": [{"role": "user", "content": _make_prompt(ck)}],
                        "temperature": 0.0,
                        "response_format": {"type": "json_object"},
                    }
                    # Simple retry mechanism for rate limits
                    for attempt in range(2):  # Max 2 attempts
                        try:
                            resp = await client.post("https://api.openai.com/v1/chat/completions", json=body, headers=headers)
                            resp.raise_for_status()
                            data = resp.json()
                            import json as _json
                            raw = data.get("choices", [{}])[0].get("message", {}).get("content")
                            obj = _parse_json_loose(raw)
                            if isinstance(obj, dict):
                                results.append(obj)
                            break  # Success, exit retry loop
                        except Exception as e:
                            if attempt == 0 and "429" in str(e):  # Rate limit on first attempt
                                _log.getLogger(__name__).info("Rate limit hit, retrying with delay...")
                                import asyncio
                                await asyncio.sleep(2)  # Wait 2 seconds
                                continue
                            else:
                                _log.getLogger(__name__).warning("LLM extraction failed on chunk", exc_info=True)
                                break  # Give up
        except Exception:
            results = []
        # Check if we have valid results from LLM
        valid_results = [r for r in results if isinstance(r, dict) and any(r.values())]
        
        if valid_results:
            print(f"LLM extraction succeeded with {len(valid_results)} valid chunk(s), merging results...")
            merged: Dict[str, Any] = {"name": None, "email": None, "phone": None, "links": {"linkedin": None, "github": None, "website": None}, "skills": []}
            names: list[str] = []
            emails: list[str] = []
            phones: list[str] = []
            links_all = {"linkedin": [], "github": [], "website": []}
            skills_all: set[str] = set()
            for r in valid_results:
                n = r.get("name"); e = r.get("email"); p = r.get("phone"); l = r.get("links") or {}
                if isinstance(n, str) and len(n.strip()) >= 3:
                    names.append(n.strip())
                if isinstance(e, str):
                    emails.append(e.strip())
                if isinstance(p, str):
                    phones.append(p.strip())
                for k in links_all:
                    v = l.get(k)
                    if isinstance(v, str) and v:
                        links_all[k].append(v)
                sk = r.get("skills") or []
                if isinstance(sk, list):
                    for s in sk:
                        if isinstance(s, str) and s:
                            skills_all.add(s)
            
            # Use heuristics as fallback for missing LLM fields
            heuristic_result = extract_candidate_fields(text, file_name)
            
            # pick best email: prefer LLM majority; fallback to heuristics
            email_re = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?:\.[A-Za-z]{2,})?")
            valid_llm_emails = [e for e in emails if email_re.search(e or "")]
            best_email = None
            if valid_llm_emails:
                counts: Dict[str, int] = {}
                for e in valid_llm_emails:
                    counts[e] = counts.get(e, 0) + 1
                best_email = sorted(counts.items(), key=lambda x: x[1], reverse=True)[0][0]
            merged["email"] = best_email or heuristic_result.get("email")
            
            # pick best name – majority vote else heuristics
            def _normalize_name(nm: str) -> str:
                nm = re.sub(r"\s+", " ", nm).strip()
                return nm
            name_vote: Dict[str, int] = {}
            for nm in names:
                key = _normalize_name(nm)
                name_vote[key] = name_vote.get(key, 0) + 1
            picked_name = None
            if name_vote:
                picked_name = sorted(name_vote.items(), key=lambda x: (x[1], len(x[0])), reverse=True)[0][0]
            merged["name"] = picked_name or heuristic_result.get("name")
            
            # phone: prefer heuristics (more reliable for TR numbers)
            merged["phone"] = heuristic_result.get("phone")
            
            # linkedin: combine LLM and heuristic results
            linkedin_from_llm = None
            for k in links_all:
                if k == "linkedin" and links_all[k]:
                    linkedin_from_llm = links_all[k][0]
                    break
            
            github_from_llm = links_all.get("github", [])
            website_from_llm = links_all.get("website", [])
            
            merged["links"] = {
                "linkedin": linkedin_from_llm or heuristic_result.get("links", {}).get("linkedin"),
                "github": (github_from_llm[0] if github_from_llm else None) or heuristic_result.get("links", {}).get("github"),
                "website": (website_from_llm[0] if website_from_llm else None) or heuristic_result.get("links", {}).get("website")
            }
            merged["skills"] = sorted(skills_all)[:24] or heuristic_result.get("skills", [])
            return merged
    # Fallback to local heuristic extractor when LLM completely fails
    print(f"LLM extraction failed completely, falling back to heuristics for file: {file_name}")
    return extract_candidate_fields(resume_text, file_name)

