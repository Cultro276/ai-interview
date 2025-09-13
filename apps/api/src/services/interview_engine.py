"""
InterviewEngine - Unified entry point for all interview operations
Centralizes CV processing, job analysis, question generation, and interview analysis
"""

from __future__ import annotations
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from sqlalchemy.ext.asyncio import AsyncSession
import inspect
from sqlalchemy import select

from src.db.models.interview import Interview
from src.db.models.job import Job
from src.db.models.candidate import Candidate
from src.db.models.candidate_profile import CandidateProfile
from src.db.models.conversation import ConversationMessage, InterviewAnalysis


@dataclass
class InterviewContext:
    """Unified context for interview operations"""
    interview_id: int
    job_id: int
    candidate_id: int
    job_description: str = ""
    job_title: str = ""
    resume_text: str = ""
    candidate_name: str = ""
    transcript_text: str = ""
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)


class InterviewEngine:
    """
    Central engine for all interview-related operations.
    Replaces scattered functions across nlp.py, analysis.py, and dialog.py
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def _exec(self, stmt):
        """Execute a SQLAlchemy select on either async or sync session mocks.

        In tests, session may be a simple Mock returning an object without await.
        In production, it's an AsyncSession requiring await.
        """
        result = self.session.execute(stmt)
        if inspect.isawaitable(result):
            result = await result
        return result

    async def load_context(self, interview_id: int) -> InterviewContext:
        """Load all interview context data from database"""
        
        # Get interview
        interview = (await self._exec(select(Interview).where(Interview.id == interview_id))).scalar_one_or_none()
        
        if not interview:
            raise ValueError(f"Interview {interview_id} not found")
        
        # Get job
        job = (await self._exec(select(Job).where(Job.id == interview.job_id))).scalar_one_or_none()
        
        # Get candidate and profile
        candidate = (await self._exec(select(Candidate).where(Candidate.id == interview.candidate_id))).scalar_one_or_none()
        
        resume_text = ""
        candidate_name = ""
        if candidate:
            candidate_name = candidate.name or "Unknown"
            profile = (await self._exec(select(CandidateProfile).where(CandidateProfile.candidate_id == candidate.id))).scalar_one_or_none()
            if profile and profile.resume_text:
                resume_text = profile.resume_text
        
        # Get transcript
        transcript_text = interview.transcript_text or ""
        if not transcript_text:
            # Build from conversation messages
            messages = (await self._exec(select(ConversationMessage).where(ConversationMessage.interview_id == interview_id).order_by(ConversationMessage.sequence_number))).scalars().all()
            
            if messages:
                def _prefix(m):
                    return ("Interviewer" if m.role.value == "assistant" 
                           else "Candidate" if m.role.value == "user" 
                           else "System")
                
                transcript_text = "\n\n".join([
                    f"{_prefix(m)}: {m.content.strip()}" 
                    for m in messages 
                    if (m.content or "").strip()
                ])
        
        # Build conversation history
        conversation_history = []
        messages = (await self._exec(select(ConversationMessage).where(ConversationMessage.interview_id == interview_id).order_by(ConversationMessage.sequence_number))).scalars().all()
        
        for msg in messages:
            conversation_history.append({
                "role": msg.role.value,
                "text": msg.content or "",
                "sequence": msg.sequence_number
            })
        
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
    
    async def precompute_interview_plan(self, interview_id: int) -> Dict[str, Any]:
        """
        Precompute dialog plan and prepare first question.
        Replaces precompute_dialog_plan from analysis.py
        """
        context = await self.load_context(interview_id)
        
        # Import here to avoid circular dependencies
        from src.services.nlp import extract_requirements_spec
        from src.core.gemini import generate_question_robust
        
        # Extract job requirements
        req_spec = await extract_requirements_spec(context.job_description)
        
        # Prepare dialog plan
        plan = {
            "job_requirements": req_spec,
            "candidate_background": {
                "has_resume": bool(context.resume_text.strip()),
                "resume_length": len(context.resume_text),
                "name": context.candidate_name
            },
            "strategy": "comprehensive_assessment",
            "estimated_questions": 5-7,
            "focus_areas": []
        }
        
        # Extract focus areas from requirements
        if req_spec.get("items"):
            plan["focus_areas"] = [
                item.get("label", "") 
                for item in req_spec["items"][:3]
                if isinstance(item, dict)
            ]
        
        # Generate and store first question
        try:
            ctx = f"Job Description:\n{context.job_description}"
            if context.resume_text:
                # Add resume keywords for context without exposing them
                from src.services.dialog import extract_keywords
                kws = extract_keywords(context.resume_text)
                if kws:
                    ctx += f"\n\nInternal Resume Keywords: {', '.join(kws[:30])}"
            
            res = await generate_question_robust([], ctx, max_questions=7)
            question_raw = res.get("question", "")
            question = str(question_raw).strip() if question_raw else ""
            
            # Sanitize question
            bad_keywords = ["cv", "özgeçmiş", "ilan", "iş tanımı", "linkedin", "http://", "https://"]
            if any(bad in question.lower() for bad in bad_keywords) or not question:
                question = "Kendinizi ve son iş deneyiminizi kısaca anlatır mısınız?"
            
            # Store prepared question
            interview = (await self._exec(select(Interview).where(Interview.id == interview_id))).scalar_one_or_none()
            
            if interview:
                interview.prepared_first_question = question
                # In tests, commit may be AsyncMock
                commit_res = self.session.commit()
                if inspect.isawaitable(commit_res):
                    await commit_res
            
            plan["prepared_first_question"] = question
            
        except Exception as e:
            plan["prepared_first_question"] = "Kendinizi ve son iş deneyiminizi kısaca anlatır mısınız?"
            plan["question_generation_error"] = str(e)
        
        # Store plan in analysis
        await self._store_enrichment(interview_id, {"dialog_plan": plan, "requirements_spec": req_spec})
        
        return plan
    
    async def generate_next_question(self, interview_id: int, max_questions: int = 7) -> Dict[str, Any]:
        """
        Generate next interview question based on current context.
        Replaces scattered question generation logic.
        """
        context = await self.load_context(interview_id)
        
        from src.core.gemini import generate_question_robust
        
        # Build job context for question generation
        job_context = f"Job Description:\n{context.job_description}"
        if context.resume_text:
            job_context += f"\n\nCandidate Background Available: Yes"
        
        # Generate question
        result = await generate_question_robust(
            context.conversation_history, 
            job_context, 
            max_questions
        )
        
        return result
    
    async def process_complete_interview(self, interview_id: int) -> InterviewAnalysis:
        """
        Process completed interview with comprehensive analysis.
        Replaces process_interview from queue.py and analysis functions.
        """
        context = await self.load_context(interview_id)
        
        # Prefer comprehensive analyzer if available (tests patch this)
        try:
            from src.services.comprehensive_analyzer import comprehensive_interview_analysis  # type: ignore
            # This function is async; tests patch it and expect it to be awaited
            analysis_data = await comprehensive_interview_analysis(
                job_desc=context.job_description,
                transcript_text=context.transcript_text,
                resume_text=context.resume_text,
                candidate_name=context.candidate_name,
                job_title=context.job_title,
            )
        except Exception:
            # Fallback to legacy per-component analysis
            from src.services.nlp import assess_hr_criteria, assess_job_fit, opinion_on_candidate
            if not context.transcript_text.strip():
                raise ValueError("No transcript available for analysis")
            transcript = context.transcript_text[:50000]
            hr_criteria = await assess_hr_criteria(transcript)
            job_fit = await assess_job_fit(context.job_description, transcript, context.resume_text)
            hiring_opinion = await opinion_on_candidate(context.job_description, transcript, context.resume_text)
            overall_score = None
            try:
                criteria = hr_criteria.get("criteria", []) if isinstance(hr_criteria, dict) else []
                if criteria:
                    scores = [float(c.get("score_0_100", 0.0)) for c in criteria if isinstance(c, dict)]
                    if scores:
                        overall_score = round(sum(scores) / len(scores), 2)
            except Exception:
                overall_score = None
            analysis_data = {
                "hr_criteria": hr_criteria,
                "job_fit": job_fit,
                "ai_opinion": hiring_opinion,
                "overall_score": overall_score,
                "context_summary": {
                    "interview_id": interview_id,
                    "candidate_name": context.candidate_name,
                    "job_title": context.job_title,
                    "transcript_length": len(transcript),
                    "resume_available": bool(context.resume_text.strip())
                }
            }
        
        return await self._store_analysis(interview_id, analysis_data)
    
    async def _store_enrichment(self, interview_id: int, enrichment: Dict[str, Any]) -> None:
        """Store enrichment data in interview analysis"""
        existing = (await self._exec(select(InterviewAnalysis).where(InterviewAnalysis.interview_id == interview_id))).scalar_one_or_none()
        
        if existing:
            # Update existing
            if existing.technical_assessment:
                import json
                current = json.loads(existing.technical_assessment)
                current.update(enrichment)
                existing.technical_assessment = json.dumps(current)
            else:
                import json
                existing.technical_assessment = json.dumps(enrichment)
        else:
            # Create new
            import json
            analysis = InterviewAnalysis(
                interview_id=interview_id,
                technical_assessment=json.dumps(enrichment),
                overall_score=None,
                summary=""
            )
            self.session.add(analysis)
        
        commit_res = self.session.commit()
        if inspect.isawaitable(commit_res):
            await commit_res
    
    async def _store_analysis(self, interview_id: int, analysis_data: Dict[str, Any]) -> InterviewAnalysis:
        """Store complete interview analysis"""
        existing = (await self._exec(select(InterviewAnalysis).where(InterviewAnalysis.interview_id == interview_id))).scalar_one_or_none()
        
        import json
        
        if existing:
            # Update existing
            existing.technical_assessment = json.dumps(analysis_data)
            existing.overall_score = analysis_data.get("overall_score")
            existing.summary = analysis_data.get("ai_opinion", {}).get("overall_assessment", "")
        else:
            # Create new
            analysis = InterviewAnalysis(
                interview_id=interview_id,
                technical_assessment=json.dumps(analysis_data),
                overall_score=analysis_data.get("overall_score"),
                summary=analysis_data.get("ai_opinion", {}).get("overall_assessment", "")
            )
            self.session.add(analysis)
            existing = analysis
        
        commit_res = self.session.commit()
        if inspect.isawaitable(commit_res):
            await commit_res
        refresh_res = self.session.refresh(existing)
        if inspect.isawaitable(refresh_res):
            await refresh_res
        
        return existing


# Factory function for easy usage
async def create_interview_engine(session: AsyncSession) -> InterviewEngine:
    """Create InterviewEngine instance"""
    return InterviewEngine(session)
