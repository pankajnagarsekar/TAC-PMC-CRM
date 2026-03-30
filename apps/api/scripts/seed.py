#!/usr/bin/env python3
# Seed script for TAC-PMC database

import asyncio
import os
from datetime import datetime, timezone

from bson import Decimal128
from motor.motor_asyncio import AsyncIOMotorClient

from app.services.auth_service import AuthService

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = "tac_pmc_crm"


async def seed():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    auth_service = AuthService(db)

    # 1. Organisation
    org_name = "TAC-PMC Construction"
    existing_org = await db.organisations.find_one({"name": org_name})
    if existing_org:
        print(f"Organisation '{org_name}' - skipped")
        org_id = str(existing_org["_id"])
    else:
        result = await db.organisations.insert_one(
            {"name": org_name, "created_at": datetime.now(timezone.utc)}
        )
        org_id = str(result.inserted_id)
        print(f"Organisation '{org_name}' - inserted")

    # 2. Admin user
    admin_email = "admin@tacpmc.com"
    existing_admin = await db.users.find_one({"email": admin_email})
    if not existing_admin:
        admin_doc = {
            "name": "Admin User",
            "email": admin_email,
            "hashed_password": auth_service.hash_password("Admin@1234"),
            "role": "Admin",
            "active_status": True,
            "organisation_id": org_id,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        await db.users.insert_one(admin_doc)
        print(f"User '{admin_email}' - inserted")

    client.close()
    print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(seed())
