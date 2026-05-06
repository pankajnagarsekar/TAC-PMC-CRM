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
            "budget_type": "commitment",
        },
        {
            "code": "PLB",
            "category_name": "Plumbing Works",
            "description": "Piping, valves, traps, drainage, pump-room piping",
            "budget_type": "commitment",
        },
        {
            "code": "ELC",
            "category_name": "Electrical Works",
            "description": "Conduits, wiring, DBs, breakers, earthing",
            "budget_type": "commitment",
        },
        {
            "code": "SWP",
            "category_name": "Swimming Pool Works",
            "description": (
                "Waterproofing, Tiling, Pool Light Fixing, Complete Pool Plumbing & Electricals, "
                "Pumps, Heaters"
            ),
            "budget_type": "commitment",
        },
        {
            "code": "HVC",
            "category_name": "HVAC / Air Conditioning",
            "description": "Copper piping, drain lines, insulation, installation",
            "budget_type": "commitment",
        },
        {
            "code": "FIN",
            "category_name": "Finishing Works",
            "description": "Doors, Windows, Glazing, Flooring, Tiling, Painting, False ceiling",
            "budget_type": "commitment",
        },
        {
            "code": "CRP",
            "category_name": "Carpentry / Fixed",
            "description": "Wardrobes, kitchen, vanities, fixed furniture",
            "budget_type": "commitment",
        },
        {
            "code": "LAN",
            "category_name": "Landscaping & External Works",
            "description": "Plants, turf, irrigation, pavers, decks",
            "budget_type": "commitment",
        },
        {
            "code": "EQP",
            "category_name": "Equipments & Special System",
            "description": "Solar, filtration, STP, CCTV backbone",
            "budget_type": "commitment",
        },
        {
            "code": "PRF",
            "category_name": "Professional Fees",
            "description": "Architect, Engineers, Consultants, PMC, CA, Security Guards",
            "budget_type": "fund_transfer",
        },
        {
            "code": "STC",
            "category_name": "Approvals & Statutory Charges",
            "description": "Govt/Panchayat Permissions, licenses, NOCs, utility connections",
            "budget_type": "fund_transfer",
        },
        {
            "code": "OVH",
            "category_name": "Site Overheads / Running Expenses",
            "description": (
                "Drinking Water, Water Tankers, Chairs, stationery, extension boards, "
                "Health compliant activities"
            ),
            "budget_type": "fund_transfer",
        },
        {
            "code": "CSA",
            "category_name": "Client Supplied Assets",
            "description": "Fixtures, lights, appliances, loose furniture, décor",
            "budget_type": "commitment",
        },
        {
            "code": "CON",
            "category_name": "Contingency",
            "description": "Buffer for variations & unforeseen items",
            "budget_type": "commitment",
        },
    ]

    for code_data in default_codes:
        code_data["updated_at"] = datetime.now(timezone.utc)
        result = await db.code_masters.update_one(
            {"code": code_data["code"]},
            {"$set": code_data},
            upsert=True
        )
        if result.upserted_id:
            await db.code_masters.update_one(
                {"_id": result.upserted_id},
                {"$set": {
                    "active_status": True,
                    "created_at": datetime.now(timezone.utc),
                    "version": 1
                }}
            )
            print(f"Seeded new category: {code_data['category_name']}")
        else:
            print(f"Updated existing category: {code_data['category_name']}")


if __name__ == "__main__":
    asyncio.run(seed_codes())
