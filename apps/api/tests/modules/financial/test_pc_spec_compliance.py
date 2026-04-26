import pytest
from decimal import Decimal
from bson import ObjectId
from app.modules.shared.domain.financial_engine import FinancialEngine

@pytest.mark.asyncio
async def test_pc_mode_b_creation_and_close(client, test_db, test_user, test_project_id):
    """Verify Mode B (Fund Request) creation, validations, and closure logic."""
    # 0. Cleanup
    await test_db.code_master.delete_many({})
    await test_db.fund_allocations.delete_many({})
    await test_db.payments.delete_many({})
    await test_db.financial_state.delete_many({})
    
    # 1. Setup Category (Fund Transfer)
    c_id = "PETTY_UNIQUE_1"
    await test_db.code_master.insert_one({
        "organisation_id": test_user["organisation_id"],
        "category_name": "Petty Cash",
        "code": c_id,
        "budget_type": "fund_transfer",
        "active_status": True
    })
    
    # 1.1 Setup Budget (1000)
    await test_db.project_category_budgets.insert_one({
        "organisation_id": test_user["organisation_id"],
        "project_id": test_project_id,
        "category_id": c_id,
        "original_budget": FinancialEngine.to_d128(1000),
        "active_status": True
    })
    
    # 2. Initialize Fund Allocation (1000)
    await test_db.fund_allocations.insert_one({
        "organisation_id": test_user["organisation_id"],
        "project_id": test_project_id,
        "category_id": c_id,
        "allocation_original": FinancialEngine.to_d128(1000),
        "allocation_received": FinancialEngine.to_d128(0),
        "allocation_remaining": FinancialEngine.to_d128(1000),
        "cash_in_hand": FinancialEngine.to_d128(0)
    })

    # 3. Create Mode B PC (Fund Request)
    pc_data = {
        "project_id": test_project_id,
        "category_id": c_id,
        "fund_request": True,
        "line_items": [
            {"sr_no": 1, "scope_of_work": "Tea and snacks", "qty": 1, "rate": 200, "unit": "LS"}
        ],
        "idempotency_key": "pc-mode-b-1"
    }
    response = await client.post("/api/v1/payments", json=pc_data)
    assert response.status_code == 201
    pc = response.json()["data"] 
    print(f"DEBUG: PC after creation: {pc}")
    pc_id_val = pc.get("id") or pc.get("_id")
    db_pc = await test_db.payments.find_one({"_id": ObjectId(pc_id_val)})
    print(f"DEBUG: PC in Database: {db_pc}")
    
    # 4. Close PC and Verify CALC-4/5
    alloc_before = await test_db.fund_allocations.find_one({"project_id": test_project_id, "category_id": c_id})
    print(f"DEBUG: Allocation BEFORE close: {alloc_before}")
    
    pc_id = str(pc.get("id") or pc.get("_id"))
    version = pc.get("version", 1)
    close_res = await client.post(f"/api/v1/payments/{pc_id}/close?expected_version={version}") 
    assert close_res.status_code == 200
    
    # 5. Verify Fund Allocation Updates (Expect 200 + 18% GST = 236)
    alloc = await test_db.fund_allocations.find_one({"project_id": test_project_id, "category_id": c_id})
    all_allocs = await test_db.fund_allocations.find({}).to_list(10)
    msg = f"PC after creation: {pc}\nAll Fund Allocations in DB: {all_allocs}\nPC Category: {pc.get('category_id')}\nPC Project: {pc.get('project_id')}"
    
    val_received = FinancialEngine.to_decimal(alloc["allocation_received"]) if alloc else None
    assert val_received == Decimal("236")
    
    assert FinancialEngine.to_decimal(alloc["allocation_remaining"]) == Decimal("764")
    assert FinancialEngine.to_decimal(alloc["cash_in_hand"]) == Decimal("236")
    
    # Verify Cash Transaction
    tx = await test_db.cash_transactions.find_one({"project_id": test_project_id, "category_id": c_id})
    assert tx["type"] == "CREDIT"
    assert FinancialEngine.to_decimal(tx["amount"]) == Decimal("236")
    
    # Verify Master Balance Impact (CALC-4)
    master = await test_db.financial_state.find_one({"project_id": test_project_id, "category_id": "MASTER"})
    assert FinancialEngine.to_decimal(master["balance_remaining"]) == Decimal("764")

@pytest.mark.asyncio
async def test_pc_mode_b_validation_failure(client, test_db, test_user, test_project_id):
    """Verify that Fund Request is rejected for commitment categories."""
    # 0. Cleanup
    # await test_db.code_master.delete_many({})
    # await test_db.fund_allocations.delete_many({})
    
    c_id = "CIVIL_UNIQUE"
    await test_db.code_master.insert_one({
        "organisation_id": test_user["organisation_id"],
        "category_name": "Civil Works",
        "code": c_id,
        "budget_type": "commitment",
        "active_status": True
    })
    
    pc_data = {
        "project_id": test_project_id,
        "category_id": c_id,
        "fund_request": True,
        "line_items": [{"sr_no": 1, "scope_of_work": "Invalid", "qty": 1, "rate": 100}]
    }
    response = await client.post("/api/v1/payments", json=pc_data)
    if response.status_code == 500:
        print(f"CRITICAL: validation_failure test got 500. Body: {response.text}")
    assert response.status_code == 422
    assert "must be of type 'fund_transfer'" in response.json()["error"]["message"]
