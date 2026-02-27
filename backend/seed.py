#!/usr/bin/env python3
# Seed script for TAC-PMC database

import os
import asyncio
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.hash import bcrypt

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = "tac_pmc_crm"


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
            "name": "Admin User",
            "email": admin_email,
            "hashed_password": bcrypt.hash("Admin@1234"),
            "role": "Admin",
            "active_status": True,
            "organisation_id": org_id,
            "dpr_generation_permission": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
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
            "name": "Supervisor User",
            "email": supervisor_email,
            "hashed_password": bcrypt.hash("Super@1234"),
            "role": "Supervisor",
            "active_status": True,
            "organisation_id": org_id,
            "dpr_generation_permission": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        await db.users.insert_one(supervisor_doc)
        print(f"User '{supervisor_email}' - inserted")

    # 4. Project
    project_name = "Site Alpha"
    existing_project = await db.projects.find_one({"name": project_name})
    if existing_project:
        # Ensure existing project has all required fields
        update_fields = {}
        if "project_name" not in existing_project:
            update_fields["project_name"] = existing_project.get("name", project_name)
        if "project_code" not in existing_project:
            update_fields["project_code"] = "SA-001"
        if "project_id" not in existing_project:
            update_fields["project_id"] = str(existing_project["_id"])
        if update_fields:
            await db.projects.update_one({"_id": existing_project["_id"]}, {"$set": update_fields})
            print(f"Project '{project_name}' - updated with missing fields")
        else:
            print(f"Project '{project_name}' - skipped (already exists)")
    else:
        project_doc = {
            "name": project_name,
            "project_name": project_name,
            "project_code": "SA-001",
            "organisation_id": org_id,
            "status": "active",
            "created_at": datetime.utcnow(),
        }
        result = await db.projects.insert_one(project_doc)
        # Also set project_id to the string version of _id for consistent lookups
        await db.projects.update_one(
            {"_id": result.inserted_id},
            {"$set": {"project_id": str(result.inserted_id)}}
        )
        print(f"Project '{project_name}' - inserted")

    client.close()
    print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(seed())
