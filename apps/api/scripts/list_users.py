import asyncio
import os

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()


async def list_all_users():
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "tac_pmc_crm")

    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    users = await db.users.find().to_list(1000)
    print(f"TOTAL_USERS:{len(users)}")
    for u in users:
        print(f"USER|{u['email']}|{u['role']}|{u.get('active_status')}")

    client.close()


if __name__ == "__main__":
    asyncio.run(list_all_users())
