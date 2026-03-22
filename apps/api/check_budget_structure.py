
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

async def main():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["tac_pmc_crm"]
    projects = await db.projects.find().to_list(length=1)
    if projects:
        p_id_str = str(projects[0]['_id'])
        print(f"Project ID Str: {p_id_str}")
        budget = await db.project_category_budgets.find_one({"project_id": p_id_str})
        if budget:
            print(f"Budget Found with string ID: {budget['_id']}")
            print(f"  project_id in budget: {budget['project_id']}, Type: {type(budget['project_id'])}")
        else:
            print("Budget NOT found with string ID")
            budget_oid = await db.project_category_budgets.find_one({"project_id": projects[0]['_id']})
            if budget_oid:
                print(f"Budget Found with ObjectId: {budget_oid['_id']}")
                print(f"  project_id in budget: {budget_oid['project_id']}, Type: {type(budget_oid['project_id'])}")
            else:
                print("Budget NOT found with ObjectId either")
    client.close()

if __name__ == "__main__":
    asyncio.run(main())
