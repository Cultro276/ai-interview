"""
ComprehensiveAnalyzer - Unified analysis engine
Replaces scattered nlp.py functions with batched, efficient analysis
"""

from __future__ import annotations
import asyncio
import json
import hashlib
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum

from src.services.llm_client import get_llm_client, LLMRequest, generate_json


class AnalysisType(str, Enum):
    HR_CRITERIA = "hr_criteria"
    JOB_FIT = "job_fit"
    HIRING_DECISION = "hiring_decision"
    CANDIDATE_PROFILE = "candidate_profile"
    SOFT_SKILLS = "soft_skills"
    REQUIREMENTS_EXTRACTION = "requirements_extraction"


@dataclass
class AnalysisInput:
    """Input data for comprehensive analysis"""
    job_description: str = ""
    transcript_text: str = ""
    resume_text: str = ""
    candidate_name: str = ""
    job_title: str = ""
    analysis_types: Optional[List[AnalysisType]] = None
    
    def __post_init__(self):
        if self.analysis_types is None:
            self.analysis_types = [
                AnalysisType.HR_CRITERIA,
                AnalysisType.JOB_FIT,
                AnalysisType.HIRING_DECISION
            ]


class ComprehensiveAnalyzer:
    """
    Unified analyzer that replaces scattered nlp.py functions
    Uses batched LLM calls for efficiency
    """
    
    def __init__(self):
        self.llm_client = get_llm_client()
    
    # --- Heuristic transcript metrics and objective penalties ---
    def _extract_candidate_utterances(self, transcript: str) -> List[str]:
        """Extract candidate utterances from transcript built as "Interviewer:"/"Candidate:" lines.
        Falls back to treating entire transcript as candidate if markers not found.
        """
        if not transcript:
            return []
        lines = [l.strip() for l in transcript.splitlines() if l.strip()]
        out: List[str] = []
        for line in lines:
            # Turkish and English markers
            if line.lower().startswith("candidate:") or line.lower().startswith("aday:"):
                out.append(line.split(":", 1)[1].strip() if ":" in line else line)
        if not out:
            # Fallback: try to split paragraphs and assume alternate turns
            parts = [p.strip() for p in transcript.split("\n\n") if p.strip()]
            # take every second part as candidate (best-effort)
            out = [p for i, p in enumerate(parts) if i % 2 == 1]
        return out

    def _compute_transcript_metrics(self, transcript: str) -> Dict[str, float]:
        """Compute simple robustness metrics that correlate with poor answers.
        - avg_answer_len_words
        - short_answer_ratio (answers <= 6 words)
        - filler_per_100_words
        - negative_phrase_count
        """
        import re
        answers = self._extract_candidate_utterances(transcript)
        if not answers:
            return {
                "avg_answer_len_words": 0.0,
                "short_answer_ratio": 1.0,
                "filler_per_100_words": 0.0,
                "negative_phrase_count": 0.0,
            }
        # Normalize text
        total_words = 0
        short = 0
        filler_words = ["şey", "hani", "yani", "ıı", "ee", "falan", "işte"]
        negative_phrases = [
            "bilmiyorum", "emin değilim", "hiç", "yok", "yapmadım", "deneyimim yok",
            "hatırlamıyorum", "zorlandım", "beceremedim", "iptal", "başaramadım",
        ]
        filler_count = 0
        neg_count = 0
        for a in answers:
            # strip punctuation for counting
            toks = re.findall(r"\w+", a.lower())
            wc = len(toks)
            total_words += wc
            if wc <= 6:
                short += 1
            # filler and negative counts
            for f in filler_words:
                filler_count += a.lower().count(f)
            for n in negative_phrases:
                neg_count += a.lower().count(n)

        avg_len = float(total_words) / max(1, len(answers))
        filler_per_100 = (filler_count * 100.0) / max(1, total_words)
        short_ratio = float(short) / max(1, len(answers))
        return {
            "avg_answer_len_words": round(avg_len, 2),
            "short_answer_ratio": round(short_ratio, 3),
            "filler_per_100_words": round(filler_per_100, 2),
            "negative_phrase_count": float(neg_count),
        }

    def _derive_overall_score(
        self,
        hr_data: Dict[str, Any] | None,
        job_fit: Dict[str, Any] | None,
        hiring_decision: Dict[str, Any] | None,
        transcript_metrics: Dict[str, float],
    ) -> float:
        """Combine multiple signals into a robust 0-100 overall score with penalties.
        Strategy:
        - Base = weighted avg of HR criteria mean, job_fit.overall_fit_score*100, skill_match mean*100.
        - Penalties for poor transcript metrics (short answers, negative phrases, high filler).
        - Penalties for unmet high-importance requirements.
        - Cap score when hiring_decision recommends 'No Hire' or confidence low.
        """
        # Base components
        hr_scores: List[float] = []
        if isinstance(hr_data, dict):
            for c in hr_data.get("criteria", []) or []:
                try:
                    hr_scores.append(float(c.get("score_0_100", 0.0)))
                except Exception:
                    continue
        hr_mean = sum(hr_scores)/len(hr_scores) if hr_scores else 50.0

        jf = job_fit or {}
        job_fit_score = float(jf.get("overall_fit_score", 0.5)) * 100.0

        hd = hiring_decision or {}
        sm = (hd.get("skill_match") or {}) if isinstance(hd, dict) else {}
        try:
            skill_vals = [float(sm.get(k, 0.5)) * 100.0 for k in ("technical_fit","soft_skills_fit","cultural_fit","growth_potential")]
            skill_mean = sum(skill_vals)/len(skill_vals)
        except Exception:
            skill_mean = 50.0

        # Weighted base
        base = 0.4*hr_mean + 0.4*job_fit_score + 0.2*skill_mean

        # Requirement penalties
        reqs = jf.get("requirements_matrix") if isinstance(jf, dict) else []
        high_missing = 0
        partial_high = 0
        if isinstance(reqs, list):
            for r in reqs:
                try:
                    importance = str(r.get("importance", "medium")).lower()
                    meets = str(r.get("meets", "neither")).lower()
                    if importance == "high":
                        if meets in ("no", "neither"):
                            high_missing += 1
                        elif meets == "partial":
                            partial_high += 1
                except Exception:
                    continue
        penalty = 0.0
        penalty += high_missing * 12.0  # strong penalty per high-importance miss
        penalty += partial_high * 6.0

        # Transcript penalties
        short_ratio = transcript_metrics.get("short_answer_ratio", 0.0)
        filler_per_100 = transcript_metrics.get("filler_per_100_words", 0.0)
        neg_count = transcript_metrics.get("negative_phrase_count", 0.0)
        if short_ratio >= 0.5:
            penalty += 12.0
        elif short_ratio >= 0.3:
            penalty += 6.0
        if filler_per_100 >= 8.0:
            penalty += 8.0
        elif filler_per_100 >= 4.0:
            penalty += 4.0
        if neg_count >= 6:
            penalty += 12.0
        elif neg_count >= 3:
            penalty += 6.0

        # Hiring decision gating
        rec = str(hd.get("hire_recommendation", "")).lower() if isinstance(hd, dict) else ""
        conf = float(hd.get("decision_confidence", 0.5)) if isinstance(hd, dict) else 0.5
        if rec == "no hire":
            base = min(base, 49.0)
        elif rec == "hold" and conf >= 0.6:
            base = min(base, 59.0)

        final_score = max(0.0, min(100.0, round(base - penalty, 2)))
        return final_score

    # --- Rubric mapping (role-based weights) ---
    def _infer_rubric_weights(self, job_title: str) -> Dict[str, float]:
        jt = (job_title or "").lower()
        # keys: problem, technical, communication, culture
        if any(k in jt for k in ["developer", "yazılım", "engineer", "mühendis"]):
            return {"problem": 0.25, "technical": 0.45, "communication": 0.15, "culture": 0.15}
        if any(k in jt for k in ["data", "ml", "ai", "bilim"]):
            return {"problem": 0.25, "technical": 0.45, "communication": 0.20, "culture": 0.10}
        if any(k in jt for k in ["product", "ürün", "pm"]):
            return {"problem": 0.25, "technical": 0.25, "communication": 0.25, "culture": 0.25}
        if any(k in jt for k in ["sales", "satış", "bdm", "business development"]):
            return {"problem": 0.15, "technical": 0.20, "communication": 0.35, "culture": 0.30}
        if any(k in jt for k in ["marketing", "pazarlama", "growth"]):
            return {"problem": 0.20, "technical": 0.25, "communication": 0.35, "culture": 0.20}
        if any(k in jt for k in ["finance", "muhasebe", "denetim", "finans"]):
            return {"problem": 0.30, "technical": 0.35, "communication": 0.20, "culture": 0.15}
        if any(k in jt for k in ["support", "destek", "müşteri"]):
            return {"problem": 0.15, "technical": 0.20, "communication": 0.40, "culture": 0.25}
        if any(k in jt for k in ["cto", "cmo", "ceo", "cfo", "vp", "director", "müdür", "yönetici", "executive"]):
            return {"problem": 0.30, "technical": 0.20, "communication": 0.25, "culture": 0.25}
        return {"problem": 0.25, "technical": 0.35, "communication": 0.20, "culture": 0.20}

    def _compute_rubric(self, job_title: str, hr_data: Dict[str, Any] | None, job_fit: Dict[str, Any] | None, hiring_decision: Dict[str, Any] | None) -> Dict[str, Any]:
        weights = self._infer_rubric_weights(job_title)
        # Map sources to rubric criteria
        # problem -> HR "Problem Çözme"
        # technical -> avg(job_fit.overall_fit_score*100, hiring_decision.skill_match.technical_fit*100)
        # communication -> HR "İletişim Netliği"
        # culture -> avg(HR "Takım Çalışması", hiring_decision.skill_match.cultural_fit*100)
        def _hr(label: str) -> float | None:
            try:
                for c in (hr_data or {}).get("criteria", []) or []:
                    if str(c.get("label", "")).lower().startswith(label.lower()[:5]):
                        return float(c.get("score_0_100", 0.0))
            except Exception:
                return None
            return None
        problem = _hr("Problem") or 50.0
        comm = _hr("İletişim") or 50.0
        team = _hr("Takım") or 50.0
        jf_score = float((job_fit or {}).get("overall_fit_score", 0.5)) * 100.0
        sm = (hiring_decision or {}).get("skill_match", {}) if isinstance(hiring_decision, dict) else {}
        tech_match = float(sm.get("technical_fit", 0.5)) * 100.0
        cult_match = float(sm.get("cultural_fit", 0.5)) * 100.0
        technical = (jf_score + tech_match) / 2.0
        culture = (team + cult_match) / 2.0
        criteria = [
            {"label": "Problem Çözme", "score_0_100": round(problem, 2), "weight": weights["problem"]},
            {"label": "Teknik Yeterlilik", "score_0_100": round(technical, 2), "weight": weights["technical"]},
            {"label": "İletişim", "score_0_100": round(comm, 2), "weight": weights["communication"]},
            {"label": "Kültür/İş Uygunluğu", "score_0_100": round(culture, 2), "weight": weights["culture"]},
        ]
        overall = 0.0
        for c in criteria:
            overall += float(c["score_0_100"]) * float(c["weight"])
        return {"criteria": criteria, "overall": round(overall, 2), "weights": weights}
    
    def _create_hr_criteria_prompt(self, transcript: str) -> str:
        """Create HR criteria analysis prompt"""
        return f"""Sen deneyimli bir HR uzmanısın. Aşağıdaki mülakat transkriptini analiz et ve her kriter için objektif, kanıta dayalı değerlendirme yap.

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
      "evidence": "Sorulara yapılandırılmış ve net cevaplar verdi.",
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
{transcript[:6000]}"""
    
    def _create_job_fit_prompt(self, job_desc: str, transcript: str, resume: str) -> str:
        """Create job fit analysis prompt"""
        return f"""Sen senior bir işe alım uzmanısın. İş tanımı, özgeçmiş ve mülakat transkriptini detaylı analiz et.

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
      "evidence": "Somut kanıt/örnek",
      "confidence": 0.9,
      "importance": "high|medium|low"
    }}
  ],
  "recommendations": ["Spesifik işe alım önerisi"],
  "risk_factors": ["Potansiyel risk alanları"],
  "competitive_advantages": ["Adayın öne çıkan artıları"]
}}

İŞ TANIMI:
{job_desc[:4500]}

ÖZGEÇMIŞ:
{(resume or 'Özgeçmiş bilgisi mevcut değil')[:3500]}

MÜLAKAT TRANSKRİPTİ:
{transcript[:4500]}"""
    
    def _create_hiring_decision_prompt(self, job_desc: str, transcript: str, resume: str) -> str:
        """Create hiring decision analysis prompt"""
        return f"""Sen deneyimli bir CTO ve hiring manager'sın. İş tanımı, özgeçmiş ve mülakat transkriptine göre yapılandırılmış işe alım kararı ver.

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
  "key_strengths": ["Spesifik güçlü yön 1 (kanıtla)"],
  "key_concerns": ["Spesifik endişe 1 (gerekçeyle)"],
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
  "risk_factors": ["Potansiyel risk 1"],
  "mitigation_strategies": ["Risk azaltma önerisi"],
  "next_steps": ["Önerilen sonraki adım"],
  "timeline_recommendation": "immediate|1_week|2_weeks|reassess"
}}

İŞ TANIMI:
{job_desc[:4000]}

ÖZGEÇMIŞ:
{(resume or 'Özgeçmiş bilgisi mevcut değil')[:2500]}

MÜLAKAT TRANSKRİPTİ:
{transcript[:4500]}"""
    
    def _create_candidate_profile_prompt(self, resume: str, job_desc: str) -> str:
        """Create candidate profile summary prompt"""
        return f"""Aşağıdaki özgeçmişi analiz et ve iş ilanına göre öz bir değerlendirme yap. 
Maksimum 4-5 cümle ile şu bilgileri ver:

📋 **Profil Özeti**: Deneyim seviyesi, ana uzmanlık alanları ve eğitim durumu
🎯 **İş Uygunluğu**: İlan gereksinimlerine uygunluk ve öne çıkan yetenekler
🚀 **Öne Çıkan Başarılar**: En dikkat çekici proje/deneyim (varsa)
💡 **Genel Değerlendirme**: Kısa bir işe alım önerisi

Türkçe ve profesyonel bir dil kullan. Çok uzun olmasın, öz ve net ol.

İş İlanı: {job_desc[:3000] or 'Belirtilmemiş'}

Özgeçmiş:
{resume[:4000]}"""
    
    def _create_soft_skills_prompt(self, transcript: str, job_desc: str) -> str:
        """Create soft skills extraction prompt"""
        return f"""Aşağıdaki yanıttan soft-skills çıkar ve kısa özet ver. 
Yanıt Türkçe olabilir. JSON dön: {{"soft_skills":[{{"label":str,"confidence":0-1,"evidence":str}}],"summary":str}}.

İş tanımı: {job_desc[:2000] or '-'}

Yanıt: {transcript[:4000]}"""
    
    def _create_requirements_extraction_prompt(self, job_desc: str) -> str:
        """Create requirements extraction prompt"""
        return f"""Aşağıdaki iş ilanından gereksinimleri çıkar ve normalize et. JSON dön.
Şema: {{"items":[{{"id":str,"label":str,"must":bool,"level":"junior|mid|senior|lead","weight":0-1,"keywords":[str],"success_rubric":str,"question_templates":[str]}}]}}

İlan Metni:
{job_desc[:5000]}"""
    
    async def _run_single_analysis(self, analysis_type: AnalysisType, input_data: AnalysisInput) -> Tuple[AnalysisType, Union[Dict[str, Any], str]]:
        """Run single analysis type"""
        try:
            if analysis_type == AnalysisType.HR_CRITERIA:
                if not input_data.transcript_text.strip():
                    return analysis_type, {}
                
                prompt = self._create_hr_criteria_prompt(input_data.transcript_text)
                result = await generate_json(prompt, temperature=0.05)
                
                # Normalize result
                if not isinstance(result.get("criteria"), list):
                    result["criteria"] = []
                
                for criterion in result.get("criteria", []):
                    criterion.setdefault("confidence", 0.5)
                    criterion.setdefault("reasoning", "")
                
                return analysis_type, result
            
            elif analysis_type == AnalysisType.JOB_FIT:
                if not (input_data.job_description.strip() and input_data.transcript_text.strip()):
                    return analysis_type, {}
                
                prompt = self._create_job_fit_prompt(
                    input_data.job_description,
                    input_data.transcript_text,
                    input_data.resume_text
                )
                result = await generate_json(prompt, temperature=0.1)
                
                # Normalize result
                if not isinstance(result.get("requirements_matrix"), list):
                    result["requirements_matrix"] = []
                
                for req in result.get("requirements_matrix", []):
                    req.setdefault("confidence", 0.5)
                    req.setdefault("importance", "medium")
                
                result.setdefault("overall_fit_score", 0.0)
                return analysis_type, result
            
            elif analysis_type == AnalysisType.HIRING_DECISION:
                if not (input_data.job_description.strip() and input_data.transcript_text.strip()):
                    return analysis_type, {}
                
                prompt = self._create_hiring_decision_prompt(
                    input_data.job_description,
                    input_data.transcript_text,
                    input_data.resume_text
                )
                result = await generate_json(prompt, temperature=0.05)
                
                # Normalize result
                result.setdefault("decision_confidence", 0.5)
                result.setdefault("timeline_recommendation", "reassess")
                
                skill_match = result.setdefault("skill_match", {})
                skill_match.setdefault("technical_fit", 0.5)
                skill_match.setdefault("soft_skills_fit", 0.5)
                skill_match.setdefault("cultural_fit", 0.5)
                skill_match.setdefault("growth_potential", 0.5)
                
                return analysis_type, result
            
            elif analysis_type == AnalysisType.CANDIDATE_PROFILE:
                if not input_data.resume_text.strip():
                    return analysis_type, {"profile": ""}
                
                prompt = self._create_candidate_profile_prompt(
                    input_data.resume_text,
                    input_data.job_description
                )
                result = await self.llm_client.generate(LLMRequest(
                    prompt=prompt,
                    temperature=0.3,
                    max_tokens=500
                ))
                
                # Clean up formatting
                import re
                text = result.content.strip()
                text = re.sub(r"\n{3,}", "\n\n", text)
                
                return analysis_type, {"profile": text}
            
            elif analysis_type == AnalysisType.SOFT_SKILLS:
                if not input_data.transcript_text.strip():
                    return analysis_type, {}
                
                prompt = self._create_soft_skills_prompt(
                    input_data.transcript_text,
                    input_data.job_description
                )
                result = await generate_json(prompt, temperature=0.2)
                return analysis_type, result
            
            elif analysis_type == AnalysisType.REQUIREMENTS_EXTRACTION:
                if not input_data.job_description.strip():
                    return analysis_type, {"items": []}
                
                prompt = self._create_requirements_extraction_prompt(input_data.job_description)
                result = await generate_json(prompt, temperature=0.1)
                
                # Defensive normalization
                items = result.get("items") if isinstance(result, dict) else None
                if not isinstance(items, list):
                    return analysis_type, {"items": []}
                
                for i, item in enumerate(items):
                    if not isinstance(item, dict):
                        continue
                    item.setdefault("id", f"req_{i}")
                    item["weight"] = float(item.get("weight", 0.5) or 0.5)
                    
                    kws = item.get("keywords") or []
                    if not isinstance(kws, list) or not kws:
                        item["keywords"] = [item.get("label", "")]
                    
                    templates = item.get("question_templates") or []
                    if not isinstance(templates, list) or not templates:
                        item["question_templates"] = [f"{item.get('label','')} ile ilgili somut bir örnek anlatır mısınız?"]
                    # Ensure success_rubric exists for UI/export clarity
                    if not isinstance(item.get("success_rubric"), str) or not item.get("success_rubric"): 
                        item["success_rubric"] = "Somut örnek, sizin aksiyonlarınız ve ölçülebilir sonuç içermeli."
                
                return analysis_type, {"items": items}
            
            else:
                return analysis_type, {}
        
        except Exception as e:
            # Log error but don't fail entire batch
            return analysis_type, {"error": str(e)}
    
    async def analyze_comprehensive(self, input_data: AnalysisInput) -> Dict[str, Any]:
        """
        Run comprehensive analysis with multiple types in parallel
        Replaces multiple nlp.py functions with single efficient call
        """
        
        # Create tasks for parallel execution
        analysis_types = input_data.analysis_types or []
        tasks = [
            self._run_single_analysis(analysis_type, input_data)
            for analysis_type in analysis_types
        ]
        
        # Run all analyses in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect results
        analysis_results = {}
        for result in results:
            if isinstance(result, Exception):
                continue
            
            if isinstance(result, tuple) and len(result) == 2:
                try:
                    analysis_type, data = result
                    analysis_results[analysis_type.value] = data
                except (TypeError, ValueError, AttributeError):
                    # Handle unpacking errors gracefully
                    continue
        
        # Robust overall score combining HR, job-fit, hiring decision and transcript penalties
        hr_data = analysis_results.get(AnalysisType.HR_CRITERIA.value) if isinstance(analysis_results, dict) else None
        job_fit = analysis_results.get(AnalysisType.JOB_FIT.value) if isinstance(analysis_results, dict) else None
        hiring_decision = analysis_results.get(AnalysisType.HIRING_DECISION.value) if isinstance(analysis_results, dict) else None
        transcript_metrics = self._compute_transcript_metrics(input_data.transcript_text or "")
        overall_score = self._derive_overall_score(hr_data, job_fit, hiring_decision, transcript_metrics)
        
        # Add metadata
        # Rubric summary
        rubric = self._compute_rubric(input_data.job_title, hr_data, job_fit, hiring_decision)

        analysis_results["rubric"] = rubric
        # Seed initial topics for early coverage from extracted requirements
        try:
            req_items = ((analysis_results.get(AnalysisType.JOB_FIT.value) or {}).get("requirements_matrix") or []) if isinstance(analysis_results, dict) else []
            topics = [it.get("label", "") for it in req_items[:6] if isinstance(it, dict) and it.get("label")]
            if topics:
                analysis_results.setdefault("dialog_plan", {})
                analysis_results["dialog_plan"]["topics"] = topics
        except Exception:
            pass

        analysis_results["meta"] = {
            "analysis_types": [t.value for t in (input_data.analysis_types or [])],
            "overall_score": overall_score,
            "input_sizes": {
                "job_description": len(input_data.job_description),
                "transcript": len(input_data.transcript_text),
                "resume": len(input_data.resume_text)
            },
            "candidate_name": input_data.candidate_name,
            "job_title": input_data.job_title,
            "transcript_metrics": transcript_metrics,
        }
        
        return analysis_results


# Convenience functions that maintain compatibility with old nlp.py interface
async def comprehensive_interview_analysis(
    job_desc: str,
    transcript_text: str,
    resume_text: str = "",
    candidate_name: str = "",
    job_title: str = ""
) -> Dict[str, Any]:
    """
    Main comprehensive analysis function - replaces multiple nlp.py functions
    """
    analyzer = ComprehensiveAnalyzer()
    
    input_data = AnalysisInput(
        job_description=job_desc,
        transcript_text=transcript_text,
        resume_text=resume_text,
        candidate_name=candidate_name,
        job_title=job_title,
        analysis_types=[
            AnalysisType.HR_CRITERIA,
            AnalysisType.JOB_FIT,
            AnalysisType.HIRING_DECISION
        ]
    )
    
    return await analyzer.analyze_comprehensive(input_data)


async def extract_requirements_spec(job_desc: str) -> Dict[str, Any]:
    """Extract job requirements - maintains compatibility"""
    if not job_desc.strip():
        return {"items": []}
    
    analyzer = ComprehensiveAnalyzer()
    input_data = AnalysisInput(
        job_description=job_desc,
        analysis_types=[AnalysisType.REQUIREMENTS_EXTRACTION]
    )
    
    result = await analyzer.analyze_comprehensive(input_data)
    return result.get(AnalysisType.REQUIREMENTS_EXTRACTION.value, {"items": []})


async def summarize_candidate_profile(resume_text: str, job_desc: str = "") -> str:
    """Summarize candidate profile - maintains compatibility"""
    if not resume_text.strip():
        return ""
    
    analyzer = ComprehensiveAnalyzer()
    input_data = AnalysisInput(
        resume_text=resume_text,
        job_description=job_desc,
        analysis_types=[AnalysisType.CANDIDATE_PROFILE]
    )
    
    result = await analyzer.analyze_comprehensive(input_data)
    profile_data = result.get(AnalysisType.CANDIDATE_PROFILE.value, {})
    if isinstance(profile_data, dict):
        return profile_data.get("profile", "")
    return str(profile_data) if profile_data else ""


# Backward compatibility functions (deprecated but maintained)
async def assess_hr_criteria(transcript_text: str) -> Dict[str, Any]:
    """Deprecated: Use comprehensive_interview_analysis instead"""
    analyzer = ComprehensiveAnalyzer()
    input_data = AnalysisInput(
        transcript_text=transcript_text,
        analysis_types=[AnalysisType.HR_CRITERIA]
    )
    result = await analyzer.analyze_comprehensive(input_data)
    return result.get(AnalysisType.HR_CRITERIA.value, {})


async def assess_job_fit(job_desc: str, transcript_text: str, resume_text: str = "") -> Dict[str, Any]:
    """Deprecated: Use comprehensive_interview_analysis instead"""
    analyzer = ComprehensiveAnalyzer()
    input_data = AnalysisInput(
        job_description=job_desc,
        transcript_text=transcript_text,
        resume_text=resume_text,
        analysis_types=[AnalysisType.JOB_FIT]
    )
    result = await analyzer.analyze_comprehensive(input_data)
    return result.get(AnalysisType.JOB_FIT.value, {})


async def opinion_on_candidate(job_desc: str, transcript_text: str, resume_text: str = "") -> Dict[str, Any]:
    """Deprecated: Use comprehensive_interview_analysis instead"""
    analyzer = ComprehensiveAnalyzer()
    input_data = AnalysisInput(
        job_description=job_desc,
        transcript_text=transcript_text,
        resume_text=resume_text,
        analysis_types=[AnalysisType.HIRING_DECISION]
    )
    result = await analyzer.analyze_comprehensive(input_data)
    return result.get(AnalysisType.HIRING_DECISION.value, {})
