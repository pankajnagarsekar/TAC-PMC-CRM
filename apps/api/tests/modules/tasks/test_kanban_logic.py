import pytest
from httpx import AsyncClient
from app.modules.tasks.domain.constants import TASK_STATUS_OPEN, TASK_STATUS_IN_PROGRESS, TASK_STATUS_REVIEW

@pytest.mark.asyncio
async def test_task_status_transitions(client: AsyncClient, admin_token: str, test_project_id: str):
    # 1. Create a task
    create_res = await client.post(
        "/api/v1/tasks/",
        json={
            "project_id": test_project_id,
            "task_description": "Kanban Test Task",
            "priority": "Normal",
            "assigned_to_name": "Test User",
            "status": TASK_STATUS_OPEN
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert create_res.status_code == 201
    task_id = create_res.json()["data"]["_id"]
    
    # 2. Transition to In Progress
    patch_res = await client.patch(
        f"/api/v1/tasks/{task_id}/status",
        json={"status": TASK_STATUS_IN_PROGRESS},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["data"]["status"] == TASK_STATUS_IN_PROGRESS
    
    # 3. Transition to Review (New Status)
    patch_res = await client.patch(
        f"/api/v1/tasks/{task_id}/status",
        json={"status": TASK_STATUS_REVIEW},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["data"]["status"] == TASK_STATUS_REVIEW
    
    # 4. Try illegal transition (Review -> Open is not allowed in state_machine.py)
    # Review -> {Completed, In Progress, Closed}
    patch_res = await client.patch(
        f"/api/v1/tasks/{task_id}/status",
        json={"status": TASK_STATUS_OPEN},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert patch_res.status_code == 400
    # The detail is a string starting with INVALID_TRANSITION
    assert "INVALID_TRANSITION" in patch_res.json()["detail"]
