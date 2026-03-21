from pymongo import MongoClient
import json
from bson import ObjectId

client = MongoClient('mongodb://localhost:27017')
db = client['tac_pmc_crm']

project = db.projects.find_one({'project_name': 'Majorda Villa'})
if not project:
    print("Project not found")
else:
    project_id = str(project['_id'])
    print(f"Project Name: {project['project_name']}")
    print(f"Project ID:   {project_id}")
    
    budgets = list(db.project_category_budgets.find({'project_id': project_id}))
    print(f"Budgets Count: {len(budgets)}")
    
    states = list(db.financial_state.find({'project_id': project_id}))
    print(f"Financial States Count: {len(states)}")
    
    if states:
        print("\nSample Financial State:")
        # Convert Decimal128 to float for printing
        sample = states[0]
        for k, v in sample.items():
            if type(v).__name__ == 'Decimal128':
                sample[k] = float(v.to_decimal())
        print(sample)
