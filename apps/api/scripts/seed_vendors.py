#!/usr/bin/env python3
"""
Comprehensive Seed Script for TAC-PMC CRM
Creates: Organisation, Users, Projects, Categories, and Vendors
Run: python seed_vendors.py
"""

import os
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.hash import bcrypt
from bson import ObjectId, Decimal128

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = "tac_pmc_crm"


async def seed():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    print("\n" + "="*60)
    print("[*] TAC-PMC CRM Seed Script - Starting")
    print("="*60 + "\n")

    # ============================================================================
    # 1. ORGANISATION
    # ============================================================================
    print("[1/6] ORGANISATION")
    org_name = "TAC-PMC Construction"
    existing_org = await db.organisations.find_one({"name": org_name})

    if existing_org:
        print(f"  [OK] Organisation '{org_name}' - already exists")
        org_id = str(existing_org["_id"])
    else:
        org_doc = {"name": org_name, "created_at": datetime.now(timezone.utc)}
        result = await db.organisations.insert_one(org_doc)
        org_id = str(result.inserted_id)
        print(f"  [OK] Organisation '{org_name}' - created")

    # Global Settings
    existing_settings = await db.global_settings.find_one({"organisation_id": org_id})
    if not existing_settings:
        settings_doc = {
            "organisation_id": org_id,
            "cgst_percentage": Decimal128("9.0"),
            "sgst_percentage": Decimal128("9.0"),
            "retention_percentage": Decimal128("5.0"),
            "terms_and_conditions": "Standard terms and conditions apply.",
            "currency": "INR",
            "currency_symbol": "₹",
            "updated_at": datetime.now(timezone.utc)
        }
        await db.global_settings.insert_one(settings_doc)
        print(f"  [OK] Global Settings - created")
    else:
        print(f"  [OK] Global Settings - already exists")

    # ============================================================================
    # 2. USERS
    # ============================================================================
    print("\n[2/6] USERS")
    users_data = [
        {
            "name": "Admin User",
            "email": "admin@tacpmc.com",
            "password": "Admin@1234",
            "role": "Admin"
        },
        {
            "name": "Supervisor User",
            "email": "supervisor@tacpmc.com",
            "password": "Super@1234",
            "role": "Supervisor"
        },
        {
            "name": "Project Manager",
            "email": "pm@tacpmc.com",
            "password": "PM@1234",
            "role": "Admin"
        }
    ]

    for user_data in users_data:
        existing_user = await db.users.find_one({"email": user_data["email"]})
        if existing_user:
            print(f"  [OK] {user_data['email']} ({user_data['role']}) - already exists")
        else:
            user_doc = {
                "name": user_data["name"],
                "email": user_data["email"],
                "hashed_password": bcrypt.hash(user_data["password"]),
                "role": user_data["role"],
                "active_status": True,
                "organisation_id": org_id,
                "dpr_generation_permission": user_data["role"] == "Admin",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
            await db.users.insert_one(user_doc)
            print(f"  [OK] {user_data['email']} ({user_data['role']}) - created")

    # ============================================================================
    # 3. CATEGORIES (Code Master)
    # ============================================================================
    print("\n[3/6] CATEGORIES")
    categories_data = [
        {"code": "STR", "code_short": "STR", "category_name": "Structure", "code_description": "Structural Work", "budget_type": "direct"},
        {"code": "REI", "code_short": "REI", "category_name": "Reinforcement", "code_description": "Reinforcement Steel", "budget_type": "direct"},
        {"code": "CON", "code_short": "CON", "category_name": "Concrete", "code_description": "Concrete & Placing", "budget_type": "direct"},
        {"code": "BRI", "code_short": "BRI", "category_name": "Brickwork", "code_description": "Masonry & Brickwork", "budget_type": "direct"},
        {"code": "PLU", "code_short": "PLU", "category_name": "Plumbing", "code_description": "Plumbing & Sanitary", "budget_type": "direct"},
        {"code": "ELE", "code_short": "ELE", "category_name": "Electrical", "code_description": "Electrical Installation", "budget_type": "direct"},
        {"code": "FIN", "code_short": "FIN", "category_name": "Finishing", "code_description": "Finishing Works", "budget_type": "direct"},
        {"code": "PET", "code_short": "PET", "category_name": "Petty", "code_description": "Petty Cash", "budget_type": "fund_transfer"},
        {"code": "OVH", "code_short": "OVH", "category_name": "Overhead", "code_description": "Site Overhead", "budget_type": "fund_transfer"},
    ]

    category_ids = {}
    for cat_data in categories_data:
        existing_cat = await db.code_master.find_one({"code": cat_data["code"]})
        if existing_cat:
            print(f"  [OK] {cat_data['code']} - {cat_data['category_name']} - already exists")
            category_ids[cat_data["code"]] = str(existing_cat["_id"])
        else:
            cat_doc = {
                "code": cat_data["code"],
                "code_short": cat_data["code_short"],
                "category_name": cat_data["category_name"],
                "code_description": cat_data["code_description"],
                "budget_type": cat_data["budget_type"],
                "active_status": True,
                "organisation_id": org_id,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
            result = await db.code_master.insert_one(cat_doc)
            category_ids[cat_data["code"]] = str(result.inserted_id)
            print(f"  [OK] {cat_data['code']} - {cat_data['category_name']} - created")

    # ============================================================================
    # 4. PROJECTS
    # ============================================================================
    print("\n[4/6] PROJECTS")
    projects_data = [
        {
            "name": "Majorda Villa",
            "project_code": "MJ-001",
            "budget": 1000000,
        },
        {
            "name": "Downtown Tower",
            "project_code": "DT-001",
            "budget": 5000000,
        },
        {
            "name": "Metro Station A",
            "project_code": "MS-001",
            "budget": 10000000,
        }
    ]

    project_ids = {}
    for proj_data in projects_data:
        existing_proj = await db.projects.find_one({"project_code": proj_data["project_code"]})
        if existing_proj:
            print(f"  [OK] {proj_data['project_code']} - {proj_data['name']} - already exists")
            project_ids[proj_data["project_code"]] = str(existing_proj["_id"])
        else:
            proj_doc = {
                "name": proj_data["name"],
                "project_name": proj_data["name"],
                "project_code": proj_data["project_code"],
                "organisation_id": org_id,
                "client_id": "CLIENT_001",
                "status": "active",
                "project_cgst_percentage": "9.0",
                "project_sgst_percentage": "9.0",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
            result = await db.projects.insert_one(proj_doc)
            project_ids[proj_data["project_code"]] = str(result.inserted_id)
            print(f"  [OK] {proj_data['project_code']} - {proj_data['name']} - created")

    # ============================================================================
    # 5. VENDORS
    # ============================================================================
    print("\n[5/6] VENDORS")
    vendors_data = [
        {
            "name": "ABC Contractors",
            "gstin": "18AABCU1234A1Z5",
            "contact_person": "Rajesh Kumar",
            "phone": "+91-98765-43210",
            "email": "rajesh@abccontractors.com",
            "address": "123 Construction Lane, Mumbai, MH 400001"
        },
        {
            "name": "BuildRight Solutions",
            "gstin": "27BDDPS1234B1Z8",
            "contact_person": "Priya Sharma",
            "phone": "+91-99876-54321",
            "email": "priya@buildright.com",
            "address": "456 Engineering Park, Pune, MH 411001"
        },
        {
            "name": "Steel & Co",
            "gstin": "22AABCT1234C1Z2",
            "contact_person": "Akshay Patel",
            "phone": "+91-97654-32109",
            "email": "akshay@steelco.com",
            "address": "789 Industrial Zone, Bangalore, KA 560001"
        },
        {
            "name": "Premium Concrete Ltd",
            "gstin": "12AABCP1234D1Z6",
            "contact_person": "Vikas Singh",
            "phone": "+91-96543-21098",
            "email": "vikas@premiumconcrete.com",
            "address": "321 Factory Area, Hyderabad, TG 500001"
        },
        {
            "name": "Electrical Experts",
            "gstin": "33AABCE1234E1Z9",
            "contact_person": "Sanjay Desai",
            "phone": "+91-95432-10987",
            "email": "sanjay@electricalexperts.com",
            "address": "654 Tech Park, Chennai, TN 600001"
        },
        {
            "name": "Plumbing Professionals",
            "gstin": "23AABCPL1234F1Z3",
            "contact_person": "Ramesh Gupta",
            "phone": "+91-94321-09876",
            "email": "ramesh@plumbingpro.com",
            "address": "987 Service Road, Delhi, DL 110001"
        },
        {
            "name": "Finishers Group",
            "gstin": "15AABCFG1234G1Z7",
            "contact_person": "Neha Kumari",
            "phone": "+91-93210-98765",
            "email": "neha@finishersgroup.com",
            "address": "159 Enterprise Hub, Kolkata, WB 700001"
        },
        {
            "name": "Material Suppliers Inc",
            "gstin": "29AABCMS1234H1Z4",
            "contact_person": "Arjun Nair",
            "phone": "+91-92109-87654",
            "email": "arjun@materialsuppliers.com",
            "address": "753 Logistics Park, Ahmedabad, GJ 380001"
        }
    ]

    vendor_ids = {}
    for vendor_data in vendors_data:
        existing_vendor = await db.vendors.find_one({"name": vendor_data["name"]})
        if existing_vendor:
            print(f"  [OK] {vendor_data['name']} - already exists")
            vendor_ids[vendor_data["name"]] = str(existing_vendor["_id"])
        else:
            vendor_doc = {
                "name": vendor_data["name"],
                "gstin": vendor_data.get("gstin"),
                "contact_person": vendor_data.get("contact_person"),
                "phone": vendor_data.get("phone"),
                "email": vendor_data.get("email"),
                "address": vendor_data.get("address"),
                "active_status": True,
                "organisation_id": org_id,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
            result = await db.vendors.insert_one(vendor_doc)
            vendor_ids[vendor_data["name"]] = str(result.inserted_id)
            print(f"  [OK] {vendor_data['name']} - created")

    # ============================================================================
    # 6. BUDGETS (Initialize project budgets for all categories)
    # ============================================================================
    print("\n[6/6] PROJECT BUDGETS")
    for project_code, project_id in project_ids.items():
        for code, category_id in category_ids.items():
            existing_budget = await db.project_category_budgets.find_one({
                "project_id": project_id,
                "category_id": category_id
            })
            if not existing_budget:
                budget_doc = {
                    "project_id": project_id,
                    "category_id": category_id,
                    "organisation_id": org_id,
                    "original_budget": Decimal128("0.0"),
                    "committed_amount": Decimal128("0.0"),
                    "remaining_budget": Decimal128("0.0"),
                    "version": 1,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc)
                }
                await db.project_category_budgets.insert_one(budget_doc)

    print(f"  [OK] Project budgets initialized for {len(project_ids)} projects × {len(category_ids)} categories")

    client.close()

    # ============================================================================
    # SUMMARY
    # ============================================================================
    print("\n" + "="*60)
    print("SEED COMPLETE")
    print("="*60)
    print(f"\nSUMMARY:")
    print(f"   Organisation:  {org_name}")
    print(f"   Users:         {len(users_data)}")
    print(f"   Categories:    {len(category_ids)}")
    print(f"   Projects:      {len(project_ids)}")
    print(f"   Vendors:       {len(vendor_ids)}")
    print(f"\nTEST CREDENTIALS:")
    print(f"   Email:    admin@tacpmc.com")
    print(f"   Password: Admin@1234")
    print(f"\n   Email:    supervisor@tacpmc.com")
    print(f"   Password: Super@1234")
    print(f"\nAccess: https://localhost:3000")
    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(seed())
