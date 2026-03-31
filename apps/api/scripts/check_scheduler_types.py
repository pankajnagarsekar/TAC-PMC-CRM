import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path
from bson import ObjectId

load_dotenv(dotenv_path=Path('apps/api/.env'))

async def check_scheduler_data():
    client = AsyncIOMotorClient(os.getenv('MONGO_URL'))
    db = client['tac_pmc_crm']
    
    project_id = "69cb67ff3c9ee524f64da53e"
    
    print(f"Checking data for project_id: {project_id}")
    
    # 1. Check projects collection
    proj = await db.projects.find_one({'_id': ObjectId(project_id)})
    if proj:
        print(f"Project Found! organisation_id: {proj.get('organisation_id')} ({type(proj.get('organisation_id'))})")
        org_id = proj.get('organisation_id')
    else:
        print("Project NOT FOUND in projects collection")
        return

    # 2. Check project_schedules collection
    # Try string query
    sched_str = await db.project_schedules.find_one({'project_id': project_id})
    print(f"Schedule (String Query) Found: {sched_str is not None}")
    if sched_str:
        print(f"Schedule project_id type: {type(sched_str.get('project_id'))}")
        print(f"Schedule organisation_id type: {type(sched_str.get('organisation_id'))}")

    # Try ObjectId query
    sched_obj = await db.project_schedules.find_one({'project_id': ObjectId(project_id)})
    print(f"Schedule (ObjectId Query) Found: {sched_obj is not None}")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(check_scheduler_data())
