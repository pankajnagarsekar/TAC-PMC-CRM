"""
Audit Logging schema for the Enterprise PPM Scheduler.
Constitution §8: "All changes... must be logged in the project_audit_logs collection."
"""
from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from .shared_types import PyObjectId, AuditAction, ChangeSource

class AuditLogEntry(BaseModel):
    """
    Mandatory audit record for scheduler actions.
    Persisted within the same transaction as the primary change.
    """
    id: Optional[PyObjectId] = Field(None, alias="_id")
    project_id: PyObjectId
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: str
    action: AuditAction
    trigger_source: ChangeSource
    
    # Context
    task_id: Optional[PyObjectId] = None
    baseline_id: Optional[PyObjectId] = None
    
    # Data diff/snapshot
    # For large projects, we store specific changes rather than full snapshots.
    changes: Optional[dict[str, Any]] = None
    comment: Optional[str] = None
    
    # Technical correlation
    idempotency_key: Optional[str] = None
    calculation_version: Optional[str] = None

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={datetime: lambda v: v.isoformat()}
    )
