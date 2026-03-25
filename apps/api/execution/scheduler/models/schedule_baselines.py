"""
schedule_baselines collection model — Immutable Snapshots.
Stores up to 11 historical schedule snapshots per project for variance tracking.

Constitution Reference: §2.2 (baseline immutability), §9 (earned value)
Schema Reference: §1.4
"""
from datetime import datetime, timezone
from typing import Optional, List, Any, Dict
from decimal import Decimal
from pydantic import BaseModel, Field, model_validator
from .shared_types import PyObjectId, MAX_BASELINES_PER_PROJECT


# =============================================================================
# Financial Snapshot — captured at baseline lock time
# =============================================================================
class BaselineFinancialSnapshot(BaseModel):
    """
    [GAP-FIX] Financial totals frozen at baseline lock time.
    Enables accurate historical S-Curve comparison without re-aggregating legacy WO/PC data.
    """
    project_total_baseline_cost: Decimal = Field(
        default=Decimal("0"),
        ge=Decimal("0"),
        description="Sum of all task baseline_costs at time of lock",
    )
    total_wo_value: Decimal = Field(
        default=Decimal("0"),
        ge=Decimal("0"),
        description="Total Work Order value aggregated from legacy work_orders at lock time",
    )
    total_payment_value: Decimal = Field(
        default=Decimal("0"),
        ge=Decimal("0"),
        description="Total approved+paid certificate value from legacy payment_certificates at lock time",
    )

    model_config = {"arbitrary_types_allowed": True}


# =============================================================================
# Baseline Task Snapshot — individual task frozen state
# =============================================================================
class BaselineTaskSnapshot(BaseModel):
    """
    Frozen copy of a single task's schedule fields at baseline lock time.
    Financial fields are NOT stored here — use financial_snapshot for totals.
    The snapshot_data array within ScheduleBaseline contains these objects.
    """
    task_id: PyObjectId
    wbs_code: str
    task_name: str
    external_ref_id: str  # Immutable reference preserved in snapshot
    is_milestone: bool
    baseline_start: Optional[str] = None   # ISO8601 string for frozen archival
    baseline_finish: Optional[str] = None
    baseline_duration: Optional[int] = None
    baseline_cost: Optional[Decimal] = None
    scheduled_start: Optional[str] = None
    scheduled_finish: Optional[str] = None
    scheduled_duration: Optional[int] = None
    percent_complete: int = 0

    model_config = {"arbitrary_types_allowed": True}


# =============================================================================
# Schedule Baseline Document
# =============================================================================
class ScheduleBaseline(BaseModel):
    """
    MongoDB document for the `schedule_baselines` collection.

    Key Invariants (Constitution §2.2):
    - is_immutable is ALWAYS True after creation
    - No API endpoint may modify this document after locked_at is set
    - Maximum MAX_BASELINES_PER_PROJECT (11) baselines per project
    - DB middleware must reject any update/delete on is_immutable == True documents
    """
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    project_id: PyObjectId = Field(..., description="Owning project")

    # Baseline sequence number (1-11)
    baseline_number: int = Field(
        ...,
        ge=1,
        le=MAX_BASELINES_PER_PROJECT,
        description=f"Sequential number 1-{MAX_BASELINES_PER_PROJECT}. UI disables lock button at max.",
    )

    # Human-readable label (optional, e.g. "Contract Baseline", "Re-baseline post-scope-change")
    label: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Optional descriptive label for this baseline",
    )

    # Full task snapshot at lock time
    snapshot_data: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Frozen array of all task objects at lock time. "
                    "Use BaselineTaskSnapshot shape for validation.",
    )

    # [GAP-FIX] Financial totals frozen at lock
    financial_snapshot: BaselineFinancialSnapshot = Field(
        default_factory=BaselineFinancialSnapshot,
        description="Financial totals captured at baseline lock time for S-Curve accuracy",
    )

    # Lock provenance
    locked_by: PyObjectId = Field(..., description="ObjectId of the user who locked this baseline")
    locked_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when this baseline was locked",
    )

    # [GAP-FIX] Hard immutability flag — DB middleware reads this before allowing writes
    is_immutable: bool = Field(
        default=True,
        description="ALWAYS True after creation. DB middleware rejects updates/deletes on immutable docs.",
    )

    @model_validator(mode="after")
    def enforce_immutability_flag(self) -> "ScheduleBaseline":
        """
        is_immutable MUST be True. This is the system-level enforcement of
        Constitution §2.2 — baseline immutability.
        """
        if not self.is_immutable:
            raise ValueError(
                "is_immutable must always be True for schedule baselines. "
                "No baseline document may be modified after creation."
            )
        return self

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
    }


# =============================================================================
# Baseline Comparison Result (computed in-memory, never persisted)
# =============================================================================
class BaselineComparisonResult(BaseModel):
    """
    Output of baseline comparison engine (Phase 4, Session 4.3).
    Computed per task from two baseline snapshots.
    Never stored to DB.
    """
    task_id: str
    wbs_code: str
    task_name: str

    # Schedule variance
    baseline_a_start: Optional[str] = None
    baseline_a_finish: Optional[str] = None
    baseline_b_start: Optional[str] = None
    baseline_b_finish: Optional[str] = None
    schedule_variance_days: Optional[int] = Field(
        default=None,
        description="baseline_b.scheduled_finish - baseline_a.scheduled_finish in working days. Positive = slipped.",
    )

    # Cost variance
    baseline_a_cost: Optional[Decimal] = None
    baseline_b_cost: Optional[Decimal] = None
    cost_variance_percent: Optional[float] = Field(
        default=None,
        description="(baseline_b_cost - baseline_a_cost) / baseline_a_cost * 100",
    )

    model_config = {"arbitrary_types_allowed": True}


# =============================================================================
# Create schema (API request to lock a baseline)
# =============================================================================
class BaselineLockRequest(BaseModel):
    project_id: str
    label: Optional[str] = None
    idempotency_key: str = Field(
        ...,
        description="UUID — prevents double-lock on network retry",
    )

    model_config = {"arbitrary_types_allowed": True}
