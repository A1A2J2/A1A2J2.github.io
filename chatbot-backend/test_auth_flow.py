from fastapi.testclient import TestClient
from main import app
from database import get_db, EmailVerification

client = TestClient(app)

def test_auth_flow():
    username = "testuser_endpt"
    email = "testendpt@test.com"
    password = "testpassword"

    # Attempt signup
    resp = client.post("/api/auth/signup", json={
        "username": username,
        "password": password,
        "email": email
    })
    assert resp.status_code in [202, 409]
    
    if resp.status_code == 202:
        db = next(get_db())
        verify_record = db.query(EmailVerification).filter(EmailVerification.email == email).first()
        code = verify_record.code
        
        # Verify
        verify_resp = client.post("/api/auth/verify-email", json={
            "email": email,
            "code": code
        })
        assert verify_resp.status_code == 201

    # Login
    resp = client.post("/api/auth/login", json={
        "username": username,
        "password": password
    })
    assert resp.status_code == 200
    token = resp.json().get("token")
    assert token
    
    # Usage
    resp2 = client.get("/api/usage/remaining", headers={"Authorization": f"Bearer {token}"})
    assert resp2.status_code == 200
    assert "usage" in resp2.json()
