"""
Interview System Monitoring
Tracks LLM usage, performance, and system health
"""

import time
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from src.core.config import settings


@dataclass
class LLMCallMetrics:
    """Metrics for LLM API calls"""
    provider: str
    model: str
    start_time: float
    end_time: float
    tokens_used: int = 0
    cost_estimate: float = 0.0
    success: bool = True
    error_type: Optional[str] = None
    cache_hit: bool = False
    
    @property
    def duration_ms(self) -> int:
        return int((self.end_time - self.start_time) * 1000)


@dataclass
class InterviewProcessMetrics:
    """Metrics for interview processing pipeline"""
    interview_id: int
    stage: str
    start_time: float
    end_time: float
    success: bool = True
    error_details: Optional[Dict[str, Any]] = None
    
    @property
    def duration_ms(self) -> int:
        return int((self.end_time - self.start_time) * 1000)


class SystemMonitor:
    """Central monitoring system"""
    
    def __init__(self):
        self.llm_calls: list[LLMCallMetrics] = []
        self.process_metrics: list[InterviewProcessMetrics] = []
        self.logger = logging.getLogger(__name__)
    
    def record_llm_call(self, metrics: LLMCallMetrics) -> None:
        """Record LLM call metrics"""
        self.llm_calls.append(metrics)
        
        # Log based on performance
        if metrics.duration_ms > 10000:  # >10s
            self.logger.warning(f"Slow LLM call: {metrics.provider} took {metrics.duration_ms}ms")
        
        if not metrics.success:
            self.logger.error(f"LLM call failed: {metrics.provider} - {metrics.error_type}")
    
    def record_process_stage(self, metrics: InterviewProcessMetrics) -> None:
        """Record interview process stage metrics"""
        self.process_metrics.append(metrics)
        
        if metrics.duration_ms > 30000:  # >30s
            self.logger.warning(f"Slow process stage: {metrics.stage} took {metrics.duration_ms}ms")
    
    def get_llm_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get LLM usage statistics"""
        cutoff = time.time() - (hours * 3600)
        recent_calls = [call for call in self.llm_calls if call.start_time >= cutoff]
        
        if not recent_calls:
            return {"total_calls": 0}
        
        total_cost = sum(call.cost_estimate for call in recent_calls)
        avg_duration = sum(call.duration_ms for call in recent_calls) / len(recent_calls)
        success_rate = sum(1 for call in recent_calls if call.success) / len(recent_calls)
        cache_hit_rate = sum(1 for call in recent_calls if call.cache_hit) / len(recent_calls)
        
        provider_stats = {}
        for call in recent_calls:
            if call.provider not in provider_stats:
                provider_stats[call.provider] = {"calls": 0, "cost": 0.0, "avg_duration": 0}
            
            provider_stats[call.provider]["calls"] += 1
            provider_stats[call.provider]["cost"] += call.cost_estimate
        
        return {
            "total_calls": len(recent_calls),
            "total_cost": round(total_cost, 4),
            "avg_duration_ms": int(avg_duration),
            "success_rate": round(success_rate, 3),
            "cache_hit_rate": round(cache_hit_rate, 3),
            "provider_breakdown": provider_stats,
            "period_hours": hours
        }
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status"""
        llm_stats = self.get_llm_stats(1)  # Last hour
        
        # Health score calculation
        health_score = 100
        issues = []
        
        # LLM health checks
        if llm_stats["total_calls"] > 0:
            if llm_stats["success_rate"] < 0.95:
                health_score -= 20
                issues.append("Low LLM success rate")
            
            if llm_stats["avg_duration_ms"] > 8000:
                health_score -= 15
                issues.append("High LLM response times")
            
            if llm_stats["cache_hit_rate"] < 0.1:
                health_score -= 10
                issues.append("Low cache efficiency")
        
        status = "healthy" if health_score >= 80 else "degraded" if health_score >= 60 else "unhealthy"
        
        return {
            "status": status,
            "health_score": max(0, health_score),
            "issues": issues,
            "llm_metrics": llm_stats,
            "timestamp": datetime.now().isoformat()
        }


# Global monitor instance
_system_monitor: Optional[SystemMonitor] = None


def get_monitor() -> SystemMonitor:
    """Get or create global system monitor"""
    global _system_monitor
    if _system_monitor is None:
        _system_monitor = SystemMonitor()
    return _system_monitor


# Monitoring decorators
def monitor_llm_call(provider: str, model: str = "unknown"):
    """Decorator to monitor LLM calls"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            monitor = get_monitor()
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                
                metrics = LLMCallMetrics(
                    provider=provider,
                    model=model,
                    start_time=start_time,
                    end_time=time.time(),
                    success=True
                )
                
                # Extract metrics from result if available
                if hasattr(result, 'tokens_used'):
                    metrics.tokens_used = result.tokens_used or 0
                if hasattr(result, 'cost_estimate'):
                    metrics.cost_estimate = result.cost_estimate or 0.0
                if hasattr(result, 'cached'):
                    metrics.cache_hit = result.cached or False
                
                monitor.record_llm_call(metrics)
                return result
                
            except Exception as e:
                metrics = LLMCallMetrics(
                    provider=provider,
                    model=model,
                    start_time=start_time,
                    end_time=time.time(),
                    success=False,
                    error_type=type(e).__name__
                )
                monitor.record_llm_call(metrics)
                raise
        
        return wrapper
    return decorator


def monitor_process_stage(stage_name: str):
    """Decorator to monitor process stages"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            monitor = get_monitor()
            start_time = time.time()
            
            # Try to extract interview_id from args/kwargs
            interview_id = 0
            if args and isinstance(args[0], int):
                interview_id = args[0]
            elif 'interview_id' in kwargs:
                interview_id = kwargs['interview_id']
            
            try:
                result = await func(*args, **kwargs)
                
                metrics = InterviewProcessMetrics(
                    interview_id=interview_id,
                    stage=stage_name,
                    start_time=start_time,
                    end_time=time.time(),
                    success=True
                )
                
                monitor.record_process_stage(metrics)
                return result
                
            except Exception as e:
                metrics = InterviewProcessMetrics(
                    interview_id=interview_id,
                    stage=stage_name,
                    start_time=start_time,
                    end_time=time.time(),
                    success=False,
                    error_details={
                        "error_type": type(e).__name__,
                        "error_message": str(e)
                    }
                )
                monitor.record_process_stage(metrics)
                raise
        
        return wrapper
    return decorator
