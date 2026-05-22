from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class RetentionRelease:
    id: Optional[str]
    wo_id: str
    organisation_id: str
    amount_released: Decimal
    release_date: datetime
    release_reference: str
    notes: Optional[str]
    released_by: str
    created_at: Optional[datetime] = None
