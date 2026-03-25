"""
project_metadata collection model — Project-level settings and cached values.
[GAP-FIX] New collection from Schema §1.6.

Constitution Reference: §2.3 (financial invariants), §8 (lifecycle), §10 (limits)
Schema Reference: §1.6
"""
from datetime import datetime, timezone
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, Field
from .shared_types import PyObjectId, ProjectStatus, SystemState


# =============================================================================
# Project Metadata Document
# =============================================================================
class ProjectMetadata(BaseModel):
    """
    MongoDB document for the `project_metadata` collection.
    One document per project. Stores project-level settings and cached
    aggregation values that are expensive to recompute on every request.

    Key cached value: total_baseline_cost_cache
    — Updated on every baseline lock (Constitution §2.3)
    — Used for weightage calculation: (task.baseline_cost / total) * 100
    — Avoids full re-aggregation on every API request
    """
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    project_id: PyObjectId = Field(..., description="Primary key — same as the project's _id")

    # Project identity
    project_name: str = Field(..., min_length=1, max_length=300)
    project_status: ProjectStatus = Field(default=ProjectStatus.DRAFT)

    # Resource leveling priority across projects (lower = higher priority)
    project_priority: int = Field(
        default=100,
        ge=1,
        description="Used in resource leveling tie-breaking across projects. Lower = higher priority.",
    )

    # [GAP-FIX] Cached financial total for weightage calculation
    # Refreshed on every baseline lock. Avoids expensive re-aggregation.
    total_baseline_cost_cache: Decimal = Field(
        default=Decimal("0"),
        ge=Decimal("0"),
        description="Sum of all task baseline_costs. Refreshed on baseline lock. "
                    "Used for: weightage = (task.baseline_cost / total) * 100",
    )

    # CPM tracking
    last_calculation_version: Optional[str] = Field(
        default=None,
        description="UUID of the most recent successful CPM run",
    )
    last_calculated_at: Optional[datetime] = Field(
        default=None,
        description="UTC timestamp of the most recent successful CPM run",
    )

    # System state for UI gating (Constitution §8)
    system_state: SystemState = Field(
        default=SystemState.DRAFT,
        description="Controls what operations are allowed in the UI",
    )

    # Audit
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    created_by: Optional[PyObjectId] = None
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
    }


# =============================================================================
# Audit Log Document [GAP-FIX — New Collection §1.5]
# =============================================================================
from typing import Any, Dict
from .shared_types import AuditAction, ChangeSource


class AuditLogEntry(BaseModel):
    """
    MongoDB document for the `audit_log` collection.
    Every change to project_schedules creates an entry.
    Retained for project lifetime + 2 years (Schema §1.5).
    """
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    project_id: PyObjectId
    task_id: Optional[PyObjectId] = Field(
        default=None,
        description="Null for project-level events (e.g. baseline locked, import completed)",
    )

    action: AuditAction
    actor_id: PyObjectId = Field(..., description="User or system account ObjectId")
    actor_role: str = Field(..., description="User role at time of action (denormalised for audit integrity)")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    change_source: ChangeSource

    # State snapshots for forensic audit trail
    before_state: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Changed fields snapshot BEFORE modification. Null for creates.",
    )
    after_state: Dict[str, Any] = Field(
        ...,
        description="Changed fields snapshot AFTER modification.",
    )

    # [GAP-FIX] Optional admin note explaining WHY the change was made
    change_reason: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Optional: delay, rework, scope change, weather, vendor issue, etc.",
    )

    # Links audit entry to a specific CPM engine run
    calculation_version: Optional[str] = Field(
        default=None,
        description="UUID linking to the engine run that triggered this change (if applicable)",
    )

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
    }
