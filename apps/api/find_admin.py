import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

async def find_admin():
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    db_name = os.environ.get('DB_NAME', 'tac_pmc_crm')
    
    print(f"DEBUG: Connecting to {mongo_url} / {db_name}")
    client = AsyncIOMotorClient(mongo_url)
    
    # List all databases
    dbs = await client.list_database_names()
    print(f"DEBUG: All Databases: {dbs}")
    
    db = client[db_name]
    user = await db.users.find_one({"email": "admin@tacpmc.com"})
    
    if user:
        print(f"FOUND: {user['email']} (ID: {user['_id']})")
    else:
        print("NOT FOUND: admin@tacpmc.com")
        
    client.close()

if __name__ == "__main__":
    asyncio.run(find_admin())
