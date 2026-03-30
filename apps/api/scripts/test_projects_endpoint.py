import asyncio

import server
from motor.motor_asyncio import AsyncIOMotorClient


async def test_endpoint():
    # Simulate the GET /api/projects endpoint
    db = AsyncIOMotorClient("mongodb://localhost:27017")["tac_pmc_crm"]

    # User Amit
    user = await db.users.find_one({"email": "amit@thirdangleconcepts.com"})
    if not user:
        print("User not found")
        return

    print(f"User found: {user['_id']}")

    # We call list_projects directly
    from project_management_routes import list_projects

    try:
        # current_user as a dict from get_current_user equivalent
        current_user = {
            "user_id": str(user["_id"]),
            "email": user["email"],
            "role": user["role"],
            "organisation_id": user["organisation_id"],
        }
        res = await list_projects(skip=0, limit=100, current_user=current_user)
        print("Success:", len(res))
    except Exception as e:
        print("Error in list_projects:")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_endpoint())
