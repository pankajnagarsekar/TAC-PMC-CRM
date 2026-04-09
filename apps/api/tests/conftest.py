import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.mongodb import db_manager
from app.core.config import settings
from app.core.dependencies import get_authenticated_user, verify_nonce

@pytest.fixture
async def client():
    # Use test database
    settings.DB_NAME = "tac_pmc_test_db"
    await db_manager.connect(settings.MONGO_URL, settings.DB_NAME)
    
    # Mock authentication
    async def mock_get_authenticated_user():
        return {"user_id": "test-user-id", "organisation_id": "test-org-123", "role": "Admin", "active_status": True}
    
    async def mock_verify_nonce():
        return "test-nonce"

    app.dependency_overrides[get_authenticated_user] = mock_get_authenticated_user
    app.dependency_overrides[verify_nonce] = mock_verify_nonce

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    
    # Cleanup
    app.dependency_overrides = {}
    if db_manager.client:
        try:
            await db_manager.client.drop_database(settings.DB_NAME)
        except Exception:
            pass
    db_manager.close()

@pytest.fixture
def admin_token():
    # In a real scenario, this would generate a valid JWT
    # For integration tests, we might mock the auth dependency or use a static test token if the app supports it
    return "test-admin-token-supreme-2026"

@pytest.fixture
def test_org_id():
    return "test-org-123"

@pytest.fixture
def test_project_id():
    return "test-proj-456"


@pytest.fixture
async def test_db():
    """Async fixture providing test MongoDB database."""
    settings.DB_NAME = "tac_pmc_test_db"
    await db_manager.connect(settings.MONGO_URL, settings.DB_NAME)

    db = db_manager.db

    yield db

    # Cleanup after test
    if db_manager.client:
        try:
            await db_manager.client.drop_database(settings.DB_NAME)
        except Exception:
            pass


@pytest.fixture
async def baseline_manager(test_db):
    """Async fixture providing BaselineManager with test database."""
    from app.modules.scheduler.baseline_manager import BaselineManager
    return BaselineManager(test_db)
