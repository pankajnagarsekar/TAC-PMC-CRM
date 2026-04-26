"""
Unit and integration tests for AI Summary Service.
Tests: summarize_*, stream_summary, generate_and_store, get_latest, refresh.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal

from app.modules.reporting.application.ai_summary_service import (
    AISummaryService,
    MockSummaryProvider,
    EmergentSummaryProvider,
)


@pytest.fixture
def mock_db():
    """Mock database client."""
    return MagicMock()


@pytest.fixture
def mock_permission_checker():
    """Mock permission checker."""
    checker = AsyncMock()
    checker.check_project_access = AsyncMock()
    return checker


@pytest.fixture
def mock_analytics_service():
    """Mock analytics service."""
    service = AsyncMock()
    return service


@pytest.fixture
def ai_summary_service(mock_db, mock_permission_checker, mock_analytics_service):
    """Create AISummaryService with mocks."""
    service = AISummaryService(
        mock_db, mock_permission_checker, mock_analytics_service
    )
    # Mock repositories
    service.ai_repo = AsyncMock()
    service.project_repo = AsyncMock()
    service.budget_repo = AsyncMock()
    service.fin_state_repo = AsyncMock()
    service.provider = MockSummaryProvider()
    return service


# --- MOCK PROVIDER TESTS ---


@pytest.mark.asyncio
async def test_mock_provider_schedule_summary():
    """Test MockSummaryProvider generates schedule summaries."""
    provider = MockSummaryProvider()
    report_data = {
        "status": "yellow",
        "on_track_tasks": 5,
        "at_risk_tasks": 2,
        "critical_path_days": 15,
    }
    summary = await provider.generate_summary(report_data, "Test Project")
    assert "Test Project" in summary
    assert "at risk" in summary or "on track" in summary
    assert "[MOCK]" in summary


@pytest.mark.asyncio
async def test_mock_provider_financial_summary():
    """Test MockSummaryProvider generates financial summaries."""
    provider = MockSummaryProvider()
    report_data = {
        "total_budget": 100000.0,
        "total_spent": 75000.0,
        "remaining_budget": 25000.0,
        "burn_rate_pct": 15.0,
    }
    summary = await provider.generate_summary(report_data, "Project Alpha")
    assert "Project Alpha" in summary
    assert "75" in summary  # Budget percentage
    assert "[MOCK]" in summary


@pytest.mark.asyncio
async def test_mock_provider_resource_summary():
    """Test MockSummaryProvider generates resource summaries."""
    provider = MockSummaryProvider()
    report_data = {
        "average_utilization_pct": 85.0,
        "over_allocated_count": 2,
        "total_resources": 10,
    }
    summary = await provider.generate_summary(report_data, "Project Beta")
    assert "Project Beta" in summary
    assert "85" in summary or "utilization" in summary
    assert "[MOCK]" in summary


# --- SUMMARIZE_SCHEDULE TESTS ---


@pytest.mark.asyncio
async def test_summarize_schedule_on_track(ai_summary_service):
    """Test schedule summary when project is on track."""
    metrics = MagicMock()
    metrics.to_dict.return_value = {
        "status": "green",
        "on_track_tasks": 8,
        "at_risk_tasks": 0,
        "critical_path_days": 30,
    }
    ai_summary_service.analytics_service.calculate_schedule_health.return_value = (
        metrics
    )

    summary = await ai_summary_service.summarize_schedule("proj-001", "org-001")
    assert "[MOCK]" in summary
    assert "on track" in summary.lower()


@pytest.mark.asyncio
async def test_summarize_schedule_at_risk(ai_summary_service):
    """Test schedule summary when project is at risk."""
    metrics = MagicMock()
    metrics.to_dict.return_value = {
        "status": "red",
        "on_track_tasks": 2,
        "at_risk_tasks": 5,
        "critical_path_days": 5,
    }
    ai_summary_service.analytics_service.calculate_schedule_health.return_value = (
        metrics
    )

    summary = await ai_summary_service.summarize_schedule("proj-001", "org-001")
    assert "[MOCK]" in summary
    assert "at risk" in summary.lower()


@pytest.mark.asyncio
async def test_summarize_schedule_no_analytics_service():
    """Test schedule summary when analytics service unavailable."""
    db = MagicMock()
    checker = AsyncMock()
    service = AISummaryService(db, checker, analytics_service=None)

    summary = await service.summarize_schedule("proj-001", "org-001")
    assert "not available" in summary.lower()


@pytest.mark.asyncio
async def test_summarize_schedule_error_handling(ai_summary_service):
    """Test schedule summary error handling."""
    ai_summary_service.analytics_service.calculate_schedule_health.side_effect = (
        Exception("DB error")
    )

    summary = await ai_summary_service.summarize_schedule("proj-001", "org-001")
    assert "Unable to generate" in summary


# --- SUMMARIZE_FINANCIALS TESTS ---


@pytest.mark.asyncio
async def test_summarize_financials_healthy(ai_summary_service):
    """Test financial summary when budget is healthy."""
    metrics = MagicMock()
    metrics.to_dict.return_value = {
        "total_budget": 100000.0,
        "total_spent": 40000.0,
        "remaining_budget": 60000.0,
        "burn_rate_pct": 10.0,
    }
    ai_summary_service.analytics_service.calculate_financial_summary.return_value = (
        metrics
    )

    summary = await ai_summary_service.summarize_financials("proj-001", "org-001")
    assert "[MOCK]" in summary
    assert "40" in summary or "consumed" in summary.lower()


@pytest.mark.asyncio
async def test_summarize_financials_overrun(ai_summary_service):
    """Test financial summary when over budget."""
    metrics = MagicMock()
    metrics.to_dict.return_value = {
        "total_budget": 100000.0,
        "total_spent": 110000.0,
        "remaining_budget": -10000.0,
        "burn_rate_pct": 15.0,
    }
    ai_summary_service.analytics_service.calculate_financial_summary.return_value = (
        metrics
    )

    summary = await ai_summary_service.summarize_financials("proj-001", "org-001")
    assert "[MOCK]" in summary
    assert "110" in summary or "consumed" in summary.lower()


@pytest.mark.asyncio
async def test_summarize_financials_error_handling(ai_summary_service):
    """Test financial summary error handling."""
    ai_summary_service.analytics_service.calculate_financial_summary.side_effect = (
        Exception("Calculation error")
    )

    summary = await ai_summary_service.summarize_financials("proj-001", "org-001")
    assert "Unable to generate" in summary


# --- SUMMARIZE_RESOURCES TESTS ---


@pytest.mark.asyncio
async def test_summarize_resources_balanced(ai_summary_service):
    """Test resource summary when team is well-balanced."""
    metrics = MagicMock()
    metrics.to_dict.return_value = {
        "average_utilization_pct": 75.0,
        "over_allocated_count": 0,
        "total_resources": 10,
    }
    ai_summary_service.analytics_service.calculate_resource_utilization.return_value = (
        metrics
    )

    summary = await ai_summary_service.summarize_resources("proj-001", "org-001")
    assert "[MOCK]" in summary
    assert "well-balanced" in summary.lower() or "75" in summary


@pytest.mark.asyncio
async def test_summarize_resources_overallocated(ai_summary_service):
    """Test resource summary when team is overallocated."""
    metrics = MagicMock()
    metrics.to_dict.return_value = {
        "average_utilization_pct": 110.0,
        "over_allocated_count": 5,
        "total_resources": 10,
    }
    ai_summary_service.analytics_service.calculate_resource_utilization.return_value = (
        metrics
    )

    summary = await ai_summary_service.summarize_resources("proj-001", "org-001")
    assert "[MOCK]" in summary
    assert "overallocated" in summary.lower() or "5" in summary


@pytest.mark.asyncio
async def test_summarize_resources_error_handling(ai_summary_service):
    """Test resource summary error handling."""
    ai_summary_service.analytics_service.calculate_resource_utilization.side_effect = (
        Exception("Repo error")
    )

    summary = await ai_summary_service.summarize_resources("proj-001", "org-001")
    assert "Unable to generate" in summary


# --- STREAM_SUMMARY TESTS ---


@pytest.mark.asyncio
async def test_stream_summary_schedule(ai_summary_service):
    """Test streaming schedule summary word-by-word."""
    metrics = MagicMock()
    metrics.to_dict.return_value = {
        "status": "green",
        "on_track_tasks": 8,
        "at_risk_tasks": 0,
        "critical_path_days": 30,
    }
    ai_summary_service.analytics_service.calculate_schedule_health.return_value = (
        metrics
    )

    chunks = []
    async for chunk in ai_summary_service.stream_summary(
        "schedule", "proj-001", "org-001"
    ):
        chunks.append(chunk)

    full_text = "".join(chunks)
    assert "[MOCK]" in full_text or "green" in full_text.lower()


@pytest.mark.asyncio
async def test_stream_summary_financial(ai_summary_service):
    """Test streaming financial summary."""
    metrics = MagicMock()
    metrics.to_dict.return_value = {
        "total_budget": 100000.0,
        "total_spent": 80000.0,
        "remaining_budget": 20000.0,
        "burn_rate_pct": 12.0,
    }
    ai_summary_service.analytics_service.calculate_financial_summary.return_value = (
        metrics
    )

    chunks = []
    async for chunk in ai_summary_service.stream_summary(
        "financial", "proj-001", "org-001"
    ):
        chunks.append(chunk)

    full_text = "".join(chunks)
    assert "[MOCK]" in full_text or len(full_text) > 0


@pytest.mark.asyncio
async def test_stream_summary_resources(ai_summary_service):
    """Test streaming resource summary."""
    metrics = MagicMock()
    metrics.to_dict.return_value = {
        "average_utilization_pct": 85.0,
        "over_allocated_count": 1,
        "total_resources": 10,
    }
    ai_summary_service.analytics_service.calculate_resource_utilization.return_value = (
        metrics
    )

    chunks = []
    async for chunk in ai_summary_service.stream_summary(
        "resources", "proj-001", "org-001"
    ):
        chunks.append(chunk)

    full_text = "".join(chunks)
    assert "[MOCK]" in full_text or len(full_text) > 0


@pytest.mark.asyncio
async def test_stream_summary_invalid_type(ai_summary_service):
    """Test stream_summary with invalid type."""
    chunks = []
    async for chunk in ai_summary_service.stream_summary(
        "invalid_type", "proj-001", "org-001"
    ):
        chunks.append(chunk)

    full_text = "".join(chunks)
    assert "Unknown" in full_text


@pytest.mark.asyncio
async def test_stream_summary_no_analytics_service():
    """Test stream_summary when analytics service unavailable."""
    db = MagicMock()
    checker = AsyncMock()
    service = AISummaryService(db, checker, analytics_service=None)

    chunks = []
    async for chunk in service.stream_summary("schedule", "proj-001", "org-001"):
        chunks.append(chunk)

    full_text = "".join(chunks)
    assert "not available" in full_text.lower()


# --- GENERATE_AND_STORE TESTS ---


@pytest.mark.asyncio
async def test_generate_and_store_creates_document(ai_summary_service):
    """Test generate_and_store creates and stores summary document."""
    # Mock _aggregate_report_data to avoid DB calls
    ai_summary_service._aggregate_report_data = AsyncMock(
        return_value={
            "total_budget": 100000.0,
            "total_committed": 50000.0,
            "total_remaining": 50000.0,
            "wo_open": 5,
            "pc_closed": 3,
            "over_budget_categories": [],
        }
    )

    ai_summary_service.project_repo.find_one.return_value = {
        "_id": "proj-001",
        "project_name": "Test Project",
        "organisation_id": "org-001",
    }

    stored_doc = {
        "_id": "doc-001",
        "project_id": "proj-001",
        "organisation_id": "org-001",
        "summary_text": "[MOCK] Test Project at 50.0% budget commitment.",
        "created_at": datetime.now(timezone.utc),
    }
    ai_summary_service.ai_repo.create.return_value = stored_doc

    result = await ai_summary_service.generate_and_store(
        "proj-001", "org-001", "manual"
    )

    assert result["project_id"] == "proj-001"
    ai_summary_service.ai_repo.create.assert_called_once()


# --- GET_LATEST TESTS ---


@pytest.mark.asyncio
async def test_get_latest_returns_existing_summary(ai_summary_service):
    """Test get_latest returns most recent summary."""
    existing_summary = {
        "_id": "doc-001",
        "project_id": "proj-001",
        "summary_text": "Previous summary",
        "created_at": datetime.now(timezone.utc),
    }
    ai_summary_service.ai_repo.find_one.return_value = existing_summary

    user = {"user_id": "usr-001", "organisation_id": "org-001"}
    result = await ai_summary_service.get_latest(user, "proj-001")

    assert result["summary_text"] == "Previous summary"


@pytest.mark.asyncio
async def test_get_latest_refreshes_if_none_exist(ai_summary_service):
    """Test get_latest generates new summary if none exist."""
    ai_summary_service.ai_repo.find_one.return_value = None

    # Mock _aggregate_report_data to avoid DB calls
    ai_summary_service._aggregate_report_data = AsyncMock(
        return_value={
            "total_budget": 100000.0,
            "total_committed": 50000.0,
            "total_remaining": 50000.0,
            "wo_open": 5,
            "pc_closed": 3,
            "over_budget_categories": [],
        }
    )

    ai_summary_service.project_repo.find_one.return_value = {
        "_id": "proj-001",
        "project_name": "Test Project",
        "organisation_id": "org-001",
    }

    new_summary = {
        "_id": "doc-002",
        "project_id": "proj-001",
        "summary_text": "New summary",
        "created_at": datetime.now(timezone.utc),
    }
    ai_summary_service.ai_repo.create.return_value = new_summary

    user = {"user_id": "usr-001", "organisation_id": "org-001"}
    result = await ai_summary_service.get_latest(user, "proj-001")

    assert result["summary_text"] == "New summary"


# --- REFRESH_SUMMARY TESTS ---


@pytest.mark.asyncio
async def test_refresh_summary_generates_new(ai_summary_service):
    """Test refresh_summary generates fresh summary."""
    # Mock _aggregate_report_data to avoid DB calls
    ai_summary_service._aggregate_report_data = AsyncMock(
        return_value={
            "total_budget": 100000.0,
            "total_committed": 75000.0,
            "total_remaining": 25000.0,
            "wo_open": 5,
            "pc_closed": 3,
            "over_budget_categories": [],
        }
    )

    ai_summary_service.project_repo.find_one.return_value = {
        "_id": "proj-001",
        "project_name": "Test Project",
        "organisation_id": "org-001",
    }

    new_summary = {
        "_id": "doc-003",
        "project_id": "proj-001",
        "summary_text": "Refreshed summary",
        "created_at": datetime.now(timezone.utc),
    }
    ai_summary_service.ai_repo.create.return_value = new_summary

    user = {"user_id": "usr-001", "organisation_id": "org-001"}
    result = await ai_summary_service.refresh_summary(user, "proj-001")

    assert result["summary_text"] == "Refreshed summary"
    ai_summary_service.ai_repo.create.assert_called_once()
