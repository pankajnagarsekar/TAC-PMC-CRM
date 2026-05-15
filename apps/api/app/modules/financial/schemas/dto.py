from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import List, Literal, Optional

import re

from pydantic import BaseModel, Field, field_validator, computed_field

from app.modules.shared.domain.types import PyObjectId


# APPROVAL EVENT SCHEMA
class ApprovalEventSchema(BaseModel):
    action: Literal["SUBMITTED", "APPROVED", "REJECTED", "PAID"]
    user_id: str
    user_role: str
    timestamp: datetime
    comment: str
    payment_state_before: str
    payment_state_after: str

    model_config = {"arbitrary_types_allowed": True}


# CODE MASTER DTOs
class CodeMaster(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    organisation_id: Optional[str] = None
    category_name: str

    @computed_field
    @property
    def name(self) -> str:
        """BUG-032: Authoritative name alias for category."""
        return self.category_name

    code: str
    description: Optional[str] = None
    budget_type: Literal["commitment", "fund_transfer"] = "commitment"
    active_status: bool = True
    version: int = 1
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


class CodeMasterCreate(BaseModel):
    category_name: str
    code: str
    description: Optional[str] = None
    budget_type: Literal["commitment", "fund_transfer"] = "commitment"

    @field_validator("code", mode="before")
    @classmethod
    def validate_code_format(cls, v: str) -> str:
        normalized = str(v).upper().strip()
        if not re.match(r"^[A-Z0-9]{2,6}$", normalized):
            raise ValueError(
                "Category code must be 2–6 uppercase alphanumeric characters (A-Z, 0-9)"
            )
        return normalized


class CodeMasterUpdate(BaseModel):
    category_name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    active_status: Optional[bool] = None
    expected_version: int


# PAYMENT CERTIFICATE DTOs
class PCDocument(BaseModel):
    file_id: str
    original_name: str
    file_path: str
    page_count: int = 1
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PCLineItem(BaseModel):
    sr_no: int
    scope_of_work: str = ""
    rate: Decimal = Field(Decimal("0.0"), ge=0)
    qty: Decimal = Field(Decimal("0.0"), ge=0)
    previous_qty: Decimal = Field(Decimal("0.0"), ge=0)
    cumulative_qty: Decimal = Field(Decimal("0.0"), ge=0)
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
    pc_refn: int = 0
    contractor_category: Optional[str] = None
    subtotal: Decimal = Field(Decimal("0.0"), ge=0)
    retention_percent: Decimal = Field(Decimal("0.0"), ge=0, le=100)
    retention_amount: Decimal = Field(Decimal("0.0"), ge=0)
    total_after_retention: Decimal = Field(Decimal("0.0"), ge=0)
    cgst: Decimal = Field(Decimal("0.0"), ge=0)
    sgst: Decimal = Field(Decimal("0.0"), ge=0)
    grand_total: Decimal = Field(Decimal("0.0"), ge=0)
    status: Literal["Draft", "Submitted", "Approved", "Processing", "Paid", "Rejected", "Cancelled"] = "Draft"
    total_payable: Decimal = Field(Decimal("0.0"), ge=0)
    fund_request: bool = False
    pc_type: Optional[Literal["WO_LINKED", "PETTY_OVH"]] = None
    line_items: List[PCLineItem] = Field(default_factory=list)
    certification_period_start: Optional[datetime] = None
    certification_period_end: Optional[datetime] = None
    vendor_gst_no: Optional[str] = None
    pmc_comments: str = ""
    idempotency_key: Optional[str] = None
    version: int = 1
    vendor_name: Optional[str] = None
    category_name: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    submitted_by: Optional[str] = None
    submitted_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejected_reason: Optional[str] = None
    approval_trail: List[ApprovalEventSchema] = Field(default_factory=list)
    additional_documents: List[PCDocument] = Field(default_factory=list)
    base_page_count: int = 1

    @computed_field
    @property
    def certification_date(self) -> datetime:
        """BUG-035: Authoritative certification date for display."""
        return self.approved_at or self.submitted_at or self.created_at

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


class PaymentCertificateCreate(BaseModel):
    project_id: str
    work_order_id: Optional[str] = None
    category_id: Optional[str] = None
    vendor_id: Optional[str] = None
    contractor_category: Optional[str] = None
    line_items: List[PCLineItem] = Field(default_factory=list)
    retention_percent: Decimal = Field(Decimal("0.0"), ge=0, le=100)
    fund_request: bool = False
    pc_type: Optional[Literal["WO_LINKED", "PETTY_OVH"]] = None
    certification_period_start: Optional[datetime] = None
    certification_period_end: Optional[datetime] = None
    vendor_gst_no: Optional[str] = None
    pmc_comments: str = ""
    idempotency_key: Optional[str] = None


# DERIVED STATE DTOs
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


# FUND ALLOCATION DTOs
class FundAllocation(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    organisation_id: str
    project_id: str
    category_id: str
    allocation_original: Decimal = Decimal("0.0")
    allocation_received: Decimal = Decimal("0.0")
    allocation_remaining: Decimal = Decimal("0.0")
    cash_in_hand: Decimal = Decimal("0.0")
    total_expenses: Decimal = Decimal("0.0")
    last_pc_paid_date: Optional[datetime] = None
    last_pc_created_at: Optional[datetime] = None
    version: int = 1
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


class FundAllocationCreate(BaseModel):
    project_id: str
    category_id: str
    amount: Decimal = Field(..., ge=0)
    description: Optional[str] = None
    idempotency_key: Optional[str] = None


# CASH TRANSACTION DTOs
class CashTransaction(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    organisation_id: str
    project_id: str
    category_id: str
    amount: Decimal
    type: Literal["DEBIT", "CREDIT"]
    flow_direction: Optional[Literal["INFLOW", "OUTFLOW"]] = None  # BUG-017
    description: Optional[str] = None
    transaction_date: datetime
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


class CashTransactionCreate(BaseModel):
    project_id: str
    category_id: str
    amount: Decimal = Field(..., ge=0)
    type: Literal["DEBIT", "CREDIT"]
    flow_direction: Optional[Literal["INFLOW", "OUTFLOW"]] = None  # BUG-017
    description: Optional[str] = None
    transaction_date: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    idempotency_key: Optional[str] = None


# LEDGER DTOs
class VendorLedgerEntry(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    vendor_id: str
    project_id: str
    ref_id: str
    entry_type: Literal["PC_CERTIFIED", "PAYMENT_MADE", "RETENTION_HELD"]
    flow_direction: Literal["INFLOW", "OUTFLOW"]  # BUG-017
    amount: Decimal = Decimal("0.0")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


# BUDGET DTOs
class BudgetAllocationDTO(BaseModel):
    code: str
    budgeted_amount: Decimal = Field(..., ge=0)
    spent_amount: Decimal = Field(Decimal("0.0"), ge=0)
    variance: Optional[Decimal] = None
    percent_spent: Optional[Decimal] = None
    threshold_percentage: int = Field(80, ge=0, le=100)
    is_threshold_breached: Optional[bool] = None
    remaining: Optional[Decimal] = None


class Budget(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    project_id: str
    organisation_id: str
    total_budget: Decimal = Field(..., gt=0)
    allocations: List[BudgetAllocationDTO] = Field(default_factory=list)
    total_spent: Optional[Decimal] = None
    total_budgeted: Optional[Decimal] = None
    variance: Optional[Decimal] = None
    status: Literal["ACTIVE", "LOCKED", "CLOSED"] = "ACTIVE"
    version: int = 1
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


class BudgetCreate(BaseModel):
    project_id: str
    total_budget: Decimal = Field(..., gt=0)
    allocations: List[BudgetAllocationDTO] = Field(default_factory=list)

    @field_validator("total_budget", mode="before")
    @classmethod
    def validate_total_budget(cls, v):
        try:
            val = Decimal(str(v))
            if val < 0:
                raise ValueError("Total budget must be non-negative")
            return val
        except (ValueError, TypeError, InvalidOperation):
            raise ValueError("Total budget must be a valid number")


class BudgetAllocationUpdate(BaseModel):
    code: str
    budgeted_amount: Decimal = Field(..., ge=0)
    threshold_percentage: int = Field(80, ge=0, le=100)

    @field_validator("budgeted_amount", mode="before")
    @classmethod
    def validate_budgeted_amount(cls, v):
        try:
            val = Decimal(str(v))
            if val < 0:
                raise ValueError("Budgeted amount must be non-negative")
            return val
        except (ValueError, TypeError, InvalidOperation):
            raise ValueError("Budgeted amount must be a valid number")


class BudgetUpdate(BaseModel):
    allocations: List[BudgetAllocationUpdate]
    expected_version: int


class BudgetCategoryUpdate(BaseModel):
    original_budget: Decimal = Field(..., ge=0)
    expected_version: int = 1


class BudgetForecast(BaseModel):
    eac: Decimal  # Estimate at Completion
    projected_overrun: Decimal
    variance_at_completion: Decimal
