from typing import List

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.db.session import get_session
from src.db.models.interview import Interview
from src.db.models.job import Job

from src.core.gemini import generate_question
from src.core.metrics import collector

router = APIRouter(prefix="/interview", tags=["interview"])


class Turn(BaseModel):
    role: str  # 'user' or 'assistant'
    text: str


class NextQuestionRequest(BaseModel):
    history: List[Turn]
    interview_id: int


class NextQuestionResponse(BaseModel):
    question: str | None = None
    done: bool


@router.post("/next-question", response_model=NextQuestionResponse)
async def next_question(req: NextQuestionRequest, session: AsyncSession = Depends(get_session)):
    # Call Gemini to get next question
    try:
        # Pull job description via interview id
        job_desc = ""
        interview = (
            await session.execute(select(Interview).where(Interview.id == req.interview_id))
        ).scalar_one_or_none()
        if interview:
            job = (
                await session.execute(select(Job).where(Job.id == interview.job_id))
            ).scalar_one_or_none()
            if job and job.description:
                job_desc = job.description

        result = await generate_question([t.dict() for t in req.history], job_desc)
    except Exception as e:
        collector.record_error()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    return NextQuestionResponse(question=result.get("question"), done=result.get("done", False)) 