import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

def test_flow():
    # 1. Login
    print("Logging in...")
    r = requests.post(f"{BASE_URL}/auth/login", json={
        "email": "amit@thirdangleconcept.com",
        "password": "Admin@1234"
    })
    if r.status_code != 200:
        print(f"Login failed: {r.status_code} {r.text}")
        return

    data = r.json()["data"]
    token = data["access_token"]
    user = data["user"]
    print(f"Logged in as {user['email']} (Org: {user['organisation_id']})")

    # 2. List projects
    print("\nListing projects...")
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{BASE_URL}/projects/", headers=headers)
    if r.status_code != 200:
        print(f"List projects failed: {r.status_code} {r.text}")
        return
    
    projects = r.json()["data"]
    if not projects:
        print("No projects found.")
        return
    
    target = None
    for p in projects:
        if p["project_name"] == "Majorda Villa - Civil Works":
            target = p
            break
    
    if not target:
        print("Majorda Villa not found.")
        target = projects[0]

    pid = target["_id"]
    print(f"Target Project: {target['project_name']} (ID: {pid})")

    headers["X-Project-Id"] = pid

    # 3. Get Financials
    print(f"\nFetching financials for {pid} with X-Project-Id...")
    r = requests.get(f"{BASE_URL}/projects/{pid}/financials", headers=headers)
    print(f"Financials Status: {r.status_code}")
    if r.status_code != 200:
        print(f"Financials Response: {r.text}")

    # 5. Get Settings
    print("\nFetching global settings...")
    r = requests.get(f"{BASE_URL}/settings/", headers=headers)
    print(f"Settings Status: {r.status_code}")
    if r.status_code != 200:
        print(f"Settings Response: {r.text}")

if __name__ == "__main__":
    test_flow()
