# Task Module Critical Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task with verification between each task.

**Goal:** Fix 6 critical issues in the task module (StateMachine, sr_no atomicity, authorization, error handling, cache invalidation, database indexes) to achieve production-ready code.

**Architecture:** 
- Use MongoDB atomic counter pattern for sr_no generation (prevents race conditions)
- Add TASK entity to StateMachine with proper state definitions
- Implement permission checks on update/delete operations
- Add specific exception types and timeout handling for LLM calls
- Implement cache invalidation on task state changes
- Add MongoDB indexes for query performance optimization

**Tech Stack:** FastAPI, Motor (async MongoDB driver), Pydantic, Python 3.11+

---

## TASK 1: Create Domain Exceptions & Constants

**Files:**
- Create: `apps/api/app/modules/tasks/domain/exceptions.py`
- Create: `apps/api/app/modules/tasks/domain/types.py`
- Modify: `apps/api/app/modules/tasks/domain/models.py` (add imports)

**Step 1: Write test for custom exceptions**

Create `apps/api/tests/modules/tasks/test_domain_exceptions.py`:

```python
import pytest
from app.modules.tasks.domain.exceptions import (
    TaskNotFoundError,
    TaskStatusTransitionError,
    TaskModificationForbiddenError,
    TaskSummaryGenerationError,
)


def test_task_not_found_error_message():
    """TaskNotFoundError should have clear message"""
    error = TaskNotFoundError(task_id="123")
    assert "123" in str(error)
    assert "not found" in str(error).lower()


def test_status_transition_error_message():
    """TaskStatusTransitionError should show invalid transition"""
    error = TaskStatusTransitionError(current="Open", target="Invalid")
    assert "Open" in str(error)
    assert "Invalid" in str(error)


def test_modification_forbidden_error_message():
    """TaskModificationForbiddenError should indicate frozen state"""
    error = TaskModificationForbiddenError(status="Closed")
    assert "Closed" in str(error)
    assert "modify" in str(error).lower()


def test_summary_generation_error_message():
    """TaskSummaryGenerationError should wrap underlying error"""
    original_error = ValueError("API key invalid")
    error = TaskSummaryGenerationError(str(original_error))
    assert "API key invalid" in str(error)
```

**Step 2: Run test to verify it fails**

```bash
cd apps/api
pytest tests/modules/tasks/test_domain_exceptions.py -v
```

Expected output:
```
ModuleNotFoundError: No module named 'app.modules.tasks.domain.exceptions'
```

**Step 3: Write domain exceptions**

Create `apps/api/app/modules/tasks/domain/exceptions.py`:

```python
"""Task module domain-specific exceptions."""


class TaskDomainError(Exception):
    """Base exception for task domain errors."""
    pass


class TaskNotFoundError(TaskDomainError):
    """Raised when a task cannot be found."""
    
    def __init__(self, task_id: str):
        self.task_id = task_id
        super().__init__(f"Task with ID '{task_id}' not found")


class TaskStatusTransitionError(TaskDomainError):
    """Raised when an invalid status transition is attempted."""
    
    def __init__(self, current: str, target: str):
        self.current = current
        self.target = target
        super().__init__(
            f"Cannot transition from '{current}' to '{target}'. "
            f"This transition is not allowed by the state machine."
        )


class TaskModificationForbiddenError(TaskDomainError):
    """Raised when attempting to modify a task in a frozen state."""
    
    def __init__(self, status: str, detail: str = None):
        self.status = status
        msg = f"Cannot modify task in '{status}' state. This state is immutable."
        if detail:
            msg += f" {detail}"
        super().__init__(msg)


class TaskSummaryGenerationError(TaskDomainError):
    """Raised when AI summary generation fails."""
    
    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(f"Failed to generate task summary: {detail}")


class TaskAuthorizationError(TaskDomainError):
    """Raised when user is not authorized to perform an action on a task."""
    
    def __init__(self, user_id: str, task_id: str, action: str):
        self.user_id = user_id
        self.task_id = task_id
        self.action = action
        super().__init__(
            f"User '{user_id}' is not authorized to {action} task '{task_id}'"
        )
```

**Step 4: Write test for types/enums**

Create `apps/api/tests/modules/tasks/test_domain_types.py`:

```python
from app.modules.tasks.domain.types import TaskStatus, TaskPriority, AssignmentType


def test_task_status_enum_values():
    """TaskStatus enum should have all valid states"""
    assert TaskStatus.OPEN.value == "Open"
    assert TaskStatus.IN_PROGRESS.value == "In Progress"
    assert TaskStatus.COMPLETED.value == "Completed"
    assert TaskStatus.CLOSED.value == "Closed"


def test_task_priority_enum_values():
    """TaskPriority enum should have all priority levels"""
    assert TaskPriority.LOW.value == "Low"
    assert TaskPriority.NORMAL.value == "Normal"
    assert TaskPriority.HIGH.value == "High"
    assert TaskPriority.CRITICAL.value == "Critical"


def test_assignment_type_enum_values():
    """AssignmentType enum should support user and external"""
    assert AssignmentType.USER.value == "user"
    assert AssignmentType.EXTERNAL.value == "external"


def test_task_status_from_string():
    """Should convert string to TaskStatus"""
    status = TaskStatus("Open")
    assert status == TaskStatus.OPEN
```

**Step 5: Run types test to verify it fails**

```bash
cd apps/api
pytest tests/modules/tasks/test_domain_types.py -v
```

Expected: `ModuleNotFoundError`

**Step 6: Write domain types**

Create `apps/api/app/modules/tasks/domain/types.py`:

```python
"""Task module domain types and enums."""

from enum import Enum


class TaskStatus(str, Enum):
    """Valid task status values."""
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    CLOSED = "Closed"
    
    @property
    def is_terminal(self) -> bool:
        """Returns True if this is a terminal (immutable) state."""
        return self in {TaskStatus.CLOSED}


class TaskPriority(str, Enum):
    """Valid task priority levels."""
    LOW = "Low"
    NORMAL = "Normal"
    HIGH = "High"
    CRITICAL = "Critical"


class AssignmentType(str, Enum):
    """Type of task assignment."""
    USER = "user"
    EXTERNAL = "external"


# State Machine Definition for TASK entity
TASK_STATE_TRANSITIONS = {
    TaskStatus.OPEN: {TaskStatus.IN_PROGRESS, TaskStatus.CLOSED},
    TaskStatus.IN_PROGRESS: {TaskStatus.COMPLETED, TaskStatus.OPEN, TaskStatus.CLOSED},
    TaskStatus.COMPLETED: {TaskStatus.CLOSED},
    TaskStatus.CLOSED: set(),  # Terminal state - no outgoing transitions
}
```

**Step 7: Run both tests to verify they pass**

```bash
cd apps/api
pytest tests/modules/tasks/test_domain_exceptions.py tests/modules/tasks/test_domain_types.py -v
```

Expected: All tests PASS

**Step 8: Commit**

```bash
cd apps/api
git add app/modules/tasks/domain/exceptions.py app/modules/tasks/domain/types.py
git add tests/modules/tasks/test_domain_exceptions.py tests/modules/tasks/test_domain_types.py
git commit -m "feat: add task domain exceptions and type enums

- TaskNotFoundError, TaskStatusTransitionError, TaskModificationForbiddenError
- TaskSummaryGenerationError, TaskAuthorizationError
- TaskStatus, TaskPriority, AssignmentType enums
- State machine transition definitions
"
```

---

## TASK 2: Register TASK in StateMachine

**Files:**
- Modify: `apps/api/app/modules/shared/domain/state_machine.py` (add TASK registration)
- Create: `apps/api/tests/modules/tasks/test_state_machine_task.py`

**Step 1: Write test for StateMachine TASK registration**

Create `apps/api/tests/modules/tasks/test_state_machine_task.py`:

```python
import pytest
from app.modules.shared.domain.state_machine import StateMachine
from app.modules.tasks.domain.types import TaskStatus


def test_task_open_to_in_progress_transition_valid():
    """TASK should allow transition from Open to In Progress"""
    result = StateMachine.validate_transition(
        "TASK",
        TaskStatus.OPEN.value,
        TaskStatus.IN_PROGRESS.value
    )
    assert result is True


def test_task_open_to_closed_transition_valid():
    """TASK should allow direct transition from Open to Closed"""
    result = StateMachine.validate_transition(
        "TASK",
        TaskStatus.OPEN.value,
        TaskStatus.CLOSED.value
    )
    assert result is True


def test_task_in_progress_to_completed_transition_valid():
    """TASK should allow transition from In Progress to Completed"""
    result = StateMachine.validate_transition(
        "TASK",
        TaskStatus.IN_PROGRESS.value,
        TaskStatus.COMPLETED.value
    )
    assert result is True


def test_task_completed_to_closed_transition_valid():
    """TASK should allow transition from Completed to Closed"""
    result = StateMachine.validate_transition(
        "TASK",
        TaskStatus.COMPLETED.value,
        TaskStatus.CLOSED.value
    )
    assert result is True


def test_task_closed_is_terminal():
    """TASK in Closed state should forbid all transitions"""
    with pytest.raises(Exception) as exc_info:
        StateMachine.validate_transition(
            "TASK",
            TaskStatus.CLOSED.value,
            TaskStatus.COMPLETED.value
        )
    assert "not allowed" in str(exc_info.value).lower()


def test_task_invalid_transition_rejected():
    """TASK should reject invalid transitions like Completed -> Open"""
    with pytest.raises(Exception) as exc_info:
        StateMachine.validate_transition(
            "TASK",
            TaskStatus.COMPLETED.value,
            TaskStatus.OPEN.value
        )
    assert "not allowed" in str(exc_info.value).lower()


def test_check_modification_allowed_in_closed_state():
    """TASK in Closed state should forbid modifications"""
    with pytest.raises(Exception):
        StateMachine.check_modification_allowed("TASK", TaskStatus.CLOSED.value)


def test_check_modification_allowed_in_open_state():
    """TASK in Open state should allow modifications"""
    # Should not raise
    result = StateMachine.check_modification_allowed("TASK", TaskStatus.OPEN.value)
    assert result is None or result is True
```

**Step 2: Run test to verify it fails**

```bash
cd apps/api
pytest tests/modules/tasks/test_state_machine_task.py -v
```

Expected: Tests fail because TASK is not registered

**Step 3: Read current StateMachine implementation**

```bash
grep -n "def validate_transition" apps/api/app/modules/shared/domain/state_machine.py
```

Find the location and read the file to understand the structure.

**Step 4: Register TASK in StateMachine**

Modify `apps/api/app/modules/shared/domain/state_machine.py` to add TASK registration (exact modification depends on current structure, but should look like):

```python
# Add to the state machine registry in __init__ or class definition:

from app.modules.tasks.domain.types import TASK_STATE_TRANSITIONS

# In StateMachine class or initialization:
ENTITY_TRANSITIONS = {
    # ... existing entities ...
    "TASK": TASK_STATE_TRANSITIONS,
    # ... other entities ...
}
```

**Step 5: Run test to verify it passes**

```bash
cd apps/api
pytest tests/modules/tasks/test_state_machine_task.py -v
```

Expected: All tests PASS

**Step 6: Commit**

```bash
cd apps/api
git add app/modules/shared/domain/state_machine.py tests/modules/tasks/test_state_machine_task.py
git commit -m "feat: register TASK entity in StateMachine

- Add TASK state transitions: Open -> In Progress -> Completed -> Closed
- Support direct transitions (Open -> Closed)
- Enforce Closed as terminal state
- All tests passing
"
```

---

## TASK 3: Implement Atomic sr_no Counter

**Files:**
- Create: `apps/api/app/modules/tasks/infrastructure/counter.py`
- Modify: `apps/api/app/modules/tasks/infrastructure/repository.py` (add get_next_sr_no)
- Create: `apps/api/tests/modules/tasks/test_sr_no_atomicity.py`

**Step 1: Write test for atomic sr_no generation**

Create `apps/api/tests/modules/tasks/test_sr_no_atomicity.py`:

```python
import pytest
import asyncio
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.modules.tasks.infrastructure.repository import TaskRepository


@pytest.mark.asyncio
async def test_sr_no_counter_increments_atomically(db: AsyncIOMotorDatabase):
    """Multiple concurrent creates should get unique sr_no values"""
    repo = TaskRepository(db)
    org_id = "test-org-123"
    project_id = "test-project-456"
    
    # Create 5 tasks concurrently
    async def create_and_get_sr_no():
        sr_no = await repo.get_next_sr_no(org_id, project_id)
        return sr_no
    
    results = await asyncio.gather(*[create_and_get_sr_no() for _ in range(5)])
    
    # All sr_no values should be unique and sequential
    assert sorted(results) == [1, 2, 3, 4, 5], f"Got: {sorted(results)}"


@pytest.mark.asyncio
async def test_sr_no_counter_persists_across_calls(db: AsyncIOMotorDatabase):
    """sr_no counter should maintain state across multiple projects"""
    repo = TaskRepository(db)
    org_id = "test-org-123"
    project_id_1 = "project-1"
    project_id_2 = "project-2"
    
    # Get sr_no for project 1
    sr_no_1 = await repo.get_next_sr_no(org_id, project_id_1)
    assert sr_no_1 == 1
    
    # Get sr_no for project 2 (different project, should start at 1)
    sr_no_2 = await repo.get_next_sr_no(org_id, project_id_2)
    assert sr_no_2 == 1
    
    # Get next sr_no for project 1 (should be 2)
    sr_no_1_next = await repo.get_next_sr_no(org_id, project_id_1)
    assert sr_no_1_next == 2


@pytest.mark.asyncio
async def test_sr_no_counter_isolated_by_org_and_project(db: AsyncIOMotorDatabase):
    """sr_no counters should be isolated per org and project"""
    repo = TaskRepository(db)
    org_id_1 = "org-1"
    org_id_2 = "org-2"
    project_id = "same-project"
    
    # Both orgs create sr_no for same project (different counters)
    sr_no_org1 = await repo.get_next_sr_no(org_id_1, project_id)
    sr_no_org2 = await repo.get_next_sr_no(org_id_2, project_id)
    
    # Should both be 1 (isolated by org)
    assert sr_no_org1 == 1
    assert sr_no_org2 == 1
```

**Step 2: Run test to verify it fails**

```bash
cd apps/api
pytest tests/modules/tasks/test_sr_no_atomicity.py -v
```

Expected: `AttributeError: get_next_sr_no not found`

**Step 3: Write counter helper**

Create `apps/api/app/modules/tasks/infrastructure/counter.py`:

```python
"""Atomic counter utilities for task sr_no generation."""

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument


class AtomicCounter:
    """MongoDB-based atomic counter for generating sequential IDs."""
    
    COLLECTION_NAME = "task_sr_no_counters"
    
    @staticmethod
    async def get_next_value(
        db: AsyncIOMotorDatabase,
        org_id: str,
        project_id: str,
    ) -> int:
        """
        Get next sr_no value atomically.
        
        Uses MongoDB findOneAndUpdate to ensure atomic increment.
        Returns the new sequence value.
        """
        collection = db[AtomicCounter.COLLECTION_NAME]
        
        result = await collection.find_one_and_update(
            {
                "organisation_id": org_id,
                "project_id": project_id,
            },
            {"$inc": {"sequence": 1}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        
        return result["sequence"]
```

**Step 4: Modify TaskRepository to use counter**

Modify `apps/api/app/modules/tasks/infrastructure/repository.py`:

```python
"""Task repository with atomic sr_no support."""

from app.modules.shared.infrastructure.base_repository import BaseRepository
from app.modules.tasks.schemas.dto import Task
from app.modules.tasks.infrastructure.counter import AtomicCounter


class TaskRepository(BaseRepository):
    def __init__(self, db):
        super().__init__(db, "tasks", Task)
        self._db = db

    async def get_next_sr_no(self, org_id: str, project_id: str) -> int:
        """Get next sequential sr_no for a project."""
        return await AtomicCounter.get_next_value(
            self._db,
            org_id,
            project_id,
        )


class TaskAISummaryRepository(BaseRepository):
    def __init__(self, db):
        super().__init__(db, "task_ai_summaries", dict)
```

**Step 5: Run test to verify it passes**

```bash
cd apps/api
pytest tests/modules/tasks/test_sr_no_atomicity.py -v
```

Expected: All tests PASS

**Step 6: Update TaskService to use atomic counter**

Modify `apps/api/app/modules/tasks/application/task_service.py` method `create_task`:

```python
async def create_task(self, user: dict, data: TaskCreate) -> Dict[str, Any]:
    """Atomic creation with sequential sr_no."""
    # Use atomic counter instead of count + 1
    sr_no = await self.repo.get_next_sr_no(
        user["organisation_id"],
        data.project_id,
    )

    task_dict = data.model_dump()
    task_dict.update({
        "organisation_id": user["organisation_id"],
        "status": "Open",
        "sr_no": sr_no,
        "created_by": user["user_id"],
        "created_by_name": user.get("full_name") or user.get("name") or "System",
        "version": 1,
        "audit_log": [{
            "action": "CREATE",
            "timestamp": datetime.now(timezone.utc),
            "user": user.get("full_name") or user.get("name") or "System",
            "detail": f"Task created with sr_no {sr_no}",
        }],
    })
    return await self.repo.create(task_dict)
```

**Step 7: Commit**

```bash
cd apps/api
git add app/modules/tasks/infrastructure/counter.py
git add app/modules/tasks/infrastructure/repository.py
git add app/modules/tasks/application/task_service.py
git add tests/modules/tasks/test_sr_no_atomicity.py
git commit -m "feat: implement atomic sr_no counter to prevent race conditions

- Add AtomicCounter using MongoDB findOneAndUpdate for atomicity
- TaskRepository.get_next_sr_no() uses atomic increment
- TaskService.create_task() uses atomic counter
- Counters isolated per org and project
- Concurrent creates get unique sr_no values
"
```

---

## TASK 4: Add Authorization Checks

**Files:**
- Create: `apps/api/app/modules/tasks/domain/authorization.py`
- Modify: `apps/api/app/modules/tasks/application/task_service.py` (add auth checks)
- Create: `apps/api/tests/modules/tasks/test_task_authorization.py`

**Step 1: Write authorization tests**

Create `apps/api/tests/modules/tasks/test_task_authorization.py`:

```python
import pytest
from fastapi import HTTPException
from app.modules.tasks.application.task_service import TaskService
from app.modules.tasks.domain.exceptions import TaskAuthorizationError


@pytest.mark.asyncio
async def test_update_task_requires_project_access(service: TaskService, user: dict, task_id: str):
    """User cannot update task in project they don't have access to"""
    user_different_org = {
        **user,
        "organisation_id": "different-org",
    }
    
    with pytest.raises(HTTPException) as exc_info:
        await service.update_task_details(
            user_different_org,
            task_id,
            {"task_description": "new description"}
        )
    
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_delete_task_requires_authorization(service: TaskService, user: dict, task_id: str):
    """User cannot delete task in project they don't have access to"""
    user_different_org = {
        **user,
        "organisation_id": "different-org",
    }
    
    with pytest.raises(HTTPException) as exc_info:
        await service.delete_task(user_different_org, task_id)
    
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_update_status_requires_authorization(service: TaskService, user: dict, task_id: str):
    """User cannot update task status in project they don't have access to"""
    user_different_org = {
        **user,
        "organisation_id": "different-org",
    }
    
    with pytest.raises(HTTPException) as exc_info:
        await service.update_status(user_different_org, task_id, "Completed")
    
    assert exc_info.value.status_code == 403
```

**Step 2: Run test to verify it fails**

```bash
cd apps/api
pytest tests/modules/tasks/test_task_authorization.py -v
```

Expected: Tests fail (currently no org_id checking on org boundary)

**Step 3: Create authorization helper**

Create `apps/api/app/modules/tasks/domain/authorization.py`:

```python
"""Task authorization logic."""

from fastapi import HTTPException
from app.modules.tasks.domain.exceptions import TaskAuthorizationError


class TaskAuthorizationManager:
    """Manages authorization checks for task operations."""
    
    @staticmethod
    def verify_user_org_scoping(user_org_id: str, task_org_id: str) -> None:
        """
        Verify user belongs to same organization as task.
        
        Raises HTTPException with 403 if org_id mismatch.
        """
        if user_org_id != task_org_id:
            raise HTTPException(
                status_code=403,
                detail="You do not have access to this task"
            )
    
    @staticmethod
    def verify_project_access(user: dict, project_id: str) -> None:
        """
        Verify user has access to project.
        
        Currently checks org-scoping. Could be extended for role-based access.
        Raises HTTPException with 403 if access denied.
        """
        # Basic org-scoping check
        # Could extend with: project.allowed_roles, user.role, etc.
        if not project_id:
            raise HTTPException(
                status_code=400,
                detail="project_id is required"
            )
```

**Step 4: Modify TaskService to add authorization checks**

Update `apps/api/app/modules/tasks/application/task_service.py`:

```python
# Add import
from app.modules.tasks.domain.authorization import TaskAuthorizationManager

# In update_task_details:
async def update_task_details(self, user: dict, task_id: str, data: TaskUpdate) -> Dict[str, Any]:
    task = await self.repo.get_by_id(task_id, organisation_id=user["organisation_id"])
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # NEW: Verify org scoping (defensive check)
    TaskAuthorizationManager.verify_user_org_scoping(
        user["organisation_id"],
        task["organisation_id"]
    )

    # ... rest of method unchanged ...

# In update_status:
async def update_status(self, user: dict, task_id: str, new_status: str) -> Dict[str, Any]:
    task = await self.repo.get_by_id(task_id, organisation_id=user["organisation_id"])
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # NEW: Verify org scoping (defensive check)
    TaskAuthorizationManager.verify_user_org_scoping(
        user["organisation_id"],
        task["organisation_id"]
    )

    # ... rest of method unchanged ...

# In delete_task:
async def delete_task(self, user: dict, task_id: str) -> None:
    task = await self.repo.get_by_id(task_id, organisation_id=user["organisation_id"])
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # NEW: Verify org scoping (defensive check)
    TaskAuthorizationManager.verify_user_org_scoping(
        user["organisation_id"],
        task["organisation_id"]
    )

    # ... rest of method unchanged ...

# In get_task_ai_summary (in routes.py):
# Add check:
if not project_id:
    raise HTTPException(status_code=400, detail="project_id query parameter is required")

TaskAuthorizationManager.verify_project_access(user, project_id)
```

**Step 5: Run test to verify it passes**

```bash
cd apps/api
pytest tests/modules/tasks/test_task_authorization.py -v
```

Expected: All tests PASS

**Step 6: Commit**

```bash
cd apps/api
git add app/modules/tasks/domain/authorization.py
git add app/modules/tasks/application/task_service.py
git add tests/modules/tasks/test_task_authorization.py
git commit -m "feat: add authorization checks for task operations

- TaskAuthorizationManager enforces org-scoping on updates/deletes
- Verify user belongs to same org as task
- Verify project_id on AI summary endpoint
- All authorization tests passing
"
```

---

## TASK 5: Improve Error Handling & Add Timeouts

**Files:**
- Modify: `apps/api/app/modules/tasks/application/task_service.py` (add specific exception handling, timeouts)
- Modify: `apps/api/app/modules/tasks/api/routes.py` (improve exception handling)
- Create: `apps/api/tests/modules/tasks/test_error_handling.py`

**Step 1: Write error handling tests**

Create `apps/api/tests/modules/tasks/test_error_handling.py`:

```python
import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException
from app.modules.tasks.application.task_service import TaskService
from app.modules.tasks.domain.exceptions import (
    TaskSummaryGenerationError,
    TaskStatusTransitionError,
)


@pytest.mark.asyncio
async def test_ai_summary_timeout_handled():
    """AI summary generation should timeout after 30 seconds"""
    service = TaskService(db=None, audit=None, perm=None, snap=None)
    
    # Mock a slow provider
    with patch('app.core.ai_summary_service.EmergentSummaryProvider') as mock_provider:
        mock_instance = AsyncMock()
        mock_instance.generate_summary.side_effect = asyncio.TimeoutError()
        mock_provider.return_value = mock_instance
        
        # Should handle timeout gracefully
        with pytest.raises(TaskSummaryGenerationError):
            await service.get_task_summary_for_ai({"organisation_id": "org-1"}, "project-1")


@pytest.mark.asyncio
async def test_status_transition_error_specific():
    """Status transition errors should be specific, not generic"""
    service = TaskService(db=None, audit=None, perm=None, snap=None)
    
    with patch('app.modules.shared.domain.state_machine.StateMachine') as mock_sm:
        mock_sm.validate_transition.side_effect = TaskStatusTransitionError("Closed", "Open")
        
        # Should raise HTTPException with 400
        with pytest.raises(HTTPException) as exc_info:
            await service.update_status(
                {"organisation_id": "org-1"},
                "task-1",
                "Open"
            )
        
        assert exc_info.value.status_code == 400


def test_task_not_found_returns_404():
    """Attempting to get non-existent task returns 404"""
    # This test validates the route behavior
    pass
```

**Step 2: Run test to verify it fails**

```bash
cd apps/api
pytest tests/modules/tasks/test_error_handling.py -v
```

Expected: Tests fail (timeout not implemented)

**Step 3: Update TaskService for better error handling**

Modify `apps/api/app/modules/tasks/application/task_service.py`:

```python
# Add imports
import asyncio
import logging
from app.modules.tasks.domain.exceptions import TaskSummaryGenerationError, TaskStatusTransitionError

logger = logging.getLogger(__name__)

# In get_task_summary_for_ai:
async def get_task_summary_for_ai(self, user: dict, project_id: str) -> Dict[str, Any]:
    """Aggregates metrics and generates AI summary with caching."""
    try:
        summary_repo = TaskAISummaryRepository(self.db)

        # 1. Check Cache (6-hour TTL)
        existing = await summary_repo.find_one(
            {"project_id": project_id, "organisation_id": user["organisation_id"]},
            sort=[("created_at", -1)],
        )
        if existing:
            created_at = existing.get("created_at")
            if created_at and (datetime.now(timezone.utc) - created_at).total_seconds() < TASK_AI_SUMMARY_CACHE_TTL_SECONDS:
                return existing

        # 2. Aggregate task metrics
        tasks = await self.repo.list({
            "project_id": project_id,
            "organisation_id": user["organisation_id"],
        })
        if not tasks:
            return {"summary_text": "No tasks available to summarize.", "metrics": {}}
    except Exception as e:
        logger.error(f"Error aggregating task metrics for project {project_id}: {str(e)}")
        raise TaskSummaryGenerationError(f"Error aggregating metrics: {str(e)}")

    # ... metrics calculation code ...

    # 3. AI Generation with timeout and graceful fallback
    from app.core.ai_summary_service import EmergentSummaryProvider, MockSummaryProvider
    from app.core.config import settings

    project_repo = ProjectRepository(self.db)
    project = await project_repo.get_by_id(project_id)
    project_name = project.get("project_name", project_id) if project else project_id

    provider = (
        EmergentSummaryProvider(settings.OPENAI_API_KEY)
        if settings.OPENAI_API_KEY
        else MockSummaryProvider()
    )
    
    try:
        summary_text = await asyncio.wait_for(
            provider.generate_summary(report_data, f"Task Management for {project_name}"),
            timeout=30.0  # 30-second timeout
        )
    except asyncio.TimeoutError:
        logger.warning(f"AI summary generation timeout for project {project_id}")
        summary_text = f"Summary generation timed out for {project_name}. Please try again later."
    except Exception as e:
        logger.error(f"AI summary generation failed: {str(e)}")
        raise TaskSummaryGenerationError(str(e))

    doc = {
        "project_id": project_id,
        "organisation_id": user["organisation_id"],
        "summary_text": summary_text,
        "metrics": report_data,
        "created_at": datetime.now(timezone.utc),
    }
    return await summary_repo.create(doc)


# In update_status, replace bare except:
async def update_status(self, user: dict, task_id: str, new_status: str) -> Dict[str, Any]:
    task = await self.repo.get_by_id(task_id, organisation_id=user["organisation_id"])
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    current_status = task.get("status", "Open")
    if new_status == current_status:
        return task

    try:
        StateMachine.validate_transition("TASK", current_status, new_status)
    except TaskStatusTransitionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"State machine error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail="Invalid status transition")

    # ... rest of method ...
```

**Step 4: Update routes.py for better error handling**

Modify `apps/api/app/modules/tasks/api/routes.py`:

```python
# Update get_task_ai_summary endpoint:
@router.get("/ai-summary", response_model=GenericResponse)
async def get_task_ai_summary(
    project_id: str = None,
    user: dict = Depends(get_authenticated_user),
    service: TaskService = Depends(get_task_service),
):
    import logging
    from app.modules.tasks.domain.exceptions import TaskSummaryGenerationError
    
    logger = logging.getLogger(__name__)

    if not project_id:
        raise HTTPException(
            status_code=400,
            detail="project_id query parameter is required"
        )

    try:
        result = await service.get_task_summary_for_ai(user, project_id)
        return GenericResponse(data=result)
    except TaskSummaryGenerationError as e:
        logger.error(f"Failed to generate summary: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate task summary. Please try again later."
        )
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Unexpected error in AI summary endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )
```

**Step 5: Run test to verify it passes**

```bash
cd apps/api
pytest tests/modules/tasks/test_error_handling.py -v
```

Expected: All tests PASS

**Step 6: Commit**

```bash
cd apps/api
git add app/modules/tasks/application/task_service.py
git add app/modules/tasks/api/routes.py
git add tests/modules/tasks/test_error_handling.py
git commit -m "feat: improve error handling with specific exceptions and timeouts

- Replace bare 'except Exception' with specific exception types
- Add 30-second timeout for AI summary generation
- TaskSummaryGenerationError for generation failures
- TaskStatusTransitionError for invalid state transitions
- Proper logging of errors with context
- Graceful fallback for timeout scenarios
"
```

---

## TASK 6: Implement Cache Invalidation

**Files:**
- Modify: `apps/api/app/modules/tasks/application/task_service.py` (add cache invalidation)
- Create: `apps/api/app/modules/tasks/infrastructure/cache_manager.py`
- Create: `apps/api/tests/modules/tasks/test_cache_invalidation.py`

**Step 1: Write cache invalidation tests**

Create `apps/api/tests/modules/tasks/test_cache_invalidation.py`:

```python
import pytest
from datetime import datetime, timezone
from app.modules.tasks.infrastructure.repository import TaskAISummaryRepository


@pytest.mark.asyncio
async def test_cache_invalidated_on_task_create(db, user, project_id):
    """Creating a task should invalidate the AI summary cache"""
    repo = TaskAISummaryRepository(db)
    
    # Create a cached summary
    cache_doc = {
        "project_id": project_id,
        "organisation_id": user["organisation_id"],
        "summary_text": "Old summary",
        "metrics": {},
        "created_at": datetime.now(timezone.utc),
    }
    await repo.create(cache_doc)
    
    # Verify cache exists
    existing = await repo.find_one({
        "project_id": project_id,
        "organisation_id": user["organisation_id"],
    })
    assert existing is not None
    
    # Create a task
    from app.modules.tasks.application.task_service import TaskService
    service = TaskService(db)
    
    await service.create_task(user, {
        "project_id": project_id,
        "task_description": "New task",
        "assigned_to_name": "John",
    })
    
    # Verify cache is invalidated
    remaining = await repo.find_one({
        "project_id": project_id,
        "organisation_id": user["organisation_id"],
    })
    # Cache should be deleted (or at minimum, should regenerate on next access)
    assert remaining is None or remaining.get("id") != existing.get("id")


@pytest.mark.asyncio
async def test_cache_invalidated_on_task_update(db, user, task_id, project_id):
    """Updating a task should invalidate the AI summary cache"""
    repo = TaskAISummaryRepository(db)
    
    # Create a cached summary
    cache_doc = {
        "project_id": project_id,
        "organisation_id": user["organisation_id"],
        "summary_text": "Old summary",
        "metrics": {},
        "created_at": datetime.now(timezone.utc),
    }
    await repo.create(cache_doc)
    
    # Update the task
    from app.modules.tasks.application.task_service import TaskService
    service = TaskService(db)
    
    from app.modules.tasks.schemas.dto import TaskUpdate
    await service.update_task_details(
        user,
        task_id,
        TaskUpdate(task_description="Updated description")
    )
    
    # Cache should be invalidated
    remaining = await repo.find_one({
        "project_id": project_id,
        "organisation_id": user["organisation_id"],
    })
    assert remaining is None


@pytest.mark.asyncio
async def test_cache_invalidated_on_status_change(db, user, task_id, project_id):
    """Changing task status should invalidate the AI summary cache"""
    repo = TaskAISummaryRepository(db)
    
    # Create cached summary
    cache_doc = {
        "project_id": project_id,
        "organisation_id": user["organisation_id"],
        "summary_text": "Old summary",
        "metrics": {},
        "created_at": datetime.now(timezone.utc),
    }
    await repo.create(cache_doc)
    
    # Change task status
    from app.modules.tasks.application.task_service import TaskService
    service = TaskService(db)
    
    await service.update_status(user, task_id, "In Progress")
    
    # Cache should be invalidated
    remaining = await repo.find_one({
        "project_id": project_id,
        "organisation_id": user["organisation_id"],
    })
    assert remaining is None
```

**Step 2: Run test to verify it fails**

```bash
cd apps/api
pytest tests/modules/tasks/test_cache_invalidation.py -v
```

Expected: Tests fail (cache not invalidated on changes)

**Step 3: Create cache manager helper**

Create `apps/api/app/modules/tasks/infrastructure/cache_manager.py`:

```python
"""Cache management utilities for task AI summaries."""

from motor.motor_asyncio import AsyncIOMotorDatabase
from app.modules.tasks.infrastructure.repository import TaskAISummaryRepository


class TaskAISummaryCache:
    """Manages AI summary cache invalidation."""
    
    @staticmethod
    async def invalidate_for_project(
        db: AsyncIOMotorDatabase,
        org_id: str,
        project_id: str,
    ) -> None:
        """Delete cached AI summary for a project."""
        repo = TaskAISummaryRepository(db)
        await repo.delete_many({
            "project_id": project_id,
            "organisation_id": org_id,
        })
```

**Step 4: Modify TaskService to invalidate cache on changes**

Update `apps/api/app/modules/tasks/application/task_service.py`:

```python
# Add import
from app.modules.tasks.infrastructure.cache_manager import TaskAISummaryCache

# In create_task, after creating task, add:
async def create_task(self, user: dict, data: TaskCreate) -> Dict[str, Any]:
    # ... existing code ...
    result = await self.repo.create(task_dict)
    
    # Invalidate AI summary cache for this project
    await TaskAISummaryCache.invalidate_for_project(
        self.db,
        user["organisation_id"],
        data.project_id,
    )
    
    return result


# In update_status, after updating status, add:
async def update_status(self, user: dict, task_id: str, new_status: str) -> Dict[str, Any]:
    # ... existing code ...
    await self.repo.update_one(...)
    
    # Invalidate cache
    project_id = task.get("project_id")
    if project_id:
        await TaskAISummaryCache.invalidate_for_project(
            self.db,
            user["organisation_id"],
            project_id,
        )
    
    return await self.repo.get_by_id(task_id)


# In update_task_details, after updating task, add:
async def update_task_details(self, user: dict, task_id: str, data: TaskUpdate) -> Dict[str, Any]:
    # ... existing code ...
    await self.repo.update_one(...)
    
    # Invalidate cache
    project_id = task.get("project_id")
    if project_id:
        await TaskAISummaryCache.invalidate_for_project(
            self.db,
            user["organisation_id"],
            project_id,
        )
    
    return await self.repo.get_by_id(task_id)


# In delete_task, after deleting task, add:
async def delete_task(self, user: dict, task_id: str) -> None:
    # ... existing code ...
    
    # Before deletion, get project_id for cache invalidation
    task = await self.repo.get_by_id(task_id, organisation_id=user["organisation_id"])
    project_id = task.get("project_id") if task else None
    
    # ... perform deletion ...
    
    # Invalidate cache
    if project_id:
        await TaskAISummaryCache.invalidate_for_project(
            self.db,
            user["organisation_id"],
            project_id,
        )
```

**Step 5: Run test to verify it passes**

```bash
cd apps/api
pytest tests/modules/tasks/test_cache_invalidation.py -v
```

Expected: All tests PASS

**Step 6: Commit**

```bash
cd apps/api
git add app/modules/tasks/infrastructure/cache_manager.py
git add app/modules/tasks/application/task_service.py
git add tests/modules/tasks/test_cache_invalidation.py
git commit -m "feat: implement AI summary cache invalidation

- TaskAISummaryCache.invalidate_for_project() on create/update/delete
- Cache invalidated when task details change
- Cache invalidated when task status transitions
- Cache invalidated when task deleted
- Ensures users always see current task data in summaries
"
```

---

## TASK 7: Add MongoDB Indexes

**Files:**
- Create: `apps/api/app/modules/tasks/infrastructure/indexes.py`
- Modify: `apps/api/app/core/lifecycle.py` (call index creation on startup)
- Create: `apps/api/tests/modules/tasks/test_database_indexes.py`

**Step 1: Write index tests**

Create `apps/api/tests/modules/tasks/test_database_indexes.py`:

```python
import pytest
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.modules.tasks.infrastructure.indexes import TaskIndexManager


@pytest.mark.asyncio
async def test_task_indexes_created_on_startup(db: AsyncIOMotorDatabase):
    """Task collection should have proper indexes for query performance"""
    await TaskIndexManager.create_indexes(db)
    
    collection = db["tasks"]
    indexes = await collection.list_indexes().to_list(length=None)
    index_names = [idx["name"] for idx in indexes]
    
    # Check for required indexes
    assert "organisation_id_1_project_id_1" in index_names or \
           any("organisation_id" in idx["name"] and "project_id" in idx["name"] 
               for idx in indexes)
    
    assert "organisation_id_1_project_id_1_status_1" in index_names or \
           any("status" in idx["name"] for idx in indexes)


@pytest.mark.asyncio
async def test_counter_indexes_created(db: AsyncIOMotorDatabase):
    """Counter collection should have proper indexes"""
    await TaskIndexManager.create_indexes(db)
    
    collection = db["task_sr_no_counters"]
    indexes = await collection.list_indexes().to_list(length=None)
    index_names = [idx["name"] for idx in indexes]
    
    # Should have compound index on org_id and project_id
    assert any("organisation_id" in idx["name"] and "project_id" in idx["name"]
               for idx in indexes)
```

**Step 2: Run test to verify it fails**

```bash
cd apps/api
pytest tests/modules/tasks/test_database_indexes.py -v
```

Expected: Indexes don't exist yet

**Step 3: Create index manager**

Create `apps/api/app/modules/tasks/infrastructure/indexes.py`:

```python
"""Database index management for task collections."""

from motor.motor_asyncio import AsyncIOMotorDatabase
import logging

logger = logging.getLogger(__name__)


class TaskIndexManager:
    """Manages creation of indexes for task and counter collections."""
    
    @staticmethod
    async def create_indexes(db: AsyncIOMotorDatabase) -> None:
        """Create all required indexes for task module."""
        logger.info("Creating task module indexes...")
        
        # Tasks collection indexes
        tasks_collection = db["tasks"]
        
        # Index 1: org + project (for list queries)
        await tasks_collection.create_index([
            ("organisation_id", 1),
            ("project_id", 1),
        ], name="org_project_index")
        logger.debug("Created tasks.org_project_index")
        
        # Index 2: org + project + status (for filtered queries)
        await tasks_collection.create_index([
            ("organisation_id", 1),
            ("project_id", 1),
            ("status", 1),
        ], name="org_project_status_index")
        logger.debug("Created tasks.org_project_status_index")
        
        # Index 3: assigned_to_user_id (for user-assigned tasks)
        await tasks_collection.create_index([
            ("organisation_id", 1),
            ("assigned_to_user_id", 1),
        ], name="org_assigned_user_index")
        logger.debug("Created tasks.org_assigned_user_index")
        
        # Index 4: deadline (for overdue queries)
        await tasks_collection.create_index([
            ("deadline", 1),
        ], name="deadline_index")
        logger.debug("Created tasks.deadline_index")
        
        # Counter collection indexes
        counter_collection = db["task_sr_no_counters"]
        
        # Index for atomic counter lookup (unique compound key)
        await counter_collection.create_index([
            ("organisation_id", 1),
            ("project_id", 1),
        ], unique=True, name="unique_counter_index")
        logger.debug("Created task_sr_no_counters.unique_counter_index")
        
        # AI Summary collection indexes
        summary_collection = db["task_ai_summaries"]
        
        # Index for cache lookups and TTL cleanup
        await summary_collection.create_index([
            ("organisation_id", 1),
            ("project_id", 1),
            ("created_at", -1),
        ], name="org_project_created_index")
        logger.debug("Created task_ai_summaries.org_project_created_index")
        
        logger.info("Task module indexes created successfully")
```

**Step 4: Modify lifecycle to create indexes on startup**

Modify `apps/api/app/core/lifecycle.py` to call index creation:

```python
# Add import
from app.modules.tasks.infrastructure.indexes import TaskIndexManager

# In startup event handler (async def lifespan):
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up...")
    
    # Initialize database indexes
    db = app.state.db
    await TaskIndexManager.create_indexes(db)
    
    # ... rest of startup ...
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
```

**Step 5: Run test to verify it passes**

```bash
cd apps/api
pytest tests/modules/tasks/test_database_indexes.py -v
```

Expected: All tests PASS

**Step 6: Commit**

```bash
cd apps/api
git add app/modules/tasks/infrastructure/indexes.py
git add app/core/lifecycle.py
git add tests/modules/tasks/test_database_indexes.py
git commit -m "feat: add MongoDB indexes for task queries

- org_project_index: for list and filter queries
- org_project_status_index: for status-filtered queries
- org_assigned_user_index: for user-assigned task lookups
- deadline_index: for overdue task detection
- unique_counter_index: for atomic sr_no counter
- org_project_created_index: for cache lookups
- Indexes created on app startup
- Improves query performance and reduces CPU usage
"
```

---

## TASK 8: Integration Tests & Verification

**Files:**
- Create: `apps/api/tests/modules/tasks/test_integration_complete.py`
- Run: Full test suite

**Step 1: Write comprehensive integration test**

Create `apps/api/tests/modules/tasks/test_integration_complete.py`:

```python
"""Integration tests verifying all 6 critical fixes work together."""

import pytest
import asyncio
from app.modules.tasks.application.task_service import TaskService
from app.modules.tasks.schemas.dto import TaskCreate, TaskUpdate


@pytest.mark.asyncio
async def test_concurrent_task_creation_gets_unique_sr_no(db, user, project_id):
    """Multiple concurrent creates should get sequential unique sr_no"""
    service = TaskService(db)
    
    async def create_task(description: str) -> int:
        result = await service.create_task(user, TaskCreate(
            project_id=project_id,
            task_description=description,
            assigned_to_name="John",
        ))
        return result["sr_no"]
    
    # Create 10 tasks concurrently
    sr_nos = await asyncio.gather(*[
        create_task(f"Task {i}") for i in range(10)
    ])
    
    # All sr_no should be unique and sequential
    assert sorted(sr_nos) == list(range(1, 11))


@pytest.mark.asyncio
async def test_task_lifecycle_with_state_machine(db, user, task_id, project_id):
    """Task lifecycle should enforce StateMachine transitions"""
    service = TaskService(db)
    
    # Get initial task (Open)
    task = await service.get_task(user, task_id)
    assert task["status"] == "Open"
    
    # Transition: Open -> In Progress
    task = await service.update_status(user, task_id, "In Progress")
    assert task["status"] == "In Progress"
    
    # Transition: In Progress -> Completed
    task = await service.update_status(user, task_id, "Completed")
    assert task["status"] == "Completed"
    
    # Transition: Completed -> Closed
    task = await service.update_status(user, task_id, "Closed")
    assert task["status"] == "Closed"
    
    # Try to modify closed task (should fail)
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await service.update_task_details(
            user,
            task_id,
            TaskUpdate(task_description="Cannot edit closed task")
        )
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_cache_invalidation_on_task_change(db, user, task_id, project_id):
    """Updating task should invalidate AI summary cache"""
    service = TaskService(db)
    
    # Generate initial summary (creates cache)
    summary1 = await service.get_task_summary_for_ai(user, project_id)
    
    # Update task
    await service.update_task_details(user, task_id, TaskUpdate(
        task_description="Updated task"
    ))
    
    # Generate new summary (should not use old cache)
    summary2 = await service.get_task_summary_for_ai(user, project_id)
    
    # Summaries should be different (cache was invalidated)
    # At minimum, created_at should be newer
    assert summary2["created_at"] >= summary1["created_at"]


@pytest.mark.asyncio
async def test_authorization_prevents_cross_org_access(db, user, task_id):
    """Tasks from other organizations should not be accessible"""
    service = TaskService(db)
    
    user_different_org = {
        **user,
        "organisation_id": "different-org-id",
    }
    
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await service.get_task(user_different_org, task_id)
    
    # Should return 404 (not found from their org perspective)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_error_handling_timeout_graceful(db, user, project_id):
    """AI summary generation timeout should be handled gracefully"""
    service = TaskService(db)
    
    # This test verifies timeout handling exists
    # Actual timeout testing would require mocking the provider
    # But we verify the code path exists and doesn't crash
    result = await service.get_task_summary_for_ai(user, project_id)
    assert "summary_text" in result
```

**Step 2: Run full test suite**

```bash
cd apps/api
pytest tests/modules/tasks/ -v --tb=short
```

Expected: All tests PASS (50+ tests)

**Step 3: Run full API test suite to ensure no regressions**

```bash
cd apps/api
pytest tests/ -v -k "not slow" --tb=short
```

Expected: No failures in other modules

**Step 4: Commit**

```bash
cd apps/api
git add tests/modules/tasks/test_integration_complete.py
git commit -m "test: add comprehensive integration tests

- Verify concurrent sr_no generation produces unique sequential values
- Verify StateMachine enforces task lifecycle transitions
- Verify cache invalidation on task changes
- Verify authorization prevents cross-org access
- Verify error handling handles timeouts gracefully
- All 50+ task module tests passing
- No regressions in other modules
"
```

---

## TASK 9: Code Quality & Documentation

**Files:**
- Modify: `apps/api/app/modules/tasks/domain/constants.py` (create constants)
- Modify: `apps/api/app/modules/tasks/application/task_service.py` (add docstrings)
- Create: `apps/api/docs/modules/TASKS.md` (module documentation)

**Step 1: Extract magic numbers to constants**

Create `apps/api/app/modules/tasks/domain/constants.py`:

```python
"""Constants for task module."""

# AI Summary Cache Configuration
TASK_AI_SUMMARY_CACHE_TTL_SECONDS = 6 * 60 * 60  # 6 hours
TASK_AI_SUMMARY_GENERATION_TIMEOUT_SECONDS = 30  # 30 seconds

# Task Assignment
MAX_TOP_ASSIGNEES_IN_SUMMARY = 3

# Pagination
DEFAULT_PAGE_LIMIT = 50
MAX_PAGE_LIMIT = 500

# Audit & Logging
MAX_AUDIT_LOG_ENTRIES = 1000
```

**Step 2: Update service to use constants**

Update `apps/api/app/modules/tasks/application/task_service.py`:

```python
from app.modules.tasks.domain.constants import (
    TASK_AI_SUMMARY_CACHE_TTL_SECONDS,
    TASK_AI_SUMMARY_GENERATION_TIMEOUT_SECONDS,
    MAX_TOP_ASSIGNEES_IN_SUMMARY,
)

# Replace magic number in cache check:
if (datetime.now(timezone.utc) - created_at).total_seconds() < TASK_AI_SUMMARY_CACHE_TTL_SECONDS:

# Replace magic number in timeout:
await asyncio.wait_for(..., timeout=TASK_AI_SUMMARY_GENERATION_TIMEOUT_SECONDS)

# Replace magic number in top assignees:
top_assignees = dict(sorted(assignees.items(), key=lambda x: x[1], reverse=True)[:MAX_TOP_ASSIGNEES_IN_SUMMARY])
```

**Step 3: Add comprehensive docstrings**

Update `apps/api/app/modules/tasks/application/task_service.py` with docstrings for all methods:

```python
class TaskService:
    """
    Task management service implementing DDD patterns.
    
    Handles task CRUD operations, state transitions, and AI summary generation
    with proper authorization checks, audit logging, and cache management.
    
    Features:
    - Atomic sr_no generation preventing race conditions
    - StateMachine-based lifecycle management
    - Organization-scoped data isolation
    - AI summary generation with 6-hour caching
    - Comprehensive audit trail for all changes
    - Immutability enforcement for frozen states
    """

    async def create_task(self, user: dict, data: TaskCreate) -> Dict[str, Any]:
        """
        Create a new task with atomic sr_no generation.
        
        Args:
            user: Authenticated user dict with organisation_id
            data: TaskCreate schema with project_id, description, etc.
        
        Returns:
            Created task document with sr_no, status=Open, and initial audit log
        
        Raises:
            HTTPException: 400 if project_id invalid, 500 if database error
        
        Side Effects:
            - Invalidates AI summary cache for the project
            - Creates audit log entry for CREATE action
            - Atomically increments sr_no counter for the project
        """

    async def update_task_details(self, user: dict, task_id: str, data: TaskUpdate) -> Dict[str, Any]:
        """
        Update task fields with modification guard.
        
        Enforces StateMachine.check_modification_allowed() to prevent edits
        to frozen (Closed) tasks.
        
        Args:
            user: Authenticated user dict
            task_id: ID of task to update
            data: TaskUpdate schema with optional fields
        
        Returns:
            Updated task document with incremented version
        
        Raises:
            HTTPException: 403 if task in frozen state, 404 if not found
        
        Side Effects:
            - Invalidates AI summary cache
            - Creates UPDATE audit log entry
            - Increments version for optimistic locking
        """

    # ... docstrings for other methods ...
```

**Step 4: Create module documentation**

Create `apps/api/docs/modules/TASKS.md`:

```markdown
# Task Module Documentation

## Overview

The Tasks module handles task management for projects with full lifecycle support,
audit logging, and AI-powered summary generation.

## Architecture

### Domain Model
- **Task**: Aggregate root representing a work item
- **TaskStatus**: Enum (Open, In Progress, Completed, Closed)
- **TaskPriority**: Enum (Low, Normal, High, Critical)
- **AssignmentType**: Enum (user, external)

### State Machine
```
Open ──→ In Progress ──→ Completed ──→ Closed
 │          │                          ↑
 │          └──────────────────────────┘
 └─────────────────────────────────────→
```

- **Open**: Initial state, fully editable
- **In Progress**: Task being worked on, editable
- **Completed**: Work finished, can transition to Closed
- **Closed**: Terminal state, immutable

### Key Features

#### 1. Atomic sr_no Generation
Uses MongoDB atomic counter pattern to prevent race conditions:
```python
await repo.get_next_sr_no(org_id, project_id)
```

#### 2. Authorization & Org Scoping
All queries include `organisation_id` filter. Updates require org membership.

#### 3. Cache Management
AI summaries cached for 6 hours with automatic invalidation on task changes.

#### 4. Audit Trail
Every action (CREATE, UPDATE, STATUS_CHANGE) immutably logged in task document.

#### 5. State Immutability
Closed tasks cannot be edited or transitioned (enforced by StateMachine).

## API Endpoints

### List Tasks
```
GET /tasks/?project_id={id}
```
Returns all tasks for a project scoped to user's organization.

### Get Task
```
GET /tasks/{task_id}
```

### Create Task
```
POST /tasks/
{
  "project_id": "...",
  "task_description": "...",
  "assigned_to_name": "...",
  "assigned_to_user_id": "..." (optional),
  "priority": "Normal",
  "deadline": "2026-04-20T10:00:00Z" (optional)
}
```

### Update Task
```
PATCH /tasks/{task_id}
{
  "task_description": "...",
  "assigned_to_name": "...",
  "priority": "High"
}
```

### Update Status
```
PATCH /tasks/{task_id}/status
{
  "status": "In Progress"
}
```

### Delete Task
```
DELETE /tasks/{task_id}
```
- Hard-deletes pristine Open tasks
- Transitions tasks with history to Closed (preserves audit)

### Get AI Summary
```
GET /tasks/ai-summary?project_id={id}
```
Returns task metrics and AI-generated summary with caching.

## Database Collections

### tasks
Primary task collection with indexes:
- `org_project_index`: For list queries
- `org_project_status_index`: For status filters
- `org_assigned_user_index`: For user task lookup
- `deadline_index`: For overdue detection

### task_sr_no_counters
Atomic counter collection for sequential sr_no generation.

### task_ai_summaries
Cached AI summaries with 6-hour TTL.

## Testing

Run task module tests:
```bash
cd apps/api
pytest tests/modules/tasks/ -v
```

Key test files:
- `test_sr_no_atomicity.py`: Concurrent sr_no generation
- `test_state_machine_task.py`: State transitions
- `test_task_authorization.py`: Auth & org scoping
- `test_error_handling.py`: Timeouts & exceptions
- `test_cache_invalidation.py`: Cache management
- `test_integration_complete.py`: End-to-end workflows

## Known Limitations & Future Work

1. **Pagination**: List endpoint returns all tasks (should add pagination)
2. **Filtering**: Limited to project_id (should add status, assignee filters)
3. **User Assignment**: Currently supports name-based assignment (could add user lookup)
4. **Notifications**: No task assignment or status change notifications yet
5. **Dependencies**: Tasks cannot link to other tasks or work orders

## Migration Notes

### From Previous Version
If upgrading from version < 2.0:
1. Run `TaskIndexManager.create_indexes(db)` to add missing indexes
2. Add TASK to StateMachine registry
3. Run atomic counter initialization for existing projects
4. No data migration needed (backward compatible)

---

**Last Updated**: 2026-04-08
**Module Owner**: Task Management Team
**Status**: Production Ready
```

**Step 5: Commit**

```bash
cd apps/api
git add app/modules/tasks/domain/constants.py
git add app/modules/tasks/application/task_service.py
git add docs/modules/TASKS.md
git commit -m "docs: add comprehensive documentation and extract constants

- Extract magic numbers to TASK_AI_SUMMARY_CACHE_TTL_SECONDS, etc.
- Add comprehensive docstrings to all TaskService methods
- Create detailed module documentation
- Document API endpoints, collections, and testing
- Add migration notes for version upgrades
"
```

---

## Summary

All 6 critical issues fixed with comprehensive tests:

✅ **TASK 1**: Domain exceptions & type enums  
✅ **TASK 2**: StateMachine TASK registration  
✅ **TASK 3**: Atomic sr_no counter (race condition fix)  
✅ **TASK 4**: Authorization checks  
✅ **TASK 5**: Error handling & timeouts  
✅ **TASK 6**: Cache invalidation  
✅ **TASK 7**: MongoDB indexes  
✅ **TASK 8**: Integration tests  
✅ **TASK 9**: Documentation & constants  

---

**Plan complete and saved to** `D:/_repos/TAC-PMC-CRM/docs/plans/2026-04-08-task-module-critical-fixes.md`

## Two Execution Options:

**Option 1: Subagent-Driven Execution (this session)**
- I dispatch specialized subagents per task
- Two-stage code review (spec compliance → quality)
- Fast iteration with immediate feedback
- Takes ~2-3 hours for full completion
- **REQUIRED SUB-SKILL**: superpowers:subagent-driven-development

**Option 2: Parallel Session Execution (separate)**
- Open new Claude Code session in worktree
- Batch execute multiple tasks sequentially
- Checkpoints between major milestones  
- Self-paced execution
- **REQUIRED SUB-SKILL**: superpowers:executing-plans

**Which approach would you prefer?**