import asyncio
from motor.motor_asyncio import AsyncIOMotorClient


async def run():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["tac_pmc_crm"]
    print("\n--- USERS ---")
    async for u in db.users.find():
        print(f"User: {u.get('email')}, Role: {u.get('role')}")


if __name__ == "__main__":
    asyncio.run(run())
