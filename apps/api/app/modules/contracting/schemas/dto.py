from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from app.modules.shared.domain.types import PyObjectId


# WORK ORDER DTOs
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


# VENDOR DTOs
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


# LEDGER DTOs (Part of Contracting Domain)
class VendorLedgerEntry(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    vendor_id: str
    project_id: str
    ref_id: str
    entry_type: Literal["PC_CERTIFIED", "PAYMENT_MADE", "RETENTION_HELD"]
    amount: Decimal = Decimal("0.0")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}
