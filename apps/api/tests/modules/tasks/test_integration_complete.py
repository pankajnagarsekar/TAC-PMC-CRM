"""Comprehensive integration tests for task module."""

import pytest
import asyncio
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.modules.tasks.application.task_service import TaskService
from app.modules.tasks.infrastructure.repository import TaskAISummaryRepository
from app.modules.tasks.infrastructure.cache_manager import TaskAISummaryCache
from app.modules.tasks.schemas.dto import TaskCreate, TaskUpdate
from app.modules.shared.domain.state_machine import StateMachine
from app.modules.shared.domain.exceptions import DataFreezeError, IllegalTransitionError
from app.db.mongodb import db_manager
from app.core.config import settings
from fastapi import HTTPException


@pytest.fixture
async def test_db():
    """Setup test database for each test."""
    settings.DB_NAME = "tac_pmc_test_integration"
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
async def test_concurrent_task_creation_with_unique_sr_no(test_db: AsyncIOMotorDatabase, auth_user):
    """Integration test: concurrent task creation maintains unique sr_no."""
    service = TaskService(test_db)
    project_id = "proj-concurrent-sr-no"

    async def create_task(desc):
        task_data = TaskCreate(
            project_id=project_id,
            task_description=desc,
            assigned_to_name="Test",
            priority="Normal"
        )
        return await service.create_task(auth_user, task_data)

    # Create 10 tasks concurrently
    tasks = [create_task(f"Task {i}") for i in range(10)]
    results = await asyncio.gather(*tasks)

    # Extract sr_no values and verify they're all unique and sequential
    sr_nos = sorted([t["sr_no"] for t in results])
    assert sr_nos == list(range(1, 11)), f"Expected [1..10], got {sr_nos}"


@pytest.mark.asyncio
async def test_task_lifecycle_with_state_machine_enforcement(test_db: AsyncIOMotorDatabase, auth_user):
    """Integration test: task lifecycle respects StateMachine transitions."""
    service = TaskService(test_db)
    project_id = "proj-lifecycle"

    # Create task
    task_data = TaskCreate(
        project_id=project_id,
        task_description="Lifecycle Test",
        assigned_to_name="Test",
        priority="Normal"
    )
    task = await service.create_task(auth_user, task_data)
    task_id = task["_id"]

    # Verify initial state is Open
    assert task["status"] == "Open"

    # Valid transition: Open -> In Progress
    task = await service.update_status(auth_user, task_id, "In Progress")
    assert task["status"] == "In Progress"

    # Valid transition: In Progress -> Completed
    task = await service.update_status(auth_user, task_id, "Completed")
    assert task["status"] == "Completed"

    # Valid transition: Completed -> Closed
    task = await service.update_status(auth_user, task_id, "Closed")
    assert task["status"] == "Closed"

    # Invalid transition: Closed is terminal
    with pytest.raises(HTTPException) as exc:
        await service.update_status(auth_user, task_id, "In Progress")
    assert exc.value.status_code == 400

    # Cannot modify frozen task
    with pytest.raises(HTTPException) as exc:
        await service.update_task_details(
            auth_user,
            task_id,
            TaskUpdate(task_description="Modified")
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_cache_invalidation_on_state_changes(test_db: AsyncIOMotorDatabase, auth_user):
    """Integration test: cache is properly invalidated on task state changes."""
    service = TaskService(test_db)
    summary_repo = TaskAISummaryRepository(test_db)
    project_id = "proj-cache-lifecycle"
    org_id = auth_user["organisation_id"]

    # Create a task
    task_data = TaskCreate(
        project_id=project_id,
        task_description="Cache Test Task",
        assigned_to_name="Test",
        priority="Normal"
    )
    task = await service.create_task(auth_user, task_data)
    task_id = task["_id"]

    # Insert a cached summary
    await summary_repo.create({
        "project_id": project_id,
        "organisation_id": org_id,
        "summary_text": "Cached",
        "metrics": {}
    })

    # Verify cache exists
    cached = await summary_repo.find_one({"project_id": project_id, "organisation_id": org_id})
    assert cached is not None

    # Update task status (should invalidate cache)
    await service.update_status(auth_user, task_id, "In Progress")

    # Verify cache is invalidated
    cached = await summary_repo.find_one({"project_id": project_id, "organisation_id": org_id})
    assert cached is None


@pytest.mark.asyncio
async def test_authorization_prevents_cross_org_access(test_db: AsyncIOMotorDatabase, auth_user):
    """Integration test: authorization checks prevent cross-org access."""
    service = TaskService(test_db)
    project_id = "proj-auth-test"

    # Create a task in org-1
    task_data = TaskCreate(
        project_id=project_id,
        task_description="Auth Test",
        assigned_to_name="Test",
        priority="Normal"
    )
    task = await service.create_task(auth_user, task_data)
    task_id = task["_id"]

    # Create user from different org
    other_org_user = {
        **auth_user,
        "organisation_id": "org-2"
    }

    # Attempt to get task from different org (should fail)
    with pytest.raises(HTTPException) as exc:
        await service.get_task(other_org_user, task_id)
    assert exc.value.status_code == 404  # org scoping returns 404

    # Attempt to update task from different org (should fail)
    with pytest.raises(HTTPException) as exc:
        await service.update_task_details(
            other_org_user,
            task_id,
            TaskUpdate(task_description="Modified")
        )
    assert exc.value.status_code == 404

    # Attempt to delete task from different org (should fail)
    with pytest.raises(HTTPException) as exc:
        await service.delete_task(other_org_user, task_id)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_task_operations_maintain_audit_trail(test_db: AsyncIOMotorDatabase, auth_user):
    """Integration test: task operations maintain audit trail."""
    service = TaskService(test_db)
    project_id = "proj-audit"

    # Create task
    task_data = TaskCreate(
        project_id=project_id,
        task_description="Audit Test",
        assigned_to_name="Test",
        priority="Normal"
    )
    task = await service.create_task(auth_user, task_data)
    task_id = task["_id"]

    # Verify audit log has CREATE entry
    assert len(task["audit_log"]) == 1
    assert task["audit_log"][0]["action"] == "CREATE"

    # Update status
    task = await service.update_status(auth_user, task_id, "In Progress")

    # Verify audit log has STATUS_CHANGE entry
    assert len(task["audit_log"]) == 2
    assert task["audit_log"][1]["action"] == "STATUS_CHANGE"

    # Update task details
    task = await service.update_task_details(
        auth_user,
        task_id,
        TaskUpdate(task_description="Updated")
    )

    # Verify audit log has UPDATE entry
    assert len(task["audit_log"]) == 3
    assert task["audit_log"][2]["action"] == "UPDATE"
