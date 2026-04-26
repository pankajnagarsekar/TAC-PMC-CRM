#!/usr/bin/env python3
# Seed script for TAC-PMC database
# Creates organisation and test users for both local development and CI/CD testing

import asyncio
import os
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient

from app.modules.identity.application.auth_service import AuthService

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = "tac_pmc_crm"


async def seed():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    auth_service = AuthService(db)

    print("🌱 Starting database seed...\n")

    # 1. Organisation
    org_name = "TAC-PMC Construction"
    existing_org = await db.organisations.find_one({"name": org_name})
    if existing_org:
        print(f"✓ Organisation '{org_name}' - already exists")
        org_id = str(existing_org["_id"])
    else:
        result = await db.organisations.insert_one(
            {"name": org_name, "created_at": datetime.now(timezone.utc)}
        )
        org_id = str(result.inserted_id)
        print(f"✓ Organisation '{org_name}' - created")

    print()

    # 2. Test Users for E2E Testing
    test_users = [
        {
            "name": "Admin User (Primary)",
            "email": "admin@tacpmc.com",
            "password": "Admin@1234",
            "role": "Admin",
        },
        {
            "name": "Amit - Admin",
            "email": "amit@thirdangleconcepts.com",
            "password": "Admin@1234",
            "role": "Admin",
        },
        {
            "name": "Amit - Admin (Singular)",
            "email": "amit@thirdangleconcept.com",
            "password": "Admin@1234",
            "role": "Admin",
        },
        {
            "name": "Client Test User",
            "email": "client@tacpmc.com",
            "password": "Client@1234",
            "role": "Client",
        },
        {
            "name": "Supervisor Test User",
            "email": "supervisor@tacpmc.com",
            "password": "Supervisor@1234",
            "role": "Supervisor",
        },
    ]

    print("Creating test users for E2E tests:")
    for user_data in test_users:
        existing_user = await db.users.find_one({"email": user_data["email"]})
        if existing_user:
            print(f"  ✓ {user_data['email']} - already exists")
        else:
            user_doc = {
                "name": user_data["name"],
                "email": user_data["email"],
                "hashed_password": auth_service.hash_password(user_data["password"]),
                "role": user_data["role"],
                "active_status": True,
                "organisation_id": org_id,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
            await db.users.insert_one(user_doc)
            print(f"  ✓ {user_data['email']} - created")

    print()

    # 3. Summary
    user_count = await db.users.count_documents({})
    print(f"✅ Seed complete! Database contains {user_count} test users")
    print("\nTest Credentials:")
    print("  Admin:      admin@tacpmc.com / Admin@1234")
    print("  Admin Alt:  amit@thirdangleconcept.com / Admin@1234")
    print("  Client:     client@tacpmc.com / Client@1234")
    print("  Supervisor: supervisor@tacpmc.com / Supervisor@1234")

    client.close()


if __name__ == "__main__":
    asyncio.run(seed())
