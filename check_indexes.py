import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os

async def list_indexes():
    mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    client = AsyncIOMotorClient(mongo_url)
    db = client["tac_pmc_crm"]
    
    indexes = await db.projects.index_information()
    with open("indexes_report.txt", "w") as f:
        for name, info in indexes.items():
            f.write(f"Index: {name}\n")
            f.write(f"  Key: {info['key']}\n")
            f.write(f"  Unique: {info.get('unique', False)}\n")
            f.write(f"  Sparse: {info.get('sparse', False)}\n")
            f.write("-" * 20 + "\n")
            
    client.close()

if __name__ == "__main__":
    asyncio.run(list_indexes())
