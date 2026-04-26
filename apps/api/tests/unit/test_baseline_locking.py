"""
Unit Tests: Baseline Locking & Immutability Enforcement

Tests for Phase 1 Task #11: Baseline Locking
- Task immutability after baseline lock
- DataFreezeError enforcement
- Snapshot creation and retrieval
- Lock/unlock lifecycle
"""

import pytest
from datetime import datetime, timezone
from app.modules.scheduler.baseline_manager import BaselineManager
from app.modules.shared.domain.exceptions import DataFreezeError, ValidationError


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def baseline_manager(test_db):
    """Create baseline manager with test database."""
    return BaselineManager(test_db)


@pytest.fixture
def sample_tasks():
    """Sample task list for testing."""
    return [
        {
            "task_id": "A",
            "task_name": "Foundation",
            "duration": 5,
            "predecessors": [],
            "scheduled_start": "2024-01-01",
            "scheduled_finish": "2024-01-05",
            "is_critical": True,
            "slack": 0,
        },
        {
            "task_id": "B",
            "task_name": "Framing",
            "duration": 10,
            "predecessors": [{"task_id": "A", "strength": "hard", "lag": 0}],
            "scheduled_start": "2024-01-06",
            "scheduled_finish": "2024-01-15",
            "is_critical": True,
            "slack": 0,
        },
        {
            "task_id": "C",
            "task_name": "Electrical",
            "duration": 8,
            "predecessors": [{"task_id": "B", "strength": "soft", "lag": 0}],
            "scheduled_start": "2024-01-06",
            "scheduled_finish": "2024-01-13",
            "is_critical": False,
            "slack": 2,
        },
    ]


# ============================================================================
# TEST: Lock Baseline
# ============================================================================

@pytest.mark.asyncio
async def test_lock_baseline_marks_tasks_immutable(baseline_manager, sample_tasks):
    """Test that lock_baseline marks all tasks as immutable."""
    result = await baseline_manager.lock_baseline(
        project_id="proj-001",
        organisation_id="org-001",
        user_id="user-001",
        tasks=sample_tasks,
        baseline_version=1,
    )

    assert result["locked_tasks"] == 3
    assert result["baseline_version"] == 1
    assert "snapshot_id" in result
    assert result["locked_by"] == "user-001"


@pytest.mark.asyncio
async def test_lock_baseline_creates_snapshot(baseline_manager, sample_tasks):
    """Test that lock_baseline creates an immutable snapshot."""
    result = await baseline_manager.lock_baseline(
        project_id="proj-001",
        organisation_id="org-001",
        user_id="user-001",
        tasks=sample_tasks,
        baseline_version=1,
    )

    snapshot_id = result["snapshot_id"]
    snapshot = await baseline_manager.get_snapshot(
        project_id="proj-001",
        organisation_id="org-001",
        baseline_version=1,
    )

    assert snapshot is not None
    assert snapshot["baseline_version"] == 1
    assert snapshot["task_count"] == 3
    assert len(snapshot["tasks"]) == 3


@pytest.mark.asyncio
async def test_lock_baseline_stores_baseline_dates(baseline_manager, sample_tasks):
    """Test that lock_baseline stores baseline_start/finish dates."""
    result = await baseline_manager.lock_baseline(
        project_id="proj-001",
        organisation_id="org-001",
        user_id="user-001",
        tasks=sample_tasks,
        baseline_version=1,
    )

    snapshot = await baseline_manager.get_snapshot(
        project_id="proj-001",
        organisation_id="org-001",
        baseline_version=1,
    )

    task_a = snapshot["tasks"][0]
    assert task_a["baseline_start"] == "2024-01-01"
    assert task_a["baseline_finish"] == "2024-01-05"


@pytest.mark.asyncio
async def test_lock_baseline_empty_task_list_raises_error(baseline_manager):
    """Test that locking with empty task list raises ValidationError."""
    with pytest.raises(ValidationError):
        await baseline_manager.lock_baseline(
            project_id="proj-001",
            organisation_id="org-001",
            user_id="user-001",
            tasks=[],
            baseline_version=1,
        )


# ============================================================================
# TEST: Check Baseline Locked
# ============================================================================

@pytest.mark.asyncio
async def test_check_baseline_locked_unlocked_task(baseline_manager, sample_tasks):
    """Test checking baseline lock on unlocked task."""
    task = sample_tasks[0]
    is_locked = baseline_manager.check_baseline_locked(task, attempting_modification=False)
    assert is_locked is False


@pytest.mark.asyncio
async def test_check_baseline_locked_locked_task_raises_freeze_error(baseline_manager, sample_tasks):
    """Test that modifying locked task raises DataFreezeError."""
    task = sample_tasks[0]
    task["baseline_locked"] = True
    task["baseline_version"] = 1

    with pytest.raises(DataFreezeError):
        baseline_manager.check_baseline_locked(task, attempting_modification=True)


@pytest.mark.asyncio
async def test_check_baseline_locked_locked_task_no_modification_allowed(baseline_manager, sample_tasks):
    """Test that locked status is detected without modification flag."""
    task = sample_tasks[0]
    task["baseline_locked"] = True

    is_locked = baseline_manager.check_baseline_locked(task, attempting_modification=False)
    assert is_locked is True


# ============================================================================
# TEST: Validate Modifications
# ============================================================================

@pytest.mark.asyncio
async def test_validate_modifications_unlocked_task_allows_all(baseline_manager, sample_tasks):
    """Test that unlocked tasks allow any modifications."""
    task = sample_tasks[0]
    modifications = {
        "scheduled_start": "2024-01-02",
        "duration": 6,
        "task_name": "Updated Foundation",
    }

    result = baseline_manager.validate_modifications(task, modifications)
    assert result is True


@pytest.mark.asyncio
async def test_validate_modifications_locked_task_blocks_schedule_fields(baseline_manager, sample_tasks):
    """Test that locked tasks block modifications to schedule fields."""
    task = sample_tasks[0]
    task["baseline_locked"] = True
    task["baseline_version"] = 1

    modifications = {"scheduled_start": "2024-01-02"}

    with pytest.raises(DataFreezeError):
        baseline_manager.validate_modifications(task, modifications)


@pytest.mark.asyncio
async def test_validate_modifications_locked_task_blocks_duration(baseline_manager, sample_tasks):
    """Test that locked tasks block duration changes."""
    task = sample_tasks[0]
    task["baseline_locked"] = True
    task["baseline_version"] = 1

    modifications = {"duration": 6}

    with pytest.raises(DataFreezeError):
        baseline_manager.validate_modifications(task, modifications)


@pytest.mark.asyncio
async def test_validate_modifications_locked_task_blocks_criticality(baseline_manager, sample_tasks):
    """Test that locked tasks block criticality changes."""
    task = sample_tasks[0]
    task["baseline_locked"] = True
    task["baseline_version"] = 1

    modifications = {"is_critical": False}

    with pytest.raises(DataFreezeError):
        baseline_manager.validate_modifications(task, modifications)


@pytest.mark.asyncio
async def test_validate_modifications_locked_task_allows_metadata(baseline_manager, sample_tasks):
    """Test that locked tasks allow metadata changes (comments, notes)."""
    task = sample_tasks[0]
    task["baseline_locked"] = True
    task["baseline_version"] = 1

    modifications = {
        "comments": "Updated comment",
        "notes": "Additional notes",
    }

    result = baseline_manager.validate_modifications(task, modifications)
    assert result is True


@pytest.mark.asyncio
async def test_validate_modifications_locked_task_blocks_name_change(baseline_manager, sample_tasks):
    """Test that locked tasks block task name changes."""
    task = sample_tasks[0]
    task["baseline_locked"] = True
    task["baseline_version"] = 1

    modifications = {"task_name": "New Name"}

    with pytest.raises(DataFreezeError):
        baseline_manager.validate_modifications(task, modifications)


# ============================================================================
# TEST: Unlock Baseline
# ============================================================================

@pytest.mark.asyncio
async def test_unlock_baseline_unfreezes_tasks(baseline_manager, sample_tasks):
    """Test that unlock_baseline removes immutability."""
    result = await baseline_manager.unlock_baseline(
        project_id="proj-001",
        organisation_id="org-001",
        user_id="user-001",
        tasks=sample_tasks,
    )

    assert result["unlocked_tasks"] == 3
    assert result["unlocked_by"] == "user-001"
    assert "unlocked_at" in result


# ============================================================================
# TEST: Snapshot Management
# ============================================================================

@pytest.mark.asyncio
async def test_list_snapshots(baseline_manager, sample_tasks):
    """Test listing snapshots for a project."""
    # Create multiple snapshots
    for v in range(1, 4):
        await baseline_manager.lock_baseline(
            project_id="proj-001",
            organisation_id="org-001",
            user_id="user-001",
            tasks=sample_tasks,
            baseline_version=v,
        )

    snapshots = await baseline_manager.list_snapshots(
        project_id="proj-001",
        organisation_id="org-001",
        limit=50,
    )

    assert len(snapshots) == 3
    # Should be in reverse order (newest first)
    assert snapshots[0]["baseline_version"] == 3


@pytest.mark.asyncio
async def test_list_snapshots_pagination(baseline_manager, sample_tasks):
    """Test snapshot list pagination."""
    for v in range(1, 6):
        await baseline_manager.lock_baseline(
            project_id="proj-001",
            organisation_id="org-001",
            user_id="user-001",
            tasks=sample_tasks,
            baseline_version=v,
        )

    page1 = await baseline_manager.list_snapshots(
        project_id="proj-001",
        organisation_id="org-001",
        limit=2,
        skip=0,
    )

    page2 = await baseline_manager.list_snapshots(
        project_id="proj-001",
        organisation_id="org-001",
        limit=2,
        skip=2,
    )

    assert len(page1) == 2
    assert len(page2) == 2
    # Verify different versions on each page
    assert page1[0]["baseline_version"] != page2[0]["baseline_version"]


@pytest.mark.asyncio
async def test_get_snapshot_not_found_returns_none(baseline_manager):
    """Test retrieving non-existent snapshot."""
    snapshot = await baseline_manager.get_snapshot(
        project_id="proj-nonexistent",
        organisation_id="org-001",
        baseline_version=1,
    )

    assert snapshot is None


# ============================================================================
# TEST: Duration Calculation
# ============================================================================

@pytest.mark.asyncio
async def test_snapshot_calculates_duration(baseline_manager, sample_tasks):
    """Test that snapshot correctly calculates project duration."""
    result = await baseline_manager.lock_baseline(
        project_id="proj-001",
        organisation_id="org-001",
        user_id="user-001",
        tasks=sample_tasks,
        baseline_version=1,
    )

    snapshot = await baseline_manager.get_snapshot(
        project_id="proj-001",
        organisation_id="org-001",
        baseline_version=1,
    )

    # From 2024-01-01 to 2024-01-15 = 14 days
    assert snapshot["total_duration_days"] == 14


@pytest.mark.asyncio
async def test_snapshot_empty_task_list_zero_duration(baseline_manager):
    """Test that empty task list results in zero duration."""
    # This should be caught by lock_baseline validation
    with pytest.raises(ValidationError):
        await baseline_manager.lock_baseline(
            project_id="proj-001",
            organisation_id="org-001",
            user_id="user-001",
            tasks=[],
            baseline_version=1,
        )


# ============================================================================
# TEST: Multi-Version Baseline
# ============================================================================

@pytest.mark.asyncio
async def test_multiple_baseline_versions(baseline_manager, sample_tasks):
    """Test managing multiple baseline versions."""
    modified_tasks_v2 = [
        {**task, "duration": task["duration"] + 2}
        for task in sample_tasks
    ]

    # Lock version 1
    v1 = await baseline_manager.lock_baseline(
        project_id="proj-001",
        organisation_id="org-001",
        user_id="user-001",
        tasks=sample_tasks,
        baseline_version=1,
    )

    # Lock version 2 with modified tasks
    v2 = await baseline_manager.lock_baseline(
        project_id="proj-001",
        organisation_id="org-001",
        user_id="user-001",
        tasks=modified_tasks_v2,
        baseline_version=2,
    )

    # Both should exist independently
    snap1 = await baseline_manager.get_snapshot(
        project_id="proj-001",
        organisation_id="org-001",
        baseline_version=1,
    )

    snap2 = await baseline_manager.get_snapshot(
        project_id="proj-001",
        organisation_id="org-001",
        baseline_version=2,
    )

    assert snap1 is not None
    assert snap2 is not None
    assert snap1["tasks"][0]["duration"] == 5
    assert snap2["tasks"][0]["duration"] == 7


# ============================================================================
# TEST: Organization Isolation
# ============================================================================

@pytest.mark.asyncio
async def test_baseline_org_isolation(baseline_manager, sample_tasks):
    """Test that baselines are isolated per organization."""
    # Lock for org-001
    await baseline_manager.lock_baseline(
        project_id="proj-001",
        organisation_id="org-001",
        user_id="user-001",
        tasks=sample_tasks,
        baseline_version=1,
    )

    # Try to get for org-002
    snap = await baseline_manager.get_snapshot(
        project_id="proj-001",
        organisation_id="org-002",
        baseline_version=1,
    )

    assert snap is None


# ============================================================================
# TEST: Immutable Fields Set
# ============================================================================

def test_immutable_fields_definition():
    """Test that immutable fields are properly defined."""
    expected_fields = {
        "scheduled_start",
        "scheduled_finish",
        "duration",
        "task_name",
        "is_critical",
        "slack"
    }

    assert BaselineManager.IMMUTABLE_FIELDS == expected_fields
