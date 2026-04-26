"""
Integration tests for DashboardService.
Tests aggregation, caching, and error handling.
"""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.modules.reporting.application.analytics_service import AnalyticsService
from app.modules.reporting.application.dashboard_service import (
    DashboardService,
    DashboardCache,
)
from app.modules.reporting.domain.metrics import ProjectDashboardData
from app.modules.project.infrastructure.repository import (
    ProjectRepository,
    ScheduleRepository,
)


@pytest.mark.asyncio
class TestDashboardService:
    """Integration tests for DashboardService."""

    @pytest.fixture
    async def analytics_service(self, test_db):
        """Create AnalyticsService instance."""
        return AnalyticsService(test_db)

    @pytest.fixture
    async def dashboard_service(self, test_db, analytics_service):
        """Create DashboardService instance."""
        return DashboardService(test_db, analytics_service)

    @pytest.fixture
    async def project_with_schedule(self, test_db, test_project_id, test_org_id):
        """Create a test project with schedule."""
        project_repo = ProjectRepository(test_db)
        schedule_repo = ScheduleRepository(test_db)

        # Create project
        project = {
            "project_id": test_project_id,
            "organisation_id": test_org_id,
            "project_name": "Test Project",
            "description": "Test",
            "created_at": datetime.now(timezone.utc),
        }
        await test_db.projects.insert_one(project)

        # Create schedule with tasks
        schedule = {
            "project_id": test_project_id,
            "organisation_id": test_org_id,
            "tasks": [
                {
                    "task_id": "task-1",
                    "name": "Task 1",
                    "duration": 5,
                    "start": datetime.now(timezone.utc).isoformat(),
                    "finish": (
                        datetime.now(timezone.utc) + asyncio.sleep.__self__.timedelta(days=5)
                    ).isoformat()
                    if hasattr(asyncio.sleep, "__self__")
                    else datetime(2026, 5, 1).isoformat(),
                    "assigned_to_name": "John",
                    "assigned_role": "MEP",
                    "slack": 10,
                    "is_critical": False,
                }
            ],
        }
        await test_db.schedules.insert_one(schedule)

        # Create financial state
        fin_state = {
            "project_id": test_project_id,
            "organisation_id": test_org_id,
            "code_id": None,
            "original_budget": 100000.0,
            "committed_value": 50000.0,
        }
        await test_db.financial_state.insert_one(fin_state)

        return project

    async def test_get_project_dashboard_full_aggregation(
        self, test_db, dashboard_service, project_with_schedule, test_org_id
    ):
        """Test that dashboard aggregates all 4 metrics correctly."""
        project_id = project_with_schedule["project_id"]
        organisation_id = test_org_id

        dashboard = await dashboard_service.get_project_dashboard(
            project_id, organisation_id
        )

        # Verify structure
        assert isinstance(dashboard, ProjectDashboardData)
        assert dashboard.project_id == project_id
        assert dashboard.project_name is not None

        # Verify all 4 metrics are present
        assert dashboard.schedule is not None
        assert dashboard.schedule.status in ["green", "yellow", "red"]
        assert dashboard.schedule.days_remaining >= 0

        assert dashboard.resources is not None
        assert isinstance(dashboard.resources.by_resource, dict)
        assert isinstance(dashboard.resources.by_role, dict)

        assert dashboard.financial is not None
        assert dashboard.financial.budget_total >= 0
        assert dashboard.financial.budget_spent >= 0

        assert dashboard.timeline is not None
        assert isinstance(dashboard.timeline.daily_completion, list)

        # Verify updated_at is present and recent
        assert dashboard.updated_at is not None
        assert "Z" in dashboard.updated_at or "+" in dashboard.updated_at

    async def test_get_project_dashboard_cache_hit(
        self, test_db, dashboard_service, project_with_schedule, test_org_id
    ):
        """Test that cache returns same object within TTL."""
        project_id = project_with_schedule["project_id"]
        organisation_id = test_org_id

        # First call (cache miss)
        dashboard1 = await dashboard_service.get_project_dashboard(
            project_id, organisation_id
        )

        # Second call immediately (cache hit)
        dashboard2 = await dashboard_service.get_project_dashboard(
            project_id, organisation_id
        )

        # Should be same timestamp (cached)
        assert dashboard1.updated_at == dashboard2.updated_at

    async def test_get_project_dashboard_cache_expiration(
        self, test_db, dashboard_service, project_with_schedule, test_org_id
    ):
        """Test that cache expires after TTL."""
        project_id = project_with_schedule["project_id"]
        organisation_id = test_org_id

        # Create service with 1-second TTL
        analytics = dashboard_service.analytics_service
        fast_cache_service = DashboardService(test_db, analytics)
        fast_cache_service._cache = DashboardCache(ttl_seconds=1)

        # First call
        dashboard1 = await fast_cache_service.get_project_dashboard(
            project_id, organisation_id
        )

        # Wait for cache to expire
        await asyncio.sleep(1.1)

        # Second call (cache miss, recalculated)
        dashboard2 = await fast_cache_service.get_project_dashboard(
            project_id, organisation_id
        )

        # Timestamps should be different (recalculated)
        assert dashboard1.updated_at != dashboard2.updated_at

    async def test_get_project_dashboard_manual_cache_invalidation(
        self, test_db, dashboard_service, project_with_schedule, test_org_id
    ):
        """Test that manual cache invalidation forces recalculation."""
        project_id = project_with_schedule["project_id"]
        organisation_id = test_org_id

        # First call
        dashboard1 = await dashboard_service.get_project_dashboard(
            project_id, organisation_id
        )

        # Invalidate cache manually
        dashboard_service.invalidate_cache(project_id, organisation_id)

        # Small delay to ensure different timestamp
        await asyncio.sleep(0.01)

        # Second call (cache miss)
        dashboard2 = await dashboard_service.get_project_dashboard(
            project_id, organisation_id
        )

        # Timestamps should be different
        assert dashboard1.updated_at != dashboard2.updated_at

    async def test_get_project_dashboard_empty_project(
        self, test_db, analytics_service, test_project_id, test_org_id
    ):
        """Test dashboard with project that has no schedule or financial state."""
        # Create fresh service (avoid cache pollution)
        fresh_service = DashboardService(test_db, analytics_service)

        # Create minimal project with unique ID
        unique_id = f"{test_project_id}-empty-proj"
        await test_db.projects.insert_one(
            {
                "project_id": unique_id,
                "organisation_id": test_org_id,
                "project_name": "Minimal Empty",
            }
        )

        dashboard = await fresh_service.get_project_dashboard(unique_id, test_org_id)

        # Should still return valid dashboard with zero metrics
        assert dashboard.project_id == unique_id
        assert dashboard.schedule.days_remaining == 0
        assert dashboard.schedule.status == "green"
        # Empty project has no financial state, so budget should be 0
        assert dashboard.financial.budget_total == 0

    async def test_get_project_dashboard_project_not_found(
        self, dashboard_service, test_org_id
    ):
        """Test that non-existent project raises NotFoundError."""
        from app.modules.shared.domain.exceptions import NotFoundError

        with pytest.raises(NotFoundError):
            await dashboard_service.get_project_dashboard(
                "nonexistent-project-id", test_org_id
            )


class TestDashboardCache:
    """Unit tests for DashboardCache."""

    def test_cache_set_and_get(self):
        """Test basic set/get operations."""
        cache = DashboardCache(ttl_seconds=60)

        cache.set("key1", {"value": "data"})
        result = cache.get("key1")

        assert result == {"value": "data"}

    def test_cache_get_nonexistent_key(self):
        """Test getting non-existent key returns None."""
        cache = DashboardCache(ttl_seconds=60)

        result = cache.get("nonexistent")

        assert result is None

    def test_cache_invalidate(self):
        """Test manual invalidation removes key."""
        cache = DashboardCache(ttl_seconds=60)

        cache.set("key1", {"value": "data"})
        cache.invalidate("key1")
        result = cache.get("key1")

        assert result is None

    def test_cache_ttl_expiration(self):
        """Test that expired entries are removed on get."""
        import time

        cache = DashboardCache(ttl_seconds=1)

        cache.set("key1", {"value": "data"})
        time.sleep(1.1)
        result = cache.get("key1")

        assert result is None
