from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from app.modules.shared.domain.types import PyObjectId


class RetentionReleaseCreate(BaseModel):
    amount_released: Decimal = Field(..., ge=0)
    release_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    release_reference: str = Field(..., min_length=1)
    notes: Optional[str] = ""


class RetentionReleaseResponse(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id", serialization_alias="id")
    organisation_id: str
    wo_id: str
    amount_released: Decimal
    release_date: datetime
    release_reference: str
    notes: Optional[str] = ""
    released_by: str
    created_at: datetime

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}
