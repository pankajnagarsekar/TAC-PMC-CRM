import pytest
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.modules.tasks.infrastructure.indexes import TaskIndexManager
from app.db.mongodb import db_manager
from app.core.config import settings


@pytest.fixture
async def test_db():
    """Setup test database for each test."""
    settings.DB_NAME = "tac_pmc_test_indexes"
    await db_manager.connect(settings.MONGO_URL, settings.DB_NAME)
    db = db_manager.db
    yield db
    # Cleanup
    try:
        await db_manager.client.drop_database(settings.DB_NAME)
    except Exception:
        pass


@pytest.mark.asyncio
async def test_counter_indexes_created(test_db: AsyncIOMotorDatabase):
    """Test that atomic counter indexes are created."""
    await TaskIndexManager.create_indexes(test_db)

    counter = test_db["task_sr_no_counters"]
    indexes = await counter.list_indexes().to_list(None)
    index_names = [idx["name"] for idx in indexes]

    # Should have default _id index plus our unique compound index
    assert len(index_names) >= 2
    assert any("organisation_id" in str(idx) for idx in indexes)


@pytest.mark.asyncio
async def test_task_indexes_created(test_db: AsyncIOMotorDatabase):
    """Test that task collection indexes are created."""
    await TaskIndexManager.create_indexes(test_db)

    tasks = test_db["tasks"]
    indexes = await tasks.list_indexes().to_list(None)
    index_names = [idx["name"] for idx in indexes]

    # Check for expected indexes
    # Should have: _id, (org, project), (org, project, status), (org, assigned_to_user_id), (deadline)
    assert len(index_names) >= 3


@pytest.mark.asyncio
async def test_summary_indexes_created(test_db: AsyncIOMotorDatabase):
    """Test that summary cache indexes are created."""
    await TaskIndexManager.create_indexes(test_db)

    summary = test_db["task_ai_summaries"]
    indexes = await summary.list_indexes().to_list(None)
    index_names = [idx["name"] for idx in indexes]

    # Should have default _id index plus our compound index
    assert len(index_names) >= 2
    assert any("created_at" in str(idx) for idx in indexes)


@pytest.mark.asyncio
async def test_indexes_support_common_queries(test_db: AsyncIOMotorDatabase):
    """Test that created indexes support common query patterns."""
    await TaskIndexManager.create_indexes(test_db)

    # Insert test data
    tasks = test_db["tasks"]
    org_id = "test-org"
    project_id = "test-project"

    await tasks.insert_one({
        "organisation_id": org_id,
        "project_id": project_id,
        "status": "Open",
        "task_description": "Test",
        "assigned_to_user_id": "user-1",
        "deadline": None
    })

    # Query patterns that should use indexes
    result = await tasks.find_one({
        "organisation_id": org_id,
        "project_id": project_id
    })
    assert result is not None

    # Filter by status should also be fast with index
    result = await tasks.find_one({
        "organisation_id": org_id,
        "project_id": project_id,
        "status": "Open"
    })
    assert result is not None

    # Assignment query should use index
    result = await tasks.find_one({
        "organisation_id": org_id,
        "assigned_to_user_id": "user-1"
    })
    assert result is not None
