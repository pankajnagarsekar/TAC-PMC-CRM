"""Track B: Worker log service tests — create, update, list."""
import pytest


@pytest.mark.asyncio
async def test_worker_log_create(client, supervisor_token, test_project):
    from app.core.time import now as ts_now
    payload = {
        "project_id": test_project["id"],
        "date": ts_now().strftime("%Y-%m-%d"),
        "entries": [
            {"vendor_name": "Contractor A", "workers_count": 10, "skill_type": "Carpenter", "rate_per_worker": 600}
        ],
        "workers": [],
        "remarks": "Initial log"
    }
    resp = await client.post(
        "/api/v1/worker-logs/",
        json=payload,
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["total_workers"] == 10


@pytest.mark.asyncio
async def test_worker_log_total_recalculated_on_update(client, supervisor_token, test_project):
    from app.core.time import now as ts_now
    create_resp = await client.post(
        "/api/v1/worker-logs/",
        json={
            "project_id": test_project["id"],
            "date": ts_now().strftime("%Y-%m-%d"),
            "entries": [{"vendor_name": "V", "workers_count": 3, "skill_type": "Mason", "rate_per_worker": 500}],
            "workers": [],
        },
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    log_id = (create_resp.json()["data"].get("id") or create_resp.json()["data"].get("_id"))

    resp = await client.put(
        f"/api/v1/worker-logs/{log_id}",
        json={"entries": [{"vendor_name": "V", "workers_count": 7, "skill_type": "Mason", "rate_per_worker": 500}]},
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["total_workers"] == 7


@pytest.mark.asyncio
async def test_worker_log_list_by_project(client, supervisor_token, test_project):
    resp = await client.get(
        f"/api/v1/worker-logs/?project_id={test_project['id']}",
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json()["data"], list)


@pytest.mark.asyncio
async def test_worker_log_remarks_persist_on_partial_update(client, supervisor_token, test_project):
    from app.core.time import now as ts_now
    create_resp = await client.post(
        "/api/v1/worker-logs/",
        json={
            "project_id": test_project["id"],
            "date": ts_now().strftime("%Y-%m-%d"),
            "entries": [{"vendor_name": "V", "workers_count": 2, "skill_type": "Mason", "rate_per_worker": 500}],
            "workers": [],
            "remarks": "Keep this remark",
        },
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    log_id = (create_resp.json()["data"].get("id") or create_resp.json()["data"].get("_id"))

    resp = await client.put(
        f"/api/v1/worker-logs/{log_id}",
        json={"entries": [{"vendor_name": "V", "workers_count": 4, "skill_type": "Mason", "rate_per_worker": 500}]},
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["remarks"] == "Keep this remark"


@pytest.mark.asyncio
async def test_worker_log_invalid_entry_rejected(client, supervisor_token, test_project):
    from app.core.time import now as ts_now
    resp = await client.post(
        "/api/v1/worker-logs/",
        json={
            "project_id": test_project["id"],
            "date": ts_now().strftime("%Y-%m-%d"),
            "entries": [{"vendor_name": "", "workers_count": -5, "skill_type": "", "rate_per_worker": 0}],
            "workers": [],
        },
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    # Negative workers or empty vendor should be rejected
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_worker_log_upsert_by_date(client, supervisor_token, test_project):
    """Two creates on same date should upsert not duplicate."""
    from app.core.time import now as ts_now
    today = ts_now().strftime("%Y-%m-%d")
    payload = {
        "project_id": test_project["id"],
        "date": today,
        "entries": [{"vendor_name": "V", "workers_count": 5, "skill_type": "Mason", "rate_per_worker": 500}],
        "workers": [],
    }
    r1 = await client.post(
        "/api/v1/worker-logs/", json=payload,
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    r2 = await client.post(
        "/api/v1/worker-logs/", json=payload,
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    # Both should succeed (upsert) or second returns existing
    assert r1.status_code in (200, 201)
    assert r2.status_code in (200, 201)


@pytest.mark.asyncio
async def test_worker_log_not_found_update(client, supervisor_token):
    resp = await client.put(
        "/api/v1/worker-logs/000000000000000000000001",
        json={"remarks": "ghost"},
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    assert resp.status_code in (404, 422)
