"""
Advanced Question Engine - High-quality, targeted interview questions
Generates industry-specific, competency-focused questions with dynamic difficulty
Focus: LLM-generated questions that naturally extract STAR components without asking explicitly
"""

from __future__ import annotations
import json
import random
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from src.services.llm_client import get_llm_client, LLMRequest


class QuestionType(str, Enum):
    BEHAVIORAL = "behavioral"
    TECHNICAL = "technical"
    SITUATIONAL = "situational"
    COMPETENCY = "competency"
    CULTURE_FIT = "culture_fit"
    LEADERSHIP = "leadership"
    PROBLEM_SOLVING = "problem_solving"


class DifficultyLevel(str, Enum):
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    EXPERT = "expert"


class IndustryType(str, Enum):
    TECH = "tech"
    FINANCE = "finance"
    HEALTHCARE = "healthcare"
    EDUCATION = "education"
    RETAIL = "retail"
    MANUFACTURING = "manufacturing"
    CONSULTING = "consulting"
    STARTUP = "startup"


@dataclass
class QuestionMetadata:
    """Metadata for interview questions"""
    question_type: QuestionType
    difficulty: DifficultyLevel
    industry: Optional[IndustryType] = None
    competencies: List[str] = field(default_factory=list)
    time_estimate_minutes: int = 3
    follow_up_indicators: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)


@dataclass
class GeneratedQuestion:
    """A generated interview question with metadata"""
    question: str
    context: str
    metadata: QuestionMetadata
    follow_up_questions: List[str] = field(default_factory=list)
    evaluation_rubric: Dict[str, str] = field(default_factory=dict)
    red_flags: List[str] = field(default_factory=list)
    ideal_response_indicators: List[str] = field(default_factory=list)


class AdvancedQuestionEngine:
    """
    Advanced question generation with industry expertise and competency focus
    """
    
    def __init__(self):
        self.llm_client = get_llm_client()
        self.fallback_questions = self._initialize_fallback_questions()
    
    def _initialize_fallback_questions(self) -> Dict[str, List[str]]:
        """Initialize minimal fallback questions - LLM should generate most questions"""
        return {
            QuestionType.TECHNICAL.value: [
                "Kariyerinizdeki en zorlu teknik problemi nasıl çözdünüz?",
                "Hangi teknoloji kararından en çok öğrendiniz?"
            ],
            QuestionType.BEHAVIORAL.value: [
                "İş hayatınızda karşılaştığınız en zor durumu nasıl aştınız?",
                "Takım içinde anlaşmazlık yaşadığınız bir deneyiminizi anlatır mısınız?"
            ],
            QuestionType.SITUATIONAL.value: [
                "Beklenmedik bir sorunla karşılaştığınızda nasıl yaklaşırsınız?",
                "Priorileleri nasıl belirlersiniz?"
            ]
        }
    
    def _detect_industry_from_job(self, job_description: str) -> IndustryType:
        """Detect industry from job description"""
        job_lower = job_description.lower()
        
        if any(keyword in job_lower for keyword in ["fintech", "banking", "financial", "trading", "investment"]):
            return IndustryType.FINANCE
        elif any(keyword in job_lower for keyword in ["startup", "scale-up", "early stage", "seed"]):
            return IndustryType.STARTUP
        elif any(keyword in job_lower for keyword in ["healthcare", "medical", "hospital", "clinic"]):
            return IndustryType.HEALTHCARE
        elif any(keyword in job_lower for keyword in ["retail", "e-commerce", "shopping", "consumer"]):
            return IndustryType.RETAIL
        elif any(keyword in job_lower for keyword in ["education", "university", "school", "learning"]):
            return IndustryType.EDUCATION
        elif any(keyword in job_lower for keyword in ["consulting", "advisory", "strategy"]):
            return IndustryType.CONSULTING
        else:
            return IndustryType.TECH  # Default to tech
    
    def _determine_difficulty_level(self, job_description: str, resume_text: str) -> DifficultyLevel:
        """Determine appropriate difficulty level based on job and candidate profile"""
        job_lower = job_description.lower()
        resume_lower = resume_text.lower()
        
        # Check job level indicators
        job_score = 0
        if any(keyword in job_lower for keyword in ["senior", "lead", "principal", "architect", "director"]):
            job_score += 2
        elif any(keyword in job_lower for keyword in ["mid-level", "intermediate", "experienced"]):
            job_score += 1
        
        # Check experience indicators in resume
        experience_score = 0
        if "years experience" in resume_lower or "years of experience" in resume_lower:
            import re
            years_match = re.search(r"(\d+)\s*(?:years?|yıl)", resume_lower)
            if years_match:
                years = int(years_match.group(1))
                if years >= 8:
                    experience_score += 2
                elif years >= 4:
                    experience_score += 1
        
        total_score = job_score + experience_score
        
        if total_score >= 3:
            return DifficultyLevel.SENIOR
        elif total_score >= 2:
            return DifficultyLevel.MID
        else:
            return DifficultyLevel.JUNIOR
    
    def _extract_key_competencies(self, job_description: str) -> List[str]:
        """Extract key competencies from job description"""
        competencies = []
        job_lower = job_description.lower()
        
        # Technical competencies
        if any(tech in job_lower for tech in ["python", "javascript", "java", "react", "node", "aws"]):
            competencies.append("Technical Proficiency")
        
        if any(keyword in job_lower for keyword in ["lead", "mentor", "guide", "manage"]):
            competencies.append("Leadership")
        
        if any(keyword in job_lower for keyword in ["architecture", "design", "system", "scalable"]):
            competencies.append("System Design")
        
        if any(keyword in job_lower for keyword in ["problem", "solve", "troubleshoot", "debug"]):
            competencies.append("Problem Solving")
        
        if any(keyword in job_lower for keyword in ["communicate", "collaborate", "team", "stakeholder"]):
            competencies.append("Communication")
        
        if any(keyword in job_lower for keyword in ["agile", "scrum", "project", "delivery"]):
            competencies.append("Project Management")
        
        return competencies
    
    async def _generate_smart_question(
        self, 
        question_type: QuestionType, 
        industry: IndustryType, 
        difficulty: DifficultyLevel,
        job_description: str,
        competencies: List[str],
        conversation_history: List[Dict[str, Any]]
    ) -> GeneratedQuestion:
        """Generate a smart question using LLM that naturally extracts STAR components"""
        
        # Build context for question generation
        prompt = f"""Sen dünyaca ünlü bir mülakat uzmanısın. {industry.value} sektöründe, {difficulty.value} seviye için {question_type.value} tipinde bir mülakat sorusu oluştur.

TEMEL PRENSIP: 
- STAR metodunu adaya SÖYLEMEYECEKSİN
- Sorun doğal olarak STAR bileşenlerini (Durum, Görev, Eylem, Sonuç) çıkaracak şekilde olmalı
- Aday fark etmeden somut örnekler vermeye yönlendirilmeli

CONTEXT:
- Sektör: {industry.value}
- Seviye: {difficulty.value} 
- Soru tipi: {question_type.value}
- Hedef yetkinlikler: {', '.join(competencies)}
- Konuşma geçmişi: {len(conversation_history)} soru soruldu

İŞ TANIMI (Referans için):
{job_description[:2000]}

SORU ÖZELLİKLERİ:
1. Somut durum/proje sorulsun ("en zorlu", "en başarılı", "kritik bir durumda")
2. Süreç ve eylemler doğal olarak çıksın ("nasıl çözdünüz", "ne yaptınız", "hangi adımları")
3. Sonuçlar ve öğrenmeler sorulsun ("sonuç ne oldu", "ne öğrendiniz")
4. Real-world senaryoları kullansın
5. Detay isteyici olsun ama STAR kelimesini GEÇMESİN

ÖRNEK TİPLER:
- Behavioral: "En zorlu takım konfliktini nasıl çözdünüz?" (durumu, yaptıklarını, sonucu doğal çıkarır)
- Technical: "Production'da kritik hatayı nasıl tespit edip düzelttiniz?" (süreci doğal çıkarır)
- Problem Solving: "Beklenmedik sistem yavaşlığını nasıl analiz ettiniz?" (yaklaşımı çıkarır)

ZORUNLU JSON FORMAT:
{{
  "question": "Ana mülakat sorusu (Türkçe, net ve doğal)",
  "context": "Bu sorunun amacı ve hangi STAR bileşenlerini çıkaracağı",
  "follow_up_questions": [
    "Bu durumda hangi alternatifleri değerlendirdiniz?",
    "Sonuçları nasıl ölçtünüz?",
    "Bu deneyimden hangi dersleri çıkardınız?",
    "Benzer durumda ne farklı yaparsınız?"
  ],
  "evaluation_rubric": {{
    "excellent": "Detaylı durum, net eylemler, ölçülebilir sonuçlar, öz-değerlendirme",
    "good": "Somut örnek, temel eylemler, genel sonuçlar",
    "poor": "Belirsiz örnek, eksik detay, sonuçsuz anlatım"
  }},
  "red_flags": [
    "Somut örnek verememe",
    "Sorumluluk almaktan kaçınma",
    "Sonuçları paylaşmama",
    "Öğrenme çıkarımı yok"
  ],
  "ideal_response_indicators": [
    "Spesifik durum/proje tarifi",
    "Net eylem ve kararlar",
    "Ölçülebilir sonuçlar",
    "Öğrenme ve gelişim farkındalığı"
  ]
}}

ÖNEMLİ: STAR metodunu, Situation/Task/Action/Result kelimelerini kullanma. Sadece doğal sorularla bu bilgileri çıkar."""

        try:
            response = await self.llm_client.generate(LLMRequest(
                prompt=prompt,
                temperature=0.3,
                response_format={"type": "json_object"}
            ))
            
            result = json.loads(response.content)
            
            metadata = QuestionMetadata(
                question_type=question_type,
                difficulty=difficulty,
                industry=industry,
                competencies=competencies,
                time_estimate_minutes=4 if difficulty in [DifficultyLevel.SENIOR, DifficultyLevel.LEAD] else 3
            )
            
            return GeneratedQuestion(
                question=result.get("question", ""),
                context=result.get("context", ""),
                metadata=metadata,
                follow_up_questions=result.get("follow_up_questions", []),
                evaluation_rubric=result.get("evaluation_rubric", {}),
                red_flags=result.get("red_flags", []),
                ideal_response_indicators=result.get("ideal_response_indicators", [])
            )
            
        except Exception as e:
            # Fallback to template-based question
            return self._get_fallback_question(question_type, industry, difficulty, competencies)
    
    def _get_fallback_question(
        self, 
        question_type: QuestionType, 
        industry: IndustryType, 
        difficulty: DifficultyLevel,
        competencies: List[str]
    ) -> GeneratedQuestion:
        """Get a fallback question when LLM generation fails"""
        
        type_questions = self.fallback_questions.get(question_type.value, [])
        
        if not type_questions:
            # Generic fallback questions
            type_questions = [
                "Kariyerinizdeki en zorlu projeyi nasıl yönettiniz?",
                "Takım içinde çatışma yaşadığınız bir durumu nasıl çözdünüz?",
                "Başarısız olduğunuz bir deneyimden ne öğrendiniz?"
            ]
        
        question = random.choice(type_questions)
        
        metadata = QuestionMetadata(
            question_type=question_type,
            difficulty=difficulty,
            industry=industry,
            competencies=competencies
        )
        
        return GeneratedQuestion(
            question=question,
            context=f"Bu soru {question_type.value} değerlendirmesi için tasarlandı",
            metadata=metadata,
            follow_up_questions=[
                "Bu durumda farklı ne yapabilirdiniz?",
                "Sonuçları nasıl ölçtünüz?",
                "Bu deneyimden hangi dersleri çıkardınız?",
                "Benzer durumda ne farklı yaparsınız?"
            ],
            evaluation_rubric={
                "excellent": "Detaylı, yapılandırılmış, öz-farkındalık içeren cevap",
                "good": "Net örnek, öğrenme çıkarımları mevcut",
                "poor": "Belirsiz, sorumluluğu üstlenmeyen, yüzeysel cevap"
            }
        )
    
    async def generate_strategic_question(
        self,
        job_description: str,
        resume_text: str = "",
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        focus_competency: Optional[str] = None
    ) -> GeneratedQuestion:
        """
        Generate strategic, high-quality interview question that naturally extracts STAR components
        """
        if conversation_history is None:
            conversation_history = []
        
        # Analyze context
        industry = self._detect_industry_from_job(job_description)
        difficulty = self._determine_difficulty_level(job_description, resume_text)
        competencies = self._extract_key_competencies(job_description)
        
        if focus_competency:
            competencies = [focus_competency] + competencies
        
        # Determine optimal question type based on conversation flow
        question_count = len([msg for msg in conversation_history if msg.get("role") == "assistant"])
        
        if question_count == 0:
            # Opening question - usually behavioral
            question_type = QuestionType.BEHAVIORAL
        elif question_count <= 2:
            # Early questions - mix of technical and competency
            question_type = random.choice([QuestionType.TECHNICAL, QuestionType.COMPETENCY])
        elif question_count <= 4:
            # Middle questions - situational and problem solving
            question_type = random.choice([QuestionType.SITUATIONAL, QuestionType.PROBLEM_SOLVING])
        else:
            # Later questions - culture fit and leadership
            question_type = random.choice([QuestionType.CULTURE_FIT, QuestionType.LEADERSHIP])
        
        return await self._generate_smart_question(
            question_type=question_type,
            industry=industry,
            difficulty=difficulty,
            job_description=job_description,
            competencies=competencies,
            conversation_history=conversation_history
        )
    
    async def generate_follow_up_question(
        self,
        original_question: str,
        candidate_answer: str,
        focus_area: str
    ) -> str:
        """Generate intelligent follow-up question that probes deeper into STAR components"""
        
        prompt = f"""Sen deneyimli bir mülakat uzmanısın. Adayın verdiği cevaba göre daha derin bilgi alacak, STAR bileşenlerini tamamlayacak follow-up sorusu oluştur.

ORIJINAL SORU: {original_question}

ADAYIN CEVABI: {candidate_answer}

FOCUS AREA: {focus_area}

HEDEF: Eksik STAR bileşenlerini doğal sorularla tamamla:
- Eğer durum belirsizse: "Bu problemin ortaya çıkma sebebi neydi?" 
- Eğer eylemler eksikse: "Hangi alternatifleri değerlendirdiniz?"
- Eğer sonuç yoksa: "Bu çözümün etkisini nasıl ölçtünüz?"
- Eğer öğrenme yoksa: "Bu deneyimden ne çıkardınız?"

FOLLOW-UP SORU KRİTERLERİ:
1. STAR kelimelerini kullanma
2. Doğal ve akıcı ol
3. Somut detay iste
4. Daha derin insight çıkar
5. Öz-farkındalığı test et

Sadece follow-up sorusunu dön, başka açıklama yapma."""

        try:
            response = await self.llm_client.generate(LLMRequest(
                prompt=prompt,
                temperature=0.4,
                max_tokens=150
            ))
            
            return response.content.strip()
            
        except Exception:
            # Fallback follow-up questions that naturally probe STAR components
            fallbacks = [
                "Bu durumda farklı ne yapabilirdiniz?",
                "Sonuçları nasıl ölçtünüz?",
                "Bu deneyimden hangi dersleri çıkardınız?",
                "Benzer bir durumla tekrar karşılaştığınızda ne yaparsınız?",
                "Bu süreçte en zorlu kısım neydi ve nasıl aştınız?"
            ]
            return random.choice(fallbacks)
    
    def get_question_analytics(self, questions: List[GeneratedQuestion]) -> Dict[str, Any]:
        """Analyze generated questions for quality metrics"""
        
        if not questions:
            return {}
        
        types_distribution = {}
        difficulty_distribution = {}
        industry_distribution = {}
        
        for q in questions:
            # Type distribution
            q_type = q.metadata.question_type.value
            types_distribution[q_type] = types_distribution.get(q_type, 0) + 1
            
            # Difficulty distribution  
            difficulty = q.metadata.difficulty.value
            difficulty_distribution[difficulty] = difficulty_distribution.get(difficulty, 0) + 1
            
            # Industry distribution
            if q.metadata.industry:
                industry = q.metadata.industry.value
                industry_distribution[industry] = industry_distribution.get(industry, 0) + 1
        
        return {
            "total_questions": len(questions),
            "type_distribution": types_distribution,
            "difficulty_distribution": difficulty_distribution,
            "industry_distribution": industry_distribution,
            "avg_estimated_time": sum(q.metadata.time_estimate_minutes for q in questions) / len(questions),
            "competency_coverage": list(set(
                comp for q in questions for comp in q.metadata.competencies
            ))
        }


# Factory function
def create_advanced_question_engine() -> AdvancedQuestionEngine:
    """Create AdvancedQuestionEngine instance"""
    return AdvancedQuestionEngine()