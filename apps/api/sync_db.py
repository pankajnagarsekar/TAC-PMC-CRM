from pymongo import MongoClient
import sys

client = MongoClient("mongodb://localhost:27017")
db = client["tac_pmc_crm"]

# Find the primary organisation ID
org = db.organisations.find_one({"name": "TAC-PMC Construction"})
if not org:
    print("Organisation not found!")
    sys.exit(1)

org_id = str(org["_id"])
print(f"Primary Org ID: {org_id}")

# Force update all users to this org_id
res1 = db.users.update_many({}, {"$set": {"organisation_id": org_id}})
print(f"Updated {res1.modified_count} users to the primary org ID.")

# Force update all projects to this org_id
res2 = db.projects.update_many({}, {"$set": {"organisation_id": org_id}})
print(f"Updated {res2.modified_count} projects to the primary org ID.")

print("Success. Run debug_api.py again to verify.")
