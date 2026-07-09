import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def inspect():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["tac_pmc_crm"]
    
    print("\n--- AUDIT LOGS IN DATABASE ---")
    logs = await db.audit_logs.find().to_list(10)
    print(f"Total count of audit logs: {await db.audit_logs.count_documents({})}")
    for log in logs:
        print(f"ID: {log.get('_id')}, Module: {log.get('module_name')}, Entity: {log.get('entity_type')}, ProjectID: {log.get('project_id')}, OrgID: {log.get('organisation_id')}")
        print(f"Details: {log}")

if __name__ == "__main__":
    asyncio.run(inspect())
