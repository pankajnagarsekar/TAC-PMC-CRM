import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient


async def setup_indexes():
    # Load env from apps/api/.env or parent
    env_path = Path(__file__).resolve().parent / ".env"
    load_dotenv(env_path)

    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "tac_pmc_crm")

    print(f"Ensuring indexes in {db_name}...")
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    # NOTE: Most collections have repositories that handle their own indexes
    # Only add indices here for collections WITHOUT repositories
    # To avoid IndexKeySpecsConflict, let repositories create their own indices

    # Only created_at index for collections that need cursor pagination
    collections_for_pagination = [
        "work_orders",
        "payment_certificates",
        "cash_transactions",
    ]

    for coll in collections_for_pagination:
        try:
            print(f"Creating created_at index for {coll}...")
            await db[coll].create_index([("created_at", -1)], background=True)
        except Exception as e:
            print(f"Note: Could not create index for {coll}: {e}")

    # Specific audit indices
    try:
        await db.audit_logs.create_index([("timestamp", -1)], background=True)
        await db.audit_logs.create_index(
            [("entity_type", 1), ("entity_id", 1)], background=True
        )
    except Exception as e:
        print(f"Note: Could not create audit indexes: {e}")

    print("Indexes ensured successfully.")
    client.close()


if __name__ == "__main__":
    asyncio.run(setup_indexes())
