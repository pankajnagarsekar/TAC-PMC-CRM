import pytest
from datetime import datetime, timezone
from decimal import Decimal
from httpx import AsyncClient
from app.modules.reporting.application.analytics_service import AnalyticsService
from app.modules.project.schemas.dto import EVMBaselineInitDTO, MonthlyPlannedValueDTO

# ──────────────────────────────────────────────────────────────────────────
# 1. ANALYTICS ENGINE UNIT TESTS: S-Curve PV calculations
# ──────────────────────────────────────────────────────────────────────────

def test_calculate_s_curve_pv_basic():
    """Verify S-curve planned value calculation with prior, current, and future months."""
    baseline = {
        "total_contract_value": 300000.0,
        "monthly_planned_values": [
            {"month": "2026-04", "planned_value": 100000.0, "cumulative_value": 100000.0},
            {"month": "2026-05", "planned_value": 100000.0, "cumulative_value": 200000.0},
            {"month": "2026-06", "planned_value": 100000.0, "cumulative_value": 300000.0},
        ]
    }

    # Test case: Today is in middle of May (May 15th, 2026)
    # May has 31 days. May 15 should be prorated: (15 / 31) * 100000 = 48387.10
    # April is fully completed: 100000
    # June is future: 0
    today = datetime(2026, 5, 15)
    pv = AnalyticsService.calculate_s_curve_pv(baseline, today)
    
    # Expected: 100000 + (15 / 31) * 100000 = 148387.0967...
    assert abs(pv - 148387.10) < 0.01

def test_calculate_s_curve_pv_first_day():
    """Verify S-curve proration on the first day of the month."""
    baseline = {
        "total_contract_value": 300000.0,
        "monthly_planned_values": [
            {"month": "2026-04", "planned_value": 100000.0, "cumulative_value": 100000.0},
            {"month": "2026-05", "planned_value": 100000.0, "cumulative_value": 200000.0},
        ]
    }
    today = datetime(2026, 5, 1)
    pv = AnalyticsService.calculate_s_curve_pv(baseline, today)
    
    # Expected: 100000 + (1 / 31) * 100000 = 103225.806...
    assert abs(pv - 103225.81) < 0.01

def test_calculate_s_curve_pv_last_day():
    """Verify S-curve proration on the last day of the month."""
    baseline = {
        "total_contract_value": 300000.0,
        "monthly_planned_values": [
            {"month": "2026-04", "planned_value": 100000.0, "cumulative_value": 100000.0},
            {"month": "2026-05", "planned_value": 100000.0, "cumulative_value": 200000.0},
        ]
    }
    today = datetime(2026, 5, 31)
    pv = AnalyticsService.calculate_s_curve_pv(baseline, today)
    
    # Expected: 100000 + (31 / 31) * 100000 = 200000.0
    assert abs(pv - 200000.0) < 0.01

def test_calculate_s_curve_pv_empty():
    """Verify S-curve PV calculations handle empty data gracefully."""
    pv = AnalyticsService.calculate_s_curve_pv(None, datetime.now())
    assert pv == 0.0
    
    pv_empty = AnalyticsService.calculate_s_curve_pv({}, datetime.now())
    assert pv_empty == 0.0


# ──────────────────────────────────────────────────────────────────────────
# 2. END-TO-END API ROUTE & SERVICES TESTS
# ──────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_evm_baseline_endpoints_e2e(client, test_db):
    """Verify EVM baseline initialization and retrieval API endpoints."""
    # 1. Create a test project document first
    project_payload = {
        "project_name": "EVM Test Project",
        "client_id": "test-client-id",
        "project_code": "EVM-TEST-001",
        "status": "active",
        "project_retention_percentage": 5.0,
        "project_cgst_percentage": 9.0,
        "project_sgst_percentage": 9.0,
        "completion_percentage": 0.0,
        "threshold_petty": 10000.0,
        "threshold_ovh": 0.0,
        "start_date": "2026-05-01T00:00:00Z",
        "end_date": "2026-07-31T00:00:00Z"
    }
    
    # We must post the new project
    proj_resp = await client.post("/api/v1/projects/", json=project_payload)
    assert proj_resp.status_code == 201
    project_data = proj_resp.json()["data"]
    project_id = project_data["project_id"]
    assert project_data["is_baseline_initialized"] is False
    assert project_data["evm_baseline"] is None

    # 2. Initialize EVM Baseline via POST /projects/{project_id}/evm-baseline
    baseline_payload = {
        "total_contract_value": 300000.00,
        "start_date": "2026-05-01T00:00:00Z",
        "end_date": "2026-07-31T00:00:00Z",
        "curve_type": "linear",
        "monthly_planned_values": [
            {"month": "2026-05", "planned_value": 100000.00, "cumulative_value": 100000.00},
            {"month": "2026-06", "planned_value": 100000.00, "cumulative_value": 200000.00},
            {"month": "2026-07", "planned_value": 100000.00, "cumulative_value": 300000.00}
        ]
    }
    
    init_resp = await client.post(
        f"/api/v1/projects/{project_id}/evm-baseline",
        json=baseline_payload
    )
    assert init_resp.status_code == 200
    init_data = init_resp.json()["data"]
    assert init_data["is_baseline_initialized"] is True
    assert init_data["evm_baseline"] is not None
    assert float(init_data["evm_baseline"]["total_contract_value"]) == 300000.0

    # Verify audit log entry is written for baseline initialization
    db_proj = await test_db.projects.find_one({"project_id": project_id})
    db_id = str(db_proj["_id"])
    
    audit_logs = await test_db.audit_logs.find_one({
        "organisation_id": "test-org-123",
        "module_name": "PROJECT_MANAGEMENT",
        "action_type": "INITIALIZE_BASELINE",
        "entity_id": db_id
    })
    assert audit_logs is not None

    # 3. Retrieve EVM Baseline via GET /projects/{project_id}/evm-baseline
    get_resp = await client.get(f"/api/v1/projects/{project_id}/evm-baseline")
    assert get_resp.status_code == 200
    baseline_details = get_resp.json()["data"]
    assert baseline_details is not None
    assert baseline_details["curve_type"] == "linear"
    assert len(baseline_details["monthly_planned_values"]) == 3
    assert float(baseline_details["monthly_planned_values"][1]["planned_value"]) == 100000.0


@pytest.mark.asyncio
async def test_evm_baseline_validation_failures(client, test_db):
    """Verify input validation gates for baseline initialization."""
    # Create test project
    project_payload = {
        "project_name": "Validation Fail Project",
        "status": "active"
    }
    proj_resp = await client.post("/api/v1/projects/", json=project_payload)
    project_id = proj_resp.json()["data"]["project_id"]

    # Test Case A: Negative contract value
    bad_payload_a = {
        "total_contract_value": -100.0,
        "start_date": "2026-05-01T00:00:00Z",
        "end_date": "2026-07-31T00:00:00Z",
        "curve_type": "linear",
        "monthly_planned_values": []
    }
    resp_a = await client.post(
        f"/api/v1/projects/{project_id}/evm-baseline",
        json=bad_payload_a
    )
    assert resp_a.status_code == 422

    # Test Case B: End date before start date
    bad_payload_b = {
        "total_contract_value": 100000.0,
        "start_date": "2026-05-01T00:00:00Z",
        "end_date": "2026-04-01T00:00:00Z",
        "curve_type": "linear",
        "monthly_planned_values": []
    }
    resp_b = await client.post(
        f"/api/v1/projects/{project_id}/evm-baseline",
        json=bad_payload_b
    )
    assert resp_b.status_code == 422
    assert "Project End Date must be after Start Date" in resp_b.json()["error"]["message"]
