#!/usr/bin/env python3
"""
Seed vendors for Third Angle Concepts (PMC) organisation
Run: python seed_vendors_thirdangle.py
"""

import os
import asyncio
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = "tac_pmc_crm"


async def seed():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    print("\n" + "="*60)
    print("[*] Seeding Vendors for Third Angle Concepts")
    print("="*60 + "\n")

    # Get Third Angle Concepts organisation
    org = await db.organisations.find_one({"name": "Third Angle Concepts (PMC)"})
    if not org:
        print("[ERROR] Third Angle Concepts organisation not found!")
        client.close()
        return

    org_id = str(org["_id"])
    print(f"[OK] Organisation ID: {org_id}\n")

    # Define vendors
    vendors_data = [
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

    print("[VENDORS] Creating vendors...\n")
    created_count = 0
    for vendor_data in vendors_data:
        existing_vendor = await db.vendors.find_one({
            "name": vendor_data["name"],
            "organisation_id": org_id
        })
        if existing_vendor:
            print(f"  [OK] {vendor_data['name']} - already exists")
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
            await db.vendors.insert_one(vendor_doc)
            print(f"  [OK] {vendor_data['name']} - created")
            created_count += 1

    client.close()

    print("\n" + "="*60)
    print("SEED COMPLETE")
    print("="*60)
    print(f"\nSUMMARY:")
    print(f"   Organisation:  Third Angle Concepts (PMC)")
    print(f"   Vendors Created: {created_count}")
    print(f"   Total Vendors: {len(vendors_data)}")
    print(f"\nYou should now see all vendors when logged in as:")
    print(f"   Email: amit@thirdangleconcepts.com")
    print(f"   Password: Admin@1234")
    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(seed())
