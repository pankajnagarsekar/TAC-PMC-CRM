from pydantic import BaseModel, Field
from typing import Optional, Literal
from decimal import Decimal
from datetime import datetime, timezone
from app.schemas.shared import PyObjectId

class FundAllocationCreate(BaseModel):
    project_id: str
    category_id: str
    amount: Decimal = Field(..., ge=0)
    description: Optional[str] = None

class CashTransactionCreate(BaseModel):
    project_id: str
    category_id: str
    amount: Decimal = Field(..., ge=0)
    type: Literal["DEBIT", "CREDIT"]
    description: Optional[str] = None
    transaction_date: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))

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
    created_at: datetime

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}

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
    created_at: datetime

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}
