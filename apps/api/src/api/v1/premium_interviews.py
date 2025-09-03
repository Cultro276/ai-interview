"""
Premium Interview API - High-quality interview experience with advanced questions and reporting
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_session
from src.services.premium_interview_service import create_premium_interview_service
from src.core.monitoring import monitor_process_stage
from src.auth import current_active_user


router = APIRouter(prefix="/premium-interviews", tags=["Premium Interviews"])


# Request/Response Models
class QuestionGenerationRequest(BaseModel):
    interview_id: int
    question_count: int = Field(default=7, ge=3, le=10)
    focus_competencies: Optional[List[str]] = None
    adaptive_difficulty: bool = True


class NextQuestionRequest(BaseModel):
    interview_id: int
    session_data: Optional[Dict[str, Any]] = None


class FollowUpRequest(BaseModel):
    interview_id: int
    original_question: str
    candidate_answer: str
    focus_area: str = "depth and specificity"


class AnalysisRequest(BaseModel):
    interview_id: int
    industry: str = Field(default="tech", description="Industry context for benchmarking")
    role_level: str = Field(default="mid", description="Role level: junior, mid, senior, lead")


class QuestionResponse(BaseModel):
    question: str
    context: str
    metadata: Dict[str, Any]
    interviewer_guidance: Dict[str, Any]
    done: bool
    session_update: Optional[Dict[str, Any]] = None


class AnalysisResponse(BaseModel):
    assessment_summary: Dict[str, Any]
    detailed_analysis: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    benchmarking: Dict[str, Any]
    recommendations: List[Dict[str, Any]]
    metadata: Dict[str, Any]


@router.post("/generate-question-set", response_model=Dict[str, Any])
@monitor_process_stage("api_generate_question_set")
async def generate_strategic_question_set(
    request: QuestionGenerationRequest,
    session: AsyncSession = Depends(get_session),
    current_user = Depends(current_active_user)  # RBAC check
):
    """
    Generate a strategic set of high-quality interview questions
    tailored to the specific job and candidate profile
    """
    try:
        premium_service = await create_premium_interview_service(session)
        
        interview_session = await premium_service.generate_strategic_question_set(
            interview_id=request.interview_id,
            question_count=request.question_count,
            focus_competencies=request.focus_competencies
        )
        
        return {
            "success": True,
            "interview_id": request.interview_id,
            "questions_generated": len(interview_session.generated_questions),
            "question_analytics": interview_session.question_analytics,
            "session_data": {
                "current_question_index": 0,
                "total_questions": len(interview_session.generated_questions),
                "focus_competencies": interview_session.focus_competencies,
                "generated_questions": [
                    {
                        "question": q.question,
                        "context": q.context,
                        "metadata": {
                            "type": q.metadata.question_type.value,
                            "difficulty": q.metadata.difficulty.value,
                            "industry": q.metadata.industry.value if q.metadata.industry else None,
                            "competencies": q.metadata.competencies,
                            "time_estimate": q.metadata.time_estimate_minutes
                        },
                        "evaluation_rubric": q.evaluation_rubric,
                        "follow_up_questions": q.follow_up_questions,
                        "red_flags": q.red_flags,
                        "ideal_response_indicators": q.ideal_response_indicators
                    }
                    for q in interview_session.generated_questions
                ]
            }
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate question set: {str(e)}"
        )


@router.post("/next-question", response_model=QuestionResponse)
@monitor_process_stage("api_next_premium_question") 
async def get_next_strategic_question(
    request: NextQuestionRequest,
    session: AsyncSession = Depends(get_session),
    current_user = Depends(current_active_user)
):
    """
    Get the next strategic interview question with enhanced guidance
    for the interviewer including evaluation rubrics and follow-up suggestions
    """
    try:
        premium_service = await create_premium_interview_service(session)
        
        result = await premium_service.get_next_strategic_question(
            interview_id=request.interview_id,
            session_data=request.session_data
        )
        
        return QuestionResponse(**result)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get next question: {str(e)}"
        )


@router.post("/follow-up-question", response_model=Dict[str, Any])
@monitor_process_stage("api_generate_followup")
async def generate_intelligent_follow_up(
    request: FollowUpRequest,
    session: AsyncSession = Depends(get_session),
    current_user = Depends(current_active_user)
):
    """
    Generate an intelligent follow-up question based on the candidate's response
    to probe deeper into their experience and competencies
    """
    try:
        premium_service = await create_premium_interview_service(session)
        
        result = await premium_service.generate_intelligent_follow_up(
            interview_id=request.interview_id,
            original_question=request.original_question,
            candidate_answer=request.candidate_answer,
            focus_area=request.focus_area
        )
        
        return {
            "success": True,
            "interview_id": request.interview_id,
            **result
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate follow-up question: {str(e)}"
        )


@router.post("/comprehensive-analysis", response_model=AnalysisResponse)
@monitor_process_stage("api_premium_analysis")
async def generate_comprehensive_analysis(
    request: AnalysisRequest,
    session: AsyncSession = Depends(get_session),
    current_user = Depends(current_active_user)
):
    """
    Generate comprehensive, realistic interview analysis with detailed scoring,
    evidence-based assessment, industry benchmarking, and actionable recommendations
    """
    try:
        premium_service = await create_premium_interview_service(session)
        
        analysis = await premium_service.generate_premium_analysis_report(
            interview_id=request.interview_id,
            industry=request.industry,
            role_level=request.role_level
        )
        
        return AnalysisResponse(**analysis)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate analysis: {str(e)}"
        )


@router.get("/interview/{interview_id}/quality-metrics", response_model=Dict[str, Any])
@monitor_process_stage("api_quality_metrics")
async def get_interview_quality_metrics(
    interview_id: int,
    session: AsyncSession = Depends(get_session),
    current_user = Depends(current_active_user)
):
    """
    Get quality metrics for an interview including question distribution,
    response quality indicators, and assessment confidence levels
    """
    try:
        premium_service = await create_premium_interview_service(session)
        
        # Load interview context
        context = await premium_service._load_interview_context(interview_id)
        
        # Calculate quality metrics
        qa_pairs = []
        for i in range(0, len(context.conversation_history) - 1, 2):
            if (i + 1 < len(context.conversation_history) and 
                context.conversation_history[i]["role"] == "assistant" and
                context.conversation_history[i + 1]["role"] == "user"):
                
                qa_pairs.append({
                    "question": context.conversation_history[i]["text"],
                    "answer": context.conversation_history[i + 1]["text"],
                    "question_length": len(context.conversation_history[i]["text"]),
                    "answer_length": len(context.conversation_history[i + 1]["text"])
                })
        
        # Basic quality metrics
        avg_question_length = sum(qa["question_length"] for qa in qa_pairs) / max(len(qa_pairs), 1)
        avg_answer_length = sum(qa["answer_length"] for qa in qa_pairs) / max(len(qa_pairs), 1)
        
        # Response quality indicators
        detailed_responses = len([qa for qa in qa_pairs if qa["answer_length"] > 100])
        short_responses = len([qa for qa in qa_pairs if qa["answer_length"] < 50])
        
        return {
            "interview_id": interview_id,
            "candidate_name": context.candidate_name,
            "metrics": {
                "total_questions": len(qa_pairs),
                "avg_question_length": round(avg_question_length, 1),
                "avg_answer_length": round(avg_answer_length, 1),
                "detailed_response_ratio": detailed_responses / max(len(qa_pairs), 1),
                "short_response_ratio": short_responses / max(len(qa_pairs), 1),
                "transcript_completeness": len(context.transcript_text) > 500,
                "estimated_duration_minutes": len(qa_pairs) * 3  # Approximate
            },
            "quality_indicators": {
                "sufficient_data_for_analysis": len(qa_pairs) >= 4 and avg_answer_length > 75,
                "response_engagement": detailed_responses / max(len(qa_pairs), 1) > 0.5,
                "interview_completion": len(qa_pairs) >= 5,
                "ready_for_premium_analysis": (
                    len(qa_pairs) >= 4 and 
                    avg_answer_length > 75 and 
                    len(context.transcript_text) > 800
                )
            }
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get quality metrics: {str(e)}"
        )


@router.get("/supported-industries", response_model=Dict[str, Any])
async def get_supported_industries():
    """Get list of supported industries for premium interview analysis"""
    return {
        "industries": [
            {
                "code": "tech",
                "name": "Technology & Software",
                "description": "Software development, IT, startups, tech companies"
            },
            {
                "code": "finance",
                "name": "Finance & Banking", 
                "description": "Banking, fintech, investment, financial services"
            },
            {
                "code": "healthcare",
                "name": "Healthcare & Medical",
                "description": "Hospitals, medical devices, pharmaceutical"
            },
            {
                "code": "education",
                "name": "Education & Academia",
                "description": "Schools, universities, educational technology"
            },
            {
                "code": "retail",
                "name": "Retail & E-commerce",
                "description": "Retail stores, e-commerce, consumer goods"
            },
            {
                "code": "consulting",
                "name": "Consulting & Advisory",
                "description": "Management consulting, strategy, advisory services"
            },
            {
                "code": "startup",
                "name": "Startup & Scale-up",
                "description": "Early-stage companies, high-growth environments"
            }
        ],
        "role_levels": [
            {
                "code": "junior",
                "name": "Junior Level",
                "description": "0-2 years experience, entry level positions"
            },
            {
                "code": "mid",
                "name": "Mid Level",
                "description": "2-5 years experience, individual contributor"
            },
            {
                "code": "senior",
                "name": "Senior Level", 
                "description": "5+ years experience, senior individual contributor"
            },
            {
                "code": "lead",
                "name": "Lead/Principal",
                "description": "Leadership roles, team leads, principals"
            }
        ]
    }


# Health check endpoint
@router.get("/health", response_model=Dict[str, str])
async def premium_service_health():
    """Health check for premium interview service"""
    return {
        "status": "healthy",
        "service": "premium-interview-service",
        "version": "v1.0.0"
    }
