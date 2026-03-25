"""
CPM Engine Test Fixtures — 5 canonical datasets for Session 2.1.

Each fixture returns a CalculationRequest ready to feed into the engine.
Fixtures are designed to test specific engine behaviours.

Phase Feeding Map Session 2.1:
    1. Simple 3-task linear chain
    2. Parallel tasks with shared predecessor
    3. All 4 dependency types (FS/SS/FF/SF) with lag
    4. Task with deadline breach
    5. Circular dependency (must be rejected BEFORE engine runs)
"""
from datetime import date, timedelta
from .interfaces import (
    CalculationRequest,
    EngineCalendar,
    TaskInput,
    PredecessorInput,
    ResourceCalendar,
)

# ---------------------------------------------------------------------------
# Shared project calendar — Goa 6-day work week (Mon-Sat)
# ---------------------------------------------------------------------------
GOA_CALENDAR = EngineCalendar(
    work_days=[1, 2, 3, 4, 5, 6],    # Mon-Sat
    holidays=[],
    shift_start="09:00",
    shift_end="18:00",
)

# Reference project start — Monday 2026-03-30
PROJECT_START = date(2026, 3, 30)


def _task(
    task_id: str,
    duration: int,
    preds: list = None,
    constraint_type: str = "ASAP",
    constraint_date: date = None,
    is_milestone: bool = False,
    deadline: date = None,
    task_mode: str = "Auto",
    actual_start: date = None,
    actual_finish: date = None,
    percent_complete: int = 0,
    is_summary: bool = False,
    summary_type: str = None,
    parent_id: str = None,
) -> TaskInput:
    """Helper to build a TaskInput with sensible defaults."""
    return TaskInput(
        task_id=task_id,
        task_mode=task_mode,
        predecessors=preds or [],
        constraint_type=constraint_type,
        constraint_date=constraint_date,
        scheduled_start=PROJECT_START,
        scheduled_finish=PROJECT_START,
        scheduled_duration=duration,
        actual_start=actual_start,
        actual_finish=actual_finish,
        percent_complete=percent_complete,
        is_milestone=is_milestone,
        deadline=deadline,
        parent_id=parent_id,
        is_summary=is_summary,
        summary_type=summary_type,
        assigned_resources=[],
    )


def _pred(
    task_id: str,
    dep_type: str = "FS",
    lag: int = 0,
    strength: str = "hard",
    is_external: bool = False,
    project_id: str = None,
) -> PredecessorInput:
    return PredecessorInput(
        task_id=task_id,
        project_id=project_id,
        type=dep_type,
        lag_days=lag,
        is_external=is_external,
        strength=strength,
    )


# =============================================================================
# Fixture 1: Simple 3-task linear chain
#
#   A(5d) → B(3d) → C(4d)
#   All FS with no lag.
#   Expected behaviour:
#     A: ES=Mon 30 Mar,  EF=Fri  3 Apr  (5 working days Mon-Fri, skip Sun)
#     B: ES=Mon  6 Apr,  EF=Wed  8 Apr  (3 working days)
#     C: ES=Thu  9 Apr,  EF=Tue 14 Apr  (4 working days, skipping Sun 12 Apr)
#     All 3 tasks are critical (slack == 0)
# =============================================================================
def fixture_linear_chain() -> CalculationRequest:
    """Fixture 1: Simple A→B→C linear FS chain."""
    tasks = [
        _task("A", duration=5),
        _task("B", duration=3, preds=[_pred("A")]),
        _task("C", duration=4, preds=[_pred("B")]),
    ]
    return CalculationRequest(
        project_id="proj_linear",
        calendar=GOA_CALENDAR,
        tasks=tasks,
    )


# Expected results for Fixture 1 (used in tests)
FIXTURE_1_EXPECTED = {
    "A": {
        "early_start":  date(2026, 3, 30),
        "early_finish": date(2026, 4, 3),   # Mon-Fri (skip nothing, no Sunday in span)
        "is_critical": True,
    },
    "B": {
        "early_start":  date(2026, 4, 4),   # Sat after A finishes (Mon-Sat work week)
        "early_finish": date(2026, 4, 7),   # Sat+Mon+Tue = 3 days (skip Sun 5 Apr)
        "is_critical": True,
    },
    "C": {
        "early_start":  date(2026, 4, 8),   # Wed
        "early_finish": date(2026, 4, 11),  # Wed+Thu+Fri+Sat = 4 days
        "is_critical": True,
    },
}


# =============================================================================
# Fixture 2: Parallel tasks with shared predecessor
#
#   A(3d) → B(5d)
#   A(3d) → C(2d)
#   B(5d) → D(1d)
#   C(2d) → D(1d)
#
#   Expected behaviour:
#     A is predecessor to both B and C.
#     D starts after BOTH B and C finish (takes the later of the two).
#     B is on critical path (longer parallel branch).
#     C has positive slack.
# =============================================================================
def fixture_parallel_tasks() -> CalculationRequest:
    """Fixture 2: Diamond dependency graph with parallel paths."""
    tasks = [
        _task("A", duration=3),
        _task("B", duration=5, preds=[_pred("A")]),
        _task("C", duration=2, preds=[_pred("A")]),
        _task("D", duration=1, preds=[_pred("B"), _pred("C")]),
    ]
    return CalculationRequest(
        project_id="proj_parallel",
        calendar=GOA_CALENDAR,
        tasks=tasks,
    )


# Expected critical path: A → B → D (C has slack = 3 days)
FIXTURE_2_EXPECTED = {
    "critical_path_includes": ["A", "B", "D"],
    "C_has_positive_slack": True,
}


# =============================================================================
# Fixture 3: All 4 dependency types with lag
#
#   A(5d) ─FS+2─► B(4d)   Finish-to-Start with 2-day lag
#   A(5d) ─SS+1─► C(3d)   Start-to-Start with 1-day lag
#   B(4d) ─FF+0─► D(2d)   Finish-to-Finish with no lag
#   C(3d) ─SF─2─► E(6d)   Start-to-Finish with -2 day lag (lead)
#
#   This tests that the parser and engine handle all 4 types.
# =============================================================================
def fixture_all_dependency_types() -> CalculationRequest:
    """Fixture 3: FS/SS/FF/SF dependency types with lag and lead."""
    tasks = [
        _task("A", duration=5),
        _task("B", duration=4, preds=[_pred("A", dep_type="FS", lag=2)]),
        _task("C", duration=3, preds=[_pred("A", dep_type="SS", lag=1)]),
        _task("D", duration=2, preds=[_pred("B", dep_type="FF", lag=0)]),
        _task("E", duration=6, preds=[_pred("C", dep_type="SF", lag=-2)]),
    ]
    return CalculationRequest(
        project_id="proj_dep_types",
        calendar=GOA_CALENDAR,
        tasks=tasks,
    )


# =============================================================================
# Fixture 4: Task with deadline breach
#
#   A(3d) → B(10d) → C(2d)
#   C has a deadline 5 working days after project start.
#   C will obviously breach its deadline.
#
#   Expected behaviour:
#     C.is_deadline_breached == True
#     C.deadline_variance_days > 0
#     Engine should complete (not fail) — breach is a warning, not an error.
# =============================================================================
def fixture_deadline_breach() -> CalculationRequest:
    """Fixture 4: Task C breaches its deadline — engine completes with warning."""
    # Deadline: 5 working days from project start = Fri 3 Apr (Mon 30 Mar + 5d = Fri 3 Apr)
    # But C starts after A(3d) + B(10d) = 13 working days in, so it's well past deadline
    tight_deadline = date(2026, 4, 3)  # 5 working days from project start

    tasks = [
        _task("A", duration=3),
        _task("B", duration=10, preds=[_pred("A")]),
        _task("C", duration=2, preds=[_pred("B")], deadline=tight_deadline),
    ]
    return CalculationRequest(
        project_id="proj_deadline",
        calendar=GOA_CALENDAR,
        tasks=tasks,
    )


# Expected
FIXTURE_4_EXPECTED = {
    "C": {
        "is_deadline_breached": True,
        "deadline_variance_days_positive": True,
    }
}


# =============================================================================
# Fixture 5: Circular dependency (must be rejected BEFORE CPM runs)
#
#   A → B → C → A   (cycle)
#
#   Expected behaviour:
#     DAG validator catches the cycle.
#     Engine NEVER called — returns error before calculation.
#     Error message identifies the cycle path: "Task A → Task B → Task C → Task A"
# =============================================================================
def fixture_circular_dependency() -> CalculationRequest:
    """Fixture 5: A→B→C→A cycle — DAG validator must reject this."""
    tasks = [
        _task("A", duration=3, preds=[_pred("C")]),  # A depends on C (creates cycle)
        _task("B", duration=4, preds=[_pred("A")]),
        _task("C", duration=2, preds=[_pred("B")]),
    ]
    return CalculationRequest(
        project_id="proj_circular",
        calendar=GOA_CALENDAR,
        tasks=tasks,
    )


# Expected: DAG validation FAILS, engine is not called
FIXTURE_5_EXPECTED = {
    "dag_valid": False,
    "should_contain_cycle_path": True,
}


# =============================================================================
# Fixture 6: SNET constraint (bonus — tests constraint system)
#
#   A(2d) → B(3d)  but B has SNET=date far in the future
#   B cannot start before its constraint_date even though A finishes early.
# =============================================================================
def fixture_snet_constraint() -> CalculationRequest:
    """Fixture 6 (bonus): B has SNET constraint that delays its start."""
    snet_date = date(2026, 4, 20)  # Far future — B must wait

    tasks = [
        _task("A", duration=2),
        _task(
            "B", duration=3,
            preds=[_pred("A")],
            constraint_type="SNET",
            constraint_date=snet_date,
        ),
    ]
    return CalculationRequest(
        project_id="proj_snet",
        calendar=GOA_CALENDAR,
        tasks=tasks,
    )


FIXTURE_6_EXPECTED = {
    "B": {
        "scheduled_start_not_before": date(2026, 4, 20),
    }
}


# =============================================================================
# All fixtures accessible by name
# =============================================================================
ALL_FIXTURES = {
    "linear_chain":         fixture_linear_chain,
    "parallel_tasks":       fixture_parallel_tasks,
    "all_dependency_types": fixture_all_dependency_types,
    "deadline_breach":      fixture_deadline_breach,
    "circular_dependency":  fixture_circular_dependency,
    "snet_constraint":      fixture_snet_constraint,
}
