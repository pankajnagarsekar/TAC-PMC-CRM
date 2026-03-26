import requests

def test_api():
    base_url = 'http://127.0.0.1:8000/api'
    
    print("--- LOGIN ---")
    login_data = {
        "email": "admin@tacpmc.com",
        "password": "Admin@1234"
    }
    res = requests.post(f"{base_url}/auth/login", json=login_data)
    
    if res.status_code != 200:
        print("Login failed!", res.status_code, res.text)
        return
        
    data = res.json()
    token = data.get("access_token")
    user_data = data.get("user", {})
    print(f"Logged in successfully.")
    print(f"User Role: {user_data.get('role')}")
    print(f"User Org ID: {user_data.get('organisation_id')}")
    
    print("\n--- GET PROJECTS ---")
    headers = {"Authorization": f"Bearer {token}"}
    proj_res = requests.get(f"{base_url}/projects", headers=headers)
    
    print(f"Status: {proj_res.status_code}")
    try:
        print(f"Response: {proj_res.json()}")
    except Exception as e:
        print(f"Response Raw: {proj_res.text}")

if __name__ == "__main__":
    test_api()
