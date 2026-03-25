"""
project_calendars collection model.
Defines the working-day and holiday constraints used by the CPM engine.

Constitution Reference: §7.2 (calendar input to engine)
Schema Reference: §1.1
"""
from datetime import datetime, date, timezone
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from .shared_types import PyObjectId


# =============================================================================
# Project Calendar Document
# =============================================================================
class ProjectCalendar(BaseModel):
    """
    MongoDB document for the `project_calendars` collection.
    One document per project. Provides the DEFAULT calendar for CPM.
    Individual resources may override via enterprise_resources.calendar_override.
    """
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    project_id: PyObjectId = Field(..., description="Reference to the project")

    # Work-week definition: list of ISO weekday integers
    # 1=Monday ... 6=Saturday ... 7=Sunday
    # Default Goa construction: Mon-Sat = [1,2,3,4,5,6]
    work_days: List[int] = Field(
        default_factory=lambda: [1, 2, 3, 4, 5, 6],
        description="ISO weekday integers (1=Mon … 7=Sun). Goa standard: [1,2,3,4,5,6]",
    )
    shift_start: str = Field(
        default="09:00",
        description="Daily shift start time (HH:MM, 24h)",
    )
    shift_end: str = Field(
        default="18:00",
        description="Daily shift end time (HH:MM, 24h)",
    )
    holidays: List[date] = Field(
        default_factory=list,
        description="Dates that are non-working even if they fall on a work_day",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @field_validator("work_days")
    @classmethod
    def validate_work_days(cls, v: List[int]) -> List[int]:
        if not v:
            raise ValueError("work_days must contain at least one day")
        for day in v:
            if day not in range(1, 8):
                raise ValueError(f"work_days values must be 1-7 (ISO weekday), got {day}")
        return sorted(set(v))  # deduplicate and sort

    @field_validator("shift_start", "shift_end")
    @classmethod
    def validate_time_format(cls, v: str) -> str:
        try:
            h, m = v.split(":")
            assert 0 <= int(h) <= 23 and 0 <= int(m) <= 59
        except Exception:
            raise ValueError(f"Time must be HH:MM format, got '{v}'")
        return v

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


# =============================================================================
# Resource Calendar Override (embedded in enterprise_resources)
# =============================================================================
class ResourceCalendarOverride(BaseModel):
    """
    [GAP-FIX] Per-resource calendar override.
    When set, the CPM engine uses this instead of the project calendar
    for tasks assigned to this resource.
    """
    work_days: List[int] = Field(
        default_factory=lambda: [1, 2, 3, 4, 5],
        description="ISO weekday integers for this resource's work schedule",
    )
    holidays: List[date] = Field(
        default_factory=list,
        description="Resource-specific non-working dates",
    )

    @field_validator("work_days")
    @classmethod
    def validate_work_days(cls, v: List[int]) -> List[int]:
        for day in v:
            if day not in range(1, 8):
                raise ValueError(f"Invalid ISO weekday: {day}")
        return sorted(set(v))

    model_config = {"arbitrary_types_allowed": True}


# =============================================================================
# Create/Update schemas
# =============================================================================
class ProjectCalendarCreate(BaseModel):
    project_id: str
    work_days: List[int] = Field(default_factory=lambda: [1, 2, 3, 4, 5, 6])
    shift_start: str = "09:00"
    shift_end: str = "18:00"
    holidays: List[date] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}


class ProjectCalendarUpdate(BaseModel):
    work_days: Optional[List[int]] = None
    shift_start: Optional[str] = None
    shift_end: Optional[str] = None
    holidays: Optional[List[date]] = None

    model_config = {"arbitrary_types_allowed": True}
