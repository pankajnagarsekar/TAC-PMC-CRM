from datetime import datetime, timezone
from typing import Optional, List, Literal
from decimal import Decimal
from pydantic import BaseModel, Field
from app.schemas.shared import PyObjectId

class WorkerEntry(BaseModel):
    worker_name: str = ""
    skill_type: str = ""
    hours_worked: Decimal = Field(Decimal("8.0"), ge=0)
    rate_per_hour: Decimal = Field(Decimal("0.0"), ge=0)
    remarks: Optional[str] = None

class VendorWorkerEntry(BaseModel):
    vendor_id: Optional[str] = None
    vendor_name: str = ""
    workers_count: int = Field(0, ge=0)
    skill_type: str = ""
    rate_per_worker: Decimal = Field(Decimal("0.0"), ge=0)
    remarks: Optional[str] = None

class WorkersDailyLog(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    organisation_id: str
    project_id: str
    date: str
    supervisor_id: str
    supervisor_name: str
    entries: List[VendorWorkerEntry] = Field(default_factory=list)
    workers: List[WorkerEntry] = Field(default_factory=list)
    total_workers: int = 0
    total_hours: Decimal = Decimal("0.0")
    weather: Optional[str] = None
    site_conditions: Optional[str] = None
    remarks: Optional[str] = None
    status: str = "draft"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}

class WorkersDailyLogCreate(BaseModel):
    project_id: str
    date: str
    entries: List[VendorWorkerEntry] = Field(default_factory=list)
    workers: List[WorkerEntry] = Field(default_factory=list)
    total_workers: Optional[int] = None
    weather: Optional[str] = None
    site_conditions: Optional[str] = None
    remarks: Optional[str] = None

class WorkersDailyLogUpdate(BaseModel):
    entries: Optional[List[VendorWorkerEntry]] = None
    workers: Optional[List[WorkerEntry]] = None
    weather: Optional[str] = None
    site_conditions: Optional[str] = None
    remarks: Optional[str] = None
    status: Optional[str] = None

class SiteOverhead(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    organisation_id: Optional[str] = None
    project_id: str
    amount: Decimal = Field(Decimal("0.0"), ge=0)
    purpose: str
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}

class SiteOverheadCreate(BaseModel):
    project_id: str
    amount: Decimal = Field(..., ge=0)
    purpose: str

class SiteOverheadUpdate(BaseModel):
    amount: Optional[Decimal] = Field(None, ge=0)
    purpose: Optional[str] = None
    description: Optional[str] = None
    version: int

class VoiceLog(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    project_id: str
    supervisor_id: str
    audio_url: str
    transcribed_text: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}

class DPR(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    project_id: str
    created_by: str
    date: datetime
    notes: str
    photos: List[str] = Field(default_factory=list)
    status: Literal['DRAFT', 'PENDING_APPROVAL', 'APPROVED', 'REJECTED'] = "DRAFT"
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejected_by: Optional[str] = None
    rejected_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}
