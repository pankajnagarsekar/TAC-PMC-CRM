from datetime import datetime, timezone
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, Field
from app.schemas.shared import PyObjectId

# Fixed CR-07: Use authoritative CodeMaster from financial schema
from app.schemas.financial import CodeMaster, CodeMasterCreate, CodeMasterUpdate

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

class AISummaryReportData(BaseModel):
    # Fixed CR-05: Using Decimal for all financial fields
    total_budget: Decimal = Field(default=Decimal("0.0"), ge=0)
    total_committed: Decimal = Field(default=Decimal("0.0"), ge=0)
    total_certified: Decimal = Field(default=Decimal("0.0"), ge=0)
    total_remaining: Decimal = Field(default=Decimal("0.0")) # Can be negative in over-committed scenarios
    over_budget_categories: List[str] = Field(default_factory=list)
    total_vendor_payable: Decimal = Field(default=Decimal("0.0"), ge=0)
    total_cash_in_hand: Decimal = Field(default=Decimal("0.0"))
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

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}
