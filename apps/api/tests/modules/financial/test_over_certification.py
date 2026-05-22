import pytest
from bson import ObjectId
from app.modules.shared.domain.financial_engine import FinancialEngine


@pytest.mark.asyncio
async def test_get_wo_certification_summary_empty(client, test_db, test_user):
    """Returns 0 when no PCs exist for a Work Order."""
    # Setup a Work Order
    wo_id = str(ObjectId())
    await test_db.work_orders.insert_one({
        "_id": ObjectId(wo_id),
        "organisation_id": test_user["organisation_id"],
        "grand_total": FinancialEngine.to_d128(10000),
        "active_status": True
    })

    response = await client.get(f"/api/v1/payments/wo-summary/{wo_id}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["previously_certified"] == 0
    assert data["wo_grand_total"] == 10000
    assert data["balance_remaining"] == 10000
    assert data["pc_count"] == 0


@pytest.mark.asyncio
async def test_get_wo_certification_summary_aggregates(client, test_db, test_user):
    """Correctly sums non-cancelled PCs against a Work Order."""
    wo_id = str(ObjectId())
    await test_db.work_orders.insert_one({
        "_id": ObjectId(wo_id),
        "organisation_id": test_user["organisation_id"],
        "grand_total": FinancialEngine.to_d128(10000),
        "active_status": True
    })

    # Insert two valid PCs
    await test_db.payment_certificates.insert_many([
        {
            "work_order_id": wo_id,
            "organisation_id": test_user["organisation_id"],
            "grand_total": FinancialEngine.to_d128(2000),
            "status": "Paid"
        },
        {
            "work_order_id": wo_id,
            "organisation_id": test_user["organisation_id"],
            "grand_total": FinancialEngine.to_d128(3000),
            "status": "Approved"
        }
    ])

    # Insert one cancelled PC (should be ignored)
    await test_db.payment_certificates.insert_one({
        "work_order_id": wo_id,
        "organisation_id": test_user["organisation_id"],
        "grand_total": FinancialEngine.to_d128(5000),
        "status": "Cancelled"
    })

    response = await client.get(f"/api/v1/payments/wo-summary/{wo_id}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["previously_certified"] == 5000
    assert data["balance_remaining"] == 5000
    assert data["pc_count"] == 2


@pytest.mark.asyncio
async def test_create_pc_blocks_over_certification(client, test_db, test_user, test_project_id):
    """Raises ValidationError when PC would exceed WO authorized total."""
    # Setup Vendor
    v_id = str(ObjectId())
    await test_db.vendors.insert_one({
        "_id": ObjectId(v_id),
        "organisation_id": test_user["organisation_id"],
        "name": "Test Vendor"
    })

    # Setup WO with 5000 total
    wo_id = str(ObjectId())
    c_id = "CIVIL_1"
    await test_db.work_orders.insert_one({
        "_id": ObjectId(wo_id),
        "organisation_id": test_user["organisation_id"],
        "project_id": test_project_id,
        "vendor_id": v_id,
        "category_id": c_id,
        "grand_total": FinancialEngine.to_d128(5000),
        "active_status": True
    })

    await test_db.code_master.insert_one({
        "organisation_id": test_user["organisation_id"],
        "code": c_id,
        "budget_type": "commitment",
        "active_status": True
    })
    await test_db.fund_allocations.insert_one({
        "organisation_id": test_user["organisation_id"],
        "project_id": test_project_id,
        "category_id": c_id,
        "allocation_remaining": FinancialEngine.to_d128(10000)
    })

    pc_data = {
        "project_id": test_project_id,
        "work_order_id": wo_id,
        "vendor_id": v_id,
        "category_id": c_id,
        "line_items": [{"sr_no": 1, "scope_of_work": "Test", "qty": 1, "rate": 5000}],
        "idempotency_key": "test-over-cert"
    }

    # Note: FinancialEngine.calculate_pc_financials will add GST (usually 18% default in some setups, but let's check)
    # If it adds 18% GST, grand_total will be 5900, which exceeds 5000.

    response = await client.post("/api/v1/payments", json=pc_data)
    if response.status_code != 422:
        print(f"DEBUG: Status {response.status_code}, Body: {response.text}")
    assert response.status_code == 422
    err_msg = response.json()["error"]["message"]
    print(f"DEBUG: Error message: {err_msg}")
    assert "would exceed WO total by" in err_msg


@pytest.mark.asyncio
async def test_create_pc_allows_exact_match(client, test_db, test_user, test_project_id):
    """Permits PC that exactly matches the remaining authorized balance."""
    # Setup Vendor
    v_id = str(ObjectId())
    await test_db.vendors.insert_one({
        "_id": ObjectId(v_id),
        "organisation_id": test_user["organisation_id"],
        "name": "Test Vendor 2"
    })

    wo_id = str(ObjectId())
    c_id = "CIVIL_2"
    # WO Total is 11800 (10000 subtotal + 1800 GST)
    await test_db.work_orders.insert_one({
        "_id": ObjectId(wo_id),
        "organisation_id": test_user["organisation_id"],
        "project_id": test_project_id,
        "vendor_id": v_id,
        "category_id": c_id,
        "grand_total": FinancialEngine.to_d128(11800),
        "active_status": True
    })

    await test_db.code_master.insert_one({
        "organisation_id": test_user["organisation_id"],
        "code": c_id,
        "budget_type": "commitment",
        "active_status": True
    })
    await test_db.fund_allocations.insert_one({
        "organisation_id": test_user["organisation_id"],
        "project_id": test_project_id,
        "category_id": c_id,
        "allocation_remaining": FinancialEngine.to_d128(20000)
    })

    pc_data = {
        "project_id": test_project_id,
        "work_order_id": wo_id,
        "vendor_id": v_id,
        "category_id": c_id,
        "line_items": [{"sr_no": 1, "scope_of_work": "Test", "qty": 1, "rate": 10000}],
        "idempotency_key": "test-exact-match"
    }

    response = await client.post("/api/v1/payments", json=pc_data)
    if response.status_code != 201:
        print(f"DEBUG: Status {response.status_code}, Body: {response.text}")
    assert response.status_code == 201
