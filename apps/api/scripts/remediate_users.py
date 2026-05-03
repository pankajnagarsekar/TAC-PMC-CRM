import asyncio
import os
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

async def remediate_users():
    # Load settings manually for script context
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "tac_pmc_crm")

    print(f"Connecting to {db_name} at {mongo_url}...")
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    # 1. Identify duplicates
    pipeline = [
        {"$group": {
            "_id": "$email",
            "count": {"$sum": 1},
            "ids": {"$push": "$_id"}
        }},
        {"$match": {"count": {"$gt": 1}}}
    ]

    duplicates = await db.users.aggregate(pipeline).to_list(None)
    
    if not duplicates:
        print("No duplicate user emails found.")
    else:
        print(f"Found {len(duplicates)} duplicate emails. Remediating...")
        for dup in duplicates:
            email = dup["_id"]
            ids = dup["ids"]
            # Keep the first one, delete the rest
            keep_id = ids[0]
            delete_ids = ids[1:]
            print(f"  Email: {email} | Keeping: {keep_id} | Deleting: {delete_ids}")
            
            # Delete duplicates
            await db.users.delete_many({"_id": {"$in": delete_ids}})
            
            # Clean up mappings if any
            await db.user_project_map.delete_many({"user_id": {"$in": delete_ids}})

    # 2. Enforce Unique Index
    print("Enforcing unique index on email...")
    try:
        # Drop if exists without unique to be safe
        await db.users.drop_index("email_1")
    except:
        pass
        
    try:
        await db.users.create_index([("email", 1)], unique=True)
        print("Unique email index created successfully.")
    except Exception as e:
        print(f"CRITICAL ERROR: Could not create unique index: {e}")

    client.close()
    print("Remediation complete.")

if __name__ == "__main__":
    asyncio.run(remediate_users())
