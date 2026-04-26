"""
Migration Script: project_budgets -> project_category_budgets

This script:
1. Copies data from 'project_budgets' collection to 'project_category_budgets'
2. Renames 'code_id' field to 'category_id' in the migrated documents
3. Creates the new indexes
4. Optionally drops the old collection

Run with: python migrate_budgets.py
"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient


async def migrate():
    env_path = Path(__file__).resolve().parent / ".env"
    load_dotenv(env_path)

    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "tac_pmc_crm")

    print(f"Connecting to {db_name}...")
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    # Check if source collection exists
    source_exists = await db.project_budgets.count_documents({})
    if source_exists == 0:
        print("No documents in 'project_budgets'. Nothing to migrate.")
        client.close()
        return

    # Check if target collection already has data
    target_exists = await db.project_category_budgets.count_documents({})
    if target_exists > 0:
        print(f"'project_category_budgets' already has {target_exists} documents.")
        response = input("Do you want to skip migration? (y/n): ")
        if response.lower() == "y":
            client.close()
            return

    print(f"Found {source_exists} documents in 'project_budgets'.")

    # Step 1: Copy and rename fields
    print("Step 1: Migrating documents...")
    cursor = db.project_budgets.find({})

    migrated_count = 0
    async for doc in cursor:
        # Create new document with category_id instead of code_id
        # Map old field names to new schema
        new_doc = {
            "project_id": doc.get("project_id"),
            "category_id": doc.get("code_id"),  # Rename field
            "original_budget": doc.get(
                "approved_budget_amount", 0
            ),  # Legacy field mapping
            "committed_amount": doc.get("committed_amount", 0),
            "remaining_budget": doc.get("remaining_budget", 0),
            "description": doc.get("description"),
            "version": doc.get("version", 1),
            "created_at": doc.get("created_at"),
            "updated_at": doc.get("updated_at"),
            # Preserve original _id for reference, but as new field
            "original_id": doc.get("_id"),
        }

        await db.project_category_budgets.insert_one(new_doc)
        migrated_count += 1

    print(f"Migrated {migrated_count} documents.")

    # Step 2: Create new indexes
    print("Step 2: Creating indexes...")

    # Drop old index if exists
    try:
        await db.project_budgets.drop_index("idx_budget_project_code")
        print("Dropped old index 'idx_budget_project_code'")
    except Exception as e:
        print(f"Note: Could not drop old index (may not exist): {e}")

    # Create new compound index
    await db.project_category_budgets.create_index(
        [("project_id", 1), ("category_id", 1)],
        unique=True,
        name="idx_budget_project_category",
    )
    print("Created index 'idx_budget_project_category'")

    # Step 3: Update financial_state documents to use category_id
    print("Step 3: Updating financial_state collection...")
    result = await db.financial_state.update_many(
        {"code_id": {"$exists": True}}, [{"$set": {"category_id": "$code_id"}}]
    )
    print(f"Updated {result.modified_count} financial_state documents.")

    # Optionally remove old code_id field from financial_state
    # (uncomment if you want to remove the old field)
    # await db.financial_state.update_many({}, {"$unset": {"code_id": ""}})

    print("\nMigration completed successfully!")
    print(f"New collection: 'project_category_budgets' with {migrated_count} documents")
    print("Verify data before dropping 'project_budgets' collection!")

    response = input("\nDrop old 'project_budgets' collection? (y/n): ")
    if response.lower() == "y":
        await db.project_budgets.drop()
        print("Dropped 'project_budgets' collection.")
    else:
        print("Kept 'project_budgets' collection. Drop manually when ready.")

    client.close()


if __name__ == "__main__":
    asyncio.run(migrate())
