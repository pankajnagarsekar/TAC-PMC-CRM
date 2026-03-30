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
from decimal import Decimal
from pathlib import Path

# Add app directory to path
app_dir = Path(__file__).parent.parent / "app"
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir.parent))

from bson import ObjectId, Decimal128
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "tac_pmc_crm")

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def seed_production():
    """Seed production data."""
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    try:
        print("\n" + "="*70)
        print("TAC-PMC-CRM PRODUCTION SEED")
        print("="*70)

        # 1. ORGANISATION
        print("\n[STEP 1] Creating Organisation...")
        org = await db.organisations.find_one({"name": "TAC-PMC"})
        if org:
            org_id = str(org["_id"])
            print(f"  Organisation exists: {org_id}")
        else:
            org_result = await db.organisations.insert_one({
                "name": "TAC-PMC",
                "description": "Third Angle Concepts - Project Management Consulting",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            })
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
                user_result = await db.users.insert_one({
                    "email": user_cfg["email"],
                    "name": user_cfg["name"],
                    "hashed_password": pwd_ctx.hash(user_cfg["password"]),
                    "role": user_cfg["role"],
                    "active_status": True,
                    "organisation_id": org_id,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                })
                user_map[user_cfg["role"]] = str(user_result.inserted_id)
                print(f"  {user_cfg['role']}: {user_cfg['email']} (created)")

        # 3. FINANCIAL CODES
        print("\n[STEP 3] Creating Financial Codes...")
        codes = [
            {"code": "LABOR", "description": "Labour Cost", "category": "Expense"},
            {"code": "MATERIAL", "description": "Material Cost", "category": "Expense"},
            {"code": "EQUIPMENT", "description": "Equipment Rental", "category": "Expense"},
            {"code": "OVERHEAD", "description": "Overhead", "category": "Expense"},
            {"code": "CONTINGENCY", "description": "Contingency", "category": "Contingency"},
        ]

        for code in codes:
            existing = await db.financial_codes.find_one({"code": code["code"]})
            if not existing:
                await db.financial_codes.insert_one({
                    **code,
                    "organisation_id": org_id,
                    "created_at": datetime.now(timezone.utc),
                })
        print(f"  Created/verified {len(codes)} financial codes")

        # 4. PROJECT: MAJORDA VILLA
        print("\n[STEP 4] Creating Majorda Villa Project...")
        project = await db.projects.find_one({"name": "Majorda Villa - Civil Works"})
        if project:
            project_id = str(project["_id"])
            print(f"  Project exists: {project_id}")
        else:
            project_oid = ObjectId()
            project_result = await db.projects.insert_one({
                "_id": project_oid,
                "project_id": str(project_oid),
                "name": "Majorda Villa - Civil Works",
                "client_name": "Mr. Sanjay Rao",
                "status": "Active",
                "project_type": "Commercial Construction",
                "start_date": datetime(2026, 2, 20, tzinfo=timezone.utc),
                "end_date": None,
                "description": "Majorda Villa - Civil Works Construction Project",
                "location": "Goa, India",
                "owner": "TAC-PMC",
                "organisation_id": org_id,
                "created_by": user_map["Admin"],
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "version": 1,
            })
            project_id = str(project_oid)
            print(f"  Created: {project_id}")

        # 5. SCHEDULER TASKS
        print("\n[STEP 5] Creating Project Scheduler with 45 tasks...")

        majorda_tasks = [
            {"task_id": 0, "task_name": "Majorda Villa - Civil Works", "baseline_duration": 246, "baseline_start": "2026-02-20", "baseline_finish": "2026-12-15", "duration": 251, "actual_start": "2026-02-20", "actual_finish": None, "percent_complete": 18, "finish_variance": 5, "dependencies": [], "task_type": "summary"},
            {"task_id": 1, "task_name": "Start", "baseline_duration": 0, "baseline_start": "2026-02-20", "baseline_finish": "2026-02-20", "duration": 0, "actual_start": "2026-02-20", "actual_finish": "2026-02-20", "percent_complete": 100, "finish_variance": 0, "dependencies": [], "task_type": "milestone"},
            {"task_id": 2, "task_name": "Mobilization at Site", "baseline_duration": 1, "baseline_start": "2026-02-20", "baseline_finish": "2026-02-20", "duration": 1, "actual_start": "2026-02-20", "actual_finish": "2026-02-20", "percent_complete": 100, "finish_variance": 0, "dependencies": [1], "task_type": "task"},
            {"task_id": 3, "task_name": "Surveying & Layout", "baseline_duration": 1, "baseline_start": "2026-02-21", "baseline_finish": "2026-02-21", "duration": 1, "actual_start": "2026-02-21", "actual_finish": "2026-02-21", "percent_complete": 100, "finish_variance": 0, "dependencies": [2], "task_type": "task"},
            {"task_id": 4, "task_name": "Approval for MEP - UGT, ST, SP", "baseline_duration": 12, "baseline_start": "2026-02-23", "baseline_finish": "2026-03-09", "duration": 12, "actual_start": "2026-02-23", "actual_finish": "2026-03-09", "percent_complete": 100, "finish_variance": 0, "dependencies": [3], "task_type": "task"},
            {"task_id": 5, "task_name": "Approval for Swimming Pool", "baseline_duration": 12, "baseline_start": "2026-02-23", "baseline_finish": "2026-03-09", "duration": 12, "actual_start": "2026-02-23", "actual_finish": "2026-03-09", "percent_complete": 100, "finish_variance": 0, "dependencies": [3], "task_type": "task"},
            {"task_id": 6, "task_name": "Excavation in Foundation Pits", "baseline_duration": 14, "baseline_start": "2026-02-21", "baseline_finish": "2026-03-10", "duration": 14, "actual_start": "2026-02-21", "actual_finish": "2026-03-10", "percent_complete": 100, "finish_variance": 0, "dependencies": [3], "task_type": "task", "is_critical": True},
            {"task_id": 7, "task_name": "Railing", "baseline_duration": 2, "baseline_start": "2026-03-10", "baseline_finish": "2026-03-11", "duration": 2, "actual_start": "2026-03-10", "actual_finish": "2026-03-11", "percent_complete": 100, "finish_variance": 0, "dependencies": [6], "task_type": "task"},
            {"task_id": 8, "task_name": "Rubble Soling", "baseline_duration": 2, "baseline_start": "2026-03-11", "baseline_finish": "2026-03-12", "duration": 2, "actual_start": "2026-03-11", "actual_finish": "2026-03-12", "percent_complete": 100, "finish_variance": 0, "dependencies": [7], "task_type": "task"},
            {"task_id": 9, "task_name": "PCC in Foundation", "baseline_duration": 2, "baseline_start": "2026-03-13", "baseline_finish": "2026-03-14", "duration": 2, "actual_start": "2026-03-13", "actual_finish": "2026-03-14", "percent_complete": 100, "finish_variance": 0, "dependencies": [8], "task_type": "task"},
            {"task_id": 10, "task_name": "Marking for Foundation", "baseline_duration": 2, "baseline_start": "2026-03-16", "baseline_finish": "2026-03-17", "duration": 1, "actual_start": "2026-03-13", "actual_finish": "2026-03-13", "percent_complete": 100, "finish_variance": -3, "dependencies": [9], "task_type": "task"},
            {"task_id": 11, "task_name": "Marking by Carpenter & Box Fitting", "baseline_duration": 1, "baseline_start": "2026-03-17", "baseline_finish": "2026-03-17", "duration": 1, "actual_start": "2026-03-14", "actual_finish": "2026-03-14", "percent_complete": 100, "finish_variance": -2, "dependencies": [10], "task_type": "task"},
            {"task_id": 12, "task_name": "Steel Tying Column Erection", "baseline_duration": 2, "baseline_start": "2026-03-18", "baseline_finish": "2026-03-19", "duration": 7, "actual_start": "2026-03-17", "actual_finish": "2026-03-24", "percent_complete": 100, "finish_variance": 4, "dependencies": [11], "task_type": "task", "is_critical": True},
            {"task_id": 13, "task_name": "Steel Checking - Inspection Hold Point", "baseline_duration": 1, "baseline_start": "2026-03-20", "baseline_finish": "2026-03-20", "duration": 1, "actual_start": "2026-03-25", "actual_finish": "2026-03-25", "percent_complete": 100, "finish_variance": 4, "dependencies": [12], "task_type": "task"},
            {"task_id": 14, "task_name": "Casting of Foundation", "baseline_duration": 1, "baseline_start": "2026-03-21", "baseline_finish": "2026-03-21", "duration": 1, "actual_start": "2026-03-27", "actual_finish": "2026-03-27", "percent_complete": 100, "finish_variance": 5, "dependencies": [13], "task_type": "task", "is_critical": True},
            {"task_id": 15, "task_name": "Starter for Column", "baseline_duration": 1, "baseline_start": "2026-03-23", "baseline_finish": "2026-03-23", "duration": 1, "actual_start": None, "actual_finish": None, "percent_complete": 0, "finish_variance": 5, "dependencies": [14], "task_type": "task"},
            {"task_id": 16, "task_name": "Casting for Column", "baseline_duration": 1, "baseline_start": "2026-03-23", "baseline_finish": "2026-03-23", "duration": 1, "actual_start": None, "actual_finish": None, "percent_complete": 0, "finish_variance": 5, "dependencies": [15], "task_type": "task"},
            {"task_id": 17, "task_name": "Column Shuttering & Casting - 1st Set", "baseline_duration": 3, "baseline_start": "2026-03-24", "baseline_finish": "2026-03-26", "duration": 3, "actual_start": None, "actual_finish": None, "percent_complete": 0, "finish_variance": 5, "dependencies": [16], "task_type": "task"},
            {"task_id": 18, "task_name": "Column Shuttering & Casting - 2nd Set", "baseline_duration": 4, "baseline_start": "2026-03-27", "baseline_finish": "2026-03-31", "duration": 4, "actual_start": None, "actual_finish": None, "percent_complete": 0, "finish_variance": 5, "dependencies": [17], "task_type": "task"},
            {"task_id": 19, "task_name": "Excavation for Foundation Masonry", "baseline_duration": 3, "baseline_start": "2026-04-01", "baseline_finish": "2026-04-03", "duration": 3, "actual_start": None, "actual_finish": None, "percent_complete": 0, "finish_variance": 5, "dependencies": [18], "task_type": "task"},
            {"task_id": 20, "task_name": "Rubble Soling PCC in Foundation", "baseline_duration": 2, "baseline_start": "2026-04-04", "baseline_finish": "2026-04-06", "duration": 2, "actual_start": None, "actual_finish": None, "percent_complete": 0, "finish_variance": 5, "dependencies": [19], "task_type": "task"},
            {"task_id": 21, "task_name": "Foundation Masonry", "baseline_duration": 5, "baseline_start": "2026-04-07", "baseline_finish": "2026-04-11", "duration": 5, "actual_start": None, "actual_finish": None, "percent_complete": 0, "finish_variance": 5, "dependencies": [20], "task_type": "task"},
            {"task_id": 22, "task_name": "Backfilling in Plinth excavation for Pool", "baseline_duration": 3, "baseline_start": "2026-04-13", "baseline_finish": "2026-04-15", "duration": 3, "actual_start": None, "actual_finish": None, "percent_complete": 0, "finish_variance": 5, "dependencies": [21], "task_type": "task"},
            {"task_id": 23, "task_name": "Compaction for Plinth Pool Soling & PCC", "baseline_duration": 3, "baseline_start": "2026-04-16", "baseline_finish": "2026-04-18", "duration": 3, "actual_start": None, "actual_finish": None, "percent_complete": 0, "finish_variance": 5, "dependencies": [22], "task_type": "task"},
            {"task_id": 24, "task_name": "Soling & PCC for Plinth Beam", "baseline_duration": 1, "baseline_start": "2026-04-20", "baseline_finish": "2026-04-20", "duration": 1, "actual_start": None, "actual_finish": None, "percent_complete": 0, "finish_variance": 5, "dependencies": [23], "task_type": "task"},
            {"task_id": 25, "task_name": "Steel for Plinth Beam", "baseline_duration": 4, "baseline_start": "2026-04-21", "baseline_finish": "2026-04-24", "duration": 4, "actual_start": None, "actual_finish": None, "percent_complete": 0, "finish_variance": 5, "dependencies": [24], "task_type": "task"},
            {"task_id": 26, "task_name": "Shuttering for Plinth Beam", "baseline_duration": 5, "baseline_start": "2026-04-25", "baseline_finish": "2026-04-30", "duration": 5, "actual_start": None, "actual_finish": None, "percent_complete": 0, "finish_variance": 5, "dependencies": [25], "task_type": "task"},
            {"task_id": 27, "task_name": "Casting of Plinth Beam", "baseline_duration": 2, "baseline_start": "2026-05-01", "baseline_finish": "2026-05-02", "duration": 2, "actual_start": None, "actual_finish": None, "percent_complete": 0, "finish_variance": 5, "dependencies": [26], "task_type": "task"},
            {"task_id": 28, "task_name": "Backfilling in Plinth", "baseline_duration": 4, "baseline_start": "2026-05-01", "baseline_finish": "2026-05-05", "duration": 4, "actual_start": None, "actual_finish": None, "percent_complete": 0, "finish_variance": 5, "dependencies": [27], "task_type": "task"},
            {"task_id": 29, "task_name": "Rubble Soling", "baseline_duration": 4, "baseline_start": "2026-05-06", "baseline_finish": "2026-05-09", "duration": 4, "actual_start": None, "actual_finish": None, "percent_complete": 0, "finish_variance": 5, "dependencies": [28], "task_type": "task"},
            {"task_id": 30, "task_name": "PCC in Plinth", "baseline_duration": 2, "baseline_start": "2026-05-11", "baseline_finish": "2026-05-12", "duration": 2, "actual_start": None, "actual_finish": None, "percent_complete": 0, "finish_variance": 5, "dependencies": [29], "task_type": "task"},
            {"task_id": 31, "task_name": "Completion of Plinth (RA-01)", "baseline_duration": 0, "baseline_start": "2026-05-12", "baseline_finish": "2026-05-12", "duration": 0, "actual_start": None, "actual_finish": None, "percent_complete": 0, "finish_variance": 5, "dependencies": [30], "task_type": "milestone", "is_critical": True},
            {"task_id": 32, "task_name": "Column Steel & Starter", "baseline_duration": 4, "baseline_start": "2026-05-11", "baseline_finish": "2026-05-14", "duration": 4, "actual_start": None, "actual_finish": None, "percent_complete": 0, "finish_variance": 5, "dependencies": [31], "task_type": "task"},
            {"task_id": 33, "task_name": "Column Shuttering & Casting - 1st Set", "baseline_duration": 3, "baseline_start": "2026-05-15", "baseline_finish": "2026-05-18", "duration": 3, "actual_start": None, "actual_finish": None, "percent_complete": 0, "finish_variance": 5, "dependencies": [32], "task_type": "task"},
            {"task_id": 34, "task_name": "Column Shuttering & Casting - 2nd Set with Staircase", "baseline_duration": 3, "baseline_start": "2026-05-19", "baseline_finish": "2026-05-21", "duration": 3, "actual_start": None, "actual_finish": None, "percent_complete": 0, "finish_variance": 5, "dependencies": [33], "task_type": "task"},
            {"task_id": 35, "task_name": "1F Slab Shuttering", "baseline_duration": 10, "baseline_start": "2026-05-22", "baseline_finish": "2026-06-02", "duration": 10, "actual_start": None, "actual_finish": None, "percent_complete": 0, "finish_variance": 5, "dependencies": [34], "task_type": "task"},
            {"task_id": 36, "task_name": "1F Steel tieing", "baseline_duration": 9, "baseline_start": "2026-06-03", "baseline_finish": "2026-06-12", "duration": 9, "actual_start": None, "actual_finish": None, "percent_complete": 0, "finish_variance": 5, "dependencies": [35], "task_type": "task"},
            {"task_id": 37, "task_name": "Side Shuttering & Electricals", "baseline_duration": 3, "baseline_start": "2026-06-13", "baseline_finish": "2026-06-16", "duration": 3, "actual_start": None, "actual_finish": None, "percent_complete": 0, "finish_variance": 5, "dependencies": [36], "task_type": "task"},
            {"task_id": 38, "task_name": "Casting for 1F Slab", "baseline_duration": 2, "baseline_start": "2026-06-17", "baseline_finish": "2026-06-18", "duration": 2, "actual_start": None, "actual_finish": None, "percent_complete": 0, "finish_variance": 5, "dependencies": [37], "task_type": "task"},
            {"task_id": 39, "task_name": "Completion of 1F Slab (RA-02)", "baseline_duration": 0, "baseline_start": "2026-06-18", "baseline_finish": "2026-06-18", "duration": 0, "actual_start": None, "actual_finish": None, "percent_complete": 0, "finish_variance": 5, "dependencies": [38], "task_type": "milestone", "is_critical": True},
            {"task_id": 40, "task_name": "Completion of 2F Slab (RA-03)", "baseline_duration": 31, "baseline_start": "2026-06-19", "baseline_finish": "2026-07-24", "duration": 31, "actual_start": None, "actual_finish": None, "percent_complete": 0, "finish_variance": 5, "dependencies": [39], "task_type": "task", "is_critical": True},
            {"task_id": 41, "task_name": "Completion of Masonry Works (RA-04)", "baseline_duration": 31, "baseline_start": "2026-07-25", "baseline_finish": "2026-08-31", "duration": 31, "actual_start": None, "actual_finish": None, "percent_complete": 0, "finish_variance": 5, "dependencies": [40], "task_type": "task", "is_critical": True},
            {"task_id": 42, "task_name": "Completion of Internal Plastering (RA-05)", "baseline_duration": 49, "baseline_start": "2026-09-01", "baseline_finish": "2026-10-30", "duration": 49, "actual_start": None, "actual_finish": None, "percent_complete": 0, "finish_variance": 5, "dependencies": [41], "task_type": "task", "is_critical": True},
            {"task_id": 43, "task_name": "Completion of External Plastering (RA-06)", "baseline_duration": 34, "baseline_start": "2026-10-31", "baseline_finish": "2026-12-15", "duration": 34, "actual_start": None, "actual_finish": None, "percent_complete": 0, "finish_variance": 5, "dependencies": [42], "task_type": "task", "is_critical": True},
            {"task_id": 44, "task_name": "External Development & Final Bill (RA-07)", "baseline_duration": 34, "baseline_start": "2026-10-31", "baseline_finish": "2026-12-15", "duration": 34, "actual_start": None, "actual_finish": None, "percent_complete": 0, "finish_variance": 5, "dependencies": [42], "task_type": "task"},
        ]

        existing_scheduler = await db.scheduler.find_one({"project_id": project_id})
        if existing_scheduler:
            await db.scheduler.delete_one({"project_id": project_id})

        await db.scheduler.insert_one({
            "project_id": project_id,
            "project_name": "Majorda Villa - Civil Works",
            "tasks": majorda_tasks,
            "total_duration_days": 246,
            "project_start_date": "2026-02-20",
            "critical_path": [0, 1, 2, 3, 6, 12, 13, 14, 31, 40, 41, 42, 43],
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "version": 1,
        })
        print(f"  Created scheduler with {len(majorda_tasks)} tasks")

        print("\n" + "="*70)
        print("SEED COMPLETE - PRODUCTION READY")
        print("="*70)
        print("\nLogins Available:")
        print("  Admin:      admin@tacpmc.com / Admin@1234")
        print("  Supervisor: supervisor@tacpmc.com / Supervisor@1234")
        print("  Client:     client@tacpmc.com / Client@1234")
        print("\nProject: Majorda Villa - Civil Works")
        print("  Tasks: 45 (14 completed, 31 pending)")
        print("  Timeline: 2026-02-20 to 2026-12-15 (246 days)")
        print("="*70 + "\n")

    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(seed_production())
