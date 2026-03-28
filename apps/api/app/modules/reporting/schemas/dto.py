from datetime import datetime, timezone
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, Field
from app.modules.shared.domain.types import PyObjectId

class AISummaryReportData(BaseModel):
    total_budget: Decimal = Field(default=Decimal("0.0"), ge=0)
    total_committed: Decimal = Field(default=Decimal("0.0"), ge=0)
    total_certified: Decimal = Field(default=Decimal("0.0"), ge=0)
    total_remaining: Decimal = Field(default=Decimal("0.0"))
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
