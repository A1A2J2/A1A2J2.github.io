import jwt
from config import settings
import time

def test_jwt_decode():
    now = time.time()
    payload = {
        "user_id": 3,
        "username": "testuser_endpt",
        "tier": "free",
        "exp": now + 3600,
        "iat": now - 10
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    
    decoded_payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    assert decoded_payload["username"] == "testuser_endpt"
