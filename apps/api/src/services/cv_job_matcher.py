"""
CV-Job relevance checking and sector matching functionality.
"""
import re
from typing import Dict, List, Tuple, Optional, Any
import logging

logger = logging.getLogger(__name__)


def extract_candidate_sectors(resume_text: str) -> List[str]:
    """Extract sectors/domains from candidate's resume."""
    if not resume_text:
        return []
    
    resume_lower = resume_text.lower()
    
    # Common sector keywords mapping
    sector_keywords = {
        "tech": ["yazılım", "software", "geliştir", "develop", "kod", "code", "programming", "python", "java", "react", "frontend", "backend", "mobile", "web", "api", "database", "sistem", "system"],
        "finance": ["finans", "finance", "bank", "muhasebe", "accounting", "yatırım", "investment", "trading", "forex", "bütçe", "budget", "mali", "financial"],
        "fashion": ["moda", "fashion", "giyim", "textile", "tekstil", "clothing", "apparel", "design", "tasarım", "collection", "koleksiyon", "retail", "mağaza"],
        "healthcare": ["sağlık", "health", "medical", "tıp", "hastane", "hospital", "clinic", "klinik", "doktor", "doctor", "hemşire", "nurse"],
        "education": ["eğitim", "education", "öğretim", "teaching", "okul", "school", "university", "üniversite", "akademi", "academy", "eğitmen", "trainer"],
        "marketing": ["pazarlama", "marketing", "reklam", "advertising", "campaign", "kampanya", "brand", "marka", "digital marketing", "sosyal medya", "social media"],
        "sales": ["satış", "sales", "müşteri", "customer", "client", "account", "hesap", "revenue", "gelir", "target", "hedef"],
        "manufacturing": ["üretim", "production", "manufacturing", "fabrika", "factory", "quality", "kalite", "operation", "operasyon", "supply chain"],
        "consulting": ["danışman", "consultant", "consulting", "advisory", "tavsiye", "strategy", "strateji", "business", "iş"],
        "logistics": ["lojistik", "logistics", "supply", "tedarik", "shipping", "kargo", "transport", "nakliye", "warehouse", "depo"]
    }
    
    detected_sectors = []
    for sector, keywords in sector_keywords.items():
        sector_score = sum(1 for keyword in keywords if keyword in resume_lower)
        if sector_score >= 2:  # At least 2 keyword matches
            detected_sectors.append(sector)
    
    return detected_sectors


def extract_job_required_sectors(job_description: str) -> List[str]:
    """Extract required sectors/domains from job description."""
    if not job_description:
        return []
    
    job_lower = job_description.lower()
    
    # More specific patterns for job requirements
    sector_patterns = {
        "tech": [r"yazılım\s+geliştir", r"software\s+develop", r"programming", r"coding", r"frontend", r"backend", r"fullstack", r"mobile\s+app"],
        "finance": [r"finans\s+sektör", r"finance\s+sector", r"banking", r"investment", r"financial\s+analys", r"muhasebe"],
        "fashion": [r"moda\s+sektör", r"fashion\s+industry", r"giyim\s+sektör", r"textile", r"apparel", r"retail\s+fashion"],
        "healthcare": [r"sağlık\s+sektör", r"healthcare", r"medical", r"tıp", r"hastane", r"hospital"],
        "education": [r"eğitim\s+sektör", r"education", r"academic", r"teaching", r"öğretim"],
        "marketing": [r"pazarlama", r"marketing", r"advertising", r"digital\s+marketing", r"brand\s+management"],
        "sales": [r"satış", r"sales", r"business\s+development", r"account\s+management"],
        "manufacturing": [r"üretim", r"manufacturing", r"production", r"factory", r"kalite\s+kontrol"],
        "consulting": [r"danışmanlık", r"consulting", r"advisory", r"strategy"],
        "logistics": [r"lojistik", r"logistics", r"supply\s+chain", r"warehouse"]
    }
    
    required_sectors = []
    for sector, patterns in sector_patterns.items():
        for pattern in patterns:
            if re.search(pattern, job_lower):
                required_sectors.append(sector)
                break
    
    return list(set(required_sectors))  # Remove duplicates


def check_cv_job_relevance(resume_text: str, job_description: str) -> Dict[str, Any]:
    """
    Check relevance between candidate's CV and job requirements.
    Returns relevance score and recommendations.
    """
    if not resume_text or not job_description:
        return {
            "relevance_score": 0.0,
            "candidate_sectors": [],
            "required_sectors": [],
            "matching_sectors": [],
            "missing_sectors": [],
            "recommendations": ["CV veya iş tanımı eksik"]
        }
    
    candidate_sectors = extract_candidate_sectors(resume_text)
    required_sectors = extract_job_required_sectors(job_description)
    
    if not required_sectors:
        # If we can't determine required sectors, assume general relevance
        return {
            "relevance_score": 0.7,
            "candidate_sectors": candidate_sectors,
            "required_sectors": [],
            "matching_sectors": [],
            "missing_sectors": [],
            "recommendations": ["İş tanımından net sektör gereksinimleri çıkarılamadı"]
        }
    
    matching_sectors = list(set(candidate_sectors) & set(required_sectors))
    missing_sectors = list(set(required_sectors) - set(candidate_sectors))
    
    # Calculate relevance score
    if not required_sectors:
        relevance_score = 0.7  # Neutral if no requirements detected
    else:
        relevance_score = len(matching_sectors) / len(required_sectors)
    
    # Generate recommendations
    recommendations = []
    if relevance_score < 0.3:
        recommendations.append("CV ile iş gereksinimlerinde önemli uyumsuzluk var")
        recommendations.append("Sektör deneyimi eksikliği sorgulanmalı")
    elif relevance_score < 0.6:
        recommendations.append("Kısmi sektör uyumu var, eksik alanlar sorgulanmalı")
    else:
        recommendations.append("CV ile iş gereksinimleri uyumlu")
    
    if missing_sectors:
        missing_str = ", ".join(missing_sectors)
        recommendations.append(f"Eksik sektör deneyimi: {missing_str}")
    
    return {
        "relevance_score": relevance_score,
        "candidate_sectors": candidate_sectors,
        "required_sectors": required_sectors,
        "matching_sectors": matching_sectors,
        "missing_sectors": missing_sectors,
        "recommendations": recommendations
    }


def generate_cv_aware_context(resume_text: str, job_description: str) -> str:
    """
    Generate enhanced context for LLM with CV-job relevance information.
    """
    relevance_check = check_cv_job_relevance(resume_text, job_description)
    
    context_additions = []
    
    if relevance_check["relevance_score"] < 0.5:
        context_additions.append("🚨 CV-JOB MISMATCH DETECTED:")
        context_additions.append(f"- Aday sektörleri: {', '.join(relevance_check['candidate_sectors'])}")
        context_additions.append(f"- Gerekli sektörler: {', '.join(relevance_check['required_sectors'])}")
        context_additions.append(f"- Eksik alanlar: {', '.join(relevance_check['missing_sectors'])}")
        context_additions.append("⚠️ Bu alanlarda deneyim soruları sormadan önce deneyim varlığını teyit et!")
    
    if relevance_check["missing_sectors"]:
        missing_sectors_str = ", ".join(relevance_check["missing_sectors"])
        context_additions.append(f"⚠️ MISSING SECTOR EXPERIENCE: {missing_sectors_str}")
        context_additions.append("Ask about transferable skills, not specific project challenges in these areas.")
    
    if context_additions:
        return "\n".join(context_additions) + "\n\n"
    
    return ""


async def validate_question_relevance(question: str, resume_text: str, job_description: str) -> Tuple[bool, Optional[str]]:
    """
    Validate if a generated question is relevant to candidate's actual experience.
    Returns (is_valid, suggestion_if_invalid)
    """
    if not question or not resume_text:
        return True, None
    
    question_lower = question.lower()
    resume_lower = resume_text.lower()
    
    # Check for sector-specific experience questions
    problematic_patterns = [
        (r"kadın giyim.*zorlad", "fashion"),
        (r"moda.*proje", "fashion"),
        (r"retail.*deneyim", "fashion"),
        (r"bankacılık.*zorlad", "finance"), 
        (r"finans.*proje", "finance"),
        (r"sağlık.*deneyim", "healthcare"),
        (r"hastane.*proje", "healthcare"),
        (r"eğitim.*zorlad", "education"),
        (r"öğretim.*deneyim", "education")
    ]
    
    candidate_sectors = extract_candidate_sectors(resume_text)
    
    for pattern, required_sector in problematic_patterns:
        if re.search(pattern, question_lower):
            if required_sector not in candidate_sectors:
                suggestion = f"CV'de {required_sector} sektörü deneyimi görünmüyor. Önce bu alanda deneyimi var mı sorun: 'Bu pozisyon {required_sector} deneyimi gerektiriyor, bu alanda deneyiminizi anlatır mısınız?'"
                return False, suggestion
    
    return True, None
