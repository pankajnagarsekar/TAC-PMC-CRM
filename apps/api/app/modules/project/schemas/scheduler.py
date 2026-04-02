from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ScheduleCalculateRequest(BaseModel):
    tasks: List[Dict[str, Any]]
    project_start: Optional[str] = None


class ScheduleSaveRequest(BaseModel):
    tasks: List[Dict[str, Any]]
    project_start: Optional[str] = None
    total_cost: Optional[float] = 0.0


class ScheduleResponse(BaseModel):
    tasks: List[Dict[str, Any]]
    critical_path: Optional[List[str]] = None
    total_duration_days: Optional[int] = None
    status: Optional[str] = None
    calculation_version: Optional[str] = None
    system_state: Optional[str] = None
    schedule_version: Optional[int] = None
