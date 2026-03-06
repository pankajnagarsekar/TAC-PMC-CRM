import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

async def seed_codes():
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    db_name = os.environ.get('DB_NAME', 'tac_pmc_crm')
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    default_codes = [
        {"code": "CIV", "category_name": "Civil Works", "description": "Excavation, RCC, Masonry"},
        {"code": "ELE", "category_name": "Electrical", "description": "Wiring, Fixtures, DBs"},
        {"code": "PLU", "category_name": "Plumbing", "description": "Piping, Sanitary, Drainage"},
        {"code": "FIN", "category_name": "Finishes", "description": "Painting, Tiling, False Ceiling"},
        {"code": "HVAC", "category_name": "HVAC", "description": "AC, Ventilation, Ducting"},
        {"code": "EXT", "category_name": "External Works", "description": "Landscaping, Paving, Fencing"},
    ]
    
    for code_data in default_codes:
        existing = await db.code_masters.find_one({"code": code_data["code"]})
        if not existing:
            code_data["active_status"] = True
            code_data["created_at"] = datetime.utcnow()
            code_data["updated_at"] = datetime.utcnow()
            await db.code_masters.insert_one(code_data)
            print(f"Seeded category: {code_data['category_name']}")
        else:
            print(f"Skipped existing category: {code_data['category_name']}")

if __name__ == "__main__":
    asyncio.run(seed_codes())
