import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os

async def check():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["tac_pmc_crm"]
    pc = await db.payment_certificates.find_one()
    if pc:
        print("Keys:", list(pc.keys()))
        print("Values:", {k: str(v) for k, v in pc.items() if k in ['grand_total', 'total_payable', 'actual_payable', 'total_after_retention']})
    else:
        print("No PC found")
    client.close()

if __name__ == "__main__":
    asyncio.run(check())
