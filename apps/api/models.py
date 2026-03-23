# MongoDB Pydantic v2 Models
from datetime import datetime, timezone
from typing import Optional, List, Annotated, Literal
from decimal import Decimal
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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}

class UserProjectMapCreate(BaseModel):
    user_id: str
    project_id: str

class Project(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    project_id: Optional[str] = None  # Derived from _id in API responses
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
    # Financial summary per DB Schema §2.2
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

class Client(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    organisation_id: str
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    gstin: Optional[str] = None
    active_status: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}

class ClientCreate(BaseModel):
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    gstin: Optional[str] = None

class ClientUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    gstin: Optional[str] = None
    active_status: Optional[bool] = None


# =============================================================================
# CODE MASTER MODELS
# =============================================================================
class CodeMaster(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    organisation_id: Optional[str] = None
    category_name: Optional[str] = None
    code: Optional[str] = None
    code_short: str = ""  # Legacy alias for code
    code_description: str = ""  # Legacy alias for category_name
    budget_type: Optional[Literal["commitment", "fund_transfer"]] = "commitment"
    active_status: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


class CodeMasterCreate(BaseModel):
    code_short: str = ""
    code_description: str = ""
    category_name: Optional[str] = None
    code: Optional[str] = None
    budget_type: Optional[Literal["commitment", "fund_transfer"]] = "commitment"


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


# =============================================================================
# SITE OVERHEAD MODELS
# =============================================================================
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


# =============================================================================
# DERIVED FINANCIAL STATE MODEL
# =============================================================================
class DerivedFinancialState(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    project_id: str
    category_id: str
    category_name: Optional[str] = None
    category_code: Optional[str] = None
    code_id: Optional[str] = None  # Legacy support
    original_budget: Decimal = Decimal("0.0")
    committed_value: Decimal = Decimal("0.0")
    certified_value: Decimal = Decimal("0.0")
    balance_budget_remaining: Decimal = Decimal("0.0")
    over_commit_flag: bool = False
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1

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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


# =============================================================================
# GLOBAL SETTINGS MODEL
# =============================================================================
class ClientPermissions(BaseModel):
    can_view_dpr: bool = True
    can_view_financials: bool = False
    can_view_reports: bool = True

class GlobalSettings(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    organisation_id: str
    name: str = ""
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
    terms_and_conditions: str = "Standard terms and conditions apply."
    currency: str = "INR"
    currency_symbol: str = "₹"
    client_permissions: ClientPermissions = Field(default_factory=ClientPermissions)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

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
    expires_in: int
    user: UserResponse


# =============================================================================
# WORKERS DAILY LOG MODELS
# =============================================================================
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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

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
    status: Literal['DRAFT', 'PENDING_APPROVAL', 'APPROVED', 'REJECTED'] = "DRAFT"
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejected_by: Optional[str] = None
    rejected_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


# =============================================================================
# PAYMENT CERTIFICATE MODELS (Spec-aligned)
# =============================================================================
class PCLineItem(BaseModel):
    sr_no: int
    scope_of_work: str = ""
    rate: Decimal = Field(Decimal("0.0"), ge=0)
    qty: Decimal = Field(Decimal("0.0"), ge=0)
    unit: str = ""
    total: Decimal = Field(Decimal("0.0"), ge=0)


class PaymentCertificate(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    organisation_id: Optional[str] = None
    project_id: str
    work_order_id: Optional[str] = None
    category_id: Optional[str] = None
    vendor_id: Optional[str] = None
    pc_ref: str = ""
    subtotal: Decimal = Field(Decimal("0.0"), ge=0)
    retention_percent: Decimal = Field(Decimal("0.0"), ge=0, le=100)
    retention_amount: Decimal = Field(Decimal("0.0"), ge=0)
    total_after_retention: Decimal = Field(Decimal("0.0"), ge=0)  # Per Spec §4.3: subtotal - retention_amount
    cgst: Decimal = Field(Decimal("0.0"), ge=0)
    sgst: Decimal = Field(Decimal("0.0"), ge=0)
    grand_total: Decimal = Field(Decimal("0.0"), ge=0)
    status: Literal["Draft", "Pending", "Completed", "Closed", "Cancelled"] = "Draft"
    fund_request: bool = False
    line_items: List[PCLineItem] = Field(default_factory=list)
    idempotency_key: Optional[str] = None
    version: int = 1
    # Legacy fields for backward compat with OCR-created PCs
    vendor_name: Optional[str] = None
    invoice_number: Optional[str] = None
    date: Optional[str] = None
    amount: Optional[Decimal] = Field(None, ge=0)
    gst_amount: Decimal = Field(Decimal("0.0"), ge=0)
    total_amount: Optional[Decimal] = Field(None, ge=0)
    ocr_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


class PaymentCertificateCreate(BaseModel):
    project_id: str
    work_order_id: Optional[str] = None
    category_id: Optional[str] = None
    vendor_id: Optional[str] = None
    line_items: List[PCLineItem] = Field(default_factory=list)
    retention_percent: Decimal = Field(Decimal("0.0"), ge=0, le=100)
    fund_request: bool = False
    idempotency_key: Optional[str] = None
    # Legacy fields
    vendor_name: Optional[str] = None
    invoice_number: Optional[str] = None
    date: Optional[str] = None
    amount: Optional[Decimal] = Field(None, ge=0)
    gst_amount: Decimal = Field(Decimal("0.0"), ge=0)
    total_amount: Optional[Decimal] = Field(None, ge=0)
    ocr_id: Optional[str] = None


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
    terms_and_conditions: Optional[str] = None
    currency: Optional[str] = None
    currency_symbol: Optional[str] = None
    client_permissions: Optional[dict] = None


# =============================================================================
# VENDOR MODELS
# =============================================================================
class Vendor(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    organisation_id: str
    name: str
    gstin: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    active_status: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


class VendorCreate(BaseModel):
    name: str
    gstin: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None


class VendorUpdate(BaseModel):
    name: Optional[str] = None
    gstin: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    active_status: Optional[bool] = None


# =============================================================================
# WORK ORDER MODELS
# =============================================================================
class WOLineItem(BaseModel):
    sr_no: int
    description: str = ""
    qty: Decimal = Field(Decimal("0.0"), ge=0)
    rate: Decimal = Field(Decimal("0.0"), ge=0)
    total: Decimal = Field(Decimal("0.0"), ge=0)


class WorkOrder(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    organisation_id: Optional[str] = None
    project_id: str
    category_id: str
    vendor_id: Optional[str] = None
    wo_ref: str = ""
    subtotal: Decimal = Field(Decimal("0.0"), ge=0)
    discount: Decimal = Field(Decimal("0.0"), ge=0)
    total_before_tax: Decimal = Field(Decimal("0.0"), ge=0)
    cgst: Decimal = Field(Decimal("0.0"), ge=0)
    sgst: Decimal = Field(Decimal("0.0"), ge=0)
    grand_total: Decimal = Field(Decimal("0.0"), ge=0)
    retention_percent: Decimal = Field(Decimal("0.0"), ge=0, le=100)
    retention_amount: Decimal = Field(Decimal("0.0"), ge=0)
    total_payable: Decimal = Field(Decimal("0.0"), ge=0)
    actual_payable: Decimal = Field(Decimal("0.0"), ge=0)
    status: Literal["Draft", "Pending", "Completed", "Closed", "Cancelled"] = "Draft"
    line_items: List[WOLineItem] = Field(default_factory=list)
    version: int = 1
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


class WorkOrderCreate(BaseModel):
    project_id: str
    category_id: str
    vendor_id: Optional[str] = None
    line_items: List[WOLineItem] = Field(default_factory=list)
    discount: Decimal = Field(Decimal("0.0"), ge=0)
    retention_percent: Decimal = Field(Decimal("0.0"), ge=0, le=100)
    idempotency_key: Optional[str] = None


class WorkOrderUpdate(BaseModel):
    category_id: Optional[str] = None
    vendor_id: Optional[str] = None
    line_items: Optional[List[WOLineItem]] = None
    discount: Optional[Decimal] = Field(None, ge=0)
    retention_percent: Optional[Decimal] = Field(None, ge=0, le=100)
    expected_version: int


# =============================================================================
# CASH TRANSACTION MODELS (Petty Cash / OVH)
# =============================================================================
class CashTransaction(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    project_id: str
    category_id: str
    amount: Decimal = Field(Decimal("0.0"), ge=0)
    type: Literal["DEBIT", "CREDIT"] = "DEBIT"
    purpose: Optional[str] = None
    bill_reference: Optional[str] = None
    image_url: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


class CashTransactionCreate(BaseModel):
    category_id: str
    amount: Decimal = Field(Decimal("0.0"), ge=0)
    type: Literal["DEBIT", "CREDIT"] = "DEBIT"
    purpose: Optional[str] = None
    bill_reference: Optional[str] = None
    image_url: Optional[str] = None

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}





# =============================================================================
# VENDOR LEDGER MODELS (Append-only / Immutable)
# =============================================================================
class VendorLedgerEntry(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    vendor_id: str
    project_id: str
    ref_id: str  # PC or WO id
    entry_type: Literal["PC_CERTIFIED", "PAYMENT_MADE", "RETENTION_HELD"]
    amount: Decimal = Decimal("0.0")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


# =============================================================================
# VOICE LOG MODEL
# =============================================================================
class VoiceLog(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    project_id: str
    supervisor_id: str
    audio_url: str
    transcribed_text: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


# =============================================================================
# FUND ALLOCATION MODEL
# =============================================================================
class FundAllocation(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    project_id: str
    category_id: str
    allocation_original: Decimal = Decimal("0.0")  # Per Spec §5.1: category budget set in project
    allocation_received: Decimal = Decimal("0.0")   # Per Spec §5.1: total money received from client
    allocation_remaining: Decimal = Decimal("0.0")  # Per Spec §5.1: allocation_original - allocation_received
    cash_in_hand: Decimal = Decimal("0.0")          # Per Spec §5.1: allocation_received - total_expenses
    total_expenses: Decimal = Decimal("0.0")        # Per Spec §5.1: SUM(all expense logs)
    last_pc_closed_date: Optional[datetime] = None  # Per Spec §5.2: Timer resets ONLY on PC CLOSE
    version: int = 1
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


# =============================================================================
# OPERATION LOG MODEL (Idempotency Tracking)
# =============================================================================
class OperationLog(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    operation_key: str
    entity_type: str
    response_payload: Optional[dict] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


# =============================================================================
# AI PROJECT SUMMARY MODELS
# =============================================================================
class AISummaryReportData(BaseModel):
    total_budget: float = 0.0
    total_committed: float = 0.0
    total_certified: float = 0.0
    total_remaining: float = 0.0
    over_budget_categories: List[str] = Field(default_factory=list)
    total_vendor_payable: float = 0.0
    total_cash_in_hand: float = 0.0
    petty_cash_status: str = "Unknown"
    ovh_status: str = "Unknown"
    wo_total: int = 0
    wo_open: int = 0
    wo_closed: int = 0
    pc_total: int = 0
    pc_closed: int = 0
    schedule_task_count: int = 0


class AISummaryDocument(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    project_id: str
    organisation_id: str
    summary_text: str
    report_data: AISummaryReportData
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    model: str = "mock"
    triggered_by: Literal["scheduler", "manual"] = "scheduler"
    date_key: str

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}
