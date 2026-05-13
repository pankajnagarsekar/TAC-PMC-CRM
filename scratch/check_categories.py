import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables from apps/api/.env
load_dotenv("apps/api/.env")

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "tac_pmc_crm")

async def check_db():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    # 1. Get fund transfer categories
    cat_cursor = db.code_master.find({"budget_type": "fund_transfer"})
    cats = await cat_cursor.to_list(length=100)
    cat_codes = [c.get("code") for c in cats]
    
    print(f"Found {len(cats)} fund transfer categories:")
    for cat in cats:
        print(f"ID: {cat['_id']}, Code: {cat.get('code')}, Name: {cat.get('category_name') or cat.get('name')}, Type: {cat.get('budget_type')}")

    # 2. Check for Fund Allocations
    fa_cursor = db.fund_allocations.find({})
    fund_allocations = await fa_cursor.to_list(length=100)
    print(f"\nFound {len(fund_allocations)} fund allocations.")
    for fa in fund_allocations:
        print(f"Project: {fa.get('project_id')}, Category: {fa.get('category_id')}, Original: {fa.get('allocation_original')}, Remaining: {fa.get('allocation_remaining')}")

    # 3. Check for Payment Certificates linked to these categories
    pc_cursor = db.payment_certificates.find({"category_id": {"$in": cat_codes}})
    pcs = await pc_cursor.to_list(length=100)
    print(f"\nFound {len(pcs)} payment certificates linked to fund transfer categories.")
    for pc in pcs:
        print(f"PC Ref: {pc.get('pc_ref')}, Project: {pc.get('project_id')}, Category: {pc.get('category_id')}, Total: {pc.get('grand_total')}, Status: {pc.get('status')}")

    client.close()

if __name__ == "__main__":
    asyncio.run(check_db())
