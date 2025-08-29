from datetime import datetime
from typing import Optional, List
from enum import Enum

from pydantic import BaseModel, Field, EmailStr


# ---- Conversation ----

class MessageRole(str, Enum):
    ASSISTANT = "assistant"
    USER = "user"
    SYSTEM = "system"


class ConversationMessageCreate(BaseModel):
    interview_id: int
    role: MessageRole
    content: str
    sequence_number: int


class ConversationMessageRead(BaseModel):
    id: int
    interview_id: int
    role: MessageRole
    content: str
    timestamp: datetime
    sequence_number: int

    model_config = {"from_attributes": True}


# ---- Interview Analysis ----

class InterviewAnalysisCreate(BaseModel):
    interview_id: int
    overall_score: Optional[float] = None
    summary: Optional[str] = None
    strengths: Optional[str] = None
    weaknesses: Optional[str] = None
    technical_assessment: Optional[str] = None
    communication_score: Optional[float] = None
    technical_score: Optional[float] = None
    cultural_fit_score: Optional[float] = None
    analysis_prompt: Optional[str] = None
    model_used: Optional[str] = None


class InterviewAnalysisRead(BaseModel):
    id: int
    interview_id: int
    overall_score: Optional[float]
    summary: Optional[str]
    strengths: Optional[str]
    weaknesses: Optional[str]
    technical_assessment: Optional[str]
    communication_score: Optional[float]
    technical_score: Optional[float]
    cultural_fit_score: Optional[float]
    analysis_prompt: Optional[str]
    model_used: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---- Job ----

class JobBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    expires_in_days: Optional[int] = Field(default=None, ge=1, le=365, description="Default invite link expiry for this job")
    # Removed manual requirements/rubric configuration


class JobCreate(JobBase):
    pass


class JobUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    # Removed manual requirements/rubric configuration


class JobRead(JobBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    default_invite_expiry_days: Optional[int] = None

    model_config = {
        "from_attributes": True,
    }


# ---- Candidate ----

class CandidateBase(BaseModel):
    name: str = Field(..., max_length=255)
    email: EmailStr
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    resume_url: Optional[str] = None


class CandidateCreate(CandidateBase):
    expires_in_days: Optional[int] = Field(default=7, ge=1, le=365)  # Default 7 days, min 1 day, max 1 year


class CandidateUpdate(BaseModel):
    name: Optional[str]
    email: Optional[EmailStr]
    phone: Optional[str]
    linkedin_url: Optional[str]
    resume_url: Optional[str]


class CandidateRead(CandidateBase):
    id: int
    user_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ---- Interview ----

class InterviewCreate(BaseModel):
    job_id: int
    candidate_id: int
    status: str = Field("pending", pattern="^(pending|completed)$")


class InterviewRead(BaseModel):
    id: int
    job_id: int
    candidate_id: int
    status: str
    created_at: datetime
    audio_url: Optional[str] = None
    video_url: Optional[str] = None
    completed_at: Optional[datetime] = None
    completed_ip: Optional[str] = None
    prepared_first_question: Optional[str] = None

    model_config = {"from_attributes": True}


class InterviewStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(pending|completed)$")


# --- Media upload ---


class InterviewMediaUpdate(BaseModel):
    audio_url: Optional[str] = None
    video_url: Optional[str] = None 