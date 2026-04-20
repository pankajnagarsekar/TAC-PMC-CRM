"""
Integration tests for Undo/Redo API endpoints with Scheduler Service
Tests full workflow including API endpoints and snapshot capture on scheduler operations.
"""
import pytest
from httpx import AsyncClient
from app.modules.project.application.scheduler_service import SchedulerService
from app.modules.project.application.undo_redo_service import UndoRedoService


@pytest.fixture
async def undo_redo_service(test_db):
    """Fixture providing UndoRedoService."""
    return UndoRedoService(test_db)


@pytest.fixture
async def scheduler_service(test_db, undo_redo_service):
    """Fixture providing SchedulerService with UndoRedoService."""
    return SchedulerService(test_db, undo_redo_service=undo_redo_service)


@pytest.fixture
async def sample_schedule():
    """Sample schedule for testing."""
    return {
        "tasks": [
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
        ],
        "project_start": "2026-05-01",
    }


class TestUndoRedoAPIEndpoints:
    """Test undo/redo API endpoints."""

    @pytest.mark.asyncio
    async def test_list_history_endpoint(self, client, sample_schedule, test_db):
        """Test GET /scheduler/{project_id}/history endpoint."""
        project_id = "test-project-123"
        org_id = "test-org-123"
        user_id = "test-user-123"

        # Setup: Save schedule to create history
        scheduler_service = SchedulerService(
            test_db, undo_redo_service=UndoRedoService(test_db)
        )
        await scheduler_service.save_schedule(
            project_id, org_id, user_id, sample_schedule
        )

        # Get history
        response = await client.get(
            f"/api/v1/scheduler/{project_id}/history",
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]) >= 1

    @pytest.mark.asyncio
    async def test_stack_info_endpoint(self, client, sample_schedule, test_db):
        """Test GET /scheduler/{project_id}/history/stack-info endpoint."""
        project_id = "test-project-456"
        org_id = "test-org-123"
        user_id = "test-user-123"

        # Setup: Save schedule
        scheduler_service = SchedulerService(
            test_db, undo_redo_service=UndoRedoService(test_db)
        )
        await scheduler_service.save_schedule(
            project_id, org_id, user_id, sample_schedule
        )

        # Get stack info
        response = await client.get(
            f"/api/v1/scheduler/{project_id}/history/stack-info",
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        info = data["data"]
        assert "current_position" in info
        assert "can_undo" in info
        assert "can_redo" in info

    @pytest.mark.asyncio
    async def test_undo_endpoint(self, client, sample_schedule, test_db):
        """Test POST /scheduler/{project_id}/undo endpoint."""
        project_id = "test-project-789"
        org_id = "test-org-123"
        user_id = "test-user-123"

        # Setup: Save multiple versions
        scheduler_service = SchedulerService(
            test_db, undo_redo_service=UndoRedoService(test_db)
        )
        await scheduler_service.save_schedule(
            project_id, org_id, user_id, sample_schedule
        )

        # Modify and save again
        modified_schedule = sample_schedule.copy()
        modified_schedule["tasks"] = [t.copy() for t in sample_schedule["tasks"]]
        modified_schedule["tasks"][0]["duration_days"] = 10
        await scheduler_service.save_schedule(
            project_id, org_id, user_id, modified_schedule
        )

        # Undo
        response = await client.post(
            f"/api/v1/scheduler/{project_id}/undo",
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "tasks" in data["data"]
        # Should be back to original duration
        assert data["data"]["tasks"][0]["duration_days"] == 5

    @pytest.mark.asyncio
    async def test_redo_endpoint(self, client, sample_schedule, test_db):
        """Test POST /scheduler/{project_id}/redo endpoint."""
        project_id = "test-project-999"
        org_id = "test-org-123"
        user_id = "test-user-123"

        # Setup: Save multiple versions
        scheduler_service = SchedulerService(
            test_db, undo_redo_service=UndoRedoService(test_db)
        )
        await scheduler_service.save_schedule(
            project_id, org_id, user_id, sample_schedule
        )

        modified_schedule = sample_schedule.copy()
        modified_schedule["tasks"] = [t.copy() for t in sample_schedule["tasks"]]
        modified_schedule["tasks"][0]["duration_days"] = 10
        await scheduler_service.save_schedule(
            project_id, org_id, user_id, modified_schedule
        )

        # Undo then Redo
        await client.post(
            f"/api/v1/scheduler/{project_id}/undo",
            headers={"Authorization": "Bearer test-token"},
        )
        response = await client.post(
            f"/api/v1/scheduler/{project_id}/redo",
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        # Should be back to modified duration
        assert data["data"]["tasks"][0]["duration_days"] == 10

    @pytest.mark.asyncio
    async def test_restore_to_version_endpoint(self, client, sample_schedule, test_db):
        """Test POST /scheduler/{project_id}/history/{change_id}/restore endpoint."""
        project_id = "test-project-restore"
        org_id = "test-org-123"
        user_id = "test-user-123"

        # Setup: Save multiple versions and get change IDs
        undo_redo_service = UndoRedoService(test_db)
        scheduler_service = SchedulerService(
            test_db, undo_redo_service=undo_redo_service
        )
        await scheduler_service.save_schedule(
            project_id, org_id, user_id, sample_schedule
        )

        # Get the initial change ID
        history = await undo_redo_service.list_history(project_id, org_id)
        initial_change_id = history[0]["id"]

        # Create more changes
        for i in range(2):
            modified = sample_schedule.copy()
            modified["tasks"] = [t.copy() for t in sample_schedule["tasks"]]
            modified["tasks"][0]["duration_days"] = 5 + (i + 1) * 5
            await scheduler_service.save_schedule(
                project_id, org_id, user_id, modified
            )

        # Restore to initial
        response = await client.post(
            f"/api/v1/scheduler/{project_id}/history/{initial_change_id}/restore",
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        # Should be back to original duration
        assert data["data"]["tasks"][0]["duration_days"] == 5


class TestSchedulerServiceSnapshotIntegration:
    """Test snapshot capture integration with scheduler service."""

    @pytest.mark.asyncio
    async def test_save_schedule_captures_snapshot(
        self, test_db, sample_schedule
    ):
        """Test that save_schedule captures undo/redo snapshot."""
        project_id = "test-project-snap-1"
        org_id = "test-org-123"
        user_id = "test-user-123"

        scheduler_service = SchedulerService(
            test_db, undo_redo_service=UndoRedoService(test_db)
        )

        # Save schedule
        await scheduler_service.save_schedule(
            project_id, org_id, user_id, sample_schedule
        )

        # Check history was created
        history = await scheduler_service.undo_redo_service.list_history(
            project_id, org_id
        )
        assert len(history) == 1
        assert history[0]["change_type"] == "SAVE_SCHEDULE"

    @pytest.mark.asyncio
    async def test_delete_task_captures_snapshot(
        self, test_db, sample_schedule
    ):
        """Test that delete_task captures undo/redo snapshot."""
        project_id = "test-project-delete"
        org_id = "test-org-123"
        user_id = "test-user-123"

        scheduler_service = SchedulerService(
            test_db, undo_redo_service=UndoRedoService(test_db)
        )

        # Save initial schedule
        await scheduler_service.save_schedule(
            project_id, org_id, user_id, sample_schedule
        )

        # Delete a task
        await scheduler_service.delete_task(
            project_id, org_id, "task_1", user_id
        )

        # Check history has two entries
        history = await scheduler_service.undo_redo_service.list_history(
            project_id, org_id
        )
        assert len(history) == 2
        assert history[0]["change_type"] == "DELETE_TASK"
        assert history[1]["change_type"] == "SAVE_SCHEDULE"

    @pytest.mark.asyncio
    async def test_save_schedule_raw_skips_snapshot(
        self, test_db, sample_schedule
    ):
        """Test that save_schedule_raw does NOT capture snapshot."""
        project_id = "test-project-raw"
        org_id = "test-org-123"
        user_id = "test-user-123"

        scheduler_service = SchedulerService(
            test_db, undo_redo_service=UndoRedoService(test_db)
        )

        # Save using raw method (used by undo/redo internally)
        await scheduler_service.save_schedule_raw(
            project_id, org_id, user_id, sample_schedule
        )

        # Check history is empty (no snapshot should be created)
        history = await scheduler_service.undo_redo_service.list_history(
            project_id, org_id
        )
        assert len(history) == 0

    @pytest.mark.asyncio
    async def test_undo_redo_cycle_preserves_data(
        self, test_db, sample_schedule
    ):
        """Test complete undo/redo cycle preserves data integrity."""
        project_id = "test-project-cycle"
        org_id = "test-org-123"
        user_id = "test-user-123"

        scheduler_service = SchedulerService(
            test_db, undo_redo_service=UndoRedoService(test_db)
        )
        undo_redo_service = scheduler_service.undo_redo_service

        # Save initial
        await scheduler_service.save_schedule(
            project_id, org_id, user_id, sample_schedule
        )
        initial_tasks = sample_schedule["tasks"]

        # Modify and save
        modified_schedule = sample_schedule.copy()
        modified_schedule["tasks"] = [t.copy() for t in sample_schedule["tasks"]]
        modified_schedule["tasks"][0]["duration_days"] = 20
        await scheduler_service.save_schedule(
            project_id, org_id, user_id, modified_schedule
        )

        # Undo
        undone_tasks = await undo_redo_service.undo(project_id, org_id, user_id)
        assert undone_tasks[0]["duration_days"] == 5

        # Redo
        redone_tasks = await undo_redo_service.redo(project_id, org_id, user_id)
        assert redone_tasks[0]["duration_days"] == 20

        # Final state should match modified
        final_schedule = await scheduler_service.load_schedule(project_id, org_id)
        assert final_schedule["tasks"][0]["duration_days"] == 20
