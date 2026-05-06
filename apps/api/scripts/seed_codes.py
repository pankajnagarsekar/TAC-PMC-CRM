import asyncio
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()


async def seed_codes():
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "tac_pmc_crm")

    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    default_codes = [
        {
            "code": "CIV",
            "category_name": "Civil Works",
            "description": "Excavation, RCC, PCC, masonry, plaster, waterproofing, basic structure",
        },
        {
            "code": "PLB",
            "category_name": "Plumbing Works",
            "description": "Piping, valves, traps, drainage, pump-room piping",
        },
        {
            "code": "ELC",
            "category_name": "Electrical Works",
            "description": "Conduits, wiring, DBs, breakers, earthing",
        },
        {
            "code": "SWP",
            "category_name": "Swimming Pool Works",
            "description": "Waterproofing, Tiling, Pool Light Fixing, Complete Pool Plumbing & Electricals, Pumps, Heaters",
        },
        {
            "code": "HVC",
            "category_name": "HVAC / Air Conditioning",
            "description": "Copper piping, drain lines, insulation, installation",
        },
        {
            "code": "FIN",
            "category_name": "Finishing Works",
            "description": "Doors, Windows, Glazing, Flooring, Tiling, Painting, False ceiling",
        },
        {
            "code": "CRP",
            "category_name": "Carpentry / Fixed",
            "description": "Wardrobes, kitchen, vanities, fixed furniture",
        },
        {
            "code": "LAN",
            "category_name": "Landscaping & External Works",
            "description": "Plants, turf, irrigation, pavers, decks",
        },
        {
            "code": "EQP",
            "category_name": "Equipments & Special System",
            "description": "Solar, filtration, STP, CCTV backbone",
        },
        {
            "code": "PRF",
            "category_name": "Professional Fees",
            "description": "Architect, Engineers, Consultants, PMC, CA, Security Guards",
        },
        {
            "code": "STC",
            "category_name": "Approvals & Statutory Charges",
            "description": "Govt/Panchayat Permissions, licenses, NOCs, utility connections",
        },
        {
            "code": "OVH",
            "category_name": "Site Overheads / Running Expenses",
            "description": "Drinking Water, Water Tankers, Chairs, stationery, extension boards, Health compliant activities",
        },
        {
            "code": "CSA",
            "category_name": "Client Supplied Assets",
            "description": "Fixtures, lights, appliances, loose furniture, décor",
        },
        {
            "code": "CON",
            "category_name": "Contingency",
            "description": "Buffer for variations & unforeseen items",
        },
    ]

    for code_data in default_codes:
        existing = await db.code_masters.find_one({"code": code_data["code"]})
        if not existing:
            code_data["active_status"] = True
            code_data["created_at"] = datetime.now(timezone.utc)
            code_data["updated_at"] = datetime.now(timezone.utc)
            await db.code_masters.insert_one(code_data)
            print(f"Seeded category: {code_data['category_name']}")
        else:
            print(f"Skipped existing category: {code_data['category_name']}")


if __name__ == "__main__":
    asyncio.run(seed_codes())
