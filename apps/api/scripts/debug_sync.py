from pymongo import MongoClient
import json
from bson import ObjectId

def serialize(obj):
    if isinstance(obj, ObjectId): return str(obj)
    return obj

client = MongoClient("mongodb://localhost:27017")
db = client["tac_pmc_crm"]

out = {"users": [], "projects": []}
for u in db.users.find():
    out["users"].append({
        "email": u.get("email"), 
        "org_id": u.get("organisation_id"),
        "role": u.get("role")
    })

for p in db.projects.find():
    out["projects"].append({
        "name": p.get("project_name") or p.get("name"),
        "org_id": p.get("organisation_id")
    })

with open("db_dump.json", "w") as f:
    json.dump(out, f, indent=2)
