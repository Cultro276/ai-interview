"""
Premium Interview Service - Integration of advanced question generation and realistic reporting
Provides highest quality interview experience with intelligent questions and detailed analysis
"""

from __future__ import annotations
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.db.models.interview import Interview
from src.db.models.job import Job
from src.db.models.candidate import Candidate
from src.db.models.candidate_profile import CandidateProfile
from src.db.models.conversation import ConversationMessage, InterviewAnalysis

from src.services.advanced_question_engine import (
    AdvancedQuestionEngine, 
    GeneratedQuestion, 
    create_advanced_question_engine
)
from src.services.realistic_reporting_engine import (
    RealisticReportingEngine, 
    DetailedAssessment, 
    ActionableRecommendation,
    create_realistic_reporting_engine
)
from src.services.interview_engine import InterviewContext
from src.core.monitoring import monitor_process_stage


@dataclass
class PremiumInterviewSession:
    """Premium interview session with advanced features"""
    interview_id: int
    context: InterviewContext
    generated_questions: List[GeneratedQuestion]
    current_question_index: int = 0
    question_analytics: Optional[Dict[str, Any]] = None
    adaptive_difficulty: bool = True
    focus_competencies: Optional[List[str]] = None


class PremiumInterviewService:
    """
    Premium interview service combining advanced question generation 
    with realistic reporting for highest quality interviews
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.question_engine = create_advanced_question_engine()
        self.reporting_engine = create_realistic_reporting_engine()
    
    @monitor_process_stage("load_premium_context")
    async def _load_interview_context(self, interview_id: int) -> InterviewContext:
        """Load complete interview context with enhanced data"""
        
        # Get interview
        interview = (
            await self.session.execute(
                select(Interview).where(Interview.id == interview_id)
            )
        ).scalar_one_or_none()
        
        if not interview:
            raise ValueError(f"Interview {interview_id} not found")
        
        # Get job with enhanced details
        job = (
            await self.session.execute(
                select(Job).where(Job.id == interview.job_id)
            )
        ).scalar_one_or_none()
        
        # Get candidate and profile
        candidate = (
            await self.session.execute(
                select(Candidate).where(Candidate.id == interview.candidate_id)
            )
        ).scalar_one_or_none()
        
        resume_text = ""
        candidate_name = ""
        if candidate:
            candidate_name = candidate.name or "Unknown"
            profile = (
                await self.session.execute(
                    select(CandidateProfile).where(CandidateProfile.candidate_id == candidate.id)
                )
            ).scalar_one_or_none()
            if profile and profile.resume_text:
                resume_text = profile.resume_text
        
        # Build conversation history with enhanced metadata
        messages = (
            await self.session.execute(
                select(ConversationMessage)
                .where(ConversationMessage.interview_id == interview_id)
                .order_by(ConversationMessage.sequence_number)
            )
        ).scalars().all()
        
        conversation_history = []
        transcript_parts = []
        
        for msg in messages:
            conversation_history.append({
                "role": msg.role.value,
                "text": msg.content or "",
                "sequence": msg.sequence_number,
                "timestamp": (lambda dt: dt.isoformat() if dt else None)(getattr(msg, 'created_at', None))
            })
            
            if msg.content:
                role_prefix = ("Interviewer" if msg.role.value == "assistant" 
                             else "Candidate" if msg.role.value == "user" 
                             else "System")
                transcript_parts.append(f"{role_prefix}: {msg.content.strip()}")
        
        transcript_text = "\n\n".join(transcript_parts)
        
        return InterviewContext(
            interview_id=interview_id,
            job_id=interview.job_id,
            candidate_id=interview.candidate_id,
            job_description=job.description if job and job.description else "",
            job_title=job.title if job and job.title else "",
            resume_text=resume_text,
            candidate_name=candidate_name,
            transcript_text=transcript_text,
            conversation_history=conversation_history
        )
    
    @monitor_process_stage("generate_premium_question_set")
    async def generate_strategic_question_set(
        self, 
        interview_id: int,
        question_count: int = 7,
        focus_competencies: Optional[List[str]] = None
    ) -> PremiumInterviewSession:
        """
        Generate a strategic set of high-quality interview questions
        """
        
        # Load context
        context = await self._load_interview_context(interview_id)
        
        # Generate questions strategically
        questions = []
        
        for i in range(question_count):
            focus_competency = None
            if focus_competencies and i < len(focus_competencies):
                focus_competency = focus_competencies[i]
            
            question = await self.question_engine.generate_strategic_question(
                job_description=context.job_description,
                resume_text=context.resume_text,
                conversation_history=context.conversation_history,
                focus_competency=focus_competency
            )
            
            questions.append(question)
            
            # Simulate adding this question to conversation for next question context
            context.conversation_history.append({
                "role": "assistant",
                "text": question.question,
                "sequence": len(context.conversation_history)
            })
        
        # Generate analytics
        question_analytics = self.question_engine.get_question_analytics(questions)
        
        return PremiumInterviewSession(
            interview_id=interview_id,
            context=context,
            generated_questions=questions,
            question_analytics=question_analytics,
            focus_competencies=focus_competencies or []
        )
    
    @monitor_process_stage("get_next_premium_question")
    async def get_next_strategic_question(
        self, 
        interview_id: int,
        session_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get next strategic question with enhanced context and guidance
        """
        
        # Load current context
        context = await self._load_interview_context(interview_id)
        
        # Check if we need to generate a new question or use pre-generated set
        if session_data and "current_question_index" in session_data:
            # Continue with existing session
            current_index = session_data["current_question_index"]
            questions = session_data.get("generated_questions", [])
            
            if current_index < len(questions):
                question_data = questions[current_index]
                return {
                    "question": question_data["question"],
                    "context": question_data.get("context", ""),
                    "metadata": question_data.get("metadata", {}),
                    "interviewer_guidance": {
                        "evaluation_rubric": question_data.get("evaluation_rubric", {}),
                        "follow_up_questions": question_data.get("follow_up_questions", []),
                        "red_flags": question_data.get("red_flags", []),
                        "ideal_indicators": question_data.get("ideal_response_indicators", [])
                    },
                    "session_update": {
                        "current_question_index": current_index + 1,
                        "questions_remaining": len(questions) - current_index - 1
                    },
                    "done": False
                }
        
        # Generate fresh strategic question
        question = await self.question_engine.generate_strategic_question(
            job_description=context.job_description,
            resume_text=context.resume_text,
            conversation_history=context.conversation_history
        )
        
        # Check if interview should end
        question_count = len([msg for msg in context.conversation_history if msg.get("role") == "assistant"])
        max_questions = 7
        
        if question_count >= max_questions:
            return {
                "question": "",
                "done": True,
                "ready_for_analysis": True,
                "total_questions_asked": question_count
            }
        
        return {
            "question": question.question,
            "context": question.context,
            "metadata": {
                "type": question.metadata.question_type.value,
                "difficulty": question.metadata.difficulty.value,
                "industry": question.metadata.industry.value if question.metadata.industry else None,
                "competencies": question.metadata.competencies,
                "estimated_time": question.metadata.time_estimate_minutes
            },
            "interviewer_guidance": {
                "evaluation_rubric": question.evaluation_rubric,
                "follow_up_questions": question.follow_up_questions,
                "red_flags": question.red_flags,
                "ideal_indicators": question.ideal_response_indicators
            },
            "done": False,
            "questions_asked": question_count + 1,
            "questions_remaining": max_questions - question_count - 1
        }
    
    @monitor_process_stage("generate_intelligent_followup")
    async def generate_intelligent_follow_up(
        self,
        interview_id: int,
        original_question: str,
        candidate_answer: str,
        focus_area: str = "depth and specificity"
    ) -> Dict[str, Any]:
        """
        Generate intelligent follow-up question based on candidate response
        """
        
        follow_up = await self.question_engine.generate_follow_up_question(
            original_question=original_question,
            candidate_answer=candidate_answer,
            focus_area=focus_area
        )
        
        return {
            "follow_up_question": follow_up,
            "focus_area": focus_area,
            "guidance": "Bu follow-up ile adayın cevabındaki belirsizlikleri netleştirin ve daha somut detay alın."
        }
    
    @monitor_process_stage("generate_premium_analysis")
    async def generate_premium_analysis_report(
        self,
        interview_id: int,
        industry: str = "tech",
        role_level: str = "mid"
    ) -> Dict[str, Any]:
        """
        Generate comprehensive, realistic interview analysis report
        """
        
        # Load context
        context = await self._load_interview_context(interview_id)
        
        if not context.transcript_text.strip():
            raise ValueError("No transcript available for analysis")
        
        # Generate detailed assessment
        assessment = await self.reporting_engine.generate_comprehensive_report(
            transcript=context.transcript_text,
            job_description=context.job_description,
            resume_text=context.resume_text,
            industry=industry,
            role_level=role_level,
            candidate_name=context.candidate_name
        )
        
        # Generate actionable recommendations
        recommendations = await self.reporting_engine.generate_actionable_recommendations(
            assessment=assessment,
            job_description=context.job_description
        )
        
        # Store analysis in database
        await self._store_premium_analysis(interview_id, assessment, recommendations)
        
        # Format for response
        return {
            "assessment_summary": {
                "overall_score": {
                    "score": assessment.overall_score.score,
                    "confidence_level": assessment.overall_score.confidence_level.value,
                    "confidence_percentage": assessment.overall_score.confidence_percentage,
                    "benchmark_percentile": assessment.overall_score.benchmark_percentile
                },
                "competency_scores": {
                    "technical": {
                        "score": assessment.technical_competency.score,
                        "confidence": assessment.technical_competency.confidence_level.value,
                        "percentile": assessment.technical_competency.benchmark_percentile
                    },
                    "behavioral": {
                        "score": assessment.behavioral_competency.score,
                        "confidence": assessment.behavioral_competency.confidence_level.value,
                        "percentile": assessment.behavioral_competency.benchmark_percentile
                    },
                    "communication": {
                        "score": assessment.communication_effectiveness.score,
                        "confidence": assessment.communication_effectiveness.confidence_level.value,
                        "percentile": assessment.communication_effectiveness.benchmark_percentile
                    },
                    "problem_solving": {
                        "score": assessment.problem_solving_approach.score,
                        "confidence": assessment.problem_solving_approach.confidence_level.value,
                        "percentile": assessment.problem_solving_approach.benchmark_percentile
                    },
                    "cultural_fit": {
                        "score": assessment.cultural_alignment.score,
                        "confidence": assessment.cultural_alignment.confidence_level.value,
                        "percentile": assessment.cultural_alignment.benchmark_percentile
                    },
                    "growth_potential": {
                        "score": assessment.growth_potential.score,
                        "confidence": assessment.growth_potential.confidence_level.value,
                        "percentile": assessment.growth_potential.benchmark_percentile
                    },
                    "leadership": {
                        "score": assessment.leadership_indicators.score,
                        "confidence": assessment.leadership_indicators.confidence_level.value,
                        "percentile": assessment.leadership_indicators.benchmark_percentile
                    }
                }
            },
            "detailed_analysis": {
                "evidence_summary": self._format_evidence_summary(assessment),
                "reasoning": assessment.overall_score.reasoning,
                "improvement_areas": self._extract_improvement_areas(assessment),
                "key_strengths": self._extract_key_strengths(assessment)
            },
            "risk_assessment": {
                "red_flags": assessment.potential_red_flags,
                "bias_indicators": [bias.value for bias in assessment.bias_indicators],
                "confidence_concerns": self._identify_confidence_concerns(assessment)
            },
            "benchmarking": {
                "industry_comparison": assessment.industry_comparison,
                "role_level_comparison": assessment.role_level_comparison,
                "industry": industry,
                "role_level": role_level
            },
            "recommendations": [
                {
                    "category": rec.category,
                    "priority": rec.priority,
                    "recommendation": rec.recommendation,
                    "reasoning": rec.reasoning,
                    "timeline": rec.timeline,
                    "success_metrics": rec.success_metrics,
                    "resources_needed": rec.resources_needed
                }
                for rec in recommendations
            ],
            "metadata": {
                "analysis_type": "premium",
                "candidate_name": context.candidate_name,
                "interview_id": interview_id,
                "transcript_length": len(context.transcript_text),
                "questions_analyzed": len(context.conversation_history) // 2,
                "industry": industry,
                "role_level": role_level
            }
        }
    
    def _format_evidence_summary(self, assessment: DetailedAssessment) -> Dict[str, Any]:
        """Format evidence summary for report"""
        all_evidence = []
        competencies = {
            "technical": assessment.technical_competency,
            "behavioral": assessment.behavioral_competency,
            "communication": assessment.communication_effectiveness,
            "problem_solving": assessment.problem_solving_approach
        }
        
        for comp_name, comp_assessment in competencies.items():
            for evidence in comp_assessment.evidence_items:
                all_evidence.append({
                    "competency": comp_name,
                    "strength": evidence.strength.value,
                    "positive": evidence.positive,
                    "excerpt": evidence.source_text[:100] + "..." if len(evidence.source_text) > 100 else evidence.source_text
                })
        
        return {
            "total_evidence_items": len(all_evidence),
            "strong_evidence_count": len([e for e in all_evidence if e["strength"] == "strong"]),
            "positive_evidence_ratio": len([e for e in all_evidence if e["positive"]]) / max(len(all_evidence), 1),
            "evidence_by_competency": {
                comp: len([e for e in all_evidence if e["competency"] == comp])
                for comp in ["technical", "behavioral", "communication", "problem_solving"]
            }
        }
    
    def _extract_improvement_areas(self, assessment: DetailedAssessment) -> List[Dict[str, Any]]:
        """Extract improvement areas from assessment"""
        improvement_areas = []
        
        competencies = {
            "Teknik Yetkinlik": assessment.technical_competency,
            "Davranışsal Yetkinlik": assessment.behavioral_competency,
            "İletişim": assessment.communication_effectiveness,
            "Problem Çözme": assessment.problem_solving_approach,
            "Kültürel Uyum": assessment.cultural_alignment,
            "Büyüme Potansiyeli": assessment.growth_potential,
            "Liderlik": assessment.leadership_indicators
        }
        
        for comp_name, comp_score in competencies.items():
            if comp_score.score < 70:
                improvement_areas.append({
                    "competency": comp_name,
                    "current_score": comp_score.score,
                    "improvement_potential": comp_score.improvement_potential,
                    "priority": "high" if comp_score.score < 50 else "medium",
                    "confidence": comp_score.confidence_level.value
                })
        
        return improvement_areas
    
    def _extract_key_strengths(self, assessment: DetailedAssessment) -> List[Dict[str, Any]]:
        """Extract key strengths from assessment"""
        strengths = []
        
        competencies = {
            "Teknik Yetkinlik": assessment.technical_competency,
            "Davranışsal Yetkinlik": assessment.behavioral_competency,
            "İletişim": assessment.communication_effectiveness,
            "Problem Çözme": assessment.problem_solving_approach,
            "Kültürel Uyum": assessment.cultural_alignment,
            "Büyüme Potansiyeli": assessment.growth_potential,
            "Liderlik": assessment.leadership_indicators
        }
        
        for comp_name, comp_score in competencies.items():
            if comp_score.score >= 80 and comp_score.confidence_level.value in ["high", "very_high"]:
                strengths.append({
                    "competency": comp_name,
                    "score": comp_score.score,
                    "confidence": comp_score.confidence_level.value,
                    "percentile": comp_score.benchmark_percentile,
                    "evidence_quality": len([e for e in comp_score.evidence_items if e.strength.value == "strong"])
                })
        
        return strengths
    
    def _identify_confidence_concerns(self, assessment: DetailedAssessment) -> List[str]:
        """Identify areas with low confidence that need attention"""
        concerns = []
        
        competencies = {
            "Teknik Yetkinlik": assessment.technical_competency,
            "Davranışsal Yetkinlik": assessment.behavioral_competency,
            "İletişim": assessment.communication_effectiveness,
            "Problem Çözme": assessment.problem_solving_approach
        }
        
        for comp_name, comp_score in competencies.items():
            if comp_score.confidence_level.value in ["low", "very_low"]:
                concerns.append(f"{comp_name}: Yetersiz kanıt - ek değerlendirme gerekebilir")
        
        return concerns
    
    async def _store_premium_analysis(
        self, 
        interview_id: int, 
        assessment: DetailedAssessment, 
        recommendations: List[ActionableRecommendation]
    ) -> None:
        """Store premium analysis results in database"""
        
        import json
        
        analysis_data = {
            "type": "premium_analysis",
            "overall_score": assessment.overall_score.score,
            "confidence_level": assessment.overall_score.confidence_level.value,
            "competency_scores": {
                "technical": assessment.technical_competency.score,
                "behavioral": assessment.behavioral_competency.score,
                "communication": assessment.communication_effectiveness.score,
                "problem_solving": assessment.problem_solving_approach.score,
                "cultural_alignment": assessment.cultural_alignment.score,
                "growth_potential": assessment.growth_potential.score,
                "leadership": assessment.leadership_indicators.score
            },
            "evidence_summary": {
                "total_items": sum(len(getattr(assessment, f"{comp}_competency").evidence_items) 
                                 for comp in ["technical", "behavioral"]) + 
                              sum(len(getattr(assessment, f"{comp}").evidence_items) 
                                  for comp in ["communication_effectiveness", "problem_solving_approach"])
            },
            "red_flags": assessment.potential_red_flags,
            "bias_indicators": [bias.value for bias in assessment.bias_indicators],
            "recommendations": [
                {
                    "category": rec.category,
                    "priority": rec.priority,
                    "recommendation": rec.recommendation,
                    "timeline": rec.timeline
                }
                for rec in recommendations
            ]
        }
        
        # Update existing analysis or create new
        existing = (
            await self.session.execute(
                select(InterviewAnalysis).where(InterviewAnalysis.interview_id == interview_id)
            )
        ).scalar_one_or_none()
        
        if existing:
            existing.overall_score = assessment.overall_score.score
            existing.technical_assessment = json.dumps(analysis_data, ensure_ascii=False)
            existing.model_used = "premium-v1"
            existing.summary = f"Premium analiz - Genel skor: {assessment.overall_score.score:.1f}, " \
                              f"Güven seviyesi: {assessment.overall_score.confidence_level.value}"
        else:
            analysis = InterviewAnalysis(
                interview_id=interview_id,
                overall_score=assessment.overall_score.score,
                technical_assessment=json.dumps(analysis_data, ensure_ascii=False),
                model_used="premium-v1",
                summary=f"Premium analiz - Genel skor: {assessment.overall_score.score:.1f}"
            )
            self.session.add(analysis)
        
        await self.session.commit()


# Factory function
async def create_premium_interview_service(session: AsyncSession) -> PremiumInterviewService:
    """Create PremiumInterviewService instance"""
    return PremiumInterviewService(session)
