import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

async def list_emails():
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    db_name = os.environ.get('DB_NAME', 'tac_pmc_crm')
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    users = await db.users.find().to_list(1000)
    print("---ALL EMAILS---")
    for u in users:
        print(u['email'])
    print("----------------")
    client.close()

if __name__ == "__main__":
    asyncio.run(list_emails())
