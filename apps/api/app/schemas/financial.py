from datetime import datetime, timezone
from typing import Optional, List, Literal
from decimal import Decimal
from pydantic import BaseModel, Field
from app.schemas.shared import PyObjectId

class CodeMaster(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    organisation_id: Optional[str] = None
    category_name: Optional[str] = None
    code: Optional[str] = None
    code_short: str = ""
    code_description: str = ""
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
    total_after_retention: Decimal = Field(Decimal("0.0"), ge=0)
    cgst: Decimal = Field(Decimal("0.0"), ge=0)
    sgst: Decimal = Field(Decimal("0.0"), ge=0)
    grand_total: Decimal = Field(Decimal("0.0"), ge=0)
    status: Literal["Draft", "Pending", "Completed", "Closed", "Cancelled"] = "Draft"
    fund_request: bool = False
    line_items: List[PCLineItem] = Field(default_factory=list)
    idempotency_key: Optional[str] = None
    version: int = 1
    # Legacy fields
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
    vendor_name: Optional[str] = None
    invoice_number: Optional[str] = None
    date: Optional[str] = None
    amount: Optional[Decimal] = Field(None, ge=0)
    gst_amount: Decimal = Field(Decimal("0.0"), ge=0)
    total_amount: Optional[Decimal] = Field(None, ge=0)
    ocr_id: Optional[str] = None

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

class DerivedFinancialState(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    project_id: str
    category_id: str
    category_name: Optional[str] = None
    category_code: Optional[str] = None
    code_id: Optional[str] = None
    original_budget: Decimal = Decimal("0.0")
    committed_value: Decimal = Decimal("0.0")
    certified_value: Decimal = Decimal("0.0")
    balance_budget_remaining: Decimal = Decimal("0.0")
    over_commit_flag: bool = False
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}

class FundAllocation(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    project_id: str
    category_id: str
    allocation_original: Decimal = Decimal("0.0")
    allocation_received: Decimal = Decimal("0.0")
    allocation_remaining: Decimal = Decimal("0.0")
    cash_in_hand: Decimal = Decimal("0.0")
    total_expenses: Decimal = Decimal("0.0")
    last_pc_closed_date: Optional[datetime] = None
    version: int = 1
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}

class VendorLedgerEntry(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    vendor_id: str
    project_id: str
    ref_id: str
    entry_type: Literal["PC_CERTIFIED", "PAYMENT_MADE", "RETENTION_HELD"]
    amount: Decimal = Decimal("0.0")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}
