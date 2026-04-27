import pytest
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.modules.tasks.application.task_service import TaskService
from app.modules.tasks.infrastructure.repository import TaskAISummaryRepository
from app.modules.tasks.infrastructure.cache_manager import TaskAISummaryCache
from app.modules.tasks.schemas.dto import TaskCreate, TaskUpdate
from app.db.mongodb import db_manager
from app.core.config import settings


@pytest.fixture
async def test_db():
    """Setup test database for each test."""
    settings.DB_NAME = "tac_pmc_test_cache"
    await db_manager.connect(settings.MONGO_URL, settings.DB_NAME)
    db = db_manager.db
    yield db
    # Cleanup
    try:
        await db_manager.client.drop_database(settings.DB_NAME)
    except Exception:
        pass


@pytest.fixture
def auth_user():
    """Sample authenticated user."""
    return {
        "user_id": "user-123",
        "organisation_id": "org-1",
        "full_name": "Test User",
        "role": "Admin"
    }


@pytest.mark.asyncio
async def test_cache_invalidated_on_task_creation(test_db: AsyncIOMotorDatabase, auth_user):
    """Test that cache is invalidated when a task is created."""
    service = TaskService(test_db)
    summary_repo = TaskAISummaryRepository(test_db)
    org_id = auth_user["organisation_id"]
    project_id = "proj-cache-test"

    # Insert a stale cached summary
    await summary_repo.create({
        "project_id": project_id,
        "organisation_id": org_id,
        "summary_text": "Stale summary",
        "metrics": {"total": 10}
    })

    # Verify cache exists
    cached = await summary_repo.find_one({
        "project_id": project_id,
        "organisation_id": org_id
    })
    assert cached is not None

    # Create a new task (should invalidate cache)
    task_data = TaskCreate(
        project_id=project_id,
        task_description="New Task",
        assigned_to_name="Assignee",
        priority="Normal"
    )
    await service.create_task(auth_user, task_data)

    # Invalidate cache (this is called by service on task creation)
    await TaskAISummaryCache.invalidate_for_project(test_db, org_id, project_id)

    # Verify cache is invalidated
    cached = await summary_repo.find_one({
        "project_id": project_id,
        "organisation_id": org_id
    })
    assert cached is None


@pytest.mark.asyncio
async def test_cache_invalidated_on_task_update(test_db: AsyncIOMotorDatabase, auth_user):
    """Test that cache is invalidated when a task is updated."""
    service = TaskService(test_db)
    summary_repo = TaskAISummaryRepository(test_db)
    org_id = auth_user["organisation_id"]
    project_id = "proj-cache-update-test"

    # Create a task
    task_data = TaskCreate(
        project_id=project_id,
        task_description="Test Task",
        assigned_to_name="Assignee",
        priority="Normal"
    )
    task = await service.create_task(auth_user, task_data)
    task_id = task.get("_id") or task.get("id")

    # Insert a cached summary
    await summary_repo.create({
        "project_id": project_id,
        "organisation_id": org_id,
        "summary_text": "Cached summary",
        "metrics": {"total": 1}
    })

    # Verify cache exists
    cached = await summary_repo.find_one({
        "project_id": project_id,
        "organisation_id": org_id
    })
    assert cached is not None

    # Update the task (should invalidate cache)
    await service.update_task_details(
        auth_user,
        task_id,
        TaskUpdate(task_description="Updated Description")
    )

    # Invalidate cache
    await TaskAISummaryCache.invalidate_for_project(test_db, org_id, project_id)

    # Verify cache is invalidated
    cached = await summary_repo.find_one({
        "project_id": project_id,
        "organisation_id": org_id
    })
    assert cached is None


@pytest.mark.asyncio
async def test_cache_invalidation_isolated_by_project(test_db: AsyncIOMotorDatabase, auth_user):
    """Test that cache invalidation is isolated per project."""
    TaskService(test_db)
    summary_repo = TaskAISummaryRepository(test_db)
    org_id = auth_user["organisation_id"]
    project_1 = "proj-1"
    project_2 = "proj-2"

    # Insert cached summaries for both projects
    await summary_repo.create({
        "project_id": project_1,
        "organisation_id": org_id,
        "summary_text": "Summary 1",
        "metrics": {}
    })
    await summary_repo.create({
        "project_id": project_2,
        "organisation_id": org_id,
        "summary_text": "Summary 2",
        "metrics": {}
    })

    # Invalidate cache for project 1 only
    await TaskAISummaryCache.invalidate_for_project(test_db, org_id, project_1)

    # Verify cache for project 1 is gone
    cached_1 = await summary_repo.find_one({
        "project_id": project_1,
        "organisation_id": org_id
    })
    assert cached_1 is None

    # Verify cache for project 2 still exists
    cached_2 = await summary_repo.find_one({
        "project_id": project_2,
        "organisation_id": org_id
    })
    assert cached_2 is not None
