import sys
from pymongo import MongoClient
import os

# Database connection
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "tac_pmc_crm")

client = MongoClient(MONGO_URL)
db = client[DB_NAME]

def fix_petty_cash_categories():
    print(f"Connecting to {MONGO_URL}, DB: {DB_NAME}")
    
    # Use regex to find Petty Cash and Site Overhead categories
    # This matches common variations (Petty Cash, PettyCash, Site Overhead, Site Ovh)
    query = {
        "category_name": {
            "$regex": r"(Petty|Overhead|Site\s*Ovh)",
            "$options": "i"
        }
    }
    
    categories = list(db.code_master.find(query))
    if not categories:
        print("No matching categories found in code_master.")
        return

    print(f"Found {len(categories)} categories to update.")
    
    updated_count = 0
    for cat in categories:
        if cat.get("budget_type") != "fund_transfer":
            res = db.code_master.update_one(
                {"_id": cat["_id"]},
                {"$set": {"budget_type": "fund_transfer"}}
            )
            updated_count += res.modified_count
            print(f"Updated: {cat.get('category_name')} ({cat.get('code')}) -> budget_type: fund_transfer")
        else:
            print(f"Already Correct: {cat.get('category_name')} ({cat.get('code')})")

    print(f"\nSuccessfully updated {updated_count} records.")

if __name__ == "__main__":
    try:
        fix_petty_cash_categories()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
