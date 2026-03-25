"""
enterprise_resources collection model.
Global resource pool used for capacity planning and AI allocation.

Constitution Reference: §4 Step 5 (resource leveling), §12 (RBAC)
Schema Reference: §1.2
"""
from datetime import datetime, timezone
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator
from .shared_types import PyObjectId, ResourceType, CostRateType
from .project_calendars import ResourceCalendarOverride


# =============================================================================
# Enterprise Resource Document
# =============================================================================
class EnterpriseResource(BaseModel):
    """
    MongoDB document for the `enterprise_resources` collection.
    Represents a single Personnel, Vendor, or Machinery resource
    available across ALL projects in the organisation.
    """
    id: Optional[PyObjectId] = Field(default=None, alias="_id")

    # Identity
    type: ResourceType
    name: str = Field(..., min_length=1, max_length=200)

    # Capacity
    max_capacity_per_day: int = Field(
        ...,
        ge=1,
        description="Maximum working hours available per day",
    )

    # [GAP-FIX] Cost rates — required for EV accuracy (Constitution §9)
    cost_rate_per_hour: Decimal = Field(
        ...,
        ge=Decimal("0"),
        description="Monetary cost per hour (stored as Decimal128 in MongoDB)",
    )
    cost_rate_type: CostRateType = Field(
        default=CostRateType.HOURLY,
        description="How the cost_rate_per_hour is applied",
    )

    # AI allocation support
    skills: List[str] = Field(
        default_factory=list,
        description="Skill tags used by the AI auto-allocation service",
    )

    # Cross-project assignment tracking
    active_assignments: List[PyObjectId] = Field(
        default_factory=list,
        description="task_ids across ALL projects currently assigned to this resource",
    )

    # [GAP-FIX] Resource-level calendar override
    calendar_override: Optional[ResourceCalendarOverride] = Field(
        default=None,
        description="When set, CPM uses this calendar instead of the project calendar for this resource's tasks",
    )

    # [GAP-FIX] Priority for resource leveling tie-breaking
    priority_rank: int = Field(
        default=100,
        ge=1,
        description="Lower number = higher priority in resource leveling conflicts",
    )

    # Metadata
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
    }


# =============================================================================
# Create / Update schemas
# =============================================================================
class EnterpriseResourceCreate(BaseModel):
    type: ResourceType
    name: str
    max_capacity_per_day: int = Field(..., ge=1)
    cost_rate_per_hour: Decimal = Field(..., ge=Decimal("0"))
    cost_rate_type: CostRateType = CostRateType.HOURLY
    skills: List[str] = Field(default_factory=list)
    calendar_override: Optional[ResourceCalendarOverride] = None
    priority_rank: int = Field(default=100, ge=1)

    model_config = {"arbitrary_types_allowed": True}


class EnterpriseResourceUpdate(BaseModel):
    name: Optional[str] = None
    max_capacity_per_day: Optional[int] = None
    cost_rate_per_hour: Optional[Decimal] = None
    cost_rate_type: Optional[CostRateType] = None
    skills: Optional[List[str]] = None
    calendar_override: Optional[ResourceCalendarOverride] = None
    priority_rank: Optional[int] = None

    model_config = {"arbitrary_types_allowed": True}


class EnterpriseResourceResponse(BaseModel):
    """Outbound shape — no hashed credentials or internal fields exposed."""
    resource_id: str
    type: ResourceType
    name: str
    max_capacity_per_day: int
    cost_rate_type: CostRateType
    skills: List[str]
    priority_rank: int
    has_calendar_override: bool

    model_config = {"arbitrary_types_allowed": True}
