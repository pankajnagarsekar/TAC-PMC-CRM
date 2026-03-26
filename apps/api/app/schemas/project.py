from datetime import datetime, timezone
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, Field
from app.schemas.shared import PyObjectId

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

class UserProjectMap(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    user_id: str
    project_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}

class UserProjectMapCreate(BaseModel):
    user_id: str
    project_id: str

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
