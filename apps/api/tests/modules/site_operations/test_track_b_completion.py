import pytest

from app.core.time import now as ts_now
from decimal import Decimal

@pytest.mark.asyncio
async def test_worker_log_partial_update(client, supervisor_token, test_project):
    """B4: Verify worker_log partial updates calculation."""
    # 1. Create initial log
    log_date = ts_now().strftime("%Y-%m-%d")
    create_payload = {
        "project_id": test_project["id"],
        "date": log_date,
        "entries": [
            {"vendor_name": "V1", "workers_count": 5, "skill_type": "Mason", "rate_per_worker": 500}
        ],
        "workers": [],
        "remarks": "Initial"
    }

    resp = await client.post(
        "/api/v1/worker-logs/",
        json=create_payload,
        headers={"Authorization": f"Bearer {supervisor_token}"}
    )
    print(f"DEBUG_WORKER_LOG: status={resp.status_code} body={resp.json()}")
    assert resp.status_code == 201
    log_data_res = resp.json()["data"]
    log_id = log_data_res.get("id") or log_data_res.get("_id")
    assert resp.json()["data"]["total_workers"] == 5

    # 2. Partial update counts
    update_payload = {
        "entries": [
            {"vendor_name": "V1", "workers_count": 8, "skill_type": "Mason", "rate_per_worker": 500}
        ]
    }
    resp = await client.put( # Using PUT as per routes.py
        f"/api/v1/worker-logs/{log_id}",
        json=update_payload,
        headers={"Authorization": f"Bearer {supervisor_token}"}
    )
    assert resp.status_code == 200
    # Total workers should be recalculated
    assert resp.json()["data"]["total_workers"] == 8
    assert resp.json()["data"]["remarks"] == "Initial" # Should persist

@pytest.mark.asyncio
async def test_attendance_checkout_calculation(client, supervisor_token, test_project):
    """B4: Verify total_hours calculation on check-out."""
    # 1. Check-in
    payload = {"project_id": test_project["id"], "gps_lat": 12.3, "gps_long": 77.8}
    await client.post(
        "/api/v1/attendance/check-in",
        json=payload,
        headers={"Authorization": f"Bearer {supervisor_token}"}
    )

    # 2. Check-out
    resp = await client.post(
        "/api/v1/attendance/check-out",
        json={"project_id": test_project["id"]},
        headers={"Authorization": f"Bearer {supervisor_token}"}
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "checked_out"
    assert "total_hours" in data
    assert isinstance(data["total_hours"], (float, int))

@pytest.mark.asyncio
async def test_site_overhead_occ(client, admin_token, test_project):
    """B4: Verify Site Overhead optimistic locking."""
    # 1. Create overhead
    payload = {"project_id": test_project["id"], "amount": 1500, "purpose": "Transport"}
    resp = await client.post(
        "/api/v1/site-overheads",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    overhead_id = data.get("id") or data.get("_id")
    version = resp.json()["data"].get("version", 1)

    # 2. Update with wrong version (OCC is validation error 422 in my implementation)
    update_payload = {"amount": 2000, "version": version + 10}
    resp = await client.put( # Using PUT as per routes.py
        f"/api/v1/site-overheads/{overhead_id}",
        json=update_payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 422

    # 3. Update with correct version
    update_payload = {"amount": 2000, "version": version}
    resp = await client.put(
        f"/api/v1/site-overheads/{overhead_id}",
        json=update_payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    assert Decimal(str(resp.json()["data"]["amount"])) == Decimal("2000")

@pytest.mark.asyncio
async def test_dpr_image_deletion(client, supervisor_token, test_project):
    """B4: Verify DPR image $pull and count decrement."""
    # 1. Create DPR
    dpr_payload = {"project_id": test_project["id"], "progress_notes": "Testing images"}
    resp = await client.post(
        "/api/v1/dprs/",
        json=dpr_payload,
        headers={"Authorization": f"Bearer {supervisor_token}"}
    )
    assert resp.status_code == 201
    dpr_data_res = resp.json()["data"]
    dpr_id = dpr_data_res.get("id") or dpr_data_res.get("_id")

    # 2. Add an image
    img_payload = {"image_data": "base64dummy", "caption": "Delete me"}
    await client.post(
        f"/api/v1/dprs/{dpr_id}/images",
        json=img_payload,
        headers={"Authorization": f"Bearer {supervisor_token}"}
    )

    # 3. Get DPR to find real image_id
    resp = await client.get(
        f"/api/v1/dprs/{dpr_id}",
        headers={"Authorization": f"Bearer {supervisor_token}"}
    )
    print(f"DEBUG_DPR: status={resp.status_code} body={resp.json()}")
    image_id = resp.json()["data"]["images"][0]["image_id"]
    assert resp.json()["data"]["image_count"] == 1

    # 4. Delete image
    resp = await client.delete(
        f"/api/v1/dprs/{dpr_id}/images/{image_id}",
        headers={"Authorization": f"Bearer {supervisor_token}"}
    )
    assert resp.status_code == 200

    # 5. Verify it's gone
    resp = await client.get(
        f"/api/v1/dprs/{dpr_id}",
        headers={"Authorization": f"Bearer {supervisor_token}"}
    )
    assert resp.json()["data"]["image_count"] == 0
    assert len(resp.json()["data"]["images"]) == 0
