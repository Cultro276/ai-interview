from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from src.api.v1.routes import router as api_v1_router
from src.core.metrics import collector
from src.core.config import settings
from src.core.s3 import upsert_lifecycle_rule
from src.core.security import SecurityHeaders, EnterpriseRateLimiter
from src.core.error_handling import (
    ApplicationError, application_error_handler, http_exception_handler,
    validation_exception_handler, generic_exception_handler
)
from src.core.logging_config import setup_production_logging, RequestLoggingMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.responses import PlainTextResponse
import os

app = FastAPI(
    title="Interview API",
    version="1.0.0",
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
)

# Setup enterprise error handlers
from fastapi import HTTPException
from pydantic import ValidationError

# Exception handlers will be added after FastAPI is fully configured
# app.add_exception_handler(ApplicationError, application_error_handler)
# app.add_exception_handler(HTTPException, http_exception_handler)
# app.add_exception_handler(ValidationError, validation_exception_handler)
# app.add_exception_handler(Exception, generic_exception_handler)

# CORS – local dev origins
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost",
    "http://127.0.0.1",
]

# Add CORS middleware early to handle preflight requests
# This must be added before any other middleware to handle OPTIONS requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*", "Authorization", "Content-Type"],
    expose_headers=["*"],
    max_age=86400,
)

# Setup production logging
setup_production_logging()

# Add enterprise security middleware
app.add_middleware(SecurityHeaders)
app.add_middleware(EnterpriseRateLimiter, default_limit=1000, default_window=3600)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Add explicit CORS preflight handler for all paths
@app.options("/{full_path:path}")
async def options_handler(request: Request, full_path: str):
    """Handle CORS preflight requests before authentication"""
    # Get the origin from the request headers
    origin = request.headers.get("origin", "*")
    
    # Check if origin is in our allowed list
    allowed_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost",
        "http://127.0.0.1",
    ]
    
    if origin in allowed_origins:
        return Response(
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Max-Age": "86400",
            }
        )
    else:
        return Response(
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Max-Age": "86400",
            }
        )

# Basic rate limiter (IP-based). For production, prefer Redis storage.
storage_uri = os.getenv("REDIS_URL") or "memory://"
limiter = Limiter(key_func=get_remote_address, default_limits=["1000/minute"], storage_uri=storage_uri)  # increased for development
app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
def _rate_limit_handler(request, exc):  # type: ignore[no-redef]
    return PlainTextResponse("Too Many Requests", status_code=429)


@app.get("/healthz", tags=["health"])
def healthcheck():
    return {"status": "ok", **collector.snapshot()}


# Remove dev-upload stub; real S3 is used in production


# Versioned API
app.include_router(api_v1_router, prefix="/api/v1") 


# Apply S3 lifecycle TTL rules at startup (best-effort, dev-safe)
try:
    if settings.s3_bucket:
        # Media (candidate uploads) and CVs
        upsert_lifecycle_rule("media/", settings.retention_media_days)
        upsert_lifecycle_rule("cvs/", settings.retention_media_days)
        # Generated TTS cache
        upsert_lifecycle_rule("tts/", settings.retention_media_days)
except Exception:
    # Do not crash app if IAM lacks permissions or S3 not configured
    pass