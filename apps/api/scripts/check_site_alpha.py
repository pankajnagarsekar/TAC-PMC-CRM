from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017")
db = client["tac_pmc_crm"]

p = db.projects.find_one({"project_name": "Site Alpha"})
if p:
    pid = str(p["_id"])
    count = db.project_category_budgets.count_documents({"project_id": pid})
    print(f"Site Alpha ID: {pid}")
    print(f"Budgets Count: {count}")
else:
    print("Site Alpha not found")
