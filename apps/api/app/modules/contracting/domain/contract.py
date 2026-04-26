from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Optional


@dataclass
class Contract:
    id: str
    work_order_id: str
    organisation_id: str
    vendor_id: str
    contract_value: Decimal
    start_date: datetime
    end_date: datetime
    terms: str
    status: str  # DRAFT | ACTIVE | EXPIRED | TERMINATED
    signed_by: Optional[str] = None
    signed_at: Optional[datetime] = None
    document_url: Optional[str] = None
