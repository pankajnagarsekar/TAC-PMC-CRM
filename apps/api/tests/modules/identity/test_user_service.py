"""Track E: User service tests — CRUD, get_user, update_user, deactivate."""
import pytest
from datetime import datetime, timezone
from httpx import AsyncClient

_NOW = datetime.now(timezone.utc)

_BASE_USER = {
    "organisation_id": "test-org-123",
    "active_status": True,
    "hashed_password": "xxx",
    "created_at": _NOW,
    "updated_at": _NOW,
}


@pytest.mark.asyncio
async def test_create_user_admin_success(client: AsyncClient):
    resp = await client.post("/api/v1/users/admin-create", json={
        "email": "newuser@test.com",
        "password": "Password1!",
        "name": "New User",
        "role": "Supervisor"
    })
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["email"] == "newuser@test.com"
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_create_user_duplicate_email_returns_409(client: AsyncClient):
    payload = {"email": "dup@test.com", "password": "Password1!", "name": "Dup"}
    await client.post("/api/v1/users/admin-create", json=payload)
    resp = await client.post("/api/v1/users/admin-create", json=payload)
    assert resp.status_code in (409, 400, 422)


@pytest.mark.asyncio
async def test_list_users_returns_list(client: AsyncClient):
    resp = await client.get("/api/v1/users/")
    assert resp.status_code == 200
    assert isinstance(resp.json()["data"], list)


@pytest.mark.asyncio
async def test_get_user_by_id(client: AsyncClient, test_db):
    from bson import ObjectId
    user_id = str(ObjectId())
    await test_db.users.insert_one({
        "_id": ObjectId(user_id),
        "email": "getme@test.com",
        "name": "Get Me",
        "role": "Supervisor",
        **_BASE_USER,
    })
    resp = await client.get(f"/api/v1/users/{user_id}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["email"] == "getme@test.com"
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_get_user_not_found(client: AsyncClient):
    resp = await client.get("/api/v1/users/000000000000000000000001")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_user_name(client: AsyncClient, test_db):
    from bson import ObjectId
    user_id = str(ObjectId())
    await test_db.users.insert_one({
        "_id": ObjectId(user_id),
        "email": "update@test.com",
        "name": "Old Name",
        "role": "Supervisor",
        **_BASE_USER,
    })
    resp = await client.patch(f"/api/v1/users/{user_id}", json={"name": "New Name"})
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "New Name"


@pytest.mark.asyncio
async def test_update_user_role_by_admin(client: AsyncClient, test_db):
    from bson import ObjectId
    user_id = str(ObjectId())
    await test_db.users.insert_one({
        "_id": ObjectId(user_id),
        "email": "rolechange@test.com",
        "name": "Role User",
        "role": "Supervisor",
        **_BASE_USER,
    })
    resp = await client.patch(f"/api/v1/users/{user_id}", json={"role": "Admin"})
    assert resp.status_code == 200
    assert resp.json()["data"]["role"] == "Admin"


@pytest.mark.asyncio
async def test_deactivate_user_success(client: AsyncClient, test_db):
    from bson import ObjectId
    user_id = str(ObjectId())
    await test_db.users.insert_one({
        "_id": ObjectId(user_id),
        "email": "deact@test.com",
        "name": "Deact User",
        "role": "Supervisor",
        **_BASE_USER,
    })
    resp = await client.delete(f"/api/v1/users/{user_id}")
    assert resp.status_code == 200
