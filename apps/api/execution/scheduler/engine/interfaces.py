"""
CPM Engine I/O Contracts — exactly matching Constitution §7.2 and §7.3.

Layer 3 rule (Constitution §1 / Tech Arch §1):
    The engine takes JSON in, returns JSON out.
    ZERO DB access. ZERO side effects. Purely deterministic.

The API (Layer 2) owns all persistence. It passes data into the engine
and persists the result via MongoDB bulkWrite transaction.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import date
from enum import Enum


# =============================================================================
# Calendar (passed into every engine invocation)
# =============================================================================

@dataclass
class EngineCalendar:
    """
    Project calendar fed into the engine.
    Matches the `calendar` field in Constitution §7.2.
    """
    work_days: List[int]          # ISO weekday integers: 1=Mon…7=Sun
    holidays: List[date]          # Non-working dates even on work_days
    shift_start: str = "09:00"    # For future hour-level scheduling (MVP: day-level only)
    shift_end: str = "18:00"


@dataclass
class ResourceCalendar:
    """Per-resource calendar override — §7.2 `resource_calendars` array."""
    resource_id: str
    work_days: List[int]
    holidays: List[date]


# =============================================================================
# Task input (Constitution §7.2 tasks array)
# =============================================================================

@dataclass
class PredecessorInput:
    """One entry in a task's predecessors array."""
    task_id: str
    project_id: Optional[str]      # None = same project
    type: str = "FS"               # FS | SS | FF | SF
    lag_days: int = 0              # Negative = lead
    is_external: bool = False
    strength: str = "hard"         # hard | soft


@dataclass
class TaskInput:
    """
    Single task as passed to the engine (Constitution §7.2 task shape).
    The engine ONLY reads these fields — it never reads from the DB.
    """
    task_id: str
    task_mode: str                  # "Auto" | "Manual"
    predecessors: List[PredecessorInput]
    constraint_type: str            # ASAP | ALAP | SNET | SNLT | FNET | FNLT | MSO | MFO
    constraint_date: Optional[date]
    scheduled_start: Optional[date]
    scheduled_finish: Optional[date]
    scheduled_duration: int         # Working days. 0 for milestones.
    actual_start: Optional[date]
    actual_finish: Optional[date]
    percent_complete: int           # 0-100
    is_milestone: bool
    deadline: Optional[date]
    parent_id: Optional[str]
    is_summary: bool
    summary_type: Optional[str]     # "auto" | "manual" | None
    assigned_resources: List[str]   # resource_ids


# =============================================================================
# Calculation request (Constitution §7.2)
# =============================================================================

@dataclass
class CalculationRequest:
    """
    Full input package to the CPM engine.
    Assembled by the API (Layer 2) from DB state, then passed to engine.
    """
    project_id: str
    calendar: EngineCalendar
    tasks: List[TaskInput]
    resource_calendars: List[ResourceCalendar] = field(default_factory=list)


# =============================================================================
# Engine output — per-task result (Constitution §7.3 tasks array)
# =============================================================================

@dataclass
class TaskResult:
    """
    CPM calculation output for a single task (Constitution §7.3).
    The API merges this with the stored task document before persisting.
    """
    task_id: str
    scheduled_start: date
    scheduled_finish: date
    scheduled_duration: int         # Working days (recalculated if Auto mode)
    early_start: date
    early_finish: date
    late_start: date
    late_finish: date
    total_slack: int                # Working days. Negative = deadline breach.
    is_critical: bool               # total_slack == 0
    deadline_variance_days: Optional[int]   # scheduled_finish - deadline. Positive = breached.
    is_deadline_breached: bool


# =============================================================================
# Engine warnings (Constitution §7.3)
# =============================================================================

class WarningType(str, Enum):
    RESOURCE_OVERALLOCATION    = "resource_overallocation"
    SOFT_DEPENDENCY_VIOLATED   = "soft_dependency_violated"
    CONSTRAINT_CONFLICT        = "constraint_conflict"
    DEADLINE_BREACHED          = "deadline_breached"
    MILESTONE_DATE_SHIFTED     = "milestone_date_shifted"


@dataclass
class EngineWarning:
    type: WarningType
    detail: str
    task_id: Optional[str] = None


# =============================================================================
# Engine errors (per-task failures that don't abort the whole run)
# =============================================================================

@dataclass
class EngineError:
    task_id: str
    error: str


# =============================================================================
# Calculation response (Constitution §7.3)
# =============================================================================

class CalculationStatus(str, Enum):
    SUCCESS         = "success"
    PARTIAL_FAILURE = "partial_failure"  # Some tasks failed, rest succeeded
    FAILURE         = "failure"           # Entire calculation failed


@dataclass
class CalculationResponse:
    """
    Full output from the CPM engine (Constitution §7.3).
    Returned to the API, which then:
        1. Merges financial data (from $lookup pipelines)
        2. Persists via MongoDB bulkWrite transaction
        3. Returns Constitution §7.4 response to the client
    """
    project_id: str
    calculation_version: str        # UUID generated by the engine
    calculated_at: str              # ISO8601 UTC timestamp
    status: CalculationStatus
    errors: List[EngineError]
    tasks: List[TaskResult]
    critical_path: List[str]        # Ordered list of task_ids on critical path
    warnings: List[EngineWarning]
