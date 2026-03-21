import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv()

async def seed_client():
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    db_name = os.environ.get('DB_NAME', 'construction_management')
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    # Get the first organisation
    org = await db.organisations.find_one({})
    if not org:
        print("No organisation found. Run seed.py first.")
        return
    
    org_id = str(org['_id'])
    
    test_client = {
        "organisation_id": org_id,
        "client_name": "Antigravity Real Estate",
        "client_email": "hello@antigravity.dev",
        "client_phone": "+91 99999 00000",
        "client_address": "123 Sky Tower, Neo City",
        "gst_number": "27BBBBB1111B1Z1",
        "active_status": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    await db.clients.insert_one(test_client)
    print("Test client seeded successfully.")

if __name__ == "__main__":
    asyncio.run(seed_client())
