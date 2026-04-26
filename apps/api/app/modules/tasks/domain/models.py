from typing import Optional
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class TaskModel:
    organisation_id: str
    project_id: str
    sr_no: int
    task_description: str
    assigned_to_name: str
    created_by: str
    created_by_name: str
    id: Optional[str] = None
    assigned_to_user_id: Optional[str] = None
    assigned_to_type: str = "user"
    deadline: Optional[datetime] = None
    status: str = "Open"
    priority: str = "Normal"
    notes: Optional[str] = None
    scheduler_task_id: Optional[str] = None
    version: int = 1
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
