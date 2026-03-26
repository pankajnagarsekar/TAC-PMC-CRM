from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from decimal import Decimal


class ScheduleTask(BaseModel):
    """Individual task in a project schedule."""
    id: str
    name: str
    duration: int  # in days
    dependencies: List[str] = Field(default_factory=list)
    estimated_cost: Optional[Decimal] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": "task-1",
                "name": "Foundation Work",
                "duration": 10,
                "dependencies": [],
                "estimated_cost": 5000.00
            }
        }


class ScheduleCalculateRequest(BaseModel):
    """Request to calculate project schedule using critical path method."""
    tasks: List[ScheduleTask] = Field(..., description="List of tasks with dependencies")
    project_start: str = Field(default="01-01-26", description="Project start date (DD-MM-YY format)")

    class Config:
        json_schema_extra = {
            "example": {
                "tasks": [
                    {"id": "task-1", "name": "Foundation", "duration": 10, "dependencies": []},
                    {"id": "task-2", "name": "Framing", "duration": 15, "dependencies": ["task-1"]}
                ],
                "project_start": "01-01-26"
            }
        }


class ScheduleSaveRequest(BaseModel):
    """Request to save a calculated project schedule."""
    tasks: List[Dict[str, Any]] = Field(..., description="Final scheduled tasks with calculated dates")
    project_start: str = Field(..., description="Project start date")
    total_cost: Decimal = Field(default=Decimal("0.00"), description="Total project cost")

    class Config:
        json_schema_extra = {
            "example": {
                "tasks": [
                    {
                        "id": "task-1",
                        "name": "Foundation",
                        "start_date": "2026-01-01",
                        "end_date": "2026-01-11"
                    }
                ],
                "project_start": "01-01-26",
                "total_cost": 150000.00
            }
        }


class ScheduleResponse(BaseModel):
    """Response with calculated schedule data."""
    tasks: List[Dict[str, Any]] = []
    critical_path: List[str] = []
    total_duration: int = 0
    project_start: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "tasks": [],
                "critical_path": ["task-1", "task-2"],
                "total_duration": 25,
                "project_start": "01-01-26"
            }
        }
