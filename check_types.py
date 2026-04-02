import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = "mongodb+srv://tacpmc_db_user:OVCxtaNhDGMuBeq6@clustertacpmc.8cbzigp.mongodb.net/?appName=ClusterTACPMC"
DB_NAME = "tac_pmc_crm"

async def check_types():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    user = await db.users.find_one({"email": "amit@thirdangleconcept.com"})
    if user:
        org_id = user.get('organisation_id')
        print(f"Amit organisation_id Type: {type(org_id)}")
        print(f"Amit organisation_id Value: {org_id}")
    
    # Check a client record too
    client_doc = await db.clients.find_one({})
    if client_doc:
        print(f"Client organisation_id Type: {type(client_doc.get('organisation_id'))}")
        print(f"Client organisation_id Value: {client_doc.get('organisation_id')}")

asyncio.run(check_types())
