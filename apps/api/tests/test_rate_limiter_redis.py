import os
import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.mark.skipif(not os.getenv("REDIS_URL"), reason="REDIS_URL not configured")
def test_rate_limiter_present_and_non_blocking_on_public_endpoint() -> None:
    # Public health endpoint should not be blocked by the limiter
    tc = TestClient(app)
    for _ in range(0, 5):
        r = tc.get("/healthz")
        assert r.status_code == 200


def test_login_endpoint_has_rate_limit_headers() -> None:
    # Even when not backed by Redis, middleware should inject headers
    tc = TestClient(app)
    r = tc.post("/api/v1/auth/login", data={"username": "x", "password": "y"})
    # We expect presence of rate limit headers from middleware
    assert "X-RateLimit-Limit" in r.headers
    assert "X-RateLimit-Window" in r.headers


