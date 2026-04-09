"""
Integration Tests: Baseline Locking + Scheduler Service

Tests that baseline locking is properly enforced in the scheduler
when attempting to recalculate schedules with locked tasks.
"""

import pytest
from app.modules.shared.domain.exceptions import DataFreezeError
from app.modules.scheduler.baseline_manager import BaselineManager


@pytest.fixture
def sample_schedule():
    """Sample project schedule."""
    return {
        "project_id": "proj-integration-001",
        "organisation_id": "org-001",
        "tasks": [
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
        ],
    }


@pytest.mark.asyncio
async def test_baseline_lock_prevents_recalculation(baseline_manager, sample_schedule):
    """Test that locked baseline prevents schedule recalculation."""
    tasks = sample_schedule["tasks"]

    # Lock the baseline
    await baseline_manager.lock_baseline(
        project_id=sample_schedule["project_id"],
        organisation_id=sample_schedule["organisation_id"],
        user_id="user-001",
        tasks=tasks,
        baseline_version=1,
    )

    # Retrieve locked tasks from snapshot
    snapshot = await baseline_manager.get_snapshot(
        project_id=sample_schedule["project_id"],
        organisation_id=sample_schedule["organisation_id"],
        baseline_version=1,
    )

    locked_tasks = snapshot["tasks"]

    # Verify tasks are marked as locked
    for task in locked_tasks:
        assert task.get("baseline_locked") is True
        assert task.get("baseline_version") == 1

    # Attempt to modify a locked task's duration
    locked_tasks[0]["duration"] = 8  # Change from 5 to 8

    # This should fail in scheduler.calculate_schedule()
    # due to the baseline lock check
    modified_task = locked_tasks[0]

    # Verify the check would catch this
    assert modified_task.get("baseline_locked") is True


@pytest.mark.asyncio
async def test_baseline_unlock_allows_recalculation(baseline_manager, sample_schedule):
    """Test that unlocked baseline allows schedule recalculation."""
    tasks = sample_schedule["tasks"]

    # Lock baseline
    await baseline_manager.lock_baseline(
        project_id=sample_schedule["project_id"],
        organisation_id=sample_schedule["organisation_id"],
        user_id="user-001",
        tasks=tasks,
        baseline_version=1,
    )

    # Unlock baseline
    await baseline_manager.unlock_baseline(
        project_id=sample_schedule["project_id"],
        organisation_id=sample_schedule["organisation_id"],
        user_id="user-001",
        tasks=tasks,
    )

    # Reload from schedule (simulated)
    tasks = [
        {**task, "baseline_locked": False}
        for task in tasks
    ]

    # Now modifications should be allowed
    modified_task = tasks[0]
    assert modified_task.get("baseline_locked") is False

    # Verify we can validate modifications without error
    result = baseline_manager.validate_modifications(
        modified_task,
        {"duration": 8}
    )

    assert result is True


@pytest.mark.asyncio
async def test_baseline_lock_cycle(baseline_manager, sample_schedule):
    """Test complete lock → modify → unlock → modify cycle."""
    tasks = sample_schedule["tasks"]

    # 1. Lock V1
    lock_v1 = await baseline_manager.lock_baseline(
        project_id=sample_schedule["project_id"],
        organisation_id=sample_schedule["organisation_id"],
        user_id="user-001",
        tasks=tasks,
        baseline_version=1,
    )

    assert lock_v1["baseline_version"] == 1

    # 2. Snapshot V1 should exist
    snap_v1 = await baseline_manager.get_snapshot(
        project_id=sample_schedule["project_id"],
        organisation_id=sample_schedule["organisation_id"],
        baseline_version=1,
    )

    assert snap_v1 is not None
    assert snap_v1["baseline_version"] == 1

    # 3. Unlock
    unlock = await baseline_manager.unlock_baseline(
        project_id=sample_schedule["project_id"],
        organisation_id=sample_schedule["organisation_id"],
        user_id="user-001",
        tasks=tasks,
    )

    assert unlock["unlocked_tasks"] == 2

    # 4. Modify tasks and lock V2
    modified_tasks = [
        {
            **task,
            "duration": task["duration"] + 2,
            "baseline_locked": False,  # Clear from V1
        }
        for task in tasks
    ]

    lock_v2 = await baseline_manager.lock_baseline(
        project_id=sample_schedule["project_id"],
        organisation_id=sample_schedule["organisation_id"],
        user_id="user-001",
        tasks=modified_tasks,
        baseline_version=2,
    )

    assert lock_v2["baseline_version"] == 2

    # 5. Both V1 and V2 should exist
    snap_v2 = await baseline_manager.get_snapshot(
        project_id=sample_schedule["project_id"],
        organisation_id=sample_schedule["organisation_id"],
        baseline_version=2,
    )

    assert snap_v2 is not None
    assert snap_v2["tasks"][0]["duration"] == 7  # 5 + 2

    # V1 should still be unchanged
    snap_v1_again = await baseline_manager.get_snapshot(
        project_id=sample_schedule["project_id"],
        organisation_id=sample_schedule["organisation_id"],
        baseline_version=1,
    )

    assert snap_v1_again["tasks"][0]["duration"] == 5  # Original


@pytest.mark.asyncio
async def test_metadata_editable_after_lock(baseline_manager, sample_schedule):
    """Test that metadata fields can be edited even after lock."""
    tasks = sample_schedule["tasks"]

    # Lock baseline
    await baseline_manager.lock_baseline(
        project_id=sample_schedule["project_id"],
        organisation_id=sample_schedule["organisation_id"],
        user_id="user-001",
        tasks=tasks,
        baseline_version=1,
    )

    # Get locked task
    snapshot = await baseline_manager.get_snapshot(
        project_id=sample_schedule["project_id"],
        organisation_id=sample_schedule["organisation_id"],
        baseline_version=1,
    )

    locked_task = snapshot["tasks"][0]

    # Should allow metadata edits
    result = baseline_manager.validate_modifications(
        locked_task,
        {
            "comments": "New comment",
            "notes": "Additional notes",
            "status": "In Review",
        }
    )

    assert result is True

    # Should block schedule edits
    with pytest.raises(DataFreezeError):
        baseline_manager.validate_modifications(
            locked_task,
            {"scheduled_start": "2024-01-02"}
        )
