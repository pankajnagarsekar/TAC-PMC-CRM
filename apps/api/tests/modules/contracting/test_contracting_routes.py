import pytest
from httpx import AsyncClient
from bson import ObjectId

@pytest.mark.asyncio
async def test_vendor_routes(client: AsyncClient):
    # 1. Create
    resp = await client.post("/api/v1/vendors/", json={
        "name": "Integration Test Vendor"
    })
    assert resp.status_code == 201
    
    # 2. List
    resp = await client.get("/api/v1/vendors/")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert any(v["name"] == "Integration Test Vendor" for v in data)

@pytest.mark.asyncio
async def test_work_order_routes(client: AsyncClient, test_db, test_user, test_project_id):
    # Setup
    vendor_id = str(ObjectId())
    await test_db.vendors.insert_one({
        "_id": ObjectId(vendor_id), 
        "organisation_id": test_user["organisation_id"], 
        "name": "Route Vendor",
        "active_status": True
    })
    await test_db.project_category_budgets.insert_one({
        "project_id": test_project_id, 
        "category_id": "C1", 
        "organisation_id": test_user["organisation_id"], 
        "remaining_budget": 10000.0, 
        "committed_amount": 0.0
    })

    # Create WO
    resp = await client.post(f"/api/v1/work-orders/{test_project_id}", json={
        "project_id": test_project_id,
        "category_id": "C1",
        "vendor_id": vendor_id,
        "line_items": [{"sr_no": 1, "qty": 1, "rate": 500}],
        "idempotency_key": "test-nonce"
    }, headers={"X-Request-Nonce": "test-nonce"})
    
    assert resp.status_code == 201
    wo_id = resp.json()["data"]["id"]

    # Submit
    resp = await client.post(f"/api/v1/work-orders/{wo_id}/submit")
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "Pending"

    # Approve (Admin role is default in fixture)
    resp = await client.post(f"/api/v1/work-orders/{wo_id}/approve")
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "Approved"

@pytest.mark.asyncio
async def test_wo_cancel(client: AsyncClient, test_db, test_user, test_project_id):
    """C5: WO cancel transitions Any → Cancelled."""
    vendor_id = str(ObjectId())
    await test_db.vendors.insert_one({
        "_id": ObjectId(vendor_id),
        "organisation_id": test_user["organisation_id"],
        "name": "Cancel Vendor",
        "active_status": True
    })
    await test_db.project_category_budgets.insert_one({
        "project_id": test_project_id,
        "category_id": "C_CANCEL",
        "organisation_id": test_user["organisation_id"],
        "remaining_budget": 5000.0,
        "committed_amount": 0.0
    })
    resp = await client.post(f"/api/v1/work-orders/{test_project_id}", json={
        "project_id": test_project_id,
        "category_id": "C_CANCEL",
        "vendor_id": vendor_id,
        "line_items": [{"sr_no": 1, "qty": 1, "rate": 100}],
        "idempotency_key": "cancel-nonce"
    }, headers={"X-Request-Nonce": "cancel-nonce"})
    assert resp.status_code == 201
    wo_id = resp.json()["data"]["id"]

    resp = await client.post(f"/api/v1/work-orders/{wo_id}/cancel")
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "Cancelled"


@pytest.mark.asyncio
async def test_vendor_delete_blocked_with_active_wo(client: AsyncClient, test_db, test_user):
    """C5: Vendor delete blocked when active WOs exist."""
    # Create vendor
    resp = await client.post("/api/v1/vendors/", json={"name": "Blocked Vendor"})
    assert resp.status_code == 201
    vendor_id = resp.json()["data"]["id"]

    # Insert an active WO referencing this vendor
    await test_db.work_orders.insert_one({
        "vendor_id": vendor_id,
        "organisation_id": test_user["organisation_id"],
        "status": "Pending",
        "project_id": "proj-block-test"
    })

    # Delete should be blocked
    resp = await client.delete(f"/api/v1/vendors/{vendor_id}")
    assert resp.status_code in (400, 409)


@pytest.mark.asyncio
async def test_contract_routes(client: AsyncClient, test_db, test_user, test_project_id):
    # Setup Approved WO
    wo_id = str(ObjectId())
    vendor_id = str(ObjectId())
    await test_db.work_orders.insert_one({
        "_id": ObjectId(wo_id),
        "organisation_id": test_user["organisation_id"],
        "status": "Approved",
        "project_id": test_project_id,
        "vendor_id": vendor_id
    })

    # Create Contract
    resp = await client.post(f"/api/v1/work-orders/{wo_id}/contract", json={
        "work_order_id": wo_id,
        "vendor_id": vendor_id,
        "contract_value": 5000,
        "start_date": "2026-01-01T00:00:00Z",
        "end_date": "2026-12-31T00:00:00Z",
        "terms": "Route test terms"
    })
    assert resp.status_code == 201
    
    # Get Contract
    resp = await client.get(f"/api/v1/work-orders/{wo_id}/contract")
    assert resp.status_code == 200
    assert resp.json()["data"]["terms"] == "Route test terms"
