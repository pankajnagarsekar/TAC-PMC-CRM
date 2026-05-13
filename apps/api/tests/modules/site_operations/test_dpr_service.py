"""Track B: DPR service tests — create, submit, approve, reject, list."""
import pytest


@pytest.mark.asyncio
async def test_dpr_create_success(client, supervisor_token, test_project):
    payload = {"project_id": test_project["id"], "progress_notes": "Foundation complete"}
    resp = await client.post(
        "/api/v1/dprs/",
        json=payload,
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["progress_notes"] == "Foundation complete"
    assert data["status"] in ("Draft", "draft")


@pytest.mark.asyncio
async def test_dpr_create_missing_notes_rejected(client, supervisor_token, test_project):
    payload = {"project_id": test_project["id"], "progress_notes": ""}
    resp = await client.post(
        "/api/v1/dprs/",
        json=payload,
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_dpr_list_by_project(client, supervisor_token, test_project):
    # Create two DPRs
    for note in ("Day 1 work", "Day 2 work"):
        await client.post(
            "/api/v1/dprs/",
            json={"project_id": test_project["id"], "progress_notes": note},
            headers={"Authorization": f"Bearer {supervisor_token}"},
        )

    resp = await client.get(
        f"/api/v1/projects/{test_project['id']}/dprs",
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    assert resp.status_code == 200
    items = resp.json()["data"]
    assert len(items) >= 2


@pytest.mark.asyncio
async def test_dpr_submit_transitions_status(client, supervisor_token, test_project):
    create_resp = await client.post(
        "/api/v1/dprs/",
        json={"project_id": test_project["id"], "progress_notes": "Submit me"},
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    dpr_id = (create_resp.json()["data"].get("id") or create_resp.json()["data"].get("_id"))

    resp = await client.post(
        f"/api/v1/dprs/{dpr_id}/submit",
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] in ("Submitted", "submitted", "Pending", "pending")


@pytest.mark.asyncio
async def test_dpr_approve_by_admin(client, supervisor_token, admin_token, test_project):
    create_resp = await client.post(
        "/api/v1/dprs/",
        json={"project_id": test_project["id"], "progress_notes": "Approve me"},
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    dpr_id = (create_resp.json()["data"].get("id") or create_resp.json()["data"].get("_id"))
    await client.post(
        f"/api/v1/dprs/{dpr_id}/submit",
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )

    resp = await client.patch(
        f"/api/v1/dprs/{dpr_id}/approve",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] in ("Approved", "approved")


@pytest.mark.asyncio
async def test_dpr_reject_requires_reason(client, supervisor_token, admin_token, test_project):
    create_resp = await client.post(
        "/api/v1/dprs/",
        json={"project_id": test_project["id"], "progress_notes": "Reject me"},
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    dpr_id = (create_resp.json()["data"].get("id") or create_resp.json()["data"].get("_id"))
    await client.post(
        f"/api/v1/dprs/{dpr_id}/submit",
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )

    # Missing reason → 422
    resp = await client.patch(
        f"/api/v1/dprs/{dpr_id}/reject",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_dpr_reject_with_reason(client, supervisor_token, admin_token, test_project):
    create_resp = await client.post(
        "/api/v1/dprs/",
        json={"project_id": test_project["id"], "progress_notes": "Reject with reason"},
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    dpr_id = (create_resp.json()["data"].get("id") or create_resp.json()["data"].get("_id"))
    await client.post(
        f"/api/v1/dprs/{dpr_id}/submit",
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )

    resp = await client.patch(
        f"/api/v1/dprs/{dpr_id}/reject",
        params={"reason": "Incomplete photos"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] in ("Rejected", "rejected")


@pytest.mark.asyncio
async def test_dpr_get_detail(client, supervisor_token, test_project):
    create_resp = await client.post(
        "/api/v1/dprs/",
        json={"project_id": test_project["id"], "progress_notes": "Detail test"},
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    dpr_id = (create_resp.json()["data"].get("id") or create_resp.json()["data"].get("_id"))

    resp = await client.get(
        f"/api/v1/dprs/{dpr_id}",
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["progress_notes"] == "Detail test"


@pytest.mark.asyncio
async def test_dpr_add_image(client, supervisor_token, test_project):
    create_resp = await client.post(
        "/api/v1/dprs/",
        json={"project_id": test_project["id"], "progress_notes": "Image test"},
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    dpr_id = (create_resp.json()["data"].get("id") or create_resp.json()["data"].get("_id"))

    resp = await client.post(
        f"/api/v1/dprs/{dpr_id}/images",
        json={"image_data": "base64testdata", "caption": "Site photo"},
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    assert resp.status_code in (200, 201)

    detail = await client.get(
        f"/api/v1/dprs/{dpr_id}",
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    assert detail.json()["data"]["image_count"] >= 1


@pytest.mark.asyncio
async def test_dpr_date_range_filter(client, supervisor_token, test_project):
    resp = await client.get(
        f"/api/v1/dprs/?project_id={test_project['id']}&start_date=2026-01-01&end_date=2026-12-31",
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json()["data"], list)
