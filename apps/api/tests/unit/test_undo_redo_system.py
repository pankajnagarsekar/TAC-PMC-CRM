"""
Comprehensive tests for Undo/Redo System (Task #15)
Tests snapshot capture, deduplication, stack operations, and state validation.
"""
import pytest
from typing import List, Dict, Any
from app.modules.project.application.undo_redo_service import (
    UndoRedoService,
    ScheduleHistoryRepository,
)
from app.modules.shared.domain.exceptions import ValidationError


@pytest.fixture
async def undo_redo_service(test_db):
    """Fixture providing initialized UndoRedoService."""
    service = UndoRedoService(test_db)
    return service


@pytest.fixture
async def sample_tasks() -> List[Dict[str, Any]]:
    """Sample task list for testing."""
    return [
        {
            "task_id": "task_1",
            "task_name": "Foundation",
            "status": "Open",
            "duration_days": 5,
            "predecessors": [],
            "start_date": "2026-05-01",
            "finish_date": "2026-05-05",
        },
        {
            "task_id": "task_2",
            "task_name": "Framing",
            "status": "Open",
            "duration_days": 10,
            "predecessors": ["task_1"],
            "start_date": "2026-05-06",
            "finish_date": "2026-05-15",
        },
        {
            "task_id": "task_3",
            "task_name": "Roofing",
            "status": "Open",
            "duration_days": 8,
            "predecessors": ["task_2"],
            "start_date": "2026-05-16",
            "finish_date": "2026-05-23",
        },
    ]


@pytest.fixture
async def modified_tasks(sample_tasks) -> List[Dict[str, Any]]:
    """Modified task list (framing duration increased)."""
    modified = [t.copy() for t in sample_tasks]
    modified[1]["duration_days"] = 15  # Increase framing from 10 to 15
    modified[1]["finish_date"] = "2026-05-20"
    return modified


class TestSnapshotCapture:
    """Test snapshot capture with deduplication and stack management."""

    @pytest.mark.asyncio
    async def test_capture_snapshot_creates_entry(self, undo_redo_service, sample_tasks):
        """Test that capture_snapshot creates a new history entry."""
        project_id = "proj_001"
        org_id = "org_001"
        user_id = "user_001"

        entry_id = await undo_redo_service.capture_snapshot(
            project_id=project_id,
            org_id=org_id,
            user_id=user_id,
            change_type="SAVE_SCHEDULE",
            summary="Initial schedule",
            tasks=sample_tasks,
        )

        assert entry_id is not None
        assert isinstance(entry_id, str)

    @pytest.mark.asyncio
    async def test_capture_snapshot_deduplication(self, undo_redo_service, sample_tasks):
        """Test that identical snapshots are deduplicated."""
        project_id = "proj_001"
        org_id = "org_001"
        user_id = "user_001"

        # Capture first snapshot
        entry_id_1 = await undo_redo_service.capture_snapshot(
            project_id=project_id,
            org_id=org_id,
            user_id=user_id,
            change_type="SAVE_SCHEDULE",
            summary="Initial schedule",
            tasks=sample_tasks,
        )

        # Capture identical snapshot again
        entry_id_2 = await undo_redo_service.capture_snapshot(
            project_id=project_id,
            org_id=org_id,
            user_id=user_id,
            change_type="SAVE_SCHEDULE",
            summary="Same schedule",
            tasks=sample_tasks,
        )

        # Should return same entry ID (deduplication)
        assert entry_id_1 == entry_id_2

    @pytest.mark.asyncio
    async def test_capture_snapshot_increments_position(
        self, undo_redo_service, sample_tasks, modified_tasks
    ):
        """Test that different snapshots increment stack position."""
        project_id = "proj_001"
        org_id = "org_001"
        user_id = "user_001"

        # Capture initial
        entry_id_1 = await undo_redo_service.capture_snapshot(
            project_id=project_id,
            org_id=org_id,
            user_id=user_id,
            change_type="SAVE_SCHEDULE",
            summary="Initial",
            tasks=sample_tasks,
        )

        # Capture modified
        entry_id_2 = await undo_redo_service.capture_snapshot(
            project_id=project_id,
            org_id=org_id,
            user_id=user_id,
            change_type="SAVE_SCHEDULE",
            summary="Modified",
            tasks=modified_tasks,
        )

        assert entry_id_1 != entry_id_2

    @pytest.mark.asyncio
    async def test_prune_redo_branch_on_new_change(
        self, undo_redo_service, sample_tasks, modified_tasks, test_db
    ):
        """Test that new changes after undo prune the redo branch."""
        project_id = "proj_001"
        org_id = "org_001"
        user_id = "user_001"

        # Capture 3 snapshots
        await undo_redo_service.capture_snapshot(
            project_id=project_id,
            org_id=org_id,
            user_id=user_id,
            change_type="SAVE_SCHEDULE",
            summary="V1",
            tasks=sample_tasks,
        )
        await undo_redo_service.capture_snapshot(
            project_id=project_id,
            org_id=org_id,
            user_id=user_id,
            change_type="SAVE_SCHEDULE",
            summary="V2",
            tasks=modified_tasks,
        )
        await undo_redo_service.capture_snapshot(
            project_id=project_id,
            org_id=org_id,
            user_id=user_id,
            change_type="SAVE_SCHEDULE",
            summary="V3",
            tasks=sample_tasks,
        )

        # Check stack size before undo
        initial_count = await undo_redo_service.repo.count_stack(project_id, org_id)
        assert initial_count == 3

        # Undo twice
        await undo_redo_service.undo(project_id, org_id, user_id)
        await undo_redo_service.undo(project_id, org_id, user_id)

        # Now create new change (should prune redo branch)
        another_modified = [t.copy() for t in sample_tasks]
        another_modified[0]["duration_days"] = 20
        await undo_redo_service.capture_snapshot(
            project_id=project_id,
            org_id=org_id,
            user_id=user_id,
            change_type="SAVE_SCHEDULE",
            summary="V2-New",
            tasks=another_modified,
        )

        # Stack should now be V1, V1->V2New (V3 pruned)
        final_count = await undo_redo_service.repo.count_stack(project_id, org_id)
        assert final_count == 2

    @pytest.mark.asyncio
    async def test_max_stack_depth_enforcement(self, undo_redo_service, sample_tasks):
        """Test that stack respects MAX_STACK_DEPTH limit."""
        project_id = "proj_001"
        org_id = "org_001"
        user_id = "user_001"

        # Capture MAX_STACK_DEPTH + 10 snapshots
        for i in range(undo_redo_service.MAX_STACK_DEPTH + 10):
            modified = [t.copy() for t in sample_tasks]
            modified[0]["duration_days"] = i
            await undo_redo_service.capture_snapshot(
                project_id=project_id,
                org_id=org_id,
                user_id=user_id,
                change_type="SAVE_SCHEDULE",
                summary=f"Change {i}",
                tasks=modified,
            )

        # Count should not exceed MAX_STACK_DEPTH
        count = await undo_redo_service.repo.count_stack(project_id, org_id)
        assert count == undo_redo_service.MAX_STACK_DEPTH


class TestUndoRedoOperations:
    """Test undo/redo stack operations."""

    @pytest.mark.asyncio
    async def test_undo_reverts_to_previous_state(
        self, undo_redo_service, sample_tasks, modified_tasks
    ):
        """Test that undo reverts to previous snapshot."""
        project_id = "proj_001"
        org_id = "org_001"
        user_id = "user_001"

        # Capture two snapshots
        await undo_redo_service.capture_snapshot(
            project_id=project_id,
            org_id=org_id,
            user_id=user_id,
            change_type="SAVE_SCHEDULE",
            summary="Initial",
            tasks=sample_tasks,
        )
        await undo_redo_service.capture_snapshot(
            project_id=project_id,
            org_id=org_id,
            user_id=user_id,
            change_type="SAVE_SCHEDULE",
            summary="Modified",
            tasks=modified_tasks,
        )

        # Undo
        restored_tasks = await undo_redo_service.undo(project_id, org_id, user_id)

        # Should match original
        assert len(restored_tasks) == len(sample_tasks)
        assert restored_tasks[1]["duration_days"] == 10  # Original value

    @pytest.mark.asyncio
    async def test_undo_raises_error_at_oldest(
        self, undo_redo_service, sample_tasks
    ):
        """Test that undo raises error when at oldest state."""
        project_id = "proj_001"
        org_id = "org_001"
        user_id = "user_001"

        # Capture single snapshot
        await undo_redo_service.capture_snapshot(
            project_id=project_id,
            org_id=org_id,
            user_id=user_id,
            change_type="SAVE_SCHEDULE",
            summary="Initial",
            tasks=sample_tasks,
        )

        # Try to undo when at oldest
        with pytest.raises(ValidationError) as exc_info:
            await undo_redo_service.undo(project_id, org_id, user_id)

        assert "Nothing to undo" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_redo_restores_next_state(
        self, undo_redo_service, sample_tasks, modified_tasks
    ):
        """Test that redo restores next snapshot after undo."""
        project_id = "proj_001"
        org_id = "org_001"
        user_id = "user_001"

        # Capture two snapshots
        await undo_redo_service.capture_snapshot(
            project_id=project_id,
            org_id=org_id,
            user_id=user_id,
            change_type="SAVE_SCHEDULE",
            summary="Initial",
            tasks=sample_tasks,
        )
        await undo_redo_service.capture_snapshot(
            project_id=project_id,
            org_id=org_id,
            user_id=user_id,
            change_type="SAVE_SCHEDULE",
            summary="Modified",
            tasks=modified_tasks,
        )

        # Undo then Redo
        await undo_redo_service.undo(project_id, org_id, user_id)
        redone_tasks = await undo_redo_service.redo(project_id, org_id, user_id)

        # Should match modified
        assert redone_tasks[1]["duration_days"] == 15

    @pytest.mark.asyncio
    async def test_redo_raises_error_at_newest(
        self, undo_redo_service, sample_tasks
    ):
        """Test that redo raises error when at newest state."""
        project_id = "proj_001"
        org_id = "org_001"
        user_id = "user_001"

        # Capture single snapshot
        await undo_redo_service.capture_snapshot(
            project_id=project_id,
            org_id=org_id,
            user_id=user_id,
            change_type="SAVE_SCHEDULE",
            summary="Initial",
            tasks=sample_tasks,
        )

        # Try to redo when at newest
        with pytest.raises(ValidationError) as exc_info:
            await undo_redo_service.redo(project_id, org_id, user_id)

        assert "Nothing to redo" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_no_history_raises_error(self, undo_redo_service):
        """Test that undo/redo raise error when no history exists."""
        project_id = "proj_001"
        org_id = "org_001"
        user_id = "user_001"

        with pytest.raises(ValidationError) as exc_info:
            await undo_redo_service.undo(project_id, org_id, user_id)

        assert "No history available" in str(exc_info.value)


class TestHistoryQueries:
    """Test history listing and metadata queries."""

    @pytest.mark.asyncio
    async def test_list_history_returns_entries(
        self, undo_redo_service, sample_tasks, modified_tasks
    ):
        """Test that list_history returns all entries (newest first)."""
        project_id = "proj_001"
        org_id = "org_001"
        user_id = "user_001"

        # Capture snapshots
        await undo_redo_service.capture_snapshot(
            project_id=project_id,
            org_id=org_id,
            user_id=user_id,
            change_type="SAVE_SCHEDULE",
            summary="Initial",
            tasks=sample_tasks,
        )
        await undo_redo_service.capture_snapshot(
            project_id=project_id,
            org_id=org_id,
            user_id=user_id,
            change_type="SAVE_SCHEDULE",
            summary="Modified",
            tasks=modified_tasks,
        )

        # List history
        entries = await undo_redo_service.list_history(project_id, org_id)

        assert len(entries) == 2
        # Newest first
        assert entries[0]["summary"] == "Modified"
        assert entries[1]["summary"] == "Initial"
        # tasks_snapshot should NOT be included
        assert "tasks_snapshot" not in entries[0]

    @pytest.mark.asyncio
    async def test_get_stack_info_when_no_history(self, undo_redo_service):
        """Test get_stack_info when no history exists."""
        project_id = "proj_001"
        org_id = "org_001"

        info = await undo_redo_service.get_stack_info(project_id, org_id)

        assert info["current_version"] is None
        assert info["can_undo"] is False
        assert info["can_redo"] is False

    @pytest.mark.asyncio
    async def test_get_stack_info_with_history(
        self, undo_redo_service, sample_tasks, modified_tasks
    ):
        """Test get_stack_info with multiple history entries."""
        project_id = "proj_001"
        org_id = "org_001"
        user_id = "user_001"

        # Capture snapshots
        await undo_redo_service.capture_snapshot(
            project_id=project_id,
            org_id=org_id,
            user_id=user_id,
            change_type="SAVE_SCHEDULE",
            summary="Initial",
            tasks=sample_tasks,
        )
        await undo_redo_service.capture_snapshot(
            project_id=project_id,
            org_id=org_id,
            user_id=user_id,
            change_type="SAVE_SCHEDULE",
            summary="Modified",
            tasks=modified_tasks,
        )
        await undo_redo_service.capture_snapshot(
            project_id=project_id,
            org_id=org_id,
            user_id=user_id,
            change_type="SAVE_SCHEDULE",
            summary="Final",
            tasks=sample_tasks,
        )

        # Get stack info (at newest)
        info = await undo_redo_service.get_stack_info(project_id, org_id)

        assert info["current_version"] is not None
        assert info["summary"] == "Final"
        assert info["can_undo"] is True
        assert info["can_redo"] is False

        # Undo
        await undo_redo_service.undo(project_id, org_id, user_id)
        info = await undo_redo_service.get_stack_info(project_id, org_id)

        assert info["summary"] == "Modified"
        assert info["can_undo"] is True
        assert info["can_redo"] is True

    @pytest.mark.asyncio
    async def test_restore_to_specific_version(
        self, undo_redo_service, sample_tasks, modified_tasks
    ):
        """Test restore_to jumps to specific history point."""
        project_id = "proj_001"
        org_id = "org_001"
        user_id = "user_001"

        # Capture snapshots
        entry_id_1 = await undo_redo_service.capture_snapshot(
            project_id=project_id,
            org_id=org_id,
            user_id=user_id,
            change_type="SAVE_SCHEDULE",
            summary="V1",
            tasks=sample_tasks,
        )
        await undo_redo_service.capture_snapshot(
            project_id=project_id,
            org_id=org_id,
            user_id=user_id,
            change_type="SAVE_SCHEDULE",
            summary="V2",
            tasks=modified_tasks,
        )
        another_modified = [t.copy() for t in sample_tasks]
        another_modified[2]["duration_days"] = 20
        await undo_redo_service.capture_snapshot(
            project_id=project_id,
            org_id=org_id,
            user_id=user_id,
            change_type="SAVE_SCHEDULE",
            summary="V3",
            tasks=another_modified,
        )

        # Restore to V1
        restored_tasks = await undo_redo_service.restore_to(
            project_id, org_id, user_id, entry_id_1
        )

        assert len(restored_tasks) == len(sample_tasks)
        assert restored_tasks[1]["duration_days"] == 10  # V1 value


class TestFrozenStateValidation:
    """Test state machine constraint validation during undo/redo."""

    @pytest.mark.asyncio
    async def test_frozen_state_revert_blocked(
        self, undo_redo_service, sample_tasks
    ):
        """Test that reverting frozen task status is blocked."""
        project_id = "proj_001"
        org_id = "org_001"
        user_id = "user_001"

        # Initial state
        await undo_redo_service.capture_snapshot(
            project_id=project_id,
            org_id=org_id,
            user_id=user_id,
            change_type="SAVE_SCHEDULE",
            summary="Initial",
            tasks=sample_tasks,
        )

        # Move to frozen state
        frozen_tasks = [t.copy() for t in sample_tasks]
        frozen_tasks[0]["status"] = "Completed"
        await undo_redo_service.capture_snapshot(
            project_id=project_id,
            org_id=org_id,
            user_id=user_id,
            change_type="SAVE_SCHEDULE",
            summary="Task completed",
            tasks=frozen_tasks,
        )

        # Try to undo (should fail)
        with pytest.raises(ValidationError) as exc_info:
            await undo_redo_service.undo(project_id, org_id, user_id)

        assert "Cannot undo/redo" in str(exc_info.value)


class TestChecksum:
    """Test checksum computation for deduplication."""

    @pytest.mark.asyncio
    async def test_checksum_deterministic(self, sample_tasks):
        """Test that checksum is deterministic."""
        checksum_1 = UndoRedoService._compute_checksum(sample_tasks)
        checksum_2 = UndoRedoService._compute_checksum(sample_tasks)

        assert checksum_1 == checksum_2

    @pytest.mark.asyncio
    async def test_checksum_differs_for_changes(self, sample_tasks, modified_tasks):
        """Test that checksum differs for different data."""
        checksum_1 = UndoRedoService._compute_checksum(sample_tasks)
        checksum_2 = UndoRedoService._compute_checksum(modified_tasks)

        assert checksum_1 != checksum_2
