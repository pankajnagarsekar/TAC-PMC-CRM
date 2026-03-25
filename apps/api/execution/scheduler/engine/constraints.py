"""
Constraint System — applies task constraints to CPM output dates.

Constitution §4 Step 3: "Constraints bound the CPM output, not replace it."

All 8 constraint types from Schema §1.3:
    ASAP  — As Soon As Possible (default, no modification)
    ALAP  — As Late As Possible (uses Late Start from backward pass)
    SNET  — Start No Earlier Than: ES = max(ES, constraint_date)
    SNLT  — Start No Later Than: LS = min(LS, constraint_date) — enforced via warning
    FNET  — Finish No Earlier Than: EF = max(EF, constraint_date) → shifts ES
    FNLT  — Finish No Later Than: LF = min(LF, constraint_date) → warning if breached
    MSO   — Must Start On: ES = LF = constraint_date
    MFO   — Must Finish On: EF = LF = constraint_date → back-calculates ES

Key rule: Constraints BOUND the CPM result. They do NOT override
actual_start / actual_finish for in-progress tasks.
"""
from datetime import date
from typing import List, Optional

from .interfaces import TaskInput, EngineWarning, WarningType
from .calendar_utils import (
    first_work_day_on_or_after,
    last_work_day_on_or_before,
    subtract_work_days,
    add_work_days,
)


def apply_constraints(
    task: TaskInput,
    unconstrained_start: date,
    calendar,
    warnings: List[EngineWarning],
) -> date:
    """
    Applies the task's constraint to the CPM-computed unconstrained start date.

    Called during the Forward Pass, after dependency-driven ES is computed.
    Returns the final scheduled_start to use.

    Note: ALAP is handled in a post-pass (not here) because it requires
    the backward pass Late Start. ALAP tasks are flagged and adjusted after
    both passes complete. For the Forward Pass, ALAP tasks use ASAP dates.

    Args:
        task:                 The task being processed.
        unconstrained_start:  ES computed purely from dependencies.
        calendar:             Project calendar for working day math.
        warnings:             Mutable list — appended to when constraint conflicts arise.

    Returns:
        The constrained start date (never earlier than unconstrained_start for SNET/FNET,
        may be later for MSO/MFO).
    """
    ct = task.constraint_type
    cd = task.constraint_date
    duration = task.scheduled_duration

    # No constraint or ASAP — return as-is
    if ct in ("ASAP", None) or ct == "Auto":
        return unconstrained_start

    # ALAP — handled post backward-pass, use unconstrained_start for now
    if ct == "ALAP":
        return unconstrained_start

    # All remaining constraints require constraint_date
    if cd is None:
        warnings.append(EngineWarning(
            type=WarningType.CONSTRAINT_CONFLICT,
            detail=f"Task '{task.task_id}' has constraint type '{ct}' but no constraint_date. Treating as ASAP.",
            task_id=task.task_id,
        ))
        return unconstrained_start

    # ─── SNET: Start No Earlier Than ─────────────────────────────────────────
    if ct == "SNET":
        constrained = first_work_day_on_or_after(cd, calendar)
        return max(unconstrained_start, constrained)

    # ─── SNLT: Start No Later Than ────────────────────────────────────────────
    # SNLT is a warning constraint — if CPM pushes start past the limit, warn but allow.
    # The engine cannot make a task start earlier than its dependencies allow.
    if ct == "SNLT":
        snlt_date = first_work_day_on_or_after(cd, calendar)
        if unconstrained_start > snlt_date:
            warnings.append(EngineWarning(
                type=WarningType.CONSTRAINT_CONFLICT,
                detail=(
                    f"Task '{task.task_id}' SNLT constraint violated: "
                    f"CPM start {unconstrained_start} is after constraint date {snlt_date}. "
                    f"Dependencies prevent earlier start."
                ),
                task_id=task.task_id,
            ))
        return unconstrained_start  # Dependencies take priority

    # ─── FNET: Finish No Earlier Than ─────────────────────────────────────────
    # If CPM finish < constraint_date, push start forward so finish meets constraint.
    if ct == "FNET":
        fnet_finish = first_work_day_on_or_after(cd, calendar)
        # What start would give us this finish?
        if duration > 0:
            required_start = subtract_work_days(fnet_finish, duration, calendar)
        else:
            required_start = fnet_finish
        return max(unconstrained_start, required_start)

    # ─── FNLT: Finish No Later Than ────────────────────────────────────────────
    # Similar to SNLT — warning only. Cannot accelerate past dependencies.
    if ct == "FNLT":
        fnlt_finish = last_work_day_on_or_before(cd, calendar)
        # Compute what finish the CPM start would produce
        if duration > 0:
            cpm_finish = add_work_days(unconstrained_start, duration, calendar)
        else:
            cpm_finish = unconstrained_start
        if cpm_finish > fnlt_finish:
            warnings.append(EngineWarning(
                type=WarningType.CONSTRAINT_CONFLICT,
                detail=(
                    f"Task '{task.task_id}' FNLT constraint violated: "
                    f"CPM finish {cpm_finish} is after constraint date {fnlt_finish}. "
                    f"Dependencies prevent earlier completion."
                ),
                task_id=task.task_id,
            ))
        return unconstrained_start

    # ─── MSO: Must Start On ──────────────────────────────────────────────────
    # Fix the start to constraint_date regardless of dependency slack.
    if ct == "MSO":
        mso_date = first_work_day_on_or_after(cd, calendar)
        if unconstrained_start > mso_date:
            warnings.append(EngineWarning(
                type=WarningType.CONSTRAINT_CONFLICT,
                detail=(
                    f"Task '{task.task_id}' MSO constraint: dependency-driven start "
                    f"{unconstrained_start} is after MSO date {mso_date}. "
                    f"Task will be scheduled after its MSO date."
                ),
                task_id=task.task_id,
            ))
            return unconstrained_start  # Can't violate dependency
        return mso_date

    # ─── MFO: Must Finish On ─────────────────────────────────────────────────
    # Fix the finish to constraint_date → back-calculate start.
    if ct == "MFO":
        mfo_finish = first_work_day_on_or_after(cd, calendar)
        if duration > 0:
            mfo_start = subtract_work_days(mfo_finish, duration, calendar)
        else:
            mfo_start = mfo_finish
        if unconstrained_start > mfo_start:
            warnings.append(EngineWarning(
                type=WarningType.CONSTRAINT_CONFLICT,
                detail=(
                    f"Task '{task.task_id}' MFO constraint: dependencies push start to "
                    f"{unconstrained_start}, making MFO finish {mfo_finish} impossible. "
                    f"Using dependency-driven dates."
                ),
                task_id=task.task_id,
            ))
            return unconstrained_start
        return mfo_start

    # Unknown constraint — log and treat as ASAP
    warnings.append(EngineWarning(
        type=WarningType.CONSTRAINT_CONFLICT,
        detail=f"Unknown constraint type '{ct}' on task '{task.task_id}'. Treating as ASAP.",
        task_id=task.task_id,
    ))
    return unconstrained_start
