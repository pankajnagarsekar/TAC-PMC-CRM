from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field

from app.modules.shared.domain.types import PyObjectId


# WORKER LOG DTOs
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


# OVERHEAD DTOs
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


# VOICE LOG DTOs
class VoiceLog(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    project_id: str
    supervisor_id: str
    audio_url: str
    transcribed_text: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


# DPR DTOs
class DPRImageDetail(BaseModel):
    image_id: str
    image_data: str
    caption: Optional[str] = None
    activity_code: Optional[str] = None
    aspect_ratio: str = "9:16"
    size_kb: float
    uploaded_by: str
    uploaded_at: datetime


class DPRImage(BaseModel):
    image_data: str = Field(..., max_length=13107200)  # 10 MB in base64
    caption: Optional[str] = Field(None, max_length=500)
    activity_code: Optional[str] = None


class UpdateImageCaptionRequest(BaseModel):
    caption: str


class RejectDPRRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)


class DPRCreate(BaseModel):
    project_id: str
    dpr_date: Optional[datetime] = None
    progress_notes: Optional[str] = None
    weather_conditions: Optional[str] = "Normal"
    # Note: Images are uploaded separately via /dprs/{id}/images


class DPR(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    organisation_id: str
    project_id: str
    supervisor_id: str
    dpr_date: datetime
    progress_notes: Optional[str] = None
    voice_summary: Optional[str] = None
    weather_conditions: str = "Normal"
    images: List[DPRImageDetail] = Field(default_factory=list)
    image_count: int = 0
    status: str = "Draft"
    locked_flag: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}
