import jwt
from config import settings

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjozLCJ1c2VybmFtZSI6InRlc3R1c2VyX2VuZHB0IiwidGllciI6ImZyZWUiLCJleHAiOjE3ODEzMjk2MzYuOTE3ODEsImlhdCI6MTc3ODczNzYzNi45MTc4Mjh9.fmCjJjW_FqgtqrK_fnBQPFilN-v7Hu75_Wq9ulBxm5s"

try:
    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    print("Success:", payload)
except Exception as e:
    import traceback
    traceback.print_exc()

