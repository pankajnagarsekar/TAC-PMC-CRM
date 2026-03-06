import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Use the same context as in auth.py
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def reseed_admin():
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "tac_pmc_crm")
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    admin_email = "admin@tacpmc.com"
    # Explicitly hash Admin@1234
    hashed_password = pwd_context.hash("Admin@1234")
    
    # 1. Ensure Organisation exists
    org_name = "TAC-PMC Construction"
    org = await db.organisations.find_one({"name": org_name})
    if not org:
        res = await db.organisations.insert_one({"name": org_name, "created_at": datetime.utcnow()})
        org_id = str(res.inserted_id)
    else:
        org_id = str(org["_id"])
    
    # 2. Force update/insert admin
    await db.users.update_one(
        {"email": admin_email},
        {
            "$set": {
                "name": "Admin User",
                "hashed_password": hashed_password,
                "role": "Admin",
                "active_status": True,
                "organisation_id": org_id,
                "updated_at": datetime.utcnow()
            },
            "$setOnInsert": {
                "created_at": datetime.utcnow(),
                "dpr_generation_permission": False
            }
        },
        upsert=True
    )
    print(f"Admin user {admin_email} has been forced to reset/inserted with new hash.")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(reseed_admin())
