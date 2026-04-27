"""
Domain models for dashboard metrics and analytics.
Used as response DTOs for analytics endpoints.
"""

from typing import Dict, List

from pydantic import BaseModel, Field


# --- SCHEDULE HEALTH MODELS ---


class ScheduleHealthMetrics(BaseModel):
    """Schedule performance KPIs."""

    days_remaining: int = Field(
        ..., description="Days remaining until project completion"
    )
    days_planned: int = Field(..., description="Total planned duration in days")
    tasks_at_risk: int = Field(
        ..., description="Number of tasks with slack < 5 days"
    )
    critical_path_days: int = Field(
        ..., description="Total duration of critical path tasks"
    )
    status: str = Field(
        ..., description="Health status: green, yellow, red"
    )  # "green", "yellow", "red"

    class Config:
        json_schema_extra = {
            "example": {
                "days_remaining": 45,
                "days_planned": 120,
                "tasks_at_risk": 2,
                "critical_path_days": 45,
                "status": "green",
            }
        }


# --- RESOURCE UTILIZATION MODELS ---


class ResourceMetric(BaseModel):
    """Individual resource allocation metric."""

    resource_id: str = Field(..., description="Unique resource identifier")
    resource_name: str = Field(..., description="Display name of resource")
    allocated_hours: float = Field(..., description="Hours allocated to this project")
    available_hours: float = Field(..., description="Hours available per week")
    utilization_pct: float = Field(
        ..., description="Utilization percentage (allocated/available * 100)"
    )
    is_over_allocated: bool = Field(
        ..., description="Whether utilization exceeds 100%"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "resource_id": "user-123",
                "resource_name": "John Doe",
                "allocated_hours": 45.0,
                "available_hours": 40.0,
                "utilization_pct": 112.5,
                "is_over_allocated": True,
            }
        }


class RoleMetric(BaseModel):
    """Role-level aggregated allocation metric."""

    role_name: str = Field(..., description="Role/department name")
    total_allocated_hours: float = Field(..., description="Total hours allocated")
    total_available_hours: float = Field(
        ..., description="Total available hours for role"
    )
    utilization_pct: float = Field(..., description="Role-level utilization %")
    resource_count: int = Field(..., description="Number of resources in this role")

    class Config:
        json_schema_extra = {
            "example": {
                "role_name": "MEP",
                "total_allocated_hours": 450.0,
                "total_available_hours": 400.0,
                "utilization_pct": 112.5,
                "resource_count": 10,
            }
        }


class ResourceUtilizationData(BaseModel):
    """Resource allocation and utilization summary."""

    by_resource: Dict[str, ResourceMetric] = Field(
        ..., description="Utilization by individual resource"
    )
    by_role: Dict[str, RoleMetric] = Field(
        ..., description="Aggregated utilization by role"
    )
    over_allocated: List[str] = Field(
        ..., description="List of over-allocated resource names"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "by_resource": {
                    "John Doe": {
                        "resource_id": "user-123",
                        "resource_name": "John Doe",
                        "allocated_hours": 45.0,
                        "available_hours": 40.0,
                        "utilization_pct": 112.5,
                        "is_over_allocated": True,
                    }
                },
                "by_role": {
                    "MEP": {
                        "role_name": "MEP",
                        "total_allocated_hours": 450.0,
                        "total_available_hours": 400.0,
                        "utilization_pct": 112.5,
                        "resource_count": 10,
                    }
                },
                "over_allocated": ["John Doe", "Jane Smith"],
            }
        }


# --- FINANCIAL SUMMARY MODELS ---


class FinancialSummaryData(BaseModel):
    """Budget utilization and financial health metrics."""

    budget_total: float = Field(..., description="Total project budget")
    budget_spent: float = Field(..., description="Amount spent to date")
    budget_remaining: float = Field(..., description="Remaining budget")
    budget_utilization_pct: float = Field(..., description="% of budget consumed")
    burn_rate_daily: float = Field(..., description="Daily burn rate in currency")
    projected_overrun: float = Field(
        ..., description="Projected amount over budget at current burn rate"
    )
    is_over_budget: bool = Field(..., description="Whether spending exceeds budget")

    # EVM Metrics (BUG-023)
    planned_value: float = Field(0.0, description="BCWS: Budgeted Cost of Work Scheduled")
    earned_value: float = Field(0.0, description="BCWP: Budgeted Cost of Work Performed")
    actual_cost: float = Field(0.0, description="ACWP: Actual Cost of Work Performed")
    cpi: float = Field(1.0, description="Cost Performance Index")
    spi: float = Field(1.0, description="Schedule Performance Index")
    cost_variance: float = Field(0.0, description="EV - AC")
    schedule_variance: float = Field(0.0, description="EV - PV")

    class Config:
        json_schema_extra = {
            "example": {
                "budget_total": 500000.0,
                "budget_spent": 425000.0,
                "budget_remaining": 75000.0,
                "budget_utilization_pct": 85.0,
                "burn_rate_daily": 5000.0,
                "projected_overrun": 50000.0,
                "is_over_budget": False,
            }
        }


# --- TIMELINE ANALYTICS MODELS ---


class DayMetric(BaseModel):
    """Single day metric in timeline."""

    date: str = Field(..., description="ISO format date")
    tasks_completed: int = Field(..., description="Tasks completed on this day")
    utilization_pct: float = Field(..., description="Average utilization %")
    budget_spent: float = Field(..., description="Amount spent on this day")

    class Config:
        json_schema_extra = {
            "example": {
                "date": "2026-04-10T00:00:00",
                "tasks_completed": 5,
                "utilization_pct": 95.0,
                "budget_spent": 25000.0,
            }
        }


class TimelineAnalytics(BaseModel):
    """Historical trend analytics over date range."""

    daily_completion: List[DayMetric] = Field(
        ..., description="Daily task completion trend"
    )
    utilization_trend: List[DayMetric] = Field(
        ..., description="Daily resource utilization trend"
    )
    budget_spent_trend: List[DayMetric] = Field(
        ..., description="Daily budget burn trend"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "daily_completion": [
                    {
                        "date": "2026-04-10T00:00:00",
                        "tasks_completed": 5,
                        "utilization_pct": 95.0,
                        "budget_spent": 25000.0,
                    }
                ],
                "utilization_trend": [],
                "budget_spent_trend": [],
            }
        }


# --- AGGREGATED DASHBOARD DATA ---


class ProjectDashboardData(BaseModel):
    """Complete dashboard data (aggregated metrics)."""

    project_id: str = Field(..., description="Project identifier")
    project_name: str = Field(..., description="Project display name")
    schedule: ScheduleHealthMetrics = Field(..., description="Schedule health KPIs")
    resources: ResourceUtilizationData = Field(
        ..., description="Resource allocation metrics"
    )
    financial: FinancialSummaryData = Field(
        ..., description="Financial health metrics"
    )
    timeline: TimelineAnalytics = Field(..., description="Historical trends")
    updated_at: str = Field(
        ..., description="ISO timestamp when data was calculated"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "proj-001",
                "project_name": "Majorda Villa",
                "schedule": {
                    "days_remaining": 45,
                    "days_planned": 120,
                    "tasks_at_risk": 2,
                    "critical_path_days": 45,
                    "status": "green",
                },
                "resources": {
                    "by_resource": {},
                    "by_role": {},
                    "over_allocated": [],
                },
                "financial": {
                    "budget_total": 500000.0,
                    "budget_spent": 425000.0,
                    "budget_remaining": 75000.0,
                    "budget_utilization_pct": 85.0,
                    "burn_rate_daily": 5000.0,
                    "projected_overrun": 0.0,
                    "is_over_budget": False,
                },
                "timeline": {
                    "daily_completion": [],
                    "utilization_trend": [],
                    "budget_spent_trend": [],
                },
                "updated_at": "2026-04-13T12:30:00Z",
            }
        }
