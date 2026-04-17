"""
Analytics Service - Core metric calculations for dashboard KPIs.
Provides schedule health, resource utilization, financial summary, and timeline analytics.
"""

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from bson import Decimal128

from app.modules.financial.infrastructure.repository import FinancialStateRepository
from app.modules.project.infrastructure.repository import (
    BudgetRepository,
    ProjectRepository,
    ScheduleRepository,
)
from app.modules.shared.domain.financial_engine import FinancialEngine

logger = logging.getLogger(__name__)


class ScheduleHealthMetrics:
    """Schedule health status KPIs."""

    def __init__(self):
        self.days_remaining: int = 0
        self.days_planned: int = 0
        self.tasks_at_risk: int = 0  # slack < 5 days
        self.critical_path_days: int = 0
        self.status: str = "green"  # green, yellow, red

    def to_dict(self) -> Dict[str, Any]:
        return {
            "days_remaining": self.days_remaining,
            "days_planned": self.days_planned,
            "tasks_at_risk": self.tasks_at_risk,
            "critical_path_days": self.critical_path_days,
            "status": self.status,
        }


class ResourceMetrics:
    """Individual resource allocation metrics."""

    def __init__(self, resource_id: str, resource_name: str):
        self.resource_id = resource_id
        self.resource_name = resource_name
        self.allocated_hours: Decimal = Decimal("0")
        self.available_hours: Decimal = Decimal("0")
        self.utilization_pct: Decimal = Decimal("0")
        self.is_over_allocated: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "resource_id": self.resource_id,
            "resource_name": self.resource_name,
            "allocated_hours": float(self.allocated_hours),
            "available_hours": float(self.available_hours),
            "utilization_pct": float(self.utilization_pct),
            "is_over_allocated": self.is_over_allocated,
        }


class RoleMetrics:
    """Role-level aggregated allocation metrics."""

    def __init__(self, role_name: str):
        self.role_name = role_name
        self.total_allocated_hours: Decimal = Decimal("0")
        self.total_available_hours: Decimal = Decimal("0")
        self.utilization_pct: Decimal = Decimal("0")
        self.resource_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role_name": self.role_name,
            "total_allocated_hours": float(self.total_allocated_hours),
            "total_available_hours": float(self.total_available_hours),
            "utilization_pct": float(self.utilization_pct),
            "resource_count": self.resource_count,
        }


class ResourceUtilizationData:
    """Resource allocation and utilization data."""

    def __init__(self):
        self.by_resource: Dict[str, ResourceMetrics] = {}
        self.by_role: Dict[str, RoleMetrics] = {}
        self.over_allocated: List[str] = []  # resource names

    def to_dict(self) -> Dict[str, Any]:
        return {
            "by_resource": {k: v.to_dict() for k, v in self.by_resource.items()},
            "by_role": {k: v.to_dict() for k, v in self.by_role.items()},
            "over_allocated": self.over_allocated,
        }


class FinancialSummaryData:
    """Budget and cash flow summary metrics."""

    def __init__(self):
        self.budget_total: Decimal = Decimal("0")
        self.budget_spent: Decimal = Decimal("0")
        self.budget_remaining: Decimal = Decimal("0")
        self.budget_utilization_pct: Decimal = Decimal("0")
        self.burn_rate_daily: Decimal = Decimal("0")
        self.projected_overrun: Decimal = Decimal("0")
        self.is_over_budget: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "budget_total": float(self.budget_total),
            "budget_spent": float(self.budget_spent),
            "budget_remaining": float(self.budget_remaining),
            "budget_utilization_pct": float(self.budget_utilization_pct),
            "burn_rate_daily": float(self.burn_rate_daily),
            "projected_overrun": float(self.projected_overrun),
            "is_over_budget": self.is_over_budget,
        }


class DayMetric:
    """Single day metric for timeline analytics."""

    def __init__(self, date: datetime):
        self.date = date.isoformat()
        self.tasks_completed: int = 0
        self.utilization_pct: Decimal = Decimal("0")
        self.budget_spent: Decimal = Decimal("0")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date,
            "tasks_completed": self.tasks_completed,
            "utilization_pct": float(self.utilization_pct),
            "budget_spent": float(self.budget_spent),
        }


class TimelineAnalytics:
    """Historical trend analytics over date range."""

    def __init__(self):
        self.daily_completion: List[DayMetric] = []
        self.utilization_trend: List[DayMetric] = []
        self.budget_spent_trend: List[DayMetric] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "daily_completion": [m.to_dict() for m in self.daily_completion],
            "utilization_trend": [m.to_dict() for m in self.utilization_trend],
            "budget_spent_trend": [m.to_dict() for m in self.budget_spent_trend],
        }


class AnalyticsService:
    """
    Calculates dashboard analytics and KPI metrics.
    All calculations are eager (not cached) but can be cached at route level.
    """

    def __init__(self, db):
        self.db = db
        self.project_repo = ProjectRepository(db)
        self.schedule_repo = ScheduleRepository(db)
        self.budget_repo = BudgetRepository(db)
        self.fin_state_repo = FinancialStateRepository(db)

    async def calculate_schedule_health(
        self, project_id: str, organisation_id: str
    ) -> ScheduleHealthMetrics:
        """
        Calculate schedule health: days remaining, tasks at risk, critical path status.

        Status logic:
        - GREEN: days_remaining >= 20% of planned AND tasks_at_risk == 0
        - YELLOW: days_remaining 10-20% OR tasks_at_risk 1-3
        - RED: days_remaining < 10% OR tasks_at_risk > 3
        """
        metrics = ScheduleHealthMetrics()

        # Fetch schedule
        schedule = await self.schedule_repo.find_one(
            {"project_id": project_id, "organisation_id": organisation_id}
        )

        if not schedule or "tasks" not in schedule:
            # No schedule → assume green (no risk)
            return metrics

        tasks = schedule.get("tasks", [])
        now = datetime.now(timezone.utc)

        # Calculate days remaining (to max task finish)
        max_finish = None
        critical_path_days = 0
        tasks_at_risk = 0

        for task in tasks:
            finish_str = task.get("finish") or task.get("end_date")
            if finish_str:
                try:
                    finish_dt = (
                        finish_str
                        if isinstance(finish_str, datetime)
                        else datetime.fromisoformat(str(finish_str).replace("Z", "+00:00"))
                    )
                    if max_finish is None or finish_dt > max_finish:
                        max_finish = finish_dt
                except (ValueError, TypeError):
                    continue

            # Count tasks at risk (slack < 5 days)
            slack = task.get("slack") or task.get("free_slack") or 0
            if slack and Decimal(str(slack)) < Decimal("5"):
                tasks_at_risk += 1

            # Track critical path
            if task.get("is_critical") or task.get("isCritical"):
                duration = task.get("duration") or 0
                critical_path_days += int(duration)

        if max_finish:
            metrics.days_remaining = max((max_finish - now).days, 0)
            # Assume planned was 1.5x of actual remaining (heuristic)
            metrics.days_planned = int(metrics.days_remaining * 1.5)
        else:
            metrics.days_remaining = 0
            metrics.days_planned = 0

        metrics.tasks_at_risk = tasks_at_risk
        metrics.critical_path_days = critical_path_days

        # Determine status color
        if metrics.days_planned > 0:
            pct_remaining = (
                Decimal(str(metrics.days_remaining))
                / Decimal(str(metrics.days_planned))
                * 100
            )
        else:
            pct_remaining = Decimal("100")

        if pct_remaining >= Decimal("20") and tasks_at_risk == 0:
            metrics.status = "green"
        elif pct_remaining < Decimal("10") or tasks_at_risk > 3:
            metrics.status = "red"
        else:
            metrics.status = "yellow"

        return metrics

    async def calculate_resource_utilization(
        self, project_id: str, organisation_id: str
    ) -> ResourceUtilizationData:
        """
        Calculate resource allocation and utilization percentages.

        Over-allocation: utilization_pct > 100%
        """
        data = ResourceUtilizationData()

        # Fetch schedule
        schedule = await self.schedule_repo.find_one(
            {"project_id": project_id, "organisation_id": organisation_id}
        )

        if not schedule or "tasks" not in schedule:
            return data

        tasks = schedule.get("tasks", [])

        # Aggregate hours by resource
        resource_hours: Dict[str, Tuple[Decimal, str]] = {}  # {resource_id: (hours, role)}

        for task in tasks:
            duration = Decimal(str(task.get("duration") or 0))
            assigned_to = task.get("assigned_to_name") or task.get("assignedTo")

            if assigned_to and duration > 0:
                role = task.get("assigned_role") or "Unspecified"
                if assigned_to not in resource_hours:
                    resource_hours[assigned_to] = (Decimal("0"), role)

                current_hours, existing_role = resource_hours[assigned_to]
                resource_hours[assigned_to] = (current_hours + duration, existing_role)

        # Calculate utilization (assume 8 hrs/day, 5 days/week)
        working_days_per_week = Decimal("5")
        hours_per_day = Decimal("8")
        hours_available_per_week = working_days_per_week * hours_per_day

        for resource_name, (allocated, role) in resource_hours.items():
            metric = ResourceMetrics(resource_name, resource_name)
            metric.allocated_hours = allocated
            # Assume 1 week availability per resource (simplified)
            metric.available_hours = hours_available_per_week

            if metric.available_hours > 0:
                metric.utilization_pct = (
                    metric.allocated_hours / metric.available_hours * Decimal("100")
                )
            else:
                metric.utilization_pct = Decimal("0")

            metric.is_over_allocated = metric.utilization_pct > Decimal("100")
            if metric.is_over_allocated:
                data.over_allocated.append(resource_name)

            data.by_resource[resource_name] = metric

            # Aggregate by role
            if role not in data.by_role:
                data.by_role[role] = RoleMetrics(role)

            role_metric = data.by_role[role]
            role_metric.total_allocated_hours += allocated
            role_metric.total_available_hours += hours_available_per_week
            role_metric.resource_count += 1

        # Calculate role-level utilization
        for role_metric in data.by_role.values():
            if role_metric.total_available_hours > 0:
                role_metric.utilization_pct = (
                    role_metric.total_allocated_hours
                    / role_metric.total_available_hours
                    * Decimal("100")
                )

        return data

    async def calculate_financial_summary(
        self, project_id: str, organisation_id: str
    ) -> FinancialSummaryData:
        """
        Calculate budget utilization and burn rate.

        Burn rate = budget_spent / days_elapsed (if any)
        Projected overrun = (burn_rate * total_days) - budget_total
        """
        data = FinancialSummaryData()

        # Fetch master financial state (project_id is sufficient; project is org-scoped)
        master_state = await self.fin_state_repo.find_one(
            {
                "project_id": project_id,
                "category_id": "MASTER",
            }
        )

        if not master_state:
            # Fallback: sum all per-category states
            agg = await self.fin_state_repo.aggregate(
                [
                    {
                        "$match": {
                            "project_id": project_id,
                            "category_id": {"$ne": "MASTER"},
                        }
                    },
                    {
                        "$group": {
                            "_id": None,
                            "budget": {"$sum": "$original_budget"},
                            "spent": {"$sum": "$committed_value"},
                        }
                    },
                ]
            ).to_list(1)

            if agg:
                data.budget_total = FinancialEngine.to_decimal(agg[0].get("budget"))
                data.budget_spent = FinancialEngine.to_decimal(agg[0].get("spent"))
        else:
            data.budget_total = FinancialEngine.to_decimal(
                master_state.get("original_budget")
            )
            data.budget_spent = FinancialEngine.to_decimal(
                master_state.get("committed_value")
            )

        # Calculate remaining budget
        data.budget_remaining = data.budget_total - data.budget_spent
        data.is_over_budget = data.budget_spent > data.budget_total

        # Calculate utilization percentage
        if data.budget_total > 0:
            data.budget_utilization_pct = (
                data.budget_spent / data.budget_total * Decimal("100")
            )
        else:
            data.budget_utilization_pct = Decimal("0")

        # Calculate daily burn rate (budget_spent / days_elapsed)
        project = await self.project_repo.get_by_id(project_id)
        if project and project.get("created_at"):
            created_at = (
                project["created_at"]
                if isinstance(project["created_at"], datetime)
                else datetime.fromisoformat(str(project["created_at"]))
            )
            days_elapsed = (datetime.now(timezone.utc) - created_at).days
            if days_elapsed > 0 and data.budget_spent > 0:
                data.burn_rate_daily = data.budget_spent / Decimal(str(days_elapsed))

                # Projected overrun = (burn_rate * total_days) - budget_total
                # Assuming total_days = 1.5 * days_elapsed (heuristic)
                projected_cost = data.burn_rate_daily * Decimal(str(days_elapsed * 1.5))
                data.projected_overrun = max(
                    Decimal("0"), projected_cost - data.budget_total
                )

        return data

    async def calculate_timeline_analytics(
        self,
        project_id: str,
        organisation_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> TimelineAnalytics:
        """
        Calculate daily trends for task completion and budget burn over date range.

        Returns daily metrics aggregated from task updates and financial records.
        """
        analytics = TimelineAnalytics()

        # Default to last 30 days if not specified
        if not end_date:
            end_date = datetime.now(timezone.utc)
        if not start_date:
            start_date = end_date - timedelta(days=30)

        # Generate daily time buckets
        current_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        while current_date <= end_date:
            analytics.daily_completion.append(DayMetric(current_date))
            analytics.utilization_trend.append(DayMetric(current_date))
            analytics.budget_spent_trend.append(DayMetric(current_date))
            current_date += timedelta(days=1)

        # Fetch task completion history (if available via audit trail)
        # For now, populate with static data; would integrate with audit service
        # This is a simplified implementation

        return analytics
