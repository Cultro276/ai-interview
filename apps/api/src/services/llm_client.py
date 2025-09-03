"""
LLMClient - Unified LLM provider management
Centralizes OpenAI, Gemini, and fallback logic with proper error handling
"""

from __future__ import annotations
import asyncio
import time
import hashlib
import json
from typing import Dict, Any, Optional, List, Literal
from enum import Enum
from dataclasses import dataclass, field
from contextlib import asynccontextmanager

import httpx
from src.core.config import settings


class LLMProvider(str, Enum):
    OPENAI = "openai"
    GEMINI = "gemini"
    FALLBACK = "fallback"


@dataclass
class LLMRequest:
    """Standardized LLM request format"""
    prompt: str
    model: str = "gpt-4o-mini"
    temperature: float = 0.3
    max_tokens: Optional[int] = None
    response_format: Optional[Dict[str, str]] = None
    system_message: Optional[str] = None
    messages: Optional[List[Dict[str, str]]] = None


@dataclass
class LLMResponse:
    """Standardized LLM response format"""
    content: str
    provider: LLMProvider
    model: str
    tokens_used: Optional[int] = None
    cost_estimate: Optional[float] = None
    response_time_ms: int = 0
    cached: bool = False


@dataclass
class CircuitBreakerState:
    """Circuit breaker state for each provider"""
    failure_count: int = 0
    last_failure_time: float = 0
    is_open: bool = False
    next_attempt_time: float = 0


class LLMClient:
    """
    Unified LLM client with circuit breaker, retry logic, and caching
    """
    
    def __init__(self):
        self.circuit_breakers: Dict[LLMProvider, CircuitBreakerState] = {
            provider: CircuitBreakerState() 
            for provider in LLMProvider
        }
        self.response_cache: Dict[str, LLMResponse] = {}
        self.cache_ttl: float = 3600  # 1 hour
        self.cache_timestamps: Dict[str, float] = {}
        
        # Circuit breaker config
        self.max_failures = 5
        self.circuit_timeout = 300  # 5 minutes
        self.base_backoff = 2  # seconds
        self.max_backoff = 60  # seconds
    
    def _get_cache_key(self, request: LLMRequest) -> str:
        """Generate cache key from request"""
        key_data = {
            "prompt": request.prompt[:500],  # First 500 chars
            "model": request.model,
            "temperature": request.temperature,
            "system_message": request.system_message,
            "response_format": request.response_format
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached response is still valid"""
        if cache_key not in self.response_cache:
            return False
        
        timestamp = self.cache_timestamps.get(cache_key, 0)
        return time.time() - timestamp < self.cache_ttl
    
    def _get_cached_response(self, cache_key: str) -> Optional[LLMResponse]:
        """Get cached response if valid"""
        if self._is_cache_valid(cache_key):
            response = self.response_cache[cache_key]
            response.cached = True
            return response
        return None
    
    def _cache_response(self, cache_key: str, response: LLMResponse) -> None:
        """Cache response"""
        self.response_cache[cache_key] = response
        self.cache_timestamps[cache_key] = time.time()
        
        # Clean old cache entries (simple LRU)
        if len(self.response_cache) > 1000:
            oldest_keys = sorted(
                self.cache_timestamps.items(), 
                key=lambda x: x[1]
            )[:100]
            
            for key, _ in oldest_keys:
                self.response_cache.pop(key, None)
                self.cache_timestamps.pop(key, None)
    
    def _is_circuit_open(self, provider: LLMProvider) -> bool:
        """Check if circuit breaker is open for provider"""
        breaker = self.circuit_breakers[provider]
        
        if not breaker.is_open:
            return False
        
        # Check if timeout period has passed
        if time.time() > breaker.next_attempt_time:
            breaker.is_open = False
            breaker.failure_count = 0
            return False
        
        return True
    
    def _record_success(self, provider: LLMProvider) -> None:
        """Record successful call"""
        breaker = self.circuit_breakers[provider]
        breaker.failure_count = 0
        breaker.is_open = False
    
    def _record_failure(self, provider: LLMProvider) -> None:
        """Record failed call and potentially open circuit"""
        breaker = self.circuit_breakers[provider]
        breaker.failure_count += 1
        breaker.last_failure_time = time.time()
        
        if breaker.failure_count >= self.max_failures:
            breaker.is_open = True
            breaker.next_attempt_time = time.time() + self.circuit_timeout
    
    async def _call_openai(self, request: LLMRequest) -> LLMResponse:
        """Call OpenAI API"""
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key not configured")
        
        headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
        
        # Build messages
        messages = []
        if request.system_message:
            messages.append({"role": "system", "content": request.system_message})
        
        if request.messages:
            messages.extend(request.messages)
        else:
            messages.append({"role": "user", "content": request.prompt})
        
        payload = {
            "model": request.model,
            "messages": messages,
            "temperature": request.temperature,
        }
        
        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens
        
        if request.response_format:
            payload["response_format"] = request.response_format
        
        start_time = time.time()
        
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            data = response.json()
        
        response_time_ms = int((time.time() - start_time) * 1000)
        content = data["choices"][0]["message"]["content"]
        tokens_used = data.get("usage", {}).get("total_tokens", 0)
        
        # Rough cost estimate (GPT-4o-mini pricing)
        cost_estimate = tokens_used * 0.000001  # $1 per 1M tokens
        
        return LLMResponse(
            content=content,
            provider=LLMProvider.OPENAI,
            model=request.model,
            tokens_used=tokens_used,
            cost_estimate=cost_estimate,
            response_time_ms=response_time_ms
        )
    
    async def _call_gemini(self, request: LLMRequest) -> LLMResponse:
        """Call Gemini API"""
        if not settings.gemini_api_key:
            raise ValueError("Gemini API key not configured")
        
        try:
            from google import genai  # type: ignore
        except ImportError:
            raise ValueError("google-genai library not installed")
        
        from anyio import to_thread
        
        def _sync_call():
            client = genai.Client(api_key=settings.gemini_api_key)
            
            # Build content
            content = ""
            if request.system_message:
                content += f"System: {request.system_message}\n\n"
            content += f"User: {request.prompt}"
            
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=content,
            )
            return response.text or ""
        
        start_time = time.time()
        content = await to_thread.run_sync(_sync_call)
        response_time_ms = int((time.time() - start_time) * 1000)
        
        return LLMResponse(
            content=content,
            provider=LLMProvider.GEMINI,
            model="gemini-2.5-flash",
            response_time_ms=response_time_ms
        )
    
    def _get_fallback_response(self, request: LLMRequest) -> LLMResponse:
        """Generate fallback response using rules"""
        
        # Simple rule-based responses based on prompt content
        prompt_lower = request.prompt.lower()
        
        if "hr criteria" in prompt_lower or "soft skills" in prompt_lower:
            content = json.dumps({
                "criteria": [
                    {
                        "label": "İletişim Netliği",
                        "score_0_100": 70,
                        "evidence": "Orta düzey iletişim becerisi gözlendi",
                        "confidence": 0.5,
                        "reasoning": "Yetersiz veri nedeniyle genel değerlendirme"
                    }
                ],
                "summary": "LLM servisi mevcut olmadığı için genel değerlendirme yapıldı",
                "overall_score": 70.0
            })
        
        elif "job fit" in prompt_lower or "requirements" in prompt_lower:
            content = json.dumps({
                "job_fit_summary": "LLM servisi mevcut olmadığı için detaylı analiz yapılamadı",
                "overall_fit_score": 0.5,
                "requirements_matrix": [],
                "recommendations": ["LLM servisi aktif olduğunda detaylı analiz yapılmalı"]
            })
        
        elif "hiring" in prompt_lower or "opinion" in prompt_lower:
            content = json.dumps({
                "hire_recommendation": "Hold",
                "overall_assessment": "LLM servisi mevcut olmadığı için manuel değerlendirme gerekli",
                "decision_confidence": 0.3,
                "key_strengths": ["Manuel değerlendirme gerekli"],
                "key_concerns": ["Otomatik analiz yapılamadı"]
            })
        
        else:
            content = "Mülakat sorusu üretimi için LLM servisi mevcut değil. Lütfen manual soru hazırlayın."
        
        return LLMResponse(
            content=content,
            provider=LLMProvider.FALLBACK,
            model="rule-based",
            response_time_ms=10
        )
    
    async def _call_with_retry(self, provider: LLMProvider, request: LLMRequest, max_retries: int = 3) -> LLMResponse:
        """Call provider with exponential backoff retry"""
        
        for attempt in range(max_retries):
            try:
                if provider == LLMProvider.OPENAI:
                    return await self._call_openai(request)
                elif provider == LLMProvider.GEMINI:
                    return await self._call_gemini(request)
                else:
                    return self._get_fallback_response(request)
            
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:  # Rate limit
                    if attempt < max_retries - 1:
                        backoff = min(self.base_backoff * (2 ** attempt), self.max_backoff)
                        await asyncio.sleep(backoff)
                        continue
                raise
            
            except Exception as e:
                if attempt < max_retries - 1:
                    backoff = min(self.base_backoff * (2 ** attempt), self.max_backoff)
                    await asyncio.sleep(backoff)
                    continue
                raise
        
        raise Exception(f"Max retries ({max_retries}) exceeded for {provider}")
    
    async def generate(self, request: LLMRequest, preferred_provider: Optional[LLMProvider] = None) -> LLMResponse:
        """
        Generate response using available providers with fallback chain
        """
        
        # Check cache first
        cache_key = self._get_cache_key(request)
        cached = self._get_cached_response(cache_key)
        if cached:
            return cached
        
        # Determine provider order
        providers = []
        if preferred_provider:
            providers.append(preferred_provider)
        
        # Add remaining providers in preference order
        default_order = [LLMProvider.OPENAI, LLMProvider.GEMINI, LLMProvider.FALLBACK]
        for provider in default_order:
            if provider not in providers:
                providers.append(provider)
        
        # Try providers in order
        for provider in providers:
            if self._is_circuit_open(provider):
                continue
            
            try:
                response = await self._call_with_retry(provider, request)
                self._record_success(provider)
                self._cache_response(cache_key, response)
                return response
            
            except Exception as e:
                self._record_failure(provider)
                if provider == LLMProvider.FALLBACK:
                    # Fallback should never fail
                    return self._get_fallback_response(request)
                continue
        
        # All providers failed, return fallback
        return self._get_fallback_response(request)
    
    async def batch_generate(self, requests: List[LLMRequest]) -> List[LLMResponse]:
        """Generate multiple responses in parallel"""
        tasks = [self.generate(request) for request in requests]
        return await asyncio.gather(*tasks)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics"""
        return {
            "cache_size": len(self.response_cache),
            "circuit_breakers": {
                provider.value: {
                    "failure_count": breaker.failure_count,
                    "is_open": breaker.is_open,
                    "next_attempt_time": breaker.next_attempt_time
                }
                for provider, breaker in self.circuit_breakers.items()
            }
        }


# Global client instance
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get or create global LLM client instance"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client


# Convenience functions for common operations
async def generate_text(
    prompt: str,
    system_message: Optional[str] = None,
    model: str = "gpt-4o-mini",
    temperature: float = 0.3,
    max_tokens: Optional[int] = None
) -> str:
    """Simple text generation"""
    client = get_llm_client()
    request = LLMRequest(
        prompt=prompt,
        system_message=system_message,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens
    )
    response = await client.generate(request)
    return response.content


async def generate_json(
    prompt: str,
    system_message: Optional[str] = None,
    model: str = "gpt-4o-mini",
    temperature: float = 0.1
) -> Dict[str, Any]:
    """JSON generation with structured output"""
    client = get_llm_client()
    request = LLMRequest(
        prompt=prompt,
        system_message=system_message,
        model=model,
        temperature=temperature,
        response_format={"type": "json_object"}
    )
    response = await client.generate(request)
    
    try:
        return json.loads(response.content)
    except json.JSONDecodeError:
        # Try to extract JSON from response
        import re
        json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        # Return structured error
        return {
            "error": "Failed to parse JSON response",
            "raw_response": response.content,
            "provider": response.provider.value
        }
