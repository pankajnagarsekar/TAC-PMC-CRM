from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


def generate_alias(string: str) -> str:
    return string


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


class TaskUpdate(BaseSchema):
    task_description: Optional[str] = None
    assigned_to_user_id: Optional[str] = None
    assigned_to_name: Optional[str] = None
    assigned_to_type: Optional[str] = None
    deadline: Optional[datetime] = None
    priority: Optional[str] = None
    notes: Optional[str] = None
    scheduler_task_id: Optional[str] = None


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
