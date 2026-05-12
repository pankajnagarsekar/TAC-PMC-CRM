import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os

async def check():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    # Try to find the db name from env or default
    db_name = os.environ.get("MONGODB_DB_NAME", "tac_pmc_crm")
    db = client[db_name]
    
    print(f"Checking database: {db_name}")
    
    cols = await db.list_collection_names()
    print(f"Collections: {cols}")
    
    counts = {}
    for col in cols:
        counts[col] = await db[col].count_documents({})
    
    for col, count in counts.items():
        print(f"  {col}: {count}")

    
    projects_count = counts.get("projects", 0)
    for col in ["projects", "work_orders", "payment_certificates", "financial_state", "project_budgets", "project_category_budgets", "code_master"]:
        if col in counts and counts[col] > 0:
            print(f"\n--- Sample Data: {col} ---")
            docs = await db[col].find({}).to_list(length=3)
            for d in docs:
                # Clean up ObjectId for printing
                d["_id"] = str(d["_id"])
                print(d)

    client.close()


if __name__ == "__main__":
    asyncio.run(check())
