"""
Enterprise Security Implementation
Comprehensive security middleware and utilities for production deployment
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
import hashlib
import secrets
import time
from typing import Dict, Optional
import re
from pydantic import BaseModel


class SecurityHeaders(BaseHTTPMiddleware):
    """
    Enterprise-grade security headers middleware
    Implements OWASP security headers recommendations
    """
    
    def __init__(self, app, csp_policy: Optional[str] = None):
        super().__init__(app)
        self.csp_policy = csp_policy or (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: blob: https:; "
            "connect-src 'self' https://api.openai.com https://generativelanguage.googleapis.com; "
            "media-src 'self' blob:; "
            "frame-ancestors 'none'; "
            "base-uri 'self'"
        )
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        
        # Security headers for production
        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
            "Content-Security-Policy": self.csp_policy,
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
            "X-Permitted-Cross-Domain-Policies": "none",
            "X-Download-Options": "noopen"
        }
        
        for header, value in security_headers.items():
            response.headers[header] = value
        
        # Remove server information leakage
        if "server" in response.headers:
            del response.headers["server"]
        
        return response


class InputSanitizer:
    """
    Enterprise input sanitization and validation
    """
    
    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
        r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
        r"(\b(OR|AND)\s+['\"]\\w+['\"]\\s*=\\s*['\"]\\w+['\"]\\s*)",
        r"(--|#|/\\*|\\*/)",
        r"(\bxp_\\w+\b)",
        r"(\bsp_\\w+\b)"
    ]
    
    # XSS patterns
    XSS_PATTERNS = [
        r"<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>",
        r"javascript:",
        r"vbscript:",
        r"onload\s*=",
        r"onerror\s*=",
        r"onclick\s*=",
        r"onmouseover\s*="
    ]
    
    @classmethod
    def sanitize_string(cls, value: str, max_length: int = 1000) -> str:
        """
        Sanitize string input against common attacks
        """
        if not isinstance(value, str):
            return str(value)[:max_length]
        
        # Length validation
        if len(value) > max_length:
            value = value[:max_length]
        
        # SQL injection detection
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                raise ValueError("Potentially malicious SQL pattern detected")
        
        # XSS detection
        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                raise ValueError("Potentially malicious script pattern detected")
        
        # Basic HTML escaping
        value = value.replace("<", "&lt;").replace(">", "&gt;")
        value = value.replace("'", "&#x27;").replace('"', "&quot;")
        
        return value.strip()
    
    @classmethod
    def sanitize_email(cls, email: str) -> str:
        """
        Sanitize and validate email addresses
        """
        email = cls.sanitize_string(email, 254)  # RFC 5321 limit
        
        # Basic email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise ValueError("Invalid email format")
        
        return email.lower()


class SecurityAuditLogger:
    """
    Security event logging for compliance and monitoring
    """
    
    @staticmethod
    def log_authentication_attempt(
        user_id: Optional[int],
        email: str,
        success: bool,
        ip_address: str,
        user_agent: str,
        failure_reason: Optional[str] = None
    ):
        """
        Log authentication attempts for security monitoring
        """
        import logging
        
        logger = logging.getLogger("security.auth")
        
        log_data = {
            "event_type": "authentication_attempt",
            "user_id": user_id,
            "email": email,
            "success": success,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "timestamp": time.time(),
            "failure_reason": failure_reason
        }
        
        if success:
            logger.info("Authentication successful", extra=log_data)
        else:
            logger.warning("Authentication failed", extra=log_data)
    
    @staticmethod
    def log_data_access(
        user_id: int,
        resource_type: str,
        resource_id: Optional[int],
        action: str,
        ip_address: str,
        success: bool = True
    ):
        """
        Log data access for GDPR compliance
        """
        import logging
        
        logger = logging.getLogger("security.data_access")
        
        log_data = {
            "event_type": "data_access",
            "user_id": user_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "action": action,
            "ip_address": ip_address,
            "success": success,
            "timestamp": time.time()
        }
        
        logger.info("Data access event", extra=log_data)
    
    @staticmethod
    def log_security_event(
        event_type: str,
        severity: str,
        details: Dict,
        ip_address: str,
        user_id: Optional[int] = None
    ):
        """
        Log security events (suspicious activity, violations, etc.)
        """
        import logging
        
        logger = logging.getLogger("security.events")
        
        log_data = {
            "event_type": event_type,
            "severity": severity,
            "user_id": user_id,
            "ip_address": ip_address,
            "details": details,
            "timestamp": time.time()
        }
        
        if severity in ["HIGH", "CRITICAL"]:
            logger.error("Security event", extra=log_data)
        else:
            logger.warning("Security event", extra=log_data)


class RateLimitStore:
    """
    Simple in-memory rate limiting store
    For production, use Redis or similar
    """
    
    def __init__(self):
        self._store: Dict[str, Dict] = {}
        self._cleanup_interval = 3600  # 1 hour
        self._last_cleanup = time.time()
    
    def is_allowed(self, key: str, limit: int, window: int) -> bool:
        """
        Check if request is within rate limits
        """
        now = time.time()
        
        # Cleanup old entries periodically
        if now - self._last_cleanup > self._cleanup_interval:
            self._cleanup_expired(now)
        
        if key not in self._store:
            self._store[key] = {"count": 1, "window_start": now}
            return True
        
        entry = self._store[key]
        
        # Reset window if expired
        if now - entry["window_start"] > window:
            entry["count"] = 1
            entry["window_start"] = now
            return True
        
        # Check if within limits
        if entry["count"] >= limit:
            return False
        
        entry["count"] += 1
        return True
    
    def _cleanup_expired(self, now: float):
        """
        Remove expired entries to prevent memory leaks
        """
        expired_keys = []
        for key, entry in self._store.items():
            if now - entry["window_start"] > 3600:  # 1 hour
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._store[key]
        
        self._last_cleanup = now


class EnterpriseRateLimiter(BaseHTTPMiddleware):
    """
    Enterprise rate limiting middleware
    """
    
    def __init__(self, app, default_limit: int = 100, default_window: int = 3600):
        super().__init__(app)
        self.store = RateLimitStore()
        self.default_limit = default_limit
        self.default_window = default_window
        
        # Different limits for different endpoints
        self.endpoint_limits = {
            "/api/v1/auth/login": (10, 300),  # 10 attempts per 5 minutes (increased)
            "/api/v1/auth/register": (5, 3600),  # 5 per hour (increased)
            "/api/v1/interviews/": (100, 300),  # 100 per 5 minutes (much more for dashboard)
            "/api/v1/candidates/": (100, 300),  # 100 per 5 minutes for dashboard
            "/api/v1/jobs/": (100, 300),  # 100 per 5 minutes for dashboard
        }
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Get rate limit for this endpoint
        path = request.url.path
        limit, window = self.endpoint_limits.get(path, (self.default_limit, self.default_window))
        
        # Create rate limit key
        rate_key = f"{client_ip}:{path}"
        
        # Check rate limit
        if not self.store.is_allowed(rate_key, limit, window):
            # Minimal security logging for rate limit events
            try:
                SecurityAuditLogger.log_security_event(
                    event_type="rate_limit_exceeded",
                    severity="LOW",
                    details={"path": path, "limit": limit, "window": window},
                    ip_address=client_ip,
                    user_id=None,
                )
            except Exception:
                pass
            from fastapi import HTTPException
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later.",
                headers={"Retry-After": str(window)}
            )
        
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Window"] = str(window)
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Extract real client IP considering proxies
        """
        # Check for forwarded headers (common in production)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct connection
        return request.client.host if request.client else "unknown"


def generate_secure_token(length: int = 32) -> str:
    """
    Generate cryptographically secure random token
    """
    return secrets.token_urlsafe(length)


def hash_password_secure(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """
    Hash password with secure salt using scrypt
    """
    if salt is None:
        salt = secrets.token_hex(32)
    
    # Use scrypt for password hashing (more secure than bcrypt against hardware attacks)
    key = hashlib.scrypt(
        password.encode('utf-8'),
        salt=salt.encode('utf-8'),
        n=16384,  # CPU/memory cost factor
        r=8,      # Block size
        p=1       # Parallelization factor
    )
    
    return key.hex(), salt


def verify_password_secure(password: str, hashed_password: str, salt: str) -> bool:
    """
    Verify password against secure hash
    """
    try:
        key = hashlib.scrypt(
            password.encode('utf-8'),
            salt=salt.encode('utf-8'),
            n=16384,
            r=8,
            p=1
        )
        return secrets.compare_digest(key.hex(), hashed_password)
    except Exception:
        return False
