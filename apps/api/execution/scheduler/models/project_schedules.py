"""
project_schedules collection model — The Master Grid.
Central document for every task/activity in a project.

Constitution Reference: §2 (invariants), §4 (pipeline), §5 (state machine),
                        §6 (rollup rules), §7 (data contracts), §12 (RBAC), §13 (precision)
Schema Reference: §1.3
"""
from datetime import datetime, date, timezone
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator, model_validator
from .shared_types import (
    PyObjectId,
    TaskStatus,
    TaskMode,
    DependencyType,
    DependencyStrength,
    ConstraintType,
    SummaryType,
    ChangeSource,
    CONSTRAINTS_REQUIRING_DATE,
    MAX_DEPENDENCIES_PER_TASK,
    WARN_DEPENDENCIES_PER_TASK,
    PERCENTAGE_MIN,
    PERCENTAGE_MAX,
)


# =============================================================================
# Predecessor Sub-document (Constitution §7.2)
# =============================================================================
class Predecessor(BaseModel):
    """
    Embedded object within project_schedules.predecessors array.
    Represents a single dependency relationship to another task.
    """
    task_id: PyObjectId = Field(..., description="The predecessor task's ObjectId")

    # [GAP-FIX] null = same project; set for cross-project dependencies
    project_id: Optional[PyObjectId] = Field(
        default=None,
        description="Null means same project. Set to foreign project_id for cross-project deps.",
    )

    # [GAP-FIX] Derived flag — True when project_id differs from current task's project
    is_external: bool = Field(
        default=False,
        description="True when project_id differs from the owning task's project_id",
    )

    type: DependencyType = Field(
        default=DependencyType.FS,
        description="FS | SS | FF | SF",
    )

    # Negative = lead (accelerate), positive = lag (delay)
    lag_days: int = Field(
        default=0,
        description="Working-day lag. Negative values = lead time.",
    )

    # [GAP-FIX] Enforcement level
    strength: DependencyStrength = Field(
        default=DependencyStrength.HARD,
        description="Hard = engine enforces; Soft = warns only",
    )

    model_config = {"arbitrary_types_allowed": True}


# =============================================================================
# Project Schedule Task Document
# =============================================================================
class ProjectScheduleTask(BaseModel):
    """
    MongoDB document for the `project_schedules` collection.
    One document per task/activity/milestone.

    Key Invariants (Constitution §2.1):
    - scheduled_finish >= scheduled_start
    - milestone: scheduled_duration == 0
    - non-milestone: scheduled_duration > 0
    - 0 <= percent_complete <= 100
    - version incremented on every write (optimistic locking)
    """

    # -------------------------------------------------------------------------
    # System fields
    # -------------------------------------------------------------------------
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    task_id: Optional[PyObjectId] = Field(
        default=None,
        description="Explicit task ObjectId (same as _id; exposed for clarity in engine I/O)",
    )
    project_id: PyObjectId = Field(..., description="Owning project")
    parent_id: Optional[PyObjectId] = Field(
        default=None,
        description="Parent task ObjectId for WBS hierarchy. Null = root task.",
    )
    version: int = Field(
        default=1,
        ge=1,
        description="Optimistic lock counter — incremented on EVERY write (Constitution §2.2)",
    )

    # [GAP-FIX] Immutable stable reference — used for WO/PC linkage and imports
    # Generated ONCE on creation, NEVER modified. NOT the same as wbs_code.
    external_ref_id: str = Field(
        ...,
        description="Immutable stable reference. Generated once. Never modified. Used for WO/PC joins.",
    )

    # [GAP-FIX] Gap-based float ordering for stable WBS display without re-indexing
    # New tasks: (prev.sort_index + next.sort_index) / 2
    sort_index: float = Field(
        default=1000.0,
        description="Gap-based float for display ordering. New items use midpoint of neighbours.",
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    # -------------------------------------------------------------------------
    # Identity fields
    # -------------------------------------------------------------------------
    # Recalculated on reorder — NOT stable. Use external_ref_id for joins.
    wbs_code: str = Field(..., description="e.g. '1.1.2'. Recalculated on reorder.")
    category_code: str = Field(default="", description="e.g. 'CIV', 'MEP', 'STR'")
    task_name: str = Field(..., min_length=1, max_length=500)
    task_mode: TaskMode = Field(default=TaskMode.AUTO)
    is_milestone: bool = Field(default=False)
    is_active: bool = Field(
        default=True,
        description="Soft-disable for what-if toggling. Inactive tasks are excluded from CPM.",
    )

    # [GAP-FIX] Summary task flags
    is_summary: bool = Field(
        default=False,
        description="True for parent/summary tasks whose dates are rolled up from children",
    )
    summary_type: Optional[SummaryType] = Field(
        default=None,
        description="auto = rollup enforced; manual = admin can override. Null for leaf tasks.",
    )

    # [GAP-FIX] Task lifecycle state — governed by state machine (Constitution §5)
    task_status: TaskStatus = Field(default=TaskStatus.DRAFT)

    # -------------------------------------------------------------------------
    # Baseline (The Contract)
    # -------------------------------------------------------------------------
    baseline_start: Optional[date] = None
    baseline_finish: Optional[date] = None
    baseline_duration: Optional[int] = Field(
        default=None,
        ge=0,
        description="Working days. 0 for milestones.",
    )
    baseline_cost: Optional[Decimal] = Field(
        default=None,
        ge=Decimal("0"),
        description="Planned cost. Stored as Decimal128 in MongoDB.",
    )
    deadline: Optional[date] = Field(
        default=None,
        description="Hard deadline for deadline variance calculation",
    )

    # [GAP-FIX] Persisted for alerting and audit queries
    deadline_variance_days: Optional[int] = Field(
        default=None,
        description="scheduled_finish - deadline in working days. Positive = breached.",
    )
    is_deadline_breached: bool = Field(
        default=False,
        description="True if deadline_variance_days > 0",
    )

    # -------------------------------------------------------------------------
    # Constraints (Constitution §4 Step 3)
    # -------------------------------------------------------------------------
    # [GAP-FIX] Default ASAP
    constraint_type: ConstraintType = Field(default=ConstraintType.ASAP)
    constraint_date: Optional[date] = Field(
        default=None,
        description="Required when constraint_type is not ASAP/ALAP",
    )

    # -------------------------------------------------------------------------
    # Dependencies
    # -------------------------------------------------------------------------
    predecessors: List[Predecessor] = Field(
        default_factory=list,
        description=f"Max {MAX_DEPENDENCIES_PER_TASK} predecessors (warn at {WARN_DEPENDENCIES_PER_TASK})",
    )

    # -------------------------------------------------------------------------
    # CPM Engine Output (Constitution §4 Step 4)
    # -------------------------------------------------------------------------
    scheduled_start: Optional[date] = None
    scheduled_finish: Optional[date] = None
    scheduled_duration: Optional[int] = Field(
        default=None,
        ge=0,
        description="Working days. Engine-calculated unless task_mode=Manual.",
    )

    # [GAP-FIX] Persisted float dates from CPM forward/backward pass
    early_start: Optional[date] = None
    early_finish: Optional[date] = None
    late_start: Optional[date] = None
    late_finish: Optional[date] = None

    # -------------------------------------------------------------------------
    # Live Execution fields
    # -------------------------------------------------------------------------
    actual_start: Optional[date] = None
    actual_finish: Optional[date] = None
    percent_complete: int = Field(
        default=0,
        ge=PERCENTAGE_MIN,
        le=PERCENTAGE_MAX,
        description="0-100. Parent rollup = weighted average by baseline_cost (Constitution §6).",
    )

    # [GAP-FIX] Multiple resources per task
    assigned_resources: List[PyObjectId] = Field(
        default_factory=list,
        description="List of enterprise_resource ObjectIds assigned to this task",
    )

    # -------------------------------------------------------------------------
    # Analytics
    # -------------------------------------------------------------------------
    total_slack: Optional[int] = Field(
        default=None,
        description="Working days. Can be negative when deadline is breached.",
    )
    is_critical: bool = Field(
        default=False,
        description="True when total_slack == 0",
    )
    ai_status_flag: Optional[str] = None

    # [GAP-FIX] AI suggestion tracking for feedback loop learning
    ai_suggested_duration: Optional[int] = Field(
        default=None,
        description="What the AI predicted. Compared against actual for model improvement.",
    )
    ai_confidence_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="AI prediction confidence (0.0-1.0). Displayed during AI suggestion review.",
    )

    # -------------------------------------------------------------------------
    # Audit fields [GAP-FIX]
    # -------------------------------------------------------------------------
    last_change_source: Optional[ChangeSource] = None
    last_change_by: Optional[PyObjectId] = Field(
        default=None,
        description="ObjectId of the user who triggered the last change",
    )
    last_change_at: Optional[datetime] = None

    # =========================================================================
    # Validators
    # =========================================================================
    @field_validator("predecessors")
    @classmethod
    def validate_predecessor_count(cls, v: List[Predecessor]) -> List[Predecessor]:
        if len(v) > MAX_DEPENDENCIES_PER_TASK:
            raise ValueError(
                f"Task may not have more than {MAX_DEPENDENCIES_PER_TASK} predecessors. "
                f"Got {len(v)}."
            )
        return v

    @model_validator(mode="after")
    def validate_schedule_invariants(self) -> "ProjectScheduleTask":
        """
        Enforces Constitution §2.1 schedule invariants post-initialisation.
        Only applied when both dates are present (engine output).
        """
        # scheduled_finish >= scheduled_start
        if self.scheduled_start and self.scheduled_finish:
            if self.scheduled_finish < self.scheduled_start:
                raise ValueError(
                    f"scheduled_finish ({self.scheduled_finish}) must be >= "
                    f"scheduled_start ({self.scheduled_start})"
                )

        # Milestone: duration must be 0
        if self.is_milestone and self.scheduled_duration is not None:
            if self.scheduled_duration != 0:
                raise ValueError(
                    "Milestone tasks must have scheduled_duration == 0"
                )

        # Non-milestone: duration must be > 0 (when set)
        if not self.is_milestone and self.scheduled_duration is not None:
            if self.scheduled_duration == 0:
                raise ValueError(
                    "Non-milestone tasks must have scheduled_duration > 0"
                )

        # Constraint date required for non-ASAP/ALAP constraints
        if self.constraint_type not in (ConstraintType.ASAP, ConstraintType.ALAP):
            if self.constraint_date is None:
                raise ValueError(
                    f"constraint_date is required when constraint_type is {self.constraint_type}"
                )

        # actual_finish >= actual_start (when both set)
        if self.actual_start and self.actual_finish:
            if self.actual_finish < self.actual_start:
                raise ValueError(
                    f"actual_finish ({self.actual_finish}) must be >= "
                    f"actual_start ({self.actual_start})"
                )

        # is_summary implies summary_type is set
        if self.is_summary and self.summary_type is None:
            raise ValueError(
                "Summary tasks must have summary_type set (auto or manual)"
            )

        return self

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
    }


# =============================================================================
# Schedule Change Request (Constitution §7.1 — Frontend → API)
# =============================================================================
class ScheduleChangeRequest(BaseModel):
    """
    Inbound payload when any client triggers a schedule change.
    Used for all trigger_sources: gantt_drag, kanban_drop, grid_edit, etc.
    """
    task_id: PyObjectId
    project_id: PyObjectId
    changes: "TaskChanges"
    version: int = Field(..., ge=1, description="Optimistic lock — must match current DB version")
    trigger_source: ChangeSource
    idempotency_key: str = Field(
        ...,
        description="UUID for request deduplication. API caches response for 5 minutes.",
    )
    deleted_task_ids: Optional[List[PyObjectId]] = Field(default=None, description="Tasks to be marked as deleted")

    model_config = {"arbitrary_types_allowed": True}


class TaskChanges(BaseModel):
    """Partial update fields accepted from the frontend."""
    scheduled_start: Optional[date] = None
    scheduled_finish: Optional[date] = None
    scheduled_duration: Optional[int] = Field(default=None, ge=0)
    percent_complete: Optional[int] = Field(default=None, ge=0, le=100)
    actual_start: Optional[date] = None
    actual_finish: Optional[date] = None
    predecessors: Optional[List[Predecessor]] = None
    assigned_resources: Optional[List[PyObjectId]] = None
    task_mode: Optional[TaskMode] = None
    task_name: Optional[str] = None
    task_status: Optional[TaskStatus] = None
    ai_suggested_duration: Optional[int] = Field(default=None, ge=0)
    ai_confidence_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    ai_status_flag: Optional[str] = None

    model_config = {"arbitrary_types_allowed": True}


# Forward reference update
ScheduleChangeRequest.model_rebuild()


# =============================================================================
# Create / Update schemas
# =============================================================================
class ProjectScheduleTaskCreate(BaseModel):
    project_id: str
    parent_id: Optional[str] = None
    wbs_code: str
    task_name: str
    task_mode: TaskMode = TaskMode.AUTO
    is_milestone: bool = False
    is_summary: bool = False
    summary_type: Optional[SummaryType] = None
    category_code: str = ""
    constraint_type: ConstraintType = ConstraintType.ASAP
    constraint_date: Optional[date] = None
    baseline_start: Optional[date] = None
    baseline_finish: Optional[date] = None
    baseline_duration: Optional[int] = None
    baseline_cost: Optional[Decimal] = None
    deadline: Optional[date] = None
    predecessors: List[Predecessor] = Field(default_factory=list)
    assigned_resources: List[str] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}
