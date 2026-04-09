import pytest
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.modules.tasks.application.task_service import TaskService
from app.modules.tasks.schemas.dto import TaskCreate, TaskUpdate
from app.db.mongodb import db_manager
from app.core.config import settings


@pytest.fixture
async def test_db():
    """Setup test database for each test."""
    settings.DB_NAME = "tac_pmc_test_auth"
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
    """Sample authenticated user from org-1."""
    return {
        "user_id": "user-123",
        "organisation_id": "org-1",
        "full_name": "Test User",
        "role": "Admin"
    }


@pytest.fixture
async def sample_task(test_db: AsyncIOMotorDatabase, auth_user):
    """Create a sample task for testing."""
    service = TaskService(test_db)
    task_data = TaskCreate(
        project_id="proj-1",
        task_description="Test Task",
        assigned_to_name="Test Assignee",
        priority="Normal"
    )
    return await service.create_task(auth_user, task_data)


@pytest.mark.asyncio
async def test_update_task_requires_org_access(test_db: AsyncIOMotorDatabase, auth_user, sample_task):
    """Test that task update raises 404 when user is from different org (org scoping)."""
    service = TaskService(test_db)
    task_id = sample_task.get("_id") or sample_task.get("id")

    # Create a user from a different organization
    user_different_org = {
        **auth_user,
        "organisation_id": "org-2"
    }

    # The repository uses org scoping in get_by_id, so different org users get 404
    # This is the secure pattern: org-scoped queries return 404 for unauthorized access
    with pytest.raises(HTTPException) as exc_info:
        await service.update_task_details(
            user_different_org,
            task_id,
            TaskUpdate(task_description="Modified")
        )
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_task_requires_org_access(test_db: AsyncIOMotorDatabase, auth_user, sample_task):
    """Test that task deletion raises 404 when user is from different org (org scoping)."""
    service = TaskService(test_db)
    task_id = sample_task.get("_id") or sample_task.get("id")

    # Create a user from a different organization
    user_different_org = {
        **auth_user,
        "organisation_id": "org-2"
    }

    # The repository uses org scoping in get_by_id, so different org users get 404
    with pytest.raises(HTTPException) as exc_info:
        await service.delete_task(user_different_org, task_id)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_update_status_requires_org_access(test_db: AsyncIOMotorDatabase, auth_user, sample_task):
    """Test that status update raises 404 when user is from different org (org scoping)."""
    service = TaskService(test_db)
    task_id = sample_task.get("_id") or sample_task.get("id")

    # Create a user from a different organization
    user_different_org = {
        **auth_user,
        "organisation_id": "org-2"
    }

    # The repository uses org scoping in get_by_id, so different org users get 404
    with pytest.raises(HTTPException) as exc_info:
        await service.update_status(user_different_org, task_id, "In Progress")
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_authorized_user_can_update_task(test_db: AsyncIOMotorDatabase, auth_user, sample_task):
    """Test that authorized user can update their own organization's task."""
    service = TaskService(test_db)
    task_id = sample_task.get("_id") or sample_task.get("id")

    # Update with same org should succeed
    result = await service.update_task_details(
        auth_user,
        task_id,
        TaskUpdate(task_description="New Description")
    )
    assert result["task_description"] == "New Description"
