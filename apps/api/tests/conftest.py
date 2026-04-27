import pytest
from app.main import app
from app.db.mongodb import db_manager
from app.core.config import settings
from app.core.dependencies import get_authenticated_user, verify_nonce
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def client(request):
    import uuid
    # Use unique DB name per test to avoid concurrent drop conflicts
    client_db_name = f"tac_pmc_client_{uuid.uuid4().hex[:8]}"
    settings.DB_NAME = client_db_name
    await db_manager.connect(settings.MONGO_URL, client_db_name)

    # Mock authentication
    async def mock_get_authenticated_user():
        return {"user_id": "test-user-id", "organisation_id": "test-org-123", "role": "Admin", "active_status": True}

    async def mock_verify_nonce():
        return "test-nonce"

    app.dependency_overrides[get_authenticated_user] = mock_get_authenticated_user
    app.dependency_overrides[verify_nonce] = mock_verify_nonce

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=True) as ac:
        yield ac

    # Cleanup
    app.dependency_overrides = {}
    if db_manager.client:
        try:
            await db_manager.client.drop_database(client_db_name)
        except Exception:
            pass
    db_manager.close()


@pytest.fixture
def admin_token():
    return "test-admin-token-supreme-2026"


@pytest.fixture
def supervisor_token():
    return "test-supervisor-token-2026"


@pytest.fixture
def test_project():
    return {
        "id": "test-proj-456",
        "project_id": "test-proj-456",
        "project_name": "Test Site Ops Project",
        "organisation_id": "test-org-123"
    }


@pytest.fixture
def test_org_id():
    return "test-org-123"


@pytest.fixture
def test_project_id():
    return "test-proj-456"


@pytest.fixture
async def test_db(request):
    """Async fixture providing test MongoDB database with unique name per test."""
    import uuid
    # Use unique DB name per test to avoid concurrent drop conflicts
    test_db_name = f"tac_pmc_test_{uuid.uuid4().hex[:8]}"
    settings.DB_NAME = test_db_name
    await db_manager.connect(settings.MONGO_URL, test_db_name)

    db = db_manager.db

    yield db

    # Cleanup after test - drop unique test database
    if db_manager.client:
        try:
            await db_manager.client.drop_database(test_db_name)
        except Exception:
            pass


@pytest.fixture
async def baseline_manager(test_db):
    """Async fixture providing BaselineManager with test database."""
    from app.modules.scheduler.baseline_manager import BaselineManager
    return BaselineManager(test_db)


@pytest.fixture
def test_user():
    """Test user fixture."""
    return {
        "user_id": "test-user-id",
        "organisation_id": "test-org-123",
        "role": "Admin",
        "active_status": True,
    }
