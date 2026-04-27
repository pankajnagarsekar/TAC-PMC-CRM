import pytest
from httpx import AsyncClient
from bson import ObjectId
from app.modules.shared.domain.financial_engine import FinancialEngine


@pytest.mark.asyncio
async def test_work_order_update_recalculates_budget(client: AsyncClient, test_db, test_user, test_project_id):
    """Verify that updating a WO correctly updates the budget committed amount."""
    # 1. Setup Vendor and Categories
    vendor_id = str(ObjectId())
    await test_db.vendors.insert_one({
        "_id": ObjectId(vendor_id),
        "organisation_id": test_user["organisation_id"],
        "name": "Lifecycle Vendor",
        "active_status": True
    })

    # Initialize two categories with budgets
    cat1_id = "C1_TEST"
    cat2_id = "C2_TEST"
    for cat_id in [cat1_id, cat2_id]:
        await test_db.project_category_budgets.insert_one({
            "project_id": test_project_id,
            "category_id": cat_id,
            "organisation_id": test_user["organisation_id"],
            "original_budget": FinancialEngine.to_d128(10000.0),
            "remaining_budget": FinancialEngine.to_d128(10000.0),
            "committed_amount": FinancialEngine.to_d128(0.0)
        })

    # 2. Create WO in Cat 1 (5000 units)
    resp = await client.post(f"/api/v1/work-orders/{test_project_id}", json={
        "project_id": test_project_id,
        "category_id": cat1_id,
        "vendor_id": vendor_id,
        "line_items": [{"sr_no": 1, "qty": 1, "rate": 5000}],
        "idempotency_key": "wo-upd-1"
    }, headers={"X-Request-Nonce": "wo-upd-1"})
    assert resp.status_code == 201
    wo = resp.json()["data"]
    print(f"DEBUG_WO: {wo}")
    wo_id = wo["id"]

    # Verify Cat 1 budget (5000 + 18% GST = 5900)
    budget1 = await test_db.financial_state.find_one({"project_id": test_project_id, "category_id": cat1_id})
    print(f"DEBUG: Cat 1 committed after create: {FinancialEngine.to_decimal(budget1['committed_value'])}")
    assert FinancialEngine.to_decimal(budget1["committed_value"]) == 5900

    # 3. Update WO: Change Category to Cat 2 and Increase Amount to 7000
    resp = await client.patch(f"/api/v1/work-orders/{wo_id}", json={
        "category_id": cat2_id,
        "line_items": [{"sr_no": 1, "qty": 1, "rate": 7000}],
        "expected_version": 1
    }, headers={"X-Request-Nonce": "upd-nonce-1"})
    if resp.status_code != 200:
        print(f"DEBUG_422: {resp.json()}")
    assert resp.status_code == 200

    # 4. Verify Budgets
    # Cat 1 should be back to 0
    budget1_after = await test_db.financial_state.find_one({"project_id": test_project_id, "category_id": cat1_id})
    print(f"DEBUG: Cat 1 committed after move: {FinancialEngine.to_decimal(budget1_after['committed_value'])}")
    assert FinancialEngine.to_decimal(budget1_after["committed_value"]) == 0

    # Cat 2 should now have 8260 (7000 + 18% GST)
    budget2_after = await test_db.financial_state.find_one({"project_id": test_project_id, "category_id": cat2_id})
    print(f"DEBUG: Cat 2 committed after move: {FinancialEngine.to_decimal(budget2_after['committed_value'])}")
    assert FinancialEngine.to_decimal(budget2_after["committed_value"]) == 8260


@pytest.mark.asyncio
async def test_work_order_delete_success(client: AsyncClient, test_db, test_user, test_project_id):
    """Verify that deleting a Draft WO reverses the budget impact."""
    # Setup
    vendor_id = str(ObjectId())
    await test_db.vendors.insert_one({
        "_id": ObjectId(vendor_id),
        "organisation_id": test_user["organisation_id"],
        "name": "Del Vendor",
        "active_status": True
    })
    cat_id = "DEL_CAT"
    await test_db.project_category_budgets.insert_one({
        "project_id": test_project_id, "category_id": cat_id, "organisation_id": test_user["organisation_id"],
        "original_budget": FinancialEngine.to_d128(10000.0), "committed_amount": FinancialEngine.to_d128(0.0)
    })

    # Create WO (3000)
    resp = await client.post(
        f"/api/v1/work-orders/{test_project_id}",
        json={
            "project_id": test_project_id,
            "category_id": cat_id,
            "vendor_id": vendor_id,
            "line_items": [{"sr_no": 1, "qty": 1, "rate": 3000}],
            "idempotency_key": "wo-del-1"
        },
        headers={"X-Request-Nonce": "wo-del-1"}
    )
    wo_id = resp.json()["data"]["id"]

    # Check budget before delete (3000 + 18% GST = 3540)
    budget = await test_db.financial_state.find_one({"category_id": cat_id})
    assert FinancialEngine.to_decimal(budget["committed_value"]) == 3540

    # Delete WO
    resp = await client.delete(f"/api/v1/work-orders/{wo_id}")
    assert resp.status_code == 200

    # Check budget after delete
    budget_after = await test_db.financial_state.find_one({"category_id": cat_id})
    assert FinancialEngine.to_decimal(budget_after["committed_value"]) == 0

    # Verify doc is gone
    wo_doc = await test_db.work_orders.find_one({"_id": ObjectId(wo_id)})
    assert wo_doc is None


@pytest.mark.asyncio
async def test_work_order_delete_blocked_if_not_draft(client: AsyncClient, test_db, test_user, test_project_id):
    """Verify that Approved work orders cannot be deleted."""
    wo_id = str(ObjectId())
    await test_db.work_orders.insert_one({
        "_id": ObjectId(wo_id),
        "organisation_id": test_user["organisation_id"],
        "status": "Approved",
        "project_id": test_project_id,
        "category_id": "C1"
    })

    resp = await client.delete(f"/api/v1/work-orders/{wo_id}")
    assert resp.status_code == 422  # ValidationError
    assert "Only Draft" in resp.json()["error"]["message"]


@pytest.mark.asyncio
async def test_budget_validation_prevents_low_budget(test_db, test_user, test_project_id):
    """Verify that BudgetService prevents reducing budget below committed amount."""
    from app.modules.financial.application.financial_service import FinancialService

    # Setup: Cat with 5000 committed
    cat_id = "VAL_CAT"
    await test_db.project_category_budgets.insert_one({
        "project_id": test_project_id, "category_id": cat_id, "organisation_id": test_user["organisation_id"],
        "original_budget": FinancialEngine.to_d128(10000.0)
    })
    # Synthetic committed state (e.g. from recalculate)
    await test_db.financial_state.insert_one({
        "project_id": test_project_id, "category_id": cat_id,
        "committed_value": FinancialEngine.to_d128(5000.0)
    })

    # Ensure there's a WO to justify the committed value (as recalculate is called in update_budget)
    await test_db.work_orders.insert_one({
        "project_id": test_project_id, "category_id": cat_id, "grand_total": FinancialEngine.to_d128(5000.0),
        "status": "Approved", "organisation_id": test_user["organisation_id"]
    })

    from app.modules.shared.application.audit_service import AuditService
    audit = AuditService(test_db)
    service = FinancialService(test_db, audit)
    from decimal import Decimal
    from app.modules.shared.domain.exceptions import ValidationError

    # Attempt to reduce original_budget to 4000 (Commit is 5000)
    with pytest.raises(ValidationError) as exc:
        await service.update_budget(
            test_user, test_project_id, cat_id,
            Decimal("4000.0"), expected_version=1
        )

    assert "below committed amount" in str(exc.value)
