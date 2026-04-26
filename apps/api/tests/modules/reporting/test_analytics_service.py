"""
Unit tests for Analytics Service metric calculations.
Tests schedule health, resource utilization, financial summary, and timeline analytics.
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from app.modules.reporting.application.analytics_service import (
    AnalyticsService,
    ScheduleHealthMetrics,
    ResourceUtilizationData,
    FinancialSummaryData,
    TimelineAnalytics,
)


@pytest.fixture
def mock_db():
    """Mock database client."""
    return MagicMock()


@pytest.fixture
def analytics_service(mock_db):
    """Create AnalyticsService with mocked repositories."""
    service = AnalyticsService(mock_db)
    # Mock all repositories
    service.project_repo = AsyncMock()
    service.schedule_repo = AsyncMock()
    service.budget_repo = AsyncMock()
    service.fin_state_repo = AsyncMock()
    return service


@pytest.mark.asyncio
async def test_calculate_schedule_health_green_status(analytics_service):
    """Test schedule health returns GREEN when no tasks at risk and days remaining > 20%."""
    # Setup
    now = datetime.now(timezone.utc)
    finish_date = now + timedelta(days=100)

    schedule = {
        "project_id": "proj-001",
        "tasks": [
            {
                "task_id": "t1",
                "name": "Task 1",
                "duration": 50,
                "finish": finish_date,
                "slack": 50,  # NOT at risk
                "is_critical": False,
            },
            {
                "task_id": "t2",
                "name": "Task 2",
                "duration": 30,
                "finish": finish_date - timedelta(days=10),
                "slack": 30,
                "is_critical": False,
            },
        ],
    }

    analytics_service.schedule_repo.find_one.return_value = schedule

    # Execute
    metrics = await analytics_service.calculate_schedule_health("proj-001", "org-001")

    # Assert
    assert isinstance(metrics, ScheduleHealthMetrics)
    assert metrics.status == "green"
    assert metrics.tasks_at_risk == 0
    assert metrics.days_remaining > 0


@pytest.mark.asyncio
async def test_calculate_schedule_health_red_status_many_at_risk(analytics_service):
    """Test schedule health returns RED when > 3 tasks at risk."""
    now = datetime.now(timezone.utc)
    finish_date = now + timedelta(days=5)  # Very soon

    schedule = {
        "project_id": "proj-001",
        "tasks": [
            {
                "task_id": f"t{i}",
                "name": f"Task {i}",
                "duration": 10,
                "finish": finish_date,
                "slack": 2,  # AT RISK (< 5 days)
                "is_critical": False,
            }
            for i in range(5)  # 5 tasks at risk
        ],
    }

    analytics_service.schedule_repo.find_one.return_value = schedule

    # Execute
    metrics = await analytics_service.calculate_schedule_health("proj-001", "org-001")

    # Assert
    assert metrics.status == "red"
    assert metrics.tasks_at_risk == 5


@pytest.mark.asyncio
async def test_calculate_schedule_health_empty_schedule(analytics_service):
    """Test schedule health with no schedule returns default metrics."""
    analytics_service.schedule_repo.find_one.return_value = None

    # Execute
    metrics = await analytics_service.calculate_schedule_health("proj-001", "org-001")

    # Assert
    assert metrics.days_remaining == 0
    assert metrics.tasks_at_risk == 0
    assert metrics.status == "green"


@pytest.mark.asyncio
async def test_calculate_resource_utilization_no_overallocation(analytics_service):
    """Test resource utilization when all resources are within capacity."""
    schedule = {
        "project_id": "proj-001",
        "tasks": [
            {
                "task_id": "t1",
                "assigned_to_name": "John Doe",
                "assigned_role": "MEP",
                "duration": 30,  # 30 hours
            },
            {
                "task_id": "t2",
                "assigned_to_name": "Jane Smith",
                "assigned_role": "MEP",
                "duration": 25,  # 25 hours
            },
        ],
    }

    analytics_service.schedule_repo.find_one.return_value = schedule

    # Execute
    data = await analytics_service.calculate_resource_utilization(
        "proj-001", "org-001"
    )

    # Assert
    assert isinstance(data, ResourceUtilizationData)
    assert len(data.by_resource) == 2
    assert len(data.over_allocated) == 0
    assert "John Doe" in data.by_resource
    assert "Jane Smith" in data.by_resource


@pytest.mark.asyncio
async def test_calculate_resource_utilization_overallocated(analytics_service):
    """Test resource utilization detects over-allocated resources."""
    schedule = {
        "project_id": "proj-001",
        "tasks": [
            {
                "task_id": f"t{i}",
                "assigned_to_name": "John Doe",
                "assigned_role": "MEP",
                "duration": 50,  # Each task 50 hours
            }
            for i in range(3)  # 150 hours total (way over 40 hrs/week)
        ],
    }

    analytics_service.schedule_repo.find_one.return_value = schedule

    # Execute
    data = await analytics_service.calculate_resource_utilization(
        "proj-001", "org-001"
    )

    # Assert
    assert len(data.over_allocated) == 1
    assert "John Doe" in data.over_allocated
    assert data.by_resource["John Doe"].is_over_allocated


@pytest.mark.asyncio
async def test_calculate_resource_utilization_empty_schedule(analytics_service):
    """Test resource utilization with no schedule returns empty data."""
    analytics_service.schedule_repo.find_one.return_value = None

    # Execute
    data = await analytics_service.calculate_resource_utilization(
        "proj-001", "org-001"
    )

    # Assert
    assert len(data.by_resource) == 0
    assert len(data.by_role) == 0
    assert len(data.over_allocated) == 0


@pytest.mark.asyncio
async def test_calculate_financial_summary_under_budget(analytics_service):
    """Test financial summary when budget is not exceeded."""
    master_state = {
        "project_id": "proj-001",
        "original_budget": 500000.0,
        "committed_value": 350000.0,
    }

    analytics_service.fin_state_repo.find_one.return_value = master_state
    analytics_service.project_repo.get_by_id.return_value = {
        "project_id": "proj-001",
        "created_at": datetime.now(timezone.utc) - timedelta(days=30),
    }

    # Execute
    data = await analytics_service.calculate_financial_summary("proj-001", "org-001")

    # Assert
    assert isinstance(data, FinancialSummaryData)
    assert data.budget_total == Decimal("500000.0")
    assert data.budget_spent == Decimal("350000.0")
    assert data.budget_remaining == Decimal("150000.0")
    assert data.is_over_budget is False
    assert data.budget_utilization_pct == Decimal("70")


@pytest.mark.asyncio
async def test_calculate_financial_summary_over_budget(analytics_service):
    """Test financial summary when budget is exceeded."""
    master_state = {
        "project_id": "proj-001",
        "original_budget": 500000.0,
        "committed_value": 550000.0,
    }

    analytics_service.fin_state_repo.find_one.return_value = master_state
    analytics_service.project_repo.get_by_id.return_value = {
        "project_id": "proj-001",
        "created_at": datetime.now(timezone.utc) - timedelta(days=30),
    }

    # Execute
    data = await analytics_service.calculate_financial_summary("proj-001", "org-001")

    # Assert
    assert data.is_over_budget is True
    assert data.budget_spent > data.budget_total
    assert data.projected_overrun > 0


@pytest.mark.asyncio
async def test_calculate_financial_summary_fallback_aggregation(analytics_service):
    """Test financial summary falls back to aggregation when master state missing."""
    # No master state
    analytics_service.fin_state_repo.find_one.return_value = None

    # Aggregation result
    agg_result = {
        "budget": 500000.0,
        "spent": 300000.0,
    }

    def mock_agg(*args, **kwargs):
        mock_cursor = AsyncMock()
        mock_cursor.to_list = AsyncMock(return_value=[agg_result])
        return mock_cursor

    analytics_service.fin_state_repo.aggregate = mock_agg

    analytics_service.project_repo.get_by_id.return_value = {
        "project_id": "proj-001",
        "created_at": datetime.now(timezone.utc) - timedelta(days=30),
    }

    # Execute
    data = await analytics_service.calculate_financial_summary("proj-001", "org-001")

    # Assert
    assert data.budget_total == Decimal("500000.0")
    assert data.budget_spent == Decimal("300000.0")


@pytest.mark.asyncio
async def test_calculate_timeline_analytics_daily_trend(analytics_service):
    """Test timeline analytics generates daily buckets for date range."""
    start_date = datetime(2026, 4, 10, tzinfo=timezone.utc)
    end_date = datetime(2026, 4, 15, tzinfo=timezone.utc)

    # Execute
    analytics = await analytics_service.calculate_timeline_analytics(
        "proj-001", "org-001", start_date=start_date, end_date=end_date
    )

    # Assert
    assert isinstance(analytics, TimelineAnalytics)
    assert len(analytics.daily_completion) == 6  # 6 days inclusive
    assert len(analytics.utilization_trend) == 6
    assert len(analytics.budget_spent_trend) == 6

    # Check first and last dates
    assert "2026-04-10" in analytics.daily_completion[0].date
    assert "2026-04-15" in analytics.daily_completion[-1].date


@pytest.mark.asyncio
async def test_empty_project_returns_zero_metrics(analytics_service):
    """Test metrics for empty project return valid zero/default values."""
    # Empty schedule
    analytics_service.schedule_repo.find_one.return_value = {"project_id": "proj-001", "tasks": []}

    # No financial state
    analytics_service.fin_state_repo.find_one.return_value = None
    mock_cursor = AsyncMock()
    mock_cursor.to_list = AsyncMock(return_value=[])
    analytics_service.fin_state_repo.aggregate = MagicMock(return_value=mock_cursor)

    # Mock project repo
    analytics_service.project_repo.get_by_id.return_value = {
        "project_id": "proj-001",
        "created_at": datetime.now(timezone.utc) - timedelta(days=10)
    }

    # Execute all metrics
    schedule_health = await analytics_service.calculate_schedule_health("proj-001", "org-001")
    resource_util = await analytics_service.calculate_resource_utilization("proj-001", "org-001")
    financial = await analytics_service.calculate_financial_summary("proj-001", "org-001")
    timeline = await analytics_service.calculate_timeline_analytics("proj-001", "org-001")

    # Assert
    assert schedule_health.days_remaining == 0
    assert schedule_health.tasks_at_risk == 0

    assert len(resource_util.by_resource) == 0
    assert len(resource_util.over_allocated) == 0

    assert financial.budget_total == Decimal("0")
    assert financial.budget_spent == Decimal("0")

    assert len(timeline.daily_completion) > 0  # Has date buckets


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
