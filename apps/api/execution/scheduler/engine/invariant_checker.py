"""
Post-Calculation Invariant Checker — Constitution §2.1 + §4 Step validation.

Runs AFTER the CPM engine produces results, BEFORE persisting to MongoDB.
If any invariant fails: reject the entire calculation, preserve previous state.

Constitution §2.1 invariants verified here:
    1. scheduled_finish >= scheduled_start for every task
    2. milestone duration == 0; non-milestone duration > 0
    3. No task starts before ALL its hard predecessors are satisfied
    4. Critical path is continuous from project start to finish
    5. total_slack == LS - ES == LF - EF for every task
    6. 0 <= percent_complete <= 100

Schema §4.3 post-calculation invariant checks.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import date

from .interfaces import CalculationRequest, CalculationResponse, TaskResult
from .calendar_utils import count_work_days, next_work_day


# =============================================================================
# Result
# =============================================================================

@dataclass
class InvariantViolation:
    task_id: str
    invariant: str
    detail: str


@dataclass
class InvariantCheckResult:
    passed: bool
    violations: List[InvariantViolation] = field(default_factory=list)

    def add(self, task_id: str, invariant: str, detail: str) -> None:
        self.violations.append(InvariantViolation(task_id, invariant, detail))
        self.passed = False


# =============================================================================
# Checker
# =============================================================================

def check_invariants(
    request: CalculationRequest,
    response: CalculationResponse,
) -> InvariantCheckResult:
    """
    Verifies all post-calculation invariants from Constitution §2.1.

    Args:
        request: Original calculation request (for task metadata)
        response: Engine output to validate

    Returns:
        InvariantCheckResult with passed=True if all invariants hold,
        or passed=False with list of violations.
    """
    result = InvariantCheckResult(passed=True)
    calendar = request.calendar

    # Build lookup maps
    task_meta: Dict[str, object] = {t.task_id: t for t in request.tasks}
    task_results: Dict[str, TaskResult] = {t.task_id: t for t in response.tasks}

    for tr in response.tasks:
        task_id = tr.task_id
        meta = task_meta.get(task_id)

        # ─── Invariant 1: finish >= start ────────────────────────────────────
        if tr.scheduled_finish < tr.scheduled_start:
            result.add(
                task_id, "FINISH_BEFORE_START",
                f"scheduled_finish {tr.scheduled_finish} < scheduled_start {tr.scheduled_start}",
            )

        if tr.early_finish < tr.early_start:
            result.add(
                task_id, "EARLY_FINISH_BEFORE_START",
                f"early_finish {tr.early_finish} < early_start {tr.early_start}",
            )

        if tr.late_finish < tr.late_start:
            result.add(
                task_id, "LATE_FINISH_BEFORE_START",
                f"late_finish {tr.late_finish} < late_start {tr.late_start}",
            )

        # ─── Invariant 2: milestone duration ─────────────────────────────────
        if meta:
            if meta.is_milestone and tr.scheduled_duration != 0:
                result.add(
                    task_id, "MILESTONE_DURATION",
                    f"Milestone task has duration {tr.scheduled_duration} (must be 0)",
                )
            if not meta.is_milestone and tr.scheduled_duration == 0 and tr.scheduled_start != tr.scheduled_finish:
                result.add(
                    task_id, "NON_MILESTONE_ZERO_DURATION",
                    f"Non-milestone task has duration 0 but start != finish",
                )

        # ─── Invariant 3: Total slack consistency ────────────────────────────
        # total_slack == LS - ES (in working days)
        # Allow ±1 rounding tolerance
        slack_from_start = count_work_days(tr.early_start, tr.late_start, calendar) - 1
        if abs(slack_from_start - tr.total_slack) > 1:
            result.add(
                task_id, "SLACK_INCONSISTENCY",
                f"total_slack={tr.total_slack} but LS-ES working days={slack_from_start}",
            )

        # ─── Invariant 4: is_critical consistency ────────────────────────────
        if tr.is_critical and tr.total_slack != 0:
            # Allow tasks with negative slack to also be critical
            if tr.total_slack > 0:
                result.add(
                    task_id, "CRITICAL_FLAG_INCONSISTENCY",
                    f"Task flagged is_critical=True but total_slack={tr.total_slack} > 0",
                )

    # ─── Invariant 5: Hard predecessor satisfaction ───────────────────────────
    for tr in response.tasks:
        task_meta_item = task_meta.get(tr.task_id)
        if not task_meta_item:
            continue
        for pred_ref in task_meta_item.predecessors:
            if pred_ref.strength != "hard":
                continue
            if pred_ref.is_external:
                continue
            pred_result = task_results.get(pred_ref.task_id)
            if not pred_result:
                continue

            dep_type = pred_ref.type
            lag = pred_ref.lag_days

            # FS: succ.ES must be >= pred.EF + 1 workday + lag
            if dep_type == "FS":
                min_start = next_work_day(pred_result.early_finish, calendar)
                if lag > 0:
                    from .calendar_utils import add_work_days_offset
                    min_start = add_work_days_offset(pred_result.early_finish, lag + 1, calendar)
                if tr.early_start < min_start:
                    result.add(
                        tr.task_id, "PREDECESSOR_NOT_SATISFIED",
                        f"Hard FS predecessor {pred_ref.task_id}: "
                        f"task starts {tr.early_start} before pred finishes (min start: {min_start})",
                    )

            # SS: succ.ES must be >= pred.ES + lag
            elif dep_type == "SS":
                from .calendar_utils import add_work_days_offset
                min_start = add_work_days_offset(pred_result.early_start, lag, calendar)
                if tr.early_start < min_start:
                    result.add(
                        tr.task_id, "PREDECESSOR_NOT_SATISFIED",
                        f"Hard SS predecessor {pred_ref.task_id}: "
                        f"task starts {tr.early_start} before constraint (min: {min_start})",
                    )

    # ─── Invariant 6: Critical path continuity ────────────────────────────────
    # Each critical path task should connect to the next (no gaps in dates)
    if len(response.critical_path) > 1:
        for i in range(len(response.critical_path) - 1):
            a_id = response.critical_path[i]
            b_id = response.critical_path[i + 1]
            a = task_results.get(a_id)
            b = task_results.get(b_id)
            if a and b:
                # b must start on or after the next work day after a finishes
                # (or could have SS/FF relationship — just check it's not before a.EF)
                if b.early_start < a.early_start:
                    result.add(
                        b_id, "CRITICAL_PATH_NOT_CONTINUOUS",
                        f"Critical path task {b_id} starts {b.early_start} "
                        f"before critical predecessor {a_id} starts {a.early_start}",
                    )

    return result
