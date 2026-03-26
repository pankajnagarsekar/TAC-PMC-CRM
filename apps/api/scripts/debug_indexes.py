
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

async def check_indexes():
    ROOT_DIR = Path(__file__).resolve().parent.parent
    load_dotenv(ROOT_DIR / '.env')
    
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    db_name = os.environ.get('DB_NAME', 'tac_pmc_crm') # Using the name from .env
    
    print(f"Connecting to {mongo_url} / {db_name}")
    
    client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=5000)
    db = client[db_name]
    
    try:
        collections = await db.list_collection_names()
        for coll_name in collections:
            print(f"\nIndexes for {coll_name}:")
            async for index in db[coll_name].list_indexes():
                print(f"  {index}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(check_indexes())
