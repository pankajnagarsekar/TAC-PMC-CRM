"""
Data Integrity Cleanup Script
Resolves duplicate DPR records and zombie PC orphans
"""

import asyncio
import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

# Fix Unicode encoding on Windows
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

load_dotenv()


class DataCleanupManager:
    def __init__(self, mongo_url: str, db_name: str):
        self.mongo_url = mongo_url
        self.db_name = db_name
        self.client = None
        self.db = None

    async def connect(self):
        """Connect to MongoDB"""
        self.client = AsyncIOMotorClient(self.mongo_url)
        self.db = self.client[self.db_name]
        await self.client.admin.command("ping")
        print(f"✓ Connected to MongoDB ({self.db_name})")

    async def cleanup_duplicate_dprs(self):
        """Remove duplicate DPR records with same project_id and dpr_date"""
        dpr_collection = self.db["dpr"]

        print("\n[1] Analyzing DPR duplicates...")

        # Find groups with duplicates
        pipeline = [
            {
                "$group": {
                    "_id": {"project_id": "$project_id", "dpr_date": "$dpr_date"},
                    "count": {"$sum": 1},
                    "ids": {"$push": "$_id"},
                    "latest_created": {"$max": "$created_at"},
                }
            },
            {"$match": {"count": {"$gt": 1}}},
        ]

        duplicates = await dpr_collection.aggregate(pipeline).to_list(None)

        if not duplicates:
            print("   ✓ No DPR duplicates found")
            return 0

        print(f"   Found {len(duplicates)} duplicate groups")

        total_removed = 0
        for dup_group in duplicates:
            key = dup_group["_id"]
            ids = dup_group["ids"]
            count = dup_group["count"]

            # Keep the most recent, delete others
            docs_for_group = await dpr_collection.find(
                {"_id": {"$in": ids}}, sort=[("created_at", -1)]
            ).to_list(None)

            keep_id = docs_for_group[0]["_id"]
            remove_ids = [d["_id"] for d in docs_for_group[1:]]

            # Delete duplicates
            result = await dpr_collection.delete_many({"_id": {"$in": remove_ids}})
            total_removed += result.deleted_count

            print(f"   ✓ {key}: Kept 1, removed {len(remove_ids)}")

        print(f"   Total DPR records removed: {total_removed}")
        return total_removed

    async def cleanup_zombie_pcs(self):
        """Remove PC records with no matching project"""
        pc_collection = self.db["payment_certificates"]
        project_collection = self.db["projects"]

        print("\n[2] Analyzing zombie PCs...")

        # Get all PCs
        all_pcs = await pc_collection.find({}).to_list(None)
        print(f"   Total PCs in database: {len(all_pcs)}")

        # Check which projects exist
        zombie_ids = []
        for pc in all_pcs:
            project_id = pc.get("project_id")
            if project_id:
                project = await project_collection.find_one({"_id": project_id})
                if not project:
                    zombie_ids.append(pc["_id"])

        if not zombie_ids:
            print("   ✓ No zombie PCs found")
            return 0

        print(f"   Found {len(zombie_ids)} zombie PC records (orphaned)")

        # Delete zombies
        result = await pc_collection.delete_many({"_id": {"$in": zombie_ids}})

        print(f"   ✓ Removed {result.deleted_count} zombie PC records")
        return result.deleted_count

    async def verify_indexes(self):
        """Verify indexes can be created"""
        print("\n[3] Verifying index creation...")

        dpr_collection = self.db["dpr"]

        try:
            # Drop the problematic index
            await dpr_collection.drop_index("project_id_1_dpr_date_1")
            print("   ✓ Dropped old DPR index")
        except Exception as e:
            if "index not found" in str(e):
                print("   ✓ Index already absent")
            else:
                raise

        # Recreate the index
        await dpr_collection.create_index([("project_id", 1), ("dpr_date", 1)])
        print("   ✓ Recreated DPR unique index (project_id, dpr_date)")

    async def generate_report(self):
        """Generate final integrity report"""
        print("\n[4] Generating integrity report...")

        pc_count = await self.db["payment_certificates"].count_documents({})
        dpr_count = await self.db["dpr"].count_documents({})
        project_count = await self.db["projects"].count_documents({})

        print(f"   Projects: {project_count}")
        print(f"   PCs: {pc_count}")
        print(f"   DPRs: {dpr_count}")
        print("\n✓ Cleanup complete!")

    async def close(self):
        """Close connection"""
        if self.client:
            self.client.close()


async def main():
    mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.getenv("DB_NAME", "tac_pmc_crm")

    cleanup = DataCleanupManager(mongo_url, db_name)

    try:
        await cleanup.connect()

        # Execute cleanup
        dpr_removed = await cleanup.cleanup_duplicate_dprs()
        pc_removed = await cleanup.cleanup_zombie_pcs()
        await cleanup.verify_indexes()
        await cleanup.generate_report()

        print(f"\nSummary:")
        print(f"  - DPR duplicates removed: {dpr_removed}")
        print(f"  - Zombie PCs removed: {pc_removed}")

    finally:
        await cleanup.close()


if __name__ == "__main__":
    asyncio.run(main())
