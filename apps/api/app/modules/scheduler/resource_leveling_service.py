"""
Resource Leveling Service

Provides high-level API for resource leveling operations.
Integrates with scheduler module and exposes leveling functionality
for project scheduling workflows.

Phase 1 Task #13: Resource Leveling
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from app.modules.scheduler.resource_leveler import (
    ResourceLeveler,
    ResourceAssignment,
    ResourceCapacity,
    LevelingStatus,
)

logger = logging.getLogger(__name__)


class ResourceLevelingService:
    """
    High-level service for resource leveling in project scheduling.

    Encapsulates the leveling-by-free-slack algorithm and provides
    methods for leveling project schedules while preserving critical path.
    """

    def __init__(self):
        """Initialize resource leveling service."""
        self.leveler = ResourceLeveler()

    async def level_project_schedule(
        self,
        project_id: str,
        organisation_id: str,
        tasks: Dict[str, Dict],
        resource_assignments: Dict[str, Dict],
        resource_capacities: Dict[str, Dict],
        max_iterations: int = 100,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Level a project schedule to resolve resource over-allocations.

        Args:
            project_id: Project identifier
            organisation_id: Organization identifier
            tasks: Dict of task_id -> task dict with es, ef, total_slack, is_critical
            resource_assignments: Dict of task_id -> assignment dict
                {resource_id, units_per_day}
            resource_capacities: Dict of resource_id -> capacity dict
                {max_units_per_day}
            max_iterations: Max leveling iterations (default: 100)
            user_id: Optional user ID for audit logging

        Returns:
            Dict with leveling result, original vs leveled schedules, and metrics
        """
        logger.info(
            f"Starting resource leveling for project {project_id} "
            f"({len(tasks)} tasks, {len(resource_assignments)} assignments)"
        )

        # Convert input dicts to domain objects
        assignments = self._convert_assignments(resource_assignments)
        capacities = self._convert_capacities(resource_capacities)

        # Run leveling algorithm
        result = self.leveler.level_schedule(
            tasks=tasks,
            assignments=assignments,
            capacities=capacities,
            max_iterations=max_iterations
        )

        # Package result for API response
        response = {
            "project_id": project_id,
            "organisation_id": organisation_id,
            "status": result.status.value,
            "summary": {
                "total_conflicts_detected": result.total_conflicts,
                "conflicts_resolved": result.conflicts_resolved,
                "iterations": result.iterations,
                "success": result.status == LevelingStatus.SUCCESS,
            },
            "original_schedule": result.original_tasks,
            "leveled_schedule": result.leveled_tasks,
            "changes": self._compute_changes(result.original_tasks, result.leveled_tasks),
        }

        logger.info(
            f"Leveling complete: {result.conflicts_resolved}/{result.total_conflicts} "
            f"conflicts resolved in {result.iterations} iterations"
        )

        return response

    async def get_resource_histogram(
        self,
        tasks: Dict[str, Dict],
        resource_assignments: Dict[str, Dict],
        resource_capacities: Dict[str, Dict],
    ) -> Dict[str, Dict[str, List[Dict]]]:
        """
        Build resource usage histogram for visualization.

        Args:
            tasks: Task schedule data
            resource_assignments: Resource assignments
            resource_capacities: Resource capacities

        Returns:
            Dict of resource_id -> {date -> usage details}
        """
        from app.modules.scheduler.resource_leveler import (
            ResourceLevelingContext,
        )

        assignments = self._convert_assignments(resource_assignments)
        capacities = self._convert_capacities(resource_capacities)

        context = ResourceLevelingContext(tasks, assignments, capacities)
        self.leveler._build_histogram(context)

        # Convert histogram to serializable format
        histogram = {}
        for resource_id, date_dict in context.histogram.items():
            histogram[resource_id] = {}
            for date, usage_day in date_dict.items():
                date_str = date.isoformat()
                histogram[resource_id][date_str] = {
                    "date": date_str,
                    "resource_id": resource_id,
                    "task_ids": usage_day.task_ids,
                    "total_units": usage_day.total_units,
                    "capacity": usage_day.capacity,
                    "available_units": usage_day.available_units,
                    "is_over_allocated": usage_day.is_over_allocated,
                    "over_allocated_by": (
                        usage_day.total_units - usage_day.capacity
                        if usage_day.is_over_allocated
                        else 0
                    ),
                }

        return histogram

    async def detect_conflicts(
        self,
        tasks: Dict[str, Dict],
        resource_assignments: Dict[str, Dict],
        resource_capacities: Dict[str, Dict],
    ) -> Dict[str, Any]:
        """
        Detect resource conflicts without leveling.

        Args:
            tasks: Task schedule data
            resource_assignments: Resource assignments
            resource_capacities: Resource capacities

        Returns:
            Dict with conflict details
        """
        from app.modules.scheduler.resource_leveler import (
            ResourceLevelingContext,
        )

        assignments = self._convert_assignments(resource_assignments)
        capacities = self._convert_capacities(resource_capacities)

        context = ResourceLevelingContext(tasks, assignments, capacities)
        self.leveler._build_histogram(context)
        self.leveler._detect_conflicts(context)

        # Convert conflicts to serializable format
        conflicts_by_date = {}
        for conflict in context.conflicts:
            date_str = conflict.date.isoformat()
            if date_str not in conflicts_by_date:
                conflicts_by_date[date_str] = []

            conflicts_by_date[date_str].append({
                "date": date_str,
                "resource_id": conflict.resource_id,
                "over_allocated_by": conflict.over_allocated_by,
                "task_ids": conflict.task_ids,
            })

        return {
            "total_conflicts": len(context.conflicts),
            "conflicts_by_date": conflicts_by_date,
            "affected_resources": list(set(c.resource_id for c in context.conflicts)),
        }

    def _convert_assignments(
        self,
        assignment_dicts: Dict[str, Dict]
    ) -> Dict[str, ResourceAssignment]:
        """Convert assignment dicts to domain objects."""
        assignments = {}
        for task_id, assignment_dict in assignment_dicts.items():
            assignments[task_id] = ResourceAssignment(
                task_id=task_id,
                resource_id=assignment_dict.get("resource_id"),
                units_per_day=assignment_dict.get("units_per_day", 1.0),
            )
        return assignments

    def _convert_capacities(
        self,
        capacity_dicts: Dict[str, Dict]
    ) -> Dict[str, ResourceCapacity]:
        """Convert capacity dicts to domain objects."""
        capacities = {}
        for resource_id, capacity_dict in capacity_dicts.items():
            capacities[resource_id] = ResourceCapacity(
                resource_id=resource_id,
                max_units_per_day=capacity_dict.get("max_units_per_day", 1.0),
            )
        return capacities

    def _compute_changes(
        self,
        original: Dict[str, Dict],
        leveled: Dict[str, Dict]
    ) -> Dict[str, Dict]:
        """
        Compute changes between original and leveled schedules.

        Returns dict of task_id -> changes dict
        """
        changes = {}

        for task_id in original:
            if task_id not in leveled:
                continue

            orig = original[task_id]
            leveled_task = leveled[task_id]

            # Check if dates changed
            es_changed = orig.get("es") != leveled_task.get("es")
            ef_changed = orig.get("ef") != leveled_task.get("ef")
            slack_changed = orig.get("slack", 0) != leveled_task.get("slack", 0)

            if es_changed or ef_changed or slack_changed:
                changes[task_id] = {
                    "task_id": task_id,
                    "original_es": orig.get("es"),
                    "leveled_es": leveled_task.get("es"),
                    "es_changed": es_changed,
                    "original_ef": orig.get("ef"),
                    "leveled_ef": leveled_task.get("ef"),
                    "ef_changed": ef_changed,
                    "original_slack": orig.get("slack", 0),
                    "leveled_slack": leveled_task.get("slack", 0),
                    "slack_changed": slack_changed,
                    "delay_days": (
                        (leveled_task.get("es") - orig.get("es")).days
                        if isinstance(leveled_task.get("es"), datetime)
                        and isinstance(orig.get("es"), datetime)
                        else 0
                    ),
                }

        return changes

    def get_leveling_status(self) -> Dict[str, Any]:
        """Get leveler status and configuration."""
        return {
            "max_iterations": self.leveler.max_iterations,
            "algorithm": "leveling-by-free-slack",
            "features": [
                "critical_path_preservation",
                "slack_based_delay",
                "multi_resource_support",
                "iteration_limits",
            ],
        }
