import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

async def debug_users():
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    db_name = os.environ.get('DB_NAME', 'tac_pmc_crm')
    
    print(f"Connecting to {mongo_url} / {db_name}")
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    users = await db.users.find().to_list(100)
    print(f"Found {len(users)} users:")
    for u in users:
        print(f" - Email: {u['email']}, Role: {u['role']}, Active: {u.get('active_status')}")
    
    if not users:
        print("NO USERS FOUND. Database might need seeding.")

if __name__ == "__main__":
    asyncio.run(debug_users())
