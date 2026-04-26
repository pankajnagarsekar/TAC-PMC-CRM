from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

import re
from pydantic import BaseModel, Field, field_validator

from app.modules.shared.domain.types import PyObjectId


# AUTH DTOs
class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    user: "UserResponse"


# USER DTOs
class User(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    organisation_id: str
    name: str
    email: str
    hashed_password: str
    role: str  # 'Admin' | 'Supervisor' | 'Other'
    active_status: bool = True
    dpr_generation_permission: bool = False
    assigned_projects: List[str] = Field(default_factory=list)
    screen_permissions: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


class UserCreate(BaseModel):
    email: str
    password: str
    name: str
    role: str = "Supervisor"
    dpr_generation_permission: bool = False


class UserCreateAdmin(BaseModel):
    email: str
    password: str
    name: str
    role: str = "Supervisor"
    dpr_generation_permission: bool = False
    assigned_projects: List[str] = Field(default_factory=list)
    screen_permissions: List[str] = Field(default_factory=list)


class UserResponse(BaseModel):
    user_id: str = Field(validation_alias="id")
    organisation_id: str
    name: str
    email: str
    role: str
    active_status: bool
    dpr_generation_permission: bool = False
    assigned_projects: List[str] = Field(default_factory=list)
    screen_permissions: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"populate_by_name": True}


class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    active_status: Optional[bool] = None
    dpr_generation_permission: Optional[bool] = None
    assigned_projects: Optional[List[str]] = None
    screen_permissions: Optional[List[str]] = None


class UserProjectMap(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    user_id: str
    project_id: str
    organisation_id: str
    write_access: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


# ORGANISATION DTOs
class Organisation(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


class OrganisationCreate(BaseModel):
    name: str


class ClientPermissions(BaseModel):
    can_view_dpr: bool = True
    can_view_financials: bool = False
    can_view_reports: bool = True
    can_view_scheduler: bool = False


class GlobalSettings(BaseModel):
    organisation_id: str
    name: str = "TAC PMC"
    address: str = ""
    email: str = ""
    phone: str = ""
    gst_number: str = ""
    pan_number: str = ""
    cgst_percentage: Decimal = Field(Decimal("9.0"), ge=0, le=100)
    sgst_percentage: Decimal = Field(Decimal("9.0"), ge=0, le=100)
    retention_percentage: Decimal = Field(Decimal("5.0"), ge=0, le=100)
    wo_prefix: str = "WO"
    pc_prefix: str = "PC"
    invoice_prefix: str = "INV"
    currency: str = "INR"
    currency_symbol: str = "₹"
    terms_and_conditions: str = "Standard terms and conditions apply..."
    logo_base64: Optional[str] = None
    client_permissions: ClientPermissions = Field(default_factory=ClientPermissions)

    @field_validator("gst_number")
    @classmethod
    def validate_gst(cls, v: str) -> str:
        if v:
            v = v.strip().upper()
            if not re.match(r"^\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d]$", v):
                raise ValueError("Invalid GSTIN format")
        return v

    @field_validator("pan_number")
    @classmethod
    def validate_pan(cls, v: str) -> str:
        if v:
            v = v.strip().upper()
            if not re.match(r"^[A-Z]{5}\d{4}[A-Z]$", v):
                raise ValueError("Invalid PAN format")
        return v


class GlobalSettingsUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    gst_number: Optional[str] = None
    pan_number: Optional[str] = None
    cgst_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    sgst_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    retention_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    wo_prefix: Optional[str] = None
    pc_prefix: Optional[str] = None
    invoice_prefix: Optional[str] = None
    currency: Optional[str] = None
    currency_symbol: Optional[str] = None
    terms_and_conditions: Optional[str] = None
    logo_base64: Optional[str] = None
    client_permissions: Optional[ClientPermissions] = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8)


Token.model_rebuild()
