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
    """Return a concise CV summary tailored to the job.

    Returns structured summary that's comprehensive but readable. Returns empty string if unavailable.
    """
    if not (settings.openai_api_key and resume_text.strip()):
        return ""
    
    prompt = (
        "Aşağıdaki özgeçmişi analiz et ve iş ilanına göre öz bir değerlendirme yap. "
        "Maksimum 4-5 cümle ile şu bilgileri ver:\n\n"
        "📋 **Profil Özeti**: Deneyim seviyesi, ana uzmanlık alanları ve eğitim durumu\n"
        "🎯 **İş Uygunluğu**: İlan gereksinimlerine uygunluk ve öne çıkan yetenekler\n"
        "🚀 **Öne Çıkan Başarılar**: En dikkat çekici proje/deneyim (varsa)\n"
        "💡 **Genel Değerlendirme**: Kısa bir işe alım önerisi\n\n"
        "Türkçe ve profesyonel bir dil kullan. Çok uzun olmasın, öz ve net ol.\n\n"
        f"İş İlanı: {job_desc or 'Belirtilmemiş'}\n\n"
        f"Özgeçmiş:\n{resume_text[:4000]}"
    )
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    body = {
        "model": "gpt-4o-mini", 
        "messages": [{"role": "user", "content": prompt}], 
        "temperature": 0.3,
        "max_tokens": 500
    }
    try:
        async with httpx.AsyncClient(timeout=25) as client:
            resp = await client.post("https://api.openai.com/v1/chat/completions", json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            text = str(data["choices"][0]["message"]["content"]).strip()
            # Clean up formatting
            text = re.sub(r"\n{3,}", "\n\n", text)  # collapse excessive blank lines
            text = text.strip()
            # No hard truncation - let LLM follow the instruction to be concise
            return text
    except Exception as e:
        # Better error handling for debugging
        import logging
        logging.error(f"CV summary generation failed: {e}")
        return ""


async def assess_hr_criteria(transcript_text: str) -> Dict[str, Any]:
    """Score broad HR criteria using structured prompts with evidence-based scoring.

    Returns: { criteria: [{label, score_0_100, evidence, confidence, reasoning}], summary, meta }
    """
    if not (settings.openai_api_key and transcript_text.strip()):
        return {}
    
    prompt = f"""Sen deneyimli bir HR uzmanısın. Aşağıdaki mülakat transkriptini analiz et ve her kriter için objektif, kanıta dayalı değerlendirme yap.

DEĞERLENDIRME KRİTERLERİ:
1. İletişim Netliği (0-100): Açık ifade, yapılandırılmış cevaplar, dinleme becerisi
2. Problem Çözme (0-100): Analitik düşünme, çözüm odaklılık, yaratıcılık
3. Takım Çalışması (0-100): Birlikte çalışma örnekleri, işbirliği, çatışma yönetimi
4. Liderlik (0-100): İnisiyatif alma, yönlendirme, sorumluluk üstlenme
5. Büyüme Zihniyeti (0-100): Öğrenme isteği, hatalardan ders alma, gelişim odaklılık

PUANLAMA REHBERİ:
- 90-100: Mükemmel, çok güçlü kanıtlar
- 80-89: Güçlü, net pozitif örnekler
- 70-79: İyi, bazı pozitif göstergeler
- 60-69: Orta, sınırlı kanıt
- 50-59: Zayıf, minimal kanıt
- 0-49: Yetersiz, kanıt yok veya negatif

ZORUNLU JSON FORMAT:
{{
  "criteria": [
    {{
      "label": "İletişim Netliği",
      "score_0_100": 85,
      "evidence": "Sorulara yapılandırılmış ve net cevaplar verdi. 'STAR yöntemi ile...' gibi örnekler kullandı.",
      "confidence": 0.9,
      "reasoning": "3 farklı örnekte net açıklama ve somut detaylar sağladı."
    }}
  ],
  "summary": "Genel HR değerlendirme özeti",
  "overall_score": 78.5,
  "meta": {{
    "total_response_time": "18 dakika",
    "answer_depth": "orta",
    "evidence_quality": "güçlü"
  }}
}}

MÜLAKAT TRANSKRİPTİ:
{transcript_text[:6000]}"""

    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    body = {
        "model": "gpt-4o-mini", 
        "messages": [{"role": "user", "content": prompt}], 
        "temperature": 0.05,
        "response_format": {"type": "json_object"}
    }
    try:
        async with httpx.AsyncClient(timeout=35) as client:
            resp = await client.post("https://api.openai.com/v1/chat/completions", json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            import json as _json
            result = _json.loads(data["choices"][0]["message"]["content"])
            
            # Validate and normalize result
            if not isinstance(result.get("criteria"), list):
                return {}
            
            # Ensure all criteria have required fields
            for criterion in result["criteria"]:
                criterion.setdefault("confidence", 0.5)
                criterion.setdefault("reasoning", "")
                
            return result
    except Exception:
        return {}


async def assess_job_fit(job_desc: str, transcript_text: str, resume_text: str | None = None) -> Dict[str, Any]:
    """Enhanced job-fit analysis with detailed requirement mapping and confidence scoring."""
    if not (settings.openai_api_key and (job_desc.strip() and transcript_text.strip())):
        return {}
    
    prompt = f"""Sen senior bir işe alım uzmanısın. İş tanımı, özgeçmiş ve mülakat transkriptini detaylı analiz et.

GÖREV: Her iş gereksinimini adayın profiliyle eşleştir ve kanıt seviyesini değerlendir.

KAYNAK TIPLERI:
- cv: Özgeçmişte yazılı/belgelenmiş
- interview: Mülakatta sözlü olarak kanıtlanmış  
- both: Hem özgeçmişte hem mülakatta teyit edilmiş
- neither: Hiçbirinde kanıt yok

KARŞILAMA SEVİYELERİ:
- yes: Tam olarak karşılıyor (güçlü kanıt)
- partial: Kısmen karşılıyor (sınırlı kanıt)
- no: Karşılamıyor (kanıt yok)

ZORUNLU JSON FORMAT:
{{
  "job_fit_summary": "3-4 cümlelik genel değerlendirme",
  "overall_fit_score": 0.75,
  "cv_existing_skills": ["Özgeçmişte net olan yetenekler"],
  "interview_demonstrated": ["Mülakatta kanıtlanan yetenekler"],
  "clear_gaps": ["Açık eksiklik gösteren alanlar"],
  "requirements_matrix": [
    {{
      "label": "Spesifik yetenek/gereksinim",
      "meets": "yes|partial|no",
      "source": "cv|interview|both|neither",
      "evidence": "Somut kanıt/örnek (özgeçmiş satırı veya mülakat cevabı)",
      "confidence": 0.9,
      "importance": "high|medium|low"
    }}
  ],
  "recommendations": [
    "Spesifik işe alım önerisi 1",
    "Gelişim alanı önerisi 2"
  ],
  "risk_factors": ["Potansiyel risk alanları"],
  "competitive_advantages": ["Adayın öne çıkan artıları"]
}}

İŞ TANIMI:
{job_desc[:4500]}

ÖZGEÇMIŞ:
{(resume_text or 'Özgeçmiş bilgisi mevcut değil')[:3500]}

MÜLAKAT TRANSKRİPTİ:
{transcript_text[:4500]}"""

    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    body = {
        "model": "gpt-4o-mini", 
        "messages": [{"role": "user", "content": prompt}], 
        "temperature": 0.1,
        "response_format": {"type": "json_object"}
    }
    try:
        async with httpx.AsyncClient(timeout=40) as client:
            resp = await client.post("https://api.openai.com/v1/chat/completions", json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            import json as _json
            result = _json.loads(data["choices"][0]["message"]["content"])
            
            # Validate and normalize
            if not isinstance(result.get("requirements_matrix"), list):
                result["requirements_matrix"] = []
            
            # Add confidence defaults
            for req in result.get("requirements_matrix", []):
                req.setdefault("confidence", 0.5)
                req.setdefault("importance", "medium")
                
            result.setdefault("overall_fit_score", 0.0)
            return result
    except Exception:
        return {}


async def opinion_on_candidate(job_desc: str, transcript_text: str, resume_text: str | None = None) -> Dict[str, Any]:
    """Enhanced hiring decision analysis with structured recommendations and risk assessment."""
    if not (settings.openai_api_key and (job_desc.strip() and transcript_text.strip())):
        return {}
    
    prompt = f"""Sen deneyimli bir CTO ve hiring manager'sın. İş tanımı, özgeçmiş ve mülakat transkriptine göre yapılandırılmış işe alım kararı ver.

GÖREV: Objektif, veri-destekli ve uygulama-odaklı karar analizi yap.

DEĞERLENDIRME ÇERÇEVESİ:
1. Teknik yeterlilik (iş gereksinimleri vs aday profili)
2. Yumuşak beceriler (takım uyumu, iletişim, liderlik)
3. Büyüme potansiyeli (öğrenme hızı, adaptasyon)
4. Kültürel uyum (şirket değerleri, çalışma tarzı)
5. Risk faktörleri (kırmızı bayraklar, endişe alanları)

HİRE RECOMMENDATİON SEVİYELERİ:
- Strong Hire: Kesinlikle işe alınmalı, role mükemmel uyum
- Hire: İşe alınmalı, gereksinimleri karşılıyor
- Hold: Kararsız, ek bilgi/mülakat gerekli
- No Hire: İşe alınmamalı, önemli eksiklikler var

ZORUNLU JSON FORMAT:
{{
  "hire_recommendation": "Strong Hire|Hire|Hold|No Hire",
  "overall_assessment": "4-5 cümlelik yapılandırılmış genel değerlendirme",
  "decision_confidence": 0.85,
  "key_strengths": [
    "Spesifik güçlü yön 1 (kanıtla)",
    "Spesifik güçlü yön 2 (kanıtla)"
  ],
  "key_concerns": [
    "Spesifik endişe 1 (gerekçeyle)",
    "Spesifik endişe 2 (gerekçeyle)"
  ],
  "skill_match": {{
    "technical_fit": 0.8,
    "soft_skills_fit": 0.7,
    "cultural_fit": 0.9,
    "growth_potential": 0.8
  }},
  "salary_analysis": {{
    "candidate_expectation": "Adayın maaş beklentisi (varsa)",
    "market_alignment": "market_appropriate|too_high|too_low|belirtilmedi",
    "recommended_range": "Önerilen maaş aralığı",
    "negotiation_notes": "Maaş müzakeresi stratejisi"
  }},
  "risk_factors": [
    "Potansiyel risk 1",
    "Potansiyel risk 2"
  ],
  "mitigation_strategies": [
    "Risk azaltma önerisi 1",
    "Risk azaltma önerisi 2"
  ],
  "next_steps": [
    "Önerilen sonraki adım 1",
    "Önerilen sonraki adım 2"
  ],
  "timeline_recommendation": "immediate|1_week|2_weeks|reassess"
}}

İŞ TANIMI:
{job_desc[:4000]}

ÖZGEÇMIŞ:
{(resume_text or 'Özgeçmiş bilgisi mevcut değil')[:2500]}

MÜLAKAT TRANSKRİPTİ:
{transcript_text[:4500]}"""

    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    body = {
        "model": "gpt-4o-mini", 
        "messages": [{"role": "user", "content": prompt}], 
        "temperature": 0.05,
        "response_format": {"type": "json_object"}
    }
    try:
        async with httpx.AsyncClient(timeout=35) as client:
            resp = await client.post("https://api.openai.com/v1/chat/completions", json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            import json as _json
            result = _json.loads(data["choices"][0]["message"]["content"])
            
            # Validate and set defaults
            result.setdefault("decision_confidence", 0.5)
            result.setdefault("timeline_recommendation", "reassess")
            
            skill_match = result.setdefault("skill_match", {})
            skill_match.setdefault("technical_fit", 0.5)
            skill_match.setdefault("soft_skills_fit", 0.5)
            skill_match.setdefault("cultural_fit", 0.5)
            skill_match.setdefault("growth_potential", 0.5)
            
            return result
    except Exception:
        return {}


# --- PHASE 2: ENHANCED MULTI-PASS ANALYSIS ---

async def analyze_interview_multipass(job_desc: str, transcript_text: str, resume_text: str | None = None) -> Dict[str, Any]:
    """Comprehensive multi-pass interview analysis with evidence extraction and confidence scoring.
    
    Pass 1: Technical assessment  
    Pass 2: Behavioral evaluation
    Pass 3: Cultural fit and growth mindset
    Pass 4: Evidence synthesis and final scoring
    """
    if not (settings.openai_api_key and transcript_text.strip()):
        return {}
    
    # Pass 1: Technical Assessment
    technical_prompt = f"""Sen senior bir teknik lead'sin. Sadece teknik yetkinlik odağında mülakat analizi yap.

ODAK ALANLARI:
- Problem çözme yaklaşımı ve teknik düşünce süreci
- Teknoloji bilgisi ve uygulamada derinlik  
- Kod kalitesi, mimari anlayışı, best practices
- Debugging, testing, performans optimizasyonu

ZORUNLU JSON FORMAT:
{{
  "technical_score": 0.75,
  "problem_solving_score": 0.8,
  "technology_depth": 0.7,
  "architecture_understanding": 0.6,
  "evidence_items": [
    {{
      "category": "problem_solving",
      "evidence": "STAR formatında somut örnek",
      "strength_level": "strong|moderate|weak",
      "technical_depth": "senior|mid|junior"
    }}
  ],
  "technical_gaps": ["Eksik olan teknik alanlar"],
  "standout_skills": ["Öne çıkan teknik beceriler"],
  "confidence": 0.85
}}

İŞ GEREKSİNİMLERİ:
{job_desc[:3000]}

MÜLAKAT TRANSKRİPTİ:
{transcript_text[:5000]}"""

    # Pass 2: Behavioral Evaluation  
    behavioral_prompt = f"""Sen experienced bir behavioral interviewer'sın. Sadece davranışsal yetkinlikleri değerlendir.

ODAK ALANLARI:
- Liderlik ve takım çalışması deneyimleri
- Çatışma yönetimi ve iletişim becerileri
- Stres altında performans ve adaptasyon
- Motivasyon kaynakları ve career vision

ZORUNLU JSON FORMAT:
{{
  "leadership_score": 0.7,
  "teamwork_score": 0.8,
  "communication_score": 0.9,
  "adaptability_score": 0.6,
  "behavioral_evidence": [
    {{
      "competency": "leadership|teamwork|communication|adaptability",
      "situation": "Durum açıklaması",
      "action": "Adayın aldığı aksiyonlar", 
      "result": "Ölçülebilir sonuç",
      "star_completeness": 0.9
    }}
  ],
  "red_flags": ["Davranışsal kırmızı bayraklar"],
  "behavioral_strengths": ["Güçlü davranışsal özellikler"],
  "confidence": 0.8
}}

MÜLAKAT TRANSKRİPTİ:
{transcript_text[:5000]}"""

    # Pass 3: Cultural Fit & Growth Mindset
    cultural_prompt = f"""Sen kültür ve değerler uzmanısın. Adayın şirket kültürü uyumu ve büyüme potansiyelini değerlendir.

ODAK ALANLARI:
- Öğrenme isteği ve merak seviyesi
- Feedback alma ve verme yaklaşımı
- Başarısızlık ve hatalardan öğrenme
- Değer uyumu ve motivasyon faktörleri

ZORUNLU JSON FORMAT:
{{
  "cultural_fit_score": 0.8,
  "growth_mindset_score": 0.7,
  "learning_agility": 0.9,
  "feedback_openness": 0.6,
  "cultural_indicators": [
    {{
      "value_area": "learning|collaboration|innovation|ownership",
      "alignment": "strong|moderate|weak",
      "evidence": "Spesifik örnek/cevap",
      "growth_potential": "high|medium|low"
    }}
  ],
  "motivation_drivers": ["Temel motivasyon faktörleri"],
  "potential_concerns": ["Kültürel uyum endişeleri"],
  "confidence": 0.75
}}

MÜLAKAT TRANSKRİPTİ:
{transcript_text[:5000]}"""

    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    
    try:
        results = {}
        
        # Execute all passes in parallel for efficiency
        import asyncio
        
        async def run_pass(prompt_name: str, prompt: str):
            body = {
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "response_format": {"type": "json_object"}
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post("https://api.openai.com/v1/chat/completions", json=body, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                import json as _json
                return prompt_name, _json.loads(data["choices"][0]["message"]["content"])
        
        # Run all passes concurrently
        tasks = [
            run_pass("technical", technical_prompt),
            run_pass("behavioral", behavioral_prompt), 
            run_pass("cultural", cultural_prompt)
        ]
        
        pass_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect successful results
        for result in pass_results:
            if isinstance(result, tuple):
                pass_name, pass_data = result
                results[pass_name] = pass_data
        
        # Synthesize final comprehensive result
        synthesis = {
            "multipass_analysis": results,
            "overall_scores": {
                "technical": results.get("technical", {}).get("technical_score", 0.5),
                "behavioral": results.get("behavioral", {}).get("communication_score", 0.5), 
                "cultural": results.get("cultural", {}).get("cultural_fit_score", 0.5)
            },
            "evidence_summary": {
                "technical_evidence": results.get("technical", {}).get("evidence_items", []),
                "behavioral_evidence": results.get("behavioral", {}).get("behavioral_evidence", []),
                "cultural_evidence": results.get("cultural", {}).get("cultural_indicators", [])
            },
            "aggregate_confidence": sum([
                results.get("technical", {}).get("confidence", 0.5),
                results.get("behavioral", {}).get("confidence", 0.5), 
                results.get("cultural", {}).get("confidence", 0.5)
            ]) / 3,
            "analysis_completeness": len(results) / 3  # How many passes succeeded
        }
        
        return synthesis
        
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

