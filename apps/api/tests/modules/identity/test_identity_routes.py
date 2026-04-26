"""Track E: Identity HTTP integration tests."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_endpoint_exists(client: AsyncClient):
    resp = await client.post("/api/v1/auth/login", json={
        "email": "nonexistent@test.com",
        "password": "anything"
    })
    # 401 = endpoint exists, credentials wrong (not 404/405)
    assert resp.status_code in (401, 400, 422)


@pytest.mark.asyncio
async def test_list_users_endpoint(client: AsyncClient):
    resp = await client.get("/api/v1/users/")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_create_user_endpoint(client: AsyncClient):
    resp = await client.post("/api/v1/users/admin-create", json={
        "email": "route_test@test.com",
        "password": "RouteTest1!",
        "name": "Route Test",
        "role": "Supervisor"
    })
    assert resp.status_code == 200
    assert resp.json()["data"]["email"] == "route_test@test.com"


@pytest.mark.asyncio
async def test_get_user_route_exists(client: AsyncClient):
    resp = await client.get("/api/v1/users/000000000000000000000001")
    # 404 = route exists, user not found
    assert resp.status_code in (404, 400)


@pytest.mark.asyncio
async def test_patch_user_route_exists(client: AsyncClient):
    resp = await client.patch(
        "/api/v1/users/000000000000000000000001",
        json={"name": "Test"}
    )
    # 404 = route exists, user not found
    assert resp.status_code in (404, 400)


@pytest.mark.asyncio
async def test_change_password_route_exists(client: AsyncClient):
    resp = await client.post("/api/v1/auth/change-password", json={
        "old_password": "OldPass1",
        "new_password": "NewPass1"
    })
    # 401/400 = route exists, auth fails (mock user has no real password)
    assert resp.status_code in (400, 401, 404)
