
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

async def main():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["tac_pmc_crm"]
    projects = await db.projects.find().to_list(length=10)
    for p in projects:
        print(f"ID: {p['_id']}, Type: {type(p['_id'])}")
        if "project_id" in p:
            print(f"  project_id field: {p['project_id']}, Type: {type(p['project_id'])}")
    client.close()

if __name__ == "__main__":
    asyncio.run(main())
