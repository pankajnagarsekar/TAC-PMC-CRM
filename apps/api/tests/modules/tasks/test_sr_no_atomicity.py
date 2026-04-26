import pytest
import asyncio
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorClient
from app.modules.tasks.infrastructure.repository import TaskRepository
from app.db.mongodb import db_manager
from app.core.config import settings


@pytest.fixture
async def test_db():
    """Setup test database for each test."""
    settings.DB_NAME = "tac_pmc_test_sr_no"
    await db_manager.connect(settings.MONGO_URL, settings.DB_NAME)
    db = db_manager.db
    yield db
    # Cleanup
    try:
        await db_manager.client.drop_database(settings.DB_NAME)
    except Exception:
        pass


@pytest.mark.asyncio
async def test_sr_no_counter_increments_atomically(test_db: AsyncIOMotorDatabase):
    """Test that sr_no counter increments atomically without race conditions."""
    repo = TaskRepository(test_db)
    org_id = "test-org-123"
    project_id = "test-project-456"

    async def create_and_get_sr_no():
        sr_no = await repo.get_next_sr_no(org_id, project_id)
        return sr_no

    # Simulate concurrent creation requests
    results = await asyncio.gather(*[create_and_get_sr_no() for _ in range(5)])

    # All sr_no values should be unique and sequential
    assert sorted(results) == [1, 2, 3, 4, 5], f"Got non-sequential sr_no: {sorted(results)}"


@pytest.mark.asyncio
async def test_sr_no_counter_persists_across_calls(test_db: AsyncIOMotorDatabase):
    """Test that sr_no counter persists across multiple calls."""
    repo = TaskRepository(test_db)
    org_id = "test-org-123"
    project_id_1 = "project-1"
    project_id_2 = "project-2"

    # Different projects should have independent counters
    sr_no_1 = await repo.get_next_sr_no(org_id, project_id_1)
    assert sr_no_1 == 1

    sr_no_2 = await repo.get_next_sr_no(org_id, project_id_2)
    assert sr_no_2 == 1

    # Subsequent call to first project should increment
    sr_no_1_next = await repo.get_next_sr_no(org_id, project_id_1)
    assert sr_no_1_next == 2


@pytest.mark.asyncio
async def test_sr_no_counter_isolated_by_org_and_project(test_db: AsyncIOMotorDatabase):
    """Test that sr_no counter is isolated by both organization and project."""
    repo = TaskRepository(test_db)
    org_id_1 = "org-1"
    org_id_2 = "org-2"
    project_id = "same-project"

    # Different orgs should have independent counters
    sr_no_org1 = await repo.get_next_sr_no(org_id_1, project_id)
    sr_no_org2 = await repo.get_next_sr_no(org_id_2, project_id)

    assert sr_no_org1 == 1
    assert sr_no_org2 == 1
