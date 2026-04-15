"""Track E: Auth service tests — login, token, logout, change_password."""
import pytest
from datetime import datetime, timezone
from httpx import AsyncClient

_NOW = datetime.now(timezone.utc)


async def _seed_user(db, email, password, role="Admin", active=True):
    from passlib.context import CryptContext
    ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    await db.users.insert_one({
        "email": email,
        "hashed_password": ctx.hash(password),
        "organisation_id": "test-org-123",
        "name": "Test User",
        "role": role,
        "active_status": active,
        "created_at": _NOW,
        "updated_at": _NOW,
    })


@pytest.mark.asyncio
async def test_login_wrong_password_returns_4xx(client: AsyncClient, test_db):
    await _seed_user(test_db, "badlogin@test.com", "CorrectPass1")
    resp = await client.post("/api/v1/auth/login", json={
        "email": "badlogin@test.com", "password": "WrongPass1"
    })
    assert resp.status_code in (400, 401, 422)


@pytest.mark.asyncio
async def test_login_success_returns_tokens(client: AsyncClient, test_db):
    await _seed_user(test_db, "goodlogin@test.com", "Correct1Pass")
    resp = await client.post("/api/v1/auth/login", json={
        "email": "goodlogin@test.com", "password": "Correct1Pass"
    })
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_token_refresh_revokes_old(client: AsyncClient, test_db):
    await _seed_user(test_db, "refresh@test.com", "Refresh1Pass")
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": "refresh@test.com", "password": "Refresh1Pass"
    })
    old_refresh = login_resp.json()["data"]["refresh_token"]

    refresh_resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert refresh_resp.status_code == 200
    assert refresh_resp.json()["data"]["refresh_token"] != old_refresh

    # Old token now invalid
    retry = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert retry.status_code in (400, 401)


@pytest.mark.asyncio
async def test_change_password_wrong_old_returns_4xx(client: AsyncClient, test_db):
    resp = await client.post("/api/v1/auth/change-password", json={
        "old_password": "WrongOld1",
        "new_password": "NewPassword1"
    })
    assert resp.status_code in (400, 401, 404)


@pytest.mark.asyncio
async def test_change_password_weak_new_returns_422(client: AsyncClient, test_db):
    resp = await client.post("/api/v1/auth/change-password", json={
        "old_password": "anything",
        "new_password": "short"
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_logout_success(client: AsyncClient, test_db):
    await _seed_user(test_db, "logout@test.com", "Logout1Pass")
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": "logout@test.com", "password": "Logout1Pass"
    })
    access_token = login_resp.json()["data"]["access_token"]
    resp = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_deactivated_user_cannot_login(client: AsyncClient, test_db):
    await _seed_user(test_db, "deactivated@test.com", "Active1Pass", active=False)
    resp = await client.post("/api/v1/auth/login", json={
        "email": "deactivated@test.com", "password": "Active1Pass"
    })
    assert resp.status_code in (400, 401, 403)


@pytest.mark.asyncio
async def test_password_strength_validation():
    from app.modules.identity.application.auth_service import AuthService
    from app.modules.identity.domain.exceptions import PasswordTooWeakError
    from passlib.context import CryptContext

    svc = AuthService.__new__(AuthService)
    svc.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    for weak in ("short", "alllowercase1", "NOLOWER1", "NoDigit"):
        try:
            svc._validate_password_strength(weak)
            assert False, f"Should raise for: {weak}"
        except PasswordTooWeakError:
            pass

    svc._validate_password_strength("ValidPass1")  # should not raise
