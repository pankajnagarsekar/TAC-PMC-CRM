import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

async def check():
    c = AsyncIOMotorClient('mongodb+srv://tacpmc_db_user:OVCxtaNhDGMuBeq6@clustertacpmc.8cbzigp.mongodb.net/?appName=ClusterTACPMC')
    db = c['tac_pmc_crm']
    u = await db.users.find_one({'email': 'amit@thirdangleconcept.com'})
    if u:
        print(f"USER_ID: {u.get('_id')}")
        print(f"USER_ACTIVE: {u.get('active_status')}")
        print(f"USER_ORG: {u.get('organisation_id')}")
    else:
        print("USER NOT FOUND")
    c.close()

if __name__ == "__main__":
    asyncio.run(check())
