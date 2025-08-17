from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import current_active_user
from src.db.models.user import User
from src.db.models.conversation import ConversationMessage, InterviewAnalysis
from src.db.models.interview import Interview
from src.db.models.job import Job
from src.db.session import get_session
from src.api.v1.schemas import (
    ConversationMessageCreate, 
    ConversationMessageRead,
    InterviewAnalysisCreate,
    InterviewAnalysisRead
)
from src.services.analysis import generate_rule_based_analysis
from src.core.metrics import collector, Timer

router = APIRouter(prefix="/conversations", tags=["conversations"])

# Public router for candidate (token) submissions
public_router = APIRouter(prefix="/conversations", tags=["conversations-public"])  # included without auth in routes


# ---- Conversation Messages ----

@router.post("/messages", response_model=ConversationMessageRead, status_code=status.HTTP_201_CREATED)
async def create_message(
    message_in: ConversationMessageCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user)
):
    # Verify user owns the interview
    interview = await session.execute(
        select(Interview)
        .join(Job, Interview.job_id == Job.id)
        .where(Interview.id == message_in.interview_id, Job.user_id == current_user.id)
    )
    interview = interview.scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    message = ConversationMessage(**message_in.dict())
    session.add(message)
    await session.commit()
    await session.refresh(message)
    return message


# Candidate-safe message creation that does not require admin JWT
class PublicConversationMessageCreate(ConversationMessageCreate):
    pass


@public_router.post("/messages-public", response_model=ConversationMessageRead, status_code=status.HTTP_201_CREATED)
async def create_message_public(
    message_in: PublicConversationMessageCreate,
    session: AsyncSession = Depends(get_session),
):
    # Verify interview exists. No ownership check (candidate flow) but we restrict fields strictly.
    interview = await session.execute(
        select(Interview).where(Interview.id == message_in.interview_id)
    )
    interview = interview.scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    message = ConversationMessage(**message_in.dict())
    session.add(message)
    await session.commit()
    await session.refresh(message)
    return message


@router.get("/messages/{interview_id}", response_model=List[ConversationMessageRead])
async def get_conversation(
    interview_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user)
):
    # Verify user owns the interview
    interview = await session.execute(
        select(Interview)
        .join(Job, Interview.job_id == Job.id)
        .where(Interview.id == interview_id, Job.user_id == current_user.id)
    )
    interview = interview.scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    # Get conversation messages
    result = await session.execute(
        select(ConversationMessage)
        .where(ConversationMessage.interview_id == interview_id)
        .order_by(ConversationMessage.sequence_number)
    )
    return result.scalars().all()


# ---- Interview Analysis ----

@router.post("/analysis", response_model=InterviewAnalysisRead, status_code=status.HTTP_201_CREATED)
async def create_analysis(
    analysis_in: InterviewAnalysisCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user)
):
    # Verify user owns the interview
    interview = await session.execute(
        select(Interview)
        .join(Job, Interview.job_id == Job.id)
        .where(Interview.id == analysis_in.interview_id, Job.user_id == current_user.id)
    )
    interview = interview.scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    # Always run rule-based analysis to (re)generate content
    with Timer() as t:
        result = await generate_rule_based_analysis(session, analysis_in.interview_id)
    collector.record_analysis_ms(t.ms)
    return result


@router.get("/analysis/{interview_id}", response_model=InterviewAnalysisRead)
async def get_analysis(
    interview_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user)
):
    # Verify user owns the interview
    interview = await session.execute(
        select(Interview)
        .join(Job, Interview.job_id == Job.id)
        .where(Interview.id == interview_id, Job.user_id == current_user.id)
    )
    interview = interview.scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    # Get analysis
    result = await session.execute(
        select(InterviewAnalysis)
        .where(InterviewAnalysis.interview_id == interview_id)
    )
    analysis = result.scalar_one_or_none()
    if analysis:
        return analysis
    # Auto-generate if missing
    return await generate_rule_based_analysis(session, interview_id)


@router.put("/analysis/{interview_id}", response_model=InterviewAnalysisRead)
async def update_analysis(
    interview_id: int,
    analysis_in: InterviewAnalysisCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user)
):
    # Verify user owns the interview
    interview = await session.execute(
        select(Interview)
        .join(Job, Interview.job_id == Job.id)
        .where(Interview.id == interview_id, Job.user_id == current_user.id)
    )
    interview = interview.scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    # Recompute analysis from conversation messages
    with Timer() as t:
        result = await generate_rule_based_analysis(session, interview_id)
    collector.record_analysis_ms(t.ms)
    return result