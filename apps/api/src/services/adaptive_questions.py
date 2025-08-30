"""
Adaptive Interview Question Generation
Analyzes candidate responses in real-time and generates targeted follow-up questions
"""
from typing import Dict, List, Any
import httpx
from src.core.config import settings


async def analyze_response_weaknesses(conversation_history: List[Dict], job_requirements: str) -> Dict[str, Any]:
    """
    Analyze conversation to identify weak areas that need deeper probing
    """
    if not (settings.openai_api_key and conversation_history):
        return {"weak_areas": [], "follow_up_strategy": "standard"}
    
    # Build conversation context
    conversation_text = ""
    for turn in conversation_history:
        role = "Mülakatçı" if turn.get("role") == "assistant" else "Aday"
        conversation_text += f"{role}: {turn.get('text', '')}\n\n"
    
    prompt = (
        "Aşağıdaki mülakat konuşmasını analiz et ve adayın zayıf kaldığı alanları tespit et.\n"
        "Hangi konularda daha derinlemesine soru sorulması gerektiğini belirle.\n\n"
        "İş Gereksinimleri:\n"
        f"{job_requirements}\n\n"
        "Konuşma:\n"
        f"{conversation_text}\n\n"
        "JSON formatında şunu döndür:\n"
        "{\n"
        "  \"weak_areas\": [\n"
        "    {\n"
        "      \"area\": \"Teknik alanın adı\",\n"
        "      \"weakness_level\": \"high|medium|low\",\n"
        "      \"evidence\": \"Zayıflığa dair kanıt\",\n"
        "      \"suggested_follow_up\": \"Önerilen takip sorusu\"\n"
        "    }\n"
        "  ],\n"
        "  \"follow_up_strategy\": \"deep_dive|clarify|challenge|standard\",\n"
        "  \"priority_area\": \"En öncelikli alan\",\n"
        "  \"confidence_score\": 0.85\n"
        "}"
    )
    
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    body = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 800
    }
    
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post("https://api.openai.com/v1/chat/completions", json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            
            import json
            result = json.loads(data["choices"][0]["message"]["content"])
            return result
    except Exception as e:
        print(f"Adaptive analysis failed: {e}")
        return {"weak_areas": [], "follow_up_strategy": "standard"}


async def generate_targeted_question(weak_area: Dict[str, Any], job_context: str) -> str:
    """
    Generate a specific probing question for identified weakness
    """
    if not (settings.openai_api_key and weak_area):
        return ""
    
    area = weak_area.get("area", "")
    weakness_level = weak_area.get("weakness_level", "medium")
    evidence = weak_area.get("evidence", "")
    
    # Adjust question difficulty and depth based on weakness level
    if weakness_level == "high":
        approach = "zorlayıcı senaryolar ve derinlemesine teknik sorular"
    elif weakness_level == "medium":
        approach = "açıklayıcı örnekler ve detay isteme"
    else:
        approach = "temel kavramları netleştirme"
    
    prompt = (
        f"'{area}' konusunda zayıflık tespit edildi. Bu alan için {approach} kullanarak "
        f"hedefli bir mülakat sorusu oluştur.\n\n"
        f"Zayıflık Kanıtı: {evidence}\n"
        f"İş Bağlamı: {job_context[:1000]}\n\n"
        "Soru şu kriterlere uymalı:\n"
        "- Direkt ve spesifik olmalı\n"
        "- STAR metodunu teşvik etmeli\n"
        "- Gerçek deneyim istemeli\n"
        "- Zorlayıcı ama adil olmalı\n\n"
        "Sadece soruyu döndür, açıklama yapma."
    )
    
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    body = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.4,
        "max_tokens": 200
    }
    
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post("https://api.openai.com/v1/chat/completions", json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Targeted question generation failed: {e}")
        return ""


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
