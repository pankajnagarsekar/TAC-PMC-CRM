#!/usr/bin/env python3
# Seed script for TAC-PMC database

import os
import asyncio
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.hash import bcrypt

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = "tac_pmc"


async def seed():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    # 1. Organisation
    org_name = "TAC-PMC Construction"
    existing_org = await db.organisations.find_one({"name": org_name})
    if existing_org:
        print(f"Organisation '{org_name}' - skipped (already exists)")
        org_id = str(existing_org["_id"])
    else:
        org_doc = {"name": org_name, "created_at": datetime.utcnow()}
        result = await db.organisations.insert_one(org_doc)
        org_id = str(result.inserted_id)
        print(f"Organisation '{org_name}' - inserted")

    # 2. Admin user
    admin_email = "admin@tacpmc.com"
    existing_admin = await db.users.find_one({"email": admin_email})
    if existing_admin:
        print(f"User '{admin_email}' - skipped (already exists)")
    else:
        admin_doc = {
            "email": admin_email,
            "hashed_password": bcrypt.hash("Admin@1234"),
            "role": "Admin",
            "is_active": True,
            "org_id": org_id,
            "created_at": datetime.utcnow(),
        }
        await db.users.insert_one(admin_doc)
        print(f"User '{admin_email}' - inserted")

    # 3. Supervisor user
    supervisor_email = "supervisor@tacpmc.com"
    existing_supervisor = await db.users.find_one({"email": supervisor_email})
    if existing_supervisor:
        print(f"User '{supervisor_email}' - skipped (already exists)")
    else:
        supervisor_doc = {
            "email": supervisor_email,
            "hashed_password": bcrypt.hash("Super@1234"),
            "role": "Supervisor",
            "is_active": True,
            "org_id": org_id,
            "created_at": datetime.utcnow(),
        }
        await db.users.insert_one(supervisor_doc)
        print(f"User '{supervisor_email}' - inserted")

    # 4. Project
    project_name = "Site Alpha"
    existing_project = await db.projects.find_one({"name": project_name})
    if existing_project:
        print(f"Project '{project_name}' - skipped (already exists)")
    else:
        project_doc = {
            "name": project_name,
            "org_id": org_id,
            "status": "active",
            "created_at": datetime.utcnow(),
        }
        await db.projects.insert_one(project_doc)
        print(f"Project '{project_name}' - inserted")

    client.close()
    print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(seed())
