import asyncio

import motor.motor_asyncio
from bson import ObjectId


async def run():
    client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.tac_pmc_crm

    print("CATS_START")
    cats = await db.code_master.find({"budget_type": "fund_transfer"}).to_list(100)
    for c in cats:
        print(f"CAT|{c['_id']}|{c.get('category_name')}")
    print("CATS_END")

    print("ALLOCS_START")
    allocs = await db.fund_allocations.find().to_list(100)
    for a in allocs:
        print(
            f"ALLOC|{a.get('project_id')}|{a.get('category_id')}|{a.get('cash_in_hand')}"
        )
    print("ALLOCS_END")

    client.close()


if __name__ == "__main__":
    asyncio.run(run())
