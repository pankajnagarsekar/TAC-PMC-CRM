import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext

MONGO_URL = "mongodb+srv://tacpmc_db_user:OVCxtaNhDGMuBeq6@clustertacpmc.8cbzigp.mongodb.net/?appName=ClusterTACPMC"
DB_NAME = "tac_pmc_crm"
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def reset_password():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    hashed = pwd_ctx.hash("Admin@1234")
    result = await db.users.update_one(
        {"email": "amit@thirdangleconcept.com"},
        {"$set": {"hashed_password": hashed}}
    )
    print(f"Update: {result.modified_count}")

if __name__ == "__main__":
    asyncio.run(reset_password())
