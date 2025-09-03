"""
PerformanceOptimizer - Caching and parallel processing optimizations
Provides intelligent caching for CV parsing, job requirements, and LLM responses
"""

from __future__ import annotations
import asyncio
import hashlib
import json
import time
from typing import Dict, Any, Optional, List, Callable, TypeVar, Awaitable
from dataclasses import dataclass
from enum import Enum

T = TypeVar('T')


class CacheType(str, Enum):
    CV_PARSING = "cv_parsing"
    JOB_REQUIREMENTS = "job_requirements"
    LLM_RESPONSE = "llm_response"
    ANALYSIS_RESULTS = "analysis_results"


@dataclass
class CacheEntry:
    """Cache entry with TTL and metadata"""
    data: Any
    timestamp: float
    ttl_seconds: int
    access_count: int = 0
    size_bytes: int = 0
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        return time.time() - self.timestamp > self.ttl_seconds
    
    def access(self) -> Any:
        """Access cache entry and update statistics"""
        self.access_count += 1
        return self.data


class PerformanceCache:
    """
    High-performance cache with intelligent eviction and size management
    """
    
    def __init__(self, max_size_mb: int = 100, default_ttl: int = 3600):
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.default_ttl = default_ttl
        self.cache: Dict[str, CacheEntry] = {}
        self.size_tracking = {
            CacheType.CV_PARSING: 0,
            CacheType.JOB_REQUIREMENTS: 0,
            CacheType.LLM_RESPONSE: 0,
            CacheType.ANALYSIS_RESULTS: 0
        }
    
    def _calculate_size(self, data: Any) -> int:
        """Estimate memory size of data"""
        try:
            if isinstance(data, (dict, list)):
                return len(json.dumps(data, ensure_ascii=False).encode('utf-8'))
            elif isinstance(data, str):
                return len(data.encode('utf-8'))
            else:
                return len(str(data).encode('utf-8'))
        except Exception:
            return 1024  # Default estimate
    
    def _evict_if_needed(self, required_space: int) -> None:
        """Evict old entries if cache is too large"""
        current_size = sum(entry.size_bytes for entry in self.cache.values())
        
        if current_size + required_space <= self.max_size_bytes:
            return
        
        # Sort by access frequency and age (LRU + LFU hybrid)
        entries_by_score = []
        current_time = time.time()
        
        for key, entry in self.cache.items():
            if entry.is_expired():
                entries_by_score.append((0, key, entry))  # Expired entries first
            else:
                # Score based on access frequency and recency
                age_penalty = (current_time - entry.timestamp) / entry.ttl_seconds
                frequency_bonus = min(entry.access_count, 10) / 10
                score = frequency_bonus - age_penalty
                entries_by_score.append((score, key, entry))
        
        # Evict lowest scoring entries
        entries_by_score.sort(key=lambda x: x[0])
        
        for score, key, entry in entries_by_score:
            del self.cache[key]
            current_size -= entry.size_bytes
            
            if current_size + required_space <= self.max_size_bytes:
                break
    
    def get_cache_key(self, cache_type: CacheType, *args) -> str:
        """Generate cache key from type and arguments"""
        key_data = f"{cache_type.value}:" + ":".join(str(arg)[:100] for arg in args)
        return hashlib.md5(key_data.encode('utf-8')).hexdigest()
    
    def get(self, cache_type: CacheType, *args) -> Optional[Any]:
        """Get cached data"""
        key = self.get_cache_key(cache_type, *args)
        entry = self.cache.get(key)
        
        if entry is None:
            return None
        
        if entry.is_expired():
            del self.cache[key]
            return None
        
        return entry.access()
    
    def set(self, cache_type: CacheType, data: Any, ttl: Optional[int] = None, *args) -> None:
        """Cache data with optional TTL override"""
        key = self.get_cache_key(cache_type, *args)
        size = self._calculate_size(data)
        
        # Evict if needed
        self._evict_if_needed(size)
        
        entry = CacheEntry(
            data=data,
            timestamp=time.time(),
            ttl_seconds=ttl or self.default_ttl,
            size_bytes=size
        )
        
        self.cache[key] = entry
    
    def invalidate_type(self, cache_type: CacheType) -> int:
        """Invalidate all entries of a specific type"""
        prefix = f"{cache_type.value}:"
        keys_to_delete = [key for key in self.cache.keys() if key.startswith(prefix)]
        
        for key in keys_to_delete:
            del self.cache[key]
        
        return len(keys_to_delete)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        current_time = time.time()
        total_size = 0
        type_counts = {cache_type: 0 for cache_type in CacheType}
        expired_count = 0
        
        for key, entry in self.cache.items():
            total_size += entry.size_bytes
            
            if entry.is_expired():
                expired_count += 1
            
            # Count by type
            for cache_type in CacheType:
                if key.startswith(f"{cache_type.value}:"):
                    type_counts[cache_type] += 1
                    break
        
        return {
            "total_entries": len(self.cache),
            "total_size_mb": total_size / (1024 * 1024),
            "expired_entries": expired_count,
            "type_counts": type_counts,
            "hit_rate": self._calculate_hit_rate()
        }
    
    def _calculate_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        # Simplified hit rate calculation
        total_accesses = sum(entry.access_count for entry in self.cache.values())
        if total_accesses == 0:
            return 0.0
        return min(1.0, total_accesses / (len(self.cache) + 1))


class ParallelProcessor:
    """
    Utility for running tasks in parallel with intelligent batching
    """
    
    @staticmethod
    async def batch_execute(
        tasks: List[Callable[[], Awaitable[T]]], 
        batch_size: int = 5,
        max_concurrency: int = 10
    ) -> List[T]:
        """
        Execute tasks in batches with controlled concurrency
        """
        if not tasks:
            return []
        
        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrency)
        
        async def limited_task(task):
            async with semaphore:
                return await task()
        
        # Execute all tasks with concurrency limit
        results = await asyncio.gather(
            *[limited_task(task) for task in tasks],
            return_exceptions=True
        )
        
        # Filter out exceptions and return successful results
        successful_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Log error but don't fail entire batch
                continue
            successful_results.append(result)
        
        return successful_results
    
    @staticmethod
    async def parallel_analysis(
        job_description: str,
        transcript_text: str, 
        resume_text: str = "",
        analysis_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Run multiple analysis types in parallel
        Optimized version of ComprehensiveAnalyzer
        """
        from src.services.comprehensive_analyzer import ComprehensiveAnalyzer, AnalysisInput, AnalysisType
        
        analyzer = ComprehensiveAnalyzer()
        
        # Default analysis types
        if analysis_types is None:
            analysis_types = ["hr_criteria", "job_fit", "hiring_decision"]
        
        # Map string types to enum types
        type_mapping = {
            "hr_criteria": AnalysisType.HR_CRITERIA,
            "job_fit": AnalysisType.JOB_FIT,
            "hiring_decision": AnalysisType.HIRING_DECISION,
            "candidate_profile": AnalysisType.CANDIDATE_PROFILE,
            "soft_skills": AnalysisType.SOFT_SKILLS,
            "requirements_extraction": AnalysisType.REQUIREMENTS_EXTRACTION
        }
        
        enum_types = [type_mapping[t] for t in analysis_types if t in type_mapping]
        
        input_data = AnalysisInput(
            job_description=job_description,
            transcript_text=transcript_text,
            resume_text=resume_text,
            analysis_types=enum_types
        )
        
        # This already runs analysis types in parallel
        return await analyzer.analyze_comprehensive(input_data)


class CachedAnalysisService:
    """
    High-level service that combines caching with parallel processing
    """
    
    def __init__(self, cache: Optional[PerformanceCache] = None):
        self.cache = cache or PerformanceCache()
        self.parallel_processor = ParallelProcessor()
    
    async def cached_cv_parsing(self, cv_content: bytes, content_type: str, filename: str = "") -> Dict[str, Any]:
        """
        Parse CV with caching based on content hash
        """
        # Generate cache key from content hash
        content_hash = hashlib.sha256(cv_content).hexdigest()
        
        # Check cache first
        cached = self.cache.get(CacheType.CV_PARSING, content_hash, content_type)
        if cached:
            return cached
        
        # Parse CV if not cached
        from src.services.nlp import parse_resume_bytes, extract_candidate_fields_smart
        
        try:
            # Parse resume text
            resume_text = parse_resume_bytes(cv_content, content_type, filename)
            
            # Extract candidate fields
            candidate_fields = await extract_candidate_fields_smart(resume_text, filename)
            
            result = {
                "resume_text": resume_text,
                "candidate_fields": candidate_fields,
                "parsed_at": time.time(),
                "content_hash": content_hash
            }
            
            # Cache for 24 hours
            self.cache.set(CacheType.CV_PARSING, result, 86400, content_hash, content_type)
            
            return result
            
        except Exception as e:
            # Return error info but don't cache errors
            return {
                "error": str(e),
                "resume_text": "",
                "candidate_fields": {},
                "content_hash": content_hash
            }
    
    async def cached_job_requirements(self, job_description: str) -> Dict[str, Any]:
        """
        Extract job requirements with caching
        """
        if not job_description.strip():
            return {"items": []}
        
        # Generate cache key from job description hash
        job_hash = hashlib.md5(job_description.strip().encode('utf-8')).hexdigest()
        
        # Check cache first
        cached = self.cache.get(CacheType.JOB_REQUIREMENTS, job_hash)
        if cached:
            return cached
        
        # Extract requirements if not cached
        from src.services.comprehensive_analyzer import extract_requirements_spec
        
        try:
            result = await extract_requirements_spec(job_description)
            
            # Cache for 1 hour (job descriptions change less frequently than CVs)
            self.cache.set(CacheType.JOB_REQUIREMENTS, result, 3600, job_hash)
            
            return result
            
        except Exception:
            # Return empty requirements on error
            return {"items": []}
    
    async def cached_comprehensive_analysis(
        self, 
        job_description: str,
        transcript_text: str,
        resume_text: str = "",
        candidate_name: str = "",
        job_title: str = ""
    ) -> Dict[str, Any]:
        """
        Run comprehensive analysis with intelligent caching
        """
        # Generate cache key from inputs
        input_hash = hashlib.md5(
            (job_description + transcript_text + resume_text).encode('utf-8')
        ).hexdigest()
        
        # Check cache first (shorter TTL for analysis results)
        cached = self.cache.get(CacheType.ANALYSIS_RESULTS, input_hash)
        if cached:
            return cached
        
        # Run analysis if not cached
        try:
            result = await self.parallel_processor.parallel_analysis(
                job_description=job_description,
                transcript_text=transcript_text,
                resume_text=resume_text
            )
            
            # Add metadata
            result["meta"] = result.get("meta", {})
            result["meta"].update({
                "candidate_name": candidate_name,
                "job_title": job_title,
                "cached_analysis": True,
                "analysis_hash": input_hash
            })
            
            # Cache for 30 minutes (analysis results can change with model updates)
            self.cache.set(CacheType.ANALYSIS_RESULTS, result, 1800, input_hash)
            
            return result
            
        except Exception as e:
            # Return error result but don't cache
            return {
                "error": str(e),
                "meta": {
                    "candidate_name": candidate_name,
                    "job_title": job_title,
                    "analysis_failed": True
                }
            }
    
    def clear_cache(self, cache_type: Optional[CacheType] = None) -> int:
        """Clear cache entries"""
        if cache_type:
            return self.cache.invalidate_type(cache_type)
        else:
            count = len(self.cache.cache)
            self.cache.cache.clear()
            return count
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return self.cache.get_stats()


# Global instances
_performance_cache: Optional[PerformanceCache] = None
_cached_analysis_service: Optional[CachedAnalysisService] = None


def get_performance_cache() -> PerformanceCache:
    """Get or create global performance cache instance"""
    global _performance_cache
    if _performance_cache is None:
        _performance_cache = PerformanceCache(max_size_mb=200, default_ttl=3600)
    return _performance_cache


def get_cached_analysis_service() -> CachedAnalysisService:
    """Get or create global cached analysis service instance"""
    global _cached_analysis_service
    if _cached_analysis_service is None:
        _cached_analysis_service = CachedAnalysisService(get_performance_cache())
    return _cached_analysis_service


# Convenience functions
async def cached_cv_analysis(cv_content: bytes, content_type: str, filename: str = "") -> Dict[str, Any]:
    """Convenience function for cached CV analysis"""
    service = get_cached_analysis_service()
    return await service.cached_cv_parsing(cv_content, content_type, filename)


async def cached_job_analysis(job_description: str) -> Dict[str, Any]:
    """Convenience function for cached job requirements analysis"""
    service = get_cached_analysis_service()
    return await service.cached_job_requirements(job_description)


async def cached_interview_analysis(
    job_description: str,
    transcript_text: str,
    resume_text: str = "",
    candidate_name: str = "",
    job_title: str = ""
) -> Dict[str, Any]:
    """Convenience function for cached comprehensive interview analysis"""
    service = get_cached_analysis_service()
    return await service.cached_comprehensive_analysis(
        job_description, transcript_text, resume_text, candidate_name, job_title
    )
