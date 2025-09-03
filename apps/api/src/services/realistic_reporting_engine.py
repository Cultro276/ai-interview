"""
Realistic Reporting Engine - Accurate, detailed interview analysis and reporting
Provides industry-benchmarked scoring with confidence intervals and actionable insights
"""

from __future__ import annotations
import json
import statistics
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import re

from src.services.llm_client import get_llm_client, LLMRequest


class ConfidenceLevel(str, Enum):
    VERY_HIGH = "very_high"    # 90%+ confidence
    HIGH = "high"              # 70-90% confidence  
    MEDIUM = "medium"          # 50-70% confidence
    LOW = "low"                # 30-50% confidence
    VERY_LOW = "very_low"      # <30% confidence


class EvidenceQuality(str, Enum):
    STRONG = "strong"          # Multiple concrete examples with details
    MODERATE = "moderate"      # Some examples with reasonable detail
    WEAK = "weak"             # Vague examples, limited detail
    INSUFFICIENT = "insufficient"  # No clear examples or evidence


class BiasIndicator(str, Enum):
    HALO_EFFECT = "halo_effect"
    CONFIRMATION_BIAS = "confirmation_bias"
    RECENCY_BIAS = "recency_bias"
    SIMILARITY_BIAS = "similarity_bias"
    CONTRAST_EFFECT = "contrast_effect"


@dataclass
class EvidenceItem:
    """Specific evidence supporting a score or assessment"""
    source_text: str
    strength: EvidenceQuality
    competency: str
    positive: bool  # True if supports competency, False if indicates weakness
    context: str = ""
    timestamp_in_interview: Optional[int] = None


@dataclass
class ScoreWithConfidence:
    """Score with confidence interval and supporting evidence"""
    score: float  # 0-100
    confidence_level: ConfidenceLevel
    confidence_percentage: float  # Numeric confidence 0-100
    evidence_items: List[EvidenceItem] = field(default_factory=list)
    reasoning: str = ""
    improvement_potential: float = 0.0  # How much score could realistically improve
    benchmark_percentile: Optional[float] = None  # Industry percentile ranking


@dataclass
class DetailedAssessment:
    """Comprehensive assessment with multiple dimensions"""
    overall_score: ScoreWithConfidence
    technical_competency: ScoreWithConfidence
    behavioral_competency: ScoreWithConfidence
    communication_effectiveness: ScoreWithConfidence
    problem_solving_approach: ScoreWithConfidence
    cultural_alignment: ScoreWithConfidence
    growth_potential: ScoreWithConfidence
    leadership_indicators: ScoreWithConfidence
    
    # Risk assessment
    potential_red_flags: List[str] = field(default_factory=list)
    bias_indicators: List[BiasIndicator] = field(default_factory=list)
    
    # Benchmarking
    industry_comparison: Dict[str, float] = field(default_factory=dict)
    role_level_comparison: Dict[str, float] = field(default_factory=dict)


@dataclass
class ActionableRecommendation:
    """Specific, actionable recommendation"""
    category: str  # "hire", "development", "further_assessment", "rejection"
    priority: str  # "high", "medium", "low"
    recommendation: str
    reasoning: str
    timeline: str  # "immediate", "3_months", "6_months", etc.
    success_metrics: List[str] = field(default_factory=list)
    resources_needed: List[str] = field(default_factory=list)


class RealisticReportingEngine:
    """
    Advanced reporting engine with realistic, evidence-based assessments
    """
    
    def __init__(self):
        self.llm_client = get_llm_client()
        self.industry_benchmarks = self._load_industry_benchmarks()
        self.role_benchmarks = self._load_role_benchmarks()
    
    def _load_industry_benchmarks(self) -> Dict[str, Dict[str, float]]:
        """Load industry-specific performance benchmarks"""
        return {
            "tech": {
                "technical_competency": 75.0,
                "problem_solving": 72.0,
                "communication": 68.0,
                "leadership": 65.0,
                "cultural_alignment": 70.0
            },
            "finance": {
                "technical_competency": 78.0,
                "problem_solving": 75.0,
                "communication": 72.0,
                "leadership": 68.0,
                "cultural_alignment": 75.0
            },
            "startup": {
                "technical_competency": 70.0,
                "problem_solving": 78.0,
                "communication": 75.0,
                "leadership": 72.0,
                "cultural_alignment": 68.0
            }
        }
    
    def _load_role_benchmarks(self) -> Dict[str, Dict[str, float]]:
        """Load role-level performance benchmarks"""
        return {
            "junior": {
                "technical_competency": 60.0,
                "problem_solving": 58.0,
                "communication": 65.0,
                "leadership": 45.0,
                "cultural_alignment": 70.0
            },
            "mid": {
                "technical_competency": 72.0,
                "problem_solving": 70.0,
                "communication": 68.0,
                "leadership": 58.0,
                "cultural_alignment": 72.0
            },
            "senior": {
                "technical_competency": 82.0,
                "problem_solving": 80.0,
                "communication": 75.0,
                "leadership": 70.0,
                "cultural_alignment": 75.0
            },
            "lead": {
                "technical_competency": 85.0,
                "problem_solving": 85.0,
                "communication": 82.0,
                "leadership": 80.0,
                "cultural_alignment": 78.0
            }
        }
    
    def _extract_evidence_from_transcript(self, transcript: str, competency: str) -> List[EvidenceItem]:
        """Extract specific evidence items from interview transcript"""
        evidence_items = []
        
        # Split transcript into Q&A pairs
        qa_pairs = self._split_transcript_to_qa(transcript)
        
        for i, (question, answer) in enumerate(qa_pairs):
            if not answer.strip():
                continue
                
            # Look for evidence indicators
            evidence = self._analyze_answer_for_evidence(answer, competency, i)
            if evidence:
                evidence_items.extend(evidence)
        
        return evidence_items
    
    def _split_transcript_to_qa(self, transcript: str) -> List[Tuple[str, str]]:
        """Split transcript into question-answer pairs"""
        lines = transcript.split('\n')
        qa_pairs = []
        current_question = ""
        current_answer = ""
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.startswith(('Interviewer:', 'interviewer:', 'INTERVIEWER:')):
                if current_question and current_answer:
                    qa_pairs.append((current_question, current_answer))
                current_question = line
                current_answer = ""
            elif line.startswith(('Candidate:', 'candidate:', 'CANDIDATE:')):
                current_answer = line
            elif current_answer:
                current_answer += " " + line
        
        if current_question and current_answer:
            qa_pairs.append((current_question, current_answer))
        
        return qa_pairs
    
    def _analyze_answer_for_evidence(self, answer: str, competency: str, position: int) -> List[EvidenceItem]:
        """Analyze answer for evidence of specific competency"""
        evidence_items = []
        answer_lower = answer.lower()
        
        # Evidence strength indicators
        concrete_indicators = ['örneğin', 'mesela', 'geçen', 'bir keresinde', 'projede', 'şirkette', 'takımda']
        detail_indicators = ['çünkü', 'nedeni', 'sonuçta', 'böylece', 'dolayısıyla']
        quantified_indicators = ['%', 'saat', 'gün', 'hafta', 'ay', 'yıl', 'kişi', 'ekip']
        
        has_concrete = any(indicator in answer_lower for indicator in concrete_indicators)
        has_detail = any(indicator in answer_lower for indicator in detail_indicators)
        has_quantified = any(indicator in answer_lower for indicator in quantified_indicators)
        
        # Determine evidence quality
        if has_concrete and has_detail and has_quantified:
            quality = EvidenceQuality.STRONG
        elif (has_concrete and has_detail) or (has_concrete and has_quantified):
            quality = EvidenceQuality.MODERATE
        elif has_concrete:
            quality = EvidenceQuality.WEAK
        else:
            quality = EvidenceQuality.INSUFFICIENT
        
        # Determine if evidence supports competency (positive) or indicates weakness (negative)
        negative_indicators = ['zorlandım', 'başaramadım', 'problem yaşadım', 'hata yaptım', 'bilmiyordum']
        positive_indicators = ['başardım', 'çözdüm', 'geliştirdim', 'organize ettim', 'liderlik yaptım']
        
        has_negative = any(indicator in answer_lower for indicator in negative_indicators)
        has_positive = any(indicator in answer_lower for indicator in positive_indicators)
        
        if quality != EvidenceQuality.INSUFFICIENT:
            evidence_items.append(EvidenceItem(
                source_text=answer[:200] + "..." if len(answer) > 200 else answer,
                strength=quality,
                competency=competency,
                positive=has_positive or not has_negative,  # Default to positive unless clearly negative
                timestamp_in_interview=position
            ))
        
        return evidence_items
    
    def _calculate_confidence(self, evidence_items: List[EvidenceItem], answer_count: int) -> Tuple[ConfidenceLevel, float]:
        """Calculate confidence level based on evidence quality and quantity"""
        if not evidence_items:
            return ConfidenceLevel.VERY_LOW, 15.0
        
        strong_evidence = len([e for e in evidence_items if e.strength == EvidenceQuality.STRONG])
        moderate_evidence = len([e for e in evidence_items if e.strength == EvidenceQuality.MODERATE])
        weak_evidence = len([e for e in evidence_items if e.strength == EvidenceQuality.WEAK])
        
        evidence_score = strong_evidence * 3 + moderate_evidence * 2 + weak_evidence * 1
        sample_size_factor = min(answer_count / 5, 1.0)  # Normalize by expected answer count
        
        confidence_score = evidence_score * sample_size_factor
        
        if confidence_score >= 8:
            return ConfidenceLevel.VERY_HIGH, 90.0
        elif confidence_score >= 6:
            return ConfidenceLevel.HIGH, 75.0
        elif confidence_score >= 4:
            return ConfidenceLevel.MEDIUM, 60.0
        elif confidence_score >= 2:
            return ConfidenceLevel.LOW, 40.0
        else:
            return ConfidenceLevel.VERY_LOW, 25.0
    
    async def _generate_detailed_score_analysis(
        self, 
        competency: str,
        transcript: str,
        job_description: str,
        industry: str,
        role_level: str
    ) -> ScoreWithConfidence:
        """Generate detailed, evidence-based score for specific competency"""
        
        # Extract evidence from transcript
        evidence_items = self._extract_evidence_from_transcript(transcript, competency)
        
        # Calculate confidence
        qa_count = len(self._split_transcript_to_qa(transcript))
        confidence_level, confidence_percentage = self._calculate_confidence(evidence_items, qa_count)
        
        # Generate LLM-based score with detailed reasoning
        prompt = f"""Sen expert bir HR assessment uzmanısın. Aşağıdaki mülakat transkriptini analiz et ve {competency} yetkinliği için kanıt-temelli skorlama yap.

COMPETENCY: {competency}
INDUSTRY: {industry}
ROLE LEVEL: {role_level}

ANALYSIS METHOD: 
- Adayın cevaplarından DURUM, EYLEM, SONUÇ bileşenlerini çıkar
- Her competency için somut örnekleri tespit et
- Detay seviyesi ve tutarlılığı değerlendir

ASSESSMENT KRİTERLERİ:
1. Somut durum/proje örnekleri (context kalitesi)
2. Net eylemler ve kararlar (implementation kalitesi)  
3. Ölçülebilir sonuçlar (impact kalitesi)
4. Öz-farkındalık ve öğrenme (growth mindset)
5. İş gereksinimlerine uygunluk

TRANSCRIPT (ilgili bölümler):
{transcript[:4000]}

JOB REQUIREMENTS:
{job_description[:1500]}

ZORUNLU JSON FORMAT:
{{
  "score": 75.5,
  "reasoning": "Hangi cevaplarda hangi kanıtları buldun - spesifik örneklerle",
  "key_strengths": ["Somut güçlü yönler - transkriptten örneklerle"],
  "improvement_areas": ["Eksik veya zayıf alanlar"],
  "evidence_quality": "strong|moderate|weak|insufficient",
  "improvement_potential": 15.5,
  "specific_examples_found": ["Transkriptten çıkardığın konkret durumlar"],
  "missing_elements": ["Bu competency için eksik kalan unsurlar"],
  "context_examples": ["Verdiği durumsal örnekler"],
  "action_examples": ["Söylediği spesifik eylemler"],
  "result_examples": ["Bahsettiği sonuçlar ve etkiler"]
}}

PUANLAMA ÖLÇEĞİ (0-100):
- 90-100: Çok detaylı örnekler, net eylemler, ölçülebilir sonuçlar - sektör lideri
- 80-89: İyi örnekler, somut eylemler, genel sonuçlar - güçlü yetkinlik
- 70-79: Bazı örnekler, temel eylemler, kısmi sonuçlar - yeterli seviye
- 60-69: Az örnek, belirsiz eylemler, sınırlı sonuçlar - geliştirme gerekli
- 50-59: Minimal örnek, vague eylemler - yapılandırılmış geliştirme şart
- 0-49: Örnek yok, somut eylem yok - role uygun değil
"""
        
        try:
            response = await self.llm_client.generate(LLMRequest(
                prompt=prompt,
                temperature=0.1,
                response_format={"type": "json_object"}
            ))
            
            result = json.loads(response.content)
            
            # Get industry benchmark
            industry_benchmarks = self.industry_benchmarks.get(industry, {})
            role_benchmarks = self.role_benchmarks.get(role_level, {})
            
            competency_key = competency.lower().replace(' ', '_')
            industry_benchmark = industry_benchmarks.get(competency_key, 70.0)
            role_benchmark = role_benchmarks.get(competency_key, 70.0)
            
            # Calculate percentile ranking
            score = result.get("score", 70.0)
            benchmark_percentile = self._calculate_percentile_ranking(score, industry_benchmark, role_benchmark)
            
            return ScoreWithConfidence(
                score=score,
                confidence_level=confidence_level,
                confidence_percentage=confidence_percentage,
                evidence_items=evidence_items,
                reasoning=result.get("reasoning", ""),
                improvement_potential=result.get("improvement_potential", 10.0),
                benchmark_percentile=benchmark_percentile
            )
            
        except Exception as e:
            # Fallback scoring
            return self._fallback_scoring(competency, evidence_items, confidence_level, confidence_percentage)
    
    def _calculate_percentile_ranking(self, score: float, industry_benchmark: float, role_benchmark: float) -> float:
        """Calculate percentile ranking against industry and role benchmarks"""
        combined_benchmark = (industry_benchmark + role_benchmark) / 2
        
        if score >= combined_benchmark + 15:
            return 90.0
        elif score >= combined_benchmark + 10:
            return 80.0
        elif score >= combined_benchmark + 5:
            return 70.0
        elif score >= combined_benchmark:
            return 60.0
        elif score >= combined_benchmark - 5:
            return 50.0
        elif score >= combined_benchmark - 10:
            return 30.0
        else:
            return 15.0
    
    def _fallback_scoring(
        self, 
        competency: str, 
        evidence_items: List[EvidenceItem], 
        confidence_level: ConfidenceLevel,
        confidence_percentage: float
    ) -> ScoreWithConfidence:
        """Fallback scoring when LLM analysis fails"""
        
        if not evidence_items:
            score = 50.0
        else:
            positive_evidence = [e for e in evidence_items if e.positive]
            strong_evidence = [e for e in evidence_items if e.strength == EvidenceQuality.STRONG]
            
            base_score = 60.0
            if positive_evidence:
                base_score += len(positive_evidence) * 5
            if strong_evidence:
                base_score += len(strong_evidence) * 3
                
            score = min(base_score, 95.0)
        
        return ScoreWithConfidence(
            score=score,
            confidence_level=confidence_level,
            confidence_percentage=confidence_percentage,
            evidence_items=evidence_items,
            reasoning="Otomatik skorlama sistemi kullanıldı - LLM analizi mevcut değil",
            improvement_potential=15.0,
            benchmark_percentile=50.0
        )
    
    def _detect_bias_indicators(self, transcript: str, scores: Dict[str, ScoreWithConfidence]) -> List[BiasIndicator]:
        """Detect potential bias indicators in the assessment"""
        bias_indicators = []
        
        # Check for halo effect (all scores very similar and high)
        score_values = [s.score for s in scores.values()]
        if score_values:
            score_std = statistics.stdev(score_values) if len(score_values) > 1 else 0
            score_mean = statistics.mean(score_values)
            
            if score_std < 5 and score_mean > 80:
                bias_indicators.append(BiasIndicator.HALO_EFFECT)
        
        # Check for recency bias (later answers weighted more heavily)
        qa_pairs = self._split_transcript_to_qa(transcript)
        if len(qa_pairs) > 3:
            # Simple heuristic: if most evidence comes from later answers
            all_evidence = []
            for score in scores.values():
                all_evidence.extend(score.evidence_items)
            
            if all_evidence:
                late_evidence = [e for e in all_evidence if e.timestamp_in_interview and e.timestamp_in_interview > len(qa_pairs) / 2]
                if len(late_evidence) / len(all_evidence) > 0.7:
                    bias_indicators.append(BiasIndicator.RECENCY_BIAS)
        
        return bias_indicators
    
    async def generate_comprehensive_report(
        self,
        transcript: str,
        job_description: str,
        resume_text: str = "",
        industry: str = "tech",
        role_level: str = "mid",
        candidate_name: str = "Aday"
    ) -> DetailedAssessment:
        """
        Generate comprehensive, realistic interview report
        """
        
        # Core competencies to assess
        competencies = [
            "Technical Competency",
            "Behavioral Competency", 
            "Communication Effectiveness",
            "Problem Solving Approach",
            "Cultural Alignment",
            "Growth Potential",
            "Leadership Indicators"
        ]
        
        # Generate detailed scores for each competency
        detailed_scores = {}
        
        for competency in competencies:
            score = await self._generate_detailed_score_analysis(
                competency=competency,
                transcript=transcript,
                job_description=job_description,
                industry=industry,
                role_level=role_level
            )
            detailed_scores[competency.lower().replace(' ', '_')] = score
        
        # Calculate overall score with weighted average
        weights = {
            "technical_competency": 0.25,
            "behavioral_competency": 0.20,
            "communication_effectiveness": 0.15,
            "problem_solving_approach": 0.15,
            "cultural_alignment": 0.10,
            "growth_potential": 0.10,
            "leadership_indicators": 0.05
        }
        
        overall_score_value = sum(
            detailed_scores[comp].score * weight 
            for comp, weight in weights.items()
        )
        
        # Calculate overall confidence (conservative approach)
        confidence_values = [s.confidence_percentage for s in detailed_scores.values()]
        overall_confidence_percentage = min(confidence_values) if confidence_values else 50.0
        
        if overall_confidence_percentage >= 85:
            overall_confidence_level = ConfidenceLevel.VERY_HIGH
        elif overall_confidence_percentage >= 70:
            overall_confidence_level = ConfidenceLevel.HIGH
        elif overall_confidence_percentage >= 55:
            overall_confidence_level = ConfidenceLevel.MEDIUM
        elif overall_confidence_percentage >= 35:
            overall_confidence_level = ConfidenceLevel.LOW
        else:
            overall_confidence_level = ConfidenceLevel.VERY_LOW
        
        # Create overall score
        overall_score = ScoreWithConfidence(
            score=overall_score_value,
            confidence_level=overall_confidence_level,
            confidence_percentage=overall_confidence_percentage,
            reasoning="Ağırlıklı ortalama ile hesaplanmış genel skor"
        )
        
        # Detect potential biases
        bias_indicators = self._detect_bias_indicators(transcript, detailed_scores)
        
        # Generate red flags
        red_flags = await self._identify_red_flags(transcript, detailed_scores)
        
        # Industry and role comparisons
        industry_comparison = self._generate_industry_comparison(detailed_scores, industry)
        role_comparison = self._generate_role_comparison(detailed_scores, role_level)
        
        return DetailedAssessment(
            overall_score=overall_score,
            technical_competency=detailed_scores["technical_competency"],
            behavioral_competency=detailed_scores["behavioral_competency"],
            communication_effectiveness=detailed_scores["communication_effectiveness"],
            problem_solving_approach=detailed_scores["problem_solving_approach"],
            cultural_alignment=detailed_scores["cultural_alignment"],
            growth_potential=detailed_scores["growth_potential"],
            leadership_indicators=detailed_scores["leadership_indicators"],
            potential_red_flags=red_flags,
            bias_indicators=bias_indicators,
            industry_comparison=industry_comparison,
            role_level_comparison=role_comparison
        )
    
    async def _identify_red_flags(self, transcript: str, scores: Dict[str, ScoreWithConfidence]) -> List[str]:
        """Identify potential red flags in the interview"""
        red_flags = []
        
        # Score-based red flags
        for comp_name, score in scores.items():
            if score.score < 40:
                red_flags.append(f"{comp_name.replace('_', ' ').title()}: Kritik düşük skor ({score.score:.1f})")
            
            if score.confidence_level in [ConfidenceLevel.VERY_LOW, ConfidenceLevel.LOW]:
                red_flags.append(f"{comp_name.replace('_', ' ').title()}: Yetersiz kanıt/belirsiz cevaplar")
        
        # Content-based red flags  
        transcript_lower = transcript.lower()
        
        content_red_flags = [
            ("Sorumluluk almaktan kaçınma", ["başkasının hatası", "benim suçum değil", "sorumluluğum değildi"]),
            ("Negatif attitude", ["berbat", "kötü", "nefret", "dayanamam"]),
            ("İletişim sorunları", ["anlamadım", "bilmiyorum", "ne soruyorsun"]),
            ("Takım çalışması problemleri", ["tek başıma çalışırım", "takımdan hoşlanmam", "çatışma yaşarım"])
        ]
        
        for flag_name, indicators in content_red_flags:
            if any(indicator in transcript_lower for indicator in indicators):
                red_flags.append(flag_name)
        
        return red_flags
    
    def _generate_industry_comparison(self, scores: Dict[str, ScoreWithConfidence], industry: str) -> Dict[str, float]:
        """Generate industry comparison percentiles"""
        industry_benchmarks = self.industry_benchmarks.get(industry, self.industry_benchmarks["tech"])
        
        comparison = {}
        for comp_name, score in scores.items():
            benchmark = industry_benchmarks.get(comp_name, 70.0)
            percentile = self._calculate_percentile_ranking(score.score, benchmark, benchmark)
            comparison[comp_name] = percentile
        
        return comparison
    
    def _generate_role_comparison(self, scores: Dict[str, ScoreWithConfidence], role_level: str) -> Dict[str, float]:
        """Generate role level comparison percentiles"""
        role_benchmarks = self.role_benchmarks.get(role_level, self.role_benchmarks["mid"])
        
        comparison = {}
        for comp_name, score in scores.items():
            benchmark = role_benchmarks.get(comp_name, 70.0)
            percentile = self._calculate_percentile_ranking(score.score, benchmark, benchmark)
            comparison[comp_name] = percentile
        
        return comparison
    
    async def generate_actionable_recommendations(self, assessment: DetailedAssessment, job_description: str) -> List[ActionableRecommendation]:
        """Generate specific, actionable recommendations"""
        recommendations = []
        
        # Hiring recommendation based on overall score and confidence
        overall_score = assessment.overall_score.score
        confidence = assessment.overall_score.confidence_percentage
        
        if overall_score >= 80 and confidence >= 70:
            recommendations.append(ActionableRecommendation(
                category="hire",
                priority="high", 
                recommendation="Kesinlikle işe alın - güçlü profil ve yüksek potansiyel",
                reasoning=f"Genel skor {overall_score:.1f}, güven seviyesi {confidence:.1f}%",
                timeline="immediate",
                success_metrics=["İlk 3 ayda proje teslimi", "Takım entegrasyonu"],
                resources_needed=["Onboarding programı", "Mentor ataması"]
            ))
        elif overall_score >= 65 and confidence >= 60:
            recommendations.append(ActionableRecommendation(
                category="hire",
                priority="medium",
                recommendation="Koşullu işe alım - gelişim planı ile birlikte",
                reasoning=f"Yeterli skor ({overall_score:.1f}) ancak belirli alanlarda geliştirme gerekli",
                timeline="immediate", 
                success_metrics=["90 günlük gelişim planı tamamlama", "Hedef skorlara ulaşma"],
                resources_needed=["Structured training", "Regular feedback"]
            ))
        elif overall_score >= 50:
            recommendations.append(ActionableRecommendation(
                category="further_assessment",
                priority="medium",
                recommendation="Ek değerlendirme gerekli - teknik test veya 2. mülakat",
                reasoning=f"Orta seviye skor ({overall_score:.1f}), daha fazla veri gerekli",
                timeline="1_week",
                success_metrics=["Ek değerlendirme sonuçları", "Reference check"],
                resources_needed=["Teknik assessment", "Panel interview"]
            ))
        else:
            recommendations.append(ActionableRecommendation(
                category="rejection",
                priority="high",
                recommendation="Bu pozisyon için uygun değil",
                reasoning=f"Düşük skor ({overall_score:.1f}) ve kritik eksiklikler",
                timeline="immediate",
                success_metrics=["Feedback verilmesi"],
                resources_needed=["Constructive feedback preparation"]
            ))
        
        # Specific development recommendations based on weak areas
        competency_scores = {
            "Technical": assessment.technical_competency.score,
            "Behavioral": assessment.behavioral_competency.score,
            "Communication": assessment.communication_effectiveness.score,
            "Problem Solving": assessment.problem_solving_approach.score,
            "Leadership": assessment.leadership_indicators.score
        }
        
        for comp_name, score in competency_scores.items():
            if score < 60:
                recommendations.append(ActionableRecommendation(
                    category="development",
                    priority="high" if score < 45 else "medium",
                    recommendation=f"{comp_name} alanında yoğun geliştirme programı",
                    reasoning=f"Düşük skor: {score:.1f}",
                    timeline="3_months",
                    success_metrics=[f"{comp_name} skorunda %20 artış"],
                    resources_needed=["Specialized training", "Mentoring", "Practice opportunities"]
                ))
        
        return recommendations


# Factory function
def create_realistic_reporting_engine() -> RealisticReportingEngine:
    """Create RealisticReportingEngine instance"""
    return RealisticReportingEngine()
