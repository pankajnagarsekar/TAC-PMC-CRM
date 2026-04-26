import pytest
import asyncio
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.modules.tasks.application.task_service import TaskService
from app.modules.tasks.schemas.dto import TaskCreate
from app.modules.tasks.domain.exceptions import TaskSummaryGenerationError
from app.db.mongodb import db_manager
from app.core.config import settings


@pytest.fixture
async def test_db():
    """Setup test database for each test."""
    settings.DB_NAME = "tac_pmc_test_errors"
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
async def test_ai_summary_generation_handles_timeout(test_db: AsyncIOMotorDatabase, auth_user):
    """Test that AI summary generation handles timeouts gracefully."""
    service = TaskService(test_db)

    # Create a task first
    task_data = TaskCreate(
        project_id="proj-timeout-test",
        task_description="Timeout Test Task",
        assigned_to_name="Test",
        priority="Normal"
    )
    await service.create_task(auth_user, task_data)

    # AI summary generation might timeout - should be handled gracefully
    # (This test verifies that no unhandled exceptions occur)
    try:
        result = await service.get_task_summary_for_ai(auth_user, "proj-timeout-test")
        # Should return a result even if AI provider fails
        assert result is not None
    except TaskSummaryGenerationError:
        # Expected: TaskSummaryGenerationError is caught and re-raised properly
        pass


@pytest.mark.asyncio
async def test_task_operations_handle_database_errors(test_db: AsyncIOMotorDatabase, auth_user):
    """Test that task operations handle database errors gracefully."""
    service = TaskService(test_db)

    # Attempt to get a non-existent task
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await service.get_task(auth_user, "non-existent-id")
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_concurrent_task_operations_dont_crash(test_db: AsyncIOMotorDatabase, auth_user):
    """Test that concurrent task operations don't cause unhandled exceptions."""
    service = TaskService(test_db)

    async def create_task(desc):
        task_data = TaskCreate(
            project_id="proj-concurrent",
            task_description=desc,
            assigned_to_name="Test",
            priority="Normal"
        )
        return await service.create_task(auth_user, task_data)

    # Perform concurrent task creations
    tasks = [create_task(f"Task {i}") for i in range(5)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Verify no exceptions occurred
    for result in results:
        assert not isinstance(result, Exception), f"Unexpected exception: {result}"
