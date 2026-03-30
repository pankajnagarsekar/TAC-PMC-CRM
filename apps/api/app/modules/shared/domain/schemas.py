from datetime import datetime, timezone
from typing import Any, Dict, Generic, Literal, Optional, TypeVar

from pydantic import BaseModel, Field

from .types import PyObjectId


class AuditLog(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    organisation_id: str
    module_name: str
    entity_type: str
    entity_id: str
    action_type: str
    user_id: str
    project_id: Optional[str] = None
    old_value_json: Optional[dict] = Field(default=None, alias="old_value")
    new_value_json: Optional[dict] = Field(default=None, alias="new_value")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


class Notification(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    organisation_id: str
    recipient_role: Optional[str] = None
    recipient_user_id: Optional[str] = None
    title: str
    message: str
    notification_type: str = "info"
    priority: str = "normal"
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    sender_id: Optional[str] = None
    sender_name: Optional[str] = None
    is_read: bool = False
    read_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


class NotificationCreate(BaseModel):
    recipient_role: Optional[str] = None
    recipient_user_id: Optional[str] = None
    title: str
    message: str
    notification_type: str = "info"
    priority: str = "normal"
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    project_id: Optional[str] = None
    project_name: Optional[str] = None


class Alert(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    organisation_id: str
    project_id: Optional[str] = None
    alert_type: (
        str  # e.g., "ZOMBIE_RECORD", "FINANCIAL_DIVERGENCE", "INTEGRITY_FAILURE"
    )
    severity: Literal["low", "medium", "high", "critical"]
    message: str
    data: Optional[Dict[str, Any]] = None
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    version: int = 1

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


class Snapshot(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    entity_type: str
    entity_id: str
    organisation_id: str
    project_id: Optional[str] = None
    report_type: str
    version: int
    data_json: Dict[str, Any]
    data_checksum: str
    generated_by: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_latest: bool = True
    immutable_flag: bool = True

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}


T = TypeVar("T")


class GenericResponse(BaseModel, Generic[T]):
    success: bool = True
    message: Optional[str] = None
    data: Optional[T] = None
