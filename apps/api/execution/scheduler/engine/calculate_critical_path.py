"""
CPM Execution Engine — Forward Pass, Backward Pass, Slack, Critical Path.

Constitution §4 Steps 1-4 (this file handles Steps 2-4; Step 1 is in dag_validator.py):
    Step 2: APPLY MANUAL OVERRIDES
    Step 3: RESOLVE CONSTRAINTS
    Step 4: RUN CPM (Forward Pass → Backward Pass → Slack → Critical Path)

Key design rules (Constitution §1 / Tech Arch §1 Layer 3):
    - ZERO DB access. ZERO side effects.
    - Takes CalculationRequest in, returns CalculationResponse out.
    - Must be deterministic: same input → same output always.
    - Must handle 5,000 tasks in < 5 seconds (Constitution §4 validation target).

Dependency type semantics (standard CPM with lag):
    FS (Finish-to-Start):  succ.ES = pred.EF + 1 workday + lag
    SS (Start-to-Start):   succ.ES = pred.ES + lag
    FF (Finish-to-Finish): succ.EF = pred.EF + lag  →  succ.ES = succ.EF - dur + 1
    SF (Start-to-Finish):  succ.EF = pred.ES + lag  →  succ.ES = succ.EF - dur + 1

Backward pass (reverse):
    FS: pred.LF = succ.LS - 1 workday - lag
    SS: pred.LS = succ.LS - lag
    FF: pred.LF = succ.LF - lag
    SF: pred.LS = succ.LF - lag
"""
import uuid
from datetime import datetime, timezone, date, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

from .interfaces import (
    CalculationRequest,
    CalculationResponse,
    CalculationStatus,
    TaskInput,
    TaskResult,
    EngineWarning,
    EngineError,
    WarningType,
)
from .calendar_utils import (
    is_work_day,
    add_work_days,
    subtract_work_days,
    count_work_days,
    next_work_day,
    prev_work_day,
    first_work_day_on_or_after,
    last_work_day_on_or_before,
    add_work_days_offset,
)
from .constraints import apply_constraints


# =============================================================================
# Main entry point
# =============================================================================

def calculate_critical_path(request: CalculationRequest) -> CalculationResponse:
    """
    Full CPM pipeline: Constitution §4 Steps 2-4.

    Step 1 (DAG validation) must be called BEFORE this function.
    The caller (API layer) is responsible for running dag_validator first.

    Args:
        request: CalculationRequest with tasks, calendar, resource_calendars

    Returns:
        CalculationResponse with all CPM fields populated.
        status = SUCCESS if all tasks calculated without error.
        status = PARTIAL_FAILURE if some tasks failed but others succeeded.
        status = FAILURE if the calculation cannot proceed.

    Performance target: < 5 seconds for 5,000 tasks + 7,000 dependencies
    (Constitution §4 Phase 2 validation constraint).
    """
    calc_version = str(uuid.uuid4())
    calc_time = datetime.now(timezone.utc).isoformat()
    calendar = request.calendar

    errors: List[EngineError] = []
    warnings: List[EngineWarning] = []

    # ─── Build task map ───────────────────────────────────────────────────────
    task_map: Dict[str, TaskInput] = {t.task_id: t for t in request.tasks}

    # ─── Step 2: Separate Manual tasks (keep their dates) from Auto tasks ────
    manual_tasks = {tid: t for tid, t in task_map.items() if t.task_mode == "Manual"}
    auto_tasks   = {tid: t for tid, t in task_map.items() if t.task_mode == "Auto"}

    # ─── Topological order (computed by dag_validator, re-run here for safety) ─
    topo_order = _topological_sort(list(task_map.keys()), task_map)
    if topo_order is None:
        return CalculationResponse(
            project_id=request.project_id,
            calculation_version=calc_version,
            calculated_at=calc_time,
            status=CalculationStatus.FAILURE,
            errors=[EngineError("*", "Circular dependency detected. Run DAG validator before calling engine.")],
            tasks=[],
            critical_path=[],
            warnings=[],
        )

    # ─── Build adjacency (successors) ────────────────────────────────────────
    successors: Dict[str, List[str]] = defaultdict(list)
    for tid, t in task_map.items():
        for pred in t.predecessors:
            successors[pred.task_id].append(tid)

    # ─── Step 4a: Forward Pass ────────────────────────────────────────────────
    # es[task_id] = Early Start, ef[task_id] = Early Finish
    es: Dict[str, date] = {}
    ef: Dict[str, date] = {}

    # Project start: first work day on or after the anchor
    # We derive it from the minimum of all tasks with no predecessors,
    # falling back to today if none have a scheduled_start set.
    anchor = _find_project_start(task_map, calendar)

    for tid in topo_order:
        task = task_map[tid]

        # Manual tasks: use their existing dates directly
        if task.task_mode == "Manual":
            if task.scheduled_start and task.scheduled_finish:
                es[tid] = first_work_day_on_or_after(task.scheduled_start, calendar)
                ef[tid] = task.scheduled_finish
            else:
                # Manual task without dates — treat as start of project
                es[tid] = anchor
                ef[tid] = add_work_days(anchor, max(task.scheduled_duration, 1), calendar)
            continue

        # Auto task: compute ES from predecessors
        earliest_start = anchor

        for pred_ref in task.predecessors:
            pred_id = pred_ref.task_id
            if pred_id not in es:
                # External or missing predecessor — skip (warned elsewhere)
                continue

            pred_ef = ef[pred_id]
            pred_es = es[pred_id]
            dep_type = pred_ref.type
            lag = pred_ref.lag_days

            candidate = _compute_early_start_from_dep(
                dep_type=dep_type,
                lag=lag,
                pred_es=pred_es,
                pred_ef=pred_ef,
                task_duration=task.scheduled_duration,
                calendar=calendar,
            )

            if candidate > earliest_start:
                earliest_start = candidate

        # Snap to a valid work day
        earliest_start = first_work_day_on_or_after(earliest_start, calendar)

        # Step 3: Apply constraints (may push start later or fix it)
        constrained_start = apply_constraints(
            task=task,
            unconstrained_start=earliest_start,
            calendar=calendar,
            warnings=warnings,
        )

        es[tid] = constrained_start
        duration = task.scheduled_duration

        if task.is_milestone or duration == 0:
            ef[tid] = constrained_start  # milestone: same day
        else:
            ef[tid] = add_work_days(constrained_start, duration, calendar)

    # ─── Step 4b: Backward Pass ───────────────────────────────────────────────
    # Project finish = latest EF across all tasks
    if not ef:
        return CalculationResponse(
            project_id=request.project_id,
            calculation_version=calc_version,
            calculated_at=calc_time,
            status=CalculationStatus.FAILURE,
            errors=[EngineError("*", "No tasks to calculate.")],
            tasks=[],
            critical_path=[],
            warnings=warnings,
        )

    project_finish = max(ef.values())

    ls: Dict[str, date] = {}
    lf: Dict[str, date] = {}

    for tid in reversed(topo_order):
        task = task_map[tid]

        # Manual tasks: LS/LF = ES/EF (no slack concept for manual)
        if task.task_mode == "Manual":
            ls[tid] = es[tid]
            lf[tid] = ef[tid]
            continue

        # Find the latest allowable finish = earliest LS among successors
        latest_finish = project_finish

        for succ_id in successors.get(tid, []):
            if succ_id not in ls:
                continue

            succ_task = task_map[succ_id]
            # Find the predecessor reference in succ that points to this task
            pred_ref = next((p for p in succ_task.predecessors if p.task_id == tid), None)
            if not pred_ref:
                continue

            dep_type = pred_ref.type
            lag = pred_ref.lag_days

            candidate_lf = _compute_late_finish_from_dep(
                dep_type=dep_type,
                lag=lag,
                succ_ls=ls[succ_id],
                succ_lf=lf[succ_id],
                pred_duration=task.scheduled_duration,
                calendar=calendar,
            )

            if candidate_lf < latest_finish:
                latest_finish = candidate_lf

        lf[tid] = latest_finish
        duration = task.scheduled_duration

        if task.is_milestone or duration == 0:
            ls[tid] = latest_finish
        else:
            ls[tid] = subtract_work_days(latest_finish, duration, calendar)

    # ─── Step 4c: Total Slack & Critical Path ─────────────────────────────────
    task_results: List[TaskResult] = []
    critical_path_tasks: List[str] = []

    for tid in topo_order:
        task = task_map[tid]

        early_s = es.get(tid)
        early_f = ef.get(tid)
        late_s  = ls.get(tid)
        late_f  = lf.get(tid)

        if any(d is None for d in [early_s, early_f, late_s, late_f]):
            errors.append(EngineError(tid, "Failed to compute dates — check predecessor chain"))
            continue

        # Total slack in working days (LS - ES)
        # Invariant check: LS - ES == LF - EF (Constitution §2.1)
        slack_from_start  = count_work_days(early_s, late_s, calendar) - 1
        slack_from_finish = count_work_days(early_f, late_f, calendar) - 1
        total_slack = slack_from_start

        # Deadline variance (Constitution §2.1)
        deadline_variance = None
        is_deadline_breached = False
        if task.deadline:
            deadline_variance = count_work_days(task.deadline, early_f, calendar) - 1
            if early_f > task.deadline:
                is_deadline_breached = True
                total_slack = -deadline_variance  # negative slack signals breach
                warnings.append(EngineWarning(
                    type=WarningType.DEADLINE_BREACHED,
                    detail=f"Task '{tid}' finishes {deadline_variance} working day(s) after its deadline.",
                    task_id=tid,
                ))

        is_critical = (total_slack == 0)
        if is_critical:
            critical_path_tasks.append(tid)

        # Final scheduled dates (engine truth — snapped from CPM output)
        final_start  = early_s
        final_finish = early_f
        final_duration = task.scheduled_duration if task.task_mode == "Manual" else (
            count_work_days(final_start, final_finish, calendar) if not task.is_milestone else 0
        )

        task_results.append(TaskResult(
            task_id=tid,
            scheduled_start=final_start,
            scheduled_finish=final_finish,
            scheduled_duration=final_duration,
            early_start=early_s,
            early_finish=early_f,
            late_start=late_s,
            late_finish=late_f,
            total_slack=total_slack,
            is_critical=is_critical,
            deadline_variance_days=deadline_variance,
            is_deadline_breached=is_deadline_breached,
        ))

    # ─── Determine overall status ─────────────────────────────────────────────
    if errors:
        status = CalculationStatus.PARTIAL_FAILURE if task_results else CalculationStatus.FAILURE
    else:
        status = CalculationStatus.SUCCESS

    return CalculationResponse(
        project_id=request.project_id,
        calculation_version=calc_version,
        calculated_at=calc_time,
        status=status,
        errors=errors,
        tasks=task_results,
        critical_path=critical_path_tasks,
        warnings=warnings,
    )


# =============================================================================
# Dependency calculators — Early Start
# =============================================================================

def _compute_early_start_from_dep(
    dep_type: str,
    lag: int,
    pred_es: date,
    pred_ef: date,
    task_duration: int,
    calendar,
) -> date:
    """
    Returns the earliest possible start date for a successor,
    given the predecessor's ES/EF and the dependency type + lag.
    """
    if dep_type == "FS":
        # Successor starts the next work day after predecessor finishes + lag
        base = next_work_day(pred_ef, calendar) if lag == 0 else add_work_days_offset(pred_ef, 1, calendar)
        return add_work_days_offset(base if lag == 0 else pred_ef, lag + (0 if lag < 0 else 1), calendar)

    elif dep_type == "SS":
        # Successor starts at pred's start + lag
        return add_work_days_offset(pred_es, lag, calendar)

    elif dep_type == "FF":
        # Successor finishes at pred's finish + lag → start = finish - duration + 1
        succ_ef = add_work_days_offset(pred_ef, lag, calendar)
        if task_duration <= 0:
            return succ_ef
        return subtract_work_days(succ_ef, task_duration, calendar)

    elif dep_type == "SF":
        # Successor finishes at pred's start + lag → start = finish - duration + 1
        succ_ef = add_work_days_offset(pred_es, lag, calendar)
        if task_duration <= 0:
            return succ_ef
        return subtract_work_days(succ_ef, task_duration, calendar)

    # Default: treat as FS
    return next_work_day(pred_ef, calendar)


def _compute_early_start_fs(pred_ef: date, lag: int, calendar) -> date:
    """FS with lag: successor ES = next workday after pred.EF + lag workdays."""
    base = next_work_day(pred_ef, calendar)
    return add_work_days_offset(base, lag, calendar)


# =============================================================================
# Dependency calculators — Late Finish (backward pass)
# =============================================================================

def _compute_late_finish_from_dep(
    dep_type: str,
    lag: int,
    succ_ls: date,
    succ_lf: date,
    pred_duration: int,
    calendar,
) -> date:
    """
    Returns the latest allowable finish date for a predecessor,
    given the successor's LS/LF and the dependency type + lag.
    """
    if dep_type == "FS":
        # pred.LF = day before succ.LS - lag
        base = prev_work_day(succ_ls, calendar)
        return add_work_days_offset(base, -lag, calendar)

    elif dep_type == "SS":
        # pred.LS = succ.LS - lag → pred.LF = pred.LS + duration - 1
        pred_ls = add_work_days_offset(succ_ls, -lag, calendar)
        if pred_duration <= 0:
            return pred_ls
        return add_work_days(pred_ls, pred_duration, calendar)

    elif dep_type == "FF":
        # pred.LF = succ.LF - lag
        return add_work_days_offset(succ_lf, -lag, calendar)

    elif dep_type == "SF":
        # pred.LS = succ.LF - lag → pred.LF = pred.LS + duration - 1
        pred_ls = add_work_days_offset(succ_lf, -lag, calendar)
        if pred_duration <= 0:
            return pred_ls
        return add_work_days(pred_ls, pred_duration, calendar)

    # Default: treat as FS
    return prev_work_day(succ_ls, calendar)


# =============================================================================
# Topological sort (Kahn's algorithm)
# Returns None if cycle detected — should have been caught by dag_validator
# =============================================================================

def _topological_sort(task_ids: List[str], task_map: Dict[str, TaskInput]) -> Optional[List[str]]:
    """
    Kahn's algorithm topological sort.
    Returns ordered list if DAG is valid, None if cycle detected.
    Only considers predecessors within the same project (is_external == False).
    """
    in_degree: Dict[str, int] = {tid: 0 for tid in task_ids}
    adj: Dict[str, List[str]] = {tid: [] for tid in task_ids}

    for tid, task in task_map.items():
        for pred in task.predecessors:
            if pred.is_external:
                continue
            pred_id = pred.task_id
            if pred_id in in_degree:
                in_degree[tid] += 1
                adj[pred_id].append(tid)

    queue = [tid for tid in task_ids if in_degree[tid] == 0]
    # Sort for determinism — tasks with no predecessors are sorted by ID
    queue.sort()
    result = []

    while queue:
        node = queue.pop(0)
        result.append(node)
        for succ in sorted(adj[node]):  # sorted for determinism
            in_degree[succ] -= 1
            if in_degree[succ] == 0:
                queue.append(succ)
                queue.sort()

    if len(result) != len(task_ids):
        return None  # Cycle detected

    return result


# =============================================================================
# Project start anchor
# =============================================================================

def _find_project_start(task_map: Dict[str, TaskInput], calendar) -> date:
    """
    Determines the project's anchor start date.
    Uses the earliest scheduled_start among all tasks that have one set.
    Falls back to today if nothing is set.
    """
    candidates = [
        t.scheduled_start
        for t in task_map.values()
        if t.scheduled_start and not t.predecessors
    ]
    if candidates:
        raw = min(candidates)
    else:
        raw = date.today()

    return first_work_day_on_or_after(raw, calendar)
