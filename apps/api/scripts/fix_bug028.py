import asyncio
import os
import sys
from decimal import Decimal
from bson import Decimal128, ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

# Add apps/api to path so we can import modules
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.modules.financial.application.financial_service import FinancialService
from app.modules.shared.application.audit_service import AuditService

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "tac_pmc_crm")

async def fix_elc_budget():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    project_id = "69e26e2ebf1296a11a2f6942"
    
    # 1. Find ELC category ID
    cat = await db.code_master.find_one({"code": "ELC"})
    if not cat:
        print("ELC category code not found in code_master!")
        return
    
    cat_id = str(cat["_id"])
    print(f"Found ELC category ID: {cat_id}")
    
    target_value = Decimal128("5000000.00")
    
    # 2. Update project_category_budgets
    budget_query = {"project_id": project_id, "category_id": cat_id}
    budget_doc = await db.project_category_budgets.find_one(budget_query)
    
    if budget_doc:
        old_val = budget_doc.get("original_budget", Decimal128("0")).to_decimal()
        print(f"Current original_budget in project_category_budgets: {old_val}")
        await db.project_category_budgets.update_one(
            {"_id": budget_doc["_id"]},
            {"$set": {"original_budget": target_value, "version": budget_doc.get("version", 1) + 1}}
        )
        print("Updated project_category_budgets successfully.")
    else:
        print("No budget document found in project_category_budgets. Creating one...")
        await db.project_category_budgets.insert_one({
            "project_id": project_id,
            "organisation_id": "org_default", # fallback or fetch from project
            "category_id": cat_id,
            "original_budget": target_value,
            "committed_amount": Decimal128("0.0"),
            "remaining_budget": target_value,
            "version": 1
        })
        print("Created new ELC category budget document.")

    # 3. Update financial_state for ELC
    state_doc = await db.financial_state.find_one({"project_id": project_id, "category_id": cat_id})
    if state_doc:
        old_state_val = state_doc.get("original_budget", Decimal128("0")).to_decimal()
        print(f"Current original_budget in financial_state (ELC): {old_state_val}")
        await db.financial_state.update_one(
            {"_id": state_doc["_id"]},
            {"$set": {"original_budget": target_value}}
        )
        print("Updated financial_state for ELC successfully.")
    else:
        print("No financial_state document found for ELC. It will be initialized during recalculation.")

    # 4. Trigger Master Budget Recalculation using FinancialService
    audit = AuditService(db)
    financial_service = FinancialService(db, audit)
    
    print("Recalculating project financials and master budget snapshot...")
    await financial_service.recalculate_project_code_financials(project_id, cat_id)
    await financial_service.recalculate_master_budget(project_id)
    print("Recalculation complete.")
    
    # Verify new state
    new_master = await db.financial_state.find_one({"project_id": project_id, "category_id": "MASTER"})
    if new_master:
        print(f"New Master Budget Total: {new_master.get('original_budget').to_decimal()}")
    else:
        print("Master state NOT FOUND after recalculation.")

if __name__ == "__main__":
    asyncio.run(fix_elc_budget())
