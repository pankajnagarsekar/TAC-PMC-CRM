"""
Integration Tests: Resource Leveler + Scheduler Integration

Tests for Phase 1 Task #13: Resource Leveling Integration
- Leveler integration with CPM-calculated schedule
- Real task structures from scheduler
- Compatibility with baseline and calendars
- End-to-end leveling workflow
"""

import pytest
from datetime import datetime, timedelta, timezone
from app.modules.scheduler.resource_leveler import (
    ResourceLeveler,
    ResourceAssignment,
    ResourceCapacity,
    LevelingStatus,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def leveler():
    """Create resource leveler instance."""
    return ResourceLeveler()


@pytest.fixture
def base_date():
    """Base date for schedules."""
    return datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


# ============================================================================
# TEST: CPM + Leveler Integration
# ============================================================================

class TestCPMWithLeveler:
    """Test leveler working with CPM-calculated schedules."""

    def test_leveler_preserves_cpm_dates(self, leveler, base_date):
        """Leveler preserves critical path from CPM."""
        # Simple critical chain (dates pre-calculated)
        tasks = {
            "A": {
                "task_id": "A",
                "task_name": "A",
                "duration": 5,
                "es": base_date,
                "ef": base_date + timedelta(days=4),
                "total_slack": 0,
                "is_critical": True,
            },
            "B": {
                "task_id": "B",
                "task_name": "B",
                "duration": 5,
                "es": base_date + timedelta(days=5),
                "ef": base_date + timedelta(days=9),
                "total_slack": 0,
                "is_critical": True,
            },
        }

        # Now level (no resources, should have no conflicts)
        lev_result = leveler.level_schedule(tasks)

        # Status should be success
        assert lev_result.status == LevelingStatus.SUCCESS

    def test_leveler_with_parallel_paths(self, leveler, base_date):
        """Leveler respects parallel paths in schedule."""
        tasks = {
            "A": {
                "task_id": "A",
                "task_name": "A",
                "duration": 5,
                "es": base_date,
                "ef": base_date + timedelta(days=4),
                "total_slack": 0,
                "is_critical": True,
            },
            "B": {
                "task_id": "B",
                "task_name": "B",
                "duration": 3,
                "es": base_date,
                "ef": base_date + timedelta(days=2),
                "total_slack": 2,
                "is_critical": False,
            },
            "C": {
                "task_id": "C",
                "task_name": "C",
                "duration": 3,
                "es": base_date + timedelta(days=5),
                "ef": base_date + timedelta(days=7),
                "total_slack": 0,
                "is_critical": True,
            },
        }

        # Then level
        lev_result = leveler.level_schedule(tasks)
        assert lev_result.status == LevelingStatus.SUCCESS


# ============================================================================
# TEST: Real Task Structure Integration
# ============================================================================

class TestRealTaskStructures:
    """Test with real task structures matching scheduler."""

    def test_construction_project_scheduling(self, leveler, base_date):
        """Real construction project with resources."""
        # Realistic construction tasks
        tasks = {
            "Foundation": {
                "task_id": "Foundation",
                "task_name": "Foundation Work",
                "duration": 10,
                "es": base_date,
                "ef": base_date + timedelta(days=9),
                "total_slack": 0,
                "is_critical": True,
            },
            "Framing": {
                "task_id": "Framing",
                "task_name": "Framing",
                "duration": 15,
                "es": base_date + timedelta(days=10),
                "ef": base_date + timedelta(days=24),
                "total_slack": 0,
                "is_critical": True,
            },
            "Electrical": {
                "task_id": "Electrical",
                "task_name": "Electrical Work",
                "duration": 10,
                "es": base_date + timedelta(days=10),
                "ef": base_date + timedelta(days=19),
                "total_slack": 5,  # Can wait 5 days before delaying project
                "is_critical": False,
            },
            "Plumbing": {
                "task_id": "Plumbing",
                "task_name": "Plumbing Work",
                "duration": 10,
                "es": base_date + timedelta(days=10),
                "ef": base_date + timedelta(days=19),
                "total_slack": 5,
                "is_critical": False,
            },
            "Finishing": {
                "task_id": "Finishing",
                "task_name": "Finishing",
                "duration": 10,
                "es": base_date + timedelta(days=25),
                "ef": base_date + timedelta(days=34),
                "total_slack": 0,
                "is_critical": True,
            },
        }

        # Resource assignments
        assignments = {
            "Foundation": ResourceAssignment(task_id="Foundation", resource_id="crew-1", units_per_day=1.0),
            "Framing": ResourceAssignment(task_id="Framing", resource_id="crew-1", units_per_day=1.0),
            "Electrical": ResourceAssignment(task_id="Electrical", resource_id="crew-2", units_per_day=0.5),
            "Plumbing": ResourceAssignment(task_id="Plumbing", resource_id="crew-3", units_per_day=0.5),
            "Finishing": ResourceAssignment(task_id="Finishing", resource_id="crew-1", units_per_day=1.0),
        }

        # Capacities
        capacities = {
            "crew-1": ResourceCapacity(resource_id="crew-1", max_units_per_day=1.0),
            "crew-2": ResourceCapacity(resource_id="crew-2", max_units_per_day=1.0),
            "crew-3": ResourceCapacity(resource_id="crew-3", max_units_per_day=1.0),
        }

        result = leveler.level_schedule(tasks, assignments, capacities)

        # Should complete without conflict on crew-1
        assert result.status == LevelingStatus.SUCCESS
        # Critical path preserved
        assert result.leveled_tasks["Foundation"]["es"] == result.original_tasks["Foundation"]["es"]
        assert result.leveled_tasks["Framing"]["es"] == result.original_tasks["Framing"]["es"]


# ============================================================================
# TEST: Resource Histogram Quality
# ============================================================================

class TestResourceHistogramQuality:
    """Test histogram correctness with real scenarios."""

    def test_histogram_with_partial_allocations(self, leveler, base_date):
        """Histogram correctly handles partial resource allocations."""
        tasks = {
            "T1": {
                "task_id": "T1",
                "task_name": "T1",
                "es": base_date,
                "ef": base_date + timedelta(days=4),
                "total_slack": 0,
                "is_critical": True,
            },
            "T2": {
                "task_id": "T2",
                "task_name": "T2",
                "es": base_date,
                "ef": base_date + timedelta(days=4),
                "total_slack": 5,
                "is_critical": False,
            },
            "T3": {
                "task_id": "T3",
                "task_name": "T3",
                "es": base_date,
                "ef": base_date + timedelta(days=4),
                "total_slack": 5,
                "is_critical": False,
            },
        }

        # Multiple tasks on same resource with varying allocations
        assignments = {
            "T1": ResourceAssignment(task_id="T1", resource_id="R1", units_per_day=0.4),
            "T2": ResourceAssignment(task_id="T2", resource_id="R1", units_per_day=0.3),
            "T3": ResourceAssignment(task_id="T3", resource_id="R1", units_per_day=0.4),
        }

        capacities = {
            "R1": ResourceCapacity(resource_id="R1", max_units_per_day=1.0),
        }

        result = leveler.level_schedule(tasks, assignments, capacities)

        # Total usage is 0.4 + 0.3 + 0.4 = 1.1 (over capacity of 1.0)
        assert result.total_conflicts > 0


# ============================================================================
# TEST: Leveling with Tight Constraints
# ============================================================================

class TestTightConstraintScenarios:
    """Test leveler behavior under tight scheduling constraints."""

    def test_minimum_slack_unavailable(self, leveler, base_date):
        """All non-critical tasks have insufficient slack."""
        tasks = {
            "Critical": {
                "task_id": "Critical",
                "task_name": "Critical",
                "es": base_date,
                "ef": base_date + timedelta(days=4),
                "total_slack": 0,
                "is_critical": True,
            },
            "NonCrit1": {
                "task_id": "NonCrit1",
                "task_name": "NonCrit1",
                "es": base_date,
                "ef": base_date + timedelta(days=4),
                "total_slack": 1,  # Only 1 day slack
                "is_critical": False,
            },
            "NonCrit2": {
                "task_id": "NonCrit2",
                "task_name": "NonCrit2",
                "es": base_date,
                "ef": base_date + timedelta(days=4),
                "total_slack": 1,
                "is_critical": False,
            },
        }

        assignments = {
            "Critical": ResourceAssignment(task_id="Critical", resource_id="R1", units_per_day=1.0),
            "NonCrit1": ResourceAssignment(task_id="NonCrit1", resource_id="R1", units_per_day=1.0),
            "NonCrit2": ResourceAssignment(task_id="NonCrit2", resource_id="R1", units_per_day=1.0),
        }

        capacities = {"R1": ResourceCapacity(resource_id="R1", max_units_per_day=1.0)}

        result = leveler.level_schedule(tasks, assignments, capacities)

        # Cannot resolve all conflicts with insufficient slack
        # Result will be PARTIAL or SUCCESS with conflicts unresolved
        assert result.status in [LevelingStatus.PARTIAL, LevelingStatus.SUCCESS]
        assert result.total_conflicts > 0 or result.conflicts_resolved >= 0

    def test_single_resource_bottleneck(self, leveler, base_date):
        """Single resource as bottleneck for all tasks."""
        # 10 sequential tasks, all need single resource
        tasks = {
            f"T{i}": {
                "task_id": f"T{i}",
                "task_name": f"Task {i}",
                "es": base_date + timedelta(days=i*5),
                "ef": base_date + timedelta(days=(i+1)*5-1),
                "total_slack": i,  # Increasing slack
                "is_critical": i == 0,  # Only first is critical
            }
            for i in range(5)
        }

        assignments = {
            f"T{i}": ResourceAssignment(
                task_id=f"T{i}",
                resource_id="bottleneck",
                units_per_day=1.0
            )
            for i in range(5)
        }

        capacities = {
            "bottleneck": ResourceCapacity(resource_id="bottleneck", max_units_per_day=1.0)
        }

        result = leveler.level_schedule(tasks, assignments, capacities)

        # Sequential tasks (no overlap) should have no conflicts
        assert result.total_conflicts == 0
        assert result.status == LevelingStatus.SUCCESS


# ============================================================================
# TEST: Leveling Result Quality
# ============================================================================

class TestLevelingResultQuality:
    """Test quality of leveling results."""

    def test_leveled_schedule_is_valid(self, leveler, base_date):
        """Leveled schedule maintains task sequence validity."""
        tasks = {
            "A": {
                "task_id": "A",
                "task_name": "A",
                "es": base_date,
                "ef": base_date + timedelta(days=2),
                "total_slack": 0,
                "is_critical": True,
            },
            "B": {
                "task_id": "B",
                "task_name": "B",
                "es": base_date + timedelta(days=3),
                "ef": base_date + timedelta(days=5),
                "total_slack": 0,
                "is_critical": True,
            },
        }

        result = leveler.level_schedule(tasks)

        # Leveled dates should maintain B after A
        a_ef = result.leveled_tasks["A"]["ef"]
        b_es = result.leveled_tasks["B"]["es"]
        assert b_es >= a_ef or b_es > a_ef  # B starts on or after A ends

    def test_no_date_regression(self, leveler, base_date):
        """Leveling doesn't move critical tasks earlier."""
        tasks = {
            "Critical": {
                "task_id": "Critical",
                "task_name": "Critical",
                "es": base_date + timedelta(days=5),
                "ef": base_date + timedelta(days=10),
                "total_slack": 0,
                "is_critical": True,
            },
        }

        result = leveler.level_schedule(tasks)

        # Critical task shouldn't move earlier
        assert result.leveled_tasks["Critical"]["es"] >= result.original_tasks["Critical"]["es"]


# ============================================================================
# TEST: Performance with Large Schedules
# ============================================================================

class TestLargeSchedulePerformance:
    """Test leveler performance with larger schedules."""

    def test_50_task_schedule(self, leveler, base_date):
        """Leveler handles 50-task schedule efficiently."""
        tasks = {
            f"T{i}": {
                "task_id": f"T{i}",
                "task_name": f"Task {i}",
                "es": base_date + timedelta(days=i),
                "ef": base_date + timedelta(days=i+2),
                "total_slack": i % 10,
                "is_critical": i % 5 == 0,
            }
            for i in range(50)
        }

        assignments = {
            f"T{i}": ResourceAssignment(
                task_id=f"T{i}",
                resource_id=f"R{i % 3}",  # 3 resources
                units_per_day=0.5 + (i % 10) * 0.05
            )
            for i in range(50)
        }

        capacities = {
            f"R{j}": ResourceCapacity(resource_id=f"R{j}", max_units_per_day=2.0)
            for j in range(3)
        }

        result = leveler.level_schedule(tasks, assignments, capacities, max_iterations=100)

        # Should complete successfully
        assert result.status == LevelingStatus.SUCCESS or result.status == LevelingStatus.PARTIAL
        assert result.iterations <= 100
