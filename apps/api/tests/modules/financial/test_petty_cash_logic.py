import pytest
from decimal import Decimal
from app.modules.shared.domain.financial_engine import FinancialEngine
from app.modules.financial.application.financial_service import FinancialService

@pytest.mark.asyncio
async def test_petty_cash_committed_logic(test_db):
    """
    BUG-004: Verify that Petty Cash (fund_transfer) categories count non-cancelled PCs as committed.
    """
    service = FinancialService(test_db, None)
    project_id = "proj-123"
    category_id = "PTC-001" # Petty Cash code
    org_id = "org-123"

    # 1. Setup Category
    await test_db.code_master.insert_one({
        "code": category_id,
        "category_name": "Petty Cash",
        "budget_type": "fund_transfer",
        "organisation_id": org_id,
        "active_status": True
    })

    # 2. Setup Budget
    await test_db.budgets.insert_one({
        "project_id": project_id,
        "category_id": category_id,
        "organisation_id": org_id,
        "original_budget": FinancialEngine.to_d128(Decimal("10000.00")),
        "version": 1
    })

    # 3. Create a PC (Draft/Approved) for Petty Cash
    # For fund_transfer, we don't have a Work Order.
    pc_data = {
        "project_id": project_id,
        "category_id": category_id,
        "organisation_id": org_id,
        "pc_type": "PETTY_OVH",
        "fund_request": True,
        "status": "Approved",
        "grand_total": FinancialEngine.to_d128(Decimal("2500.00")),
        "net_payable": FinancialEngine.to_d128(Decimal("2500.00")),
        "created_at": "2024-01-01T00:00:00Z"
    }
    await test_db.payment_certificates.insert_one(pc_data)

    # 4. Recalculate
    res = await service.recalculate_project_code_financials(project_id, category_id)

    # 5. Assertions
    # Current behavior: committed_value will be 0 because it only looks at WOs.
    # Expected behavior: committed_value should be 2500.00
    committed = FinancialEngine.to_decimal(res["committed_value"])
    print(f"DEBUG: Committed Value = {committed}")
    
    assert committed == Decimal("2500.00"), "Petty Cash PC should be counted as committed"

@pytest.mark.asyncio
async def test_petty_cash_certified_logic(test_db):
    """
    Verify that paid Petty Cash PCs update certified_value.
    """
    service = FinancialService(test_db, None)
    project_id = "proj-456"
    category_id = "PTC-002"
    org_id = "org-456"

    await test_db.code_master.insert_one({
        "code": category_id,
        "category_name": "Petty Cash",
        "budget_type": "fund_transfer",
        "organisation_id": org_id,
        "active_status": True
    })

    await test_db.payment_certificates.insert_one({
        "project_id": project_id,
        "category_id": category_id,
        "organisation_id": org_id,
        "pc_type": "PETTY_OVH",
        "fund_request": True,
        "status": "Paid",
        "grand_total": FinancialEngine.to_d128(Decimal("3000.00")),
        "net_payable": FinancialEngine.to_d128(Decimal("3000.00")),
        "paid_at": "2024-01-02T00:00:00Z"
    })

    res = await service.recalculate_project_code_financials(project_id, category_id)
    
    certified = FinancialEngine.to_decimal(res["certified_value"])
    assert certified == Decimal("3000.00")
