"""
Enterprise Production Logging Configuration
Structured logging with JSON format for centralized log management
"""
import json
import logging
import logging.config
import sys
from datetime import datetime
from typing import Dict, Any, Optional
class CustomJSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON"""
        log_record = {}
        
        # Add standard fields
        log_record['timestamp'] = datetime.utcnow().isoformat()
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        log_record['module'] = record.module
        log_record['function'] = record.funcName
        log_record['line'] = record.lineno
        log_record['message'] = record.getMessage()
        
        # Add application metadata
        log_record['application'] = 'ai-interview-api'
        log_record['version'] = '1.0.0'
        log_record['environment'] = 'production'  # From environment variable
        
        # Add correlation ID if available
        correlation_id = getattr(record, 'correlation_id', None)
        if correlation_id is not None:
            log_record['correlation_id'] = correlation_id
        
        # Add user context if available
        user_id = getattr(record, 'user_id', None)
        if user_id is not None:
            log_record['user_id'] = user_id
        
        # Add request context if available
        request_id = getattr(record, 'request_id', None)
        if request_id is not None:
            log_record['request_id'] = request_id
        
        endpoint = getattr(record, 'endpoint', None)
        if endpoint is not None:
            log_record['endpoint'] = endpoint
        
        method = getattr(record, 'method', None)
        if method is not None:
            log_record['method'] = method
        
        status_code = getattr(record, 'status_code', None)
        if status_code is not None:
            log_record['status_code'] = status_code
        
        # Add performance metrics if available
        duration_ms = getattr(record, 'duration_ms', None)
        if duration_ms is not None:
            log_record['duration_ms'] = duration_ms
        
        memory_usage = getattr(record, 'memory_usage', None)
        if memory_usage is not None:
            log_record['memory_usage'] = memory_usage
        
        # Add exception info if present
        if record.exc_info:
            log_record['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_record, default=str)


def setup_logging():
    """
    Setup production logging configuration
    """
    
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'json': {
                '()': CustomJSONFormatter,
                'format': '%(levelname)s %(name)s %(message)s'
            },
            'standard': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'WARNING',
                'formatter': 'json',
                'stream': sys.stdout
            },
            # File logging disabled for Docker development
            # In production, use external log aggregation (ELK, CloudWatch, etc.)
        },
        'loggers': {
            '': {  # Root logger
                'handlers': ['console'],
                'level': 'WARNING',
                'propagate': False
            },
            'security': {
                'handlers': ['console'],
                'level': 'WARNING',
                'propagate': False
            },
            'audit': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': False
            },
            'uvicorn': {
                'handlers': ['console'],
                'level': 'WARNING',
                'propagate': False
            },
            'sqlalchemy': {
                'handlers': ['console'],
                'level': 'WARNING',
                'propagate': False
            },
            'fastapi': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': False
            }
        }
    }
    
    logging.config.dictConfig(logging_config)


# Request logging middleware
class RequestLoggingMiddleware:
    """
    Middleware to log all HTTP requests with structured data
    """
    
    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger('api.requests')
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        import time
        import uuid
        
        # Generate request ID
        request_id = str(uuid.uuid4())
        
        # Capture request start time
        start_time = time.time()
        
        # Extract request information
        method = scope.get("method", "")
        path = scope.get("path", "")
        query_string = scope.get("query_string", b"").decode()
        
        # Get client IP
        client_ip = "unknown"
        for header_name, header_value in scope.get("headers", []):
            if header_name == b"x-forwarded-for":
                client_ip = header_value.decode().split(",")[0].strip()
                break
            elif header_name == b"x-real-ip":
                client_ip = header_value.decode()
                break
        
        if client_ip == "unknown" and scope.get("client"):
            client_ip = scope["client"][0]
        
        # Log request start
        self.logger.info(
            "HTTP request started",
            extra={
                'request_id': request_id,
                'method': method,
                'path': path,
                'query_string': query_string,
                'client_ip': client_ip,
                'user_agent': self._get_user_agent(scope)
            }
        )
        
        # Wrap send to capture response
        async def send_wrapper(message):
            nonlocal start_time
            
            if message["type"] == "http.response.start":
                status_code = message["status"]
                duration_ms = round((time.time() - start_time) * 1000, 2)
                
                # Log request completion
                log_level = logging.INFO
                if status_code >= 500:
                    log_level = logging.ERROR
                elif status_code >= 400:
                    log_level = logging.WARNING
                
                self.logger.log(
                    log_level,
                    "HTTP request completed",
                    extra={
                        'request_id': request_id,
                        'method': method,
                        'path': path,
                        'status_code': status_code,
                        'duration_ms': duration_ms,
                        'client_ip': client_ip
                    }
                )
            
            await send(message)
        
        await self.app(scope, receive, send_wrapper)
    
    def _get_user_agent(self, scope):
        """Extract user agent from headers"""
        for header_name, header_value in scope.get("headers", []):
            if header_name == b"user-agent":
                return header_value.decode()
        return "unknown"


# Performance monitoring
class PerformanceLogger:
    """
    Log performance metrics for monitoring
    """
    
    def __init__(self):
        self.logger = logging.getLogger('performance')
    
    def log_database_query(self, query: str, duration_ms: float, result_count: Optional[int] = None):
        """Log database query performance"""
        self.logger.info(
            "Database query executed",
            extra={
                'query_type': 'database',
                'duration_ms': duration_ms,
                'result_count': result_count,
                'query': query[:200] + '...' if len(query) > 200 else query
            }
        )
    
    def log_external_api_call(self, service: str, endpoint: str, duration_ms: float, status_code: int):
        """Log external API call performance"""
        self.logger.info(
            "External API call completed",
            extra={
                'service': service,
                'endpoint': endpoint,
                'duration_ms': duration_ms,
                'status_code': status_code,
                'call_type': 'external_api'
            }
        )
    
    def log_ai_processing(self, provider: str, model: str, tokens_used: int, duration_ms: float):
        """Log AI processing performance"""
        self.logger.info(
            "AI processing completed",
            extra={
                'provider': provider,
                'model': model,
                'tokens_used': tokens_used,
                'duration_ms': duration_ms,
                'processing_type': 'ai'
            }
        )


# Error tracking
class ErrorTracker:
    """
    Enhanced error tracking and reporting
    """
    
    def __init__(self):
        self.logger = logging.getLogger('errors')
    
    def log_exception(
        self,
        exception: Exception,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
        request_id: Optional[str] = None
    ):
        """Log exception with full context"""
        import traceback
        
        error_context = {
            'exception_type': type(exception).__name__,
            'exception_message': str(exception),
            'stack_trace': traceback.format_exc(),
            'user_id': user_id,
            'request_id': request_id
        }
        
        if context:
            error_context.update(context)
        
        self.logger.error(
            "Exception occurred",
            extra=error_context
        )
    
    def log_validation_error(self, field: str, value: Any, error_message: str):
        """Log validation errors"""
        self.logger.warning(
            "Validation error",
            extra={
                'error_type': 'validation',
                'field': field,
                'value': str(value)[:100],  # Truncate long values
                'error_message': error_message
            }
        )
    
    def log_business_logic_error(self, operation: str, details: Dict[str, Any]):
        """Log business logic errors"""
        self.logger.error(
            "Business logic error",
            extra={
                'error_type': 'business_logic',
                'operation': operation,
                **details
            }
        )


# Global instances
performance_logger = PerformanceLogger()
error_tracker = ErrorTracker()


# Logging decorators
def log_performance(operation_name: str):
    """Decorator to log function performance"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            import time
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                duration_ms = round((time.time() - start_time) * 1000, 2)
                
                performance_logger.logger.info(
                    f"Operation completed: {operation_name}",
                    extra={
                        'operation': operation_name,
                        'duration_ms': duration_ms,
                        'success': True
                    }
                )
                
                return result
            
            except Exception as e:
                duration_ms = round((time.time() - start_time) * 1000, 2)
                
                performance_logger.logger.error(
                    f"Operation failed: {operation_name}",
                    extra={
                        'operation': operation_name,
                        'duration_ms': duration_ms,
                        'success': False,
                        'error': str(e)
                    }
                )
                
                raise
        
        def sync_wrapper(*args, **kwargs):
            import time
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration_ms = round((time.time() - start_time) * 1000, 2)
                
                performance_logger.logger.info(
                    f"Operation completed: {operation_name}",
                    extra={
                        'operation': operation_name,
                        'duration_ms': duration_ms,
                        'success': True
                    }
                )
                
                return result
            
            except Exception as e:
                duration_ms = round((time.time() - start_time) * 1000, 2)
                
                performance_logger.logger.error(
                    f"Operation failed: {operation_name}",
                    extra={
                        'operation': operation_name,
                        'duration_ms': duration_ms,
                        'success': False,
                        'error': str(e)
                    }
                )
                
                raise
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def setup_production_logging():
    """
    Complete production logging setup
    """
    # Setup basic logging configuration
    setup_logging()
    
    # Log directories not needed for Docker development
    # In production, use external log management
    
    # Log startup
    logger = logging.getLogger('startup')
    logger.info(
        "Application logging initialized",
        extra={
            'event': 'logging_initialized',
            'log_level': 'INFO',
            'log_format': 'JSON'
        }
    )
