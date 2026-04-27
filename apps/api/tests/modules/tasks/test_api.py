import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_task(client: AsyncClient, admin_token: str, test_project_id: str, test_org_id: str):
    response = await client.post(
        "/api/v1/tasks/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "organisation_id": test_org_id,
            "project_id": test_project_id,
            "task_description": "Test Task 1",
            "assigned_to_name": "Test User",
            "assigned_to_type": "user",
            "priority": "High"
        }
    )
    res_json = response.json()
    if response.status_code != 201:
        print(f"DEBUG ERROR: {res_json}")
    assert response.status_code == 201, f"Expected 201, got {response.status_code}. Body: {res_json}"
    data = res_json.get("data")
    if not data:
        print(f"DEBUG_FULL_RES: {res_json}")
    assert data["task_description"] == "Test Task 1"
    assert data["status"] == "Open"
    assert data["sr_no"] == 1

@pytest.mark.asyncio
async def test_get_task_details_with_audit(client: AsyncClient, admin_token: str, test_project_id: str, test_org_id: str):
    # Create task
    create_res = await client.post(
        "/api/v1/tasks/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "organisation_id": test_org_id,
            "project_id": test_project_id,
            "task_description": "Audit Log Test",
            "assigned_to_name": "Test User",
        }
    )
    res_json = create_res.json()
    data = res_json["data"]
    task_id = data.get("id") or data.get("_id")
    if not task_id:
        raise KeyError(f"Neither 'id' nor '_id' found in {data}")

    # Update status
    update_res = await client.patch(
        f"/api/v1/tasks/{task_id}/status",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"status": "In Progress"}
    )
    assert update_res.status_code == 200

    # Get details
    get_res = await client.get(
        f"/api/v1/tasks/{task_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert get_res.status_code == 200
    res_json = get_res.json()
    data = res_json["data"]
    assert len(data["audit_log"]) >= 1
    assert data["audit_log"][0]["action"] in ["CREATE", "STATUS_CHANGE"]

@pytest.mark.asyncio
async def test_invalid_transition(client: AsyncClient, admin_token: str, test_project_id: str, test_org_id: str):
    # Create task
    create_res = await client.post(
        "/api/v1/tasks/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "organisation_id": test_org_id,
            "project_id": test_project_id,
            "task_description": "Invalid Transition Test",
            "assigned_to_name": "Test User",
            "assigned_to_type": "user"
        }
    )
    res_json = create_res.json()
    data = res_json["data"]
    task_id = data.get("id") or data.get("_id")

    # Attempt invalid jump: Open -> Completed
    response = await client.patch(
        f"/api/v1/tasks/{task_id}/status",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"status": "Completed"}
    )
    assert response.status_code == 400
    assert "INVALID_TRANSITION" in response.json()["detail"]

@pytest.mark.asyncio
async def test_data_freeze_in_closed(client: AsyncClient, admin_token: str, test_project_id: str, test_org_id: str):
    # Create task
    create_res = await client.post(
        "/api/v1/tasks/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "organisation_id": test_org_id,
            "project_id": test_project_id,
            "task_description": "Freeze Test",
            "assigned_to_name": "Test User",
            "assigned_to_type": "user"
        }
    )
    res_json = create_res.json()
    data = res_json["data"]
    task_id = data.get("id") or data.get("_id")

    # Move to In Progress
    res = await client.patch(f"/api/v1/tasks/{task_id}/status", headers={"Authorization": f"Bearer {admin_token}"}, json={"status": "In Progress"})
    assert res.status_code == 200, f"Failed to move to In Progress: {res.text}"
    # Move to Completed
    res = await client.patch(f"/api/v1/tasks/{task_id}/status", headers={"Authorization": f"Bearer {admin_token}"}, json={"status": "Completed"})
    assert res.status_code == 200, f"Failed to move to Completed: {res.text}"
    # Move to Closed
    res = await client.patch(f"/api/v1/tasks/{task_id}/status", headers={"Authorization": f"Bearer {admin_token}"}, json={"status": "Closed"})
    assert res.status_code == 200, f"Failed to move to Closed: {res.text}"

    # Attempt update
    response = await client.patch(
        f"/api/v1/tasks/{task_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"task_description": "Modified Description"}
    )
    assert response.status_code == 400
    assert "DATA_FREEZE" in response.json()["detail"]
