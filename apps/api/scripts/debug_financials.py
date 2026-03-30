import json

import requests
from pymongo import MongoClient

# 1. Login to get token
login_url = "http://127.0.0.1:8000/api/auth/login"
login_payload = {"email": "amit@thirdangleconcepts.com", "password": "Password123"}

print("Logging in as Amit...")
response = requests.post(login_url, json=login_payload)
if response.status_code != 200:
    print(f"Login failed: {response.text}")
    exit(1)

token = response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 2. Get Project ID for Majorda Villa
client = MongoClient("mongodb://localhost:27017")
db = client["tac_pmc_crm"]
project = db.projects.find_one({"project_name": "Majorda Villa"})
project_id = str(project["_id"])
print(f"Target Project ID: {project_id}")

# 3. Call Financials API
financials_url = f"http://127.0.0.1:8000/api/v1/projects/{project_id}/financials"
print(f"Calling Financials API: {financials_url}")
response = requests.get(financials_url, headers=headers)

print(f"Financials Status: {response.status_code}")
data = response.json()
print(f"Items returned: {len(data)}")

if len(data) > 0:
    print("Sample Item Map:")
    print(json.dumps(data[0], indent=2))

    # Calculate aggregate metrics like the frontend does
    # const totalBudget = financials?.reduce((sum, f) => sum + (normalizeFinancial(f.original_budget)), 0) ?? 0;
    total_budget = sum(float(f.get("original_budget", 0)) for f in data)
    total_committed = sum(float(f.get("committed_value", 0)) for f in data)
    print(f"Calculated Total Budget:    {total_budget}")
    print(f"Calculated Total Committed: {total_committed}")
else:
    print("Zero items returned! Investigating DB contents for this PROJECT_ID...")

    budgets_count = db.project_category_budgets.count_documents(
        {"project_id": project_id}
    )
    states_count = db.financial_state.count_documents({"project_id": project_id})
    print(f"DB Budgets Count: {budgets_count}")
    print(f"DB States Count:  {states_count}")

    # Sample from DB
    sample_b = db.project_category_budgets.find_one({"project_id": project_id})
    if sample_b:
        print(f"Sample Budget entry keys: {list(sample_b.keys())}")
        print(f"Sample Budget project_id type: {type(sample_b['project_id'])}")
