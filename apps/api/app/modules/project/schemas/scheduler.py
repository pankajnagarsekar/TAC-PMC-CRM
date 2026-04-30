from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ScheduleTaskDTO(BaseModel):
    """Authoritative DTO for a single task within a project schedule."""
    task_id: str
    task_name: str
    project_id: str
    parent_id: Optional[str] = None
    wbs_code: Optional[str] = None
    
    # Scheduling fields
    scheduled_start: Optional[str] = None
    scheduled_finish: Optional[str] = None
    scheduled_duration: Optional[int] = 0
    
    # Resources (REQ-010, REQ-011)
    assignee_ids: List[str] = Field(default_factory=list)
    heads: int = 0
    
    # Status & Progress
    task_status: Optional[str] = "Planned"
    percent_complete: float = 0.0
    
    # CPM Results
    is_critical: bool = False
    total_slack: int = 0
    
    model_config = {"extra": "allow"}


class ScheduleCalculateRequest(BaseModel):
    tasks: List[ScheduleTaskDTO]
    project_start: Optional[str] = None


class ScheduleSaveRequest(BaseModel):
    tasks: List[ScheduleTaskDTO]
    project_start: Optional[str] = None
    total_cost: Optional[float] = 0.0


class ScheduleChangeRequest(BaseModel):
    project_id: str
    task_id: str
    changes: Dict[str, Any]
    version: int
    trigger_source: str


class ScheduleResponse(BaseModel):
    tasks: List[ScheduleTaskDTO]
    critical_path: Optional[List[str]] = None
    total_duration_days: Optional[int] = None
    status: Optional[str] = None
    calculation_version: Optional[str] = None
    system_state: Optional[str] = None
    schedule_version: Optional[int] = None
