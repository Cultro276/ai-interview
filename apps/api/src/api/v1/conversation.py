from typing import List

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel

from src.core.gemini import generate_question
from src.core.metrics import collector

router = APIRouter(prefix="/interview", tags=["interview"])


class Turn(BaseModel):
    role: str  # 'user' or 'assistant'
    text: str


class NextQuestionRequest(BaseModel):
    history: List[Turn]


class NextQuestionResponse(BaseModel):
    question: str | None = None
    done: bool


@router.post("/next-question", response_model=NextQuestionResponse)
async def next_question(req: NextQuestionRequest):
    # Call Gemini to get next question
    try:
        result = await generate_question([t.dict() for t in req.history])
    except Exception as e:
        collector.record_error()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    return NextQuestionResponse(question=result.get("question"), done=result.get("done", False)) 