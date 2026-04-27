import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from unittest.mock import MagicMock


@pytest.mark.asyncio
async def test_global_exception_handler(test_db):
    """BUG-10: Verify unhandled exception returns JSON."""
    from app.core.dependencies import get_payment_service, get_authenticated_user

    mock_service = MagicMock()
    mock_service.get_payment_certificate.side_effect = Exception("Surprise Failure")

    app.dependency_overrides[get_payment_service] = lambda: mock_service
    app.dependency_overrides[get_authenticated_user] = lambda: {"user_id": "test_user"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/payments/id/anyid")

    assert response.status_code == 500
    data = response.json()
    assert data["success"] is False
    assert "error" in data
    assert data["error"]["code"] == "SYSTEM_FAULT"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_mongodb_health_check():
    """BUG-06: Verify health check endpoint."""
    from unittest.mock import AsyncMock, patch

    # Mock the health check to return True regardless of lifecycle
    with patch("app.core.lifecycle.BackgroundGuardian.mongodb_health_check", new_callable=AsyncMock) as mock_health:
        mock_health.return_value = True
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/system/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["db"] == "connected"


@pytest.mark.asyncio
async def test_dpr_validation_empty_notes(test_db):
    """BUG-09: Verify DPR progress_notes validation."""
    from app.core.dependencies import get_authenticated_user
    app.dependency_overrides[get_authenticated_user] = lambda: {"user_id": "test_user"}

    payload = {
        "project_id": "507f1f77bcf86cd799439011",
        "progress_notes": ""  # Should fail
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/v1/dprs/", json=payload)
    assert response.status_code == 422
    assert "progress_notes" in str(response.json())

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_backpressure_middleware():
    """BUG-02: Verify backpressure rejection."""
    from app.core.middleware import BackpressureMiddleware
    # Manually set the semaphore to 0 available units
    sem = BackpressureMiddleware.get_semaphore()

    # Exhaust the semaphore
    for _ in range(BackpressureMiddleware.MAX_CONCURRENT):
        await sem.acquire()

    try:
        print("DEBUG: Test - calling API while saturated")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/system/health")

        print(f"DEBUG: Test - response status: {response.status_code}")
        assert response.status_code == 503
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "BACKPRESSURE_REJECTION"
    finally:
        # Release all
        for _ in range(BackpressureMiddleware.MAX_CONCURRENT):
            sem.release()
