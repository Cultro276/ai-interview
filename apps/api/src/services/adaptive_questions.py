"""
Adaptive Interview Question Generation
Analyzes candidate responses in real-time and generates targeted follow-up questions
"""
from typing import Dict, List, Any
import httpx
from src.core.config import settings


async def analyze_response_weaknesses(conversation_history: List[Dict], job_requirements: str) -> Dict[str, Any]:
    """
    Enhanced competency gap detection with detailed evidence tracking
    """
    if not (settings.openai_api_key and conversation_history):
        return {"weak_areas": [], "follow_up_strategy": "standard"}
    
    # Build conversation context with turn tracking
    conversation_text = ""
    for i, turn in enumerate(conversation_history):
        role = "Mülakatçı" if turn.get("role") == "assistant" else "Aday"
        conversation_text += f"[Turn {i+1}] {role}: {turn.get('text', '')}\n\n"
    
    prompt = f"""Sen deneyimli bir mülakat analisti ve behavioural interviewer'sın. Konuşma akışını detaylı analiz et.

ANALIZ HEDEFLERİ:
1. Eksik kompetans alanlarını tespit et
2. Zayıf cevap kalitelerini belirle  
3. Kaçırılan soru fırsatlarını bulunu
4. Stratejik takip-up plan oluştur

WEAKNESS LEVELS:
- critical: İş için hayati, derhal derinleştir
- high: Önemli eksiklik, zorlayıcı sorularla test et
- medium: Sınırlı kanıt, daha detay al
- low: Minör endişe, onaylatma amaçlı

ZORUNLU JSON FORMAT:
{{
  "weak_areas": [
    {{
      "area": "Spesifik kompetans alanı",
      "weakness_level": "critical|high|medium|low",
      "evidence": "Hangi yanıtta ne eksikliği gözlemlendi",
      "gap_type": "no_evidence|shallow_response|vague_answer|inconsistent",
      "suggested_follow_up": "Hedeft soru önerisi",
      "probing_strategy": "scenario|behavioral|technical|clarifying",
      "importance_score": 0.9
    }}
  ],
  "follow_up_strategy": "deep_dive|challenge|clarify|scenario_based|standard",
  "priority_area": "En kritik eksik alan",
  "interview_momentum": "strong|moderate|weak|stalled",
  "suggested_next_moves": ["Önerilen sıradaki adımlar"],
  "confidence_score": 0.85,
  "competency_coverage": {{
    "technical": 0.7,
    "behavioral": 0.6,
    "cultural": 0.5
  }}
}}

İŞ GEREKSİNİMLERİ:
{job_requirements}

MÜLAKAT KONUŞMASI:
{conversation_text}"""
    
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    body = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "response_format": {"type": "json_object"}
    }
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post("https://api.openai.com/v1/chat/completions", json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            
            import json
            result = json.loads(data["choices"][0]["message"]["content"])
            
            # Validate and set defaults
            for area in result.get("weak_areas", []):
                area.setdefault("importance_score", 0.5)
                area.setdefault("gap_type", "shallow_response")
                area.setdefault("probing_strategy", "clarifying")
            
            result.setdefault("interview_momentum", "moderate")
            result.setdefault("competency_coverage", {"technical": 0.5, "behavioral": 0.5, "cultural": 0.5})
            
            return result
    except Exception as e:
        print(f"Adaptive analysis failed: {e}")
        return {"weak_areas": [], "follow_up_strategy": "standard"}


async def generate_targeted_question(weak_area: Dict[str, Any], job_context: str) -> str:
    """
    Generate strategically targeted follow-up questions with dynamic difficulty adjustment
    """
    if not (settings.openai_api_key and weak_area):
        return ""
    
    area = weak_area.get("area", "")
    weakness_level = weak_area.get("weakness_level", "medium")
    evidence = weak_area.get("evidence", "")
    gap_type = weak_area.get("gap_type", "shallow_response")
    probing_strategy = weak_area.get("probing_strategy", "clarifying")
    importance_score = weak_area.get("importance_score", 0.5)
    
    prompt = f"""Sen master-level bir behavioral interviewer'sın. Tespit edilen zayıflık için stratejik takip sorusu geliştir.

ZAYIFLIK DETAYI:
- Alan: {area}
- Seviye: {weakness_level}
- Gap Tipi: {gap_type}
- Strateji: {probing_strategy}
- Önem: {importance_score}
- Kanıt: {evidence}

SORU STRATEJİLERİ:
- scenario: Zorlayıcı durum senaryoları
- behavioral: STAR formatında gerçek deneyim
- technical: Derinlemesine teknik bilgi
- clarifying: Netleştirme ve detay alma

ZORLUK SEVİYELERİ:
- critical: Max zorluk, yüksek stakes senaryo
- high: Zorlayıcı, gerçekçi durumlar  
- medium: Orta seviye detay talebi
- low: Basit netleştirme

SORU KRİTERLERİ:
✓ Spesifik ve hedefli (generic değil)
✓ STAR metodunu teşvik eder
✓ Ölçülebilir cevap bekler
✓ İş bağlamına uygun
✓ Adil ama zorlayıcı
✓ Maksimum 2 cümle

İŞ BAĞLAMI:
{job_context[:1200]}

SADECE SORUYU DÖNDÜR (açıklama yok):"""
    
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    body = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 150
    }
    
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post("https://api.openai.com/v1/chat/completions", json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            
            question = data["choices"][0]["message"]["content"].strip()
            
            # Clean up the question
            question = question.replace('"', '').replace("'", "'")
            if question.endswith('.'):
                question = question[:-1] + '?'
            elif not question.endswith('?'):
                question += '?'
                
            return question
    except Exception as e:
        print(f"Targeted question generation failed: {e}")
        return get_fallback_adaptive_question(area, weakness_level)


async def should_adapt_interview(conversation_history: List[Dict], asked_count: int) -> bool:
    """
    Determine if we should switch to adaptive mode based on conversation patterns
    """
    # Start adaptive mode after 3rd question
    if asked_count < 3:
        return False
    
    # Look for signs that adaptation is needed
    user_responses = [turn for turn in conversation_history if turn.get("role") == "user"]
    
    # Check for consistently short responses
    avg_response_length = sum(len(r.get("text", "")) for r in user_responses) / len(user_responses) if user_responses else 0
    
    # Check for vague responses
    vague_indicators = ["bilmiyorum", "emin değilim", "tam hatırlamıyorum", "sanırım", "belki"]
    vague_responses = sum(1 for r in user_responses if any(indicator in r.get("text", "").lower() for indicator in vague_indicators))
    
    # Adapt if responses are too short or too vague
    return avg_response_length < 50 or vague_responses >= 2


def get_fallback_adaptive_question(area: str, level: str = "medium") -> str:
    """
    Fallback adaptive questions when API fails
    """
    question_templates = {
        "teknik": {
            "high": "En karmaşık teknik problemi çözdüğünüz bir durumu STAR metoduyla anlatır mısınız? Hangi teknolojileri kullandınız ve neden?",
            "medium": "Teknik bir zorluğu nasıl çözdüğünüz somut bir örnek verebilir misiniz?",
            "low": "Kullandığınız teknolojiler hakkında biraz daha detay verebilir misiniz?"
        },
        "liderlik": {
            "high": "Ekibinizde ciddi bir çatışma yaşandığı ve projeyi tehlikeye attığı bir durumda nasıl müdahale ettiniz?",
            "medium": "Zorlu bir projede ekibinizi nasıl motive ettiğinizi anlatır mısınız?",
            "low": "Takım çalışmasında hangi rolü tercih ediyorsunuz?"
        },
        "problem_solving": {
            "high": "Hiç karşılaşmadığınız bir problemle başbaşa kaldığınızda hangi adımları izlersiniz? Somut örnek verebilir misiniz?",
            "medium": "Karmaşık bir problemi nasıl parçalara ayırıp çözdüğünüz bir örnek paylaşır mısınız?",
            "low": "Problem çözme yaklaşımınızı nasıl tanımlarsınız?"
        }
    }
    
    return question_templates.get(area, {}).get(level, "Bu konuda daha detaylı bilgi verebilir misiniz?")


# --- PHASE 3: ADVANCED ADAPTIVE FEATURES ---

async def calculate_interview_difficulty_adjustment(conversation_history: List[Dict], candidate_performance: Dict[str, float]) -> Dict[str, Any]:
    """
    Dynamically adjust interview difficulty based on candidate performance patterns
    """
    if not conversation_history:
        return {"difficulty_level": "medium", "adjustment_reason": "insufficient_data"}
    
    user_responses = [turn for turn in conversation_history if turn.get("role") == "user"]
    if len(user_responses) < 2:
        return {"difficulty_level": "medium", "adjustment_reason": "insufficient_responses"}
    
    # Analyze response quality indicators
    total_words = sum(len(response.get("text", "").split()) for response in user_responses)
    avg_response_length = total_words / len(user_responses)
    
    # Check for confidence indicators
    confidence_words = ["kesinlikle", "eminim", "deneyimim var", "uzmanım", "başarıyla"]
    uncertainty_words = ["sanırım", "belki", "tam emin değilim", "çok bilmiyorum", "deneyimim yok"]
    
    confidence_count = sum(1 for response in user_responses 
                          if any(word in response.get("text", "").lower() for word in confidence_words))
    uncertainty_count = sum(1 for response in user_responses 
                           if any(word in response.get("text", "").lower() for word in uncertainty_words))
    
    # Calculate technical depth (presence of technical terms)
    technical_terms = ["api", "database", "algorithm", "framework", "architecture", "performance", "scalability"]
    technical_mentions = sum(1 for response in user_responses 
                            if any(term in response.get("text", "").lower() for term in technical_terms))
    
    # Performance-based scoring
    avg_performance = sum(candidate_performance.values()) / len(candidate_performance) if candidate_performance else 0.5
    
    # Decision logic
    if avg_performance > 0.8 and avg_response_length > 80 and confidence_count > uncertainty_count:
        difficulty = "high"
        reason = "strong_performance_increase_challenge"
    elif avg_performance < 0.4 or uncertainty_count > confidence_count * 2:
        difficulty = "low"
        reason = "struggling_reduce_pressure"
    elif technical_mentions >= len(user_responses) * 0.6:
        difficulty = "high"
        reason = "technical_competence_detected"
    else:
        difficulty = "medium"
        reason = "balanced_approach"
    
    return {
        "difficulty_level": difficulty,
        "adjustment_reason": reason,
        "performance_indicators": {
            "avg_response_length": avg_response_length,
            "confidence_ratio": confidence_count / max(1, uncertainty_count),
            "technical_density": technical_mentions / len(user_responses),
            "avg_performance_score": avg_performance
        },
        "suggested_approach": _get_difficulty_approach(difficulty)
    }


def _get_difficulty_approach(difficulty: str) -> str:
    """Return interview approach based on difficulty level"""
    approaches = {
        "high": "Zorlayıcı senaryolar, derinlemesine teknik sorular, karmaşık problemler",
        "medium": "Dengeli yaklaşım, STAR örnekleri, orta seviye detay",
        "low": "Destekleyici sorular, temel kavramlar, güven artırıcı yaklaşım"
    }
    return approaches.get(difficulty, approaches["medium"])


async def generate_competency_focused_questions(missing_competencies: List[str], job_requirements: str) -> List[Dict[str, Any]]:
    """
    Generate a sequence of questions specifically targeting missing competencies
    """
    if not (settings.openai_api_key and missing_competencies):
        return []
    
    competencies_text = ", ".join(missing_competencies)
    
    prompt = f"""Sen competency-based interview uzmanısın. Eksik bulunan yetkinlikler için hedefli soru dizisi oluştur.

EKSİK YETKİNLİKLER: {competencies_text}

Her yetkinlik için şu formatta soru tasarla:

ZORUNLU JSON FORMAT:
{{
  "questions": [
    {{
      "competency": "Spesifik yetkinlik adı",
      "question": "STAR formatını teşvik eden açık uçlu soru",
      "difficulty": "junior|mid|senior",
      "follow_up_probes": [
        "Detay alma sorusu 1",
        "Derinleştirme sorusu 2"
      ],
      "evaluation_criteria": [
        "Değerlendirme kriteri 1",
        "Değerlendirme kriteri 2"
      ],
      "red_flags": ["Kırmızı bayrak işaretleri"],
      "ideal_response_indicators": ["Güçlü cevap göstergeleri"]
    }}
  ]
}}

İŞ GEREKSİNİMLERİ:
{job_requirements[:2000]}"""
    
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    body = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "response_format": {"type": "json_object"}
    }
    
    try:
        async with httpx.AsyncClient(timeout=35) as client:
            resp = await client.post("https://api.openai.com/v1/chat/completions", json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            
            import json
            result = json.loads(data["choices"][0]["message"]["content"])
            return result.get("questions", [])
    except Exception as e:
        print(f"Competency question generation failed: {e}")
        return []
