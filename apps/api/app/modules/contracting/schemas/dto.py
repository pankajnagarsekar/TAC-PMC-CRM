from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Literal, Optional

import html
import re

from pydantic import BaseModel, Field, field_validator, computed_field

from app.modules.shared.domain.types import PyObjectId


# WORK ORDER DTOs
class WOLineItem(BaseModel):
    sr_no: int
    description: str = ""
    qty: Decimal = Field(Decimal("0.0"), ge=0)
    rate: Decimal = Field(Decimal("0.0"), ge=0)
    total: Decimal = Field(Decimal("0.0"), ge=0)

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}

    @field_validator("qty", "rate")
    @classmethod
    def prevent_negative(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("Value cannot be negative")
        return v


class WorkOrder(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id", serialization_alias="id")
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
    status: Literal["Draft", "Pending", "Approved", "Completed", "Closed", "Cancelled"] = "Draft"
    line_items: List[WOLineItem] = Field(default_factory=list)
    version: int = 1
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @computed_field
    @property
    def wo_date(self) -> datetime:
        """Alias for created_at to stay consistent with template and display requirements."""
        return self.created_at

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
    status: Optional[Literal["Draft", "Pending", "Approved", "Completed", "Closed", "Cancelled"]] = None
    line_items: Optional[List[WOLineItem]] = None
    discount: Optional[Decimal] = Field(None, ge=0)
    retention_percent: Optional[Decimal] = Field(None, ge=0, le=100)
    expected_version: int

    @field_validator("status")
    @classmethod
    def validate_transition(cls, v, info):
        # Placeholder for complex transition logic if needed
        return v


# VENDOR DTOs
class Vendor(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id", serialization_alias="id")
    organisation_id: str
    name: str
    gstin: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    active_status: bool = True
    version: int = 1
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


class VendorCreate(BaseModel):
    name: str
    gstin: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None

    @field_validator("name", mode="before")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        # Strip HTML tags to prevent stored XSS
        v = re.sub(r"<[^>]+>", "", str(v)).strip()
        if not v:
            raise ValueError("Vendor name cannot be empty")
        return html.escape(v)

    @field_validator("gstin")
    @classmethod
    def validate_gstin(cls, v: Optional[str]) -> Optional[str]:
        if v:
            v = v.strip().upper()
            if not re.match(r"^\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d]$", v):
                raise ValueError("Invalid GSTIN format. Expected: 22AAAAA0000A1Z5")
        return v
    address: Optional[str] = None


class VendorUpdate(BaseModel):
    name: Optional[str] = None
    gstin: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    active_status: Optional[bool] = None
    expected_version: int

    @field_validator("name", mode="before")
    @classmethod
    def sanitize_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = re.sub(r"<[^>]+>", "", str(v)).strip()
        if not v:
            raise ValueError("Vendor name cannot be empty")
        return html.escape(v)

    @field_validator("gstin")
    @classmethod
    def validate_gstin(cls, v: Optional[str]) -> Optional[str]:
        if v:
            v = v.strip().upper()
            if not re.match(r"^\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d]$", v):
                raise ValueError("Invalid GSTIN format. Expected: 22AAAAA0000A1Z5")
        return v


# LEDGER DTOs (Part of Contracting Domain)
class VendorLedgerEntry(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id", serialization_alias="id")
    vendor_id: str
    project_id: str
    ref_id: str
    entry_type: Literal["COMMITTED", "PC_CERTIFIED", "PAYMENT_MADE", "RETENTION_HELD"]
    amount: Decimal = Decimal("0.0")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


# CONTRACT DTOs
class Contract(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id", serialization_alias="id")
    work_order_id: str
    organisation_id: str
    vendor_id: str
    contract_value: Decimal = Field(Decimal("0.0"), ge=0)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    terms: str = ""
    status: Literal["DRAFT", "ACTIVE", "EXPIRED", "TERMINATED"] = "DRAFT"
    signed_by: Optional[str] = None
    signed_at: Optional[datetime] = None
    document_url: Optional[str] = None
    version: int = 1
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


class ContractCreate(BaseModel):
    work_order_id: str
    vendor_id: str
    contract_value: Decimal = Field(..., ge=0)
    start_date: datetime
    end_date: datetime
    terms: str


class ContractUpdate(BaseModel):
    terms: Optional[str] = None
    status: Optional[Literal["DRAFT", "ACTIVE", "EXPIRED", "TERMINATED"]] = None
    document_url: Optional[str] = None
    signed_by: Optional[str] = None
    signed_at: Optional[datetime] = None
    expected_version: int
