"""
Enterprise Error Handling System
Standardized error responses, logging, and user-friendly messages
"""
import traceback
import uuid
from typing import Dict, Any, Optional, List, Union
from enum import Enum
from datetime import datetime
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError as PydanticValidationError
import logging


class ErrorCategory(str, Enum):
    """Categories of errors for better classification"""
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    NOT_FOUND = "not_found"
    BUSINESS_LOGIC = "business_logic"
    EXTERNAL_SERVICE = "external_service"
    SYSTEM = "system"
    RATE_LIMIT = "rate_limit"
    MAINTENANCE = "maintenance"


class ErrorSeverity(str, Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorResponse(BaseModel):
    """Standardized error response model"""
    error: str = Field(..., description="Error identifier")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    request_id: str = Field(..., description="Unique request identifier")
    timestamp: str = Field(..., description="ISO timestamp of the error")
    category: ErrorCategory = Field(..., description="Error category")
    severity: ErrorSeverity = Field(..., description="Error severity")
    
    # User guidance
    user_message: Optional[str] = Field(None, description="User-friendly message")
    suggested_action: Optional[str] = Field(None, description="Suggested action for the user")
    documentation_url: Optional[str] = Field(None, description="Link to relevant documentation")
    
    # Development info (only in development mode)
    stack_trace: Optional[str] = Field(None, description="Stack trace for debugging")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "validation_failed",
                "message": "Input validation failed",
                "details": {"field": "email", "issue": "Invalid email format"},
                "request_id": "req_123456789",
                "timestamp": "2024-01-15T10:30:00Z",
                "category": "validation",
                "severity": "medium",
                "user_message": "Lütfen geçerli bir e-posta adresi giriniz.",
                "suggested_action": "E-posta formatını kontrol edip tekrar deneyiniz.",
                "documentation_url": "https://docs.example.com/api/validation"
            }
        }


class ValidationErrorDetail(BaseModel):
    """Detailed validation error information"""
    field: str = Field(..., description="Field that failed validation")
    message: str = Field(..., description="Validation error message")
    code: str = Field(..., description="Validation error code")
    value: Optional[Any] = Field(None, description="Invalid value (sanitized)")


class ApplicationError(Exception):
    """Base application error with rich context"""
    
    def __init__(
        self,
        error_code: str,
        message: str,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None,
        suggested_action: Optional[str] = None,
        documentation_url: Optional[str] = None
    ):
        self.error_code = error_code
        self.message = message
        self.category = category
        self.severity = severity
        self.status_code = status_code
        self.details = details or {}
        self.user_message = user_message
        self.suggested_action = suggested_action
        self.documentation_url = documentation_url
        self.request_id = str(uuid.uuid4())
        self.timestamp = datetime.utcnow()
        
        super().__init__(message)


class ValidationError(ApplicationError):
    """Validation-specific error"""
    
    def __init__(
        self,
        message: str,
        field_errors: Optional[List[ValidationErrorDetail]] = None,
        user_message: str = "Girilen bilgilerde hata bulundu. Lütfen kontrol edip tekrar deneyiniz."
    ):
        super().__init__(
            error_code="validation_failed",
            message=message,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            status_code=422,
            details={"field_errors": [error.dict() for error in (field_errors or [])]},
            user_message=user_message,
            suggested_action="Girilen bilgileri kontrol edip tekrar deneyiniz.",
            documentation_url="https://docs.aiinterview.com/api/validation"
        )


class AuthenticationError(ApplicationError):
    """Authentication-specific error"""
    
    def __init__(
        self,
        message: str = "Authentication failed",
        user_message: str = "Giriş yapmanız gerekiyor.",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            error_code="authentication_failed",
            message=message,
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.HIGH,
            status_code=401,
            details=details,
            user_message=user_message,
            suggested_action="Lütfen giriş yapın veya token'ınızı kontrol edin.",
            documentation_url="https://docs.aiinterview.com/api/authentication"
        )


class AuthorizationError(ApplicationError):
    """Authorization-specific error"""
    
    def __init__(
        self,
        message: str = "Access denied",
        required_permission: Optional[str] = None,
        user_message: str = "Bu işlem için yetkiniz bulunmuyor."
    ):
        super().__init__(
            error_code="access_denied",
            message=message,
            category=ErrorCategory.AUTHORIZATION,
            severity=ErrorSeverity.HIGH,
            status_code=403,
            details={"required_permission": required_permission} if required_permission else None,
            user_message=user_message,
            suggested_action="Yöneticinizle iletişime geçin veya gerekli yetkileri edinin.",
            documentation_url="https://docs.aiinterview.com/api/permissions"
        )


class NotFoundError(ApplicationError):
    """Resource not found error"""
    
    def __init__(
        self,
        resource_type: str,
        resource_id: Optional[Union[str, int]] = None,
        user_message: str = "Aranan kaynak bulunamadı."
    ):
        message = f"{resource_type} not found"
        if resource_id:
            message += f" (ID: {resource_id})"
        
        super().__init__(
            error_code="resource_not_found",
            message=message,
            category=ErrorCategory.NOT_FOUND,
            severity=ErrorSeverity.LOW,
            status_code=404,
            details={"resource_type": resource_type, "resource_id": resource_id},
            user_message=user_message,
            suggested_action="Kaynak ID'sini kontrol edin veya başka bir kaynak deneyin.",
            documentation_url="https://docs.aiinterview.com/api/resources"
        )


class BusinessLogicError(ApplicationError):
    """Business logic violation error"""
    
    def __init__(
        self,
        rule: str,
        message: str,
        user_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            error_code="business_rule_violation",
            message=message,
            category=ErrorCategory.BUSINESS_LOGIC,
            severity=ErrorSeverity.MEDIUM,
            status_code=409,
            details={"rule": rule, **(details or {})},
            user_message=user_message or "İşlem iş kuralları nedeniyle gerçekleştirilemedi.",
            suggested_action="İşlem koşullarını kontrol edin ve tekrar deneyin."
        )


class ExternalServiceError(ApplicationError):
    """External service error"""
    
    def __init__(
        self,
        service: str,
        message: str,
        service_status_code: Optional[int] = None,
        user_message: str = "Harici serviste geçici bir sorun oluştu."
    ):
        super().__init__(
            error_code="external_service_error",
            message=message,
            category=ErrorCategory.EXTERNAL_SERVICE,
            severity=ErrorSeverity.HIGH,
            status_code=502,
            details={"service": service, "service_status_code": service_status_code},
            user_message=user_message,
            suggested_action="Lütfen birkaç dakika sonra tekrar deneyin.",
            documentation_url="https://docs.aiinterview.com/api/external-services"
        )


class RateLimitError(ApplicationError):
    """Rate limit exceeded error"""
    
    def __init__(
        self,
        limit: int,
        window_seconds: int,
        retry_after_seconds: Optional[int] = None
    ):
        super().__init__(
            error_code="rate_limit_exceeded",
            message=f"Rate limit exceeded: {limit} requests per {window_seconds} seconds",
            category=ErrorCategory.RATE_LIMIT,
            severity=ErrorSeverity.MEDIUM,
            status_code=429,
            details={
                "limit": limit,
                "window_seconds": window_seconds,
                "retry_after_seconds": retry_after_seconds
            },
            user_message="Çok fazla istek gönderdiniz. Lütfen bekleyin.",
            suggested_action=f"Lütfen {retry_after_seconds or window_seconds} saniye bekleyip tekrar deneyin."
        )


class ErrorHandler:
    """Centralized error handling system"""
    
    def __init__(self):
        self.logger = logging.getLogger("errors")
        self.development_mode = False  # Set from environment
    
    async def handle_application_error(
        self,
        request: Request,
        error: ApplicationError
    ) -> JSONResponse:
        """Handle custom application errors"""
        
        # Log the error
        await self._log_error(request, error)
        
        # Create response
        response = ErrorResponse(
            error=error.error_code,
            message=error.message,
            details=error.details,
            request_id=error.request_id,
            timestamp=error.timestamp.isoformat(),
            category=error.category,
            severity=error.severity,
            user_message=error.user_message,
            suggested_action=error.suggested_action,
            documentation_url=error.documentation_url,
            stack_trace=None
        )
        
        # Add stack trace in development mode
        if self.development_mode:
            response.stack_trace = traceback.format_exc()
        
        return JSONResponse(
            status_code=error.status_code,
            content=response.dict(exclude_none=True)
        )
    
    async def handle_http_exception(
        self,
        request: Request,
        exc: HTTPException
    ) -> JSONResponse:
        """Handle FastAPI HTTP exceptions"""
        
        # Convert to ApplicationError
        category = self._categorize_http_exception(exc.status_code)
        severity = self._determine_severity(exc.status_code)
        
        error = ApplicationError(
            error_code=f"http_{exc.status_code}",
            message=str(exc.detail),
            category=category,
            severity=severity,
            status_code=exc.status_code,
            user_message=self._get_user_friendly_message(exc.status_code),
            suggested_action=self._get_suggested_action(exc.status_code)
        )
        
        return await self.handle_application_error(request, error)
    
    async def handle_validation_exception(
        self,
        request: Request,
        exc: Union[PydanticValidationError, Exception]
    ) -> JSONResponse:
        """Handle Pydantic validation exceptions"""
        
        field_errors = []
        if isinstance(exc, PydanticValidationError):
            for error in exc.errors():
                field_errors.append(ValidationErrorDetail(
                    field='.'.join(str(loc) for loc in error['loc']),
                    message=error['msg'],
                    code=error['type'],
                    value=str(error.get('input', ''))[:100]  # Truncate long values
                ))
        
        validation_error = ValidationError(
            message="Validation failed",
            field_errors=field_errors
        )
        
        return await self.handle_application_error(request, validation_error)
    
    async def handle_generic_exception(
        self,
        request: Request,
        exc: Exception
    ) -> JSONResponse:
        """Handle unexpected exceptions"""
        
        error = ApplicationError(
            error_code="internal_server_error",
            message="An unexpected error occurred",
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.CRITICAL,
            status_code=500,
            details={"exception_type": type(exc).__name__},
            user_message="Beklenmeyen bir hata oluştu. Teknik ekibimiz bilgilendirildi.",
            suggested_action="Lütfen birkaç dakika sonra tekrar deneyin. Sorun devam ederse destek ekibiyle iletişime geçin."
        )
        
        # Log with full stack trace
        self.logger.error(
            f"Unhandled exception: {exc}",
            extra={
                "request_id": error.request_id,
                "path": request.url.path,
                "method": request.method,
                "exception_type": type(exc).__name__,
                "stack_trace": traceback.format_exc()
            },
            exc_info=True
        )
        
        return await self.handle_application_error(request, error)
    
    async def _log_error(self, request: Request, error: ApplicationError):
        """Log error with context"""
        
        log_data = {
            "request_id": error.request_id,
            "error_code": error.error_code,
            "category": error.category.value,
            "severity": error.severity.value,
            "status_code": error.status_code,
            "path": request.url.path,
            "method": request.method,
            "user_agent": request.headers.get("user-agent"),
            "client_ip": self._get_client_ip(request)
        }
        
        # Add user context if available
        if hasattr(request.state, 'user'):
            log_data["user_id"] = getattr(request.state.user, 'id', None)
        
        # Log based on severity
        if error.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(error.message, extra=log_data)
        elif error.severity == ErrorSeverity.HIGH:
            self.logger.error(error.message, extra=log_data)
        elif error.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(error.message, extra=log_data)
        else:
            self.logger.info(error.message, extra=log_data)
    
    def _categorize_http_exception(self, status_code: int) -> ErrorCategory:
        """Categorize HTTP status codes"""
        if status_code == 401:
            return ErrorCategory.AUTHENTICATION
        elif status_code == 403:
            return ErrorCategory.AUTHORIZATION
        elif status_code == 404:
            return ErrorCategory.NOT_FOUND
        elif status_code == 422:
            return ErrorCategory.VALIDATION
        elif status_code == 429:
            return ErrorCategory.RATE_LIMIT
        elif 400 <= status_code < 500:
            return ErrorCategory.VALIDATION
        else:
            return ErrorCategory.SYSTEM
    
    def _determine_severity(self, status_code: int) -> ErrorSeverity:
        """Determine error severity from status code"""
        if status_code >= 500:
            return ErrorSeverity.CRITICAL
        elif status_code in [401, 403]:
            return ErrorSeverity.HIGH
        elif status_code == 429:
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.LOW
    
    def _get_user_friendly_message(self, status_code: int) -> str:
        """Get user-friendly message for status codes"""
        messages = {
            400: "İstek formatında hata bulundu.",
            401: "Giriş yapmanız gerekiyor.",
            403: "Bu işlem için yetkiniz bulunmuyor.",
            404: "Aranan kaynak bulunamadı.",
            409: "İşlem çakışması nedeniyle gerçekleştirilemedi.",
            422: "Girilen bilgilerde hata bulundu.",
            429: "Çok fazla istek gönderdiniz. Lütfen bekleyin.",
            500: "Sunucu hatası oluştu.",
            502: "Harici serviste sorun oluştu.",
            503: "Servis geçici olarak kullanılamıyor."
        }
        return messages.get(status_code, "Bir hata oluştu.")
    
    def _get_suggested_action(self, status_code: int) -> str:
        """Get suggested action for status codes"""
        actions = {
            400: "İstek formatını kontrol edip tekrar deneyin.",
            401: "Giriş yapın veya token'ınızı yenileyin.",
            403: "Yöneticinizle iletişime geçin.",
            404: "URL'yi kontrol edin veya başka bir kaynak deneyin.",
            409: "İşlem durumunu kontrol edip tekrar deneyin.",
            422: "Girilen bilgileri kontrol edip düzeltin.",
            429: "Birkaç dakika bekleyip tekrar deneyin.",
            500: "Sorun devam ederse destek ekibiyle iletişime geçin.",
            502: "Birkaç dakika sonra tekrar deneyin.",
            503: "Servis bakımı bitene kadar bekleyin."
        }
        return actions.get(status_code, "Tekrar deneyin veya destek ekibiyle iletişime geçin.")
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request"""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        return getattr(request.client, 'host', 'unknown')


# Global error handler
error_handler = ErrorHandler()


# FastAPI exception handlers
async def application_error_handler(request: Request, exc: ApplicationError):
    """Handler for ApplicationError exceptions"""
    return await error_handler.handle_application_error(request, exc)


async def http_exception_handler(request: Request, exc: HTTPException):
    """Handler for HTTPException"""
    return await error_handler.handle_http_exception(request, exc)


async def validation_exception_handler(request: Request, exc: Exception):
    """Handler for validation exceptions"""
    return await error_handler.handle_validation_exception(request, exc)


async def generic_exception_handler(request: Request, exc: Exception):
    """Handler for all other exceptions"""
    return await error_handler.handle_generic_exception(request, exc)
