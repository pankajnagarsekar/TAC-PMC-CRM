# MongoDB Pydantic v2 Models
from datetime import datetime
from typing import Optional, List, Annotated, Any
from bson import ObjectId
from pydantic import BaseModel, Field, BeforeValidator


# =============================================================================
# PyObjectId Helper for MongoDB _id fields
# =============================================================================
def validate_object_id(v):
    if isinstance(v, ObjectId):
        return str(v)
    if isinstance(v, str) and ObjectId.is_valid(v):
        return v
    raise ValueError("Invalid ObjectId")


PyObjectId = Annotated[str, BeforeValidator(validate_object_id)]


# =============================================================================
# ORGANISATION MODELS
# =============================================================================
class Organisation(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


class OrganisationCreate(BaseModel):
    name: str


# =============================================================================
# USER MODELS
# =============================================================================
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
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


class UserCreate(BaseModel):
    email: str
    password: str
    name: str
    role: str = "Supervisor"
    dpr_generation_permission: bool = False


class UserResponse(BaseModel):
    user_id: str
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


# =============================================================================
# USER PROJECT MAPPING MODELS
# =============================================================================
class UserProjectMap(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    user_id: str
    project_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


class UserProjectMapCreate(BaseModel):
    user_id: str
    project_id: str


# =============================================================================
# PROJECT MODELS
# =============================================================================
class Project(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    organisation_id: str
    project_name: str
    project_code: Optional[str] = None
    status: str = "active"
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    project_retention_percentage: float = 0.0
    project_cgst_percentage: float = 9.0
    project_sgst_percentage: float = 9.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


class ProjectCreate(BaseModel):
    project_name: str
    project_code: Optional[str] = None
    status: str = "active"
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    project_retention_percentage: float = 0.0
    project_cgst_percentage: float = 9.0
    project_sgst_percentage: float = 9.0


class ProjectUpdate(BaseModel):
    project_name: Optional[str] = None
    project_code: Optional[str] = None
    status: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    project_retention_percentage: Optional[float] = None
    project_cgst_percentage: Optional[float] = None
    project_sgst_percentage: Optional[float] = None


# =============================================================================
# CODE MASTER MODELS
# =============================================================================
class CodeMaster(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    code_short: str
    code_description: str
    active_status: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


class CodeMasterCreate(BaseModel):
    code_short: str
    code_description: str


class CodeMasterUpdate(BaseModel):
    code_short: Optional[str] = None
    code_description: Optional[str] = None
    active_status: Optional[bool] = None


# =============================================================================
# PROJECT BUDGET MODELS
# =============================================================================
class ProjectBudget(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    project_id: str
    code_id: str
    approved_budget_amount: float
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


class ProjectBudgetCreate(BaseModel):
    project_id: str
    code_id: str
    approved_budget_amount: float
    description: Optional[str] = None


class ProjectBudgetUpdate(BaseModel):
    approved_budget_amount: Optional[float] = None
    description: Optional[str] = None


# =============================================================================
# DERIVED FINANCIAL STATE MODEL
# =============================================================================
class DerivedFinancialState(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    project_id: str
    code_id: str
    approved_budget_amount: float = 0.0
    committed_value: float = 0.0
    certified_value: float = 0.0
    balance_budget_remaining: float = 0.0
    over_commit_flag: bool = False
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


# =============================================================================
# AUDIT LOG MODEL
# =============================================================================
class AuditLog(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    organisation_id: str
    module_name: str
    entity_type: str
    entity_id: str
    action_type: str
    user_id: str
    project_id: Optional[str] = None
    old_value: Optional[dict] = None
    new_value: Optional[dict] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


# =============================================================================
# GLOBAL SETTINGS MODEL
# =============================================================================
class GlobalSettings(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    organisation_id: str
    name: str = ""
    address: str = ""
    email: str = ""
    phone: str = ""
    gst_number: str = ""
    pan_number: str = ""
    cgst_percentage: float = 9.0
    sgst_percentage: float = 9.0
    wo_prefix: str = "WO"
    pc_prefix: str = "PC"
    invoice_prefix: str = "INV"
    terms_and_conditions: str = ""
    currency: str = "INR"
    currency_symbol: str = "₹"
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


# =============================================================================
# AUTH MODELS
# =============================================================================
class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    user: UserResponse


# =============================================================================
# WORKERS DAILY LOG MODELS
# =============================================================================
class WorkerEntry(BaseModel):
    worker_name: str = ""
    skill_type: str = ""
    hours_worked: float = 8.0
    rate_per_hour: float = 0.0
    remarks: Optional[str] = None


class VendorWorkerEntry(BaseModel):
    vendor_id: Optional[str] = None
    vendor_name: str = ""
    workers_count: int = 0
    skill_type: str = ""
    rate_per_worker: float = 0.0
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
    total_hours: float = 0.0
    weather: Optional[str] = None
    site_conditions: Optional[str] = None
    remarks: Optional[str] = None
    status: str = "draft"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

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


# =============================================================================
# NOTIFICATION MODELS
# =============================================================================
class Notification(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    organisation_id: str
    recipient_role: Optional[str] = None
    recipient_user_id: Optional[str] = None
    title: str
    message: str
    notification_type: str = "info"
    priority: str = "normal"
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    sender_id: Optional[str] = None
    sender_name: Optional[str] = None
    is_read: bool = False
    read_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


class NotificationCreate(BaseModel):
    recipient_role: Optional[str] = None
    recipient_user_id: Optional[str] = None
    title: str
    message: str
    notification_type: str = "info"
    priority: str = "normal"
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    project_id: Optional[str] = None
    project_name: Optional[str] = None


# =============================================================================
# DPR MODEL (existing)
# =============================================================================
class DPR(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    project_id: str
    created_by: str
    date: datetime
    notes: str
    photos: List[str] = Field(default_factory=list)
    status: str = "draft"  # 'draft' | 'submitted' | 'approved' | 'rejected'
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


# =============================================================================
# PETTY CASH MODEL (existing)
# =============================================================================
class PettyCash(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    project_id: str
    created_by: str
    amount: float
    purpose: str
    receipt_photo: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


# =============================================================================
# ATTENDANCE MODEL (existing)
# =============================================================================
class Attendance(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    user_id: str
    project_id: str
    selfie_url: str
    gps_lat: float
    gps_lng: float
    check_in_time: datetime

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}
