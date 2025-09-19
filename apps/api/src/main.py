from fastapi import FastAPI, Request
import sys, os as _os
sys.path.append(str(_os.path.dirname(__file__)))
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
import json

from src.api.v1.routes import router as api_v1_router
from src.core.metrics import collector
try:
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, CollectorRegistry  # type: ignore
except Exception:  # pragma: no cover
    generate_latest = None  # type: ignore
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"  # type: ignore
    CollectorRegistry = None  # type: ignore
from src.core.config import settings
from src.core.s3 import upsert_lifecycle_rule
from src.core.security import SecurityHeaders, EnterpriseRateLimiter
from src.core.error_handling import (
    ApplicationError, application_error_handler, http_exception_handler,
    validation_exception_handler, generic_exception_handler
)
from src.core.logging_config import setup_production_logging, RequestLoggingMiddleware
from urllib.parse import urlparse
from src.core.monitoring import setup_opentelemetry, instrument_frameworks, setup_sentry
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

# Exception handlers (enable in all envs; handlers are safe)
app.add_exception_handler(ApplicationError, application_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(ValidationError, validation_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(Exception, generic_exception_handler)  # type: ignore[arg-type]

# CORS – dynamic origins (local + configured)
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost",
    "http://127.0.0.1",
]
ext = (settings.web_external_base_url or "").strip()
if ext:
    try:
        origins.append(ext)
        # Also include scheme-less host alternatives if useful
        parsed = urlparse(ext)
        if parsed.netloc:
            host_only = f"https://{parsed.netloc}"
            if host_only not in origins:
                origins.append(host_only)
    except Exception:
        pass
# Append any configured CORS origins from settings
try:
    for o in settings.cors_allowed_origins:
        if o not in origins:
            origins.append(o)
except Exception:
    pass

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

# Setup OpenTelemetry (no-op if not configured)
setup_opentelemetry()
try:
    setup_sentry()
except Exception:
    pass

# Add enterprise security middleware
app.add_middleware(SecurityHeaders)
# Calibrated defaults. Endpoint-specific stricter limits are configured in middleware
app.add_middleware(EnterpriseRateLimiter, default_limit=600, default_window=60)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Rely on CORSMiddleware for preflight handling; explicit OPTIONS handler removed

# SlowAPI limiter removed; EnterpriseRateLimiter middleware will enforce limits centrally


@app.get("/healthz", tags=["health"])
def healthcheck():
    return {"status": "ok", **collector.snapshot()}


@app.get("/metrics", tags=["health"])
def metrics_prometheus():
    # Expose Prometheus endpoint if library available; fallback to JSON snapshot
    if generate_latest and CollectorRegistry:
        registry = CollectorRegistry()
        data = generate_latest(registry)
        return Response(content=data, media_type=CONTENT_TYPE_LATEST)
    return Response(content=json.dumps(collector.snapshot()), media_type="application/json")


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

# Instrument frameworks after app fully configured
try:
    instrument_frameworks(app)
except Exception:
    pass