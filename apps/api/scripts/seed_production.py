#!/usr/bin/env python3
"""
Production Seed Script — TAC-PMC-CRM
=====================================

Creates minimal, production-ready data:
- 1 Organisation: TAC-PMC
- 3 Users: Admin, Supervisor, Client
- 1 Project: Majorda Villa (with 45 construction tasks)
- Financial codes and categories

Run: python seed_production.py
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from apps/api/
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Add app directory to path
app_dir = Path(__file__).parent.parent / "app"
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir.parent))

from bson import ObjectId  # noqa: E402
from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402
from passlib.context import CryptContext  # noqa: E402

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "tac_pmc_crm")

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def seed_production():
    """Seed production data."""
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    try:
        print("\n" + "=" * 70)
        print("TAC-PMC-CRM PRODUCTION SEED")
        print("=" * 70)

        # 1. ORGANISATION
        print("\n[STEP 1] Creating Organisation...")
        org = await db.organisations.find_one({"name": "TAC-PMC"})
        if org:
            org_id = str(org["_id"])
            print(f"  Organisation exists: {org_id}")
        else:
            org_result = await db.organisations.insert_one(
                {
                    "name": "TAC-PMC",
                    "created_at": datetime.now(timezone.utc),
                }
            )
            org_id = str(org_result.inserted_id)
            print(f"  Created: {org_id}")

        # 2. USERS (3 only: admin, supervisor, client)
        print("\n[STEP 2] Creating Users (3: admin, supervisor, client)...")
        users_config = [
            {
                "email": "amit@thirdangleconcept.com",
                "name": "Amit (Third Angle)",
                "role": "Admin",
                "password": "Admin@1234",
            },
            {
                "email": "admin@tacpmc.com",
                "name": "Administrator",
                "role": "Admin",
                "password": "Admin@1234",
            },
            {
                "email": "supervisor@tacpmc.com",
                "name": "Project Supervisor",
                "role": "Supervisor",
                "password": "Supervisor@1234",
            },
            {
                "email": "client@tacpmc.com",
                "name": "Client Representative",
                "role": "Other",
                "password": "Client@1234",
            },
        ]

        user_map = {}
        for user_cfg in users_config:
            existing = await db.users.find_one({"email": user_cfg["email"]})
            if existing:
                user_map[user_cfg["role"]] = str(existing["_id"])
                print(f"  {user_cfg['role']}: {user_cfg['email']} (exists)")
            else:
                user_result = await db.users.insert_one(
                    {
                        "email": user_cfg["email"],
                        "name": user_cfg["name"],
                        "hashed_password": pwd_ctx.hash(user_cfg["password"]),
                        "role": user_cfg["role"],
                        "active_status": True,
                        "organisation_id": org_id,
                        "created_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc),
                    }
                )
                user_map[user_cfg["role"]] = str(user_result.inserted_id)
                print(f"  {user_cfg['role']}: {user_cfg['email']} (created)")

        # 3. FINANCIAL CODES & MASTER DATA
        print("\n[STEP 3] Creating Financial Codes & Master Data...")
        codes = [
            {"code": "CIV", "description": "Civil Works", "category": "Construction"},
            {"code": "PLB", "description": "Plumbing Works", "category": "Services"},
            {"code": "ELC", "description": "Electrical Works", "category": "Services"},
            {"code": "DWG", "description": "Doors, Windows & Glazing", "category": "Finishing"},
            {"code": "SWP", "description": "Swimming Pool Works", "category": "Specialized"},
            {"code": "HVC", "description": "HVAC / Air Conditioning", "category": "Services"},
            {"code": "FIN", "description": "Finishing Works", "category": "Finishing"},
            {"code": "LAN", "description": "Landscapping & External Works", "category": "External"},
            {"code": "FAB", "description": "Metal & Steel Fabrication", "category": "Construction"},
            {"code": "CSA", "description": "Client Supplied Assets", "category": "Supply"},
            {"code": "PRF", "description": "Professional Fees", "category": "Consultancy"},
            {"code": "STC", "description": "Approvals & Statutory Charges", "category": "Legal"},
            {"code": "PTC", "description": "Petty Cash / Running Expenses", "category": "Admin"},
            {"code": "CON", "description": "Contingency", "category": "Risk"},
        ]

        print("\n[STEP 3.5] Creating Client & Vendor...")
        client_doc = await db.clients.find_one({"name": "Mr. Sanjay Rao"})
        if not client_doc:
            client_result = await db.clients.insert_one({
                "organisation_id": org_id,
                "name": "Mr. Sanjay Rao",
                "address": "Majorda",
                "city": "South Goa",
                "state": "Goa",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            })
            client_id = str(client_result.inserted_id)
        else:
            client_id = str(client_doc["_id"])
            
        vendors_to_create = ["Default Vendor", "SS Construction", "Suraj Electrician", "Rajesh Construction", "CDSP Global"]
        vendor_map = {}
        for v_name in vendors_to_create:
            v_doc = await db.vendors.find_one({"name": v_name})
            if not v_doc:
                result = await db.vendors.insert_one({
                    "organisation_id": org_id,
                    "name": v_name,
                    "active_status": True,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc)
                })
                vendor_map[v_name] = str(result.inserted_id)
            else:
                vendor_map[v_name] = str(v_doc["_id"])
        vendor_id = vendor_map["Default Vendor"]

        code_map = {}
        for code in codes:
            existing_master = await db.code_master.find_one({"code": code["code"]})
            if not existing_master:
                result = await db.code_master.insert_one(
                    {
                        "code": code["code"],
                        "code_short": code["code"],
                        "code_description": code["description"],
                        "category_name": code["category"],
                        "organisation_id": org_id,
                        "active_status": True,
                        "created_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc),
                    }
                )
                code_map[code["code"]] = str(result.inserted_id)
            else:
                code_map[code["code"]] = str(existing_master["_id"])
                # update fields if exists
                await db.code_master.update_one({"_id": existing_master["_id"]}, {"$set": {"code_description": code["description"], "category_name": code["category"], "active_status": True}})
        print(f"  Created/verified {len(codes)} financial codes in code_master")

        # 4. PROJECT: MAJORDA VILLA
        print("\n[STEP 4] Creating Majorda Villa Project...")
        project = await db.projects.find_one({"project_name": "Majorda Villa - Civil Works"})
        
        # Consistent realistic budget values from MIS
        original_budget = 70000000 # 70M Cr
        remaining_budget = 68465000 # Adjusted
        
        if project:
            project_id = str(project["_id"])
            print(f"  Project exists: {project_id}")
            # Ensure budget is updated
            await db.projects.update_one(
                {"_id": project["_id"]},
                {"$set": {
                    "master_original_budget": original_budget, 
                    "master_remaining_budget": remaining_budget,
                    "completion_percentage": 18,
                    "client_id": client_id,
                    "address": "Majorda",
                    "city": "South Goa",
                    "state": "Goa"
                }}
            )
        else:
            project_oid = ObjectId()
            await db.projects.insert_one(
                {
                    "_id": project_oid,
                    "project_code": "MV-01",
                    "project_name": "Majorda Villa - Civil Works",
                    "client_id": client_id,
                    "status": "active",
                    "address": "Majorda",
                    "city": "South Goa",
                    "state": "Goa",
                    "project_retention_percentage": 0.0,
                    "project_cgst_percentage": 9.0,
                    "project_sgst_percentage": 9.0,
                    "organisation_id": org_id,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                    "master_original_budget": original_budget,
                    "master_remaining_budget": remaining_budget,
                    "completion_percentage": 18,
                    "threshold_petty": 0.0,
                    "threshold_ovh": 0.0,
                    "version": 1,
                }
            )
            project_id = str(project_oid)
            print(f"  Created: {project_id}")

        # 5. SCHEDULER TASKS
        print("\n[STEP 5] Creating Project Scheduler with 45 tasks...")

        majorda_tasks = [
            {
                "task_id": 0,
                "task_name": "Majorda Villa - Civil Works",
                "baseline_duration": 246,
                "baseline_start": "2026-02-20",
                "baseline_finish": "2026-12-15",
                "scheduled_duration": 251,
                "scheduled_start": "2026-02-20",
                "scheduled_finish": "2026-12-15",
                "actual_start": "2026-02-20",
                "actual_finish": None,
                "percent_complete": 18,
                "task_status": "in_progress",
                "dependencies": [],
                "task_type": "summary",
                "wo_value": 10107425.95,
            },
            {
                "task_id": 1,
                "task_name": "Start",
                "baseline_duration": 0,
                "baseline_start": "2026-02-20",
                "baseline_finish": "2026-02-20",
                "scheduled_duration": 0,
                "scheduled_start": "2026-02-20",
                "scheduled_finish": "2026-02-20",
                "actual_start": "2026-02-20",
                "actual_finish": "2026-02-20",
                "percent_complete": 100,
                "task_status": "completed",
                "dependencies": [],
                "task_type": "milestone",
            },
            {
                "task_id": 2,
                "task_name": "Mobilization at Site",
                "baseline_duration": 1,
                "baseline_start": "2026-02-20",
                "baseline_finish": "2026-02-20",
                "scheduled_duration": 1,
                "scheduled_start": "2026-02-20",
                "scheduled_finish": "2026-02-20",
                "actual_start": "2026-02-20",
                "actual_finish": "2026-02-20",
                "percent_complete": 100,
                "task_status": "completed",
                "dependencies": [1],
                "task_type": "task",
            },
            {
                "task_id": 3,
                "task_name": "Surveying & Layout",
                "baseline_duration": 1,
                "baseline_start": "2026-02-21",
                "baseline_finish": "2026-02-21",
                "scheduled_duration": 1,
                "scheduled_start": "2026-02-21",
                "scheduled_finish": "2026-02-21",
                "actual_start": "2026-02-21",
                "actual_finish": "2026-02-21",
                "percent_complete": 100,
                "task_status": "completed",
                "dependencies": [2],
                "task_type": "task",
            },
            {
                "task_id": 4,
                "task_name": "Approval for MEP - UGT, ST, SP",
                "baseline_duration": 12,
                "baseline_start": "2026-02-23",
                "baseline_finish": "2026-03-09",
                "scheduled_duration": 12,
                "scheduled_start": "2026-02-23",
                "scheduled_finish": "2026-03-09",
                "actual_start": "2026-02-23",
                "actual_finish": "2026-03-09",
                "percent_complete": 100,
                "task_status": "completed",
                "dependencies": [3],
                "task_type": "task",
            },
            {
                "task_id": 5,
                "task_name": "Approval for Swimming Pool",
                "baseline_duration": 12,
                "baseline_start": "2026-02-23",
                "baseline_finish": "2026-03-09",
                "scheduled_duration": 12,
                "scheduled_start": "2026-02-23",
                "scheduled_finish": "2026-03-09",
                "actual_start": "2026-02-23",
                "actual_finish": "2026-03-09",
                "percent_complete": 100,
                "task_status": "completed",
                "dependencies": [3],
                "task_type": "task",
            },
            {
                "task_id": 6,
                "task_name": "Excavation in Foundation Pits",
                "baseline_duration": 14,
                "baseline_start": "2026-02-21",
                "baseline_finish": "2026-03-10",
                "scheduled_duration": 14,
                "scheduled_start": "2026-02-21",
                "scheduled_finish": "2026-03-10",
                "actual_start": "2026-02-21",
                "actual_finish": "2026-03-10",
                "percent_complete": 100,
                "task_status": "completed",
                "dependencies": [3],
                "task_type": "task",
                "is_critical": True,
            },
            {
                "task_id": 7,
                "task_name": "Railing",
                "baseline_duration": 2,
                "baseline_start": "2026-03-10",
                "baseline_finish": "2026-03-11",
                "scheduled_duration": 2,
                "scheduled_start": "2026-03-10",
                "scheduled_finish": "2026-03-11",
                "actual_start": "2026-03-10",
                "actual_finish": "2026-03-11",
                "percent_complete": 100,
                "task_status": "completed",
                "dependencies": [6],
                "task_type": "task",
            },
            {
                "task_id": 8,
                "task_name": "Rubble Soling",
                "baseline_duration": 2,
                "baseline_start": "2026-03-11",
                "baseline_finish": "2026-03-12",
                "scheduled_duration": 2,
                "scheduled_start": "2026-03-11",
                "scheduled_finish": "2026-03-12",
                "actual_start": "2026-03-11",
                "actual_finish": "2026-03-12",
                "percent_complete": 100,
                "task_status": "completed",
                "dependencies": [7],
                "task_type": "task",
            },
            {
                "task_id": 9,
                "task_name": "PCC in Foundation",
                "baseline_duration": 2,
                "baseline_start": "2026-03-13",
                "baseline_finish": "2026-03-14",
                "scheduled_duration": 2,
                "scheduled_start": "2026-03-13",
                "scheduled_finish": "2026-03-14",
                "actual_start": "2026-03-13",
                "actual_finish": "2026-03-14",
                "percent_complete": 100,
                "task_status": "completed",
                "dependencies": [8],
                "task_type": "task",
            },
            {
                "task_id": 10,
                "task_name": "Marking for Foundation",
                "baseline_duration": 2,
                "baseline_start": "2026-03-16",
                "baseline_finish": "2026-03-17",
                "scheduled_duration": 1,
                "scheduled_start": "2026-03-13",
                "scheduled_finish": "2026-03-13",
                "actual_start": "2026-03-13",
                "actual_finish": "2026-03-13",
                "percent_complete": 100,
                "task_status": "completed",
                "dependencies": [9],
                "task_type": "task",
            },
            {
                "task_id": 11,
                "task_name": "Marking by Carpenter & Box Fitting",
                "baseline_duration": 1,
                "baseline_start": "2026-03-17",
                "baseline_finish": "2026-03-17",
                "scheduled_duration": 1,
                "scheduled_start": "2026-03-14",
                "scheduled_finish": "2026-03-14",
                "actual_start": "2026-03-14",
                "actual_finish": "2026-03-14",
                "percent_complete": 100,
                "task_status": "completed",
                "dependencies": [10],
                "task_type": "task",
            },
            {
                "task_id": 12,
                "task_name": "Steel Tying Column Erection",
                "baseline_duration": 2,
                "baseline_start": "2026-03-18",
                "baseline_finish": "2026-03-19",
                "scheduled_duration": 7,
                "scheduled_start": "2026-03-17",
                "scheduled_finish": "2026-03-24",
                "actual_start": "2026-03-17",
                "actual_finish": "2026-03-24",
                "percent_complete": 100,
                "task_status": "completed",
                "dependencies": [11],
                "task_type": "task",
                "is_critical": True,
            },
            {
                "task_id": 13,
                "task_name": "Steel Checking - Inspection Hold Point",
                "baseline_duration": 1,
                "baseline_start": "2026-03-20",
                "baseline_finish": "2026-03-20",
                "scheduled_duration": 1,
                "scheduled_start": "2026-03-25",
                "scheduled_finish": "2026-03-25",
                "actual_start": "2026-03-25",
                "actual_finish": "2026-03-25",
                "percent_complete": 100,
                "task_status": "completed",
                "dependencies": [12],
                "task_type": "task",
            },
            {
                "task_id": 14,
                "task_name": "Casting of Foundation",
                "baseline_duration": 1,
                "baseline_start": "2026-03-21",
                "baseline_finish": "2026-03-21",
                "scheduled_duration": 1,
                "scheduled_start": "2026-03-27",
                "scheduled_finish": "2026-03-27",
                "actual_start": "2026-03-27",
                "actual_finish": "2026-03-27",
                "percent_complete": 100,
                "task_status": "completed",
                "dependencies": [13],
                "task_type": "task",
                "is_critical": True,
            },
            {
                "task_id": 15,
                "task_name": "Starter for Column",
                "baseline_duration": 1,
                "baseline_start": "2026-03-23",
                "baseline_finish": "2026-03-23",
                "scheduled_duration": 1,
                "scheduled_start": "2026-03-23",
                "scheduled_finish": "2026-03-23",
                "actual_start": None,
                "actual_finish": None,
                "percent_complete": 0,
                "task_status": "draft",
                "dependencies": [14],
                "task_type": "task",
            },
            {
                "task_id": 16,
                "task_name": "Casting for Column",
                "baseline_duration": 1,
                "baseline_start": "2026-03-23",
                "baseline_finish": "2026-03-23",
                "scheduled_duration": 1,
                "scheduled_start": "2026-03-23",
                "scheduled_finish": "2026-03-23",
                "actual_start": None,
                "actual_finish": None,
                "percent_complete": 0,
                "task_status": "draft",
                "dependencies": [15],
                "task_type": "task",
            },
            {
                "task_id": 17,
                "task_name": "Column Shuttering & Casting - 1st Set",
                "baseline_duration": 3,
                "baseline_start": "2026-03-24",
                "baseline_finish": "2026-03-26",
                "scheduled_duration": 3,
                "scheduled_start": "2026-03-24",
                "scheduled_finish": "2026-03-26",
                "actual_start": None,
                "actual_finish": None,
                "percent_complete": 0,
                "task_status": "draft",
                "dependencies": [16],
                "task_type": "task",
            },
            {
                "task_id": 18,
                "task_name": "Column Shuttering & Casting - 2nd Set",
                "baseline_duration": 4,
                "baseline_start": "2026-03-27",
                "baseline_finish": "2026-03-31",
                "scheduled_duration": 4,
                "scheduled_start": "2026-03-27",
                "scheduled_finish": "2026-03-31",
                "actual_start": None,
                "actual_finish": None,
                "percent_complete": 0,
                "task_status": "draft",
                "dependencies": [17],
                "task_type": "task",
            },
            {
                "task_id": 19,
                "task_name": "Excavation for Foundation Masonry",
                "baseline_duration": 3,
                "baseline_start": "2026-04-01",
                "baseline_finish": "2026-04-03",
                "scheduled_duration": 3,
                "scheduled_start": "2026-04-01",
                "scheduled_finish": "2026-04-03",
                "actual_start": None,
                "actual_finish": None,
                "percent_complete": 0,
                "task_status": "draft",
                "dependencies": [18],
                "task_type": "task",
            },
            {
                "task_id": 20,
                "task_name": "Rubble Soling PCC in Foundation",
                "baseline_duration": 2,
                "baseline_start": "2026-04-04",
                "baseline_finish": "2026-04-06",
                "scheduled_duration": 2,
                "scheduled_start": "2026-04-04",
                "scheduled_finish": "2026-04-06",
                "actual_start": None,
                "actual_finish": None,
                "percent_complete": 0,
                "task_status": "draft",
                "dependencies": [19],
                "task_type": "task",
            },
            {
                "task_id": 21,
                "task_name": "Foundation Masonry",
                "baseline_duration": 5,
                "baseline_start": "2026-04-07",
                "baseline_finish": "2026-04-11",
                "scheduled_duration": 5,
                "scheduled_start": "2026-04-07",
                "scheduled_finish": "2026-04-11",
                "actual_start": None,
                "actual_finish": None,
                "percent_complete": 0,
                "task_status": "draft",
                "dependencies": [20],
                "task_type": "task",
            },
            {
                "task_id": 22,
                "task_name": "Backfilling in Plinth excavation for Pool",
                "baseline_duration": 3,
                "baseline_start": "2026-04-13",
                "baseline_finish": "2026-04-15",
                "scheduled_duration": 3,
                "scheduled_start": "2026-04-13",
                "scheduled_finish": "2026-04-15",
                "actual_start": None,
                "actual_finish": None,
                "percent_complete": 0,
                "task_status": "draft",
                "dependencies": [21],
                "task_type": "task",
            },
            {
                "task_id": 23,
                "task_name": "Compaction for Plinth Pool Soling & PCC",
                "baseline_duration": 3,
                "baseline_start": "2026-04-16",
                "baseline_finish": "2026-04-18",
                "scheduled_duration": 3,
                "scheduled_start": "2026-04-16",
                "scheduled_finish": "2026-04-18",
                "actual_start": None,
                "actual_finish": None,
                "percent_complete": 0,
                "task_status": "draft",
                "dependencies": [22],
                "task_type": "task",
            },
            {
                "task_id": 24,
                "task_name": "Soling & PCC for Plinth Beam",
                "baseline_duration": 1,
                "baseline_start": "2026-04-20",
                "baseline_finish": "2026-04-20",
                "scheduled_duration": 1,
                "scheduled_start": "2026-04-20",
                "scheduled_finish": "2026-04-20",
                "actual_start": None,
                "actual_finish": None,
                "percent_complete": 0,
                "task_status": "draft",
                "dependencies": [23],
                "task_type": "task",
            },
            {
                "task_id": 25,
                "task_name": "Steel for Plinth Beam",
                "baseline_duration": 4,
                "baseline_start": "2026-04-21",
                "baseline_finish": "2026-04-24",
                "scheduled_duration": 4,
                "scheduled_start": "2026-04-21",
                "scheduled_finish": "2026-04-24",
                "actual_start": None,
                "actual_finish": None,
                "percent_complete": 0,
                "task_status": "draft",
                "dependencies": [24],
                "task_type": "task",
            },
            {
                "task_id": 26,
                "task_name": "Shuttering for Plinth Beam",
                "baseline_duration": 5,
                "baseline_start": "2026-04-25",
                "baseline_finish": "2026-04-30",
                "scheduled_duration": 5,
                "scheduled_start": "2026-04-25",
                "scheduled_finish": "2026-04-30",
                "actual_start": None,
                "actual_finish": None,
                "percent_complete": 0,
                "task_status": "draft",
                "dependencies": [25],
                "task_type": "task",
            },
            {
                "task_id": 27,
                "task_name": "Casting of Plinth Beam",
                "baseline_duration": 2,
                "baseline_start": "2026-05-01",
                "baseline_finish": "2026-05-02",
                "scheduled_duration": 2,
                "scheduled_start": "2026-05-01",
                "scheduled_finish": "2026-05-02",
                "actual_start": None,
                "actual_finish": None,
                "percent_complete": 0,
                "task_status": "draft",
                "dependencies": [26],
                "task_type": "task",
            },
            {
                "task_id": 28,
                "task_name": "Backfilling in Plinth",
                "baseline_duration": 4,
                "baseline_start": "2026-05-01",
                "baseline_finish": "2026-05-05",
                "scheduled_duration": 4,
                "scheduled_start": "2026-05-01",
                "scheduled_finish": "2026-05-05",
                "actual_start": None,
                "actual_finish": None,
                "percent_complete": 0,
                "task_status": "draft",
                "dependencies": [27],
                "task_type": "task",
            },
            {
                "task_id": 29,
                "task_name": "Rubble Soling",
                "baseline_duration": 4,
                "baseline_start": "2026-05-06",
                "baseline_finish": "2026-05-09",
                "scheduled_duration": 4,
                "scheduled_start": "2026-05-06",
                "scheduled_finish": "2026-05-09",
                "actual_start": None,
                "actual_finish": None,
                "percent_complete": 0,
                "task_status": "draft",
                "dependencies": [28],
                "task_type": "task",
            },
            {
                "task_id": 30,
                "task_name": "PCC in Plinth",
                "baseline_duration": 2,
                "baseline_start": "2026-05-11",
                "baseline_finish": "2026-05-12",
                "scheduled_duration": 2,
                "scheduled_start": "2026-05-11",
                "scheduled_finish": "2026-05-12",
                "actual_start": None,
                "actual_finish": None,
                "percent_complete": 0,
                "task_status": "draft",
                "dependencies": [29],
                "task_type": "task",
            },
            {
                "task_id": 31,
                "task_name": "Completion of Plinth (RA-01)",
                "baseline_duration": 0,
                "baseline_start": "2026-05-12",
                "baseline_finish": "2026-05-12",
                "scheduled_duration": 0,
                "scheduled_start": "2026-05-12",
                "scheduled_finish": "2026-05-12",
                "actual_start": None,
                "actual_finish": None,
                "percent_complete": 0,
                "task_status": "draft",
                "dependencies": [30],
                "task_type": "milestone",
                "is_critical": True,
            },
            {
                "task_id": 32,
                "task_name": "Column Steel & Starter",
                "baseline_duration": 4,
                "baseline_start": "2026-05-11",
                "baseline_finish": "2026-05-14",
                "scheduled_duration": 4,
                "scheduled_start": "2026-05-11",
                "scheduled_finish": "2026-05-14",
                "actual_start": None,
                "actual_finish": None,
                "percent_complete": 0,
                "task_status": "draft",
                "dependencies": [31],
                "task_type": "task",
            },
            {
                "task_id": 33,
                "task_name": "Column Shuttering & Casting - 1st Set",
                "baseline_duration": 3,
                "baseline_start": "2026-05-15",
                "baseline_finish": "2026-05-18",
                "scheduled_duration": 3,
                "scheduled_start": "2026-05-15",
                "scheduled_finish": "2026-05-18",
                "actual_start": None,
                "actual_finish": None,
                "percent_complete": 0,
                "task_status": "draft",
                "dependencies": [32],
                "task_type": "task",
            },
            {
                "task_id": 34,
                "task_name": "Column Shuttering & Casting - 2nd Set with Staircase",
                "baseline_duration": 3,
                "baseline_start": "2026-05-19",
                "baseline_finish": "2026-05-21",
                "scheduled_duration": 3,
                "scheduled_start": "2026-05-19",
                "scheduled_finish": "2026-05-21",
                "actual_start": None,
                "actual_finish": None,
                "percent_complete": 0,
                "task_status": "draft",
                "dependencies": [33],
                "task_type": "task",
            },
            {
                "task_id": 35,
                "task_name": "1F Slab Shuttering",
                "baseline_duration": 10,
                "baseline_start": "2026-05-22",
                "baseline_finish": "2026-06-02",
                "scheduled_duration": 10,
                "scheduled_start": "2026-05-22",
                "scheduled_finish": "2026-06-02",
                "actual_start": None,
                "actual_finish": None,
                "percent_complete": 0,
                "task_status": "draft",
                "dependencies": [34],
                "task_type": "task",
            },
            {
                "task_id": 36,
                "task_name": "1F Steel tieing",
                "baseline_duration": 9,
                "baseline_start": "2026-06-03",
                "baseline_finish": "2026-06-12",
                "scheduled_duration": 9,
                "scheduled_start": "2026-06-03",
                "scheduled_finish": "2026-06-12",
                "actual_start": None,
                "actual_finish": None,
                "percent_complete": 0,
                "task_status": "draft",
                "dependencies": [35],
                "task_type": "task",
            },
            {
                "task_id": 37,
                "task_name": "Side Shuttering & Electricals",
                "baseline_duration": 3,
                "baseline_start": "2026-06-13",
                "baseline_finish": "2026-06-16",
                "scheduled_duration": 3,
                "scheduled_start": "2026-06-13",
                "scheduled_finish": "2026-06-16",
                "actual_start": None,
                "actual_finish": None,
                "percent_complete": 0,
                "task_status": "draft",
                "dependencies": [36],
                "task_type": "task",
            },
            {
                "task_id": 38,
                "task_name": "Casting for 1F Slab",
                "baseline_duration": 2,
                "baseline_start": "2026-06-17",
                "baseline_finish": "2026-06-18",
                "scheduled_duration": 2,
                "scheduled_start": "2026-06-17",
                "scheduled_finish": "2026-06-18",
                "actual_start": None,
                "actual_finish": None,
                "percent_complete": 0,
                "task_status": "draft",
                "dependencies": [37],
                "task_type": "task",
            },
            {
                "task_id": 39,
                "task_name": "Completion of 1F Slab (RA-02)",
                "baseline_duration": 0,
                "baseline_start": "2026-06-18",
                "baseline_finish": "2026-06-18",
                "scheduled_duration": 0,
                "scheduled_start": "2026-06-18",
                "scheduled_finish": "2026-06-18",
                "actual_start": None,
                "actual_finish": None,
                "percent_complete": 0,
                "task_status": "draft",
                "dependencies": [38],
                "task_type": "milestone",
                "is_critical": True,
            },
            {
                "task_id": 40,
                "task_name": "Completion of 2F Slab (RA-03)",
                "baseline_duration": 31,
                "baseline_start": "2026-06-19",
                "baseline_finish": "2026-07-24",
                "scheduled_duration": 31,
                "scheduled_start": "2026-06-19",
                "scheduled_finish": "2026-07-24",
                "actual_start": None,
                "actual_finish": None,
                "percent_complete": 0,
                "task_status": "draft",
                "dependencies": [39],
                "task_type": "task",
                "is_critical": True,
            },
            {
                "task_id": 41,
                "task_name": "Completion of Masonry Works (RA-04)",
                "baseline_duration": 31,
                "baseline_start": "2026-07-25",
                "baseline_finish": "2026-08-31",
                "scheduled_duration": 31,
                "scheduled_start": "2026-07-25",
                "scheduled_finish": "2026-08-31",
                "actual_start": None,
                "actual_finish": None,
                "percent_complete": 0,
                "task_status": "draft",
                "dependencies": [40],
                "task_type": "task",
                "is_critical": True,
            },
            {
                "task_id": 42,
                "task_name": "Completion of Internal Plastering (RA-05)",
                "baseline_duration": 49,
                "baseline_start": "2026-09-01",
                "baseline_finish": "2026-10-30",
                "scheduled_duration": 49,
                "scheduled_start": "2026-09-01",
                "scheduled_finish": "2026-10-30",
                "actual_start": None,
                "actual_finish": None,
                "percent_complete": 0,
                "task_status": "draft",
                "dependencies": [41],
                "task_type": "task",
                "is_critical": True,
            },
            {
                "task_id": 43,
                "task_name": "Completion of External Plastering (RA-06)",
                "baseline_duration": 34,
                "baseline_start": "2026-10-31",
                "baseline_finish": "2026-12-15",
                "scheduled_duration": 34,
                "scheduled_start": "2026-10-31",
                "scheduled_finish": "2026-12-15",
                "actual_start": None,
                "actual_finish": None,
                "percent_complete": 0,
                "task_status": "draft",
                "dependencies": [42],
                "task_type": "task",
                "is_critical": True,
            },
            {
                "task_id": 44,
                "task_name": "External Development & Final Bill (RA-07)",
                "baseline_duration": 34,
                "baseline_start": "2026-10-31",
                "baseline_finish": "2026-12-15",
                "scheduled_duration": 34,
                "scheduled_start": "2026-10-31",
                "scheduled_finish": "2026-12-15",
                "actual_start": None,
                "actual_finish": None,
                "percent_complete": 0,
                "task_status": "draft",
                "dependencies": [42],
                "task_type": "task",
            },
        ]


        existing_scheduler = await db.project_schedules.find_one({"project_id": project_id})
        if existing_scheduler:
            await db.project_schedules.delete_one({"project_id": project_id})

        await db.project_schedules.insert_one(
            {
                "project_id": project_id,
                "organisation_id": org_id,
                "project_name": "Majorda Villa - Civil Works",
                "tasks": majorda_tasks,
                "total_duration_days": 246,
                "project_start_date": "2026-02-20",
                "critical_path": [0, 1, 2, 3, 6, 12, 13, 14, 31, 40, 41, 42, 43],
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "version": 1,
            }
        )
        print(f"  Created scheduler with {len(majorda_tasks)} tasks")

        # 6. INITIAL FINANCIAL STATES
        print("\n[STEP 6] Seeding Financial States...")
        await db.financial_state.delete_many({"project_id": project_id})
        try:
            await db.financial_state.drop_index("project_id_1_code_id_1")
            print("  Dropped temporary index project_id_1_code_id_1")
        except Exception:
            pass

        try:
            await db.financial_state.create_index([("project_id", 1), ("category_id", 1)], unique=True)
        except Exception as e:
            print(f"Skipping index creation: {e}")
            pass
            
        financial_categories = [
            {"category_id": "CIV", "original": 15000000, "committed": 10072425, "certified": 1535000},
            {"category_id": "PLB", "original": 5000000, "committed": 0, "certified": 0},
            {"category_id": "ELC", "original": 5000000, "committed": 13530, "certified": 0},
            {"category_id": "PRF", "original": 5000000, "committed": 14000, "certified": 14000},
            {"category_id": "PTC", "original": 85000, "committed": 81300, "certified": 81300},
        ]

        for fc in financial_categories:
            code_id = code_map.get(fc["category_id"])
            if not code_id: continue
            await db.financial_state.update_one(
                {"project_id": project_id, "category_id": code_id},
                {"$set": {
                    "code_id": code_id,
                    "category_id": code_id,
                    "original_budget": fc["original"],
                    "committed_value": fc["committed"],
                    "certified_value": fc["certified"],
                    "balance_budget_remaining": fc["original"] - fc["committed"],
                    "last_updated": datetime.now(timezone.utc)
                }},
                upsert=True
            )
        print(f"  Projected financial states for {len(financial_categories)} categories")

        print("\n[STEP 7] Seeding Missing WOs, PCs and Site Tasks...")
        await db.work_orders.delete_many({"project_id": project_id})
        await db.payment_certificates.delete_many({"project_id": project_id})
        
        await db.work_orders.insert_many([
            {
                "wo_ref": "TAC_WO_25_003",
                "organisation_id": org_id,
                "project_id": project_id,
                "category_id": code_map.get("ELC"),
                "vendor_id": vendor_map.get("Suraj Electrician"),
                "subtotal": 13530,
                "grand_total": 13530,
                "status": "Completed"
            },
            {
                "wo_ref": "TAC_WO_25_004",
                "organisation_id": org_id,
                "project_id": project_id,
                "category_id": code_map.get("PRF"),
                "vendor_id": vendor_map.get("CDSP Global"),
                "subtotal": 14000,
                "grand_total": 14000,
                "status": "Completed"
            }
        ])
        
        await db.payment_certificates.insert_many([
            {
                "pc_ref": "TAC_PC_25_001",
                "organisation_id": org_id,
                "project_id": project_id,
                "category_id": code_map.get("CIV"),
                "vendor_id": vendor_map.get("SS Construction"),
                "subtotal": 1000000,
                "grand_total": 1000000,
                "status": "Approved"
            },
            {
                "pc_ref": "TAC_PC_25_002",
                "organisation_id": org_id,
                "project_id": project_id,
                "category_id": code_map.get("CIV"),
                "vendor_id": vendor_map.get("Rajesh Construction"),
                "subtotal": 535000,
                "grand_total": 535000,
                "status": "Approved"
            }
        ])
        
        print("  Created missing entities.")

        print("\n" + "=" * 70)
        print("SEED COMPLETE - PRODUCTION READY")
        print("=" * 70)
        print("\nLogins Available:")
        print("  Admin:      admin@tacpmc.com / Admin@1234")
        print("  Supervisor: supervisor@tacpmc.com / Supervisor@1234")
        print("  Client:     client@tacpmc.com / Client@1234")
        print("\nProject: Majorda Villa - Civil Works")
        print("  Tasks: 45 (14 completed, 31 pending)")
        print("  Timeline: 2026-02-20 to 2026-12-15 (246 days)")
        print("=" * 70 + "\n")

    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(seed_production())
