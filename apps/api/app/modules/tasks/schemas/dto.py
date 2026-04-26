from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


def generate_alias(string: str) -> str:
    return string


def parse_flexible_date(v: Any) -> Optional[datetime]:
    if not v:
        return None
    if isinstance(v, datetime):
        return v
    if isinstance(v, str):
        if not v.strip():
            return None
        # Try ISO first
        try:
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            # Fallback to DD-MM-YYYY
            try:
                return datetime.strptime(v, "%d-%m-%Y")
            except ValueError:
                # Let pydantic try its default parsing if both custom ways fail
                return v
    return v


class BaseSchema(BaseModel):
    class Config:
        populate_by_name = True
        alias_generator = generate_alias


class TaskCreate(BaseSchema):
    project_id: str
    task_description: str
    assigned_to_user_id: Optional[str] = None
    assigned_to_name: str
    assigned_to_type: str = "user"
    deadline: Optional[datetime] = None
    priority: str = "Normal"
    notes: Optional[str] = None
    scheduler_task_id: Optional[str] = None

    @field_validator("deadline", mode="before")
    @classmethod
    def validate_deadline(cls, v: Any) -> Any:
        return parse_flexible_date(v)


class TaskUpdate(BaseSchema):
    task_description: Optional[str] = None
    assigned_to_user_id: Optional[str] = None
    assigned_to_name: Optional[str] = None
    assigned_to_type: Optional[str] = None
    deadline: Optional[datetime] = None
    priority: Optional[str] = None
    notes: Optional[str] = None
    scheduler_task_id: Optional[str] = None

    @field_validator("deadline", mode="before")
    @classmethod
    def validate_deadline(cls, v: Any) -> Any:
        return parse_flexible_date(v)


class TaskStatusUpdate(BaseSchema):
    status: str


class Task(TaskCreate):
    id: str = Field(alias="_id")
    sr_no: int
    status: str = "Open"
    created_by: str
    created_by_name: str
    version: int = 1
    created_at: datetime
    updated_at: datetime
    audit_log: List[Dict[str, Any]] = []
