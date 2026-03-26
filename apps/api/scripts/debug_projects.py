import asyncio
import os
import sys
from bson import ObjectId

# Add current dir to path
sys.path.append(os.getcwd())

from core.database import db_manager
from dotenv import load_dotenv

async def check_project():
    load_dotenv()
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "tac_pmc_crm")
    db_manager.connect(mongo_url=mongo_url, db_name=db_name)
    try:
        proj = await db_manager.db.projects.find_one({'project_name': 'Majorda Villa'})
        if proj:
            print(f"Project ID: {proj.get('_id')}")
            print(f"master_original_budget: {proj.get('master_original_budget')}")
            print(f"master_remaining_budget: {proj.get('master_remaining_budget')}")
            
            output = []
            output.append(f"Project ID: {proj.get('_id')}")
            output.append(f"Master Orig: {proj.get('master_original_budget')}")
            
            budgets = await db_manager.db.project_category_budgets.find({'project_id': str(proj['_id'])}).to_list(5)
            for b in budgets:
                output.append(f"BID:{b.get('category_id')} O:{b.get('original_budget')}")
                
            financials = await db_manager.db.financial_state.find({'project_id': str(proj['_id'])}).to_list(10)
            for f in financials:
                output.append(f"FID:{f.get('category_id')} C:{f.get('certified_value')}")
            
            output.append("WOS:")
            wos = await db_manager.db.work_orders.find({'project_id': str(proj['_id'])}).to_list(10)
            for w in wos:
                output.append(f"{w.get('wo_ref')}={w.get('status')}")
            
            with open("debug_output.txt", "w") as f:
                f.write(" | ".join(output))
            
        else:
            print("Project not found")
    finally:
        db_manager.disconnect()

if __name__ == "__main__":
    asyncio.run(check_project())
