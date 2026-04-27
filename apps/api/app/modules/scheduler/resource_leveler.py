"""
Resource Leveling Module

Implements leveling-by-free-slack algorithm to resolve resource over-allocation.
Preserves critical path by only delaying non-critical tasks within their slack.

Architecture:
- ResourceAssignment: task → resource mapping
- ResourceCapacity: resource → max units/day
- ResourceUsageDay: daily usage tracking
- ResourceLevelingContext: state management
- ResourceLeveler: core leveling engine
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class LevelingStatus(str, Enum):
    """Status of leveling operation."""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class ResourceAssignment:
    """Maps a task to a resource with capacity requirement."""
    task_id: str
    resource_id: str
    units_per_day: float = 1.0  # e.g., 1.0 = full-time, 0.5 = half-time

    def __hash__(self):
        return hash((self.task_id, self.resource_id))


@dataclass
class ResourceCapacity:
    """Resource capacity definition."""
    resource_id: str
    max_units_per_day: float = 1.0  # Default: 1 full-time resource

    def __hash__(self):
        return hash(self.resource_id)


@dataclass
class Conflict:
    """Represents a resource over-allocation conflict."""
    date: datetime
    resource_id: str
    over_allocated_by: float  # How much over capacity
    task_ids: List[str] = field(default_factory=list)  # Tasks on this day

    def __lt__(self, other):
        """Sort by date (chronological)."""
        return self.date < other.date


@dataclass
class ResourceUsageDay:
    """Tracks resource usage on a single day."""
    date: datetime
    resource_id: str
    task_ids: List[str] = field(default_factory=list)
    total_units: float = 0.0
    capacity: float = 1.0

    @property
    def available_units(self) -> float:
        """Available capacity on this day."""
        return self.capacity - self.total_units

    @property
    def is_over_allocated(self) -> bool:
        """Check if this day is over-allocated."""
        return self.total_units > self.capacity


@dataclass
class LevelingResult:
    """Result of leveling operation."""
    status: LevelingStatus
    original_tasks: Dict[str, Dict] = field(default_factory=dict)
    leveled_tasks: Dict[str, Dict] = field(default_factory=dict)
    conflicts_resolved: int = 0
    total_conflicts: int = 0
    iterations: int = 0
    errors: List[str] = field(default_factory=list)


class ResourceLevelingContext:
    """
    State management for leveling operation.
    Tracks tasks, assignments, capacities, and resource histogram.
    """

    def __init__(
        self,
        tasks: Dict[str, Dict],
        assignments: Dict[str, ResourceAssignment],
        capacities: Dict[str, ResourceCapacity]
    ):
        """Initialize context with task data and resource definitions."""
        self.tasks = tasks
        self.assignments = assignments
        self.capacities = capacities
        self.histogram: Dict[str, Dict[datetime, ResourceUsageDay]] = {}
        self.conflicts: List[Conflict] = []
        self.project_start: Optional[datetime] = None
        self.project_end: Optional[datetime] = None


class ResourceLeveler:
    """
    Core leveling engine implementing leveling-by-free-slack algorithm.

    Resolves resource over-allocation by delaying non-critical tasks
    within their slack, preserving the critical path.
    """

    def __init__(self):
        """Initialize leveler."""
        self.max_iterations = 100

    def level_schedule(
        self,
        tasks: Dict[str, Dict],
        assignments: Optional[Dict[str, ResourceAssignment]] = None,
        capacities: Optional[Dict[str, ResourceCapacity]] = None,
        max_iterations: int = 100
    ) -> LevelingResult:
        """
        Main entry point for schedule leveling.

        Args:
            tasks: task_id → task dict (must have es, ef, total_slack, is_critical)
            assignments: task_id → ResourceAssignment
            capacities: resource_id → ResourceCapacity
            max_iterations: max leveling iterations (default: 100)

        Returns:
            LevelingResult with leveled task dates
        """
        # Handle empty cases
        if not tasks:
            return LevelingResult(status=LevelingStatus.SUCCESS)

        if not assignments:
            assignments = {}

        if not capacities:
            capacities = {}

        self.max_iterations = max_iterations

        # Create context
        context = ResourceLevelingContext(tasks, assignments, capacities)

        # Store original task dates
        result = LevelingResult(status=LevelingStatus.SUCCESS)
        for task_id, task in tasks.items():
            result.original_tasks[task_id] = {
                "es": task.get("es"),
                "ef": task.get("ef"),
                "slack": task.get("total_slack", 0)
            }

        # If no assignments, no leveling needed
        if not assignments:
            result.leveled_tasks = {
                tid: {
                    "es": t.get("es"),
                    "ef": t.get("ef"),
                    "slack": t.get("total_slack", 0)
                }
                for tid, t in tasks.items()
            }
            return result

        # Build initial histogram
        self._build_histogram(context)

        # Detect initial conflicts
        self._detect_conflicts(context)
        result.total_conflicts = len(context.conflicts)

        # If no conflicts, no leveling needed
        if not context.conflicts:
            result.status = LevelingStatus.SUCCESS
            result.leveled_tasks = result.original_tasks
            return result

        # Iteratively resolve conflicts
        iteration = 0
        while context.conflicts and iteration < self.max_iterations:
            iteration += 1

            # Get next conflict (chronological)
            conflict = context.conflicts.pop(0)

            # Try to resolve by delaying non-critical tasks
            delayed_tasks = self._resolve_conflict(context, conflict)

            if delayed_tasks:
                result.conflicts_resolved += 1

                # Rebuild histogram with new dates
                self._build_histogram(context)

                # Detect new conflicts
                self._detect_conflicts(context)
            else:
                # Could not resolve - log and continue
                logger.warning(
                    f"Could not resolve conflict on {conflict.date} for "
                    f"resource {conflict.resource_id}"
                )

        result.iterations = iteration
        result.status = LevelingStatus.SUCCESS if not context.conflicts else LevelingStatus.PARTIAL

        # Capture leveled task dates
        for task_id, task in context.tasks.items():
            result.leveled_tasks[task_id] = {
                "es": task.get("es"),
                "ef": task.get("ef"),
                "slack": task.get("total_slack", 0)
            }

        return result

    def _build_histogram(self, context: ResourceLevelingContext) -> None:
        """
        Build resource usage histogram.

        For each task with an assignment, iterate through its date range
        and track which tasks use which resources on which days.
        """
        # Clear existing histogram
        context.histogram = {}

        # Process each assignment
        for task_id, assignment in context.assignments.items():
            if task_id not in context.tasks:
                continue

            task = context.tasks[task_id]
            es = task.get("es")
            ef = task.get("ef")

            if not es or not ef:
                continue

            # Normalize dates
            if isinstance(es, str):
                es = datetime.fromisoformat(es.replace("Z", "+00:00"))
            if isinstance(ef, str):
                ef = datetime.fromisoformat(ef.replace("Z", "+00:00"))

            es = es.replace(hour=0, minute=0, second=0, microsecond=0)
            ef = ef.replace(hour=0, minute=0, second=0, microsecond=0)

            resource_id = assignment.resource_id
            units_per_day = assignment.units_per_day

            # Initialize resource in histogram
            if resource_id not in context.histogram:
                context.histogram[resource_id] = {}

            # Add task to each day in range
            current = es
            while current <= ef:
                if current not in context.histogram[resource_id]:
                    capacity = context.capacities.get(
                        resource_id,
                        ResourceCapacity(resource_id=resource_id)
                    ).max_units_per_day

                    context.histogram[resource_id][current] = ResourceUsageDay(
                        date=current,
                        resource_id=resource_id,
                        capacity=capacity
                    )

                usage_day = context.histogram[resource_id][current]
                usage_day.task_ids.append(task_id)
                usage_day.total_units += units_per_day

                current += timedelta(days=1)

        # Update project start/end
        all_dates = []
        for resource_dict in context.histogram.values():
            all_dates.extend(resource_dict.keys())

        if all_dates:
            context.project_start = min(all_dates)
            context.project_end = max(all_dates)

    def _detect_conflicts(self, context: ResourceLevelingContext) -> None:
        """
        Detect all over-allocated days (usage > capacity).

        Creates Conflict objects for each over-allocated day and resource.
        """
        context.conflicts = []

        for resource_id, date_dict in context.histogram.items():
            for date, usage_day in date_dict.items():
                if usage_day.is_over_allocated:
                    conflict = Conflict(
                        date=date,
                        resource_id=resource_id,
                        over_allocated_by=usage_day.total_units - usage_day.capacity,
                        task_ids=usage_day.task_ids.copy()
                    )
                    context.conflicts.append(conflict)

        # Sort by date (chronological)
        context.conflicts.sort()

    def _resolve_conflict(
        self,
        context: ResourceLevelingContext,
        conflict: Conflict
    ) -> Set[str]:
        """
        Attempt to resolve a single conflict by delaying non-critical tasks.

        Algorithm:
        1. Find all tasks on conflict date
        2. Filter to non-critical tasks with slack > 0
        3. Rank by slack (ascending - smallest slack first)
        4. For each candidate task, try minimum delay to resolve conflict
        5. Apply delay and return affected task IDs

        Returns:
            Set of task IDs that were delayed (empty if couldn't resolve)
        """
        delayed_tasks = set()

        # Get all tasks on conflict day for this resource
        tasks_on_day = [
            tid for tid in conflict.task_ids
            if tid in context.tasks
        ]

        if not tasks_on_day:
            return delayed_tasks

        # Filter to non-critical tasks with slack
        non_critical_candidates = []
        for task_id in tasks_on_day:
            task = context.tasks[task_id]
            slack = task.get("total_slack", 0)
            is_critical = task.get("is_critical", False)

            # Only delay non-critical tasks with available slack
            if not is_critical and slack > 0:
                non_critical_candidates.append((task_id, slack))

        # Sort by slack (ascending - delay smallest slack first)
        non_critical_candidates.sort(key=lambda x: x[1])

        # Try delaying each candidate
        for task_id, slack in non_critical_candidates:
            task = context.tasks[task_id]

            # Calculate minimum delay needed
            # Find how much we need to reduce usage on conflict date
            assignment = context.assignments.get(task_id)
            if not assignment:
                continue

            units_to_remove = conflict.over_allocated_by
            required_delay_days = max(1, int(units_to_remove / assignment.units_per_day) + 1)

            # Don't delay more than available slack
            if required_delay_days > slack:
                continue

            # Apply delay
            es = task.get("es")
            ef = task.get("ef")

            if isinstance(es, str):
                es = datetime.fromisoformat(es.replace("Z", "+00:00"))
            if isinstance(ef, str):
                ef = datetime.fromisoformat(ef.replace("Z", "+00:00"))

            # Delay start and finish by required days
            delay_delta = timedelta(days=required_delay_days)
            new_es = es + delay_delta
            new_ef = ef + delay_delta

            # Update task
            task["es"] = new_es
            task["ef"] = new_ef
            task["total_slack"] = slack - required_delay_days

            delayed_tasks.add(task_id)

            # Only delay one task per conflict (deterministic)
            break

        return delayed_tasks
