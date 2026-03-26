from pymongo import MongoClient
from bson import Decimal128

client = MongoClient('mongodb://localhost:27017')
db = client['tac_pmc_crm']

project = db.projects.find_one({'project_name': 'Majorda Villa'})
project_id = str(project['_id'])

states = list(db.financial_state.find({'project_id': project_id}))

total_committed = 0
total_certified = 0

for s in states:
    total_committed += float(s.get('committed_value', Decimal128("0")).to_decimal())
    total_certified += float(s.get('certified_value', Decimal128("0")).to_decimal())

print(f"Total Committed: {total_committed}")
print(f"Total Certified: {total_certified}")

# Check budgets too
budgets = list(db.project_category_budgets.find({'project_id': project_id}))
total_budget = 0
for b in budgets:
    total_budget += float(b.get('original_budget', Decimal128("0")).to_decimal())
print(f"Total Budget:    {total_budget}")
