"""
Test CORS configuration for work order API endpoint.
Verifies that HTTPS origins are properly allowed.
"""

import pytest
from fastapi.testclient import TestClient
from server import app

client = TestClient(app)


def test_cors_headers_for_https_localhost():
    """Test that HTTPS localhost origins are allowed."""
    response = client.options(
        "/api/work-orders",
        headers={
            "Origin": "https://localhost:3000",
            "Access-Control-Request-Method": "PUT",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    # Check that CORS headers are present
    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] == "https://localhost:3000"
    assert "access-control-allow-methods" in response.headers
    assert "PUT" in response.headers["access-control-allow-methods"]


def test_cors_headers_for_https_127():
    """Test that HTTPS 127.0.0.1 origins are allowed."""
    response = client.options(
        "/api/work-orders",
        headers={
            "Origin": "https://127.0.0.1:3000",
            "Access-Control-Request-Method": "PUT",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] == "https://127.0.0.1:3000"


def test_cors_headers_for_http_localhost():
    """Test that HTTP localhost origins still work (backward compatibility)."""
    response = client.options(
        "/api/work-orders",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "PUT",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
