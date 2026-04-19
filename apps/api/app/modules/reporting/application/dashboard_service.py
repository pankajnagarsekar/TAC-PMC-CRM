"""
Dashboard Service - Aggregates analytics into unified dashboard response.
Provides 30-second caching for performance optimization.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from bson import ObjectId
from app.modules.shared.domain.financial_engine import FinancialEngine
from app.modules.project.infrastructure.repository import ProjectRepository
from app.modules.reporting.domain.metrics import ProjectDashboardData
from app.modules.reporting.application.analytics_service import AnalyticsService

logger = logging.getLogger(__name__)


class DashboardCache:
    """Simple in-memory cache with TTL (30 seconds)."""

    def __init__(self, ttl_seconds: int = 30):
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, tuple[Any, datetime]] = {}

    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired."""
        if key not in self.cache:
            return None

        value, created_at = self.cache[key]
        if datetime.now(timezone.utc) - created_at > timedelta(seconds=self.ttl_seconds):
            del self.cache[key]
            return None

        return value

    def set(self, key: str, value: Any) -> None:
        """Set cached value with current timestamp."""
        self.cache[key] = (value, datetime.now(timezone.utc))

    def invalidate(self, key: str) -> None:
        """Manually invalidate a cache key."""
        if key in self.cache:
            del self.cache[key]


class DashboardService:
    """
    Aggregates all dashboard analytics into a single response.
    Caches results for 30 seconds to avoid recalculation on rapid requests.
    """

    # Shared cache instance
    _cache = DashboardCache(ttl_seconds=5)

    def __init__(self, db, analytics_service: AnalyticsService):
        self.db = db
        self.analytics_service = analytics_service
        self.project_repo = ProjectRepository(db)

    @classmethod
    def invalidate_project_cache(cls, project_id: str):
        """Authoritative cache invalidation for a project (BUG-009)."""
        cls._cache.invalidate(project_id)
        logger.info(f"DASHBOARD_CACHE_INVALIDATED: {project_id}")

    async def get_project_dashboard(
        self, project_id: str, organisation_id: str
    ) -> ProjectDashboardData:
        """
        Aggregate all analytics into single dashboard response.

        Returns cached result for 30 seconds to avoid expensive recalculations.

        Args:
            project_id: Project identifier
            organisation_id: Organisation for scoping

        Returns:
            ProjectDashboardData with all metrics aggregated
        """
        cache_key = f"dashboard:{organisation_id}:{project_id}"

        # Check cache first
        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.debug(f"Dashboard cache hit for {project_id}")
            return cached

        logger.debug(f"Dashboard cache miss for {project_id}, recalculating...")

        # Fetch project details
        project = await self.project_repo.get_by_id(project_id)
        if not project:
            project = await self.project_repo.find_one(
                {"project_id": project_id, "organisation_id": organisation_id}
            )

        if not project:
            from app.modules.shared.domain.exceptions import NotFoundError

            raise NotFoundError("Project", project_id)

        project_name = project.get("project_name") or project.get("name") or "Untitled"

        # Aggregate all 4 metrics in parallel
        schedule = await self.analytics_service.calculate_schedule_health(
            project_id, organisation_id
        )
        resources = await self.analytics_service.calculate_resource_utilization(
            project_id, organisation_id
        )
        financial = await self.analytics_service.calculate_financial_summary(
            project_id, organisation_id
        )
        timeline = await self.analytics_service.calculate_timeline_analytics(
            project_id, organisation_id
        )

        # Convert analytics objects to dicts for Pydantic model validation
        from app.modules.reporting.domain.metrics import (
            ScheduleHealthMetrics as ScheduleModel,
            ResourceUtilizationData as ResourceModel,
            FinancialSummaryData as FinancialModel,
            TimelineAnalytics as TimelineModel,
        )

        schedule_dict = schedule.to_dict() if hasattr(schedule, "to_dict") else schedule
        resources_dict = resources.to_dict() if hasattr(resources, "to_dict") else resources
        financial_dict = financial.to_dict() if hasattr(financial, "to_dict") else financial
        timeline_dict = timeline.to_dict() if hasattr(timeline, "to_dict") else timeline

        # Construct dashboard
        dashboard = ProjectDashboardData(
            project_id=project_id,
            project_name=project_name,
            schedule=schedule_dict,
            resources=resources_dict,
            financial=financial_dict,
            timeline=timeline_dict,
            updated_at=datetime.now(timezone.utc).isoformat() + "Z",
        )

        # Cache result
        self._cache.set(cache_key, dashboard)

        return dashboard

    async def get_project_dashboard_stats(
        self, project_id: str, organisation_id: str
    ) -> Dict[str, Any]:
        """Returns aggregated statistics for the project dashboard."""
        # 1. Fetch Master Financial State
        master_state = await self.db.financial_state.find_one(
            {"project_id": project_id, "category_id": "MASTER"}
        )

        # 2. Fetch Project Metadata
        project = await self.project_repo.get_by_id(project_id)

        # 3. Fetch counts for active items (Tasks + Work Orders)
        active_tasks_count = await self.db.tasks.count_documents(
            {
                "project_id": project_id,
                "organisation_id": organisation_id,
                "status": {"$in": ["Open", "In Progress"]},
            }
        )
        active_wos_count = await self.db.work_orders.count_documents(
            {
                "project_id": project_id,
                "organisation_id": organisation_id,
                "status": {"$in": ["Draft", "Pending", "Approved"]},
            }
        )

        schedule = await self.db.project_schedules.find_one({"project_id": project_id})
        tasks_count = len(schedule.get("tasks", [])) if schedule else 0

        # 4. Filter overdue milestones from schedule
        overdue_milestones_count = 0
        if schedule:
            now_str = datetime.now(timezone.utc).date().isoformat()
            for t in schedule.get("tasks", []):
                finish_date = t.get("scheduled_finish")
                if (
                    t.get("is_milestone")
                    and finish_date
                    and finish_date < now_str
                    and float(t.get("percent_complete", 0)) < 100
                ):
                    overdue_milestones_count += 1

        # 5. Construct high-level stats
        stats = {
            "overview": {
                "total_phases": tasks_count,
                "active_items": active_tasks_count + active_wos_count,
                "overdue_milestones": overdue_milestones_count,
                "total_budget": float(
                    FinancialEngine.to_decimal(master_state.get("original_budget", 0))
                    if master_state
                    else 0
                ),
                "net_committed": float(
                    FinancialEngine.to_decimal(master_state.get("committed_value", 0))
                    if master_state
                    else 0
                ),
                "net_certified": float(
                    FinancialEngine.to_decimal(master_state.get("certified_value", 0))
                    if master_state
                    else 0
                ),
            },
            "tasks_count": tasks_count,
            "completion_percentage": float(
                project.get("completion_percentage", 0) if project else 0
            ),
            "status": project.get("status", "active") if project else "active",
        }

        return stats

    async def get_financials(self, project_id: str) -> List[Any]:
        """Fetch category-wise financial status for a project."""
        # Fetch all financial states for this project (excluding MASTER)
        states_cursor = self.db.financial_state.find(
            {"project_id": project_id, "category_id": {"$ne": "MASTER"}}
        )
        states = await states_cursor.to_list(length=100)

        # Join with category names
        results = []
        for s in states:
            cat_id = s.get("category_id")
            category = await self.db.code_master.find_one({"code": cat_id})
            if not category and ObjectId.is_valid(str(cat_id)):
                category = await self.db.code_master.find_one({"_id": ObjectId(str(cat_id))})

            code_str = category.get("code", "") if category else ""
            original_budget = float(FinancialEngine.to_decimal(s.get("original_budget", 0)))
            committed_value = float(FinancialEngine.to_decimal(s.get("committed_value", 0)))
            certified_value = float(FinancialEngine.to_decimal(s.get("certified_value", 0)))
            results.append(
                {
                    "_id": str(s.get("_id", "")),
                    "project_id": project_id,
                    "category_id": cat_id,
                    "category_name": category.get("category_name", "Unknown")
                    if category
                    else "Unknown",
                    "category_code": code_str,
                    "original_budget": original_budget,
                    "committed_value": committed_value,
                    "certified_value": certified_value,
                    "balance_budget_remaining": float(
                        FinancialEngine.to_decimal(s.get("balance_budget_remaining", 0))
                    ),
                    "over_commit_flag": s.get("over_commit_flag", False),
                    # Legacy aliases kept for backward compat
                    "budget": original_budget,
                    "committed": committed_value,
                    "certified": certified_value,
                }
            )

        return results

    async def get_vendor_payables(self, project_id: str) -> List[Any]:
        """Fetch outstanding amounts per vendor for a project."""
        # Aggregate from vendor_ledger
        pipeline = [
            {"$match": {"project_id": project_id}},
            {
                "$group": {
                    "_id": "$vendor_id",
                    "total_certified": {
                        "$sum": {
                            "$cond": [
                                {"$eq": ["$entry_type", "PC_CERTIFIED"]},
                                "$amount",
                                0,
                            ]
                        }
                    },
                    "total_paid": {
                        "$sum": {
                            "$cond": [
                                {"$eq": ["$entry_type", "PAYMENT_MADE"]},
                                "$amount",
                                0,
                            ]
                        }
                    },
                    "retention_held": {
                        "$sum": {
                            "$cond": [
                                {"$eq": ["$entry_type", "RETENTION_HELD"]},
                                "$amount",
                                0,
                            ]
                        }
                    },
                }
            },
        ]

        agg_results = await self.db.vendor_ledger.aggregate(pipeline).to_list(length=100)

        results = []
        for r in agg_results:
            vendor_id = r["_id"]
            vendor = None
            if vendor_id:
                vendor = await self.db.vendors.find_one({"_id": vendor_id})
                if not vendor and ObjectId.is_valid(str(vendor_id)):
                    vendor = await self.db.vendors.find_one({"_id": ObjectId(str(vendor_id))})

            certified = FinancialEngine.to_decimal(r["total_certified"])
            paid = FinancialEngine.to_decimal(r["total_paid"])
            outstanding = certified - paid

            results.append(
                {
                    "vendor_id": str(vendor_id),
                    "vendor_name": vendor.get("name", "Unknown Vendor")
                    if vendor
                    else "Unknown Vendor",
                    "total_certified": float(certified),
                    "total_paid": float(paid),
                    "outstanding": float(outstanding),
                    "retention_held": float(
                        FinancialEngine.to_decimal(r["retention_held"])
                    ),
                }
            )

        return results

    def invalidate_cache(self, project_id: str, organisation_id: str) -> None:
        """
        Manually invalidate dashboard cache (call on data updates).

        Args:
            project_id: Project identifier
            organisation_id: Organisation for scoping
        """
        cache_key = f"dashboard:{organisation_id}:{project_id}"
        self._cache.invalidate(cache_key)
        logger.debug(f"Dashboard cache invalidated for {project_id}")
