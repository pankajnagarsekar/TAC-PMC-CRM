from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from app.modules.shared.domain.types import PyObjectId


# CODE MASTER DTOs
class CodeMaster(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    organisation_id: Optional[str] = None
    category_name: str
    code: str
    description: Optional[str] = None
    budget_type: Literal["commitment", "fund_transfer"] = "commitment"
    active_status: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


class CodeMasterCreate(BaseModel):
    category_name: str
    code: str
    description: Optional[str] = None
    budget_type: Literal["commitment", "fund_transfer"] = "commitment"


class CodeMasterUpdate(BaseModel):
    category_name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    active_status: Optional[bool] = None


# PAYMENT CERTIFICATE DTOs
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
    status: Literal["Draft", "Pending", "Approved", "Completed", "Closed", "Cancelled"] = "Draft"
    total_payable: Decimal = Field(Decimal("0.0"), ge=0)
    fund_request: bool = False
    line_items: List[PCLineItem] = Field(default_factory=list)
    idempotency_key: Optional[str] = None
    version: int = 1
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
    last_pc_closed_date: Optional[datetime] = None
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
    amount: Decimal = Decimal("0.0")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}
