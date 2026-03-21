import requests
import json

base_url = "http://localhost:8000/api"
login_url = f"{base_url}/auth/login"
projects_url = f"{base_url}/projects"

credentials = {
    "email": "amit@thirdangleconcepts.com",
    "password": "Admin@1234"
}

print("Attempting login...")
res = requests.post(login_url, json=credentials)
if res.status_code == 200:
    token = res.json()["access_token"]
    print("Login successful. Fetching projects...")
    
    headers = {"Authorization": f"Bearer {token}"}
    projects_res = requests.get(projects_url, headers=headers)
    print(f"Projects Status: {projects_res.status_code}")
    try:
        print(json.dumps(projects_res.json(), indent=2))
    except:
        print(projects_res.text)
else:
    print(f"Login failed: {res.status_code}")
    print(res.text)
