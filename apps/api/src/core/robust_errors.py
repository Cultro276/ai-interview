"""
Robust Error Handling - Replaces empty dict returns with structured errors
"""

from __future__ import annotations
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
from functools import wraps


class ErrorType(str, Enum):
    LLM_ERROR = "llm_error"
    PARSE_ERROR = "parse_error" 
    DATA_ERROR = "data_error"
    NETWORK_ERROR = "network_error"


@dataclass
class SafeResult:
    """Result wrapper with error handling"""
    data: Any = None
    error_message: Optional[str] = None
    error_type: Optional[ErrorType] = None
    success: bool = True
    
    @classmethod
    def ok(cls, data: Any) -> 'SafeResult':
        return cls(data=data)
    
    @classmethod
    def error(cls, message: str, error_type: ErrorType = ErrorType.DATA_ERROR) -> 'SafeResult':
        return cls(error_message=message, error_type=error_type, success=False)
    
    def get_data_or_empty(self) -> Dict[str, Any]:
        """Get data or safe empty dict"""
        if self.success and isinstance(self.data, dict):
            return self.data
        elif self.success:
            return {"result": self.data}
        else:
            error_type_value = self.error_type.value if self.error_type else "unknown_error"
            return {"error": self.error_message, "error_type": error_type_value}


def safe_async(default_return=None):
    """Decorator for safe async execution"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                logging.error(f"Error in {func.__name__}: {e}")
                return default_return or {}
        return wrapper
    return decorator


# Apply to key functions that currently return empty dicts
@safe_async(default_return={})
async def safe_assess_hr_criteria(transcript_text: str) -> Dict[str, Any]:
    """Safe HR criteria assessment"""
    from src.services.comprehensive_analyzer import assess_hr_criteria
    
    if not transcript_text.strip():
        return {"error": "Empty transcript", "criteria": []}
    
    return await assess_hr_criteria(transcript_text)


@safe_async(default_return={})
async def safe_assess_job_fit(job_desc: str, transcript: str, resume: str = "") -> Dict[str, Any]:
    """Safe job fit assessment"""
    from src.services.comprehensive_analyzer import assess_job_fit
    
    if not job_desc.strip() or not transcript.strip():
        return {"error": "Missing required data", "overall_fit_score": 0.0}
    
    return await assess_job_fit(job_desc, transcript, resume)


@safe_async(default_return={})
async def safe_opinion_on_candidate(job_desc: str, transcript: str, resume: str = "") -> Dict[str, Any]:
    """Safe hiring opinion generation"""
    from src.services.comprehensive_analyzer import opinion_on_candidate
    
    if not job_desc.strip() or not transcript.strip():
        return {
            "error": "Missing required data",
            "hire_recommendation": "Hold",
            "decision_confidence": 0.0
        }
    
    return await opinion_on_candidate(job_desc, transcript, resume)


# Enhanced versions with better error messages
def get_safe_nlp_functions():
    """Get safe versions of nlp functions"""
    return {
        "assess_hr_criteria": safe_assess_hr_criteria,
        "assess_job_fit": safe_assess_job_fit,
        "opinion_on_candidate": safe_opinion_on_candidate
    }
