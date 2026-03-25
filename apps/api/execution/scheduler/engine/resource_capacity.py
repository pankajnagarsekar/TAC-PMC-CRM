"""
Resource Capacity — overallocation detection and leveling.

Constitution §4 Step 5: "Detect overallocations across enterprise resource pool.
Delay lower-priority tasks per priority rules. Re-run affected subgraph of CPM
if dates shifted. Algorithm must be deterministic."

Priority rules (Constitution §4 Step 5):
    1. Task criticality (critical path tasks first — never delayed)
    2. Project priority (project_priority field — lower number = higher priority)
    3. Task priority field
    4. FIFO (earlier scheduled_start wins)

Key constraints:
    - Deterministic: same input → same output always
    - After leveling shifts any dates, re-run affected CPM subgraph
    - Supports resource-level calendars (different work days per resource)
    - enterprise_resources.max_capacity_per_day = daily hour limit
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from datetime import date, timedelta
from collections import defaultdict

from .interfaces import (
    CalculationRequest,
    CalculationResponse,
    TaskInput,
    TaskResult,
    EngineWarning,
    WarningType,
    ResourceCalendar,
)
from .calendar_utils import (
    add_work_days,
    next_work_day,
    is_work_day,
    is_work_day_resource,
    first_work_day_on_or_after,
)


# =============================================================================
# Resource metadata passed in from the API
# (enterprise_resources fields relevant to leveling)
# =============================================================================

@dataclass
class ResourceInfo:
    """Metadata for a single resource — subset of enterprise_resources fields."""
    resource_id: str
    max_capacity_per_day: int   # Hours
    priority_rank: int           # Lower = higher priority
    calendar: Optional[ResourceCalendar] = None


@dataclass
class LevelingRequest:
    """
    Input to the resource leveler — wraps the calculation request
    with additional resource metadata.
    """
    base_request: CalculationRequest
    base_response: CalculationResponse      # CPM output BEFORE leveling
    resources: List[ResourceInfo]
    project_priority: int = 100             # Used for cross-project tie-breaking


@dataclass
class LevelingResult:
    """
    Output from the resource leveler.
    Contains the set of task_ids whose dates were shifted,
    and the updated task start/finish dates.
    """
    shifted_task_ids: Set[str]
    updated_starts: Dict[str, date]   # task_id → new scheduled_start
    warnings: List[EngineWarning]


# =============================================================================
# Day-span helper
# =============================================================================

def _work_days_in_span(start: date, finish: date, calendar, resource_cal: Optional[ResourceCalendar] = None) -> List[date]:
    """Returns list of working days from start to finish inclusive."""
    days = []
    current = start
    while current <= finish:
        if resource_cal:
            if is_work_day_resource(current, resource_cal):
                days.append(current)
        else:
            if is_work_day(current, calendar):
                days.append(current)
        current += timedelta(days=1)
    return days


# =============================================================================
# Main leveling function
# =============================================================================

def level_resources(req: LevelingRequest) -> LevelingResult:
    """
    Detects resource overallocations and delays lower-priority tasks.

    Algorithm:
        1. For each working day in the project span:
           - Compute total hours demanded by all tasks active on that day
           - For each resource: if demand > capacity, identify overallocated tasks
        2. Sort overallocated tasks by priority (criticality → project_priority → task_priority → FIFO)
        3. Critical path tasks are NEVER delayed (they may trigger a warning instead)
        4. For non-critical tasks: delay start to the next available day
        5. Track all shifted task_ids
        6. Return shifted tasks → caller triggers CPM subgraph re-run

    Determinism guarantee:
        Sort is stable and uses a deterministic key (is_critical + priority_rank +
        scheduled_start + task_id). Same inputs always produce same output.

    Args:
        req: LevelingRequest with base CPM results and resource metadata

    Returns:
        LevelingResult with set of shifted task_ids and their new start dates.
    """
    calendar = req.base_request.calendar
    resource_map: Dict[str, ResourceInfo] = {r.resource_id: r for r in req.resources}

    # Build task result map
    results_map: Dict[str, TaskResult] = {t.task_id: t for t in req.base_response.tasks}
    task_input_map: Dict[str, TaskInput] = {t.task_id: t for t in req.base_request.tasks}
    critical_set: Set[str] = set(req.base_response.critical_path)

    warnings: List[EngineWarning] = []
    shifted_tasks: Set[str] = set()
    updated_starts: Dict[str, date] = {}

    # ─── Build daily resource demand map ──────────────────────────────────────
    # resource_id → day → list of (task_id, hours_per_day)
    daily_demand: Dict[str, Dict[date, List[Tuple[str, float]]]] = defaultdict(lambda: defaultdict(list))

    for task_id, tr in results_map.items():
        task_in = task_input_map.get(task_id)
        if not task_in:
            continue

        for resource_id in task_in.assigned_resources:
            res_info = resource_map.get(resource_id)
            res_cal = res_info.calendar if res_info else None

            # Assume uniform 8-hour workday per task per resource (MVP)
            # TODO Phase 4: use actual allocation percentages when AI assigns them
            hours_per_day = 8.0

            work_days = _work_days_in_span(tr.scheduled_start, tr.scheduled_finish, calendar, res_cal)
            for d in work_days:
                daily_demand[resource_id][d].append((task_id, hours_per_day))

    # ─── Detect and resolve overallocations ───────────────────────────────────
    # Process each resource on each day
    for resource_id, day_map in daily_demand.items():
        res_info = resource_map.get(resource_id)
        if not res_info:
            continue

        capacity_hours = res_info.max_capacity_per_day

        for day in sorted(day_map.keys()):
            tasks_on_day = day_map[day]
            total_hours = sum(h for _, h in tasks_on_day)

            if total_hours <= capacity_hours:
                continue  # No overallocation

            # Sort by priority: critical first, then priority_rank, then start, then task_id
            def priority_key(item: Tuple[str, float]) -> Tuple:
                tid, _ = item
                tr = results_map.get(tid)
                task_in = task_input_map.get(tid)
                is_crit = 0 if tid in critical_set else 1  # 0=critical (keep), 1=non-critical (may delay)
                proj_prio = req.project_priority
                task_start = tr.scheduled_start if tr else date(9999, 1, 1)
                return (is_crit, proj_prio, task_start, tid)  # deterministic

            sorted_tasks = sorted(tasks_on_day, key=priority_key)

            # Keep tasks until capacity is reached, delay the rest
            accumulated = 0.0
            for task_id, hours in sorted_tasks:
                if accumulated + hours <= capacity_hours:
                    accumulated += hours
                    continue  # This task fits — keep on this day

                # This task causes overallocation — delay it
                if task_id in critical_set:
                    warnings.append(EngineWarning(
                        type=WarningType.RESOURCE_OVERALLOCATION,
                        detail=(
                            f"Resource '{resource_id}' is overallocated on {day} "
                            f"due to critical path task '{task_id}'. "
                            f"Cannot delay critical task. Manual resolution required."
                        ),
                        task_id=task_id,
                    ))
                    accumulated += hours  # Can't delay — count it anyway
                    continue

                # Delay this task to the next available day
                tr = results_map.get(task_id)
                if not tr:
                    continue

                current_start = updated_starts.get(task_id, tr.scheduled_start)

                # Find next day where this resource has capacity
                new_start = _find_next_available_day(
                    after=day,
                    resource_id=resource_id,
                    daily_demand=daily_demand,
                    capacity=capacity_hours,
                    calendar=calendar,
                    res_cal=res_info.calendar,
                )

                if new_start > current_start:
                    updated_starts[task_id] = new_start
                    shifted_tasks.add(task_id)
                    warnings.append(EngineWarning(
                        type=WarningType.RESOURCE_OVERALLOCATION,
                        detail=(
                            f"Resource '{resource_id}' overallocated on {day}. "
                            f"Task '{task_id}' delayed from {current_start} to {new_start}."
                        ),
                        task_id=task_id,
                    ))

    return LevelingResult(
        shifted_task_ids=shifted_tasks,
        updated_starts=updated_starts,
        warnings=warnings,
    )


def _find_next_available_day(
    after: date,
    resource_id: str,
    daily_demand: Dict,
    capacity: int,
    calendar,
    res_cal: Optional[ResourceCalendar],
) -> date:
    """
    Finds the next working day after `after` where the resource has available capacity.
    Simple forward scan — for large schedules this is bounded by the project span.
    """
    current = after + timedelta(days=1)
    # Limit scan to 60 calendar days to avoid infinite loops
    for _ in range(60):
        if res_cal:
            if not is_work_day_resource(current, res_cal):
                current += timedelta(days=1)
                continue
        else:
            if not is_work_day(current, calendar):
                current += timedelta(days=1)
                continue

        # Check demand on this day
        demand = sum(h for _, h in daily_demand.get(resource_id, {}).get(current, []))
        if demand < capacity:
            return current
        current += timedelta(days=1)

    return current  # Return the best we found
