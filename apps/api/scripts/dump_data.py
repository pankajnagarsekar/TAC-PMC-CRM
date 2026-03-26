from pymongo import MongoClient
from bson import Decimal128, ObjectId

client = MongoClient('mongodb://localhost:27017')
db = client['tac_pmc_crm']

project = db.projects.find_one({'project_name': 'Majorda Villa'})
project_id = str(project['_id'])
print(f"MAJORDA VILLA IDENTITY: {project_id}\n")

print("--- BUDGETS ---")
budgets = list(db.project_category_budgets.find({'project_id': project_id}))
for b in budgets:
    print(f"Cat: {b['category_id']} | Budget: {b['original_budget']} | Type: {type(b['category_id'])}")

print("\n--- FINANCIAL STATES ---")
states = list(db.financial_state.find({'project_id': project_id}))
for s in states:
    print(f"Cat: {s['category_id']} | Committed: {s['committed_value']} | Type: {type(s['category_id'])}")
