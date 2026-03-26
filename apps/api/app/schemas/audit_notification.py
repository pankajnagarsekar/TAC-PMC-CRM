from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field
from app.schemas.shared import PyObjectId

class AuditLog(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    organisation_id: str
    module_name: str
    entity_type: str
    entity_id: str
    action_type: str
    user_id: str
    project_id: Optional[str] = None
    old_value: Optional[dict] = None
    new_value: Optional[dict] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

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
