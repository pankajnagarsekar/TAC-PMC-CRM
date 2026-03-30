from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017")
db = client["tac_pmc_crm"]

project = db.projects.find_one({"project_name": "Majorda Villa"})
if not project:
    print("Majorda Villa project not found in DB.")
    exit(1)

project_id = str(project["_id"])
print(f"Migrating records for Project ID: {project_id}")

# 1. Update financial_state records: rename code_id to category_id
print("Updating financial_state collection...")
result = db.financial_state.update_many(
    {"project_id": project_id, "code_id": {"$exists": True}},
    {"$rename": {"code_id": "category_id"}},
)

print(f"Migration complete. Records updated: {result.modified_count}")
