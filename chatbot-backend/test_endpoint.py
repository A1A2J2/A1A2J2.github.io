import requests
import json
import time

API_URL = "http://127.0.0.1:8000"

# Sign up
resp = requests.post(f"{API_URL}/api/auth/signup", json={
    "username": "testuser_endpt",
    "password": "testpassword",
    "email": "testendpt@test.com"
})
print("Signup:", resp.status_code, resp.text)

# Login
resp = requests.post(f"{API_URL}/api/auth/login", json={
    "username": "testuser_endpt",
    "password": "testpassword"
})
print("Login:", resp.status_code, resp.text)

if resp.status_code == 200:
    token = resp.json().get("token")
    
    # Usage
    resp2 = requests.get(f"{API_URL}/api/usage/remaining", headers={"Authorization": f"Bearer {token}"})
    print("Usage:", resp2.status_code, resp2.text)

