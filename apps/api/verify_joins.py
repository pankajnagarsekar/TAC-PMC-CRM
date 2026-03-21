from pymongo import MongoClient

client = MongoClient('mongodb://localhost:27017')
db = client['tac_pmc_crm']

project = db.projects.find_one({'project_name': 'Majorda Villa'})
pid = str(project['_id'])

budgets = list(db.project_category_budgets.find({'project_id': pid}))
states  = list(db.financial_state.find({'project_id': pid}))

state_map = {s.get('category_id'): s for s in states}

print(f"Project ID: {pid}")
print(f"Budgets:    {len(budgets)}")
print(f"States:     {len(states)}")

matches = 0
for b in budgets:
    cid = b.get('category_id')
    if cid in state_map:
        matches += 1

print(f"Successful Joins: {matches}")
if matches == len(budgets):
    print("ALL CATEGORIES JOINED SUCCESSFULLY")
else:
    print("MISSING JOINS DETECTED")
    if states:
        print(f"Sample State keys: {list(states[0].keys())}")
