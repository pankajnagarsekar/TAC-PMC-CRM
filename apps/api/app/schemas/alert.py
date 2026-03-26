from datetime import datetime, timezone
from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from app.schemas.shared import PyObjectId

class Alert(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    organisation_id: str
    project_id: Optional[str] = None
    alert_type: str # e.g., "ZOMBIE_RECORD", "FINANCIAL_DIVERGENCE", "INTEGRITY_FAILURE"
    severity: Literal["low", "medium", "high", "critical"]
    message: str
    data: Optional[Dict[str, Any]] = None
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    version: int = 1

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}
