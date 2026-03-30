import asyncio

from bson import ObjectId
from models import Project
from motor.motor_asyncio import AsyncIOMotorClient


async def main():
    db = AsyncIOMotorClient("mongodb://localhost:27017")["tac_pmc_crm"]
    org_id = "69be85794e2fd1c295d5f83f"  # Amit's org ID from earlier checks (wait, I need to get it directly)
    user = await db.users.find_one({"email": "amit@thirdangleconcepts.com"})
    projects = await db.projects.find(
        {"organisation_id": str(user["organisation_id"])}
    ).to_list(length=100)
    for p in projects:
        p["project_id"] = str(p["_id"])
        try:
            proj = Project(**p)
            print(f"Project validation SUCCESS: {p['project_name']}")
        except Exception as e:
            print(f"Project validation FAILED: {p.get('project_name')}")
            print(e)
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
