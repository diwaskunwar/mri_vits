import httpx
import re

API_URL = "http://localhost:8000/api"

def setup():
    # 1. Login as admin
    resp = httpx.post(f"{API_URL}/auth/login", data={"username": "admin", "password": "admin123"})
    if resp.status_code != 200:
        print("Failed to login as admin:", resp.text)
        return
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Create patient via invitations API
    inv_resp = httpx.post(f"{API_URL}/invitations/", headers=headers, json={"name": "Test", "surname": "Patient", "role": "patient", "email": "test@example.com"})
    if inv_resp.status_code != 200:
         print("Failed to create invitation", inv_resp.text)
         return
         
    inv_token = inv_resp.json()["token"]
    # Accept invitation
    accept_resp = httpx.post(f"{API_URL}/invitations/accept", json={"token": inv_token, "username":"testpatient", "password":"password123"})
    
    # Login as patient
    pat_resp = httpx.post(f"{API_URL}/auth/login", data={"username": "testpatient", "password": "password123"})
    if pat_resp.status_code != 200:
        print("Failed to login as patient:", pat_resp.text)
        return

    pat_token = pat_resp.json()["access_token"]
    pat_id = pat_resp.json()["user"]["id"]
    
    print(f"Token: {pat_token}")
    print(f"Patient ID: {pat_id}")
    
    # Update test_scaling.py
    with open("test_scaling.py", "r") as f:
        content = f.read()
    content = re.sub(r'AUTH_TOKEN = ".*?"', f'AUTH_TOKEN = "{pat_token}"', content)
    content = re.sub(r"data = \{'user_id': '.*?'", f"data = {{'user_id': '{pat_id}'", content)
    
    with open("test_scaling.py", "w") as f:
        f.write(content)
    
    print("Updated test_scaling.py")

if __name__ == "__main__":
    setup()
