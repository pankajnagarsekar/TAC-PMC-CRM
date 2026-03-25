"""
Shared enums, constants, and base types for the Enterprise PPM Scheduler.
This is the Living Types file — updated at every phase boundary.

Constitution Reference: §1 (stack), §2 (invariants), §5 (state machine),
                        §8 (lifecycle), §12 (RBAC), §13 (precision)
"""
from enum import Enum
from typing import Annotated
from decimal import Decimal
from bson import ObjectId
from pydantic import BeforeValidator


# =============================================================================
# PyObjectId — MongoDB ObjectId ↔ string bridge (shared with legacy models)
# =============================================================================
def validate_object_id(v):
    if isinstance(v, ObjectId):
        return str(v)
    if isinstance(v, str) and ObjectId.is_valid(v):
        return v
    raise ValueError(f"Invalid ObjectId: {v!r}")


PyObjectId = Annotated[str, BeforeValidator(validate_object_id)]


# =============================================================================
# Task State Machine (Constitution §5)
# =============================================================================
class TaskStatus(str, Enum):
    DRAFT = "draft"
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CLOSED = "closed"


# Valid state transitions — used by state_machine validator
# Key = current state, Value = set of allowable next states
TASK_STATE_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.DRAFT:        {TaskStatus.NOT_STARTED},
    TaskStatus.NOT_STARTED:  {TaskStatus.IN_PROGRESS, TaskStatus.CLOSED},
    TaskStatus.IN_PROGRESS:  {TaskStatus.COMPLETED, TaskStatus.NOT_STARTED},  # reopen → NOT_STARTED
    TaskStatus.COMPLETED:    {TaskStatus.IN_PROGRESS, TaskStatus.CLOSED},
    TaskStatus.CLOSED:       set(),  # terminal
}


# =============================================================================
# Task Mode
# =============================================================================
class TaskMode(str, Enum):
    AUTO = "Auto"
    MANUAL = "Manual"


# =============================================================================
# Dependency Types (Constitution §7.2)
# =============================================================================
class DependencyType(str, Enum):
    FS = "FS"  # Finish-to-Start (default)
    SS = "SS"  # Start-to-Start
    FF = "FF"  # Finish-to-Finish
    SF = "SF"  # Start-to-Finish


class DependencyStrength(str, Enum):
    HARD = "hard"   # Engine enforces — violation blocks
    SOFT = "soft"   # Engine warns but allows violation


# =============================================================================
# Constraint Types (Constitution §4 Step 3, Schema §1.3)
# =============================================================================
class ConstraintType(str, Enum):
    ASAP = "ASAP"    # As Soon As Possible (default)
    ALAP = "ALAP"    # As Late As Possible
    SNET = "SNET"    # Start No Earlier Than
    SNLT = "SNLT"    # Start No Later Than
    FNET = "FNET"    # Finish No Earlier Than
    FNLT = "FNLT"    # Finish No Later Than
    MSO  = "MSO"     # Must Start On
    MFO  = "MFO"     # Must Finish On


# Constraints that REQUIRE a constraint_date
CONSTRAINTS_REQUIRING_DATE: set[ConstraintType] = {
    ConstraintType.SNET,
    ConstraintType.SNLT,
    ConstraintType.FNET,
    ConstraintType.FNLT,
    ConstraintType.MSO,
    ConstraintType.MFO,
}


# =============================================================================
# Summary Task Type (Schema §1.3)
# =============================================================================
class SummaryType(str, Enum):
    AUTO   = "auto"    # Rollup rules enforced — parent fields read-only
    MANUAL = "manual"  # Admin can override fields


# =============================================================================
# Project Lifecycle (Constitution §8)
# =============================================================================
class ProjectStatus(str, Enum):
    DRAFT                  = "draft"
    PLANNING               = "planning"
    ACTIVE                 = "active"
    SUBSTANTIALLY_COMPLETE = "substantially_complete"
    CLOSED                 = "closed"


class SystemState(str, Enum):
    DRAFT       = "draft"        # Pre-first CPM calculation
    INITIALIZED = "initialized"  # Post-first successful CPM
    ACTIVE      = "active"       # Live updates flowing
    LOCKED      = "locked"       # Baseline enforced


# =============================================================================
# Resource Types (Schema §1.2)
# =============================================================================
class ResourceType(str, Enum):
    PERSONNEL = "Personnel"
    VENDOR    = "Vendor"
    MACHINERY = "Machinery"


class CostRateType(str, Enum):
    HOURLY = "hourly"
    DAILY  = "daily"
    FIXED  = "fixed"


# =============================================================================
# Audit / Change Source (Schema §1.3, §1.5)
# =============================================================================
class ChangeSource(str, Enum):
    GANTT_DRAG    = "gantt_drag"
    KANBAN_DROP   = "kanban_drop"
    GRID_EDIT     = "grid_edit"
    DPR_SYNC      = "dpr_sync"
    IMPORT        = "import"
    API           = "api"
    AI_SUGGESTION = "ai_suggestion"
    ENGINE_RECALC = "engine_recalc"


class AuditAction(str, Enum):
    TASK_CREATED            = "task_created"
    TASK_UPDATED            = "task_updated"
    TASK_DELETED            = "task_deleted"
    BASELINE_LOCKED         = "baseline_locked"
    SCHEDULE_RECALCULATED   = "schedule_recalculated"
    DEPENDENCY_ADDED        = "dependency_added"
    DEPENDENCY_REMOVED      = "dependency_removed"
    RESOURCE_ASSIGNED       = "resource_assigned"
    IMPORT_COMPLETED        = "import_completed"


# =============================================================================
# RBAC Roles (Constitution §12)
# =============================================================================
class SchedulerRole(str, Enum):
    SUPER_ADMIN      = "super_admin"
    PROJECT_MANAGER  = "project_manager"
    SUPERVISOR       = "supervisor"
    CLIENT           = "client"
    VIEWER           = "viewer"


# =============================================================================
# Cost Variance Flag (Constitution §2.3, Schema §2.3)
# =============================================================================
class CostVarianceFlag(str, Enum):
    ON_BUDGET = "on_budget"
    OVERRUN   = "overrun"
    UNDERRUN  = "underrun"


# =============================================================================
# Hard System Limits (Constitution §10)
# =============================================================================
MAX_TASKS_PER_PROJECT       = 10_000
MAX_DEPENDENCIES_PER_TASK   = 50
WARN_DEPENDENCIES_PER_TASK  = 30
MAX_CONCURRENT_USERS        = 25
MAX_BASELINES_PER_PROJECT   = 11
MAX_PROJECTS_IN_PORTFOLIO   = 50
CPM_TIMEOUT_SECONDS         = 10
API_REQUEST_TIMEOUT_SECONDS = 30

# =============================================================================
# Precision (Constitution §13)
# =============================================================================
CURRENCY_DECIMAL_PLACES = 2
PERCENTAGE_MAX          = 100
PERCENTAGE_MIN          = 0
