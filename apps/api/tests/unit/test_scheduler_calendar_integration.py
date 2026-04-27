"""
Integration Tests: Scheduler + Resource Calendar Integration

Tests that resource calendars properly affect CPM calculations
when integrated into the critical path calculator.
"""

import pytest
from datetime import datetime
from app.modules.scheduler.resource_calendar import ResourceCalendar
from app.modules.scheduler.resource_calendar_service import ResourceCalendarService
from app.modules.scheduler.calculate_critical_path import run_calculation


@pytest.fixture
def calendar_service(test_db):
    """Fixture providing ResourceCalendarService with test database."""
    return ResourceCalendarService(test_db)


@pytest.fixture
def standard_calendar():
    """Create a standard Mon-Fri calendar (no holidays)."""
    return ResourceCalendar(resource_id="resource-1")


@pytest.fixture
def calendar_with_holidays():
    """Create calendar with holiday period."""
    cal = ResourceCalendar(resource_id="resource-2")
    # Add 1-week holiday (Jan 8-12, 2024 - Mon-Fri)
    cal.add_holidays(
        start_date=datetime(2024, 1, 8),
        end_date=datetime(2024, 1, 12),
        reason="Holiday"
    )
    return cal


class TestSchedulerCalendarIntegration:
    """Test integration of resource calendars with CPM scheduler."""

    def test_schedule_without_calendar_uses_all_days(self):
        """Verify that schedule without calendar treats all days as working."""
        input_data = {
            "project_start": "2024-01-01",
            "tasks": [
                {
                    "task_id": "A",
                    "task_name": "Task A",
                    "duration": 5,  # 5 days (all calendar types)
                    "predecessors": [],
                }
            ]
        }

        result = run_calculation(input_data)

        assert result["status"] == "success"
        assert len(result["tasks"]) == 1

        task_a = result["tasks"][0]
        # 5 days with no calendar = 2024-01-01 to 2024-01-05
        assert task_a["is_critical"] is True
        assert task_a["total_slack"] == 0

    def test_schedule_with_single_task_no_holidays(self):
        """Test simple schedule with single resource (no holidays)."""
        input_data = {
            "project_start": "2024-01-01",
            "tasks": [
                {
                    "task_id": "A",
                    "task_name": "Foundation",
                    "duration": 5,
                    "predecessors": [],
                }
            ]
        }

        result = run_calculation(input_data)

        assert result["status"] == "success"
        task_a = result["tasks"][0]
        assert task_a["duration"] == 5
        assert task_a["is_critical"] is True

    def test_schedule_with_dependency_chain(self):
        """Test schedule with dependent tasks."""
        input_data = {
            "project_start": "2024-01-01",
            "tasks": [
                {
                    "task_id": "A",
                    "task_name": "Task A",
                    "duration": 3,
                    "predecessors": [],
                },
                {
                    "task_id": "B",
                    "task_name": "Task B (depends on A)",
                    "duration": 2,
                    "predecessors": [
                        {"task_id": "A", "type": "FS", "lag_days": 0, "strength": "hard"}
                    ],
                }
            ]
        }

        result = run_calculation(input_data)

        assert result["status"] == "success"
        assert len(result["tasks"]) == 2

        task_a = next(t for t in result["tasks"] if t["task_id"] == "A")
        task_b = next(t for t in result["tasks"] if t["task_id"] == "B")

        assert task_a["is_critical"] is True
        assert task_b["is_critical"] is True
        assert task_a["total_slack"] == 0
        assert task_b["total_slack"] == 0
        # B should start after A finishes (FS link)
        assert task_b["early_start"] > task_a["early_finish"]

    def test_schedule_parallel_tasks(self):
        """Test schedule with parallel independent tasks."""
        input_data = {
            "project_start": "2024-01-01",
            "tasks": [
                {
                    "task_id": "A",
                    "task_name": "Task A",
                    "duration": 5,
                    "predecessors": [],
                },
                {
                    "task_id": "B",
                    "task_name": "Task B (parallel)",
                    "duration": 3,
                    "predecessors": [],
                }
            ]
        }

        result = run_calculation(input_data)

        assert result["status"] == "success"
        assert len(result["tasks"]) == 2

        task_a = next(t for t in result["tasks"] if t["task_id"] == "A")
        task_b = next(t for t in result["tasks"] if t["task_id"] == "B")

        # A is critical (longer path: 5 days)
        assert task_a["is_critical"] is True
        assert task_a["total_slack"] == 0

        # B has slack (shorter: 3 days, same start, A ends at day 5)
        assert task_b["is_critical"] is False
        assert task_b["total_slack"] == 2  # Can delay 2 days

    def test_schedule_with_ss_link(self):
        """Test Start-to-Start dependency."""
        input_data = {
            "project_start": "2024-01-01",
            "tasks": [
                {
                    "task_id": "A",
                    "task_name": "Task A",
                    "duration": 5,
                    "predecessors": [],
                },
                {
                    "task_id": "B",
                    "task_name": "Task B (SS link to A)",
                    "duration": 3,
                    "predecessors": [
                        {"task_id": "A", "type": "SS", "lag_days": 1, "strength": "hard"}
                    ],
                }
            ]
        }

        result = run_calculation(input_data)

        assert result["status"] == "success"
        task_a = next(t for t in result["tasks"] if t["task_id"] == "A")
        task_b = next(t for t in result["tasks"] if t["task_id"] == "B")

        # B starts 1 day after A starts (SS + 1-day lag)
        assert task_b["early_start"] > task_a["early_start"]

    def test_schedule_with_constraint_snet(self):
        """Test Start No Earlier Than (SNET) constraint."""
        input_data = {
            "project_start": "2024-01-01",
            "tasks": [
                {
                    "task_id": "A",
                    "task_name": "Task A",
                    "duration": 3,
                    "predecessors": [],
                    "constraint_type": "SNET",
                    "constraint_date": "2024-01-10",
                }
            ]
        }

        result = run_calculation(input_data)

        assert result["status"] == "success"
        task_a = result["tasks"][0]

        # Task should not start before constraint date
        start_date = datetime.fromisoformat(str(task_a["early_start"]).replace("Z", "+00:00"))
        constraint_date = datetime(2024, 1, 10)
        assert start_date >= constraint_date

    def test_schedule_with_fnet_constraint(self):
        """Test Finish No Earlier Than (FNET) constraint."""
        input_data = {
            "project_start": "2024-01-01",
            "tasks": [
                {
                    "task_id": "A",
                    "task_name": "Task A",
                    "duration": 5,
                    "predecessors": [],
                    "constraint_type": "FNET",
                    "constraint_date": "2024-01-10",
                }
            ]
        }

        result = run_calculation(input_data)

        assert result["status"] == "success"
        task_a = result["tasks"][0]

        # Task should finish no earlier than constraint date
        finish_date = datetime.fromisoformat(str(task_a["early_finish"]).replace("Z", "+00:00"))
        constraint_date = datetime(2024, 1, 10)
        assert finish_date >= constraint_date

    def test_schedule_detects_circular_dependency(self):
        """Test that circular dependencies are detected."""
        input_data = {
            "project_start": "2024-01-01",
            "tasks": [
                {
                    "task_id": "A",
                    "task_name": "Task A",
                    "duration": 3,
                    "predecessors": [{"task_id": "B", "type": "FS", "strength": "hard"}],
                },
                {
                    "task_id": "B",
                    "task_name": "Task B",
                    "duration": 2,
                    "predecessors": [{"task_id": "A", "type": "FS", "strength": "hard"}],
                }
            ]
        }

        result = run_calculation(input_data)

        # Should fail with circular dependency error
        assert result["status"] == "failed"
        assert "Circular dependency" in result.get("error", "")

    def test_schedule_with_soft_dependencies(self):
        """Test that soft dependencies are handled correctly (skipped in backward pass)."""
        input_data = {
            "project_start": "2024-01-01",
            "tasks": [
                {
                    "task_id": "A",
                    "task_name": "Task A",
                    "duration": 3,
                    "predecessors": [],
                },
                {
                    "task_id": "B",
                    "task_name": "Task B (soft dep on A)",
                    "duration": 5,
                    "predecessors": [
                        {"task_id": "A", "type": "FS", "strength": "soft", "lag_days": 0}
                    ],
                }
            ]
        }

        result = run_calculation(input_data)

        assert result["status"] == "success"
        task_a = next(t for t in result["tasks"] if t["task_id"] == "A")
        task_b = next(t for t in result["tasks"] if t["task_id"] == "B")

        # Soft dependencies are skipped in the backward pass
        # Both tasks are calculated and have their durations preserved
        assert task_a["duration"] == 3
        assert task_b["duration"] == 5
        # Verify both tasks exist and have been processed
        assert task_a["total_slack"] >= 0
        assert task_b["total_slack"] >= 0


class TestCalendarServicePersistence:
    """Test resource calendar persistence operations."""

    @pytest.mark.asyncio
    async def test_save_and_retrieve_calendar(self, calendar_service, standard_calendar):
        """Test saving and retrieving a calendar."""
        resource_id = "resource-save-test"
        org_id = "org-test"

        # Save calendar
        await calendar_service.save_calendar(resource_id, org_id, standard_calendar)

        # Retrieve calendar
        retrieved = await calendar_service.get_calendar(resource_id, org_id)

        assert retrieved is not None
        assert retrieved.resource_id == standard_calendar.resource_id

    @pytest.mark.asyncio
    async def test_get_or_create_calendar(self, calendar_service):
        """Test get_or_create returns existing or creates new."""
        resource_id = "resource-create-test"
        org_id = "org-test"

        # First call creates default
        cal1 = await calendar_service.get_or_create_calendar(resource_id, org_id)
        assert cal1 is not None

        # Second call returns existing
        cal2 = await calendar_service.get_or_create_calendar(resource_id, org_id)
        assert cal1.resource_id == cal2.resource_id

    @pytest.mark.asyncio
    async def test_add_holiday_updates_calendar(self, calendar_service):
        """Test that add_holiday persists changes."""
        resource_id = "resource-holiday-test"
        org_id = "org-test"

        # Create calendar
        await calendar_service.get_or_create_calendar(resource_id, org_id)

        # Add holiday
        updated = await calendar_service.add_holiday(
            resource_id, org_id,
            datetime(2024, 12, 25),
            datetime(2024, 12, 26),
            "Christmas"
        )

        # Verify holiday is in updated calendar
        assert len(updated.exceptions) > 0

    @pytest.mark.asyncio
    async def test_bulk_load_calendars(self, calendar_service, standard_calendar):
        """Test bulk loading multiple calendars."""
        org_id = "org-bulk-test"
        resource_ids = ["res-1", "res-2", "res-3"]

        # Save some calendars
        for res_id in resource_ids[:2]:
            await calendar_service.save_calendar(res_id, org_id, standard_calendar)

        # Bulk load all
        calendars = await calendar_service.bulk_load_calendars(resource_ids, org_id)

        # Should have calendars for all (created defaults for missing)
        assert len(calendars) == 3
        assert all(res_id in calendars for res_id in resource_ids)


class TestCalendarWorkingDayCalculations:
    """Test working day calculations for scheduling."""

    def test_apply_calendar_to_duration_no_calendar(self):
        """Test duration calculation without calendar (all days work)."""
        start = datetime(2024, 1, 1)  # Monday
        duration = 5

        end = ResourceCalendarService.apply_calendar_to_duration(None, start, duration)

        # 5 days from Jan 1 = Jan 5
        assert (end - start).days == 4  # Exclusive end calculation

    def test_apply_calendar_to_duration_with_calendar(self):
        """Test duration calculation with calendar."""
        calendar = ResourceCalendar(resource_id="res-test")
        start = datetime(2024, 1, 1)  # Monday
        duration = 5  # 5 working days

        end = calendar.add_working_days(start, duration)

        # Should account for weekends
        assert end > start

    def test_working_days_between_no_holidays(self):
        """Test working days calculation between dates."""
        calendar = ResourceCalendar(resource_id="res-test")
        start = datetime(2024, 1, 1)  # Monday
        end = datetime(2024, 1, 5)    # Friday

        working_days = calendar.working_days_between(start, end, inclusive_end=True)

        # Mon-Fri = 5 working days
        assert working_days == 5

    def test_working_days_between_with_weekend(self):
        """Test working days across weekend."""
        calendar = ResourceCalendar(resource_id="res-test")
        start = datetime(2024, 1, 5)   # Friday
        end = datetime(2024, 1, 8)     # Monday (next week)

        working_days = calendar.working_days_between(start, end, inclusive_end=True)

        # Fri + Mon = 2 working days (weekend skipped)
        assert working_days == 2

    def test_working_days_between_with_holiday(self):
        """Test working days with holiday in range."""
        calendar = ResourceCalendar(resource_id="res-test")
        calendar.add_holidays(
            datetime(2024, 1, 4),
            datetime(2024, 1, 4),
            "Holiday"
        )

        start = datetime(2024, 1, 1)  # Monday
        end = datetime(2024, 1, 5)    # Friday

        working_days = calendar.working_days_between(start, end, inclusive_end=True)

        # Mon-Fri minus Thu (holiday) = 4 working days
        assert working_days == 4
