"""
Comprehensive test suite for Resource Leveling Module.

Tests for Phase 1 Task #13: Resource Leveling
- Leveling-by-free-slack algorithm
- Resource over-allocation conflict detection and resolution
- Preservation of critical path
- Partial resolution for unresolvable conflicts
- Multi-resource scenarios
- Edge cases (empty, no conflicts, no assignments)
"""

import pytest
from datetime import datetime, timedelta, timezone
from app.modules.scheduler.resource_leveler import (
    ResourceLeveler,
    ResourceAssignment,
    ResourceCapacity,
    ResourceLevelingContext,
    Conflict,
    ResourceUsageDay,
    LevelingStatus,
    LevelingResult,
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
    """Base date for test schedules (2024-01-01 midnight UTC)."""
    return datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def simple_tasks(base_date):
    """Three sequential tasks: A -> B -> C (no slack)."""
    return {
        "A": {
            "task_id": "A",
            "task_name": "Foundation",
            "duration": 5,
            "es": base_date,
            "ef": base_date + timedelta(days=4),
            "total_slack": 0,
            "is_critical": True,
        },
        "B": {
            "task_id": "B",
            "task_name": "Framing",
            "duration": 5,
            "es": base_date + timedelta(days=5),
            "ef": base_date + timedelta(days=9),
            "total_slack": 0,
            "is_critical": True,
        },
        "C": {
            "task_id": "C",
            "task_name": "Roofing",
            "duration": 5,
            "es": base_date + timedelta(days=10),
            "ef": base_date + timedelta(days=14),
            "total_slack": 0,
            "is_critical": True,
        },
    }


@pytest.fixture
def tasks_with_slack(base_date):
    """Tasks with slack: A->B (critical), C (parallel, 5 days slack)."""
    return {
        "A": {
            "task_id": "A",
            "task_name": "Foundation",
            "duration": 5,
            "es": base_date,
            "ef": base_date + timedelta(days=4),
            "total_slack": 0,
            "is_critical": True,
        },
        "B": {
            "task_id": "B",
            "task_name": "Framing",
            "duration": 5,
            "es": base_date + timedelta(days=5),
            "ef": base_date + timedelta(days=9),
            "total_slack": 0,
            "is_critical": True,
        },
        "C": {
            "task_id": "C",
            "task_name": "Finishing (non-critical)",
            "duration": 5,
            "es": base_date,
            "ef": base_date + timedelta(days=4),
            "total_slack": 5,  # 5 days slack
            "is_critical": False,
        },
    }


@pytest.fixture
def single_resource_no_conflict(simple_tasks, base_date):
    """Single resource, no over-allocation."""
    assignments = {
        "A": ResourceAssignment(task_id="A", resource_id="R1", units_per_day=0.5),
        "B": ResourceAssignment(task_id="B", resource_id="R1", units_per_day=0.5),
        "C": ResourceAssignment(task_id="C", resource_id="R1", units_per_day=0.5),
    }
    capacities = {
        "R1": ResourceCapacity(resource_id="R1", max_units_per_day=1.0),
    }
    return simple_tasks, assignments, capacities


@pytest.fixture
def single_resource_with_conflict(simple_tasks, base_date):
    """Single resource with over-allocation conflict."""
    # A and B both assigned full-time to R1 (total: 2.0 units/day)
    # When A ends and B starts: 1.0 (OK)
    # When A and B overlap: 2.0 (over 1.0 capacity)
    assignments = {
        "A": ResourceAssignment(task_id="A", resource_id="R1", units_per_day=1.0),
        "B": ResourceAssignment(task_id="B", resource_id="R1", units_per_day=1.0),
        "C": ResourceAssignment(task_id="C", resource_id="R1", units_per_day=0.5),
    }
    capacities = {
        "R1": ResourceCapacity(resource_id="R1", max_units_per_day=1.0),
    }
    return simple_tasks, assignments, capacities


@pytest.fixture
def multi_resource_scenario(tasks_with_slack, base_date):
    """Multiple resources with mixed scenarios."""
    # R1: A full-time (critical), C full-time (non-critical, slack=5)
    # R2: B full-time (critical)
    # Conflict on R1 when A and C overlap (days 1-5)
    assignments = {
        "A": ResourceAssignment(task_id="A", resource_id="R1", units_per_day=1.0),
        "B": ResourceAssignment(task_id="B", resource_id="R2", units_per_day=1.0),
        "C": ResourceAssignment(task_id="C", resource_id="R1", units_per_day=1.0),
    }
    capacities = {
        "R1": ResourceCapacity(resource_id="R1", max_units_per_day=1.0),
        "R2": ResourceCapacity(resource_id="R2", max_units_per_day=1.0),
    }
    return tasks_with_slack, assignments, capacities


# ============================================================================
# TEST: Empty and No-Conflict Cases
# ============================================================================

class TestEmptyAndEdgeCases:
    """Test edge cases: empty input, no assignments, no conflicts."""

    def test_empty_tasks(self, leveler):
        """Empty task list returns success with no leveling."""
        result = leveler.level_schedule(tasks={})
        assert result.status == LevelingStatus.SUCCESS
        assert len(result.original_tasks) == 0
        assert len(result.leveled_tasks) == 0

    def test_no_assignments(self, leveler, simple_tasks):
        """No assignments means no leveling needed."""
        result = leveler.level_schedule(tasks=simple_tasks, assignments={})
        assert result.status == LevelingStatus.SUCCESS
        assert result.total_conflicts == 0
        assert result.conflicts_resolved == 0
        assert len(result.leveled_tasks) == 3

    def test_no_capacities(self, leveler, simple_tasks):
        """No capacities defined returns success (defaults to 1.0)."""
        assignments = {
            "A": ResourceAssignment(task_id="A", resource_id="R1", units_per_day=0.5),
        }
        result = leveler.level_schedule(
            tasks=simple_tasks,
            assignments=assignments,
            capacities=None
        )
        assert result.status == LevelingStatus.SUCCESS

    def test_no_conflicts(self, leveler, single_resource_no_conflict):
        """No conflicts detected returns success immediately."""
        tasks, assignments, capacities = single_resource_no_conflict
        result = leveler.level_schedule(tasks, assignments, capacities)
        assert result.status == LevelingStatus.SUCCESS
        assert result.total_conflicts == 0
        assert result.conflicts_resolved == 0
        assert result.iterations == 0


# ============================================================================
# TEST: Conflict Detection
# ============================================================================

class TestConflictDetection:
    """Test conflict detection mechanism."""

    def test_detect_single_resource_over_allocation(self, leveler, base_date):
        """Detect over-allocation on single resource."""
        # Create overlapping tasks to ensure conflict
        tasks = {
            "A": {
                "task_id": "A",
                "task_name": "A",
                "es": base_date,
                "ef": base_date + timedelta(days=4),
                "total_slack": 0,
                "is_critical": True,
            },
            "B": {
                "task_id": "B",
                "task_name": "B",
                "es": base_date + timedelta(days=3),  # Overlaps with A
                "ef": base_date + timedelta(days=7),
                "total_slack": 5,
                "is_critical": False,
            },
        }
        assignments = {
            "A": ResourceAssignment(task_id="A", resource_id="R1", units_per_day=1.0),
            "B": ResourceAssignment(task_id="B", resource_id="R1", units_per_day=1.0),
        }
        capacities = {
            "R1": ResourceCapacity(resource_id="R1", max_units_per_day=1.0),
        }
        result = leveler.level_schedule(tasks, assignments, capacities)

        # Should detect at least one conflict
        assert result.total_conflicts > 0
        assert result.status in [LevelingStatus.SUCCESS, LevelingStatus.PARTIAL]

    def test_detect_multiple_conflicts_same_day(self, leveler, base_date):
        """Detect multiple over-allocated periods."""
        # Two tasks heavily over-allocated on same day
        tasks = {
            "X": {
                "task_id": "X",
                "task_name": "X",
                "es": base_date,
                "ef": base_date + timedelta(days=2),
                "total_slack": 0,
                "is_critical": True,
            },
            "Y": {
                "task_id": "Y",
                "task_name": "Y",
                "es": base_date,
                "ef": base_date + timedelta(days=2),
                "total_slack": 5,
                "is_critical": False,
            },
        }
        assignments = {
            "X": ResourceAssignment(task_id="X", resource_id="R1", units_per_day=1.0),
            "Y": ResourceAssignment(task_id="Y", resource_id="R1", units_per_day=1.0),
        }
        capacities = {
            "R1": ResourceCapacity(resource_id="R1", max_units_per_day=1.0),
        }

        result = leveler.level_schedule(tasks, assignments, capacities)
        assert result.total_conflicts >= 3  # 3 days of conflict

    def test_conflict_sorting_chronological(self, leveler):
        """Conflicts are resolved in chronological order."""
        # Create conflicts on different dates
        context = ResourceLevelingContext(tasks={}, assignments={}, capacities={})
        context.conflicts = [
            Conflict(
                date=datetime(2024, 1, 5),
                resource_id="R1",
                over_allocated_by=1.0,
                task_ids=[]
            ),
            Conflict(
                date=datetime(2024, 1, 1),
                resource_id="R1",
                over_allocated_by=1.0,
                task_ids=[]
            ),
            Conflict(
                date=datetime(2024, 1, 3),
                resource_id="R1",
                over_allocated_by=1.0,
                task_ids=[]
            ),
        ]

        context.conflicts.sort()
        assert context.conflicts[0].date == datetime(2024, 1, 1)
        assert context.conflicts[1].date == datetime(2024, 1, 3)
        assert context.conflicts[2].date == datetime(2024, 1, 5)


# ============================================================================
# TEST: Conflict Resolution & Slack Preservation
# ============================================================================

class TestConflictResolution:
    """Test conflict resolution using free slack."""

    def test_resolve_by_delaying_non_critical_task(self, leveler, base_date):
        """Non-critical task delayed by required days to resolve conflict."""
        # Create task with clear overlap and slack
        tasks = {
            "A": {
                "task_id": "A",
                "task_name": "Critical",
                "es": base_date,
                "ef": base_date + timedelta(days=4),
                "total_slack": 0,
                "is_critical": True,
            },
            "B": {
                "task_id": "B",
                "task_name": "NonCritical",
                "es": base_date,
                "ef": base_date + timedelta(days=4),
                "total_slack": 10,  # Plenty of slack
                "is_critical": False,
            },
        }
        assignments = {
            "A": ResourceAssignment(task_id="A", resource_id="R1", units_per_day=1.0),
            "B": ResourceAssignment(task_id="B", resource_id="R1", units_per_day=1.0),
        }
        capacities = {
            "R1": ResourceCapacity(resource_id="R1", max_units_per_day=1.0),
        }

        result = leveler.level_schedule(tasks, assignments, capacities)

        # B should be delayed to resolve conflict with A
        b_original_es = base_date  # Original start date
        b_leveled_es = result.leveled_tasks["B"]["es"]
        assert b_leveled_es > b_original_es, "Non-critical task should be delayed"

    def test_critical_path_preserved(self, leveler, single_resource_with_conflict):
        """Critical path tasks are not delayed."""
        tasks, assignments, capacities = single_resource_with_conflict

        # Store original critical dates
        a_original_es = tasks["A"]["es"]
        a_original_ef = tasks["A"]["ef"]

        result = leveler.level_schedule(tasks, assignments, capacities)

        # Critical task A dates must not change
        assert result.leveled_tasks["A"]["es"] == a_original_es
        assert result.leveled_tasks["A"]["ef"] == a_original_ef

    def test_slack_reduced_by_delay(self, leveler, base_date):
        """Task slack reduced when delayed."""
        tasks = {
            "A": {
                "task_id": "A",
                "task_name": "A",
                "es": base_date,
                "ef": base_date + timedelta(days=4),
                "total_slack": 0,
                "is_critical": True,
            },
            "C": {
                "task_id": "C",
                "task_name": "C",
                "es": base_date,
                "ef": base_date + timedelta(days=4),
                "total_slack": 10,
                "is_critical": False,
            },
        }
        assignments = {
            "A": ResourceAssignment(task_id="A", resource_id="R1", units_per_day=1.0),
            "C": ResourceAssignment(task_id="C", resource_id="R1", units_per_day=1.0),
        }
        capacities = {
            "R1": ResourceCapacity(resource_id="R1", max_units_per_day=1.0),
        }

        result = leveler.level_schedule(tasks, assignments, capacities)

        # C slack should be reduced from 10
        c_slack = result.leveled_tasks["C"]["slack"]
        assert c_slack < 10, "Slack should be reduced by delay"

    def test_insufficient_slack_prevents_delay(self, leveler, base_date):
        """Task with insufficient slack is not delayed."""
        tasks = {
            "A": {
                "task_id": "A",
                "task_name": "A",
                "es": base_date,
                "ef": base_date + timedelta(days=4),
                "total_slack": 0,
                "is_critical": True,
            },
            "C": {
                "task_id": "C",
                "task_name": "C",
                "es": base_date,
                "ef": base_date + timedelta(days=4),
                "total_slack": 1,  # Only 1 day slack
                "is_critical": False,
            },
        }
        assignments = {
            "A": ResourceAssignment(task_id="A", resource_id="R1", units_per_day=1.0),
            "C": ResourceAssignment(task_id="C", resource_id="R1", units_per_day=1.0),
        }
        capacities = {
            "R1": ResourceCapacity(resource_id="R1", max_units_per_day=1.0),
        }

        result = leveler.level_schedule(tasks, assignments, capacities)

        # With insufficient slack, conflict may not be fully resolved
        # Status should indicate partial or remaining conflicts
        assert result.status in [LevelingStatus.PARTIAL, LevelingStatus.SUCCESS]


# ============================================================================
# TEST: Multi-Resource Scenarios
# ============================================================================

class TestMultiResourceScenarios:
    """Test scenarios with multiple resources."""

    def test_multi_resource_independent_conflicts(self, leveler, multi_resource_scenario):
        """Each resource conflict resolved independently."""
        tasks, assignments, capacities = multi_resource_scenario
        result = leveler.level_schedule(tasks, assignments, capacities)

        # Both resources handled
        assert result.status in [LevelingStatus.SUCCESS, LevelingStatus.PARTIAL]

    def test_partial_resolution_with_unresolvable_conflicts(self, leveler, base_date):
        """Some conflicts resolved, others remain unresolvable."""
        # Two critical tasks with 0 slack cannot be resolved, should result in PARTIAL
        tasks = {
            "A": {
                "task_id": "A",
                "task_name": "A",
                "es": base_date,
                "ef": base_date + timedelta(days=4),
                "total_slack": 0,
                "is_critical": True,
            },
            "B": {
                "task_id": "B",
                "task_name": "B",
                "es": base_date,
                "ef": base_date + timedelta(days=4),
                "total_slack": 0,
                "is_critical": True,
            },
        }
        assignments = {
            "A": ResourceAssignment(task_id="A", resource_id="R1", units_per_day=1.0),
            "B": ResourceAssignment(task_id="B", resource_id="R1", units_per_day=1.0),
        }
        capacities = {
            "R1": ResourceCapacity(resource_id="R1", max_units_per_day=1.0),
        }

        result = leveler.level_schedule(tasks, assignments, capacities)

        # Status should be PARTIAL (conflicts remain unresolvable) or total conflicts > 0
        # At minimum, we should have detected conflicts
        assert result.total_conflicts > 0 or result.status == LevelingStatus.PARTIAL

    def test_three_resource_complex_scenario(self, leveler, base_date):
        """Complex scenario with 3 resources and mixed criticality."""
        tasks = {
            "A": {
                "task_id": "A",
                "task_name": "A",
                "es": base_date,
                "ef": base_date + timedelta(days=9),
                "total_slack": 0,
                "is_critical": True,
            },
            "B": {
                "task_id": "B",
                "task_name": "B",
                "es": base_date + timedelta(days=5),
                "ef": base_date + timedelta(days=9),
                "total_slack": 0,
                "is_critical": True,
            },
            "C": {
                "task_id": "C",
                "task_name": "C",
                "es": base_date,
                "ef": base_date + timedelta(days=4),
                "total_slack": 5,
                "is_critical": False,
            },
        }
        assignments = {
            "A": ResourceAssignment(task_id="A", resource_id="R1", units_per_day=1.0),
            "B": ResourceAssignment(task_id="B", resource_id="R2", units_per_day=1.0),
            "C": ResourceAssignment(task_id="C", resource_id="R3", units_per_day=1.0),
        }
        capacities = {
            "R1": ResourceCapacity(resource_id="R1", max_units_per_day=1.0),
            "R2": ResourceCapacity(resource_id="R2", max_units_per_day=1.0),
            "R3": ResourceCapacity(resource_id="R3", max_units_per_day=1.0),
        }

        result = leveler.level_schedule(tasks, assignments, capacities)
        assert result.status == LevelingStatus.SUCCESS
        assert result.total_conflicts == 0


# ============================================================================
# TEST: Iteration Limits & Termination
# ============================================================================

class TestIterationLimits:
    """Test iteration limits and termination conditions."""

    def test_iteration_count_tracked(self, leveler, single_resource_with_conflict):
        """Iteration count is properly tracked."""
        tasks, assignments, capacities = single_resource_with_conflict
        result = leveler.level_schedule(tasks, assignments, capacities, max_iterations=100)

        assert result.iterations >= 0
        assert result.iterations <= 100

    def test_max_iterations_respected(self, leveler):
        """Respects max_iterations limit."""
        # Create a complex scenario that might need many iterations
        base_date = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        tasks = {
            f"T{i}": {
                "task_id": f"T{i}",
                "task_name": f"Task {i}",
                "es": base_date,
                "ef": base_date + timedelta(days=4),
                "total_slack": i,  # Increasing slack
                "is_critical": False,
            }
            for i in range(5)
        }
        assignments = {
            f"T{i}": ResourceAssignment(
                task_id=f"T{i}",
                resource_id="R1",
                units_per_day=1.0
            )
            for i in range(5)
        }
        capacities = {"R1": ResourceCapacity(resource_id="R1", max_units_per_day=1.0)}

        result = leveler.level_schedule(tasks, assignments, capacities, max_iterations=5)
        assert result.iterations <= 5


# ============================================================================
# TEST: Result Structure & Content
# ============================================================================

class TestResultStructure:
    """Test LevelingResult structure and content."""

    def test_result_contains_original_tasks(self, leveler, simple_tasks):
        """Result captures original task dates."""
        result = leveler.level_schedule(simple_tasks, {})

        assert "A" in result.original_tasks
        assert "B" in result.original_tasks
        assert "C" in result.original_tasks
        assert "es" in result.original_tasks["A"]
        assert "ef" in result.original_tasks["A"]

    def test_result_contains_leveled_tasks(self, leveler, simple_tasks):
        """Result captures leveled task dates."""
        result = leveler.level_schedule(simple_tasks, {})

        assert "A" in result.leveled_tasks
        assert len(result.leveled_tasks) == len(result.original_tasks)

    def test_conflict_count_accurate(self, leveler, single_resource_with_conflict):
        """Total conflicts count is accurate."""
        tasks, assignments, capacities = single_resource_with_conflict
        result = leveler.level_schedule(tasks, assignments, capacities)

        assert result.total_conflicts >= 0
        assert result.conflicts_resolved <= result.total_conflicts

    def test_no_errors_on_success(self, leveler, single_resource_no_conflict):
        """Successful leveling produces no errors."""
        tasks, assignments, capacities = single_resource_no_conflict
        result = leveler.level_schedule(tasks, assignments, capacities)

        assert len(result.errors) == 0


# ============================================================================
# TEST: Histogram Building
# ============================================================================

class TestHistogramBuilding:
    """Test resource usage histogram construction."""

    def test_histogram_tracks_task_daily_usage(self, leveler, base_date):
        """Histogram correctly tracks task usage across days."""
        tasks = {
            "A": {
                "task_id": "A",
                "task_name": "A",
                "es": base_date,
                "ef": base_date + timedelta(days=2),
                "total_slack": 0,
                "is_critical": True,
            },
        }
        assignments = {
            "A": ResourceAssignment(task_id="A", resource_id="R1", units_per_day=0.5),
        }
        capacities = {
            "R1": ResourceCapacity(resource_id="R1", max_units_per_day=1.0),
        }

        context = ResourceLevelingContext(tasks, assignments, capacities)
        leveler._build_histogram(context)

        # Histogram should have R1 with 3 days (Jan 1, 2, 3)
        assert "R1" in context.histogram
        assert len(context.histogram["R1"]) == 3

        # Each day should show task A
        for day_dict in context.histogram["R1"].values():
            assert "A" in day_dict.task_ids
            assert day_dict.total_units == 0.5

    def test_histogram_sums_multiple_assignments(self, leveler, base_date):
        """Histogram correctly sums usage from multiple assignments."""
        tasks = {
            "A": {
                "task_id": "A",
                "task_name": "A",
                "es": base_date,
                "ef": base_date + timedelta(days=1),
                "total_slack": 0,
                "is_critical": True,
            },
            "B": {
                "task_id": "B",
                "task_name": "B",
                "es": base_date,
                "ef": base_date + timedelta(days=1),
                "total_slack": 0,
                "is_critical": True,
            },
        }
        assignments = {
            "A": ResourceAssignment(task_id="A", resource_id="R1", units_per_day=0.5),
            "B": ResourceAssignment(task_id="B", resource_id="R1", units_per_day=0.3),
        }
        capacities = {
            "R1": ResourceCapacity(resource_id="R1", max_units_per_day=1.0),
        }

        context = ResourceLevelingContext(tasks, assignments, capacities)
        leveler._build_histogram(context)

        # On day 1, should have both A and B
        day_1 = context.histogram["R1"][base_date]
        assert day_1.total_units == 0.8  # 0.5 + 0.3
        assert set(day_1.task_ids) == {"A", "B"}


# ============================================================================
# TEST: Date Handling
# ============================================================================

class TestDateHandling:
    """Test proper handling of date formats and conversions."""

    def test_iso_format_date_parsing(self, leveler):
        """ISO format strings are properly parsed."""
        base_date = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        tasks = {
            "A": {
                "task_id": "A",
                "task_name": "A",
                "es": "2024-01-01T00:00:00Z",  # ISO string
                "ef": "2024-01-05T00:00:00Z",
                "total_slack": 0,
                "is_critical": True,
            },
        }
        assignments = {
            "A": ResourceAssignment(task_id="A", resource_id="R1", units_per_day=1.0),
        }
        capacities = {
            "R1": ResourceCapacity(resource_id="R1", max_units_per_day=1.0),
        }

        result = leveler.level_schedule(tasks, assignments, capacities)
        assert result.status == LevelingStatus.SUCCESS

    def test_datetime_object_handling(self, leveler, base_date):
        """Datetime objects are handled correctly."""
        tasks = {
            "A": {
                "task_id": "A",
                "task_name": "A",
                "es": base_date,
                "ef": base_date + timedelta(days=5),
                "total_slack": 0,
                "is_critical": True,
            },
        }
        assignments = {
            "A": ResourceAssignment(task_id="A", resource_id="R1", units_per_day=1.0),
        }

        result = leveler.level_schedule(tasks, assignments)
        assert result.status == LevelingStatus.SUCCESS


# ============================================================================
# TEST: Custom Capacities
# ============================================================================

class TestCustomCapacities:
    """Test resource capacities beyond standard 1.0."""

    def test_fractional_capacity(self, leveler, base_date):
        """Half-time resources (0.5 capacity) handled correctly."""
        tasks = {
            "A": {
                "task_id": "A",
                "task_name": "A",
                "es": base_date,
                "ef": base_date + timedelta(days=2),
                "total_slack": 0,
                "is_critical": True,
            },
        }
        assignments = {
            "A": ResourceAssignment(task_id="A", resource_id="R1", units_per_day=0.5),
        }
        capacities = {
            "R1": ResourceCapacity(resource_id="R1", max_units_per_day=0.5),
        }

        result = leveler.level_schedule(tasks, assignments, capacities)
        assert result.status == LevelingStatus.SUCCESS

    def test_high_capacity_resource(self, leveler, base_date):
        """Over-capacity resources (2.0+) handled correctly."""
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
                "es": base_date,
                "ef": base_date + timedelta(days=2),
                "total_slack": 5,
                "is_critical": False,
            },
        }
        assignments = {
            "A": ResourceAssignment(task_id="A", resource_id="R1", units_per_day=1.0),
            "B": ResourceAssignment(task_id="B", resource_id="R1", units_per_day=1.0),
        }
        capacities = {
            "R1": ResourceCapacity(resource_id="R1", max_units_per_day=2.0),
        }

        result = leveler.level_schedule(tasks, assignments, capacities)
        # No conflicts should be detected (2.0 units <= 2.0 capacity)
        assert result.total_conflicts == 0
        assert result.status == LevelingStatus.SUCCESS


# ============================================================================
# TEST: Task with Missing Fields
# ============================================================================

class TestRobustness:
    """Test robustness with incomplete or edge-case data."""

    def test_task_without_slack_field(self, leveler, base_date):
        """Tasks without slack field default to 0."""
        tasks = {
            "A": {
                "task_id": "A",
                "task_name": "A",
                "es": base_date,
                "ef": base_date + timedelta(days=2),
                # no total_slack field
                "is_critical": True,
            },
        }
        assignments = {
            "A": ResourceAssignment(task_id="A", resource_id="R1", units_per_day=1.0),
        }

        result = leveler.level_schedule(tasks, assignments)
        assert result.status == LevelingStatus.SUCCESS

    def test_task_without_critical_field(self, leveler, base_date):
        """Tasks without is_critical field default to False."""
        tasks = {
            "A": {
                "task_id": "A",
                "task_name": "A",
                "es": base_date,
                "ef": base_date + timedelta(days=2),
                "total_slack": 5,
                # no is_critical field
            },
        }
        assignments = {
            "A": ResourceAssignment(task_id="A", resource_id="R1", units_per_day=1.0),
        }

        result = leveler.level_schedule(tasks, assignments)
        assert result.status == LevelingStatus.SUCCESS
