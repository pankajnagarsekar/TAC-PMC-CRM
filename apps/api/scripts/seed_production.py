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
                    "description": "Third Angle Concepts - Project Management Consulting",
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                }
            )
            org_id = str(org_result.inserted_id)
            print(f"  Created: {org_id}")

        # 2. USERS (3 only: admin, supervisor, client)
        print("\n[STEP 2] Creating Users (3: admin, supervisor, client)...")
        users_config = [
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
                "role": "Client",
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

        for code in codes:
            # Sync to financial_codes (legacy/internal)
            existing = await db.financial_codes.find_one({"code": code["code"]})
            if not existing:
                await db.financial_codes.insert_one(
                    {
                        **code,
                        "organisation_id": org_id,
                        "created_at": datetime.now(timezone.utc),
                    }
                )
            # Sync to code_master (DDD repository standard)
            existing_master = await db.code_master.find_one({"code": code["code"]})
            if not existing_master:
                await db.code_master.insert_one(
                    {
                        "code": code["code"],
                        "code_short": code["code"],
                        "description": code["description"],
                        "category": code["category"],
                        "organisation_id": org_id,
                        "is_active": True,
                        "created_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc),
                    }
                )
        print(f"  Created/verified {len(codes)} financial codes in both collections")

        # 4. PROJECT: MAJORDA VILLA
        print("\n[STEP 4] Creating Majorda Villa Project...")
        project = await db.projects.find_one({"project_name": "Majorda Villa - Civil Works"})
        
        # Consistent realistic budget values from MIS
        original_budget = 12000000 # ~12M Cr
        remaining_budget = 7500000 # After ~4.5M expenditure
        
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
                    "client_name": "Mr. Sanjay Rao",
                    "location": "Majorda, South Goa"
                }}
            )
        else:
            project_oid = ObjectId()
            await db.projects.insert_one(
                {
                    "_id": project_oid,
                    "project_id": str(project_oid),
                    "project_name": "Majorda Villa - Civil Works",
                    "client_name": "Mr. Sanjay Rao",
                    "status": "active",
                    "project_type": "Luxury Construction",
                    "start_date": datetime(2026, 2, 20, tzinfo=timezone.utc),
                    "end_date": datetime(2026, 12, 15, tzinfo=timezone.utc),
                    "description": "Premium villa construction project in Majorda.",
                    "location": "Majorda, South Goa",
                    "owner": "TAC-PMC",
                    "organisation_id": org_id,
                    "created_by": user_map["Admin"],
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                    "master_original_budget": original_budget,
                    "master_remaining_budget": remaining_budget,
                    "completion_percentage": 18,
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
        financial_categories = [
            {"category_id": "CIV", "original": 10072425, "committed": 10072425, "certified": 4500000},
            {"category_id": "PLB", "original": 350000, "committed": 0, "certified": 0},
            {"category_id": "ELC", "original": 500000, "committed": 13530, "certified": 0},
            {"category_id": "PRF", "original": 200000, "committed": 14000, "certified": 14000},
            {"category_id": "PTC", "original": 100000, "committed": 25000, "certified": 25000},
        ]

        for fc in financial_categories:
            await db.financial_state.update_one(
                {"project_id": project_id, "category_id": fc["category_id"]},
                {"$set": {
                    "original_budget": fc["original"],
                    "committed_value": fc["committed"],
                    "certified_value": fc["certified"],
                    "balance_budget_remaining": fc["original"] - fc["committed"],
                    "updated_at": datetime.now(timezone.utc)
                }},
                upsert=True
            )
        print(f"  Projected financial states for {len(financial_categories)} categories")

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
