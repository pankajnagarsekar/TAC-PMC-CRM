"""
Dashboard Service - Aggregates analytics into unified dashboard response.
Provides 30-second caching for performance optimization.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

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
    _cache = DashboardCache(ttl_seconds=30)

    def __init__(self, db, analytics_service: AnalyticsService):
        self.db = db
        self.analytics_service = analytics_service
        self.project_repo = ProjectRepository(db)

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
