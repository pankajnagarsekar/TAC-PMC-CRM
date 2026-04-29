from datetime import datetime, timezone
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator, computed_field, model_validator
from typing import Optional, Any, List
import re
import html

from app.modules.shared.domain.types import PyObjectId



# CALENDAR DTOs
class CalendarExceptionDTO(BaseModel):
    start_date: datetime
    end_date: datetime
    exception_type: str = "holiday"
    reason: Optional[str] = ""


class ProjectCalendarDTO(BaseModel):
    project_id: str
    working_days: List[int] = [0, 1, 2, 3, 4, 5]  # Mon-Sat by default for Goa
    shift_start: str = "08:00"
    shift_end: str = "17:00"
    lunch_start: str = "13:00"
    lunch_end: str = "14:00"
    exceptions: List[CalendarExceptionDTO] = []


# PROJECT DTOs
class Project(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    project_id: Optional[str] = None
    organisation_id: str
    project_name: str
    client_id: Optional[str] = None
    project_code: Optional[str] = None
    status: str = "active"
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    project_retention_percentage: Decimal = Field(Decimal("0.0"), ge=0, le=100)
    project_cgst_percentage: Decimal = Field(Decimal("9.0"), ge=0, le=100)
    project_sgst_percentage: Decimal = Field(Decimal("9.0"), ge=0, le=100)
    completion_percentage: Decimal = Field(Decimal("0.0"), ge=0, le=100)
    master_original_budget: Decimal = Field(Decimal("0.0"), ge=0)
    master_remaining_budget: Decimal = Field(Decimal("0.0"), ge=0)
    threshold_petty: Decimal = Field(Decimal("0.0"), ge=0)
    threshold_ovh: Decimal = Field(Decimal("0.0"), ge=0)
    version: int = 1
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @computed_field
    @property
    def name(self) -> str:
        """BUG-032: Authoritative name alias."""
        return self.project_name

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


class ProjectCreate(BaseModel):
    project_name: str
    client_id: Optional[str] = None
    project_code: Optional[str] = None
    status: str = "active"
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    project_retention_percentage: Decimal = Field(Decimal("0.0"), ge=0, le=100)
    project_cgst_percentage: Decimal = Field(Decimal("9.0"), ge=0, le=100)
    project_sgst_percentage: Decimal = Field(Decimal("9.0"), ge=0, le=100)
    completion_percentage: Decimal = Field(Decimal("0.0"), ge=0, le=100)
    threshold_petty: Decimal = Field(Decimal("0.0"), ge=0)
    threshold_ovh: Decimal = Field(Decimal("0.0"), ge=0)

    @field_validator("project_name", mode="before")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        v = re.sub(r"<[^>]+>", "", str(v)).strip()
        if not v:
            raise ValueError("Project name cannot be empty")
        return html.escape(v)


class ProjectUpdate(BaseModel):
    project_name: Optional[str] = None
    client_id: Optional[str] = None
    project_code: Optional[str] = None
    status: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    project_retention_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    project_cgst_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    project_sgst_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    completion_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    threshold_petty: Optional[Decimal] = Field(None, ge=0)
    threshold_ovh: Optional[Decimal] = Field(None, ge=0)

    @field_validator("project_name", mode="before")
    @classmethod
    def sanitize_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = re.sub(r"<[^>]+>", "", str(v)).strip()
        if not v:
            raise ValueError("Project name cannot be empty")
        return html.escape(v)


# MAPPING DTOs
class UserProjectMap(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    user_id: str
    project_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


class UserProjectMapCreate(BaseModel):
    user_id: str
    project_id: str


# BUDGET DTOs
class ProjectBudget(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    project_id: str
    category_id: str
    original_budget: Decimal = Field(..., ge=0)
    committed_amount: Decimal = Field(Decimal("0.0"), ge=0)
    remaining_budget: Decimal = Field(Decimal("0.0"), ge=0)
    description: Optional[str] = None
    version: int = 1
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


class ProjectBudgetCreate(BaseModel):
    project_id: str
    category_id: str
    original_budget: Decimal = Field(..., ge=0)
    description: Optional[str] = None


class ProjectBudgetUpdate(BaseModel):
    original_budget: Optional[Decimal] = Field(None, ge=0)
    version: int


# CLIENT DTOs
class Client(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    organisation_id: Optional[str] = None
    client_name: str
    client_address: Optional[str] = None
    client_phone: Optional[str] = None
    client_email: Optional[str] = None
    gst_number: Optional[str] = None
    can_view_scheduler: bool = True
    active_status: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="before")
    @classmethod
    def handle_legacy_fields(cls, data: Any) -> Any:
        """BUG-071: Harmonize unsuffixed DB fields with DTO schema."""
        if isinstance(data, dict):
            # Map name -> client_name
            if not data.get("client_name") and data.get("name"):
                data["client_name"] = data["name"]

            # Map address -> client_address
            if not data.get("client_address") and data.get("address"):
                data["client_address"] = data["address"]

            # Map phone -> client_phone
            if not data.get("client_phone") and data.get("phone"):
                data["client_phone"] = data["phone"]

            # Map email -> client_email
            if not data.get("client_email") and data.get("email"):
                data["client_email"] = data["email"]

            # Map gstin -> gst_number
            if not data.get("gst_number") and data.get("gstin"):
                data["gst_number"] = data["gstin"]
        return data

    @computed_field
    @property
    def name(self) -> str:
        """BUG-033: Authoritative name alias for client."""
        return self.client_name

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


class ClientCreate(BaseModel):
    client_name: str
    client_address: Optional[str] = None
    client_phone: Optional[str] = None
    client_email: Optional[str] = None
    gst_number: Optional[str] = None
    can_view_scheduler: bool = True

    @field_validator("client_name", mode="before")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        v = re.sub(r"<[^>]+>", "", str(v)).strip()
        if not v:
            raise ValueError("Client name cannot be empty")
        return html.escape(v)

    @field_validator("gst_number")
    @classmethod
    def validate_gstin(cls, v: Optional[str]) -> Optional[str]:
        if v:
            v = v.strip().upper()
            if not re.match(r"^\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d]$", v):
                raise ValueError("Invalid GSTIN format. Expected: 22AAAAA0000A1Z5")
        return v


class ClientUpdate(BaseModel):
    client_name: Optional[str] = None
    client_address: Optional[str] = None
    client_phone: Optional[str] = None
    client_email: Optional[str] = None
    gst_number: Optional[str] = None
    can_view_scheduler: Optional[bool] = None
    active_status: Optional[bool] = None

    @field_validator("client_name", mode="before")
    @classmethod
    def sanitize_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = re.sub(r"<[^>]+>", "", str(v)).strip()
        if not v:
            raise ValueError("Client name cannot be empty")
        return html.escape(v)

    @field_validator("gst_number")
    @classmethod
    def validate_gstin(cls, v: Optional[str]) -> Optional[str]:
        if v:
            v = v.strip().upper()
            if not re.match(r"^\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d]$", v):
                raise ValueError("Invalid GSTIN format. Expected: 22AAAAA0000A1Z5")
        return v
