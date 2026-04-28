import pytest
from app.modules.financial.application.master_data_service import MasterDataService

@pytest.mark.asyncio
async def test_petty_cash_categories_regex_plural(test_db):
    """Verify that MasterDataService.list_petty_cash_categories handles plural/singular Site Overhead(s)."""
    # 1. Setup mock service
    service = MasterDataService(test_db, None, None)
    
    # 2. Seed test data
    test_org_id = "test-org-123"
    categories = [
        {"category_name": "Petty Cash", "organisation_id": test_org_id, "budget_type": "material", "active_status": True},
        {"category_name": "Site Overheads", "organisation_id": test_org_id, "budget_type": "labor", "active_status": True},
        {"category_name": "Food Expense", "organisation_id": test_org_id, "budget_type": "misc", "active_status": True}
    ]
    for cat in categories:
        await test_db.code_master.insert_one(cat)
        
    # 3. Test list_petty_cash_categories
    user = {"organisation_id": test_org_id}
    results = await service.list_petty_cash_categories(user)
    
    # 4. Assertions
    assert len(results) == 2
    names = [r["category_name"] for r in results]
    assert "Petty Cash" in names
    assert "Site Overheads" in names
    
    # Verify budget_type enforcement
    for r in results:
        assert r["budget_type"] == "fund_transfer"

@pytest.mark.asyncio
async def test_petty_cash_categories_regex_singular(test_db):
    """Verify that MasterDataService.list_petty_cash_categories handles singular Site Overhead."""
    service = MasterDataService(test_db, None, None)
    test_org_id = "test-org-singular"
    
    categories = [
        {"category_name": "Petty Cash", "organisation_id": test_org_id, "budget_type": "material", "active_status": True},
        {"category_name": "Site Overhead", "organisation_id": test_org_id, "budget_type": "labor", "active_status": True}
    ]
    for cat in categories:
        await test_db.code_master.insert_one(cat)
        
    user = {"organisation_id": test_org_id}
    results = await service.list_petty_cash_categories(user)
    
    assert len(results) == 2
    names = [r["category_name"] for r in results]
    assert "Petty Cash" in names
    assert "Site Overhead" in names

@pytest.mark.asyncio
async def test_petty_cash_categories_case_insensitive(test_db):
    """Verify that MasterDataService.list_petty_cash_categories is case-insensitive."""
    service = MasterDataService(test_db, None, None)
    test_org_id = "test-org-case"
    
    categories = [
        {"category_name": "petty cash", "organisation_id": test_org_id, "budget_type": "material", "active_status": True},
        {"category_name": "SITE OVERHEADS", "organisation_id": test_org_id, "budget_type": "labor", "active_status": True}
    ]
    for cat in categories:
        await test_db.code_master.insert_one(cat)
        
    user = {"organisation_id": test_org_id}
    results = await service.list_petty_cash_categories(user)
    
    assert len(results) == 2
    names = [r["category_name"] for r in results]
    assert "petty cash" in names
    assert "SITE OVERHEADS" in names
