"""Track B: Attendance service tests — check_in, check_out, verify, admin list."""
import pytest


@pytest.mark.asyncio
async def test_check_in_success(client, supervisor_token, test_project):
    payload = {"project_id": test_project["id"], "gps_lat": 12.34, "gps_long": 77.56}
    resp = await client.post(
        "/api/v1/attendance/check-in",
        json=payload,
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    assert resp.status_code in (200, 201)
    data = resp.json()["data"]
    assert data["status"] in ("checked_in", "CheckedIn")


@pytest.mark.asyncio
async def test_check_in_duplicate_blocked(client, supervisor_token, test_project):
    payload = {"project_id": test_project["id"], "gps_lat": 12.34, "gps_long": 77.56}
    await client.post(
        "/api/v1/attendance/check-in",
        json=payload,
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    # Second check-in same day should fail
    resp = await client.post(
        "/api/v1/attendance/check-in",
        json=payload,
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    assert resp.status_code in (400, 409, 422)


@pytest.mark.asyncio
async def test_check_out_without_check_in_blocked(client, supervisor_token, test_project):
    resp = await client.post(
        "/api/v1/attendance/check-out",
        json={"project_id": test_project["id"]},
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    assert resp.status_code in (400, 404, 422)


@pytest.mark.asyncio
async def test_check_out_total_hours_set(client, supervisor_token, test_project):
    # Check in first
    await client.post(
        "/api/v1/attendance/check-in",
        json={"project_id": test_project["id"], "gps_lat": 0.0, "gps_long": 0.0},
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    resp = await client.post(
        "/api/v1/attendance/check-out",
        json={"project_id": test_project["id"]},
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    assert resp.status_code == 200
    assert "total_hours" in resp.json()["data"]


@pytest.mark.asyncio
async def test_double_checkout_blocked(client, supervisor_token, test_project):
    await client.post(
        "/api/v1/attendance/check-in",
        json={"project_id": test_project["id"], "gps_lat": 0.0, "gps_long": 0.0},
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    await client.post(
        "/api/v1/attendance/check-out",
        json={"project_id": test_project["id"]},
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    resp = await client.post(
        "/api/v1/attendance/check-out",
        json={"project_id": test_project["id"]},
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    assert resp.status_code in (400, 409, 422)


@pytest.mark.asyncio
async def test_admin_list_attendance(client, admin_token, test_project):
    resp = await client.get(
        f"/api/v1/attendance/?project_id={test_project['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json()["data"], list)


@pytest.mark.asyncio
async def test_attendance_verify(client, supervisor_token, admin_token, test_project):
    # Create attendance record
    await client.post(
        "/api/v1/attendance/check-in",
        json={"project_id": test_project["id"], "gps_lat": 1.0, "gps_long": 1.0},
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    list_resp = await client.get(
        f"/api/v1/attendance/?project_id={test_project['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    items = list_resp.json()["data"]
    if not items:
        pytest.skip("No attendance records to verify")
    att_id = items[0].get("id") or items[0].get("_id")

    resp = await client.patch(
        f"/api/v1/attendance/{att_id}/verify",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_attendance_date_filter(client, admin_token, test_project):
    resp = await client.get(
        f"/api/v1/attendance/?project_id={test_project['id']}&start_date=2026-01-01&end_date=2026-12-31",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
