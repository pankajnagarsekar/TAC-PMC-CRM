import pytest
from fastapi import status
from app.modules.identity.schemas.dto import LoginRequest, GlobalSettingsUpdate
from app.modules.financial.schemas.dto import CodeMasterCreate

@pytest.mark.asyncio
async def test_password_length_limit():
    # Verify LoginRequest rejects oversized passwords (DTO validation)
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        LoginRequest(email="test@example.com", password="a" * 129)
    
    # 128 should pass
    LoginRequest(email="test@example.com", password="a" * 128)

@pytest.mark.asyncio
async def test_email_validation_dto():
    # Verify GlobalSettingsUpdate rejects invalid emails
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        GlobalSettingsUpdate(email="invalid-email", expected_version=1)
    
    # Valid email should pass
    GlobalSettingsUpdate(email="valid@example.com", expected_version=1)


@pytest.mark.asyncio
async def test_category_uniqueness_logic(client, admin_token):
    # This requires a running DB or mock. Since I shouldn't rely on full integration 
    # without setup, I'll attempt a localized test if possible, 
    # but usually 'pytest' with 'client' fixture works in this repo.
    
    # Create first category
    cat1 = {
        "code": "T001",
        "category_name": "Test Category",
        "budget_type": "fund_transfer"
    }
    resp = await client.post("/api/v1/settings/codes", json=cat1, headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 201

    # Try same code
    cat2 = {
        "code": "T001",
        "category_name": "Different Name",
        "budget_type": "fund_transfer"
    }
    resp = await client.post("/api/v1/settings/codes", json=cat2, headers={"Authorization": f"Bearer {admin_token}"})
    if resp.status_code != 422:
        print(f"DEBUG: Status {resp.status_code}, Detail: {resp.json().get('detail')}")
    assert resp.status_code == 422
    assert "CODE_EXISTS" in str(resp.json())

    # Try same name
    cat3 = {
        "code": "T002",
        "category_name": "Test Category",
        "budget_type": "fund_transfer"
    }
    resp = await client.post("/api/v1/settings/codes", json=cat3, headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 422
    assert "NAME_EXISTS" in str(resp.json())


