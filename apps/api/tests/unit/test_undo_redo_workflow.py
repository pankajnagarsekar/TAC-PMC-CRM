"""
End-to-End Workflow Test for Undo/Redo System
Validates the complete lifecycle of undo/redo operations with scheduler integration.
"""
import pytest
from app.modules.project.application.undo_redo_service import UndoRedoService
from app.modules.project.application.scheduler_service import SchedulerService


@pytest.fixture
async def workflow_service(test_db):
    """Fixture with both scheduler and undo/redo services."""
    undo_redo = UndoRedoService(test_db)
    scheduler = SchedulerService(test_db, undo_redo_service=undo_redo)
    return {"scheduler": scheduler, "undo_redo": undo_redo}


class TestCompleteWorkflow:
    """Test complete undo/redo workflow."""

    @pytest.mark.asyncio
    async def test_full_edit_undo_redo_cycle(self, workflow_service):
        """Test complete workflow: save -> modify -> undo -> redo."""
        scheduler = workflow_service["scheduler"]
        undo_redo = workflow_service["undo_redo"]

        project_id = "proj_workflow_001"
        org_id = "org_001"
        user_id = "user_001"

        # Step 1: Save initial schedule
        initial_schedule = {
            "tasks": [
                {
                    "task_id": "task_1",
                    "task_name": "Foundation",
                    "status": "Open",
                    "duration_days": 5,
                    "predecessors": [],
                },
                {
                    "task_id": "task_2",
                    "task_name": "Framing",
                    "status": "Open",
                    "duration_days": 10,
                    "predecessors": ["task_1"],
                },
            ],
            "project_start": "2026-05-01",
        }

        await scheduler.save_schedule(
            project_id, org_id, user_id, initial_schedule
        )

        # Verify initial state
        stack_info = await undo_redo.get_stack_info(project_id, org_id)
        assert stack_info["can_undo"] is False
        assert stack_info["can_redo"] is False
        assert "Initial" not in stack_info.get("summary", "")

        # Step 2: Modify and save
        modified_schedule = initial_schedule.copy()
        modified_schedule["tasks"] = [t.copy() for t in initial_schedule["tasks"]]
        modified_schedule["tasks"][0]["duration_days"] = 10

        await scheduler.save_schedule(
            project_id, org_id, user_id, modified_schedule
        )

        # Verify can undo but not redo
        stack_info = await undo_redo.get_stack_info(project_id, org_id)
        assert stack_info["can_undo"] is True
        assert stack_info["can_redo"] is False

        # Step 3: Undo the modification
        undone_tasks = await undo_redo.undo(project_id, org_id, user_id)
        assert undone_tasks[0]["duration_days"] == 5

        # Verify can redo now
        stack_info = await undo_redo.get_stack_info(project_id, org_id)
        assert stack_info["can_undo"] is False
        assert stack_info["can_redo"] is True

        # Step 4: Redo the modification
        redone_tasks = await undo_redo.redo(project_id, org_id, user_id)
        assert redone_tasks[0]["duration_days"] == 10

        # Verify back to undo-able state
        stack_info = await undo_redo.get_stack_info(project_id, org_id)
        assert stack_info["can_undo"] is True
        assert stack_info["can_redo"] is False

    @pytest.mark.asyncio
    async def test_multiple_changes_with_branching(self, workflow_service):
        """Test that creating new changes after undo prunes redo branch."""
        scheduler = workflow_service["scheduler"]
        undo_redo = workflow_service["undo_redo"]

        project_id = "proj_branch_001"
        org_id = "org_001"
        user_id = "user_001"

        base_schedule = {
            "tasks": [
                {"task_id": "t1", "task_name": "A", "duration_days": 5},
                {"task_id": "t2", "task_name": "B", "duration_days": 10},
            ],
            "project_start": "2026-05-01",
        }

        # Create a chain: A(5) -> B(10,5) -> C(20) -> D(25)
        for i, (name, duration) in enumerate(
            [("Original", 5), ("Mod1", 10), ("Mod2", 20), ("Mod3", 25)]
        ):
            schedule = base_schedule.copy()
            schedule["tasks"] = [t.copy() for t in base_schedule["tasks"]]
            schedule["tasks"][0]["duration_days"] = duration
            await scheduler.save_schedule(project_id, org_id, user_id, schedule)

        # Verify we have 4 entries
        history = await undo_redo.list_history(project_id, org_id)
        assert len(history) == 4

        # Undo 2 steps (back to Mod1)
        await undo_redo.undo(project_id, org_id, user_id)
        await undo_redo.undo(project_id, org_id, user_id)

        history = await undo_redo.list_history(project_id, org_id)
        assert len(history) == 4  # Still have all entries

        # Create a new branch
        new_schedule = base_schedule.copy()
        new_schedule["tasks"] = [t.copy() for t in base_schedule["tasks"]]
        new_schedule["tasks"][0]["duration_days"] = 15
        await scheduler.save_schedule(project_id, org_id, user_id, new_schedule)

        # Now we should have pruned the redo branch (Mod2, Mod3)
        # So we should have: Original, Mod1, New = 3 entries
        history = await undo_redo.list_history(project_id, org_id)
        assert len(history) == 3

    @pytest.mark.asyncio
    async def test_history_list_formatting(self, workflow_service):
        """Test that history list returns properly formatted entries without snapshots."""
        scheduler = workflow_service["scheduler"]
        undo_redo = workflow_service["undo_redo"]

        project_id = "proj_history_001"
        org_id = "org_001"
        user_id = "user_001"

        schedule = {
            "tasks": [{"task_id": "t1", "task_name": "A", "duration_days": 5}],
            "project_start": "2026-05-01",
        }

        await scheduler.save_schedule(project_id, org_id, user_id, schedule)

        # Get history
        history = await undo_redo.list_history(project_id, org_id)

        assert len(history) == 1
        entry = history[0]

        # Verify required fields are present
        assert "id" in entry
        assert "change_type" in entry
        assert "summary" in entry
        assert "captured_by" in entry
        assert "captured_at" in entry
        assert "stack_position" in entry
        assert "is_current" in entry

        # Verify snapshot is NOT included (too heavy for list view)
        assert "tasks_snapshot" not in entry

    @pytest.mark.asyncio
    async def test_restore_creates_restore_snapshot(self, workflow_service):
        """Test that restore_to creates a new RESTORE snapshot."""
        scheduler = workflow_service["scheduler"]
        undo_redo = workflow_service["undo_redo"]

        project_id = "proj_restore_snap"
        org_id = "org_001"
        user_id = "user_001"

        base_schedule = {
            "tasks": [{"task_id": "t1", "task_name": "A", "duration_days": 5}],
            "project_start": "2026-05-01",
        }

        # Create multiple versions
        for duration in [5, 10, 15, 20]:
            schedule = base_schedule.copy()
            schedule["tasks"] = [t.copy() for t in base_schedule["tasks"]]
            schedule["tasks"][0]["duration_days"] = duration
            await scheduler.save_schedule(project_id, org_id, user_id, schedule)

        # Get the first entry ID
        history = await undo_redo.list_history(project_id, org_id)
        first_id = None
        for entry in reversed(history):
            if entry["stack_position"] == 0:
                first_id = entry["id"]
                break

        assert first_id is not None

        # Restore to first version
        await undo_redo.restore_to(project_id, org_id, user_id, first_id)

        # Check that a new RESTORE snapshot was created
        updated_history = await undo_redo.list_history(project_id, org_id)
        latest = updated_history[0]

        assert latest["change_type"] == "RESTORE"
        assert "Restored to" in latest["summary"]
