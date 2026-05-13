import requests

API_URL = "http://127.0.0.1:8000"

# signup
resp = requests.post(f"{API_URL}/api/auth/signup", json={
    "username": "testuser3",
    "password": "testpassword",
    "email": "test3@test.com"
})
print("Signup:", resp.status_code, resp.text)

# login
resp = requests.post(f"{API_URL}/api/auth/login", json={
    "username": "testuser3",
    "password": "testpassword"
})
print("Login:", resp.status_code, resp.text)
if resp.status_code == 200:
    token = resp.json().get("token")
    
    # usage
    resp2 = requests.get(f"{API_URL}/api/usage/remaining", headers={"Authorization": f"Bearer {token}"})
    print("Usage:", resp2.status_code, resp2.text)

