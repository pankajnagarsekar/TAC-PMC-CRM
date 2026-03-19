import os
import json
from datetime import datetime, timezone
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv
from pathlib import Path

# Load env
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
db_name = os.environ.get('DB_NAME', 'tac_pmc_crm')

client = MongoClient(mongo_url)
db = client[db_name]

def seed_data():
    # 1. Guirim Villament (from TAC_Baseline_R0.pdf)
    guirim_tasks = [
        {"id": "T1", "name": "Issuance of Mobilisation Advance", "duration": 1, "start": "30-03-26", "finish": "30-03-26", "predecessors": [], "cost": 0},
        {"id": "T2", "name": "Site Mobilisation", "duration": 10, "start": "30-03-26", "finish": "09-04-26", "predecessors": ["T1"], "cost": 0},
        {"id": "T3", "name": "Excavation", "duration": 15, "start": "10-04-26", "finish": "27-04-26", "predecessors": ["T2"], "cost": 0},
        {"id": "T4", "name": "Raft Foundation", "duration": 20, "start": "28-04-26", "finish": "20-05-26", "predecessors": ["T3"], "cost": 0},
        {"id": "T5", "name": "Plinth Completion", "duration": 0, "start": "20-05-26", "finish": "20-05-26", "predecessors": ["T4"], "cost": 3600000, "is_milestone": True, "is_critical": True},
        {"id": "T6", "name": "GF Slab", "duration": 30, "start": "21-05-26", "finish": "24-06-26", "predecessors": ["T5"], "cost": 0},
        {"id": "T7", "name": "Ground Floor Slab Milestone", "duration": 0, "start": "24-06-26", "finish": "24-06-26", "predecessors": ["T6"], "cost": 3600000, "is_milestone": True, "is_critical": True},
    ]
    
    # 2. Majorda Villa (from CIV_Rajesh_Tracking_14032026.pdf)
    majorda_tasks = [
        {"id": "M1", "name": "Start", "duration": 0, "start": "20-02-26", "finish": "20-02-26", "predecessors": [], "cost": 0},
        {"id": "M2", "name": "Mobilization at Site", "duration": 1, "start": "20-02-26", "finish": "20-02-26", "predecessors": ["M1"], "cost": 0},
        {"id": "M3", "name": "Surveying & Layout", "duration": 1, "start": "21-02-26", "finish": "21-02-26", "predecessors": ["M2"], "cost": 0},
        {"id": "M4", "name": "Excavation", "duration": 23, "start": "21-02-26", "finish": "20-03-26", "predecessors": ["M1"], "cost": 0, "progress": 84},
        {"id": "M5", "name": "PCC in Foundation", "duration": 2, "start": "13-03-26", "finish": "14-03-26", "predecessors": ["M4"], "cost": 0},
    ]
    
    # Seed Guirim
    db.project_schedules.update_one(
        {"project_id": "guirim-villament-dummy"},
        {"$set": {
            "project_id": "guirim-villament-dummy",
            "organisation_id": "org_123_dummy",
            "tasks": guirim_tasks,
            "project_start": "30-03-26",
            "total_cost": 7200000,
            "updated_at": datetime.now(timezone.utc)
        }},
        upsert=True
    )
    
    # Seed Majorda
    db.project_schedules.update_one(
        {"project_id": "majorda-villa-dummy"},
        {"$set": {
            "project_id": "majorda-villa-dummy",
            "organisation_id": "org_123_dummy",
            "tasks": majorda_tasks,
            "project_start": "20-02-26",
            "total_cost": 0,
            "updated_at": datetime.now(timezone.utc)
        }},
        upsert=True
    )
    
    print("Seed completed: Guirim Villament and Majorda Villa dummy data inserted.")

if __name__ == "__main__":
    seed_data()
