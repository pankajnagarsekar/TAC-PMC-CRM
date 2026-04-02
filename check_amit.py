import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = "mongodb+srv://tacpmc_db_user:OVCxtaNhDGMuBeq6@clustertacpmc.8cbzigp.mongodb.net/?appName=ClusterTACPMC"
DB_NAME = "tac_pmc_crm"

async def check_user():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    user = await db.users.find_one({"email": "amit@thirdangleconcept.com"})
    if user:
        print(f"Amit keys: {list(user.keys())}")
        print(f"Amit organisation_id: {user.get('organisation_id')}")
    else:
        print("Amit not found")
        
    org = await db.organisations.find_one({"name": "TAC-PMC"})
    if org:
        print(f"Org ID: {org['_id']}")

asyncio.run(check_user())
